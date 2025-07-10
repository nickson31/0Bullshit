import os
import json
import google.generativeai as genai
from typing import Dict, Any, List, Optional
from models.schemas import (
    JudgeDecision, JudgeProbabilities, ExtractedData, 
    Project, ProjectData
)
import logging
import re

logger = logging.getLogger(__name__)

class JudgeSystem:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "temperature": 0.3,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2000,
            }
        )
    
    async def analyze_user_intent(
        self, 
        user_message: str, 
        project: Project, 
        conversation_history: List[Dict[str, str]] = None
    ) -> JudgeDecision:
        """
        Analizar la intención del usuario y decidir qué acción tomar
        """
        try:
            # Calcular completeness score
            completeness_score = self._calculate_completeness_score(project.project_data)
            
            # Preparar contexto
            context = self._prepare_context(project, conversation_history, completeness_score)
            
            # Crear prompt para Gemini
            prompt = self._create_judge_prompt(user_message, context, completeness_score)
            
            # Obtener respuesta de Gemini
            response = self.model.generate_content(prompt)
            
            # Parsear respuesta JSON
            decision_data = self._parse_gemini_response(response.text)
            
            # Verificar anti-spam
            anti_spam_check = self._check_anti_spam(user_message)
            
            # Ajustar decisión si es necesario
            final_decision = self._adjust_decision_based_on_completeness(
                decision_data, completeness_score, anti_spam_check
            )
            
            return final_decision
            
        except Exception as e:
            logger.error(f"Error in judge analysis: {e}")
            # Retorno de emergencia
            return self._create_fallback_decision(user_message, completeness_score)
    
    def _calculate_completeness_score(self, project_data: ProjectData) -> float:
        """
        Calcular score de completitud del proyecto
        Categories (25%) + Stage (25%) + Other fields (50%)
        """
        score = 0.0
        
        # Categories - 25%
        if project_data.categories and len(project_data.categories) > 0:
            score += 0.25
        
        # Stage - 25%
        if project_data.stage:
            score += 0.25
        
        # Metrics - 15%
        if project_data.metrics:
            if any([project_data.metrics.arr, project_data.metrics.mrr, 
                   project_data.metrics.users, project_data.metrics.revenue]):
                score += 0.15
        
        # Team info - 10%
        if project_data.team_info:
            if any([project_data.team_info.size, project_data.team_info.roles, 
                   project_data.team_info.experience]):
                score += 0.10
        
        # Problem solved - 10%
        if project_data.problem_solved:
            score += 0.10
        
        # Product status - 10%
        if project_data.product_status:
            score += 0.10
        
        # Previous funding - 5%
        if project_data.previous_funding:
            score += 0.05
        
        return round(score, 2)
    
    def _prepare_context(
        self, 
        project: Project, 
        conversation_history: List[Dict[str, str]], 
        completeness_score: float
    ) -> Dict[str, Any]:
        """Preparar contexto para el análisis"""
        return {
            "project_name": project.name,
            "project_description": project.description,
            "categories": project.project_data.categories or [],
            "stage": project.project_data.stage,
            "completeness_score": completeness_score,
            "has_metrics": bool(project.project_data.metrics),
            "has_team_info": bool(project.project_data.team_info),
            "conversation_history": conversation_history[-3:] if conversation_history else [],
            "platform_capabilities": [
                "buscar inversores especializados",
                "buscar empresas/servicios para solucionar problemas",
                "mentoría estilo Y-Combinator",
                "hacer preguntas para completar información del proyecto",
                "outreach automatizado (después de búsquedas)"
            ]
        }
    
    def _create_judge_prompt(self, user_message: str, context: Dict[str, Any], completeness_score: float) -> str:
        """Crear prompt para Gemini que actúe como juez/policía"""
        
        y_combinator_principles = """
        PRINCIPIOS Y-COMBINATOR PARA CONTEXTO:
        - Ser conciso y directo, no perder tiempo
        - Hacer preguntas específicas que realmente importen
        - Enfocarse en métricas reales (ARR, MRR, usuarios, growth)
        - Validar problem-solution fit antes de hablar de dinero
        - El equipo es crítico - quién programa, experiencia previa
        - Tracción > ideas, ejecutar > planear
        - Preguntar por el "ask" específico cuando sea apropiado
        """
        
        return f"""
        ACTÚA COMO UN EJECUTIVO DE Y-COMBINATOR EXPERTO EN STARTUPS QUE DEBE JUZGAR LA INTENCIÓN DEL USUARIO.

        {y_combinator_principles}

        CONTEXTO DEL PROYECTO:
        {json.dumps(context, indent=2, ensure_ascii=False)}

        MENSAJE DEL USUARIO: "{user_message}"

        SCORE DE COMPLETITUD ACTUAL: {completeness_score:.0%}

        INSTRUCCIONES:
        1. Analiza la intención real del usuario con expertise de Y-Combinator
        2. Considera el contexto del proyecto y completitud
        3. Decide la mejor acción basada en principios de mentoría efectiva
        4. Si detectas spam/bullshit/contenido ofensivo, marca anti_spam
        5. Si completitud < 50%, considera si necesita hacer preguntas obligatorias primero

        RESPONDE SOLO CON JSON VÁLIDO:
        {{
            "probabilities": {{
                "search_investors": 0-100,
                "search_companies": 0-100,
                "mentoring": 0-100,
                "ask_questions": 0-100,
                "anti_spam": 0-100
            }},
            "decision": "search_investors|search_companies|mentoring|ask_questions|anti_spam",
            "reasoning": "Explicación detallada de la decisión basada en Y-Combinator principles",
            "confidence_score": 0-100,
            "required_questions": ["pregunta1", "pregunta2"] (solo si ask_questions),
            "extracted_data": {{
                "categories": ["categoria1", "categoria2"] (si detectas),
                "stage": "stage detectado" (si detectas),
                "metrics": {{"arr": "valor", "mrr": "valor"}} (si detectas),
                "team_info": {{"size": numero}} (si detectas),
                "problem_solved": "descripción" (si detectas),
                "product_status": "estado" (si detectas),
                "additional_data": {{}} (otros datos relevantes)
            }},
            "should_ask_questions": true/false,
            "anti_spam_triggered": true/false
        }}

        CRITERIOS DE DECISIÓN:
        - SEARCH_INVESTORS: Usuario menciona funding, inversión, Serie A/B, runway, ARR/MRR altos
        - SEARCH_COMPANIES: Usuario menciona necesidad de servicios (legal, marketing, tech, etc.)
        - MENTORING: Preguntas sobre estrategia, growth, product-market fit, equipo
        - ASK_QUESTIONS: Completitud < 50% Y usuario quiere búsquedas, O información muy vaga
        - ANTI_SPAM: Contenido ofensivo, sin sentido, o claramente spam

        RECUERDA: Actúa como un mentor Y-Combinator que prioriza EJECUTAR y obtener TRACCIÓN REAL.
        """
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parsear respuesta JSON de Gemini"""
        try:
            # Limpiar respuesta
            json_text = response_text.strip()
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0]
            
            return json.loads(json_text.strip())
            
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            logger.error(f"Response text: {response_text}")
            raise
    
    def _check_anti_spam(self, message: str) -> bool:
        """Verificar si el mensaje es spam o bullshit"""
        spam_patterns = [
            r'\b(fuck|shit|damn|puta|mierda|joder)\b',  # Palabras ofensivas
            r'^.{1,5}$',  # Mensajes muy cortos (menos de 5 caracteres)
            r'(.)\1{4,}',  # Caracteres repetidos (aaaaa)
            r'^\s*$',  # Solo espacios
            r'(jajaja|hahaha|lol){3,}',  # Risas repetitivas
        ]
        
        message_lower = message.lower().strip()
        
        for pattern in spam_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _adjust_decision_based_on_completeness(
        self, 
        decision_data: Dict[str, Any], 
        completeness_score: float,
        anti_spam_triggered: bool
    ) -> JudgeDecision:
        """Ajustar decisión basada en completitud y anti-spam"""
        
        # Si es anti-spam, override decision
        if anti_spam_triggered or decision_data.get("anti_spam_triggered", False):
            decision_data["decision"] = "anti_spam"
            decision_data["probabilities"]["anti_spam"] = 100
            decision_data["should_ask_questions"] = False
        
        # Si completitud < 50% y quiere búsquedas, forzar preguntas
        elif completeness_score < 0.5 and decision_data["decision"] in ["search_investors", "search_companies"]:
            decision_data["should_ask_questions"] = True
            decision_data["required_questions"] = self._generate_required_questions(completeness_score)
        
        # Si completitud >= 50% pero < 70%, recomendar preguntas después
        elif 0.5 <= completeness_score < 0.7 and decision_data["decision"] in ["search_investors", "search_companies"]:
            decision_data["should_ask_questions"] = False  # No bloquear, pero recomendar después
        
        return JudgeDecision(
            probabilities=JudgeProbabilities(**decision_data["probabilities"]),
            decision=decision_data["decision"],
            reasoning=decision_data["reasoning"],
            confidence_score=decision_data["confidence_score"],
            required_questions=decision_data.get("required_questions", []),
            extracted_data=ExtractedData(**decision_data.get("extracted_data", {})) if decision_data.get("extracted_data") else None,
            completeness_score=completeness_score,
            should_ask_questions=decision_data.get("should_ask_questions", False),
            anti_spam_triggered=anti_spam_triggered or decision_data.get("anti_spam_triggered", False)
        )
    
    def _generate_required_questions(self, completeness_score: float) -> List[str]:
        """Generar preguntas obligatorias basadas en completitud"""
        questions = []
        
        if completeness_score < 0.25:  # Faltan categories Y stage
            questions.extend([
                "¿En qué sector/industria opera tu startup? (ej: fintech, saas, ecommerce)",
                "¿En qué etapa se encuentra tu proyecto? (idea, mvp, seed, series-a, etc.)"
            ])
        elif completeness_score < 0.5:  # Falta categories O stage
            questions.append("Para hacer una búsqueda efectiva, necesito saber el sector y la etapa de tu startup.")
        
        return questions
    
    def _create_fallback_decision(self, user_message: str, completeness_score: float) -> JudgeDecision:
        """Crear decisión de fallback en caso de error"""
        
        # Análisis simple basado en keywords
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["inversor", "funding", "financiación", "capital", "serie"]):
            decision = "search_investors" if completeness_score >= 0.5 else "ask_questions"
        elif any(word in message_lower for word in ["empresa", "servicio", "ayuda", "legal", "marketing"]):
            decision = "search_companies"
        else:
            decision = "mentoring"
        
        return JudgeDecision(
            probabilities=JudgeProbabilities(
                search_investors=70 if "inversor" in message_lower else 10,
                search_companies=70 if "empresa" in message_lower else 10,
                mentoring=50,
                ask_questions=30 if completeness_score < 0.5 else 10,
                anti_spam=0
            ),
            decision=decision,
            reasoning="Análisis de fallback por error en Gemini",
            confidence_score=50.0,
            required_questions=self._generate_required_questions(completeness_score) if completeness_score < 0.5 else [],
            extracted_data=None,
            completeness_score=completeness_score,
            should_ask_questions=completeness_score < 0.5,
            anti_spam_triggered=False
        )

# Instancia global
judge = JudgeSystem()
