"""
Chat models for 0BullshitIntelligence microservice.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import Field, validator

from .base import BaseModel, TimestampMixin, UUIDMixin, MessageRole, Language
from .ai_systems import AISystemResponse
from .search import InvestorResult, CompanyResult


# ==========================================
# CHAT MESSAGE MODELS
# ==========================================

class ChatMessage(BaseModel, UUIDMixin, TimestampMixin):
    """Individual chat message"""
    conversation_id: UUID
    role: MessageRole
    content: str = Field(min_length=1, max_length=10000)
    
    # Metadata
    user_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    language: Optional[Language] = None
    
    # AI processing results (for assistant messages)
    ai_response: Optional[AISystemResponse] = None
    
    # Message state
    processed: bool = False
    processing_time_ms: Optional[float] = None
    token_count: Optional[int] = None
    
    # Search results (if applicable)
    search_results: Optional[Dict[str, Any]] = None


class ChatMessageRequest(BaseModel):
    """Request to send a chat message"""
    message: str = Field(min_length=1, max_length=10000)
    conversation_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    
    # Context
    user_context: Optional[Dict[str, Any]] = None
    force_language: Optional[Language] = None
    
    # Processing options
    include_search: bool = True
    include_upsell: bool = True
    include_welcome: bool = True


# ==========================================
# CONVERSATION MODELS
# ==========================================

class ConversationContext(BaseModel):
    """Context for a conversation"""
    # User and project information
    user_id: UUID
    project_id: Optional[UUID] = None
    user_plan: str = "free"
    
    # Language preferences
    detected_language: Language = Language.SPANISH
    user_preferred_language: Optional[Language] = None
    
    # AI system states
    onboarding_stage: Optional[str] = None
    completed_onboarding: bool = False
    spam_warnings: int = 0
    upsell_attempts_today: int = 0
    
    # Project completeness
    project_completeness_score: float = 0.0
    last_completeness_check: Optional[datetime] = None
    
    # Conversation metrics
    message_count: int = 0
    search_count: int = 0
    last_activity: datetime = Field(default_factory=datetime.utcnow)


class ChatConversation(BaseModel, UUIDMixin, TimestampMixin):
    """Chat conversation with full context"""
    # Basic information
    title: Optional[str] = None
    context: ConversationContext
    
    # Conversation state
    active: bool = True
    archived: bool = False
    archived_at: Optional[datetime] = None
    
    # Summary and insights
    summary: Optional[str] = None
    key_topics: List[str] = Field(default_factory=list)
    ai_extractions: Optional[Dict[str, Any]] = None
    
    # Performance tracking
    total_processing_time_ms: float = 0.0
    total_tokens_used: int = 0
    
    @validator('title', pre=True, always=True)
    def generate_title(cls, v, values):
        """Generate title if not provided"""
        if not v and 'created_at' in values:
            timestamp = values['created_at']
            return f"Conversation {timestamp.strftime('%Y-%m-%d %H:%M')}"
        return v


# ==========================================
# CHAT RESPONSE MODELS
# ==========================================

class ChatResponse(BaseModel, TimestampMixin):
    """Response to a chat message"""
    # Core response
    response: str
    conversation_id: UUID
    message_id: UUID
    
    # AI system results
    ai_decision: str  # The main action taken
    language_info: Dict[str, Any]
    
    # Optional components
    upsell_opportunity: Optional[Dict[str, Any]] = None
    welcome_info: Optional[Dict[str, Any]] = None
    search_results: Optional[Dict[str, Any]] = None
    
    # Performance metrics
    processing_time_ms: float
    ai_tokens_used: Optional[int] = None
    
    # Context updates
    context_updated: bool = False
    project_updated: bool = False
    
    # Next steps
    suggested_actions: List[str] = Field(default_factory=list)
    requires_follow_up: bool = False


class ChatSearchResponse(ChatResponse):
    """Chat response that includes search results"""
    investor_results: Optional[List[InvestorResult]] = None
    company_results: Optional[List[CompanyResult]] = None
    search_metadata: Optional[Dict[str, Any]] = None
    
    # Results saved for outreach
    results_saved_count: int = 0
    results_saved_ids: List[UUID] = Field(default_factory=list)


# ==========================================
# CONVERSATION HISTORY MODELS
# ==========================================

class ConversationHistory(BaseModel):
    """Conversation history for context"""
    conversation_id: UUID
    messages: List[ChatMessage]
    total_messages: int
    
    # Filtered views
    recent_messages: List[ChatMessage] = Field(default_factory=list)
    user_messages_only: List[ChatMessage] = Field(default_factory=list)
    assistant_messages_only: List[ChatMessage] = Field(default_factory=list)
    
    # Context summary
    conversation_summary: Optional[str] = None
    key_extractions: Optional[Dict[str, Any]] = None
    
    @validator('recent_messages', pre=True, always=True)
    def set_recent_messages(cls, v, values):
        """Set recent messages (last 10)"""
        if 'messages' in values:
            return values['messages'][-10:]
        return v


class ConversationAnalytics(BaseModel, TimestampMixin):
    """Analytics for conversation performance"""
    conversation_id: UUID
    user_id: UUID
    
    # Message metrics
    total_messages: int
    user_messages: int
    assistant_messages: int
    average_message_length: float
    
    # AI performance
    total_processing_time_ms: float
    average_processing_time_ms: float
    total_tokens_used: int
    ai_systems_used: List[str]
    
    # User engagement
    session_duration_minutes: float
    responses_per_minute: float
    search_requests: int
    successful_searches: int
    
    # Outcomes
    onboarding_completed: bool = False
    project_completeness_improved: bool = False
    upsell_presented: bool = False
    upsell_converted: bool = False
    
    # Quality metrics
    user_satisfaction: Optional[int] = None  # 1-5 rating
    conversation_quality_score: Optional[float] = None


# ==========================================
# WEBSOCKET MODELS
# ==========================================

class WebSocketMessage(BaseModel):
    """WebSocket message structure"""
    type: str  # "message", "typing", "search_progress", "error", "status"
    data: Dict[str, Any]
    conversation_id: Optional[UUID] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WebSocketConnection(BaseModel, UUIDMixin, TimestampMixin):
    """WebSocket connection tracking"""
    user_id: UUID
    conversation_id: Optional[UUID] = None
    connection_status: str = "connected"  # "connected", "disconnected", "error"
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    # Connection metadata
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None


class TypingIndicator(BaseModel):
    """Typing indicator for real-time chat"""
    conversation_id: UUID
    user_id: UUID
    is_typing: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==========================================
# VALIDATION AND UTILITIES
# ==========================================

def validate_message_content(content: str) -> str:
    """Validate and clean message content"""
    content = content.strip()
    if not content:
        raise ValueError("Message content cannot be empty")
    if len(content) > 10000:
        raise ValueError("Message content too long")
    return content


def create_chat_message(
    content: str,
    conversation_id: UUID,
    role: MessageRole,
    user_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None
) -> ChatMessage:
    """Helper function to create chat messages"""
    return ChatMessage(
        content=validate_message_content(content),
        conversation_id=conversation_id,
        role=role,
        user_id=user_id,
        project_id=project_id
    )


def create_conversation_context(
    user_id: UUID,
    project_id: Optional[UUID] = None,
    user_plan: str = "free",
    detected_language: Language = Language.SPANISH
) -> ConversationContext:
    """Helper function to create conversation context"""
    return ConversationContext(
        user_id=user_id,
        project_id=project_id,
        user_plan=user_plan,
        detected_language=detected_language
    )