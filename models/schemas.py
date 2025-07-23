"""
Pydantic models and schemas for 0Bullshit backend API.
Contains request/response models for all endpoints.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
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
    stage: ProjectStage = ProjectStage.IDEA
    category: ProjectCategory = ProjectCategory.OTHER

class ProjectCreate(ProjectBase):
    """Project creation model"""
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

class ProjectUpdate(BaseModel):
    """Project update model"""
    name: Optional[str] = None
    description: Optional[str] = None
    stage: Optional[ProjectStage] = None
    category: Optional[ProjectCategory] = None
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

class ProjectResponse(ProjectBase):
    """Project response model"""
    id: UUID
    user_id: UUID
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
    completeness_score: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

# ==========================================
# CONVERSATION & MESSAGE MODELS
# ==========================================

class ConversationCreate(BaseModel):
    """Conversation creation model"""
    title: Optional[str] = None
    project_id: Optional[UUID] = None

class ConversationResponse(BaseModel):
    """Conversation response model"""
    id: UUID
    user_id: UUID
    project_id: Optional[UUID] = None
    title: Optional[str] = None
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class MessageCreate(BaseModel):
    """Message creation model"""
    content: str = Field(..., min_length=1, max_length=10000)
    conversation_id: UUID

class MessageResponse(BaseModel):
    """Message response model"""
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    ai_extractions: Optional[Dict[str, Any]] = None
    gemini_prompt_used: Optional[str] = None
    credits_used: int = 0
    created_at: datetime

# ==========================================
# SEARCH MODELS
# ==========================================

class InvestorSearchRequest(BaseModel):
    """Investor search request model"""
    project_id: Optional[UUID] = None
    categories: Optional[List[str]] = None
    stage: Optional[str] = None
    location: Optional[str] = None
    check_size_min: Optional[int] = None
    check_size_max: Optional[int] = None
    limit: int = Field(default=15, le=50)

class CompanySearchRequest(BaseModel):
    """Company search request model"""
    industry: Optional[str] = None
    size_range: Optional[str] = None
    location: Optional[str] = None
    technologies: Optional[List[str]] = None
    limit: int = Field(default=10, le=50)

class InvestorResponse(BaseModel):
    """Investor response model"""
    id: UUID
    name: str
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    investment_focus: Optional[str] = None
    stage_preference: Optional[str] = None
    check_size_min: Optional[int] = None
    check_size_max: Optional[int] = None
    portfolio_companies: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    relevance_score: Optional[float] = None

class CompanyResponse(BaseModel):
    """Company response model"""
    id: UUID
    name: str
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    size_range: Optional[str] = None
    location: Optional[str] = None
    founded_year: Optional[int] = None
    revenue_range: Optional[str] = None
    technologies: Optional[List[str]] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    relevance_score: Optional[float] = None

class SearchResultsResponse(BaseModel):
    """Search results response model"""
    results: List[InvestorResponse | CompanyResponse]
    total_found: int
    average_relevance: float
    credits_used: int
    query_params: Dict[str, Any]

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
# LINKEDIN AUTOMATION MODELS
# ==========================================

class LinkedInAccountConnect(BaseModel):
    """LinkedIn account connection model"""
    email: str
    password: str

class LinkedInAccountResponse(BaseModel):
    """LinkedIn account response model"""
    id: UUID
    user_id: UUID
    unipile_account_id: str
    email: str
    status: str
    last_sync: Optional[datetime] = None
    created_at: datetime

class CampaignCreate(BaseModel):
    """Campaign creation model"""
    name: str = Field(..., min_length=1, max_length=255)
    project_id: Optional[UUID] = None
    linkedin_account_id: UUID
    sequence_type: str = "standard"
    target_investors: List[UUID]

class CampaignResponse(BaseModel):
    """Campaign response model"""
    id: UUID
    user_id: UUID
    project_id: Optional[UUID] = None
    linkedin_account_id: UUID
    name: str
    status: CampaignStatus
    sequence_type: str
    target_count: int
    sent_count: int
    response_count: int
    connection_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

class MessageGenerationRequest(BaseModel):
    """Message generation request model"""
    investor_id: UUID
    message_type: str
    project_context: Optional[str] = None
    personalization_notes: Optional[str] = None

class GeneratedMessageResponse(BaseModel):
    """Generated message response model"""
    id: UUID
    investor_id: str
    message_type: str
    message_content: str
    personalization_score: float
    generated_at: datetime

# ==========================================
# ANALYTICS MODELS
# ==========================================

class UserAnalyticsResponse(BaseModel):
    """User analytics response model"""
    total_credits_used: int
    total_searches: int
    total_messages_generated: int
    total_campaigns: int
    average_response_rate: float
    most_active_day: Optional[str] = None
    last_30_days_activity: Dict[str, int]

class PlatformAnalyticsResponse(BaseModel):
    """Platform analytics response model"""
    total_users: int
    active_users_30d: int
    total_projects: int
    total_searches: int
    total_credits_used: int
    revenue_30d: float
    conversion_rate: float
    most_popular_categories: List[Dict[str, Any]]

# ==========================================
# ONBOARDING MODELS
# ==========================================

class OnboardingStageUpdate(BaseModel):
    """Onboarding stage update model"""
    stage: str
    completed: bool = True

class OnboardingResponse(BaseModel):
    """Onboarding response model"""
    id: UUID
    user_id: UUID
    current_stage: str
    completed_stages: List[str]
    completed: bool
    progress_percentage: float
    next_recommended_action: Optional[str] = None
    started_at: datetime
    updated_at: Optional[datetime] = None

# ==========================================
# WEBSOCKET MODELS
# ==========================================

class WebSocketMessage(BaseModel):
    """WebSocket message model"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatMessage(BaseModel):
    """Chat message for WebSocket"""
    conversation_id: UUID
    message: str
    project_id: Optional[UUID] = None

class ChatResponse(BaseModel):
    """Chat response for WebSocket"""
    conversation_id: UUID
    message_id: UUID
    content: str
    role: MessageRole
    ai_extractions: Optional[Dict[str, Any]] = None
    credits_used: int = 0

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
# ALIASES FOR BACKWARD COMPATIBILITY
# ==========================================

# Aliases for database imports compatibility
Project = ProjectResponse
ProjectData = ProjectResponse
InvestorResult = InvestorResponse
CompanyResult = CompanyResponse
ChatConversation = ConversationResponse
OutreachCampaign = CampaignResponse
OutreachTarget = CampaignResponse  # This might need specific model later
LinkedInAccount = LinkedInAccountResponse
LinkedInResponse = LinkedInAccountResponse

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
