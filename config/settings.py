import os
from typing import List, Optional
from pydantic import BaseSettings, validator
from functools import lru_cache

class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # ==========================================
    # CONFIGURACIÓN BÁSICA
    # ==========================================
    PROJECT_NAME: str = "0Bullshit Backend"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # ==========================================
    # BASE DE DATOS
    # ==========================================
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    @validator("SUPABASE_URL")
    def validate_supabase_url(cls, v):
        if not v or not v.startswith("https://"):
            raise ValueError("SUPABASE_URL must be a valid HTTPS URL")
        return v
    
    # ==========================================
    # APIS EXTERNAS
    # ==========================================
    GEMINI_API_KEY: str
    UNIPILE_API_KEY: Optional[str] = None
    UNIPILE_DSN: Optional[str] = None
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    @validator("GEMINI_API_KEY")
    def validate_gemini_key(cls, v):
        if not v or len(v) < 20:
            raise ValueError("GEMINI_API_KEY must be provided and valid")
        return v
    
    # ==========================================
    # SEGURIDAD
    # ==========================================
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    @validator("JWT_SECRET_KEY")
    def validate_jwt_secret(cls, v):
        if not v or len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return v
    
    # ==========================================
    # CORS
    # ==========================================
    CORS_ORIGINS: List[str] = ["*"]  # En producción, especificar dominios
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # ==========================================
    # CHAT CONFIGURATION
    # ==========================================
    
    # Gemini settings
    GEMINI_TEMPERATURE: float = 0.7
    GEMINI_TOP_P: float = 0.9
    GEMINI_TOP_K: int = 40
    GEMINI_MAX_OUTPUT_TOKENS: int = 3000
    
    # Chat limits
    MAX_MESSAGE_LENGTH: int = 10000
    MAX_CONVERSATION_HISTORY: int = 50
    MAX_PROJECTS_PER_USER: int = 50
    
    # Search settings
    MAX_INVESTOR_RESULTS: int = 15
    MAX_COMPANY_RESULTS: int = 10
    SEARCH_CACHE_TTL_MINUTES: int = 30
    
    # Completeness scoring
    CATEGORIES_WEIGHT: float = 0.25
    STAGE_WEIGHT: float = 0.25
    METRICS_WEIGHT: float = 0.15
    TEAM_WEIGHT: float = 0.10
    PROBLEM_WEIGHT: float = 0.10
    PRODUCT_WEIGHT: float = 0.10
    FUNDING_WEIGHT: float = 0.05
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 30
    RATE_LIMIT_WINDOW_MINUTES: int = 1
    
    # WebSocket settings
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 1000
    
    # ==========================================
    # FEATURES FLAGS
    # ==========================================
    ENABLE_LIBRARIAN_BOT: bool = True
    ENABLE_WELCOME_MESSAGES: bool = True
    ENABLE_ANTI_SPAM: bool = True
    ENABLE_SEARCH_CACHING: bool = True
    ENABLE_WEBSOCKETS: bool = True
    ENABLE_RATE_LIMITING: bool = True
    
    # ==========================================
    # LOGGING
    # ==========================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = None
    
    # ==========================================
    # EXTERNAL SERVICES
    # ==========================================
    
    # Email settings (para futuro)
    SENDGRID_API_KEY: Optional[str] = None
    FROM_EMAIL: str = "noreply@0bullshit.com"
    
    # Redis (para futuro)
    REDIS_URL: Optional[str] = None
    
    # Monitoring (para futuro)
    SENTRY_DSN: Optional[str] = None
    
    # ==========================================
    # BUSINESS LOGIC SETTINGS
    # ==========================================
    
    # Y-Combinator principles toggle
    ENABLE_YC_PRINCIPLES: bool = True
    
    # Anti-spam configuration
    SPAM_DETECTION_THRESHOLD: float = 0.8
    MIN_MESSAGE_LENGTH: int = 3
    MAX_REPEATED_CHARS: int = 5
    
    # Judge system thresholds
    SEARCH_INVESTORS_THRESHOLD: float = 70.0
    SEARCH_COMPANIES_THRESHOLD: float = 70.0
    ASK_QUESTIONS_THRESHOLD: float = 50.0
    ANTI_SPAM_THRESHOLD: float = 80.0
    
    # Completeness thresholds
    MIN_COMPLETENESS_FOR_SEARCH: float = 0.5
    RECOMMEND_QUESTIONS_THRESHOLD: float = 0.7
    
    # Search relevance
    MIN_INVESTOR_RELEVANCE: float = 0.3
    MIN_COMPANY_RELEVANCE: float = 0.2
    
    # ==========================================
    # VALIDATION
    # ==========================================
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()
    
    @validator("CORS_ORIGINS")
    def validate_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # ==========================================
    # COMPUTED PROPERTIES
    # ==========================================
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def database_url(self) -> str:
        return self.SUPABASE_URL
    
    @property
    def gemini_config(self) -> dict:
        return {
            "temperature": self.GEMINI_TEMPERATURE,
            "top_p": self.GEMINI_TOP_P,
            "top_k": self.GEMINI_TOP_K,
            "max_output_tokens": self.GEMINI_MAX_OUTPUT_TOKENS,
        }
    
    @property
    def completeness_weights(self) -> dict:
        return {
            "categories": self.CATEGORIES_WEIGHT,
            "stage": self.STAGE_WEIGHT,
            "metrics": self.METRICS_WEIGHT,
            "team_info": self.TEAM_WEIGHT,
            "problem_solved": self.PROBLEM_WEIGHT,
            "product_status": self.PRODUCT_WEIGHT,
            "previous_funding": self.FUNDING_WEIGHT,
        }
    
    @property
    def judge_thresholds(self) -> dict:
        return {
            "search_investors": self.SEARCH_INVESTORS_THRESHOLD,
            "search_companies": self.SEARCH_COMPANIES_THRESHOLD,
            "ask_questions": self.ASK_QUESTIONS_THRESHOLD,
            "anti_spam": self.ANTI_SPAM_THRESHOLD,
        }
    
    # ==========================================
    # CONFIGURACIÓN DE CLASE
    # ==========================================
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# ==========================================
# CONFIGURACIONES POR AMBIENTE
# ==========================================

class DevelopmentSettings(Settings):
    """Configuración para desarrollo"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    ENABLE_RATE_LIMITING: bool = False

class ProductionSettings(Settings):
    """Configuración para producción"""
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    CORS_ORIGINS: List[str] = [
        "https://app.0bullshit.com",
        "https://0bullshit.com"
    ]

class TestingSettings(Settings):
    """Configuración para testing"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    ENABLE_RATE_LIMITING: bool = False
    ENABLE_WEBSOCKETS: bool = False

# ==========================================
# FACTORY FUNCTION
# ==========================================

@lru_cache()
def get_settings() -> Settings:
    """Factory function para obtener settings basado en ENVIRONMENT"""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "development":
        return DevelopmentSettings()
    elif environment == "production":
        return ProductionSettings()
    elif environment == "testing":
        return TestingSettings()
    else:
        return Settings()

# Instancia global
settings = get_settings()

# ==========================================
# VALIDATION HELPERS
# ==========================================

def validate_settings() -> bool:
    """Validar que todas las configuraciones críticas estén presentes"""
    try:
        settings = get_settings()
        
        # Verificar configuraciones críticas
        critical_settings = [
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY,
            settings.GEMINI_API_KEY,
            settings.JWT_SECRET_KEY
        ]
        
        if not all(critical_settings):
            return False
        
        return True
        
    except Exception:
        return False

def get_feature_flags() -> dict:
    """Obtener feature flags activos"""
    return {
        "librarian_bot": settings.ENABLE_LIBRARIAN_BOT,
        "welcome_messages": settings.ENABLE_WELCOME_MESSAGES,
        "anti_spam": settings.ENABLE_ANTI_SPAM,
        "search_caching": settings.ENABLE_SEARCH_CACHING,
        "websockets": settings.ENABLE_WEBSOCKETS,
        "rate_limiting": settings.ENABLE_RATE_LIMITING,
        "yc_principles": settings.ENABLE_YC_PRINCIPLES,
    }
