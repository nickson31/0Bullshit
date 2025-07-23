import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import google.generativeai as genai
from fastapi import HTTPException

from config.settings import GEMINI_API_KEY
from database.database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

class UpsellSystem:
    def __init__(self):
        self.db = Database()
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        # Anti-saturation settings
        self.max_upsells_per_day = 3
        self.cooldown_hours = 4
        
        # Upsell triggers and thresholds
        self.upsell_triggers = {
            "search_limit_reached": {
                "target_plan": "pro",
                "message_type": "search_limitation",
                "priority": 90
            },
            "outreach_interest": {
                "target_plan": "outreach", 
                "message_type": "outreach_opportunity",
                "priority": 85
            },
            "multiple_searches": {
                "target_plan": "pro",
                "message_type": "power_user",
                "priority": 75
            },
            "high_engagement": {
                "target_plan": "outreach",
                "message_type": "engagement_boost",
                "priority": 80
            }
        }

    async def analyze_upsell_opportunity(
        self, 
        user_id: UUID, 
        conversation_context: str,
        user_data: Dict,
        current_action: str
    ) -> Optional[Dict]:
        """
        Analiza si existe una oportunidad de upsell y genera el mensaje apropiado
        """
        try:
            # Verificar anti-saturación
            if not await self._check_anti_saturation(user_id):
                return None
            
            # Obtener contexto del usuario
            user_context = await self._get_user_context(user_id, user_data)
            
            # Analizar oportunidad con Gemini
            upsell_analysis = await self._analyze_with_gemini(
                conversation_context, 
                user_context, 
                current_action
            )
            
            if not upsell_analysis.get("should_upsell", False):
                return None
                
            # Generar mensaje personalizado
            upsell_message = await self._generate_upsell_message(
                upsell_analysis, 
                user_context
            )
            
            # Registrar intento de upsell
            await self._record_upsell_attempt(user_id, upsell_analysis)
            
            return {
                "should_upsell": True,
                "target_plan": upsell_analysis["target_plan"],
                "confidence": upsell_analysis["confidence"],
                "message": upsell_message,
                "trigger": upsell_analysis["trigger"],
                "priority": upsell_analysis["priority"]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing upsell opportunity: {e}")
            return None

    async def _check_anti_saturation(self, user_id: UUID) -> bool:
        """
        Verifica que no se haya superado el límite de upsells diarios
        """
        try:
            today = datetime.now().date()
            
            query = self.db.supabase.table("upsell_attempts")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .gte("created_at", today.isoformat())\
                .execute()
            
            attempts_today = len(query.data) if query.data else 0
            
            if attempts_today >= self.max_upsells_per_day:
                return False
                
            # Verificar cooldown
            if attempts_today > 0:
                last_attempt = max(query.data, key=lambda x: x["created_at"])
                last_attempt_time = datetime.fromisoformat(last_attempt["created_at"])
                
                if datetime.now() - last_attempt_time < timedelta(hours=self.cooldown_hours):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking anti-saturation: {e}")
            return False

    async def _get_user_context(self, user_id: UUID, user_data: Dict) -> Dict:
        """
        Obtiene el contexto completo del usuario para personalización
        """
        try:
            # Datos del usuario
            context = {
                "plan": user_data.get("plan", "free"),
                "credits": user_data.get("credits", 0),
                "daily_credits_used": user_data.get("daily_credits_used", 0),
                "account_age_days": (
                    datetime.now() - datetime.fromisoformat(user_data["created_at"])
                ).days,
            }
            
            # Obtener proyectos
            projects_query = self.db.supabase.table("projects")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .execute()
            
            context["projects_count"] = len(projects_query.data) if projects_query.data else 0
            
            # Obtener historial de búsquedas
            searches_query = self.db.supabase.table("search_results")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .gte("created_at", (datetime.now() - timedelta(days=30)).isoformat())\
                .execute()
            
            context["searches_30_days"] = len(searches_query.data) if searches_query.data else 0
            
            # Obtener actividad de chat
            chat_query = self.db.supabase.table("conversations")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .gte("created_at", (datetime.now() - timedelta(days=7)).isoformat())\
                .execute()
            
            context["chat_sessions_7_days"] = len(chat_query.data) if chat_query.data else 0
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {}

    async def _analyze_with_gemini(
        self, 
        conversation_context: str, 
        user_context: Dict, 
        current_action: str
    ) -> Dict:
        """
        Utiliza Gemini para analizar la oportunidad de upsell
        """
        try:
            prompt = f"""
            Analiza esta conversación y contexto de usuario para determinar si existe una oportunidad de upsell contextual y natural.

            CONVERSACIÓN ACTUAL:
            {conversation_context}

            CONTEXTO DEL USUARIO:
            - Plan actual: {user_context.get('plan', 'free')}
            - Créditos restantes: {user_context.get('credits', 0)}
            - Créditos usados hoy: {user_context.get('daily_credits_used', 0)}
            - Días como usuario: {user_context.get('account_age_days', 0)}
            - Proyectos creados: {user_context.get('projects_count', 0)}
            - Búsquedas últimos 30 días: {user_context.get('searches_30_days', 0)}
            - Sesiones chat última semana: {user_context.get('chat_sessions_7_days', 0)}

            ACCIÓN ACTUAL: {current_action}

            PLANES DISPONIBLES:
            - FREE: 200 créditos/mes, búsquedas limitadas
            - PRO ($19/mes): 1000 créditos/mes, búsquedas ilimitadas, análisis avanzado
            - OUTREACH ($49/mes): Todo lo anterior + automatización LinkedIn, campañas

            CRITERIOS PARA UPSELL:
            1. El usuario debe mostrar interés genuino o necesidad
            2. Debe ser contextual y natural, NO agresivo
            3. Solo si realmente beneficia al usuario
            4. Máximo 1 upsell por conversación

            TRIGGERS PRINCIPALES:
            - Usuario se queda sin créditos o cerca del límite
            - Muestra interés en contactar inversores (→ OUTREACH)
            - Hace múltiples búsquedas (→ PRO)
            - Pregunta por funcionalidades premium

            Responde en JSON con:
            {{
                "should_upsell": true/false,
                "confidence": 0-100,
                "target_plan": "pro/outreach",
                "trigger": "descripción del trigger",
                "reasoning": "por qué recomiendas este upsell",
                "priority": 0-100,
                "contextual_hook": "gancho contextual específico de la conversación"
            }}

            SI NO HAY OPORTUNIDAD CLARA Y NATURAL, responde should_upsell: false.
            """

            response = self.model.generate_content(prompt)
            
            try:
                result = json.loads(response.text)
                return result
            except json.JSONDecodeError:
                # Fallback parsing
                return {"should_upsell": False, "confidence": 0}
                
        except Exception as e:
            logger.error(f"Error analyzing with Gemini: {e}")
            return {"should_upsell": False, "confidence": 0}

    async def _generate_upsell_message(self, analysis: Dict, user_context: Dict) -> str:
        """
        Genera un mensaje de upsell personalizado y contextual
        """
        try:
            prompt = f"""
            Genera un mensaje de upsell personalizado, contextual y natural en español.

            ANÁLISIS:
            {json.dumps(analysis, indent=2)}

            CONTEXTO DEL USUARIO:
            {json.dumps(user_context, indent=2)}

            DIRECTRICES:
            1. Debe ser conversacional y natural, como si fuera parte de la respuesta del asistente
            2. Enfocarse en el BENEFICIO específico para el usuario
            3. Usar el gancho contextual del análisis
            4. Incluir call-to-action claro pero no agresivo
            5. Máximo 3-4 líneas
            6. Usar emojis apropiados

            EJEMPLOS DE TONO:
            - "Por cierto, he notado que estás muy activo buscando inversores. Con el plan Outreach podrías automatizar todo el proceso de contacto por LinkedIn 🚀"
            - "Veo que has hecho varias búsquedas. Con el plan Pro tendrías créditos ilimitados y análisis más profundos 💡"

            GENERA SOLO EL MENSAJE, sin explicaciones adicionales.
            """

            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating upsell message: {e}")
            return ""

    async def _record_upsell_attempt(self, user_id: UUID, analysis: Dict):
        """
        Registra el intento de upsell en la base de datos
        """
        try:
            upsell_data = {
                "user_id": str(user_id),
                "target_plan": analysis.get("target_plan"),
                "trigger": analysis.get("trigger"),
                "confidence": analysis.get("confidence"),
                "priority": analysis.get("priority"),
                "created_at": datetime.now().isoformat()
            }
            
            self.db.supabase.table("upsell_attempts")\
                .insert(upsell_data)\
                .execute()
                
        except Exception as e:
            logger.error(f"Error recording upsell attempt: {e}")

    async def get_upsell_analytics(self, user_id: UUID) -> Dict:
        """
        Obtiene analytics de upselling para el usuario
        """
        try:
            query = self.db.supabase.table("upsell_attempts")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .execute()
            
            attempts = query.data if query.data else []
            
            return {
                "total_attempts": len(attempts),
                "attempts_last_30_days": len([
                    a for a in attempts 
                    if datetime.fromisoformat(a["created_at"]) > datetime.now() - timedelta(days=30)
                ]),
                "most_common_trigger": max(
                    [a["trigger"] for a in attempts], 
                    key=[a["trigger"] for a in attempts].count
                ) if attempts else None,
                "average_confidence": sum(a["confidence"] for a in attempts) / len(attempts) if attempts else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting upsell analytics: {e}")
            return {}


# Instancia global
upsell_system = UpsellSystem()