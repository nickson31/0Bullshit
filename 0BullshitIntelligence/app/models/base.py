"""
Base models and mixins for 0BullshitIntelligence microservice.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel as PydanticBaseModel, Field
from enum import Enum


class BaseModel(PydanticBaseModel):
    """Base model with common configuration"""
    
    class Config:
        # Enable JSON serialization for UUID and datetime
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        # Allow population by field name or alias
        allow_population_by_field_name = True
        # Validate assignments to ensure data integrity
        validate_assignment = True
        # Use enum values instead of names
        use_enum_values = True


class TimestampMixin(BaseModel):
    """Mixin for models that need timestamp fields"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class UUIDMixin(BaseModel):
    """Mixin for models that need UUID primary keys"""
    id: UUID = Field(default_factory=uuid4)


# ==========================================
# ENUM DEFINITIONS
# ==========================================

class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"
    OUTREACH = "outreach"


class ProjectStage(str, Enum):
    IDEA = "idea"
    PROTOTYPE = "prototype"
    MVP = "mvp"
    EARLY_REVENUE = "early_revenue"
    GROWTH = "growth"
    SCALE = "scale"


class ProjectCategory(str, Enum):
    FINTECH = "fintech"
    HEALTHTECH = "healthtech"
    EDTECH = "edtech"
    PROPTECH = "proptech"
    RETAIL = "retail"
    SAAS = "saas"
    MARKETPLACE = "marketplace"
    SOCIAL = "social"
    GAMING = "gaming"
    AI = "ai"
    OTHER = "other"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Language(str, Enum):
    SPANISH = "spanish"
    ENGLISH = "english"
    OTHER = "other"


class SearchType(str, Enum):
    INVESTORS = "investors"
    COMPANIES = "companies"
    HYBRID = "hybrid"


# ==========================================
# RESPONSE MODELS
# ==========================================

class ResponseModel(BaseModel):
    """Base response model"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class SuccessResponse(ResponseModel):
    """Standard success response"""
    success: bool = True


class ErrorResponse(ResponseModel):
    """Standard error response"""
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class PaginatedResponse(ResponseModel):
    """Paginated response model"""
    page: int = 1
    page_size: int = 20
    total_count: int = 0
    total_pages: int = 0
    has_next: bool = False
    has_previous: bool = False


# ==========================================
# METRICS AND ANALYTICS
# ==========================================

class PerformanceMetrics(BaseModel):
    """Performance metrics for operations"""
    duration_ms: float
    start_time: datetime
    end_time: datetime
    success: bool = True
    error_message: Optional[str] = None


class AIMetrics(BaseModel):
    """Metrics specific to AI operations"""
    system_name: str
    model_used: str
    token_count: Optional[int] = None
    confidence_score: Optional[float] = None
    temperature: Optional[float] = None


class SearchMetrics(BaseModel):
    """Metrics for search operations"""
    search_type: str
    results_count: int
    filters_applied: Optional[Dict[str, Any]] = None
    total_available: Optional[int] = None


# ==========================================
# VALIDATION HELPERS
# ==========================================

def validate_uuid(value: str) -> UUID:
    """Validate and convert string to UUID"""
    try:
        return UUID(value)
    except ValueError:
        raise ValueError(f"Invalid UUID format: {value}")


def validate_email(value: str) -> str:
    """Basic email validation"""
    if "@" not in value or "." not in value.split("@")[-1]:
        raise ValueError(f"Invalid email format: {value}")
    return value.lower()


def validate_language(value: str) -> Language:
    """Validate language code"""
    try:
        return Language(value.lower())
    except ValueError:
        return Language.OTHER