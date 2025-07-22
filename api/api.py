import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.auth import auth_router, get_current_user
from api.linkedin import linkedin_router
from api.outreach import outreach_router
from api.webhooks import webhooks_router
from api.campaigns import campaigns_router
from api.analytics import router as analytics_router
from payments.payments import router as payments_router
from config.settings import *
from database.database import DatabaseManager
from investors.investors import investor_search_engine
from chat.upsell_system import upsell_system
from chat.welcome_system import welcome_system
from campaigns.message_generator import message_generator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="0Bullshit API",
    description="AI-powered investor matching and outreach platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database instance
db = DatabaseManager()

# Incluir todos los routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(payments_router, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(linkedin_router, prefix="/api/v1", tags=["LinkedIn"])
app.include_router(outreach_router, prefix="/api/v1", tags=["Outreach"])
app.include_router(webhooks_router, prefix="/api/v1", tags=["Webhooks"])
app.include_router(campaigns_router, prefix="/api/v1", tags=["Campaigns"])

# ==========================================
# MODELS
# ==========================================

class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    project_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    ai_extractions: Optional[Dict] = None
    upsell_opportunity: Optional[Dict] = None
    onboarding_info: Optional[Dict] = None

class ProjectCreate(BaseModel):
    name: str
    description: str
    stage: str
    category: str
    business_model: Optional[str] = None
    target_market: Optional[str] = None
    funding_amount: Optional[str] = None

class SearchRequest(BaseModel):
    project_id: str
    search_type: str = "hybrid"  # hybrid, angels, funds
    limit: int = 15

# ==========================================
# WEBSOCKET MANAGER
# ==========================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")
                self.disconnect(user_id)

manager = ConnectionManager()

# ==========================================
# ENHANCED CHAT SYSTEM
# ==========================================

class EnhancedChatSystem:
    def __init__(self):
        self.db = DatabaseManager()
        
    async def process_chat_message(
        self, 
        user_id: UUID, 
        message: str, 
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict:
        """
        Procesa un mensaje de chat con todas las funcionalidades integradas
        """
        try:
            # Obtener datos del usuario
            user_data = await self._get_user_data(user_id)
            if not user_data:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Manejar onboarding si es necesario
            onboarding_response = await self._handle_onboarding(user_id, user_data, message)
            if onboarding_response:
                return onboarding_response
            
            # Crear o obtener conversación
            if not conversation_id:
                conversation_id = await self._create_conversation(user_id, project_id)
            
            # Obtener contexto de la conversación
            conversation_context = await self._get_conversation_context(conversation_id)
            
            # Procesar mensaje con AI (Judge, Mentor, Librarian)
            ai_response = await self._process_with_ai_agents(
                user_id, message, conversation_context, user_data, project_id
            )
            
            # Guardar mensaje del usuario
            await self._save_message(conversation_id, "user", message)
            
            # Analizar oportunidad de upsell
            upsell_opportunity = await upsell_system.analyze_upsell_opportunity(
                user_id=user_id,
                conversation_context=conversation_context + f"\nUser: {message}",
                user_data=user_data,
                current_action=ai_response.get("action", "chat")
            )
            
            # Construir respuesta final
            final_response = ai_response["response"]
            if upsell_opportunity and upsell_opportunity.get("should_upsell"):
                final_response += f"\n\n{upsell_opportunity['message']}"
            
            # Guardar respuesta del asistente
            await self._save_message(
                conversation_id, 
                "assistant", 
                final_response,
                ai_response.get("extractions"),
                upsell_opportunity
            )
            
            # Deducir créditos si es necesario
            if ai_response.get("credits_used", 0) > 0:
                await db.deduct_user_credits(user_id, ai_response["credits_used"])
            
            return {
                "response": final_response,
                "conversation_id": conversation_id,
                "ai_extractions": ai_response.get("extractions"),
                "upsell_opportunity": upsell_opportunity,
                "credits_used": ai_response.get("credits_used", 0),
                "action_taken": ai_response.get("action")
            }
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            raise HTTPException(status_code=500, detail="Error processing message")
    
    async def _handle_onboarding(self, user_id: UUID, user_data: Dict, message: str) -> Optional[Dict]:
        """
        Maneja el proceso de onboarding si es necesario
        """
        try:
            # Verificar si el usuario necesita onboarding
            if not user_data.get("onboarding_completed", False):
                # Verificar progreso actual
                progress = await welcome_system._get_onboarding_progress(user_id)
                
                if not progress:
                    # Iniciar onboarding
                    return await welcome_system.start_onboarding(user_id, user_data)
                else:
                    # Continuar onboarding
                    current_stage = progress.get("current_stage", "welcome")
                    return await welcome_system.continue_onboarding(
                        user_id, current_stage, {"message": message}
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling onboarding: {e}")
            return None
    
    async def _process_with_ai_agents(
        self, 
        user_id: UUID, 
        message: str, 
        conversation_context: str, 
        user_data: Dict,
        project_id: Optional[str]
    ) -> Dict:
        """
        Procesa el mensaje con los agentes AI (Judge, Mentor, Librarian)
        """
        try:
            # Importar sistemas de chat
            from chat.judge import judge_system
            from chat.chat import ChatSystem
            
            # Usar el Judge para determinar la acción
            judge_decision = await judge_system.analyze_user_intent(
                message, conversation_context, user_data, project_id
            )
            
            credits_used = 0
            extractions = {}
            
            if judge_decision["action"] == "search_investors":
                # Buscar inversores
                if not project_id:
                    return {
                        "response": "Necesito que me proporciones más información sobre tu proyecto antes de buscar inversores. ¿Podrías contarme sobre tu startup?",
                        "action": "request_project_info",
                        "credits_used": 0
                    }
                
                # Obtener datos del proyecto
                project_data = await self._get_project_data(project_id)
                if not project_data:
                    return {
                        "response": "No encontré información del proyecto. ¿Podrías crear un proyecto primero?",
                        "action": "request_project_creation",
                        "credits_used": 0
                    }
                
                # Realizar búsqueda
                search_results, metadata = await investor_search_engine.search_investors(
                    project_data=project_data,
                    completeness_score=judge_decision.get("completeness_score", 75),
                    search_type="hybrid",
                    limit=15
                )
                
                # Generar respuesta con resultados
                response = await self._format_search_results(search_results, metadata)
                credits_used = metadata.get("credits_used", 50)
                extractions = {
                    "search_results": {
                        "total_found": len(search_results),
                        "displayed": min(len(search_results), 5),
                        "average_relevance": metadata.get("average_relevance", 0)
                    }
                }
                
            elif judge_decision["action"] == "provide_advice":
                # Usar Mentor Y-Combinator
                chat_system = ChatSystem()
                response = await chat_system.get_mentor_advice(message, conversation_context, user_data)
                
            elif judge_decision["action"] == "answer_question":
                # Usar Librarian
                chat_system = ChatSystem()
                response = await chat_system.get_librarian_response(message, conversation_context)
                
            else:
                # Respuesta general del chat
                chat_system = ChatSystem()
                response = await chat_system.generate_response(message, conversation_context, user_data)
            
            return {
                "response": response,
                "action": judge_decision["action"],
                "credits_used": credits_used,
                "extractions": {
                    "judge_decision": judge_decision,
                    **extractions
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing with AI agents: {e}")
            return {
                "response": "Lo siento, hubo un error procesando tu mensaje. ¿Podrías intentar de nuevo?",
                "action": "error",
                "credits_used": 0
            }
    
    async def _get_user_data(self, user_id: UUID) -> Optional[Dict]:
        """Obtiene datos completos del usuario"""
        try:
            query = db.supabase.table("users").select("*").eq("id", str(user_id)).execute()
            return query.data[0] if query.data else None
        except Exception as e:
            logger.error(f"Error getting user data: {e}")
            return None
    
    async def _get_project_data(self, project_id: str) -> Optional[Dict]:
        """Obtiene datos del proyecto"""
        try:
            query = db.supabase.table("projects").select("*").eq("id", project_id).execute()
            return query.data[0] if query.data else None
        except Exception as e:
            logger.error(f"Error getting project data: {e}")
            return None
    
    async def _create_conversation(self, user_id: UUID, project_id: Optional[str]) -> str:
        """Crea una nueva conversación"""
        try:
            conversation_id = str(uuid4())
            conversation_data = {
                "id": conversation_id,
                "user_id": str(user_id),
                "project_id": project_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            db.supabase.table("conversations").insert(conversation_data).execute()
            return conversation_id
            
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise
    
    async def _get_conversation_context(self, conversation_id: str) -> str:
        """Obtiene el contexto de la conversación"""
        try:
            query = db.supabase.table("messages")\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("created_at", desc=False)\
                .limit(20)\
                .execute()
            
            messages = query.data if query.data else []
            
            context = ""
            for msg in messages:
                role = "Usuario" if msg["role"] == "user" else "Asistente"
                context += f"{role}: {msg['content']}\n"
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return ""
    
    async def _save_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str,
        ai_extractions: Optional[Dict] = None,
        upsell_data: Optional[Dict] = None
    ):
        """Guarda un mensaje en la base de datos"""
        try:
            message_data = {
                "id": str(uuid4()),
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "ai_extractions": ai_extractions,
                "created_at": datetime.now().isoformat()
            }
            
            if upsell_data:
                message_data["ai_extractions"] = {
                    **(ai_extractions or {}),
                    "upsell_opportunity": upsell_data
                }
            
            db.supabase.table("messages").insert(message_data).execute()
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
    
    async def _format_search_results(self, results: List[Dict], metadata: Dict) -> str:
        """Formatea los resultados de búsqueda para mostrar al usuario"""
        try:
            if not results:
                return "No encontré inversores que coincidan con tu perfil en este momento. ¿Podrías proporcionar más detalles sobre tu proyecto?"
            
            response = f"Perfecto, he encontrado {len(results)} inversores especializados que coinciden con tu perfil:\n\n**TOP MATCHES:**\n"
            
            # Mostrar top 3 resultados
            for i, investor in enumerate(results[:3], 1):
                response += f"{i}. **{investor.get('name', 'Inversor')}**"
                if investor.get('company'):
                    response += f" - {investor['company']}"
                response += f"\n   - Especialización: {investor.get('investment_focus', 'General')}"
                if investor.get('stage_preference'):
                    response += f"\n   - Etapa: {investor['stage_preference']}"
                response += f"\n   - Score de relevancia: {investor.get('relevance_score', 0):.1f}%\n\n"
            
            response += "**NEXT STEPS:**\n¿Quieres que prepare una campaña de outreach personalizada para contactar a estos inversores automáticamente por LinkedIn?"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting search results: {e}")
            return "Encontré varios inversores interesantes. ¿Te gustaría ver los detalles?"

# Instancia global del chat mejorado
enhanced_chat = EnhancedChatSystem()

# ==========================================
# ENDPOINTS
# ==========================================

@app.get("/")
async def root():
    return {"message": "0Bullshit API - AI Investor Matching Platform"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ==========================================
# CHAT ENDPOINTS
# ==========================================

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(
    chat_data: ChatMessage,
    current_user: UUID = Depends(get_current_user)
):
    """
    Endpoint principal de chat con AI integrado
    """
    return await enhanced_chat.process_chat_message(
        user_id=current_user,
        message=chat_data.message,
        conversation_id=chat_data.conversation_id,
        project_id=chat_data.project_id
    )

@app.get("/api/v1/conversations")
async def get_conversations(current_user: UUID = Depends(get_current_user)):
    """
    Obtiene las conversaciones del usuario
    """
    try:
        query = db.supabase.table("conversations")\
            .select("*")\
            .eq("user_id", str(current_user))\
            .order("updated_at", desc=True)\
            .execute()
        
        return {"conversations": query.data if query.data else []}
        
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving conversations")

@app.get("/api/v1/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_user: UUID = Depends(get_current_user)
):
    """
    Obtiene los mensajes de una conversación
    """
    try:
        # Verificar que la conversación pertenece al usuario
        conv_query = db.supabase.table("conversations")\
            .select("*")\
            .eq("id", conversation_id)\
            .eq("user_id", str(current_user))\
            .execute()
        
        if not conv_query.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Obtener mensajes
        messages_query = db.supabase.table("messages")\
            .select("*")\
            .eq("conversation_id", conversation_id)\
            .order("created_at", desc=False)\
            .execute()
        
        return {"messages": messages_query.data if messages_query.data else []}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation messages: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving messages")

# ==========================================
# PROJECTS ENDPOINTS
# ==========================================

@app.post("/api/v1/projects")
async def create_project(
    project_data: ProjectCreate,
    current_user: UUID = Depends(get_current_user)
):
    """
    Crea un nuevo proyecto
    """
    try:
        project_id = str(uuid4())
        project_dict = {
            "id": project_id,
            "user_id": str(current_user),
            "name": project_data.name,
            "description": project_data.description,
            "stage": project_data.stage,
            "category": project_data.category,
            "business_model": project_data.business_model,
            "target_market": project_data.target_market,
            "funding_amount": project_data.funding_amount,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        result = db.supabase.table("projects").insert(project_dict).execute()
        
        if result.data:
            return {"message": "Project created successfully", "project": result.data[0]}
        else:
            raise HTTPException(status_code=500, detail="Failed to create project")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail="Error creating project")

@app.get("/api/v1/projects")
async def get_user_projects(current_user: UUID = Depends(get_current_user)):
    """
    Obtiene los proyectos del usuario
    """
    try:
        query = db.supabase.table("projects")\
            .select("*")\
            .eq("user_id", str(current_user))\
            .order("created_at", desc=True)\
            .execute()
        
        return {"projects": query.data if query.data else []}
        
    except Exception as e:
        logger.error(f"Error getting user projects: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving projects")

# ==========================================
# SEARCH ENDPOINTS
# ==========================================

@app.post("/api/v1/search/investors")
async def search_investors(
    search_data: SearchRequest,
    current_user: UUID = Depends(get_current_user)
):
    """
    Busca inversores para un proyecto específico
    """
    try:
        # Verificar que el proyecto pertenece al usuario
        project_query = db.supabase.table("projects")\
            .select("*")\
            .eq("id", search_data.project_id)\
            .eq("user_id", str(current_user))\
            .execute()
        
        if not project_query.data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_data = project_query.data[0]
        
        # Verificar créditos del usuario
        user_query = db.supabase.table("users")\
            .select("credits, plan")\
            .eq("id", str(current_user))\
            .execute()
        
        if not user_query.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_credits = user_query.data[0].get("credits", 0)
        if user_credits < 50:  # Costo de búsqueda
            raise HTTPException(status_code=402, detail="Insufficient credits")
        
        # Callback para WebSocket updates
        async def websocket_callback(progress_data):
            await manager.send_personal_message(
                json.dumps({"type": "search_progress", "data": progress_data}),
                str(current_user)
            )
        
        # Realizar búsqueda
        search_results, metadata = await investor_search_engine.search_investors(
            project_data=project_data,
            completeness_score=75.0,  # Calcular dinámicamente
            search_type=search_data.search_type,
            limit=search_data.limit,
            websocket_callback=websocket_callback
        )
        
        # Deducir créditos
        await db.deduct_user_credits(current_user, metadata.get("credits_used", 50))
        
        return {
            "results": search_results,
            "metadata": metadata,
            "credits_used": metadata.get("credits_used", 50)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching investors: {e}")
        raise HTTPException(status_code=500, detail="Error performing search")

# ==========================================
# WEBSOCKET ENDPOINTS
# ==========================================

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint para actualizaciones en tiempo real
    """
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Mantener conexión viva
            data = await websocket.receive_text()
            
            # Echo para ping/pong
            if data == "ping":
                await websocket.send_text("pong")
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
