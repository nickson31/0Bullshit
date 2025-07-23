import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import google.generativeai as genai
from fastapi import HTTPException

from config.settings import GEMINI_API_KEY
from database.database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

class WelcomeSystem:
    def __init__(self):
        self.db = Database()
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        # Onboarding stages
        self.onboarding_stages = {
            "welcome": {
                "order": 1,
                "title": "Bienvenida",
                "description": "Presentación inicial del sistema",
                "required": True
            },
            "project_creation": {
                "order": 2,
                "title": "Crear Proyecto",
                "description": "Creación del primer proyecto",
                "required": True
            },
            "project_details": {
                "order": 3,
                "title": "Detalles del Proyecto",
                "description": "Completar información básica",
                "required": True
            },
            "first_search": {
                "order": 4,
                "title": "Primera Búsqueda",
                "description": "Realizar primera búsqueda de inversores",
                "required": False
            }
        }
        
        # Project completeness categories
        self.completeness_categories = {
            "basic_info": {
                "weight": 25,
                "fields": ["name", "description", "stage", "category"],
                "name": "Información Básica"
            },
            "business_model": {
                "weight": 25,
                "fields": ["business_model", "revenue_model", "target_market"],
                "name": "Modelo de Negocio"
            },
            "financials": {
                "weight": 25,
                "fields": ["funding_amount", "current_revenue", "projected_revenue"],
                "name": "Información Financiera"
            },
            "team_traction": {
                "weight": 25,
                "fields": ["team_size", "key_metrics", "achievements"],
                "name": "Equipo y Tracción"
            }
        }

    async def start_onboarding(self, user_id: UUID, user_data: Dict) -> Dict:
        """
        Inicia el proceso de onboarding para un nuevo usuario
        """
        try:
            # Verificar si ya completó onboarding
            existing_progress = await self._get_onboarding_progress(user_id)
            if existing_progress and existing_progress.get("completed", False):
                return await self.generate_returning_user_welcome(user_id, user_data)
            
            # Crear registro de onboarding
            onboarding_data = {
                "user_id": str(user_id),
                "current_stage": "welcome",
                "completed_stages": [],
                "completed": False,
                "started_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            self.db.supabase.table("user_onboarding")\
                .upsert(onboarding_data)\
                .execute()
            
            # Generar mensaje de bienvenida personalizado
            welcome_message = await self._generate_welcome_message(user_data)
            
            return {
                "type": "onboarding_welcome",
                "stage": "welcome",
                "message": welcome_message,
                "next_actions": [
                    {
                        "action": "create_project",
                        "title": "Crear mi primer proyecto",
                        "description": "Cuéntame sobre tu startup"
                    }
                ],
                "progress": {
                    "current_stage": 1,
                    "total_stages": len(self.onboarding_stages),
                    "completed": False
                }
            }
            
        except Exception as e:
            logger.error(f"Error starting onboarding: {e}")
            raise HTTPException(status_code=500, detail="Error initializing onboarding")

    async def continue_onboarding(self, user_id: UUID, stage: str, user_input: Dict) -> Dict:
        """
        Continúa el proceso de onboarding basado en la etapa actual
        """
        try:
            progress = await self._get_onboarding_progress(user_id)
            if not progress:
                return await self.start_onboarding(user_id, user_input)
            
            if stage == "project_creation":
                return await self._handle_project_creation(user_id, user_input, progress)
            elif stage == "project_details":
                return await self._handle_project_details(user_id, user_input, progress)
            elif stage == "first_search":
                return await self._handle_first_search(user_id, user_input, progress)
            else:
                return await self._generate_stage_response(user_id, stage, user_input)
                
        except Exception as e:
            logger.error(f"Error continuing onboarding: {e}")
            raise HTTPException(status_code=500, detail="Error in onboarding process")

    async def _handle_project_creation(self, user_id: UUID, user_input: Dict, progress: Dict) -> Dict:
        """
        Maneja la creación del primer proyecto durante onboarding
        """
        try:
            # Extraer información del proyecto con Gemini
            project_info = await self._extract_project_info(user_input.get("message", ""))
            
            # Crear proyecto inicial
            project_id = uuid4()
            project_data = {
                "id": str(project_id),
                "user_id": str(user_id),
                "name": project_info.get("name", "Mi Startup"),
                "description": project_info.get("description", ""),
                "stage": project_info.get("stage", "idea"),
                "category": project_info.get("category", "other"),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            self.db.supabase.table("projects")\
                .insert(project_data)\
                .execute()
            
            # Actualizar progreso de onboarding
            await self._update_onboarding_progress(user_id, "project_details", ["welcome", "project_creation"])
            
            # Calcular completeness inicial
            completeness = await self._calculate_project_completeness(project_id)
            
            # Generar respuesta de continuación
            response_message = await self._generate_project_creation_response(project_info, completeness)
            
            return {
                "type": "onboarding_project_created",
                "stage": "project_details",
                "message": response_message,
                "project_id": str(project_id),
                "completeness": completeness,
                "next_actions": [
                    {
                        "action": "add_details",
                        "title": "Agregar más detalles",
                        "description": "Cuéntame más sobre tu modelo de negocio"
                    }
                ],
                "progress": {
                    "current_stage": 3,
                    "total_stages": len(self.onboarding_stages),
                    "completed": False
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling project creation: {e}")
            return {"error": "No pude crear tu proyecto. Inténtalo de nuevo."}

    async def _handle_project_details(self, user_id: UUID, user_input: Dict, progress: Dict) -> Dict:
        """
        Maneja la recopilación de detalles del proyecto
        """
        try:
            # Obtener proyecto actual
            project = await self._get_user_current_project(user_id)
            if not project:
                return {"error": "No se encontró proyecto activo"}
            
            # Extraer detalles adicionales con Gemini
            project_updates = await self._extract_project_details(user_input.get("message", ""))
            
            # Actualizar proyecto
            if project_updates:
                self.db.supabase.table("projects")\
                    .update(project_updates)\
                    .eq("id", project["id"])\
                    .execute()
            
            # Recalcular completeness
            completeness = await self._calculate_project_completeness(project["id"])
            
            # Determinar siguiente paso
            if completeness["total_percentage"] >= 50:
                # Listo para primera búsqueda
                await self._update_onboarding_progress(user_id, "first_search", ["welcome", "project_creation", "project_details"])
                
                response_message = await self._generate_search_ready_message(project, completeness)
                
                return {
                    "type": "onboarding_search_ready",
                    "stage": "first_search",
                    "message": response_message,
                    "completeness": completeness,
                    "next_actions": [
                        {
                            "action": "search_investors",
                            "title": "Buscar inversores",
                            "description": "Encuentra inversores perfectos para tu startup"
                        }
                    ]
                }
            else:
                # Necesita más información
                response_message = await self._generate_more_details_needed_message(completeness)
                
                return {
                    "type": "onboarding_need_details",
                    "stage": "project_details",
                    "message": response_message,
                    "completeness": completeness,
                    "missing_categories": [
                        cat for cat, data in completeness["categories"].items()
                        if data["percentage"] < 80
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error handling project details: {e}")
            return {"error": "Error procesando detalles del proyecto"}

    async def _extract_project_info(self, user_message: str) -> Dict:
        """
        Extrae información del proyecto usando Gemini
        """
        try:
            prompt = f"""
            Extrae información del proyecto/startup de este mensaje del usuario.

            MENSAJE DEL USUARIO:
            {user_message}

            Extrae y categoriza la información disponible. Si algo no está claro, usa "unknown".

            CATEGORÍAS DE STARTUP:
            - fintech, healthtech, edtech, proptech, retail, saas, marketplace, social, gaming, ai, other

            ETAPAS:
            - idea, prototype, mvp, early_revenue, growth, scale

            Responde en JSON:
            {{
                "name": "nombre del proyecto",
                "description": "descripción breve",
                "category": "categoría",
                "stage": "etapa",
                "business_model": "modelo de negocio si mencionado",
                "target_market": "mercado objetivo si mencionado",
                "problem_solving": "problema que resuelve"
            }}
            """

            response = self.model.generate_content(prompt)
            
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                return {"name": "Mi Startup", "description": user_message[:200], "category": "other", "stage": "idea"}
                
        except Exception as e:
            logger.error(f"Error extracting project info: {e}")
            return {"name": "Mi Startup", "category": "other", "stage": "idea"}

    async def _calculate_project_completeness(self, project_id: str) -> Dict:
        """
        Calcula el score de completeness del proyecto
        """
        try:
            # Obtener datos del proyecto
            project_query = self.db.supabase.table("projects")\
                .select("*")\
                .eq("id", project_id)\
                .execute()
            
            if not project_query.data:
                return {"total_percentage": 0, "categories": {}}
            
            project = project_query.data[0]
            
            # Calcular completeness por categoría
            categories_completeness = {}
            total_weighted_score = 0
            
            for category, config in self.completeness_categories.items():
                filled_fields = 0
                total_fields = len(config["fields"])
                
                for field in config["fields"]:
                    if project.get(field) and project[field] not in [None, "", "unknown"]:
                        filled_fields += 1
                
                category_percentage = (filled_fields / total_fields) * 100
                weighted_score = (category_percentage / 100) * config["weight"]
                total_weighted_score += weighted_score
                
                categories_completeness[category] = {
                    "percentage": category_percentage,
                    "filled_fields": filled_fields,
                    "total_fields": total_fields,
                    "weight": config["weight"],
                    "name": config["name"]
                }
            
            return {
                "total_percentage": total_weighted_score,
                "categories": categories_completeness,
                "project_id": project_id
            }
            
        except Exception as e:
            logger.error(f"Error calculating completeness: {e}")
            return {"total_percentage": 0, "categories": {}}

    async def generate_returning_user_welcome(self, user_id: UUID, user_data: Dict) -> Dict:
        """
        Genera mensaje de bienvenida para usuarios que regresan
        """
        try:
            # Obtener información del usuario
            user_stats = await self._get_user_stats(user_id)
            
            # Generar mensaje personalizado
            welcome_message = await self._generate_returning_welcome_message(user_data, user_stats)
            
            return {
                "type": "returning_user_welcome",
                "message": welcome_message,
                "user_stats": user_stats,
                "quick_actions": [
                    {
                        "action": "search_investors",
                        "title": "Buscar inversores",
                        "description": "Encuentra nuevos inversores"
                    },
                    {
                        "action": "check_campaigns",
                        "title": "Ver campañas",
                        "description": "Revisar campañas activas"
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating returning user welcome: {e}")
            return {"error": "Error generando mensaje de bienvenida"}

    async def _get_onboarding_progress(self, user_id: UUID) -> Optional[Dict]:
        """
        Obtiene el progreso actual de onboarding del usuario
        """
        try:
            query = self.db.supabase.table("user_onboarding")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .execute()
            
            return query.data[0] if query.data else None
            
        except Exception as e:
            logger.error(f"Error getting onboarding progress: {e}")
            return None

    async def _update_onboarding_progress(self, user_id: UUID, current_stage: str, completed_stages: List[str]):
        """
        Actualiza el progreso de onboarding
        """
        try:
            update_data = {
                "current_stage": current_stage,
                "completed_stages": completed_stages,
                "completed": current_stage == "completed",
                "updated_at": datetime.now().isoformat()
            }
            
            if current_stage == "completed":
                update_data["completed_at"] = datetime.now().isoformat()
            
            self.db.supabase.table("user_onboarding")\
                .update(update_data)\
                .eq("user_id", str(user_id))\
                .execute()
                
        except Exception as e:
            logger.error(f"Error updating onboarding progress: {e}")

    async def _get_user_current_project(self, user_id: UUID) -> Optional[Dict]:
        """
        Obtiene el proyecto actual del usuario
        """
        try:
            query = self.db.supabase.table("projects")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            return query.data[0] if query.data else None
            
        except Exception as e:
            logger.error(f"Error getting user current project: {e}")
            return None

    async def _get_user_stats(self, user_id: UUID) -> Dict:
        """
        Obtiene estadísticas del usuario para mensajes personalizados
        """
        try:
            stats = {}
            
            # Proyectos
            projects_query = self.db.supabase.table("projects")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .execute()
            stats["projects_count"] = len(projects_query.data) if projects_query.data else 0
            
            # Búsquedas
            searches_query = self.db.supabase.table("search_results")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .execute()
            stats["searches_count"] = len(searches_query.data) if searches_query.data else 0
            
            # Conversaciones
            conversations_query = self.db.supabase.table("conversations")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .execute()
            stats["conversations_count"] = len(conversations_query.data) if conversations_query.data else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}

    async def _generate_welcome_message(self, user_data: Dict) -> str:
        """
        Genera mensaje de bienvenida personalizado
        """
        try:
            prompt = f"""
            Genera un mensaje de bienvenida cálido y profesional para un nuevo usuario de 0Bullshit.

            INFORMACIÓN DEL USUARIO:
            - Nombre: {user_data.get('name', 'Usuario')}
            - Email: {user_data.get('email', '')}

            SOBRE 0BULLSHIT:
            - Plataforma AI para encontrar inversores perfectos para startups
            - Sistema de chat inteligente como ChatGPT pero especializado
            - Automatización de outreach por LinkedIn
            - Base de datos de +10,000 inversores

            DIRECTRICES:
            1. Saludo personal usando su nombre
            2. Explicar brevemente qué es 0Bullshit (2-3 líneas)
            3. Mencionar que vamos a crear su primer proyecto
            4. Tono profesional pero amigable
            5. Usar emojis apropiados
            6. Máximo 4-5 líneas

            EJEMPLO DE TONO:
            "¡Hola [Nombre]! 👋 Bienvenido a 0Bullshit, tu asistente AI especializado en conseguir inversión para startups..."

            Genera SOLO el mensaje, sin explicaciones adicionales.
            """

            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating welcome message: {e}")
            return f"¡Hola {user_data.get('name', 'Usuario')}! 👋 Bienvenido a 0Bullshit. Vamos a encontrar los inversores perfectos para tu startup."


# Instancia global
welcome_system = WelcomeSystem()