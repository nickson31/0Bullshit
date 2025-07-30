"""
Configuration settings for 0BullshitIntelligence microservice.
Manages environment variables, database connections, and AI configurations.
"""

import os
from typing import Optional, List
from pydantic import BaseSettings, validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # ==========================================
    # APPLICATION SETTINGS
    # ==========================================
    app_name: str = "0BullshitIntelligence"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # ==========================================
    # DATABASE CONFIGURATION
    # ==========================================
    
    # Primary Supabase instance (for this microservice)
    supabase_url: str
    supabase_key: str  # anon key
    supabase_service_key: Optional[str] = None  # service role key for admin operations
    
    # Sync Supabase instance (main repository database)
    sync_supabase_url: Optional[str] = None
    sync_supabase_key: Optional[str] = None
    sync_enabled: bool = True
    
    @validator("supabase_url", "supabase_key")
    def validate_required_supabase(cls, v):
        if not v:
            raise ValueError("Supabase URL and KEY are required")
        return v
    
    # ==========================================
    # AI CONFIGURATION
    # ==========================================
    
    # Google Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash"
    gemini_temperature: float = 0.7
    gemini_max_tokens: int = 3000
    
    @validator("gemini_api_key")
    def validate_gemini_key(cls, v):
        if not v:
            raise ValueError("Gemini API key is required")
        return v
    
    # ==========================================
    # AUTHENTICATION & SECURITY
    # ==========================================
    
    # JWT Configuration
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Service-to-service authentication
    service_api_key: Optional[str] = None  # For main repository communication
    
    # ==========================================
    # API CONFIGURATION
    # ==========================================
    
    # CORS settings
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://localhost:8000",
        "http://localhost:8001"
    ]
    
    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    
    # ==========================================
    # SEARCH ENGINE CONFIGURATION
    # ==========================================
    
    # Investor search settings
    min_angel_score: float = 40.0
    min_employee_score: float = 5.9
    default_search_limit: int = 15
    max_search_limit: int = 50
    
    # Company search settings
    company_search_limit: int = 10
    max_company_search_limit: int = 30
    
    # ==========================================
    # AI SYSTEM CONFIGURATION
    # ==========================================
    
    # Language detection
    default_language: str = "spanish"
    supported_languages: List[str] = ["spanish", "english"]
    
    # Anti-spam system
    spam_threshold: int = 70
    spam_cache_ttl: int = 3600  # 1 hour
    
    # Upselling system
    upsell_max_attempts_per_day: int = 3
    upsell_cooldown_hours: int = 4
    upsell_min_confidence: float = 0.7
    
    # Welcome system
    onboarding_stages_required: int = 3
    welcome_message_cache_ttl: int = 1800  # 30 minutes
    
    # ==========================================
    # WEBSOCKET CONFIGURATION
    # ==========================================
    
    websocket_heartbeat_interval: int = 30
    websocket_max_connections_per_user: int = 5
    websocket_message_queue_size: int = 100
    
    # ==========================================
    # LOGGING CONFIGURATION
    # ==========================================
    
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[str] = None
    
    # ==========================================
    # PERFORMANCE CONFIGURATION
    # ==========================================
    
    # Background tasks
    librarian_queue_size: int = 1000
    librarian_batch_size: int = 10
    librarian_process_interval: int = 5  # seconds
    
    # Caching
    cache_ttl_default: int = 3600  # 1 hour
    cache_ttl_search_results: int = 1800  # 30 minutes
    cache_ttl_user_context: int = 600  # 10 minutes
    
    # ==========================================
    # TESTING INTERFACE CONFIGURATION
    # ==========================================
    
    testing_interface_enabled: bool = True
    testing_auth_required: bool = False
    testing_max_concurrent_sessions: int = 50
    
    # ==========================================
    # MONITORING & ANALYTICS
    # ==========================================
    
    metrics_enabled: bool = True
    analytics_batch_size: int = 100
    analytics_flush_interval: int = 300  # 5 minutes
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Environment variable prefixes
        env_prefix = ""
        
        # Field aliases for environment variables
        fields = {
            "supabase_url": {"env": "SUPABASE_URL"},
            "supabase_key": {"env": "SUPABASE_KEY"},
            "supabase_service_key": {"env": "SUPABASE_SERVICE_KEY"},
            "sync_supabase_url": {"env": "SYNC_SUPABASE_URL"},
            "sync_supabase_key": {"env": "SYNC_SUPABASE_KEY"},
            "gemini_api_key": {"env": "GEMINI_API_KEY"},
            "jwt_secret_key": {"env": "JWT_SECRET_KEY"},
            "service_api_key": {"env": "SERVICE_API_KEY"},
            "environment": {"env": "ENVIRONMENT"},
            "debug": {"env": "DEBUG"},
            "host": {"env": "HOST"},
            "port": {"env": "PORT"},
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenient access to settings
settings = get_settings()


# ==========================================
# VALIDATION FUNCTIONS
# ==========================================

def validate_environment() -> None:
    """Validate that all required environment variables are set"""
    try:
        settings = get_settings()
        
        # Test critical connections
        if not settings.supabase_url or not settings.supabase_key:
            raise ValueError("Supabase configuration is incomplete")
            
        if not settings.gemini_api_key:
            raise ValueError("Gemini API key is required")
            
        print("✅ Environment validation successful")
        
    except Exception as e:
        print(f"❌ Environment validation failed: {e}")
        raise


def get_database_url() -> str:
    """Get the database URL for async connections"""
    return settings.supabase_url.replace("https://", "postgresql://postgres:")


# ==========================================
# FEATURE FLAGS
# ==========================================

class FeatureFlags:
    """Feature flags for enabling/disabling functionality"""
    
    @staticmethod
    def is_sync_enabled() -> bool:
        return settings.sync_enabled and settings.sync_supabase_url is not None
    
    @staticmethod
    def is_testing_interface_enabled() -> bool:
        return settings.testing_interface_enabled
    
    @staticmethod
    def is_metrics_enabled() -> bool:
        return settings.metrics_enabled
    
    @staticmethod
    def is_debug_mode() -> bool:
        return settings.debug or settings.environment == "development"


# Convenient access to feature flags
features = FeatureFlags()