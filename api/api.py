import os
import jwt
import asyncio
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from datetime import datetime
import json
import logging

# Imports locales
from models.schemas import (
    ChatMessage, ChatResponse, ProjectCreate, Project, 
    WelcomeMessage, ConversationHistory, CompletenessResponse,
    ApiResponse, ConversationList, HealthCheck, UserProfile
)
from database.database import db
from chat.chat import chat_system
from chat.welcome import welcome_system
from chat.judge import judge
from chat.librarian import librarian

# Imports routers
from api.linkedin import router as linkedin_router
from api.outreach import router as outreach_router
from api.webhooks import router as webhooks_router

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="0Bullshit Chat API",
    description="API para el sistema de chat con IA especializado en startups",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seguridad JWT
security = HTTPBearer()

# ==========================================
# UTILITIES Y MIDDLEWARE
# ==========================================

def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decodificar JWT token"""
    try:
        payload = jwt.decode(
            token, 
            os.getenv("JWT_SECRET_KEY", "default-secret-key"), 
            algorithms=[os.getenv("JWT_ALGORITHM", "HS256")]
        )
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UUID:
    """Obtener usuario actual del JWT"""
    payload = decode_jwt_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    return UUID(user_id)

# ==========================================
# WEBSOCKET MANAGER
# ==========================================

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_message(self, client_id: str, message: Dict[str, Any]):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending websocket message: {e}")
                self.disconnect(client_id)

ws_manager = WebSocketManager()

# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    services = {}
    
    # Check Supabase
    try:
        # Simple query to test connection
        result = db.supabase.table("users").select("id").limit(1).execute()
        services["supabase"] = "healthy"
    except Exception:
        services["supabase"] = "unhealthy"
    
    # Check Gemini API
    try:
        # Test with simple generation
        test_response = judge.model.generate_content("Test connection")
        services["gemini"] = "healthy" if test_response else "unhealthy"
    except Exception:
        services["gemini"] = "unhealthy"
    
    return HealthCheck(
        status="healthy" if all(s == "healthy" for s in services.values()) else "degraded",
        timestamp=datetime.now(),
        services=services
    )

# ==========================================
# PROJECT ENDPOINTS
# ==========================================

@app.post("/api/v1/projects", response_model=Project)
async def create_project(
    project_data: ProjectCreate,
    current_user: UUID = Depends(get_current_user)
):
    """Crear nuevo proyecto"""
    try:
        project = await db.create_project(current_user, project_data)
        return project
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail="Error creating project")

@app.get("/api/v1/projects", response_model=List[Project])
async def get_user_projects(current_user: UUID = Depends(get_current_user)):
    """Obtener todos los proyectos del usuario"""
    try:
        projects = await db.get_user_projects(current_user)
        return projects
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        raise HTTPException(status_code=500, detail="Error getting projects")

@app.get("/api/v1/projects/{project_id}", response_model=Project)
async def get_project(
    project_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Obtener proyecto específico"""
    try:
        project = await db.get_project(project_id, current_user)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail="Error getting project")

@app.get("/api/v1/projects/{project_id}/completeness", response_model=CompletenessResponse)
async def get_project_completeness(
    project_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Obtener análisis de completitud del proyecto"""
    try:
        completeness = await chat_system.get_project_completeness(project_id, current_user)
        return completeness
    except Exception as e:
        logger.error(f"Error getting completeness: {e}")
        raise HTTPException(status_code=500, detail="Error analyzing project completeness")

# ==========================================
# CHAT ENDPOINTS
# ==========================================

@app.post("/api/v1/chat/welcome-message/{project_id}", response_model=WelcomeMessage)
async def generate_welcome_message(
    project_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Generar mensaje de bienvenida personalizado"""
    try:
        # Obtener proyecto
        project = await db.get_project(project_id, current_user)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Verificar si es primera vez
        user_projects = await db.get_user_projects(current_user)
        is_first_time = len(user_projects) <= 1
        
        # Generar mensaje
        welcome_msg = await welcome_system.generate_welcome_message(
            project, current_user, is_first_time
        )
        
        # Guardar como conversación
        welcome_conversation = ChatResponse(
            id=uuid4(),
            project_id=project_id,
            role="assistant",
            content=welcome_msg.message,
            ai_extractions={"welcome_type": welcome_msg.message_type},
            created_at=datetime.now()
        )
        await db.save_conversation(welcome_conversation)
        
        return welcome_msg
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating welcome message: {e}")
        raise HTTPException(status_code=500, detail="Error generating welcome message")

@app.post("/api/v1/chat/message", response_model=ChatResponse)
async def send_chat_message(
    message: ChatMessage,
    current_user: UUID = Depends(get_current_user)
):
    """Enviar mensaje de chat"""
    try:
        # Verificar que el proyecto pertenece al usuario
        project = await db.get_project(message.project_id, current_user)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Procesar mensaje
        response, search_results = await chat_system.process_message(
            message.content,
            message.project_id,
            current_user,
            websocket_callback=lambda msg: ws_manager.send_message(
                f"{current_user}_{message.project_id}", msg
            )
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail="Error processing message")

@app.get("/api/v1/chat/conversations/{project_id}", response_model=List[ChatResponse])
async def get_conversation_history(
    project_id: UUID,
    limit: int = 50,
    current_user: UUID = Depends(get_current_user)
):
    """Obtener historial de conversación"""
    try:
        # Verificar proyecto
        project = await db.get_project(project_id, current_user)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Obtener conversaciones
        conversations = await db.get_conversations(project_id, limit)
        return conversations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(status_code=500, detail="Error getting conversation history")

@app.get("/api/v1/chat/conversations", response_model=ConversationList)
async def get_conversation_list(current_user: UUID = Depends(get_current_user)):
    """Obtener lista de conversaciones (como ChatGPT)"""
    try:
        conversations = await db.get_conversation_titles(current_user)
        return ConversationList(
            conversations=conversations,
            total=len(conversations)
        )
    except Exception as e:
        logger.error(f"Error getting conversation list: {e}")
        raise HTTPException(status_code=500, detail="Error getting conversation list")

# ==========================================
# WEBSOCKET ENDPOINT
# ==========================================

@app.websocket("/ws/chat/{project_id}")
async def websocket_chat(websocket: WebSocket, project_id: UUID):
    """WebSocket para chat en tiempo real"""
    
    # Obtener user_id del query param o token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return
    
    try:
        user_payload = decode_jwt_token(token)
        user_id = UUID(user_payload.get("sub"))
    except Exception:
        await websocket.close(code=4001, reason="Invalid authentication token")
        return
    
    # Verificar proyecto
    try:
        project = await db.get_project(project_id, user_id)
        if not project:
            await websocket.close(code=4004, reason="Project not found")
            return
    except Exception:
        await websocket.close(code=4000, reason="Error verifying project")
        return
    
    # Conectar WebSocket
    client_id = f"{user_id}_{project_id}"
    await ws_manager.connect(websocket, client_id)
    
    try:
        # Mantener conexión viva
        while True:
            try:
                # Esperar por mensajes del cliente (keepalive)
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Echo del mensaje para keepalive
                await websocket.send_text(json.dumps({
                    "type": "keepalive",
                    "timestamp": datetime.now().isoformat()
                }))
                
            except asyncio.TimeoutError:
                # Enviar ping
                await websocket.send_text(json.dumps({"type": "ping"}))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        ws_manager.disconnect(client_id)

# ==========================================
# USER ENDPOINTS
# ==========================================

@app.get("/api/v1/user/profile", response_model=UserProfile)
async def get_user_profile(current_user: UUID = Depends(get_current_user)):
    """Obtener perfil del usuario"""
    try:
        profile = await db.get_user_profile(current_user)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail="Error getting user profile")

# ==========================================
# ADMIN/DEBUG ENDPOINTS
# ==========================================

@app.post("/api/v1/admin/force-librarian-analysis/{project_id}")
async def force_librarian_analysis(
    project_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Forzar análisis del bibliotecario (para testing)"""
    try:
        # Obtener conversaciones
        conversations = await db.get_conversations(project_id, limit=10)
        conversation_texts = [conv.content for conv in conversations]
        
        # Forzar análisis
        result = await librarian.force_analysis(project_id, current_user, conversation_texts)
        
        return ApiResponse(
            success=True,
            message="Librarian analysis completed",
            data=result.dict() if result else None
        )
        
    except Exception as e:
        logger.error(f"Error in force librarian analysis: {e}")
        raise HTTPException(status_code=500, detail="Error in librarian analysis")

@app.get("/api/v1/admin/judge-analysis/{project_id}")
async def debug_judge_analysis(
    project_id: UUID,
    message: str,
    current_user: UUID = Depends(get_current_user)
):
    """Debug: Obtener análisis del juez sin procesar mensaje"""
    try:
        project = await db.get_project(project_id, current_user)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        decision = await judge.analyze_user_intent(message, project, [])
        
        return ApiResponse(
            success=True,
            message="Judge analysis completed",
            data=decision.dict()
        )
        
    except Exception as e:
        logger.error(f"Error in judge analysis: {e}")
        raise HTTPException(status_code=500, detail="Error in judge analysis")

# ==========================================
# ERROR HANDLERS
# ==========================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# ==========================================
# STARTUP/SHUTDOWN EVENTS
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Eventos de inicio"""
    logger.info("0Bullshit Chat API starting up...")
    
    # Verificar conexiones
    try:
        # Test Supabase
        db.supabase.table("users").select("id").limit(1).execute()
        logger.info("✅ Supabase connection OK")
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {e}")
    
    try:
        # Test Gemini
        test_response = judge.model.generate_content("Test")
        logger.info("✅ Gemini API connection OK")
    except Exception as e:
        logger.error(f"❌ Gemini API connection failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Eventos de cierre"""
    logger.info("0Bullshit Chat API shutting down...")
    
    # Cerrar conexiones WebSocket
    for client_id in list(ws_manager.active_connections.keys()):
        ws_manager.disconnect(client_id)

# Al final de la configuración de FastAPI, después de app = FastAPI(...)
app.include_router(linkedin_router, prefix="/api/v1")
app.include_router(outreach_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )

