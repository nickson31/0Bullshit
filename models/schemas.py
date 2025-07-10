from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
import uuid

# ==========================================
# CHAT MODELS
# ==========================================

class ChatMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    project_id: UUID

class ChatResponse(BaseModel):
    id: UUID
    project_id: UUID
    role: str  # 'user' or 'assistant'
    content: str
    ai_extractions: Optional[Dict[str, Any]] = None
    gemini_prompt_used: Optional[str] = None
    gemini_response_raw: Optional[str] = None
    created_at: datetime

class ConversationHistory(BaseModel):
    conversations: List[ChatResponse]
    project_info: Dict[str, Any]
    completeness_score: float

# ==========================================
# PROJECT MODELS
# ==========================================

class ProjectMetrics(BaseModel):
    arr: Optional[str] = None
    mrr: Optional[str] = None
    users: Optional[str] = None
    revenue: Optional[str] = None
    growth_rate: Optional[str] = None

class TeamInfo(BaseModel):
    size: Optional[int] = None
    roles: Optional[List[str]] = None
    experience: Optional[str] = None
    previous_companies: Optional[List[str]] = None

class ProjectData(BaseModel):
    # Campos obligatorios (50% del score)
    categories: Optional[List[str]] = None  # 25%
    stage: Optional[str] = None  # 25%
    
    # Campos importantes (50% restante)
    metrics: Optional[ProjectMetrics] = None  # 15%
    team_info: Optional[TeamInfo] = None  # 10%
    problem_solved: Optional[str] = None  # 10%
    product_status: Optional[str] = None  # 10%
    previous_funding: Optional[str] = None  # 5%
    
    # Campo libre para extensiones futuras
    additional_fields: Optional[Dict[str, Any]] = None

class Project(BaseModel):
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

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

# ==========================================
# JUDGE/POLICE MODELS
# ==========================================

class JudgeProbabilities(BaseModel):
    search_investors: float = Field(..., ge=0, le=100)
    search_companies: float = Field(..., ge=0, le=100)
    mentoring: float = Field(..., ge=0, le=100)
    ask_questions: float = Field(..., ge=0, le=100)
    anti_spam: float = Field(..., ge=0, le=100)

class ExtractedData(BaseModel):
    categories: Optional[List[str]] = None
    stage: Optional[str] = None
    metrics: Optional[Dict[str, str]] = None
    team_info: Optional[Dict[str, Any]] = None
    problem_solved: Optional[str] = None
    product_status: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

class JudgeDecision(BaseModel):
    probabilities: JudgeProbabilities
    decision: str  # "search_investors", "search_companies", "mentoring", "ask_questions", "anti_spam"
    reasoning: str
    confidence_score: float = Field(..., ge=0, le=100)
    required_questions: List[str] = []
    extracted_data: Optional[ExtractedData] = None
    completeness_score: float
    should_ask_questions: bool
    anti_spam_triggered: bool = False

# ==========================================
# WELCOME MESSAGE MODELS
# ==========================================

class WelcomeMessageRequest(BaseModel):
    project_id: UUID

class WelcomeMessage(BaseModel):
    message: str
    message_type: str  # "new_user", "returning_user", "low_completeness", "high_completeness"
    suggested_actions: List[str] = []

# ==========================================
# SEARCH MODELS
# ==========================================

class SearchProgress(BaseModel):
    status: str  # "starting", "searching", "processing", "completed", "error"
    message: str
    progress_percentage: Optional[int] = None

class InvestorResult(BaseModel):
    id: UUID
    full_name: str
    headline: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_name: Optional[str] = None
    fund_name: Optional[str] = None
    relevance_score: float
    categories_match: List[str] = []
    stage_match: bool = False

class CompanyResult(BaseModel):
    nombre: str
    descripcion_corta: Optional[str] = None
    web_empresa: Optional[str] = None
    sector_categorias: Optional[str] = None
    service_category: Optional[str] = None
    startup_relevance_score: Optional[str] = None

class SearchResults(BaseModel):
    investors: Optional[List[InvestorResult]] = None
    companies: Optional[List[CompanyResult]] = None
    total_found: int
    search_criteria: Dict[str, Any]
    recommendations: List[str] = []

# ==========================================
# LIBRARIAN MODELS
# ==========================================

class LibrarianUpdate(BaseModel):
    project_id: UUID
    conversation_id: UUID
    updates_made: Dict[str, Any]
    confidence_score: float
    reasoning: str

# ==========================================
# WEBSOCKET MODELS
# ==========================================

class WebSocketMessage(BaseModel):
    type: str  # "search_start", "search_progress", "search_complete", "response_chunk", "response_complete", "error"
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

class ResponseChunk(BaseModel):
    chunk: str
    is_final: bool = False

# ==========================================
# API RESPONSE MODELS
# ==========================================

class CompletenessResponse(BaseModel):
    score: float
    missing_fields: List[str]
    required_fields: List[str]
    suggestions: List[str]
    breakdown: Dict[str, float]  # field -> score contribution

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None

class ChatConversation(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    project_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

class ConversationList(BaseModel):
    conversations: List[ChatConversation]
    total: int

# ==========================================
# USER MODELS
# ==========================================

class UserProfile(BaseModel):
    id: UUID
    email: str
    credits_balance: int
    plan: str
    created_at: datetime

# ==========================================
# UTILITY MODELS
# ==========================================

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, str]  # service_name -> status
