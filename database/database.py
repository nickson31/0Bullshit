import os
import json
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from supabase import create_client, Client
from models.schemas import (
    Project, ProjectCreate, ProjectData, ChatResponse, 
    InvestorResult, CompanyResult, UserProfile, ChatConversation
)
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
    
    # ==========================================
    # PROJECT OPERATIONS
    # ==========================================
    
    async def create_project(self, user_id: UUID, project_data: ProjectCreate) -> Project:
        """Crear nuevo proyecto"""
        try:
            project_id = uuid4()
            
            # Estructura inicial del project_data
            initial_data = ProjectData(
                categories=None,
                stage=None,
                metrics=None,
                team_info=None,
                problem_solved=None,
                product_status=None,
                previous_funding=None,
                additional_fields={}
            )
            
            project_dict = {
                "id": str(project_id),
                "user_id": str(user_id),
                "name": project_data.name,
                "description": project_data.description,
                "categories": [],
                "stage": None,
                "project_data": initial_data.dict(),
                "context_summary": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("projects").insert(project_dict).execute()
            
            if result.data:
                return self._dict_to_project(result.data[0])
            else:
                raise Exception("Failed to create project")
                
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            raise
    
    async def get_project(self, project_id: UUID, user_id: UUID) -> Optional[Project]:
        """Obtener proyecto por ID"""
        try:
            result = self.supabase.table("projects").select("*").eq("id", str(project_id)).eq("user_id", str(user_id)).execute()
            
            if result.data:
                return self._dict_to_project(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Error getting project: {e}")
            return None
    
    async def update_project_data(self, project_id: UUID, user_id: UUID, project_data: ProjectData) -> bool:
        """Actualizar datos del proyecto"""
        try:
            # También actualizar categories y stage en campos separados para búsquedas
            update_data = {
                "project_data": project_data.dict(),
                "categories": project_data.categories or [],
                "stage": project_data.stage,
                "updated_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("projects").update(update_data).eq("id", str(project_id)).eq("user_id", str(user_id)).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating project data: {e}")
            return False
    
    async def get_user_projects(self, user_id: UUID) -> List[Project]:
        """Obtener todos los proyectos del usuario"""
        try:
            result = self.supabase.table("projects").select("*").eq("user_id", str(user_id)).order("updated_at", desc=True).execute()
            
            return [self._dict_to_project(project) for project in result.data]
            
        except Exception as e:
            logger.error(f"Error getting user projects: {e}")
            return []
    
    # ==========================================
    # CONVERSATION OPERATIONS
    # ==========================================
    
    async def save_conversation(self, conversation: ChatResponse) -> bool:
        """Guardar conversación"""
        try:
            conv_dict = {
                "id": str(conversation.id),
                "project_id": str(conversation.project_id),
                "role": conversation.role,
                "content": conversation.content,
                "ai_extractions": conversation.ai_extractions,
                "gemini_prompt_used": conversation.gemini_prompt_used,
                "gemini_response_raw": conversation.gemini_response_raw,
                "created_at": conversation.created_at.isoformat()
            }
            
            result = self.supabase.table("conversations").insert(conv_dict).execute()
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            return False
    
    async def get_conversations(self, project_id: UUID, limit: int = 50) -> List[ChatResponse]:
        """Obtener historial de conversaciones"""
        try:
            result = self.supabase.table("conversations").select("*").eq("project_id", str(project_id)).order("created_at", desc=False).limit(limit).execute()
            
            conversations = []
            for conv in result.data:
                conversations.append(ChatResponse(
                    id=UUID(conv["id"]),
                    project_id=UUID(conv["project_id"]),
                    role=conv["role"],
                    content=conv["content"],
                    ai_extractions=conv.get("ai_extractions"),
                    gemini_prompt_used=conv.get("gemini_prompt_used"),
                    gemini_response_raw=conv.get("gemini_response_raw"),
                    created_at=datetime.fromisoformat(conv["created_at"].replace("Z", "+00:00"))
                ))
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            return []
    
    async def get_conversation_titles(self, user_id: UUID) -> List[ChatConversation]:
        """Obtener lista de conversaciones agrupadas por proyecto (como ChatGPT)"""
        try:
            # Obtener proyectos con count de mensajes
            result = self.supabase.table("projects").select("""
                id, name, created_at, updated_at,
                conversations(count)
            """).eq("user_id", str(user_id)).order("updated_at", desc=True).execute()
            
            conversations = []
            for project in result.data:
                message_count = len(project.get("conversations", []))
                if message_count > 0:  # Solo mostrar proyectos con mensajes
                    conversations.append(ChatConversation(
                        id=UUID(project["id"]),
                        project_id=UUID(project["id"]),
                        title=project["name"],
                        created_at=datetime.fromisoformat(project["created_at"].replace("Z", "+00:00")),
                        updated_at=datetime.fromisoformat(project["updated_at"].replace("Z", "+00:00")),
                        message_count=message_count
                    ))
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting conversation titles: {e}")
            return []
    
    # ==========================================
    # SEARCH OPERATIONS
    # ==========================================
    
    async def search_investors(self, categories: List[str], stage: str, limit: int = 10) -> List[InvestorResult]:
        """Buscar inversores relevantes"""
        try:
            query = self.supabase.table("investors").select("*")
            
            # Filtrar por categorías si se proporcionan
            if categories:
                # Buscar en categories_general y categories_strong
                for category in categories:
                    query = query.or_(f"categories_general.cs.{{{category}}},categories_strong.cs.{{{category}}}")
            
            # Filtrar por stage si se proporciona
            if stage:
                query = query.or_(f"stages_general.cs.{{{stage}}},stages_strong.cs.{{{stage}}}")
            
            result = query.limit(limit).execute()
            
            investors = []
            for inv in result.data:
                # Calcular relevance_score basado en matches
                relevance_score = self._calculate_investor_relevance(inv, categories, stage)
                
                investors.append(InvestorResult(
                    id=UUID(inv.get("id", str(uuid4()))),
                    full_name=inv.get("full_name", ""),
                    headline=inv.get("headline"),
                    email=inv.get("email"),
                    linkedin_url=inv.get("linkedin_url"),
                    company_name=inv.get("company_name"),
                    fund_name=inv.get("fund_name"),
                    relevance_score=relevance_score,
                    categories_match=self._get_category_matches(inv, categories),
                    stage_match=self._check_stage_match(inv, stage)
                ))
            
            # Ordenar por relevancia
            investors.sort(key=lambda x: x.relevance_score, reverse=True)
            return investors
            
        except Exception as e:
            logger.error(f"Error searching investors: {e}")
            return []
    
    async def search_companies(self, problem_context: str, categories: List[str], limit: int = 10) -> List[CompanyResult]:
        """Buscar empresas/servicios relevantes"""
        try:
            query = self.supabase.table("COMPANIES").select("*")
            
            # Filtrar por categorías o contexto
            if categories:
                for category in categories:
                    query = query.ilike("sector_categorias", f"%{category}%")
            
            result = query.limit(limit).execute()
            
            companies = []
            for comp in result.data:
                companies.append(CompanyResult(
                    nombre=comp.get("nombre", ""),
                    descripcion_corta=comp.get("descripcion_corta"),
                    web_empresa=comp.get("web_empresa"),
                    sector_categorias=comp.get("sector_categorias"),
                    service_category=comp.get("service_category"),
                    startup_relevance_score=comp.get("startup_relevance_score")
                ))
            
            return companies
            
        except Exception as e:
            logger.error(f"Error searching companies: {e}")
            return []
    
    # ==========================================
    # USER OPERATIONS
    # ==========================================
    
    async def get_user_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Obtener perfil del usuario"""
        try:
            result = self.supabase.table("users").select("*").eq("id", str(user_id)).execute()
            
            if result.data:
                user_data = result.data[0]
                return UserProfile(
                    id=UUID(user_data["id"]),
                    email=user_data["email"],
                    credits_balance=user_data.get("credits_balance", 0),
                    plan=user_data.get("plan", "free"),
                    created_at=datetime.fromisoformat(user_data["created_at"].replace("Z", "+00:00"))
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    # ==========================================
    # HELPER METHODS
    # ==========================================
    
    def _dict_to_project(self, data: Dict) -> Project:
        """Convertir dict a Project model"""
        # Parsear project_data JSON si existe
        project_data = data.get("project_data", {})
        if isinstance(project_data, str):
            project_data = json.loads(project_data)
        
        return Project(
            id=UUID(data["id"]),
            user_id=UUID(data["user_id"]),
            name=data["name"],
            description=data.get("description"),
            categories=data.get("categories", []),
            stage=data.get("stage"),
            project_data=ProjectData(**project_data) if project_data else ProjectData(),
            context_summary=data.get("context_summary"),
            last_context_update=datetime.fromisoformat(data["last_context_update"].replace("Z", "+00:00")) if data.get("last_context_update") else None,
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
        )
    
    def _calculate_investor_relevance(self, investor: Dict, categories: List[str], stage: str) -> float:
        """Calcular score de relevancia para investor"""
        score = 0.0
        
        # Puntos por categorías
        if categories:
            categories_general = investor.get("categories_general", []) or []
            categories_strong = investor.get("categories_strong", []) or []
            
            for category in categories:
                if category in categories_strong:
                    score += 0.3
                elif category in categories_general:
                    score += 0.2
        
        # Puntos por stage
        if stage:
            stages_general = investor.get("stages_general", []) or []
            stages_strong = investor.get("stages_strong", []) or []
            
            if stage in stages_strong:
                score += 0.3
            elif stage in stages_general:
                score += 0.2
        
        return min(score, 1.0)  # Máximo 1.0
    
    def _get_category_matches(self, investor: Dict, categories: List[str]) -> List[str]:
        """Obtener categorías que coinciden"""
        if not categories:
            return []
        
        matches = []
        categories_general = investor.get("categories_general", []) or []
        categories_strong = investor.get("categories_strong", []) or []
        
        for category in categories:
            if category in categories_general or category in categories_strong:
                matches.append(category)
        
        return matches
    
    def _check_stage_match(self, investor: Dict, stage: str) -> bool:
        """Verificar si el stage coincide"""
        if not stage:
            return False
        
        stages_general = investor.get("stages_general", []) or []
        stages_strong = investor.get("stages_strong", []) or []
        
        return stage in stages_general or stage in stages_strong

# Instancia global
db = Database()
