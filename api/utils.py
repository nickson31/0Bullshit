# api/utils.py
import os
import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

# Seguridad JWT
security = HTTPBearer()

# ==========================================
# AUTHENTICATION UTILITIES
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
# VALIDATION UTILITIES
# ==========================================

def validate_campaign_name(name: str) -> str:
    """Validar nombre de campaña"""
    if not name or len(name.strip()) < 1:
        raise HTTPException(status_code=400, detail="Campaign name cannot be empty")
    
    if len(name) > 200:
        raise HTTPException(status_code=400, detail="Campaign name too long (max 200 characters)")
    
    return name.strip()

def validate_message_template(template: str) -> str:
    """Validar template de mensaje"""
    if not template or len(template.strip()) < 10:
        raise HTTPException(status_code=400, detail="Message template must be at least 10 characters")
    
    if len(template) > 2000:
        raise HTTPException(status_code=400, detail="Message template too long (max 2000 characters)")
    
    return template.strip()

def validate_linkedin_message_length(message: str) -> bool:
    """Validar longitud de mensaje de LinkedIn"""
    return len(message) <= 300  # LinkedIn invitation limit

# ==========================================
# RESPONSE UTILITIES
# ==========================================

def format_error_response(error: Exception, context: str = "") -> Dict[str, Any]:
    """Formatear respuesta de error"""
    logger.error(f"Error in {context}: {error}")
    
    return {
        "success": False,
        "error": str(error),
        "context": context
    }

def format_success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """Formatear respuesta exitosa"""
    response = {
        "success": True,
        "message": message
    }
    
    if data is not None:
        response["data"] = data
    
    return response

# ==========================================
# PAGINATION UTILITIES
# ==========================================

def validate_pagination_params(page: int = 1, limit: int = 50) -> tuple[int, int]:
    """Validar parámetros de paginación"""
    if page < 1:
        page = 1
    
    if limit < 1:
        limit = 50
    elif limit > 100:
        limit = 100
    
    offset = (page - 1) * limit
    
    return offset, limit

# ==========================================
# CAMPAIGN UTILITIES
# ==========================================

def calculate_campaign_metrics(campaign_data: Dict[str, Any]) -> Dict[str, float]:
    """Calcular métricas de campaña"""
    total_targets = campaign_data.get("total_targets", 0)
    sent_count = campaign_data.get("sent_count", 0)
    reply_count = campaign_data.get("reply_count", 0)
    accepted_count = campaign_data.get("accepted_count", 0)
    
    # Evitar división por cero
    response_rate = 0.0
    acceptance_rate = 0.0
    conversion_rate = 0.0
    
    if sent_count > 0:
        response_rate = round((reply_count / sent_count) * 100, 2)
        acceptance_rate = round((accepted_count / sent_count) * 100, 2)
    
    if total_targets > 0:
        conversion_rate = round((reply_count / total_targets) * 100, 2)
    
    return {
        "response_rate": response_rate,
        "acceptance_rate": acceptance_rate,
        "conversion_rate": conversion_rate,
        "total_targets": total_targets,
        "sent_count": sent_count,
        "reply_count": reply_count,
        "accepted_count": accepted_count
    }

def get_campaign_status_color(status: str) -> str:
    """Obtener color para estado de campaña"""
    colors = {
        "draft": "gray",
        "active": "green",
        "paused": "yellow",
        "completed": "blue",
        "error": "red"
    }
    return colors.get(status, "gray")

# ==========================================
# TARGET UTILITIES
# ==========================================

def format_target_response(target_data: Dict[str, Any]) -> Dict[str, Any]:
    """Formatear respuesta de target"""
    return {
        "id": target_data["id"],
        "investor_name": target_data.get("linkedin_name", "Unknown"),
        "linkedin_url": target_data.get("linkedin_profile_url"),
        "personalized_message": target_data["personalized_message"],
        "status": target_data["status"],
        "sent_at": target_data.get("sent_at"),
        "replied_at": target_data.get("replied_at"),
        "relevance_score": target_data.get("relevance_score", 0.0),
        "character_count": target_data.get("message_character_count", 0)
    }

def get_target_status_icon(status: str) -> str:
    """Obtener icono para estado de target"""
    icons = {
        "pending": "⏳",
        "sent": "✉️",
        "replied": "💬",
        "accepted": "✅",
        "failed": "❌",
        "skipped": "⏭️"
    }
    return icons.get(status, "❓")

# ==========================================
# LINKEDIN UTILITIES
# ==========================================

def format_linkedin_account_response(account_data: Dict[str, Any]) -> Dict[str, Any]:
    """Formatear respuesta de cuenta de LinkedIn"""
    return {
        "id": account_data["id"],
        "unipile_account_id": account_data["unipile_account_id"],
        "account_name": account_data.get("account_name"),
        "account_email": account_data.get("account_email"),
        "account_type": account_data.get("account_type", "classic"),
        "status": account_data["status"],
        "last_sync": account_data.get("last_sync"),
        "error_message": account_data.get("error_message"),
        "created_at": account_data["created_at"],
        "is_connected": account_data["status"] == "connected"
    }

def validate_linkedin_provider_id(provider_id: str) -> bool:
    """Validar LinkedIn provider ID"""
    # LinkedIn provider IDs suelen tener un formato específico
    return provider_id and len(provider_id) > 0

# ==========================================
# ANALYTICS UTILITIES
# ==========================================

def calculate_time_series_data(data: list, date_field: str, value_field: str, days: int = 30) -> Dict[str, Any]:
    """Calcular datos de serie temporal"""
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    # Crear diccionario con los últimos N días
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    daily_data = defaultdict(int)
    
    # Inicializar todos los días con 0
    current_date = start_date
    while current_date <= end_date:
        date_key = current_date.strftime("%Y-%m-%d")
        daily_data[date_key] = 0
        current_date += timedelta(days=1)
    
    # Agregar datos reales
    for item in data:
        if date_field in item:
            item_date = datetime.fromisoformat(item[date_field].replace("Z", "+00:00"))
            if start_date <= item_date <= end_date:
                date_key = item_date.strftime("%Y-%m-%d")
                daily_data[date_key] += item.get(value_field, 1)
    
    # Convertir a listas ordenadas
    dates = sorted(daily_data.keys())
    values = [daily_data[date] for date in dates]
    
    return {
        "dates": dates,
        "values": values,
        "total": sum(values),
        "average": sum(values) / len(values) if values else 0
    }

# ==========================================
# SECURITY UTILITIES
# ==========================================

def sanitize_user_input(text: str, max_length: int = 1000) -> str:
    """Sanitizar entrada del usuario"""
    if not text:
        return ""
    
    # Remover caracteres peligrosos
    dangerous_chars = ["<", ">", "&", "\"", "'", "\x00"]
    for char in dangerous_chars:
        text = text.replace(char, "")
    
    # Limitar longitud
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()

def validate_uuid_parameter(uuid_str: str, param_name: str = "ID") -> UUID:
    """Validar parámetro UUID"""
    try:
        return UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {param_name} format. Must be a valid UUID."
        )

# ==========================================
# RATE LIMITING UTILITIES
# ==========================================

def check_daily_limits(user_id: UUID, operation: str) -> bool:
    """Verificar límites diarios del usuario"""
    # En una implementación completa, esto consultaría Redis o base de datos
    # Por ahora retornar True
    return True

def get_user_tier_limits(user_plan: str) -> Dict[str, int]:
    """Obtener límites según el plan del usuario"""
    limits = {
        "free": {
            "campaigns_per_month": 1,
            "targets_per_campaign": 50,
            "daily_sends": 20
        },
        "pro": {
            "campaigns_per_month": 5,
            "targets_per_campaign": 200,
            "daily_sends": 80
        },
        "enterprise": {
            "campaigns_per_month": -1,  # unlimited
            "targets_per_campaign": -1,
            "daily_sends": 200
        }
    }
    
    return limits.get(user_plan, limits["free"])

# ==========================================
# LOGGING UTILITIES
# ==========================================

def log_user_action(user_id: UUID, action: str, details: Dict[str, Any] = None):
    """Loguear acción del usuario"""
    log_data = {
        "user_id": str(user_id),
        "action": action,
        "timestamp": datetime.now().isoformat()
    }
    
    if details:
        log_data["details"] = details
    
    logger.info(f"User action: {action} by {user_id}", extra=log_data)

# ==========================================
# FEATURE FLAGS
# ==========================================

def is_feature_enabled(feature_name: str, user_id: UUID = None) -> bool:
    """Verificar si una feature está habilitada"""
    # Feature flags básicos desde variables de entorno
    feature_flags = {
        "linkedin_outreach": os.getenv("ENABLE_LINKEDIN_OUTREACH", "true").lower() == "true",
        "ai_message_generation": os.getenv("ENABLE_AI_MESSAGES", "true").lower() == "true",
        "advanced_analytics": os.getenv("ENABLE_ADVANCED_ANALYTICS", "false").lower() == "true",
        "auto_follow_up": os.getenv("ENABLE_AUTO_FOLLOW_UP", "false").lower() == "true"
    }
    
    return feature_flags.get(feature_name, False)
