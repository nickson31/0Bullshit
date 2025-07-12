# campaigns/message_generator.py
import os
import json
import google.generativeai as genai
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MessagePersonalizer:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "temperature": 0.6,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 400,
            }
        )
    
    async def personalize_message(
        self, 
        template: str, 
        investor_data: Dict[str, Any], 
        startup_data: Dict[str, Any]
    ) -> str:
        """Personalizar mensaje usando IA"""
        try:
            # Preparar contexto
            context = {
                "investor": {
                    "name": investor_data.get("full_name", ""),
                    "fund": investor_data.get("fund_name", ""),
                    "specialties": investor_data.get("categories_match", []),
                    "headline": investor_data.get("headline", ""),
                    "company": investor_data.get("company_name", "")
                },
                "startup": {
                    "name": startup_data.get("name", ""),
                    "description": startup_data.get("description", ""),
                    "stage": startup_data.get("stage", ""),
                    "categories": startup_data.get("categories", []),
                    "metrics": startup_data.get("project_data", {}).get("metrics", {}),
                    "problem": startup_data.get("project_data", {}).get("problem_solved", "")
                }
            }
            
            prompt = f"""
            ACTÚA COMO UN EXPERTO EN OUTREACH B2B QUE PERSONALIZA MENSAJES PARA STARTUPS.

            TEMPLATE ORIGINAL:
            {template}

            DATOS DEL INVERSOR:
            {json.dumps(context["investor"], indent=2, ensure_ascii=False)}

            DATOS DE LA STARTUP:
            {json.dumps(context["startup"], indent=2, ensure_ascii=False)}

            INSTRUCCIONES:
            1. Personaliza el template usando los datos específicos del inversor y startup
            2. Menciona especialidades del inversor que coincidan con la startup
            3. Destaca métricas relevantes si están disponibles
            4. Mantén el tono profesional pero personal
            5. Máximo 300 caracteres para LinkedIn (límite de invitaciones)
            6. Incluye un call-to-action claro
            7. NO uses placeholders como {{name}} - reemplaza con datos reales

            PRINCIPIOS DE PERSONALIZACIÓN:
            - Si el inversor tiene experiencia en el sector de la startup, mencionarlo
            - Si hay métricas impresionantes (ARR, usuarios), incluirlas
            - Ser específico sobre por qué este inversor en particular
            - Evitar lenguaje genérico o spam

            RESPONDE SOLO CON EL MENSAJE PERSONALIZADO (NO JSON, NO EXPLICACIONES):
            """
            
            response = self.model.generate_content(prompt)
            personalized = response.text.strip()
            
            # Verificar longitud (LinkedIn límite)
            if len(personalized) > 300:
                personalized = await self._shorten_message(personalized)
            
            return personalized
            
        except Exception as e:
            logger.error(f"Error personalizing message: {e}")
            # Fallback: template básico con nombre
            return template.replace("{{name}}", investor_data.get("full_name", ""))
    
    async def _shorten_message(self, message: str) -> str:
        """Acortar mensaje manteniendo personalización"""
        try:
            prompt = f"""
            Acorta este mensaje de LinkedIn manteniendo la personalización clave:
            
            MENSAJE ORIGINAL:
            {message}
            
            REQUISITOS:
            - Máximo 280 caracteres
            - Mantener personalización más importante
            - Mantener call-to-action
            - Ser directo y conciso
            
            RESPONDE SOLO CON EL MENSAJE ACORTADO:
            """
            
            response = self.model.generate_content(prompt)
            shortened = response.text.strip()
            
            # Verificar que no exceda límite
            if len(shortened) <= 300:
                return shortened
            else:
                # Fallback manual
                return message[:280] + "..."
                
        except Exception as e:
            logger.error(f"Error shortening message: {e}")
            return message[:280] + "..."
    
    async def generate_follow_up(
        self, 
        original_message: str, 
        response_text: str, 
        investor_data: Dict[str, Any],
        startup_data: Dict[str, Any]
    ) -> str:
        """Generar follow-up inteligente basado en respuesta"""
        try:
            prompt = f"""
            GENERA UN FOLLOW-UP INTELIGENTE PARA ESTA CONVERSACIÓN DE LINKEDIN.

            MENSAJE ORIGINAL ENVIADO:
            {original_message}

            RESPUESTA RECIBIDA:
            {response_text}

            CONTEXTO:
            Inversor: {investor_data.get("full_name", "")} de {investor_data.get("fund_name", "")}
            Startup: {startup_data.get("name", "")} - {startup_data.get("description", "")}

            INSTRUCCIONES:
            1. Analiza el tono y contenido de la respuesta
            2. Responde de manera apropiada al contexto
            3. Si muestra interés, sugiere próximos pasos concretos
            4. Si es neutral, proporciona más valor/información
            5. Si es negativo, agradece y deja puerta abierta
            6. Mantén profesionalismo y concisión
            7. Máximo 500 caracteres

            RESPONDE SOLO CON EL FOLLOW-UP:
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating follow-up: {e}")
            return "Gracias por tu respuesta. ¿Te gustaría agendar una breve llamada para discutir nuestra startup?"

    async def analyze_response_sentiment(self, response_text: str) -> Dict[str, Any]:
        """Analizar sentimiento e intención de respuesta"""
        try:
            prompt = f"""
            ANALIZA EL SENTIMIENTO E INTENCIÓN DE ESTA RESPUESTA DE LINKEDIN.

            RESPUESTA:
            {response_text}

            RESPONDE EN FORMATO JSON:
            {{
                "sentiment": "positive|negative|neutral",
                "interest_level": "high|medium|low",
                "next_action": "schedule_call|send_info|follow_up_later|no_action",
                "reasoning": "breve explicación del análisis"
            }}
            """
            
            response = self.model.generate_content(prompt)
            analysis = json.loads(response.text.strip())
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing response sentiment: {e}")
            return {
                "sentiment": "neutral",
                "interest_level": "medium", 
                "next_action": "follow_up_later",
                "reasoning": "Error in analysis"
            }

# campaigns/rate_limiter.py
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class LinkedInRateLimiter:
    def __init__(self):
        # Track usage per account
        self.usage_tracker = {}
    
    async def can_send_invitation(self, account_id: str) -> bool:
        """Verificar si puede enviar invitación"""
        today = datetime.now().date()
        this_week = self._get_week_start(today)
        
        # Obtener stats del día y semana
        daily_sent = await self._get_daily_invitations(account_id, today)
        weekly_sent = await self._get_weekly_invitations(account_id, this_week)
        
        # Límites de LinkedIn (conservadores)
        DAILY_LIMIT = 80  # 80-100 por día
        WEEKLY_LIMIT = 200  # 200 por semana máximo
        
        return daily_sent < DAILY_LIMIT and weekly_sent < WEEKLY_LIMIT
    
    async def can_search_profiles(self, account_id: str) -> bool:
        """Verificar si puede hacer búsquedas de perfiles"""
        today = datetime.now().date()
        daily_searches = await self._get_daily_searches(account_id, today)
        
        SEARCH_LIMIT = 100  # ~100 perfiles por día
        return daily_searches < SEARCH_LIMIT
    
    async def record_invitation_sent(self, account_id: str):
        """Registrar invitación enviada"""
        await self._record_action(account_id, "invitation", datetime.now())
    
    async def record_search_performed(self, account_id: str):
        """Registrar búsqueda realizada"""
        await self._record_action(account_id, "search", datetime.now())
    
    async def get_next_available_slot(self, account_id: str) -> datetime:
        """Calcular próximo slot disponible"""
        if await self.can_send_invitation(account_id):
            return datetime.now()
        
        # Si no puede enviar hoy, calcular para mañana
        tomorrow = datetime.now().replace(hour=9, minute=0, second=0) + timedelta(days=1)
        return tomorrow
    
    async def _get_daily_invitations(self, account_id: str, date) -> int:
        """Obtener invitaciones enviadas hoy"""
        # Query a la base de datos
        from database.database import db
        
        result = db.supabase.table("outreach_targets").select("id").eq(
            "linkedin_account_id", account_id
        ).eq("status", "sent").gte(
            "sent_at", date.isoformat()
        ).lt(
            "sent_at", (date + timedelta(days=1)).isoformat()
        ).execute()
        
        return len(result.data)
    
    async def _get_weekly_invitations(self, account_id: str, week_start) -> int:
        """Obtener invitaciones enviadas esta semana"""
        from database.database import db
        
        week_end = week_start + timedelta(days=7)
        
        result = db.supabase.table("outreach_targets").select("id").eq(
            "linkedin_account_id", account_id
        ).eq("status", "sent").gte(
            "sent_at", week_start.isoformat()
        ).lt(
            "sent_at", week_end.isoformat()
        ).execute()
        
        return len(result.data)
    
    async def _get_daily_searches(self, account_id: str, date) -> int:
        """Obtener búsquedas realizadas hoy"""
        # Implementar tracking de búsquedas
        # Por ahora retornar 0
        return 0
    
    def _get_week_start(self, date) -> datetime:
        """Obtener inicio de semana (lunes)"""
        days_since_monday = date.weekday()
        week_start = date - timedelta(days=days_since_monday)
        return datetime.combine(week_start, datetime.min.time())
    
    async def _record_action(self, account_id: str, action_type: str, timestamp: datetime):
        """Registrar acción para tracking"""
        # Implementar logging de acciones si es necesario
        pass

# Instancias globales
message_personalizer = MessagePersonalizer()
linkedin_rate_limiter = LinkedInRateLimiter()
