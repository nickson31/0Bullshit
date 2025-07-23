# campaigns/message_generator.py
import os
import json
import google.generativeai as genai
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from uuid import UUID

import asyncio
from fastapi import HTTPException

from config.settings import GEMINI_API_KEY
from database.database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

class MessageGenerator:
    def __init__(self):
        self.db = Database()
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        # Message templates and strategies
        self.message_strategies = {
            "connection_request": {
                "max_length": 300,
                "tone": "professional_friendly",
                "goal": "get_connection_accepted",
                "personalization_level": "high"
            },
            "first_message": {
                "max_length": 500,
                "tone": "professional_warm",
                "goal": "start_conversation",
                "personalization_level": "very_high"
            },
            "follow_up": {
                "max_length": 400,
                "tone": "polite_persistent",
                "goal": "maintain_engagement",
                "personalization_level": "medium"
            },
            "pitch_message": {
                "max_length": 600,
                "tone": "confident_professional",
                "goal": "present_opportunity",
                "personalization_level": "very_high"
            }
        }
        
        # Anti-spam and personalization rules
        self.personalization_factors = [
            "investor_name",
            "investor_company", 
            "recent_investments",
            "investment_focus",
            "shared_connections",
            "geographic_relevance",
            "timing_context"
        ]

    async def generate_personalized_message(
        self,
        user_id: UUID,
        project_data: Dict,
        investor_data: Dict,
        message_type: str,
        campaign_context: Optional[Dict] = None
    ) -> Dict:
        """
        Genera un mensaje personalizado para un inversor específico
        """
        try:
            # Validar entrada
            if message_type not in self.message_strategies:
                raise ValueError(f"Invalid message type: {message_type}")
            
            # Obtener contexto del usuario y proyecto
            user_context = await self._get_user_context(user_id)
            project_context = await self._enrich_project_context(project_data)
            
            # Analizar perfil del inversor
            investor_analysis = await self._analyze_investor_profile(investor_data)
            
            # Generar mensaje con Gemini
            message = await self._generate_with_gemini(
                user_context,
                project_context,
                investor_analysis,
                message_type,
                campaign_context
            )
            
            # Aplicar validaciones de calidad
            quality_check = await self._validate_message_quality(message, message_type)
            
            if not quality_check["is_valid"]:
                # Regenerar si no pasa validaciones
                message = await self._regenerate_message(
                    user_context, project_context, investor_analysis, 
                    message_type, quality_check["issues"]
                )
            
            # Calcular score de personalización
            personalization_score = await self._calculate_personalization_score(
                message, investor_data, project_data
            )
            
            # Registrar mensaje generado
            await self._log_generated_message(user_id, investor_data["id"], message_type, message, personalization_score)
            
            return {
                "message": message,
                "message_type": message_type,
                "personalization_score": personalization_score,
                "investor_id": investor_data["id"],
                "investor_name": investor_data.get("name", ""),
                "generated_at": datetime.now().isoformat(),
                "quality_check": quality_check,
                "strategy_used": self.message_strategies[message_type]
            }
            
        except Exception as e:
            logger.error(f"Error generating personalized message: {e}")
            raise HTTPException(status_code=500, detail="Error generating message")

    async def generate_campaign_sequence(
        self,
        user_id: UUID,
        project_data: Dict,
        investor_list: List[Dict],
        sequence_type: str = "standard"
    ) -> Dict:
        """
        Genera secuencia completa de mensajes para una campaña
        """
        try:
            sequence_messages = []
            
            # Definir secuencia según tipo
            if sequence_type == "standard":
                message_sequence = [
                    {"type": "connection_request", "delay_days": 0},
                    {"type": "first_message", "delay_days": 2},
                    {"type": "follow_up", "delay_days": 7},
                    {"type": "pitch_message", "delay_days": 14}
                ]
            elif sequence_type == "aggressive":
                message_sequence = [
                    {"type": "connection_request", "delay_days": 0},
                    {"type": "first_message", "delay_days": 1},
                    {"type": "follow_up", "delay_days": 4},
                    {"type": "pitch_message", "delay_days": 8}
                ]
            else:  # conservative
                message_sequence = [
                    {"type": "connection_request", "delay_days": 0},
                    {"type": "first_message", "delay_days": 3},
                    {"type": "follow_up", "delay_days": 10},
                    {"type": "pitch_message", "delay_days": 21}
                ]
            
            # Generar mensajes para cada inversor
            for investor in investor_list:
                investor_messages = []
                
                for step in message_sequence:
                    message_result = await self.generate_personalized_message(
                        user_id=user_id,
                        project_data=project_data,
                        investor_data=investor,
                        message_type=step["type"],
                        campaign_context={
                            "sequence_type": sequence_type,
                            "step_number": len(investor_messages) + 1,
                            "total_steps": len(message_sequence),
                            "delay_days": step["delay_days"]
                        }
                    )
                    
                    investor_messages.append({
                        **message_result,
                        "send_delay_days": step["delay_days"],
                        "sequence_order": len(investor_messages) + 1
                    })
                
                sequence_messages.append({
                    "investor_id": investor["id"],
                    "investor_name": investor.get("name", ""),
                    "messages": investor_messages,
                    "total_personalization_score": sum(
                        msg["personalization_score"] for msg in investor_messages
                    ) / len(investor_messages)
                })
            
            return {
                "sequence_type": sequence_type,
                "total_investors": len(investor_list),
                "messages_per_investor": len(message_sequence),
                "total_messages": len(investor_list) * len(message_sequence),
                "sequences": sequence_messages,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating campaign sequence: {e}")
            raise HTTPException(status_code=500, detail="Error generating campaign sequence")

    async def _generate_with_gemini(
        self,
        user_context: Dict,
        project_context: Dict,
        investor_analysis: Dict,
        message_type: str,
        campaign_context: Optional[Dict]
    ) -> str:
        """
        Utiliza Gemini para generar el mensaje personalizado
        """
        try:
            strategy = self.message_strategies[message_type]
            
            prompt = f"""
            Genera un mensaje de LinkedIn {message_type} altamente personalizado para contactar a un inversor.

            CONTEXTO DEL USUARIO:
            {json.dumps(user_context, indent=2)}

            CONTEXTO DEL PROYECTO:
            {json.dumps(project_context, indent=2)}

            ANÁLISIS DEL INVERSOR:
            {json.dumps(investor_analysis, indent=2)}

            ESTRATEGIA DEL MENSAJE:
            - Tipo: {message_type}
            - Tono: {strategy['tone']}
            - Objetivo: {strategy['goal']}
            - Límite de caracteres: {strategy['max_length']}
            - Nivel de personalización: {strategy['personalization_level']}

            CONTEXTO DE CAMPAÑA:
            {json.dumps(campaign_context or {}, indent=2)}

            DIRECTRICES CRÍTICAS:
            1. PERSONALIZACIÓN MÁXIMA: Menciona específicamente por qué este inversor es relevante
            2. VALOR CLARO: Explica qué hace único al proyecto en relación al perfil del inversor
            3. CALL TO ACTION: Incluye una solicitud específica y clara
            4. ANTI-SPAM: Suena natural y genuino, no como mensaje masivo
            5. PROFESSIONAL: Tono profesional pero cálido
            6. BREVEDAD: Respeta el límite de caracteres
            7. NO USAR PLANTILLAS: Cada mensaje debe ser único

            ESTRUCTURA SEGÚN TIPO:
            
            CONNECTION_REQUEST:
            - Saludo personalizado
            - Mención de conexión específica (inversión, sector, etc.)
            - Breve valor proposition
            - Solicitud de conexión

            FIRST_MESSAGE:
            - Agradecimiento por aceptar conexión
            - Contexto personalizado del por qué lo contactas
            - Presentación breve del proyecto con hook específico
            - Pregunta o solicitud de feedback

            FOLLOW_UP:
            - Referencia al mensaje anterior
            - Nuevo ángulo de valor o información adicional
            - Respeto por su tiempo
            - Call to action suave

            PITCH_MESSAGE:
            - Presentación completa del proyecto
            - Match específico con el perfil de inversión
            - Métricas y tracción relevantes
            - Solicitud clara de reunión/call

            EVITAR:
            - Frases genéricas como "Espero que te encuentres bien"
            - Súper ventas agresivas
            - Información irrelevante para este inversor
            - Mensajes que suenan a plantilla

            GENERA SOLO EL MENSAJE, sin explicaciones adicionales.
            El mensaje debe estar en español y ser perfecto para enviar directamente.
            """

            response = self.model.generate_content(prompt)
            message = response.text.strip()
            
            # Verificar límite de caracteres
            if len(message) > strategy['max_length']:
                message = await self._trim_message(message, strategy['max_length'])
            
            return message
            
        except Exception as e:
            logger.error(f"Error generating with Gemini: {e}")
            return self._get_fallback_message(message_type, investor_analysis)

    async def _analyze_investor_profile(self, investor_data: Dict) -> Dict:
        """
        Analiza el perfil del inversor para personalización
        """
        try:
            prompt = f"""
            Analiza este perfil de inversor para identificar puntos clave de personalización.

            DATOS DEL INVERSOR:
            {json.dumps(investor_data, indent=2)}

            Identifica y extrae:
            1. Especialización principal de inversión
            2. Etapa preferida de inversión
            3. Sectores de interés
            4. Investments recientes relevantes
            5. Background profesional
            6. Posibles puntos de conexión
            7. Estilo de comunicación probable
            8. Factores diferenciadores

            Responde en JSON:
            {{
                "investment_focus": "área principal de especialización",
                "preferred_stage": "etapa preferida",
                "key_sectors": ["sector1", "sector2"],
                "recent_investments": ["empresa1", "empresa2"],
                "background": "resumen de background",
                "communication_style": "estilo probable",
                "personalization_hooks": ["hook1", "hook2", "hook3"],
                "relevance_factors": ["factor1", "factor2"]
            }}
            """

            response = self.model.generate_content(prompt)
            
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                return self._create_basic_investor_analysis(investor_data)
                
        except Exception as e:
            logger.error(f"Error analyzing investor profile: {e}")
            return self._create_basic_investor_analysis(investor_data)

    async def _validate_message_quality(self, message: str, message_type: str) -> Dict:
        """
        Valida la calidad del mensaje generado
        """
        try:
            issues = []
            
            # Validar longitud
            max_length = self.message_strategies[message_type]["max_length"]
            if len(message) > max_length:
                issues.append(f"Message too long: {len(message)} > {max_length}")
            
            # Validar que no sea genérico
            generic_phrases = [
                "espero que te encuentres bien",
                "me pongo en contacto contigo",
                "plantilla de mensaje",
                "mensaje masivo"
            ]
            
            for phrase in generic_phrases:
                if phrase.lower() in message.lower():
                    issues.append(f"Contains generic phrase: {phrase}")
            
            # Validar personalización con Gemini
            personalization_check = await self._check_personalization_with_gemini(message)
            
            if personalization_check["score"] < 70:
                issues.append(f"Low personalization score: {personalization_check['score']}")
            
            return {
                "is_valid": len(issues) == 0,
                "issues": issues,
                "personalization_score": personalization_check["score"],
                "quality_score": max(0, 100 - len(issues) * 20)
            }
            
        except Exception as e:
            logger.error(f"Error validating message quality: {e}")
            return {"is_valid": True, "issues": [], "quality_score": 75}

    async def _check_personalization_with_gemini(self, message: str) -> Dict:
        """
        Verifica el nivel de personalización del mensaje
        """
        try:
            prompt = f"""
            Analiza este mensaje de LinkedIn y califica su nivel de personalización del 0 al 100.

            MENSAJE:
            {message}

            CRITERIOS:
            - 90-100: Altamente personalizado, menciona detalles específicos del receptor
            - 70-89: Bien personalizado, algunos elementos específicos
            - 50-69: Moderadamente personalizado, algo genérico
            - 30-49: Poco personalizado, mayormente genérico
            - 0-29: Mensaje completamente genérico

            Responde en JSON:
            {{
                "score": 0-100,
                "reasoning": "explicación de la puntuación",
                "personalization_elements": ["elemento1", "elemento2"],
                "generic_elements": ["elemento1", "elemento2"]
            }}
            """

            response = self.model.generate_content(prompt)
            
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                return {"score": 75, "reasoning": "Default score", "personalization_elements": [], "generic_elements": []}
                
        except Exception as e:
            logger.error(f"Error checking personalization: {e}")
            return {"score": 75, "reasoning": "Error in analysis", "personalization_elements": [], "generic_elements": []}

    async def _get_user_context(self, user_id: UUID) -> Dict:
        """
        Obtiene contexto completo del usuario
        """
        try:
            user_query = self.db.supabase.table("users")\
                .select("*")\
                .eq("id", str(user_id))\
                .execute()
            
            return user_query.data[0] if user_query.data else {}
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {}

    async def _enrich_project_context(self, project_data: Dict) -> Dict:
        """
        Enriquece el contexto del proyecto con datos adicionales
        """
        try:
            # El project_data ya contiene la información necesaria
            # Aquí se puede agregar lógica para enriquecer con datos externos
            return {
                **project_data,
                "enriched_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error enriching project context: {e}")
            return project_data

    async def _calculate_personalization_score(self, message: str, investor_data: Dict, project_data: Dict) -> float:
        """
        Calcula el score de personalización del mensaje
        """
        try:
            score = 0.0
            
            # Verificar menciones específicas
            investor_name = investor_data.get("name", "").lower()
            investor_company = investor_data.get("company", "").lower()
            
            if investor_name and investor_name in message.lower():
                score += 20
            
            if investor_company and investor_company in message.lower():
                score += 15
            
            # Verificar referencias a sector/categoría
            project_category = project_data.get("category", "").lower()
            investor_focus = investor_data.get("investment_focus", "").lower()
            
            if project_category and project_category in message.lower():
                score += 10
            
            if investor_focus and any(focus in message.lower() for focus in investor_focus.split()):
                score += 15
            
            # Verificar longitud apropiada (no muy corto ni muy largo)
            message_length = len(message)
            if 200 <= message_length <= 500:
                score += 10
            elif 100 <= message_length < 200 or 500 < message_length <= 600:
                score += 5
            
            # Bonus por call to action específico
            if any(cta in message.lower() for cta in ["me encantaría", "te interesaría", "podríamos", "me gustaría"]):
                score += 10
            
            # Penalizar frases genéricas
            generic_penalties = [
                "espero que te encuentres bien",
                "me pongo en contacto",
                "por favor déjame saber"
            ]
            
            for penalty in generic_penalties:
                if penalty in message.lower():
                    score -= 15
            
            return min(100.0, max(0.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating personalization score: {e}")
            return 50.0

    async def _log_generated_message(
        self, 
        user_id: UUID, 
        investor_id: str, 
        message_type: str, 
        message: str, 
        personalization_score: float
    ):
        """
        Registra el mensaje generado en la base de datos
        """
        try:
            log_data = {
                "user_id": str(user_id),
                "investor_id": investor_id,
                "message_type": message_type,
                "message_content": message,
                "personalization_score": personalization_score,
                "generated_at": datetime.now().isoformat()
            }
            
            self.db.supabase.table("generated_messages")\
                .insert(log_data)\
                .execute()
                
        except Exception as e:
            logger.error(f"Error logging generated message: {e}")

    def _create_basic_investor_analysis(self, investor_data: Dict) -> Dict:
        """
        Crea análisis básico cuando Gemini falla
        """
        return {
            "investment_focus": investor_data.get("investment_focus", "general"),
            "preferred_stage": investor_data.get("stage_preference", "unknown"),
            "key_sectors": [investor_data.get("category", "general")],
            "recent_investments": [],
            "background": investor_data.get("bio", ""),
            "communication_style": "professional",
            "personalization_hooks": [investor_data.get("name", ""), investor_data.get("company", "")],
            "relevance_factors": ["investment_interest"]
        }

    def _get_fallback_message(self, message_type: str, investor_analysis: Dict) -> str:
        """
        Genera mensaje de fallback cuando Gemini falla
        """
        investor_name = investor_analysis.get("personalization_hooks", [""])[0]
        
        fallback_messages = {
            "connection_request": f"Hola {investor_name}, me interesa mucho tu experiencia en inversiones. Me encantaría conectar contigo para compartir mi proyecto.",
            "first_message": f"Gracias por aceptar mi conexión, {investor_name}. Tengo un proyecto innovador que creo podría interesarte basado en tu perfil de inversión.",
            "follow_up": f"Hola {investor_name}, espero que hayas tenido oportunidad de revisar mi mensaje anterior. Me encantaría conocer tus thoughts.",
            "pitch_message": f"Hola {investor_name}, me gustaría presentarte formalmente mi startup y cómo se alinea con tu portfolio de inversiones."
        }
        
        return fallback_messages.get(message_type, "Mensaje de prueba")


# Instancia global
message_generator = MessageGenerator()
