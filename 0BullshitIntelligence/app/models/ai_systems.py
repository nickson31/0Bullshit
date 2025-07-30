"""
Models for AI systems in 0BullshitIntelligence microservice.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import Field, validator

from .base import BaseModel, TimestampMixin, Language, PlanType


# ==========================================
# JUDGE SYSTEM MODELS
# ==========================================

class JudgeProbabilities(BaseModel):
    """Probabilities for different judge decisions"""
    chat: float = Field(ge=0, le=1)
    search_investors: float = Field(ge=0, le=1)
    search_companies: float = Field(ge=0, le=1)
    welcome: float = Field(ge=0, le=1)
    upsell: float = Field(ge=0, le=1)
    completeness: float = Field(ge=0, le=1)


class ExtractedData(BaseModel):
    """Data extracted from user messages"""
    categories: Optional[List[str]] = None
    stage: Optional[str] = None
    funding_amount: Optional[str] = None
    location: Optional[str] = None
    team_size: Optional[int] = None
    revenue: Optional[str] = None
    additional_fields: Dict[str, Any] = Field(default_factory=dict)


class JudgeDecision(BaseModel):
    """Judge system decision result"""
    decision: str  # Main action to take
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    probabilities: JudgeProbabilities
    extracted_data: Optional[ExtractedData] = None
    suggested_response: Optional[str] = None
    requires_context: bool = False
    urgency_level: int = Field(ge=1, le=5, default=3)  # 1=low, 5=urgent


# ==========================================
# LANGUAGE DETECTION MODELS
# ==========================================

class LanguageDetection(BaseModel):
    """Language detection result"""
    detected_language: Language
    confidence: float = Field(ge=0, le=1)
    detected_phrases: List[str] = Field(default_factory=list)
    response_language: Language
    is_mixed_language: bool = False
    alternative_languages: Optional[List[str]] = None


# ==========================================
# ANTI-SPAM MODELS
# ==========================================

class SpamIndicators(BaseModel):
    """Indicators that suggest spam content"""
    repeated_content: bool = False
    offensive_language: bool = False
    nonsensical_text: bool = False
    system_manipulation: bool = False
    off_topic: bool = False
    excessive_length: bool = False


class AntiSpamResult(BaseModel):
    """Anti-spam detection result"""
    is_spam: bool
    spam_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    reason: str
    indicators: SpamIndicators
    suggested_action: str  # "allow", "warn", "block", "moderate"
    response_tone: str = "normal"  # "normal", "warning", "strict"


# ==========================================
# UPSELLING SYSTEM MODELS
# ==========================================

class UpsellTrigger(BaseModel):
    """Upselling trigger information"""
    trigger_type: str
    trigger_value: Optional[str] = None
    priority: int = Field(ge=1, le=100)
    message_type: str


class UpsellOpportunity(BaseModel):
    """Upselling opportunity details"""
    should_upsell: bool
    current_plan: PlanType
    target_plan: PlanType
    trigger: UpsellTrigger
    confidence: float = Field(ge=0, le=1)
    message: str
    benefits: List[str] = Field(default_factory=list)
    urgency: str = "medium"  # "low", "medium", "high"
    call_to_action: str
    discount_available: bool = False


# ==========================================
# WELCOME SYSTEM MODELS
# ==========================================

class OnboardingStage(BaseModel):
    """Individual onboarding stage"""
    stage_id: str
    title: str
    description: str
    order: int
    required: bool = True
    completed: bool = False
    completion_date: Optional[datetime] = None


class WelcomeContext(BaseModel):
    """Context for welcome system"""
    is_new_user: bool
    current_stage: Optional[str] = None
    completed_stages: List[str] = Field(default_factory=list)
    onboarding_progress: float = Field(ge=0, le=100, default=0)
    needs_welcome: bool = True


class WelcomeMessage(BaseModel):
    """Welcome system message"""
    message_type: str  # "welcome", "onboarding", "progress", "completion"
    content: str
    context: WelcomeContext
    next_steps: List[str] = Field(default_factory=list)
    stage_info: Optional[OnboardingStage] = None
    show_progress: bool = True
    interactive_elements: Optional[List[Dict[str, Any]]] = None


# ==========================================
# LIBRARIAN SYSTEM MODELS
# ==========================================

class ProjectMetrics(BaseModel):
    """Project metrics data"""
    revenue: Optional[str] = None
    users: Optional[int] = None
    growth_rate: Optional[str] = None
    burn_rate: Optional[str] = None
    runway: Optional[str] = None
    mrr: Optional[str] = None
    arr: Optional[str] = None
    churn_rate: Optional[float] = None


class TeamInfo(BaseModel):
    """Team information"""
    size: Optional[int] = None
    founders: Optional[List[str]] = None
    key_hires: Optional[List[str]] = None
    advisors: Optional[List[str]] = None
    investors: Optional[List[str]] = None
    experience: Optional[str] = None


class LibrarianExtraction(BaseModel):
    """Data extracted by librarian"""
    categories: Optional[List[str]] = None
    stage: Optional[str] = None
    metrics: Optional[ProjectMetrics] = None
    team_info: Optional[TeamInfo] = None
    problem_solved: Optional[str] = None
    target_market: Optional[str] = None
    business_model: Optional[str] = None
    competitive_advantage: Optional[str] = None
    funding_needs: Optional[str] = None
    use_of_funds: Optional[str] = None


class LibrarianUpdate(BaseModel, TimestampMixin):
    """Librarian system update"""
    conversation_id: UUID
    project_id: UUID
    user_message: str = Field(max_length=500)  # Truncated for storage
    assistant_response: str = Field(max_length=500)  # Truncated for storage
    extractions: LibrarianExtraction
    confidence: float = Field(ge=0, le=1)
    changes_made: List[str] = Field(default_factory=list)
    processing_time_ms: float
    success: bool = True


# ==========================================
# Y-COMBINATOR MENTOR MODELS
# ==========================================

class YCPrinciple(BaseModel):
    """Y-Combinator principle reference"""
    principle_id: str
    title: str
    description: str
    relevance_score: float = Field(ge=0, le=1)


class MentorAdvice(BaseModel):
    """Y-Combinator style mentor advice"""
    advice_type: str  # "direct", "question", "challenge", "guidance"
    content: str
    principles_applied: List[YCPrinciple] = Field(default_factory=list)
    actionable_steps: List[str] = Field(default_factory=list)
    tough_questions: List[str] = Field(default_factory=list)
    tone: str = "direct"  # "direct", "supportive", "challenging"
    follow_up_needed: bool = False


# ==========================================
# COMPOSITE AI RESPONSE MODEL
# ==========================================

class AISystemResponse(BaseModel, TimestampMixin):
    """Complete AI system response combining all components"""
    judge_decision: JudgeDecision
    language_detection: LanguageDetection
    anti_spam_result: Optional[AntiSpamResult] = None
    upsell_opportunity: Optional[UpsellOpportunity] = None
    welcome_message: Optional[WelcomeMessage] = None
    mentor_advice: Optional[MentorAdvice] = None
    librarian_update: Optional[LibrarianUpdate] = None
    
    # Performance metrics
    total_processing_time_ms: float
    ai_tokens_used: Optional[int] = None
    
    # Context
    user_id: UUID
    conversation_id: UUID
    project_id: Optional[UUID] = None