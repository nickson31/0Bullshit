"""
Pydantic models and schemas for 0Bullshit backend API.
Contains request/response models for all endpoints.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from enum import Enum

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

class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

class OutreachStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    CONNECTED = "connected"
    RESPONDED = "responded"
    NOT_INTERESTED = "not_interested"
    ERROR = "error"

# ==========================================
# BASIC RESPONSE MODELS
# ==========================================

class MessageResponse(BaseModel):
    """Standard message response"""
    message: str

class ApiResponse(BaseModel):
    """Generic API response with optional data"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str

class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str
    detail: Optional[str] = None

# ==========================================
# PROJECT DATA MODELS (NUEVOS)
# ==========================================

class ProjectMetrics(BaseModel):
    """Project metrics model"""
    arr: Optional[str] = None
    mrr: Optional[str] = None
    users: Optional[str] = None
    revenue: Optional[str] = None
    growth_rate: Optional[str] = None

class TeamInfo(BaseModel):
    """Team information model"""
    size: Optional[int] = None
    roles: Optional[List[str]] = None
    experience: Optional[str] = None
    previous_companies: Optional[List[str]] = None

class ProjectData(BaseModel):
    """Complete project data model"""
    categories: Optional[List[str]] = None
    stage: Optional[str] = None
    metrics: Optional[ProjectMetrics] = None
    team_info: Optional[TeamInfo] = None
    problem_solved: Optional[str] = None
    product_status: Optional[str] = None
    previous_funding: Optional[str] = None
    additional_fields: Optional[Dict[str, Any]] = None

# ==========================================
# JUDGE SYSTEM MODELS (NUEVOS)
# ==========================================

class JudgeProbabilities(BaseModel):
    """Judge decision probabilities"""
    search_investors: float
    search_companies: float
    mentoring: float
    ask_questions: float
    anti_spam: float

class ExtractedData(BaseModel):
    """Data extracted by the judge"""
    categories: Optional[List[str]] = None
    stage: Optional[str] = None
    metrics: Optional[Dict[str, str]] = None
    team_info: Optional[Dict[str, Any]] = None
    problem_solved: Optional[str] = None
    product_status: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

class JudgeDecision(BaseModel):
    """Judge decision model"""
    probabilities: JudgeProbabilities
    decision: str
    reasoning: str
    confidence_score: float
    required_questions: Optional[List[str]] = None
    extracted_data: Optional[ExtractedData] = None
    completeness_score: float
    should_ask_questions: bool
    anti_spam_triggered: bool

# ==========================================
# SEARCH MODELS (ACTUALIZADOS)
# ==========================================

class InvestorResult(BaseModel):
    """Investor search result"""
    id: UUID
    full_name: str
    headline: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_name: Optional[str] = None
    fund_name: Optional[str] = None
    relevance_score: float
    categories_match: Optional[List[str]] = None
    stage_match: Optional[bool] = None

class CompanyResult(BaseModel):
    """Company search result"""
    nombre: str
    descripcion_corta: Optional[str] = None
    web_empresa: Optional[str] = None
    sector_categorias: Optional[str] = None
    service_category: Optional[str] = None
    startup_relevance_score: Optional[float] = None

class SearchResults(BaseModel):
    """Search results container"""
    investors: Optional[List[InvestorResult]] = None
    companies: Optional[List[CompanyResult]] = None
    total_found: int
    search_criteria: Dict[str, Any]

class SearchProgress(BaseModel):
    """Search progress model"""
    status: str
    message: str
    progress_percentage: int
    current_step: Optional[str] = None

# ==========================================
# USER MODELS
# ==========================================

class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    name: str

class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=8, max_length=128)

class UserUpdate(BaseModel):
    """User update model"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None

class UserResponse(BaseModel):
    """User response model"""
    id: UUID
    email: str
    name: str
    plan: PlanType
    credits: int
    daily_credits_remaining: int
    onboarding_completed: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

class UserProfile(UserResponse):
    """Extended user profile with additional info"""
    stripe_customer_id: Optional[str] = None
    last_login: Optional[datetime] = None
    total_projects: int = 0
    total_conversations: int = 0

# ==========================================
# PROJECT MODELS
# ==========================================

class ProjectBase(BaseModel):
    """Base project model"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    """Project creation model"""
    stage: Optional[str] = None
    category: Optional[str] = None
    business_model: Optional[str] = None
    revenue_model: Optional[str] = None
    target_market: Optional[str] = None
    funding_amount: Optional[str] = None
    current_revenue: Optional[str] = None
    projected_revenue: Optional[str] = None
    team_size: Optional[int] = None
    key_metrics: Optional[Dict[str, Any]] = None
    achievements: Optional[str] = None
    problem_solving: Optional[str] = None

class Project(BaseModel):
    """Complete project model"""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    categories: Optional[List[str]] = None
    stage: Optional[str] = None
    project_data: ProjectData
    context_summary: Optional[str] = None
    last_context_update: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

# ==========================================
# CONVERSATION & MESSAGE MODELS
# ==========================================

class ChatMessage(BaseModel):
    """Chat message model"""
    message: str
    conversation_id: Optional[str] = None
    project_id: Optional[str] = None

class ChatResponse(BaseModel):
    """Chat response model"""
    id: UUID
    project_id: UUID
    role: str
    content: str
    ai_extractions: Optional[Dict[str, Any]] = None
    gemini_prompt_used: Optional[str] = None
    gemini_response_raw: Optional[str] = None
    created_at: datetime

class ChatConversation(BaseModel):
    """Chat conversation model"""
    id: UUID
    project_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

# ==========================================
# COMPLETENESS MODELS (NUEVOS)
# ==========================================

class CompletenessResponse(BaseModel):
    """Project completeness response"""
    score: float
    missing_fields: List[str]
    required_fields: List[str]
    suggestions: List[str]
    breakdown: Dict[str, float]

# ==========================================
# WELCOME SYSTEM MODELS (NUEVOS)
# ==========================================

class WelcomeMessage(BaseModel):
    """Welcome message model"""
    type: str
    stage: str
    message: str
    next_actions: Optional[List[Dict[str, Any]]] = None
    progress: Optional[Dict[str, Any]] = None

# ==========================================
# LIBRARIAN MODELS (NUEVOS)
# ==========================================

class LibrarianUpdate(BaseModel):
    """Librarian update model"""
    project_id: UUID
    conversation_id: UUID
    updates_made: Dict[str, Any]
    confidence_score: float
    reasoning: str

# ==========================================
# OUTREACH MODELS
# ==========================================

class OutreachCampaign(BaseModel):
    """Outreach campaign model"""
    id: UUID
    user_id: UUID
    project_id: Optional[UUID] = None
    name: str
    status: str
    total_targets: int
    sent_count: int
    reply_count: int
    created_at: datetime

class OutreachTarget(BaseModel):
    """Outreach target model"""
    id: UUID
    campaign_id: UUID
    investor_id: UUID
    status: str
    personalized_message: str
    created_at: datetime

class LinkedInAccount(BaseModel):
    """LinkedIn account model"""
    id: UUID
    user_id: UUID
    unipile_account_id: str
    status: str
    created_at: datetime

class LinkedInResponse(BaseModel):
    """LinkedIn response model"""
    id: UUID
    target_id: UUID
    response_text: str
    received_at: datetime

# ==========================================
# PAYMENT MODELS
# ==========================================

class SubscriptionCreate(BaseModel):
    """Subscription creation model"""
    plan: PlanType
    payment_method_id: str

class SubscriptionResponse(BaseModel):
    """Subscription response model"""
    id: UUID
    user_id: UUID
    stripe_subscription_id: str
    plan: PlanType
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    created_at: datetime

class CreditPurchaseRequest(BaseModel):
    """Credit purchase request model"""
    credits: int = Field(..., gt=0, le=10000)
    payment_method_id: str

class CreditPurchaseResponse(BaseModel):
    """Credit purchase response model"""
    id: UUID
    user_id: UUID
    credits_purchased: int
    amount_usd: float
    status: str
    stripe_payment_intent_id: str
    created_at: datetime

# ==========================================
# WEBSOCKET MODELS
# ==========================================

class WebSocketMessage(BaseModel):
    """WebSocket message model"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

# ==========================================
# UTILITY MODELS
# ==========================================

class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    database_connected: bool
    ai_service_connected: bool
    payment_service_connected: bool

class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[Any]
    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool

# ==========================================
# CONFIGURATION
# ==========================================

class Config:
    """Pydantic configuration"""
    use_enum_values = True
    json_encoders = {
        datetime: lambda v: v.isoformat(),
        UUID: lambda v: str(v)
    }
