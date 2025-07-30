"""
Search models for 0BullshitIntelligence microservice.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import Field, validator

from .base import BaseModel, TimestampMixin, UUIDMixin, SearchType, ProjectStage


# ==========================================
# SEARCH REQUEST MODELS
# ==========================================

class SearchFilters(BaseModel):
    """Base search filters"""
    categories: Optional[List[str]] = None
    stage: Optional[ProjectStage] = None
    location: Optional[str] = None
    min_score: Optional[float] = None
    max_results: int = Field(ge=1, le=50, default=15)


class InvestorSearchFilters(SearchFilters):
    """Investor-specific search filters"""
    investor_type: Optional[str] = None  # "angel", "vc", "fund"
    min_angel_score: float = Field(ge=0, le=100, default=40.0)
    min_employee_score: float = Field(ge=0, le=100, default=5.9)
    funding_stage: Optional[List[str]] = None
    investment_size: Optional[str] = None
    previous_investments: Optional[bool] = None


class CompanySearchFilters(SearchFilters):
    """Company-specific search filters"""
    service_type: Optional[List[str]] = None
    company_size: Optional[str] = None
    industry_focus: Optional[List[str]] = None
    geography: Optional[str] = None


class SearchRequest(BaseModel):
    """Base search request"""
    search_type: SearchType
    query: Optional[str] = None
    filters: SearchFilters
    user_context: Optional[Dict[str, Any]] = None
    save_results: bool = True  # Always save for CTO outreach
    include_metadata: bool = True


# ==========================================
# SEARCH RESULT MODELS
# ==========================================

class ContactInfo(BaseModel):
    """Contact information for search results"""
    email: Optional[str] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None


class InvestorResult(BaseModel, TimestampMixin):
    """Investor search result"""
    # Basic information
    name: str
    type: str  # "angel", "vc", "fund"
    description: Optional[str] = None
    
    # Scoring
    relevance_score: float = Field(ge=0, le=100)
    angel_score: Optional[float] = None
    employee_score: Optional[float] = None
    
    # Investment details
    categories: List[str] = Field(default_factory=list)
    stages: List[str] = Field(default_factory=list)
    typical_investment: Optional[str] = None
    portfolio_companies: Optional[List[str]] = None
    
    # Contact and location
    contact_info: Optional[ContactInfo] = None
    location: Optional[str] = None
    
    # Additional metadata
    verified: bool = False
    last_activity: Optional[datetime] = None
    investment_count: Optional[int] = None
    successful_exits: Optional[int] = None
    
    # Search context
    search_keywords: List[str] = Field(default_factory=list)
    match_reasons: List[str] = Field(default_factory=list)


class CompanyResult(BaseModel, TimestampMixin):
    """Company search result"""
    # Basic information
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    
    # Company details
    industry: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    company_size: Optional[str] = None
    founded_year: Optional[int] = None
    
    # Services
    services_offered: List[str] = Field(default_factory=list)
    target_market: Optional[str] = None
    
    # Contact and location
    contact_info: Optional[ContactInfo] = None
    location: Optional[str] = None
    
    # Scoring and relevance
    relevance_score: float = Field(ge=0, le=100)
    match_reasons: List[str] = Field(default_factory=list)
    
    # Additional metadata
    verified: bool = False
    last_updated: Optional[datetime] = None
    client_testimonials: Optional[List[str]] = None
    
    # Search context
    search_keywords: List[str] = Field(default_factory=list)


# ==========================================
# SEARCH RESPONSE MODELS
# ==========================================

class SearchMetadata(BaseModel):
    """Metadata about the search operation"""
    total_found: int
    search_time_ms: float
    filters_applied: Dict[str, Any]
    search_id: UUID
    saved_to_database: bool = True


class SearchResponse(BaseModel, TimestampMixin):
    """Base search response"""
    search_type: SearchType
    results: List[Dict[str, Any]]  # Will be typed as InvestorResult or CompanyResult
    metadata: SearchMetadata
    success: bool = True
    message: Optional[str] = None


class InvestorSearchResponse(SearchResponse):
    """Investor search response"""
    results: List[InvestorResult]
    
    # Search-specific metadata
    angel_results_count: int = 0
    fund_results_count: int = 0
    average_relevance_score: float = 0.0


class CompanySearchResponse(SearchResponse):
    """Company search response"""
    results: List[CompanyResult]
    
    # Search-specific metadata
    industries_found: List[str] = Field(default_factory=list)
    service_types_found: List[str] = Field(default_factory=list)
    average_relevance_score: float = 0.0


# ==========================================
# SAVED SEARCH MODELS
# ==========================================

class SavedSearchResult(BaseModel, UUIDMixin, TimestampMixin):
    """Saved search result for CTO outreach campaigns"""
    # Search information
    search_id: UUID
    search_type: SearchType
    search_query: Optional[str] = None
    search_filters: Dict[str, Any]
    
    # User/Project context
    user_id: UUID
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    
    # Result data
    result_data: Dict[str, Any]  # The actual InvestorResult or CompanyResult
    relevance_score: float
    
    # Outreach tracking
    contacted: bool = False
    contact_date: Optional[datetime] = None
    contact_method: Optional[str] = None
    response_received: bool = False
    response_date: Optional[datetime] = None
    notes: Optional[str] = None
    
    # Campaign tracking
    campaign_id: Optional[UUID] = None
    campaign_status: Optional[str] = None


# ==========================================
# SEARCH ANALYTICS MODELS
# ==========================================

class SearchAnalytics(BaseModel, TimestampMixin):
    """Analytics for search operations"""
    search_type: SearchType
    user_id: UUID
    project_id: Optional[UUID] = None
    
    # Search details
    query_length: int
    filters_used: List[str]
    results_count: int
    processing_time_ms: float
    
    # User interaction
    results_clicked: int = 0
    results_saved: int = 0
    search_refined: bool = False
    
    # Quality metrics
    average_relevance_score: float
    user_satisfaction_score: Optional[int] = None  # 1-5 rating


class SearchTrends(BaseModel):
    """Search trends and patterns"""
    period: str  # "daily", "weekly", "monthly"
    search_type: SearchType
    
    # Volume metrics
    total_searches: int
    unique_users: int
    average_results_per_search: float
    
    # Popular filters
    top_categories: List[Dict[str, Any]]
    top_stages: List[Dict[str, Any]]
    top_locations: List[Dict[str, Any]]
    
    # Performance metrics
    average_processing_time_ms: float
    success_rate: float
    user_satisfaction: float


# ==========================================
# VALIDATION AND UTILITIES
# ==========================================

@validator('relevance_score', pre=True, always=True)
def validate_relevance_score(cls, v):
    """Ensure relevance score is within valid range"""
    if v is None:
        return 0.0
    return max(0.0, min(100.0, float(v)))


def create_search_request(
    search_type: SearchType,
    query: Optional[str] = None,
    **filter_kwargs
) -> SearchRequest:
    """Helper function to create search requests"""
    if search_type == SearchType.INVESTORS:
        filters = InvestorSearchFilters(**filter_kwargs)
    elif search_type == SearchType.COMPANIES:
        filters = CompanySearchFilters(**filter_kwargs)
    else:
        filters = SearchFilters(**filter_kwargs)
    
    return SearchRequest(
        search_type=search_type,
        query=query,
        filters=filters
    )