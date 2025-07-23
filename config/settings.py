"""
Configuration settings for 0Bullshit backend application.
Loads environment variables and provides default values.
"""

import os
from typing import Optional

# ==========================================
# ENVIRONMENT DETECTION
# ==========================================

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"

# ==========================================
# DATABASE CONFIGURATION
# ==========================================

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # anon key
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # service_role key for admin operations

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

# ==========================================
# JWT CONFIGURATION
# ==========================================

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    if DEBUG:
        JWT_SECRET_KEY = "dev-secret-key-change-in-production"
    else:
        raise ValueError("JWT_SECRET_KEY must be set in production")

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# ==========================================
# AI CONFIGURATION
# ==========================================

# Google Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY must be set in environment variables")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

# ==========================================
# PAYMENT CONFIGURATION
# ==========================================

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if not STRIPE_SECRET_KEY:
    if not DEBUG:
        raise ValueError("STRIPE_SECRET_KEY must be set in production")

# Stripe Product/Price IDs
STRIPE_PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO")
STRIPE_PRICE_ID_OUTREACH = os.getenv("STRIPE_PRICE_ID_OUTREACH")
STRIPE_PRICE_ID_CREDITS_100 = os.getenv("STRIPE_PRICE_ID_CREDITS_100")
STRIPE_PRICE_ID_CREDITS_500 = os.getenv("STRIPE_PRICE_ID_CREDITS_500")

# ==========================================
# LINKEDIN AUTOMATION CONFIGURATION
# ==========================================

# Unipile Configuration
UNIPILE_API_KEY = os.getenv("UNIPILE_API_KEY")
UNIPILE_BASE_URL = os.getenv("UNIPILE_BASE_URL", "https://api.unipile.com/v1")

if not UNIPILE_API_KEY:
    if not DEBUG:
        raise ValueError("UNIPILE_API_KEY must be set in production")

# ==========================================
# APPLICATION CONFIGURATION
# ==========================================

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", "8000"))  # Render uses PORT env var
API_WORKERS = int(os.getenv("API_WORKERS", "1"))

# CORS Configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
ALLOWED_ORIGINS = [
    FRONTEND_URL,
    "http://localhost:3000",
    "http://localhost:3001",
    "https://your-production-domain.com"  # Update with actual production domain
]

# ==========================================
# RATE LIMITING CONFIGURATION
# ==========================================

# Credit System Configuration
DEFAULT_FREE_CREDITS = int(os.getenv("DEFAULT_FREE_CREDITS", "200"))
DEFAULT_DAILY_CREDIT_LIMIT_FREE = int(os.getenv("DEFAULT_DAILY_CREDIT_LIMIT_FREE", "50"))
DEFAULT_DAILY_CREDIT_LIMIT_PRO = int(os.getenv("DEFAULT_DAILY_CREDIT_LIMIT_PRO", "150"))
DEFAULT_DAILY_CREDIT_LIMIT_OUTREACH = int(os.getenv("DEFAULT_DAILY_CREDIT_LIMIT_OUTREACH", "200"))

# LinkedIn Rate Limits (per day)
LINKEDIN_CONNECTION_LIMIT_PER_DAY = int(os.getenv("LINKEDIN_CONNECTION_LIMIT_PER_DAY", "100"))
LINKEDIN_MESSAGE_LIMIT_PER_DAY = int(os.getenv("LINKEDIN_MESSAGE_LIMIT_PER_DAY", "50"))

# ==========================================
# AI AGENT CONFIGURATION
# ==========================================

# Upselling System Configuration
UPSELL_MAX_ATTEMPTS_PER_DAY = int(os.getenv("UPSELL_MAX_ATTEMPTS_PER_DAY", "3"))
UPSELL_COOLDOWN_HOURS = int(os.getenv("UPSELL_COOLDOWN_HOURS", "4"))
UPSELL_MIN_CONFIDENCE = float(os.getenv("UPSELL_MIN_CONFIDENCE", "0.7"))

# ==========================================
# LOGGING CONFIGURATION
# ==========================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ==========================================
# EMAIL CONFIGURATION (Optional)
# ==========================================

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM_ADDRESS = os.getenv("EMAIL_FROM_ADDRESS", "noreply@0bullshit.com")

# ==========================================
# WEBSOCKET CONFIGURATION
# ==========================================

WEBSOCKET_HEARTBEAT_INTERVAL = int(os.getenv("WEBSOCKET_HEARTBEAT_INTERVAL", "30"))
WEBSOCKET_MAX_CONNECTIONS_PER_USER = int(os.getenv("WEBSOCKET_MAX_CONNECTIONS_PER_USER", "5"))

# ==========================================
# CACHE CONFIGURATION
# ==========================================

# Redis Configuration (optional for caching)
REDIS_URL = os.getenv("REDIS_URL")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour

# ==========================================
# SECURITY CONFIGURATION
# ==========================================

# Password Requirements
MIN_PASSWORD_LENGTH = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))
MAX_PASSWORD_LENGTH = int(os.getenv("MAX_PASSWORD_LENGTH", "128"))

# Session Configuration
SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
REFRESH_TOKEN_LIFETIME_DAYS = int(os.getenv("REFRESH_TOKEN_LIFETIME_DAYS", "30"))

# API Rate Limiting
API_RATE_LIMIT_PER_MINUTE = int(os.getenv("API_RATE_LIMIT_PER_MINUTE", "60"))
API_RATE_LIMIT_PER_HOUR = int(os.getenv("API_RATE_LIMIT_PER_HOUR", "1000"))

# ==========================================
# FEATURE FLAGS
# ==========================================

# Enable/Disable Features
ENABLE_REGISTRATION = os.getenv("ENABLE_REGISTRATION", "true").lower() == "true"
ENABLE_PASSWORD_RESET = os.getenv("ENABLE_PASSWORD_RESET", "true").lower() == "true"
ENABLE_LINKEDIN_AUTOMATION = os.getenv("ENABLE_LINKEDIN_AUTOMATION", "true").lower() == "true"
ENABLE_UPSELLING = os.getenv("ENABLE_UPSELLING", "true").lower() == "true"
ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS", "true").lower() == "true"

# ==========================================
# PLAN CONFIGURATIONS
# ==========================================

PLAN_LIMITS = {
    "free": {
        "credits": DEFAULT_FREE_CREDITS,
        "daily_credits": DEFAULT_DAILY_CREDIT_LIMIT_FREE,
        "projects": 1,
        "monthly_price": 0,
        "features": [
            "Basic AI Chat",
            "Limited Investor Search",
            "Basic Analytics"
        ]
    },
    "pro": {
        "credits": -1,  # Unlimited
        "daily_credits": DEFAULT_DAILY_CREDIT_LIMIT_PRO,
        "projects": 5,
        "monthly_price": 19,
        "features": [
            "Unlimited AI Chat",
            "Advanced Investor Search",
            "Full Analytics",
            "Priority Support"
        ]
    },
    "outreach": {
        "credits": -1,  # Unlimited
        "daily_credits": DEFAULT_DAILY_CREDIT_LIMIT_OUTREACH,
        "projects": -1,  # Unlimited
        "monthly_price": 49,
        "features": [
            "Everything in Pro",
            "LinkedIn Automation",
            "Outreach Campaigns",
            "Custom Message Generation",
            "Advanced Analytics"
        ]
    }
}

# ==========================================
# API ENDPOINTS CONFIGURATION
# ==========================================

# External API Endpoints
UNIPILE_LINKEDIN_CONNECT_URL = f"{UNIPILE_BASE_URL}/linkedin/connect"
UNIPILE_LINKEDIN_MESSAGE_URL = f"{UNIPILE_BASE_URL}/linkedin/message"
UNIPILE_LINKEDIN_PROFILE_URL = f"{UNIPILE_BASE_URL}/linkedin/profile"

# ==========================================
# VALIDATION FUNCTIONS
# ==========================================

def validate_environment() -> None:
    """Validate that all required environment variables are set"""
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "GEMINI_API_KEY"
    ]
    
    if not DEBUG:
        required_vars.extend([
            "JWT_SECRET_KEY",
            "STRIPE_SECRET_KEY",
            "UNIPILE_API_KEY"
        ])
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

def get_plan_limits(plan: str) -> dict:
    """Get limits for a specific plan"""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

def is_feature_enabled(feature: str) -> bool:
    """Check if a feature is enabled"""
    feature_flags = {
        "registration": ENABLE_REGISTRATION,
        "password_reset": ENABLE_PASSWORD_RESET,
        "linkedin_automation": ENABLE_LINKEDIN_AUTOMATION,
        "upselling": ENABLE_UPSELLING,
        "analytics": ENABLE_ANALYTICS
    }
    return feature_flags.get(feature, False)

# ==========================================
# INITIALIZE VALIDATION
# ==========================================

if __name__ == "__main__":
    try:
        validate_environment()
        print("✅ All environment variables are properly configured")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        exit(1)
else:
    # Validate environment when module is imported
    try:
        validate_environment()
    except ValueError as e:
        if not DEBUG:
            raise e
        else:
            print(f"⚠️  Development mode warning: {e}")
