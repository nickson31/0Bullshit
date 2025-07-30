"""
User and project models for 0BullshitIntelligence microservice.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import Field, validator, EmailStr

from .base import BaseModel, TimestampMixin, UUIDMixin, PlanType, ProjectStage, ProjectCategory


# ==========================================
# USER MODELS
# ==========================================

class UserProfile(BaseModel, UUIDMixin, TimestampMixin):
    """User profile information"""
    # Basic information
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Plan and billing
    plan: PlanType = PlanType.FREE
    subscription_status: str = "inactive"  # "active", "inactive", "canceled", "past_due"
    trial_ends_at: Optional[datetime] = None
    
    # Preferences
    language_preference: Optional[str] = None
    timezone: Optional[str] = None
    notification_preferences: Dict[str, bool] = Field(default_factory=dict)
    
    # Usage tracking
    credits_remaining: int = 200
    daily_credits_used: int = 0
    last_activity: Optional[datetime] = None
    
    # Onboarding
    onboarding_completed: bool = False
    onboarding_stage: Optional[str] = None
    welcome_shown: bool = False
    
    # Analytics
    total_conversations: int = 0
    total_searches: int = 0
    total_projects: int = 0


class UserContext(BaseModel):
    """Lightweight user context for AI systems"""
    user_id: UUID
    plan: PlanType
    language_preference: Optional[str] = None
    credits_remaining: int
    daily_credits_used: int
    onboarding_completed: bool
    onboarding_stage: Optional[str] = None
    
    # Recent activity
    recent_searches: int = 0
    recent_conversations: int = 0
    last_activity: Optional[datetime] = None
    
    # Temporary session data
    session_data: Dict[str, Any] = Field(default_factory=dict)


# ==========================================
# PROJECT MODELS
# ==========================================

class ProjectMetrics(BaseModel):
    """Project metrics and KPIs"""
    # Financial metrics
    revenue: Optional[str] = None
    mrr: Optional[str] = None
    arr: Optional[str] = None
    burn_rate: Optional[str] = None
    runway: Optional[str] = None
    
    # User metrics
    users: Optional[int] = None
    active_users: Optional[int] = None
    growth_rate: Optional[str] = None
    churn_rate: Optional[float] = None
    
    # Business metrics
    cac: Optional[str] = None  # Customer Acquisition Cost
    ltv: Optional[str] = None  # Lifetime Value
    unit_economics: Optional[str] = None


class TeamInfo(BaseModel):
    """Team and founder information"""
    size: Optional[int] = None
    founders: List[str] = Field(default_factory=list)
    key_hires: List[str] = Field(default_factory=list)
    advisors: List[str] = Field(default_factory=list)
    investors: List[str] = Field(default_factory=list)
    
    # Founder background
    founder_experience: Optional[str] = None
    previous_companies: List[str] = Field(default_factory=list)
    technical_team: bool = False
    business_team: bool = False


class FundingInfo(BaseModel):
    """Funding and investment information"""
    funding_stage: Optional[str] = None
    amount_raised: Optional[str] = None
    current_round: Optional[str] = None
    target_amount: Optional[str] = None
    
    # Previous rounds
    previous_funding: List[Dict[str, Any]] = Field(default_factory=list)
    investors: List[str] = Field(default_factory=list)
    
    # Use of funds
    use_of_funds: Optional[str] = None
    funding_timeline: Optional[str] = None


class ProjectData(BaseModel):
    """Complete project data structure"""
    # Basic information
    categories: Optional[List[ProjectCategory]] = None
    stage: Optional[ProjectStage] = None
    
    # Core business
    problem_solved: Optional[str] = None
    solution: Optional[str] = None
    target_market: Optional[str] = None
    business_model: Optional[str] = None
    competitive_advantage: Optional[str] = None
    
    # Product information
    product_status: Optional[str] = None
    product_features: List[str] = Field(default_factory=list)
    technology_stack: List[str] = Field(default_factory=list)
    
    # Metrics and performance
    metrics: Optional[ProjectMetrics] = None
    
    # Team information
    team_info: Optional[TeamInfo] = None
    
    # Funding information
    funding_info: Optional[FundingInfo] = None
    
    # Market and competition
    market_size: Optional[str] = None
    competition: List[str] = Field(default_factory=list)
    go_to_market: Optional[str] = None
    
    # Additional fields for flexibility
    additional_fields: Dict[str, Any] = Field(default_factory=dict)


class Project(BaseModel, UUIDMixin, TimestampMixin):
    """Project model"""
    # Basic information
    user_id: UUID
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(max_length=1000)
    
    # Quick access fields
    categories: List[ProjectCategory] = Field(default_factory=list)
    stage: Optional[ProjectStage] = None
    
    # Complete project data
    project_data: ProjectData = Field(default_factory=ProjectData)
    
    # AI-generated insights
    context_summary: Optional[str] = None
    ai_suggestions: List[str] = Field(default_factory=list)
    completeness_score: float = 0.0
    last_analysis: Optional[datetime] = None
    
    # Activity tracking
    last_conversation: Optional[datetime] = None
    total_conversations: int = 0
    total_searches: int = 0
    
    # Status
    active: bool = True
    archived: bool = False

    @validator('completeness_score', pre=True, always=True)
    def validate_completeness_score(cls, v):
        """Ensure completeness score is within valid range"""
        if v is None:
            return 0.0
        return max(0.0, min(100.0, float(v)))


class ProjectCreate(BaseModel):
    """Model for creating new projects"""
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(max_length=1000)
    stage: Optional[ProjectStage] = None
    categories: Optional[List[ProjectCategory]] = None
    initial_data: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    """Model for updating projects"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    stage: Optional[ProjectStage] = None
    categories: Optional[List[ProjectCategory]] = None
    project_data: Optional[ProjectData] = None
    active: Optional[bool] = None


# ==========================================
# COMPLETENESS MODELS
# ==========================================

class CompletenessCheck(BaseModel):
    """Project completeness analysis"""
    project_id: UUID
    overall_score: float = Field(ge=0, le=100)
    
    # Category scores
    basic_info_score: float = Field(ge=0, le=100)
    business_model_score: float = Field(ge=0, le=100)
    market_score: float = Field(ge=0, le=100)
    team_score: float = Field(ge=0, le=100)
    metrics_score: float = Field(ge=0, le=100)
    funding_score: float = Field(ge=0, le=100)
    
    # Missing fields
    missing_fields: List[str] = Field(default_factory=list)
    suggested_improvements: List[str] = Field(default_factory=list)
    
    # Readiness indicators
    ready_for_investor_search: bool = False
    ready_for_company_search: bool = False
    
    # Analysis timestamp
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class CompletenessResponse(BaseModel):
    """Response for completeness check"""
    completeness: CompletenessCheck
    recommendations: List[str]
    next_steps: List[str]
    can_proceed: bool
    

# ==========================================
# SYNCHRONIZATION MODELS
# ==========================================

class SyncOperation(BaseModel, UUIDMixin, TimestampMixin):
    """Database synchronization operation"""
    operation_type: str  # "create", "update", "delete"
    table_name: str
    record_id: UUID
    data: Optional[Dict[str, Any]] = None
    
    # Sync status
    status: str = "pending"  # "pending", "synced", "failed", "skipped"
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Direction
    source: str  # "intelligence", "main"
    target: str  # "main", "intelligence"


class UserSync(BaseModel):
    """User data synchronization"""
    user_id: UUID
    profile_data: Optional[UserProfile] = None
    projects: Optional[List[Project]] = None
    last_sync: datetime = Field(default_factory=datetime.utcnow)
    sync_status: str = "success"  # "success", "partial", "failed"


# ==========================================
# VALIDATION AND UTILITIES
# ==========================================

def calculate_completeness_score(project_data: ProjectData) -> float:
    """Calculate project completeness score"""
    total_fields = 0
    completed_fields = 0
    
    # Basic information (30% weight)
    basic_fields = ['categories', 'stage', 'problem_solved', 'solution', 'target_market']
    for field in basic_fields:
        total_fields += 1
        if getattr(project_data, field, None):
            completed_fields += 1
    
    # Business model (20% weight)
    business_fields = ['business_model', 'competitive_advantage']
    for field in business_fields:
        total_fields += 1
        if getattr(project_data, field, None):
            completed_fields += 1
    
    # Team information (20% weight)
    if project_data.team_info:
        team_fields = ['size', 'founders', 'founder_experience']
        for field in team_fields:
            total_fields += 1
            if getattr(project_data.team_info, field, None):
                completed_fields += 1
    else:
        total_fields += 3
    
    # Metrics (15% weight)
    if project_data.metrics:
        metric_fields = ['revenue', 'users', 'growth_rate']
        for field in metric_fields:
            total_fields += 1
            if getattr(project_data.metrics, field, None):
                completed_fields += 1
    else:
        total_fields += 3
    
    # Market information (15% weight)
    market_fields = ['market_size', 'go_to_market']
    for field in market_fields:
        total_fields += 1
        if getattr(project_data, field, None):
            completed_fields += 1
    
    return (completed_fields / total_fields) * 100 if total_fields > 0 else 0.0


def validate_project_for_search(project: Project, search_type: str) -> tuple[bool, List[str]]:
    """Validate if project is ready for specific search type"""
    issues = []
    
    # Basic requirements
    if not project.project_data.categories:
        issues.append("Project categories are required")
    
    if not project.project_data.stage:
        issues.append("Project stage is required")
    
    if not project.project_data.problem_solved:
        issues.append("Problem description is required")
    
    # Search-specific requirements
    if search_type == "investors":
        if project.completeness_score < 50.0:
            issues.append("Project must be at least 50% complete for investor search")
        
        if not project.project_data.funding_info:
            issues.append("Funding information is required for investor search")
    
    elif search_type == "companies":
        if not project.project_data.solution:
            issues.append("Solution description is required for company search")
    
    return len(issues) == 0, issues