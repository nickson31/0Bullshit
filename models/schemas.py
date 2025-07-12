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

# ==========================================
# OUTREACH CAMPAIGN MODELS (NUEVOS)
# ==========================================

class OutreachCampaignCreate(BaseModel):
    """Modelo para crear campaña de outreach"""
    name: str = Field(..., min_length=1, max_length=200)
    message_template: str = Field(..., min_length=1)
    project_id: UUID
    linkedin_account_id: Optional[str] = None
    daily_limit: int = Field(default=80, ge=1, le=200)
    delay_between_sends: int = Field(default=120, ge=30, le=3600)  # 30 segundos a 1 hora
    send_schedule: Optional[Dict[str, Any]] = None

class OutreachCampaign(BaseModel):
    """Modelo completo de campaña de outreach"""
    id: UUID
    user_id: UUID
    project_id: UUID
    linkedin_account_id: Optional[str] = None
    name: str
    message_template: str
    status: str = "draft"  # draft, active, paused, completed, error
    
    # Contadores
    total_targets: int = 0
    sent_count: int = 0
    reply_count: int = 0
    accepted_count: int = 0
    error_count: int = 0
    
    # Configuración
    daily_limit: int = 80
    delay_between_sends: int = 120
    send_schedule: Optional[Dict[str, Any]] = None
    
    # Métricas
    open_rate: float = 0.00
    response_rate: float = 0.00
    conversion_rate: float = 0.00
    
    # Timestamps
    created_at: datetime
    launched_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_processed: Optional[datetime] = None

class OutreachTargetCreate(BaseModel):
    """Modelo para crear target de outreach"""
    campaign_id: UUID
    investor_id: Optional[UUID] = None
    linkedin_provider_id: Optional[str] = None
    linkedin_profile_url: Optional[str] = None
    linkedin_name: Optional[str] = None
    personalized_message: str
    relevance_score: Optional[float] = None
    scheduled_for: Optional[datetime] = None

class OutreachTarget(BaseModel):
    """Modelo completo de target de outreach"""
    id: UUID
    campaign_id: UUID
    investor_id: Optional[UUID] = None
    
    # LinkedIn específico
    linkedin_provider_id: Optional[str] = None
    linkedin_profile_url: Optional[str] = None
    linkedin_name: Optional[str] = None
    
    # Mensaje
    personalized_message: str
    message_character_count: Optional[int] = None
    
    # Estado
    status: str = "pending"  # pending, sent, replied, accepted, failed, skipped
    
    # Timestamps
    created_at: datetime
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    
    # Gestión de errores
    failure_reason: Optional[str] = None
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    max_retries: int = 3
    
    # Datos adicionales
    profile_data: Optional[Dict[str, Any]] = None
    relevance_score: Optional[float] = None
    
    # Tracking de interacciones
    invitation_sent: bool = False
    invitation_accepted: bool = False
    message_sent: bool = False
    profile_viewed: bool = False

class LinkedInResponse(BaseModel):
    """Modelo completo de respuesta de LinkedIn"""
    id: UUID
    outreach_target_id: UUID
    campaign_id: UUID
    
    # Contenido
    response_text: str
    response_type: str = "message"  # message, invitation_note, comment
    
    # Análisis de IA
    response_sentiment: Optional[str] = None  # positive, negative, neutral
    interest_level: Optional[str] = None  # high, medium, low
    next_action_suggested: Optional[str] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    
    # Datos de Unipile
    unipile_event_data: Optional[Dict[str, Any]] = None
    unipile_message_id: Optional[str] = None
    unipile_chat_id: Optional[str] = None
    
    # Follow-up
    follow_up_scheduled: bool = False
    follow_up_sent: bool = False
    follow_up_at: Optional[datetime] = None
    
    # Timestamps
    received_at: datetime
    processed_at: Optional[datetime] = None
    created_at: datetime

class LinkedInAccountCreate(BaseModel):
    """Modelo para crear cuenta de LinkedIn"""
    unipile_account_id: str
    account_type: str = "classic"  # classic, sales_navigator, recruiter
    account_name: Optional[str] = None
    account_email: Optional[str] = None

class LinkedInAccount(BaseModel):
    """Modelo completo de cuenta de LinkedIn"""
    id: UUID
    user_id: UUID
    unipile_account_id: str
    account_type: str = "classic"
    status: str = "connected"  # connected, disconnected, error, credentials
    account_name: Optional[str] = None
    account_email: Optional[str] = None
    last_sync: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# ==========================================
# RESPONSE MODELS PARA API
# ==========================================

class CampaignStats(BaseModel):
    """Estadísticas de campaña"""
    total_targets: int
    sent_count: int
    reply_count: int
    accepted_count: int
    failed_count: int
    pending_count: int
    response_rate: float
    acceptance_rate: float

class CampaignSummary(BaseModel):
    """Resumen de campaña para dashboard"""
    id: UUID
    name: str
    status: str
    stats: CampaignStats
    created_at: datetime
    launched_at: Optional[datetime] = None
    project_name: Optional[str] = None

class OutreachProgress(BaseModel):
    """Progreso de outreach en tiempo real"""
    campaign_id: UUID
    status: str  # "starting", "processing", "paused", "completed", "error"
    progress_percentage: float
    current_target: Optional[str] = None
    targets_processed: int
    targets_remaining: int
    estimated_completion: Optional[datetime] = None
    last_update: datetime

class BulkTargetCreate(BaseModel):
    """Crear múltiples targets en bulk"""
    campaign_id: UUID
    targets: List[OutreachTargetCreate]

class BulkTargetResponse(BaseModel):
    """Respuesta de creación bulk"""
    success_count: int
    error_count: int
    created_targets: List[UUID]
    errors: List[Dict[str, Any]]

class UnipileWebhookEvent(BaseModel):
    """Modelo para eventos de webhook de Unipile"""
    id: UUID
    event_type: str
    unipile_account_id: Optional[str] = None
    payload: Dict[str, Any]
    processed: bool = False
    processing_error: Optional[str] = None
    received_at: datetime
    processed_at: Optional[datetime] = None
    campaign_id: Optional[UUID] = None
    target_id: Optional[UUID] = None
