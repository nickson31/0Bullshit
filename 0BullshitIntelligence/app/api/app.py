"""
Main FastAPI application for 0BullshitIntelligence microservice.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.core.config import settings, features
from app.core.logging import get_logger, performance_logger
from app.models import ResponseModel, ErrorResponse
from .routers import chat_router, search_router, webhooks_router, health_router
from .middleware import LoggingMiddleware, RateLimitMiddleware, AuthMiddleware
from .websockets import websocket_manager

logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="0BullshitIntelligence",
    description="Independent AI Chat Microservice for 0Bullshit Platform",
    version=settings.app_version,
    docs_url="/docs" if features.is_debug_mode() else None,
    redoc_url="/redoc" if features.is_debug_mode() else None,
    openapi_url="/openapi.json" if features.is_debug_mode() else None
)

# ==========================================
# MIDDLEWARE SETUP
# ==========================================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

# ==========================================
# EXCEPTION HANDLERS
# ==========================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with structured responses"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            message=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            details={"status_code": exc.status_code}
        ).dict()
    )


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors"""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            success=False,
            message=str(exc),
            error_code="VALIDATION_ERROR"
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            message="Internal server error",
            error_code="INTERNAL_ERROR"
        ).dict()
    )

# ==========================================
# ROUTE SETUP
# ==========================================

# Health and status endpoints
app.include_router(health_router, prefix="/health", tags=["Health"])

# Core API endpoints
app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(search_router, prefix="/api/v1/search", tags=["Search"])
app.include_router(webhooks_router, prefix="/api/v1/webhooks", tags=["Webhooks"])

# Static files for testing interface
if features.is_testing_interface_enabled():
    try:
        app.mount("/test-interface", StaticFiles(directory="testing_interface"), name="testing_interface")
        logger.info("✅ Testing interface mounted at /test-interface")
    except RuntimeError:
        logger.warning("⚠️ Testing interface directory not found, skipping mount")

# ==========================================
# WEBSOCKET ENDPOINTS
# ==========================================

@app.websocket("/ws/chat/{conversation_id}")
async def chat_websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """WebSocket endpoint for real-time chat communication"""
    try:
        await websocket_manager.connect(websocket, conversation_id)
        logger.info(f"WebSocket connected for conversation {conversation_id}")
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Process message and broadcast to connected clients
            await websocket_manager.handle_message(conversation_id, data)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for conversation {conversation_id}")
        await websocket_manager.disconnect(websocket, conversation_id)
    except Exception as e:
        logger.error(f"WebSocket error for conversation {conversation_id}: {e}")
        await websocket_manager.disconnect(websocket, conversation_id)


# ==========================================
# STARTUP AND SHUTDOWN EVENTS
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Application startup initialization"""
    logger.info("🚀 Starting 0BullshitIntelligence application...")
    
    # Log configuration
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {features.is_debug_mode()}")
    logger.info(f"Features enabled:")
    logger.info(f"  - Database sync: {features.is_sync_enabled()}")
    logger.info(f"  - Testing interface: {features.is_testing_interface_enabled()}")
    logger.info(f"  - Metrics: {features.is_metrics_enabled()}")
    
    # Start background tasks
    if features.is_metrics_enabled():
        from app.services.analytics_service import analytics_service
        asyncio.create_task(analytics_service.start_background_processing())
        logger.info("✅ Analytics service started")
    
    if features.is_sync_enabled():
        from app.services.sync_service import sync_service
        asyncio.create_task(sync_service.start_background_sync())
        logger.info("✅ Sync service started")
    
    logger.info("✅ Application startup completed")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown cleanup"""
    logger.info("🛑 Shutting down 0BullshitIntelligence application...")
    
    # Close WebSocket connections
    await websocket_manager.disconnect_all()
    
    # Stop background services
    if features.is_sync_enabled():
        from app.services.sync_service import sync_service
        await sync_service.stop()
    
    if features.is_metrics_enabled():
        from app.services.analytics_service import analytics_service
        await analytics_service.stop()
    
    logger.info("✅ Application shutdown completed")


# ==========================================
# ROOT ENDPOINTS
# ==========================================

@app.get("/", response_model=ResponseModel)
async def root():
    """Root endpoint with service information"""
    return ResponseModel(
        success=True,
        message="0BullshitIntelligence Microservice",
        data={
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "features": {
                "database_sync": features.is_sync_enabled(),
                "testing_interface": features.is_testing_interface_enabled(),
                "metrics": features.is_metrics_enabled()
            },
            "endpoints": {
                "chat": "/api/v1/chat",
                "search": "/api/v1/search",
                "websocket": "/ws/chat/{conversation_id}",
                "health": "/health",
                "docs": "/docs" if features.is_debug_mode() else None,
                "testing": "/test-interface" if features.is_testing_interface_enabled() else None
            }
        }
    )


@app.get("/status", response_model=ResponseModel)
async def status():
    """Detailed service status"""
    try:
        # Check database connectivity
        from app.database import database_manager
        db_status = await database_manager.health_check()
        
        # Check AI systems
        from app.ai_systems import ai_coordinator
        ai_status = await ai_coordinator.health_check()
        
        # Check search engines
        from app.search import search_coordinator
        search_status = await search_coordinator.health_check()
        
        overall_healthy = all([db_status, ai_status, search_status])
        
        return ResponseModel(
            success=overall_healthy,
            message="Service status check completed",
            data={
                "overall_status": "healthy" if overall_healthy else "degraded",
                "components": {
                    "database": "healthy" if db_status else "unhealthy",
                    "ai_systems": "healthy" if ai_status else "unhealthy", 
                    "search_engines": "healthy" if search_status else "unhealthy"
                },
                "uptime": "calculated_uptime_here",  # TODO: Implement uptime tracking
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return ResponseModel(
            success=False,
            message="Status check failed",
            data={"error": str(e)}
        )


# ==========================================
# METRICS ENDPOINT
# ==========================================

@app.get("/metrics", response_model=ResponseModel)
async def metrics():
    """Service metrics (if enabled)"""
    if not features.is_metrics_enabled():
        raise HTTPException(status_code=404, detail="Metrics not enabled")
    
    try:
        from app.services.analytics_service import analytics_service
        metrics_data = await analytics_service.get_current_metrics()
        
        return ResponseModel(
            success=True,
            message="Current service metrics",
            data=metrics_data
        )
        
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


# Export the app instance
__all__ = ["app"]