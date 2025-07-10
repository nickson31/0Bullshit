import os
import json
import google.generativeai as genai
from typing import Dict, Any, List, Optional
from uuid import UUID
from models.schemas import WelcomeMessage, Project
from database.database import db
import logging

logger = logging.getLogger(__name__)

class WelcomeSystem:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "temperature": 0.4,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 1000,
            }
        )
    
    async def generate_welcome_message(
        self, 
        project: Project, 
        user_id: UUID,
        is_first_time_user: bool = False
    ) -> WelcomeMessage:
        """
        Generar mensaje de bienvenida personalizado
        """
        try:
            # Calcular completitud
            completeness_score = self._calculate_completeness_score(project.project_data)
            
            # Verificar si es primera vez
            if is_first_time_user:
                user_projects = await db.get_user_projects(user_id)
                is_first_time = len(user_projects) <= 1
            else:
                is_first_time = False
            
            # Verificar si tiene conversaciones previas
            conversations = await db.get_conversations(project.id, limit=5)
            has_previous_conversations = len(conversations) > 0
            
            # Determinar tipo de mensaje
            message_type = self._determine_message_type(
                is_first_time, 
                has_previous_conversations, 
                completeness_score
            )
            
            # Generar mensaje personalizado
            message_content = await self._generate_personalized_message(
                project, 
                message_type, 
                completeness_score
            )
            
            # Generar acciones sugeridas
            suggested_actions = self._generate_suggested_actions(
                message_type, 
                completeness_score,
                project.project_data
            )
            
            return WelcomeMessage(
                message=message_content,
                message_type=message_type,
                suggested_actions=suggested_actions
            )
            
        except Exception as e:
            logger.error(f"Error generating welcome message: {e}")
            return self._get_fallback_welcome_message(is_first_time_user)
    
    def _calculate_completeness_score(self, project_data) -> float:
        """Calcular score de completitud (mismo que en judge.py)"""
        score = 0.0
        
        if project_data.categories and len(project_data.categories) > 0:
            score += 0.25
        
        if project_data.stage:
            score += 0.25
        
        if project_data.metrics:
            if any([project_data.metrics.arr, project_data.metrics.mrr, 
                   project_data.metrics.users, project_data.metrics.revenue]):
                score += 0.15
        
        if project_data.team_info:
            if any([project_data.team_info.size, project_data.team_info.roles, 
                   project_data.team_info.experience]):
                score += 0.10
        
        if project_data.problem_solved:
            score += 0.10
        
        if project_data.product_status:
            score += 0.10
        
        if project_data.previous_funding:
            score += 0.05
        
        return round(score, 2)
    
    def _determine_message_type(
        self, 
        is_first_time: bool, 
        has_conversations: bool, 
        completeness_score: float
    ) -> str:
        """Determinar el tipo de mensaje de bienvenida"""
        
        if is_first_time and not has_conversations:
            return "new_user"
        elif not has_conversations:
            return "new_project"
        elif completeness_score < 0.5:
            return "low_completeness"
        else:
            return "returning_user"
    
    async def _generate_personalized_message(
        self, 
        project: Project, 
        message_type: str, 
        completeness_score: float
    ) -> str:
        """Generar mensaje personalizado con Gemini"""
        
        context = {
            "project_name": project.name,
            "project_description": project.description,
            "categories": project.project_data.categories or [],
            "stage": project.project_data.stage,
            "completeness_score": completeness_score,
            "message_type": message_type
        }
        
        prompt = f"""
        ACTÚA COMO UN EJECUTIVO DE Y-COMBINATOR CREANDO UN MENSAJE DE BIENVENIDA PERSONALIZADO.

        CONTEXTO DEL PROYECTO:
        {json.dumps(context, indent=2, ensure_ascii=False)}

        TIPO DE MENSAJE: {message_type}
        COMPLETITUD: {completeness_score:.0%}

        INSTRUCCIONES SEGÚN TIPO:

        NEW_USER: 
        - Bienvenida cálida explicando qué es 0Bullshit
        - Explicar capacidades: buscar inversores, empresas, mentoría Y-Combinator
        - Mencionar que necesitamos conocer su proyecto para ayudar mejor
        - Tono: Profesional pero friendly, como Y-Combinator

        NEW_PROJECT:
        - Usuario conoce la plataforma, nuevo proyecto
        - Enfocarse en este proyecto específico
        - Mencionar brevemente las capacidades

        LOW_COMPLETENESS:
        - Usuario tiene proyecto pero falta información clave
        - Explicar por qué necesitamos más contexto
        - Motivar a completar información sin presionar

        RETURNING_USER:
        - Bienvenida de vuelta, mencionar proyecto
        - Listo para ayudar con lo que necesite
        - Breve y directo

        PRINCIPIOS Y-COMBINATOR:
        - Ser directo y conciso
        - Enfocarse en EJECUTAR, no solo planear
        - Preguntar por métricas y tracción real
        - Priorizar problem-solution fit

        CAPACIDADES DE LA PLATAFORMA:
        - Conectar con Angels, Fondos y Empresas especializadas
        - Outreach inteligente en LinkedIn
        - Mentoría estilo Y-Combinator
        - Búsquedas personalizadas

        RESPONDE SOLO CON EL MENSAJE (NO JSON):
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating personalized message: {e}")
            return self._get_static_message(message_type)
    
    def _generate_suggested_actions(
        self, 
        message_type: str, 
        completeness_score: float,
        project_data
    ) -> List[str]:
        """Generar acciones sugeridas"""
        actions = []
        
        if message_type == "new_user":
            actions = [
                "Cuéntame sobre tu startup",
                "Buscar inversores especializados",
                "Necesito ayuda con mentoría",
                "Buscar empresas/servicios"
            ]
        
        elif message_type == "low_completeness":
            missing_fields = self._get_missing_fields(project_data)
            actions = [
                f"Completar información: {', '.join(missing_fields[:2])}",
                "Buscar inversores ahora",
                "Necesito mentoría",
                "Buscar servicios especializados"
            ]
        
        elif message_type in ["returning_user", "new_project"]:
            actions = [
                "Buscar inversores",
                "Buscar empresas/servicios",
                "Mentoría Y-Combinator",
                "Actualizar información del proyecto"
            ]
        
        return actions
    
    def _get_missing_fields(self, project_data) -> List[str]:
        """Obtener campos faltantes"""
        missing = []
        
        if not project_data.categories:
            missing.append("sector/industria")
        
        if not project_data.stage:
            missing.append("etapa del proyecto")
        
        if not project_data.metrics or not any([
            project_data.metrics.arr, 
            project_data.metrics.mrr, 
            project_data.metrics.users
        ]):
            missing.append("métricas (ARR/MRR/usuarios)")
        
        if not project_data.team_info:
            missing.append("información del equipo")
        
        if not project_data.problem_solved:
            missing.append("problema que resuelves")
        
        return missing
    
    def _get_static_message(self, message_type: str) -> str:
        """Mensajes estáticos de fallback"""
        
        messages = {
            "new_user": """¡Bienvenido/a a 0Bullshit! 🚀

Conecta. Financia. Crece.

Somos tu plataforma para conectar con Angels, Fondos y Empresas especializadas. Hacemos outreach inteligente en LinkedIn y te damos mentoría estilo Y-Combinator.

Para ayudarte mejor, cuéntame brevemente sobre tu empresa:
- ¿Qué problema resuelves y para quién?
- ¿En qué etapa estás? (idea, MVP, seed, etc.)
- ¿Qué sector/industria?

¡Vamos a empezar esta aventura! 💪""",

            "new_project": """¡Perfecto! Nuevo proyecto en marcha. 

Cuéntame sobre esta startup:
- ¿Qué hace exactamente?
- ¿En qué etapa se encuentra?
- ¿Necesitas inversores, servicios o mentoría?""",

            "low_completeness": f"""¡Hola de nuevo! 👋

Veo que tenemos información básica de tu proyecto, pero para darte las mejores recomendaciones necesito conocer un poco más:

- Sector/industria específico
- Etapa actual del proyecto
- Algunas métricas si las tienes

¿Qué necesitas hoy?""",

            "returning_user": """¡Bienvenido/a de vuelta! 🎯

¿En qué puedo ayudarte hoy? Buscar inversores, empresas especializadas, o necesitas mentoría sobre algún tema específico?"""
        }
        
        return messages.get(message_type, messages["returning_user"])
    
    def _get_fallback_welcome_message(self, is_first_time: bool) -> WelcomeMessage:
        """Mensaje de fallback en caso de error"""
        
        if is_first_time:
            message = self._get_static_message("new_user")
            message_type = "new_user"
            actions = [
                "Cuéntame sobre tu startup",
                "Buscar inversores",
                "Necesito mentoría",
                "Buscar servicios"
            ]
        else:
            message = self._get_static_message("returning_user")
            message_type = "returning_user"
            actions = [
                "Buscar inversores",
                "Buscar empresas",
                "Mentoría",
                "Actualizar proyecto"
            ]
        
        return WelcomeMessage(
            message=message,
            message_type=message_type,
            suggested_actions=actions
        )

# Instancia global
welcome_system = WelcomeSystem()
