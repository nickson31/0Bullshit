import os
import json
import asyncio
import google.generativeai as genai
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4
from datetime import datetime
from models.schemas import (
    ChatMessage, ChatResponse, JudgeDecision, WelcomeMessage,
    SearchResults, InvestorResult, CompanyResult, CompletenessResponse
)
from database.database import db
from chat.judge import judge
from chat.librarian import librarian
from chat.welcome import welcome_system
import logging

logger = logging.getLogger(__name__)

class ChatSystem:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 3000,
            }
        )
        
        # Y-Combinator principles para el mentor
        self.yc_principles = """
        PRINCIPIOS Y-COMBINATOR PARA MENTORÍA:
        
        1. ENFÓCATE EN EJECUTAR: Menos planear, más hacer
        2. TALK TO USERS: Hablar con usuarios es más importante que features
        3. METRICS MATTER: ARR, MRR, growth rate, churn - números reales
        4. PROBLEM-SOLUTION FIT: ¿Realmente resuelves un problema doloroso?
        5. TEAM IS EVERYTHING: ¿Quién programa? ¿Experiencia previa?
        6. CONCISIÓN: Explicar en 2 frases qué haces y cómo generas dinero
        7. TRACCIÓN > IDEAS: Qué has conseguido, no qué vas a conseguir
        8. BE DIRECT: Preguntas directas, respuestas directas
        9. PRODUCT-MARKET FIT: Lo más importante antes de escalar
        10. ASK FOR MONEY: Si necesitas funding, pídelo explícitamente
        """
    
    async def process_message(
        self, 
        user_message: str, 
        project_id: UUID, 
        user_id: UUID,
        websocket_callback=None
    ) -> Tuple[ChatResponse, Optional[SearchResults]]:
        """
        Procesar mensaje del usuario - Función principal
        """
        try:
            # 1. Obtener proyecto y contexto
            project = await db.get_project(project_id, user_id)
            if not project:
                raise ValueError("Project not found")
            
            conversation_history = await db.get_conversations(project_id, limit=10)
            
            # 2. Guardar mensaje del usuario
            user_conversation = ChatResponse(
                id=uuid4(),
                project_id=project_id,
                role="user",
                content=user_message,
                created_at=datetime.now()
            )
            await db.save_conversation(user_conversation)
            
            # 3. FASE JUEZ: Analizar intención
            if websocket_callback:
                await websocket_callback({
                    "type": "analysis_start",
                    "message": "Analizando tu solicitud..."
                })
            
            judge_decision = await judge.analyze_user_intent(
                user_message, 
                project, 
                [{"role": conv.role, "content": conv.content} for conv in conversation_history[-5:]]
            )
            
            # 4. Ejecutar acción basada en decisión del juez
            assistant_response, search_results = await self._execute_judge_decision(
                judge_decision,
                user_message,
                project,
                user_id,
                websocket_callback
            )
            
            # 5. Guardar respuesta del asistente
            assistant_conversation = ChatResponse(
                id=uuid4(),
                project_id=project_id,
                role="assistant",
                content=assistant_response,
                ai_extractions={
                    "judge_decision": judge_decision.dict(),
                    "search_results": search_results.dict() if search_results else None
                },
                gemini_prompt_used="chat_response",
                gemini_response_raw=assistant_response,
                created_at=datetime.now()
            )
            await db.save_conversation(assistant_conversation)
            
            # 6. BOT BIBLIOTECARIO: Procesar en background
            asyncio.create_task(
                librarian.process_conversation_update(
                    project_id,
                    assistant_conversation.id,
                    user_message,
                    assistant_response,
                    project.project_data
                )
            )
            
            return assistant_conversation, search_results
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Respuesta de error
            error_response = ChatResponse(
                id=uuid4(),
                project_id=project_id,
                role="assistant",
                content=f"Lo siento, hubo un error procesando tu mensaje. Por favor, inténtalo de nuevo.",
                created_at=datetime.now()
            )
            return error_response, None
    
    async def _execute_judge_decision(
        self,
        decision: JudgeDecision,
        user_message: str,
        project,
        user_id: UUID,
        websocket_callback=None
    ) -> Tuple[str, Optional[SearchResults]]:
        """Ejecutar la decisión del juez"""
        
        if decision.anti_spam_triggered:
            return await self._handle_anti_spam(), None
        
        elif decision.decision == "ask_questions":
            return await self._handle_ask_questions(decision, project), None
        
        elif decision.decision == "search_investors":
            return await self._handle_search_investors(
                decision, project, user_message, websocket_callback
            )
        
        elif decision.decision == "search_companies":
            return await self._handle_search_companies(
                decision, project, user_message, websocket_callback
            )
        
        elif decision.decision == "mentoring":
            return await self._handle_mentoring(
                decision, user_message, project
            ), None
        
        else:
            return await self._handle_general_response(user_message, project), None
    
    async def _handle_anti_spam(self) -> str:
        """Manejar contenido spam/ofensivo"""
        
        anti_spam_responses = [
            "Entiendo que quieres probar la plataforma, pero estoy aquí para ayudarte con tu startup de verdad. ¿Podrías contarme sobre tu proyecto?",
            
            "Esta plataforma está diseñada para founders serios. Si tienes una startup o idea de negocio, me encantaría ayudarte. ¿Qué estás construyendo?",
            
            "Hey, soy un mentor de Y-Combinator virtual. Estoy aquí para ayudarte a hacer crecer tu startup. ¿Tienes un proyecto en el que esté trabajando?",
            
            "Vamos a enfocarnos en algo productivo. ¿Tienes una startup, idea de negocio, o necesitas ayuda para conseguir inversión? Estoy aquí para eso.",
        ]
        
        return anti_spam_responses[0]  # Por ahora usar el primero
    
    async def _handle_ask_questions(self, decision: JudgeDecision, project) -> str:
        """Manejar cuando se necesita hacer preguntas"""
        
        if decision.should_ask_questions and decision.required_questions:
            questions = "\n".join([f"• {q}" for q in decision.required_questions])
            
            return f"""Para ayudarte de la mejor manera, necesito conocer un poco más sobre tu startup:

{questions}

Una vez que tenga esta información, podré hacer búsquedas más precisas y darte recomendaciones específicas.

{decision.reasoning}"""
        
        else:
            # Preguntas más generales para completar información
            missing_info = self._get_missing_info_questions(project.project_data)
            
            return f"""Veo que tu proyecto tiene potencial. Para darte las mejores recomendaciones, me gustaría conocer:

{missing_info}

No te preocupes por ser perfecto, podemos ir afinando los detalles. ¿Qué información puedes compartir?"""
    
    async def _handle_search_investors(
        self, 
        decision: JudgeDecision, 
        project, 
        user_message: str,
        websocket_callback=None
    ) -> Tuple[str, SearchResults]:
        """Manejar búsqueda de inversores"""
        
        # Verificar completitud para decidir flujo
        if decision.completeness_score < 0.5:
            # Preguntar primero, luego buscar
            questions = self._get_missing_info_questions(project.project_data)
            response = f"""Perfecto, te voy a ayudar a encontrar inversores. Pero primero necesito:

{questions}

Una vez que tenga esta información, haré una búsqueda personalizada. ¿Puedes compartir estos detalles?"""
            
            return response, None
        
        else:
            # Buscar directamente
            if websocket_callback:
                await websocket_callback({
                    "type": "search_start",
                    "message": "Buscando inversores especializados en tu sector..."
                })
            
            # Realizar búsqueda
            investors = await db.search_investors(
                categories=project.project_data.categories or [],
                stage=project.project_data.stage,
                limit=10
            )
            
            search_results = SearchResults(
                investors=investors,
                companies=None,
                total_found=len(investors),
                search_criteria={
                    "categories": project.project_data.categories,
                    "stage": project.project_data.stage
                }
            )
            
            if websocket_callback:
                await websocket_callback({
                    "type": "search_complete",
                    "data": search_results.dict()
                })
            
            # Generar respuesta
            response = await self._generate_investor_search_response(
                investors, decision, project
            )
            
            return response, search_results
    
    async def _handle_search_companies(
        self, 
        decision: JudgeDecision, 
        project, 
        user_message: str,
        websocket_callback=None
    ) -> Tuple[str, SearchResults]:
        """Manejar búsqueda de empresas/servicios"""
        
        if websocket_callback:
            await websocket_callback({
                "type": "search_start", 
                "message": "Buscando empresas especializadas para ayudarte..."
            })
        
        # Realizar búsqueda
        companies = await db.search_companies(
            problem_context=user_message,
            categories=project.project_data.categories or [],
            limit=8
        )
        
        search_results = SearchResults(
            investors=None,
            companies=companies,
            total_found=len(companies),
            search_criteria={
                "problem_context": user_message,
                "categories": project.project_data.categories
            }
        )
        
        if websocket_callback:
            await websocket_callback({
                "type": "search_complete",
                "data": search_results.dict()
            })
        
        # Generar respuesta
        response = await self._generate_company_search_response(
            companies, decision, user_message
        )
        
        return response, search_results
    
    async def _handle_mentoring(
        self, 
        decision: JudgeDecision, 
        user_message: str, 
        project
    ) -> str:
        """Manejar mentoría estilo Y-Combinator"""
        
        context = self._prepare_mentoring_context(project, decision)
        
        prompt = f"""
        ACTÚA COMO UN MENTOR DE Y-COMBINATOR RESPONDIENDO A UNA STARTUP.

        {self.yc_principles}

        CONTEXTO DEL PROYECTO:
        {json.dumps(context, indent=2, ensure_ascii=False)}

        PREGUNTA/SOLICITUD DEL FOUNDER: "{user_message}"

        ANÁLISIS DEL JUEZ: {decision.reasoning}

        INSTRUCCIONES:
        1. Responde como un mentor Y-Combinator experimentado
        2. Sé directo, conciso y práctico
        3. Enfócate en EJECUTAR y obtener TRACCIÓN
        4. Haz preguntas específicas si necesitas más información
        5. Da consejos accionables, no teoría
        6. Ajusta el length de respuesta según la complejidad de la pregunta
        7. Si es una pregunta simple, respuesta simple
        8. Si es compleja, profundiza pero mantén estructura clara

        RESPONDE DIRECTAMENTE (NO JSON):
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error in mentoring response: {e}")
            return self._get_fallback_mentoring_response(user_message)
    
    async def _handle_general_response(self, user_message: str, project) -> str:
        """Manejar respuesta general"""
        
        prompt = f"""
        Responde como un asistente especializado en startups.
        
        Proyecto: {project.name}
        Pregunta: {user_message}
        
        Sé útil, conciso y enfócate en ayudar con temas de startup.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error in general response: {e}")
            return "¿En qué puedo ayudarte con tu startup hoy?"
    
    def _get_missing_info_questions(self, project_data) -> str:
        """Generar preguntas para información faltante"""
        questions = []
        
        if not project_data.categories:
            questions.append("• ¿En qué sector/industria opera tu startup?")
        
        if not project_data.stage:
            questions.append("• ¿En qué etapa se encuentra? (idea, MVP, seed, series-A, etc.)")
        
        if not project_data.metrics or not any([
            project_data.metrics.arr, project_data.metrics.mrr, project_data.metrics.users
        ]):
            questions.append("• ¿Tienes métricas como ARR, MRR o número de usuarios?")
        
        return "\n".join(questions) if questions else "• Más detalles sobre tu modelo de negocio"
    
    def _prepare_mentoring_context(self, project, decision) -> Dict[str, Any]:
        """Preparar contexto para mentoría"""
        return {
            "project_name": project.name,
            "description": project.description,
            "categories": project.project_data.categories,
            "stage": project.project_data.stage,
            "completeness_score": decision.completeness_score,
            "metrics": project.project_data.metrics.dict() if project.project_data.metrics else None,
            "team_info": project.project_data.team_info.dict() if project.project_data.team_info else None,
            "problem_solved": project.project_data.problem_solved,
            "product_status": project.project_data.product_status
        }
    
    async def _generate_investor_search_response(
        self, 
        investors: List[InvestorResult], 
        decision: JudgeDecision, 
        project
    ) -> str:
        """Generar respuesta para búsqueda de inversores"""
        
        if not investors:
            return f"""No encontré inversores específicos para tu criterio de búsqueda actual. 

Esto puede ser porque:
• Los criterios son muy específicos
• Necesito más información sobre tu sector/etapa

¿Podrías darme más detalles sobre tu startup para ampliar la búsqueda?"""
        
        # Generar resumen de resultados
        investor_summary = []
        for inv in investors[:3]:  # Top 3
            summary = f"**{inv.full_name}**"
            if inv.fund_name:
                summary += f" - {inv.fund_name}"
            if inv.categories_match:
                summary += f" (Especialista en {', '.join(inv.categories_match)})"
            investor_summary.append(summary)
        
        response = f"""🎯 **Encontré {len(investors)} inversores relevantes para tu startup:**

{chr(10).join(investor_summary)}

*Relevancia calculada basada en tu sector ({', '.join(project.project_data.categories or [])}) y etapa ({project.project_data.stage or 'No especificada'})*

"""
        
        # Añadir recomendación si completitud es media
        if 0.5 <= decision.completeness_score < 0.7:
            response += """
💡 **Para mejores resultados de outreach, recomiendo que completes:**
• Métricas específicas (ARR, MRR, crecimiento)
• Información del equipo fundador
• Descripción clara del problema que resuelves

¿Te gustaría que hagamos el outreach con la información actual o prefieres completar más detalles primero?"""
        
        return response
    
    async def _generate_company_search_response(
        self, 
        companies: List[CompanyResult], 
        decision: JudgeDecision, 
        user_message: str
    ) -> str:
        """Generar respuesta para búsqueda de empresas"""
        
        if not companies:
            return f"""No encontré empresas específicas para tu necesidad actual.

¿Podrías ser más específico sobre qué tipo de ayuda necesitas? Por ejemplo:
• Desarrollo tecnológico
• Marketing y growth
• Legal y compliance
• Finanzas y accounting"""
        
        # Generar resumen de empresas
        company_summary = []
        for comp in companies[:3]:
            summary = f"**{comp.nombre}**"
            if comp.service_category:
                summary += f" - {comp.service_category}"
            if comp.descripcion_corta:
                summary += f"\n  {comp.descripcion_corta[:100]}..."
            company_summary.append(summary)
        
        return f"""🏢 **Encontré {len(companies)} empresas que pueden ayudarte:**

{chr(10).join(company_summary)}

*Basado en tu solicitud: "{user_message[:100]}..."*

¿Te interesa alguna de estas opciones o necesitas un tipo de servicio diferente?"""
    
    def _get_fallback_mentoring_response(self, user_message: str) -> str:
        """Respuesta de fallback para mentoría"""
        return f"""Entiendo tu pregunta sobre: "{user_message}"

Como mentor, mi recomendación es enfocarte en:
1. **Validar con usuarios reales** - Habla con 10 usuarios potenciales esta semana
2. **Medir lo que importa** - ARR, MRR, growth rate, churn
3. **Ejecutar rápido** - Menos planning, más building y testing

¿Hay algún aspecto específico en el que quieres profundizar?"""
    
    async def get_project_completeness(self, project_id: UUID, user_id: UUID) -> CompletenessResponse:
        """Obtener análisis de completitud del proyecto"""
        try:
            project = await db.get_project(project_id, user_id)
            if not project:
                raise ValueError("Project not found")
            
            # Calcular score y breakdown
            breakdown = {}
            score = 0.0
            
            # Categories - 25%
            if project.project_data.categories and len(project.project_data.categories) > 0:
                breakdown["categories"] = 0.25
                score += 0.25
            else:
                breakdown["categories"] = 0.0
            
            # Stage - 25%  
            if project.project_data.stage:
                breakdown["stage"] = 0.25
                score += 0.25
            else:
                breakdown["stage"] = 0.0
            
            # Otros campos...
            if project.project_data.metrics and any([
                project.project_data.metrics.arr, 
                project.project_data.metrics.mrr,
                project.project_data.metrics.users
            ]):
                breakdown["metrics"] = 0.15
                score += 0.15
            else:
                breakdown["metrics"] = 0.0
            
            # Identificar campos faltantes
            missing_fields = []
            required_fields = ["categories", "stage"]
            
            if not project.project_data.categories:
                missing_fields.append("categories")
            if not project.project_data.stage:
                missing_fields.append("stage")
            if not project.project_data.metrics:
                missing_fields.append("metrics")
            
            suggestions = []
            if "categories" in missing_fields:
                suggestions.append("Especifica el sector de tu startup (ej: fintech, saas, ecommerce)")
            if "stage" in missing_fields:
                suggestions.append("Indica en qué etapa estás (idea, mvp, seed, series-a)")
            if "metrics" in missing_fields:
                suggestions.append("Comparte métricas como ARR, MRR o número de usuarios")
            
            return CompletenessResponse(
                score=round(score, 2),
                missing_fields=missing_fields,
                required_fields=required_fields,
                suggestions=suggestions,
                breakdown=breakdown
            )
            
        except Exception as e:
            logger.error(f"Error calculating completeness: {e}")
            return CompletenessResponse(
                score=0.0,
                missing_fields=["categories", "stage"],
                required_fields=["categories", "stage"],
                suggestions=["Complete la información básica del proyecto"],
                breakdown={}
            )

# Instancia global
chat_system = ChatSystem()
