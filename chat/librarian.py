import os
import json
import asyncio
import google.generativeai as genai
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from models.schemas import ProjectData, ProjectMetrics, TeamInfo, LibrarianUpdate
from database.database import db
import logging

logger = logging.getLogger(__name__)

class LibrarianBot:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "temperature": 0.2,  # Más conservador para extraer datos
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 1500,
            }
        )
        self.update_queue = asyncio.Queue()
        self.is_processing = False
    
    async def process_conversation_update(
        self, 
        project_id: UUID, 
        conversation_id: UUID, 
        user_message: str, 
        assistant_response: str,
        current_project_data: ProjectData
    ) -> None:
        """
        Procesar una nueva conversación para extraer y actualizar información
        Se ejecuta en background sin bloquear la respuesta al usuario
        """
        try:
            # Añadir a la cola de procesamiento
            await self.update_queue.put({
                "project_id": project_id,
                "conversation_id": conversation_id,
                "user_message": user_message,
                "assistant_response": assistant_response,
                "current_project_data": current_project_data,
                "timestamp": datetime.now()
            })
            
            # Si no está procesando, iniciar procesamiento
            if not self.is_processing:
                asyncio.create_task(self._process_queue())
                
        except Exception as e:
            logger.error(f"Error adding to librarian queue: {e}")
    
    async def _process_queue(self):
        """Procesar cola de actualizaciones"""
        self.is_processing = True
        
        try:
            while not self.update_queue.empty():
                try:
                    # Obtener siguiente item
                    item = await asyncio.wait_for(self.update_queue.get(), timeout=1.0)
                    
                    # Procesar actualización
                    await self._analyze_and_update_project_data(item)
                    
                    # Marcar como completado
                    self.update_queue.task_done()
                    
                    # Pequeña pausa para no sobrecargar
                    await asyncio.sleep(0.5)
                    
                except asyncio.TimeoutError:
                    break
                except Exception as e:
                    logger.error(f"Error processing librarian item: {e}")
                    continue
                    
        finally:
            self.is_processing = False
    
    async def _analyze_and_update_project_data(self, item: Dict[str, Any]) -> Optional[LibrarianUpdate]:
        """Analizar conversación y actualizar datos del proyecto"""
        try:
            project_id = item["project_id"]
            current_data = item["current_project_data"]
            user_message = item["user_message"]
            assistant_response = item["assistant_response"]
            
            # Crear prompt para análisis
            prompt = self._create_analysis_prompt(
                user_message, 
                assistant_response, 
                current_data
            )
            
            # Obtener análisis de Gemini
            response = self.model.generate_content(prompt)
            analysis = self._parse_analysis_response(response.text)
            
            # Si hay actualizaciones, aplicarlas
            if analysis and analysis.get("has_updates", False):
                updated_data = self._merge_project_data(current_data, analysis["updates"])
                
                # Guardar en base de datos
                success = await db.update_project_data(
                    project_id, 
                    item.get("user_id"),  # Necesitaríamos pasarlo en el item
                    updated_data
                )
                
                if success:
                    logger.info(f"Librarian updated project {project_id}")
                    
                    return LibrarianUpdate(
                        project_id=project_id,
                        conversation_id=item["conversation_id"],
                        updates_made=analysis["updates"],
                        confidence_score=analysis.get("confidence_score", 0.8),
                        reasoning=analysis.get("reasoning", "")
                    )
                
        except Exception as e:
            logger.error(f"Error in librarian analysis: {e}")
            return None
    
    def _create_analysis_prompt(
        self, 
        user_message: str, 
        assistant_response: str, 
        current_data: ProjectData
    ) -> str:
        """Crear prompt para analizar la conversación"""
        
        current_data_dict = current_data.dict() if current_data else {}
        
        return f"""
        ACTÚA COMO UN BIBLIOTECARIO EXPERTO QUE EXTRAE INFORMACIÓN ESTRUCTURADA DE CONVERSACIONES.

        CONVERSACIÓN A ANALIZAR:
        Usuario: "{user_message}"
        Asistente: "{assistant_response}"

        DATOS ACTUALES DEL PROYECTO:
        {json.dumps(current_data_dict, indent=2, ensure_ascii=False)}

        INSTRUCCIONES:
        1. Analiza si la conversación contiene nueva información sobre el proyecto
        2. Extrae solo información EXPLÍCITA y CONFIABLE (no supongas)
        3. Mantén datos existentes si no hay información contradictoria
        4. Prioriza métricas específicas, información del equipo, y detalles del producto

        CAMPOS A BUSCAR:
        - categories: [lista de sectores/industrias mencionados]
        - stage: idea, mvp, seed, series-a, series-b, growth, etc.
        - metrics: ARR, MRR, usuarios, revenue, growth_rate
        - team_info: tamaño del equipo, roles, experiencia
        - problem_solved: descripción del problema que resuelven
        - product_status: estado del producto (idea, desarrollo, mvp, lanzado)
        - previous_funding: financiación anterior
        - additional_fields: cualquier otro dato relevante

        RESPONDE SOLO CON JSON VÁLIDO:
        {{
            "has_updates": true/false,
            "confidence_score": 0.0-1.0,
            "reasoning": "Explicación de qué información se extrajo",
            "updates": {{
                "categories": ["categoria1"] (solo si detectas),
                "stage": "stage" (solo si detectas),
                "metrics": {{
                    "arr": "valor",
                    "mrr": "valor",
                    "users": "valor",
                    "revenue": "valor",
                    "growth_rate": "valor"
                }} (solo campos detectados),
                "team_info": {{
                    "size": numero,
                    "roles": ["rol1", "rol2"],
                    "experience": "descripción",
                    "previous_companies": ["empresa1"]
                }} (solo campos detectados),
                "problem_solved": "descripción" (solo si detectas),
                "product_status": "estado" (solo si detectas),
                "previous_funding": "descripción" (solo si detectas),
                "additional_fields": {{
                    "campo_custom": "valor"
                }} (solo si detectas información relevante no categorizada)
            }}
        }}

        IMPORTANTE:
        - Solo incluye campos en "updates" si hay información NUEVA y CONFIABLE
        - No dupliques información que ya existe exactamente igual
        - Si no hay información nueva, marca has_updates: false
        - Confidence_score alto (>0.8) solo para información muy explícita
        """
    
    def _parse_analysis_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parsear respuesta de análisis"""
        try:
            # Limpiar respuesta JSON
            json_text = response_text.strip()
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0]
            
            return json.loads(json_text.strip())
            
        except Exception as e:
            logger.error(f"Error parsing librarian response: {e}")
            logger.error(f"Response text: {response_text}")
            return None
    
    def _merge_project_data(self, current_data: ProjectData, updates: Dict[str, Any]) -> ProjectData:
        """Fusionar datos actuales con actualizaciones"""
        try:
            # Convertir datos actuales a dict
            current_dict = current_data.dict() if current_data else {}
            
            # Aplicar actualizaciones
            for field, value in updates.items():
                if field == "metrics" and value:
                    # Fusionar métricas
                    current_metrics = current_dict.get("metrics", {}) or {}
                    for metric_key, metric_value in value.items():
                        if metric_value:  # Solo actualizar si hay valor
                            current_metrics[metric_key] = metric_value
                    current_dict["metrics"] = current_metrics
                    
                elif field == "team_info" and value:
                    # Fusionar información del equipo
                    current_team = current_dict.get("team_info", {}) or {}
                    for team_key, team_value in value.items():
                        if team_value:  # Solo actualizar si hay valor
                            current_team[team_key] = team_value
                    current_dict["team_info"] = current_team
                    
                elif field == "additional_fields" and value:
                    # Fusionar campos adicionales
                    current_additional = current_dict.get("additional_fields", {}) or {}
                    current_additional.update(value)
                    current_dict["additional_fields"] = current_additional
                    
                elif field == "categories" and value:
                    # Para categorías, fusionar listas evitando duplicados
                    current_categories = current_dict.get("categories", []) or []
                    new_categories = list(set(current_categories + value))
                    current_dict["categories"] = new_categories
                    
                else:
                    # Para otros campos, reemplazar si hay valor
                    if value:
                        current_dict[field] = value
            
            # Crear objeto ProjectData actualizado
            return ProjectData(**current_dict)
            
        except Exception as e:
            logger.error(f"Error merging project data: {e}")
            return current_data  # Retornar datos originales si hay error
    
    async def force_analysis(
        self, 
        project_id: UUID, 
        user_id: UUID, 
        conversation_history: List[str]
    ) -> Optional[LibrarianUpdate]:
        """
        Forzar análisis completo del historial de conversación
        Útil para proyectos con datos incompletos
        """
        try:
            # Obtener proyecto actual
            project = await db.get_project(project_id, user_id)
            if not project:
                return None
            
            # Crear prompt con todo el historial
            full_context = "\n".join(conversation_history[-10:])  # Últimas 10 conversaciones
            
            prompt = f"""
            ANALIZA TODO EL HISTORIAL DE CONVERSACIÓN PARA EXTRAER INFORMACIÓN COMPLETA DEL PROYECTO.

            HISTORIAL COMPLETO:
            {full_context}

            DATOS ACTUALES:
            {json.dumps(project.project_data.dict(), indent=2, ensure_ascii=False)}

            Extrae TODA la información posible sobre el proyecto siguiendo el mismo formato JSON.
            Prioriza información más reciente si hay contradicciones.
            """
            
            response = self.model.generate_content(prompt)
            analysis = self._parse_analysis_response(response.text)
            
            if analysis and analysis.get("has_updates", False):
                updated_data = self._merge_project_data(project.project_data, analysis["updates"])
                
                success = await db.update_project_data(project_id, user_id, updated_data)
                
                if success:
                    return LibrarianUpdate(
                        project_id=project_id,
                        conversation_id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
                        updates_made=analysis["updates"],
                        confidence_score=analysis.get("confidence_score", 0.8),
                        reasoning="Análisis forzado del historial completo"
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in force analysis: {e}")
            return None

# Instancia global
librarian = LibrarianBot()
