import os
import jwt
import asyncio
import re
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, status, Field
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import json
import logging

# Imports locales
from models.schemas import (
    ChatMessage, ChatResponse, ProjectCreate, Project, 
    WelcomeMessage, ConversationHistory, CompletenessResponse,
    ApiResponse, ConversationList, HealthCheck, UserProfile
)
from database.database import db
from chat.chat import chat_system
from chat.welcome import welcome_system
from chat.judge import judge
from chat.librarian import librarian

# Imports de utilidades
from api.utils import get_current_user

# Imports de routers
from api.linkedin import router as linkedin_router
from api.outreach import router as outreach_router
from api.webhooks import router as webhooks_router
from api.campaigns import router as campaigns_router
from payments.payments import router as payments_router

# Imports de sistemas adicionales
import stripe
from passlib.context import CryptContext
from pydantic import EmailStr

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar Stripe
stripe.api_key = os.getenv("STRIPE_API_KEY")

# Configuración de seguridad para auth
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Inicializar FastAPI
app = FastAPI(
    title="0Bullshit Chat API",
    description="API para el sistema de chat con IA especializado en startups con outreach automatizado",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# WEBSOCKET MANAGER
# ==========================================

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_message(self, client_id: str, message: Dict[str, Any]):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending websocket message: {e}")
                self.disconnect(client_id)

ws_manager = WebSocketManager()

# ==========================================
# AUTHENTICATION MODELS AND FUNCTIONS
# ==========================================

class UserRegistration(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    credits_balance: int
    daily_credits: int
    plan: str
    created_at: datetime
    preferred_language: str = "es"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfileResponse

class CreditsPurchase(BaseModel):
    package: str = Field(..., regex="^(small|medium|large)$")

def hash_password(password: str) -> str:
    """Hashear contraseña"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: Dict[str, Any]) -> str:
    """Crear token JWT"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, os.getenv("JWT_SECRET_KEY"), algorithm="HS256")

async def get_current_user_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserProfileResponse:
    """Obtener usuario actual del token"""
    try:
        payload = jwt.decode(credentials.credentials, os.getenv("JWT_SECRET_KEY"), algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        result = db.supabase.table("users").select("*").eq("id", user_id).eq("is_active", True).execute()
        if not result.data:
            raise HTTPException(status_code=401, detail="User not found")
        
        user_db = result.data[0]
        return UserProfileResponse(
            id=UUID(user_db["id"]),
            email=user_db["email"],
            first_name=user_db.get("first_name"),
            last_name=user_db.get("last_name"),
            credits_balance=user_db.get("credits_balance", 0),
            daily_credits=user_db.get("daily_credits", 0),
            plan=user_db.get("plan", "free"),
            created_at=datetime.fromisoformat(user_db["created_at"].replace("Z", "+00:00")),
            preferred_language=user_db.get("preferred_language", "es")
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def check_and_deduct_credits(user_id: UUID, operation: str) -> bool:
    """Verificar y deducir créditos según el tipo de operación"""
    result = db.supabase.table("users").select("credits_balance, plan").eq("id", str(user_id)).execute()
    
    if not result.data:
        return False
    
    user_data = result.data[0]
    current_credits = user_data["credits_balance"]
    plan = user_data["plan"]
    
    # Configuración de costos por operación según el plan
    operation_costs = {
        "free": {
            "chat_message": 10,
            "investor_search": 1000,  # No disponible en plan free
            "company_search": 250     # No disponible en plan free
        },
        "pro": {
            "chat_message": 5,
            "investor_search": 1000,
            "company_search": 250
        },
        "outreach": {
            "chat_message": 0,  # Ilimitado
            "investor_search": 1000,
            "company_search": 250
        }
    }
    
    cost = operation_costs.get(plan, {}).get(operation, 0)
    
    # Para plan free, verificar si la operación está permitida
    if plan == "free" and operation in ["investor_search", "company_search"]:
        return False  # No permitido en plan gratuito
    
    # Para plan outreach, los mensajes de chat son gratis
    if plan == "outreach" and operation == "chat_message":
        return True
    
    # Verificar si hay suficientes créditos
    if current_credits < cost:
        return False
    
    # Deducir créditos
    new_credits = max(0, current_credits - cost)
    update_result = db.supabase.table("users").update({
        "credits_balance": new_credits,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", str(user_id)).execute()
    
    return len(update_result.data) > 0

# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    services = {}
    
    # Check Supabase
    try:
        result = db.supabase.table("users").select("id").limit(1).execute()
        services["supabase"] = "healthy"
    except Exception as e:
        logger.error(f"Supabase health check failed: {e}")
        services["supabase"] = "unhealthy"
    
    # Check Gemini API
    try:
        test_response = judge.model.generate_content("Test connection")
        services["gemini"] = "healthy" if test_response else "unhealthy"
    except Exception as e:
        logger.error(f"Gemini health check failed: {e}")
        services["gemini"] = "unhealthy"
    
    # Check Unipile (if configured)
    try:
        from integrations.unipile_client import unipile_client
        if unipile_client and unipile_client.api_key:
            # Test simple API call
            accounts = await unipile_client.get_accounts()
            services["unipile"] = "healthy"
        else:
            services["unipile"] = "not_configured"
    except Exception as e:
        logger.error(f"Unipile health check failed: {e}")
        services["unipile"] = "unhealthy"
    
    overall_status = "healthy" if all(s in ["healthy", "not_configured"] for s in services.values()) else "degraded"
    
    return HealthCheck(
        status=overall_status,
        timestamp=datetime.now(),
        services=services
    )

# ==========================================
# AUTHENTICATION ENDPOINTS
# ==========================================

@app.post("/api/v1/auth/register", response_model=TokenResponse, status_code=201)
async def register(user_data: UserRegistration):
    """Registrar nuevo usuario"""
    # Verificar si el email ya existe
    existing_result = db.supabase.table("users").select("id").eq("email", user_data.email).execute()
    if existing_result.data:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    user_id = uuid4()
    hashed_password = hash_password(user_data.password)
    
    user_dict = {
        "id": str(user_id),
        "email": user_data.email,
        "password_hash": hashed_password,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "credits_balance": 200,  # Plan gratuito: 200 créditos iniciales
        "daily_credits": 50,     # 50 créditos diarios
        "plan": "free",
        "preferred_language": "es",
        "created_at": datetime.utcnow().isoformat(),
        "is_active": True
    }
    
    result = db.supabase.table("users").insert(user_dict).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    user = UserProfileResponse(
        id=user_id,
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        credits_balance=200,
        daily_credits=50,
        plan="free",
        created_at=datetime.utcnow(),
        preferred_language="es"
    )
    
    access_token = create_access_token(data={"sub": str(user_id), "email": user_data.email})
    
    return TokenResponse(
        access_token=access_token,
        expires_in=24 * 3600,
        user=user
    )

@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """Login de usuario"""
    result = db.supabase.table("users").select("*").eq("email", user_data.email).eq("is_active", True).execute()
    
    if not result.data:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    user_db = result.data[0]
    
    if not verify_password(user_data.password, user_db["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Actualizar último login
    db.supabase.table("users").update({
        "last_login": datetime.utcnow().isoformat()
    }).eq("id", user_db["id"]).execute()
    
    user = UserProfileResponse(
        id=UUID(user_db["id"]),
        email=user_db["email"],
        first_name=user_db.get("first_name"),
        last_name=user_db.get("last_name"),
        credits_balance=user_db.get("credits_balance", 0),
        daily_credits=user_db.get("daily_credits", 0),
        plan=user_db.get("plan", "free"),
        created_at=datetime.fromisoformat(user_db["created_at"].replace("Z", "+00:00")),
        preferred_language=user_db.get("preferred_language", "es")
    )
    
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    
    return TokenResponse(
        access_token=access_token,
        expires_in=24 * 3600,
        user=user
    )

@app.get("/api/v1/auth/me", response_model=UserProfileResponse)
async def get_me(current_user: UserProfileResponse = Depends(get_current_user_auth)):
    """Obtener perfil del usuario actual"""
    return current_user

@app.get("/api/v1/auth/credits")
async def get_credit_balance(current_user: UserProfileResponse = Depends(get_current_user_auth)):
    """Obtener balance de créditos"""
    return {
        "credits_balance": current_user.credits_balance,
        "daily_credits": current_user.daily_credits,
        "plan": current_user.plan
    }

# ==========================================
# STRIPE PAYMENT ENDPOINTS
# ==========================================

@app.post("/api/v1/payments/create-subscription")
async def create_subscription(
    plan: str = Field(..., regex="^(pro|outreach)$"),
    current_user: UserProfileResponse = Depends(get_current_user_auth)
):
    """Crear suscripción de Stripe"""
    try:
        price_ids = {
            "pro": "price_pro_monthly",      # Reemplazar con ID real de Stripe
            "outreach": "price_outreach_monthly"  # Reemplazar con ID real de Stripe
        }
        
        # Crear cliente en Stripe si no existe
        customer = stripe.Customer.create(
            email=current_user.email,
            metadata={"user_id": str(current_user.id)}
        )
        
        # Crear sesión de checkout
        session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_ids[plan],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{os.getenv('FRONTEND_URL')}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.getenv('FRONTEND_URL')}/payment/cancel",
        )
        
        return {"checkout_url": session.url}
        
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail="Error creating subscription")

@app.post("/api/v1/payments/purchase-credits")
async def purchase_credits(
    purchase_data: CreditsPurchase,
    current_user: UserProfileResponse = Depends(get_current_user_auth)
):
    """Comprar créditos adicionales"""
    try:
        credit_packages = {
            "small": {"credits": 4900, "price": 1900, "stripe_price_id": "price_credits_small"},
            "medium": {"credits": 19900, "price": 5900, "stripe_price_id": "price_credits_medium"},
            "large": {"credits": 49900, "price": 14900, "stripe_price_id": "price_credits_large"}
        }
        
        package = credit_packages.get(purchase_data.package)
        if not package:
            raise HTTPException(status_code=400, detail="Invalid credit package")
        
        # Crear sesión de checkout
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': package["stripe_price_id"],
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{os.getenv('FRONTEND_URL')}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.getenv('FRONTEND_URL')}/payment/cancel",
            metadata={
                "user_id": str(current_user.id),
                "credits": package["credits"],
                "type": "credit_purchase"
            }
        )
        
        return {"checkout_url": session.url}
        
    except Exception as e:
        logger.error(f"Error purchasing credits: {e}")
        raise HTTPException(status_code=500, detail="Error purchasing credits")

# ==========================================
# SEARCH SYSTEM
# ==========================================

class SearchRequest(BaseModel):
    project_id: UUID
    query: Optional[str] = None
    search_type: str  # "investors" or "companies"

class InvestorSearchResult(BaseModel):
    linkedin_url: str
    full_name: str
    headline: Optional[str]
    email: Optional[str] 
    location: Optional[str]
    profile_pic: Optional[str]
    angel_score: float
    validation_reasons_es: Optional[str]
    categories_match: List[str]
    stage_match: bool
    relevance_score: float

class CompanySearchResult(BaseModel):
    linkedin_url: str
    nombre: str
    descripcion_corta: Optional[str]
    web_empresa: Optional[str]
    sector_categorias: Optional[str]
    ubicacion_general: Optional[str]
    relevance_score: float

class SearchResults(BaseModel):
    results: List[Any]
    total_found: int
    search_type: str
    criteria_used: Dict[str, Any]
    has_more: bool

async def extract_search_keywords(query: str, project_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """Extraer keywords del query y datos del proyecto usando Gemini"""
    
    project_context = f"""
    Categorías del proyecto: {project_data.get('categories', [])}
    Stage del proyecto: {project_data.get('stage', 'No especificado')}
    Descripción del proyecto: {project_data.get('description', 'No disponible')}
    """
    
    prompt = f"""
    Analiza el siguiente query y contexto del proyecto para extraer keywords relevantes para búsquedas.

    QUERY DEL USUARIO: "{query}"
    
    CONTEXTO DEL PROYECTO:
    {project_context}
    
    Extrae entre 10-30 keywords específicas del query del usuario.
    Incluye tanto keywords en español como en inglés.
    Enfócate en industrias, tecnologías, modelos de negocio, etapas de funding.
    
    Responde SOLO con un JSON en este formato:
    {{
        "categories_keywords": ["keyword1", "keyword2"],
        "stage_keywords": ["seed", "series-a"],
        "industry_keywords": ["fintech", "healthtech"],
        "general_keywords": ["keyword1", "keyword2"]
    }}
    """
    
    try:
        # Usar Gemini para extraer keywords
        from chat.judge import judge
        response = judge.model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Limpiar respuesta para obtener solo el JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        keywords_data = json.loads(response_text)
        return keywords_data
        
    except Exception as e:
        # Fallback: keywords básicas del query
        words = re.findall(r'\w+', query.lower())
        return {
            "categories_keywords": words[:5],
            "stage_keywords": [],
            "industry_keywords": [],
            "general_keywords": words
        }

async def search_angel_investors(keywords: Dict[str, List[str]], limit: int = 15) -> List[InvestorSearchResult]:
    """Buscar inversores ángeles en la base de datos"""
    
    try:
        # Construir query base
        query_builder = db.supabase.table("Angel_Investors").select("*")
        
        # Filtrar por score mínimo (como especifica el prompt)
        query_builder = query_builder.gte("angel_score", 40.0)
        
        # Aplicar filtros de keywords
        conditions = []
        
        # Categories matching
        all_category_keywords = keywords.get("categories_keywords", []) + keywords.get("industry_keywords", [])
        for keyword in all_category_keywords[:5]:  # Limitar para evitar queries muy largas
            conditions.extend([
                f"categories_general_es.ilike.%{keyword}%",
                f"categories_general_en.ilike.%{keyword}%", 
                f"categories_strong_es.ilike.%{keyword}%",
                f"categories_strong_en.ilike.%{keyword}%"
            ])
        
        # Stage matching
        for stage_keyword in keywords.get("stage_keywords", []):
            conditions.extend([
                f"stage_general_es.ilike.%{stage_keyword}%",
                f"stage_general_en.ilike.%{stage_keyword}%",
                f"stage_strong_es.ilike.%{stage_keyword}%", 
                f"stage_strong_en.ilike.%{stage_keyword}%"
            ])
        
        # Si hay condiciones, aplicar OR entre ellas
        if conditions:
            or_condition = ",".join(conditions)
            query_builder = query_builder.or_(or_condition)
        
        # Ejecutar query con límite
        result = query_builder.limit(limit).execute()
        
        investors = []
        for inv in result.data:
            # Calcular relevance score básico
            relevance = 0.5  # Score base
            
            # Determinar matches de categorías
            category_matches = []
            for cat in all_category_keywords:
                for field in ["categories_general_es", "categories_strong_es"]:
                    field_data = inv.get(field, "")
                    if cat.lower() in field_data.lower():
                        category_matches.append(cat)
                        relevance += 0.2
                        break
            
            # Stage match
            stage_match = False
            for stage in keywords.get("stage_keywords", []):
                for field in ["stage_general_es", "stage_strong_es"]:
                    field_data = inv.get(field, "")
                    if stage.lower() in field_data.lower():
                        stage_match = True
                        relevance += 0.3
                        break
            
            investors.append(InvestorSearchResult(
                linkedin_url=inv.get("linkedinUrl", ""),
                full_name=inv.get("fullName", ""),
                headline=inv.get("headline"),
                email=inv.get("email"),
                location=inv.get("addressWithCountry"),
                profile_pic=inv.get("profilePic"),
                angel_score=float(inv.get("angel_score", 0)),
                validation_reasons_es=inv.get("validation_reasons_spanish"),
                categories_match=category_matches,
                stage_match=stage_match,
                relevance_score=min(relevance, 1.0)
            ))
        
        # Ordenar por relevancia y score
        investors.sort(key=lambda x: (x.relevance_score, x.angel_score), reverse=True)
        
        return investors
        
    except Exception as e:
        logger.error(f"Error in search_angel_investors: {e}")
        return []

async def search_investment_funds(keywords: Dict[str, List[str]], limit: int = 15) -> List[Dict[str, Any]]:
    """Buscar fondos de inversión"""
    
    try:
        # Construir query para fondos
        query_builder = db.supabase.table("Investment_Funds").select("*")
        
        # Filtrar fondos que tengan keywords válidas (no vacías)
        query_builder = query_builder.neq("category_keywords", "[]")
        
        result = query_builder.limit(limit).execute()
        
        funds = []
        for fund in result.data:
            # Calcular relevancia básica
            relevance = 0.3
            
            category_keywords_str = fund.get("category_keywords", "")
            stage_keywords_str = fund.get("stage_keywords", "")
            
            all_keywords = (keywords.get("categories_keywords", []) + 
                           keywords.get("industry_keywords", []) + 
                           keywords.get("stage_keywords", []))
            
            for keyword in all_keywords:
                if keyword.lower() in category_keywords_str.lower():
                    relevance += 0.4
                if keyword.lower() in stage_keywords_str.lower():
                    relevance += 0.3
            
            # Obtener empleados del fondo con score >= 5.9
            employees_result = db.supabase.table("Employee_Funds").select("*").eq("fund_name", fund.get("name", "")).gte("score_combinado", 5.9).limit(5).execute()
            
            employees = []
            for emp in employees_result.data:
                employees.append({
                    "linkedin_url": emp.get("linkedinUrl"),
                    "full_name": emp.get("fullName"),
                    "headline": emp.get("headline"),
                    "email": emp.get("email"),
                    "profile_pic": emp.get("profilePic"),
                    "location": emp.get("addressWithCountry"),
                    "job_title": emp.get("jobTitle"),
                    "combined_score": emp.get("score_combinado", 0)
                })
            
            funds.append({
                "fund_data": fund,
                "employees": employees,
                "relevance_score": min(relevance, 1.0)
            })
        
        # Ordenar por relevancia
        funds.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return funds
        
    except Exception as e:
        logger.error(f"Error in search_investment_funds: {e}")
        return []

async def search_companies(keywords: Dict[str, List[str]], limit: int = 10) -> List[CompanySearchResult]:
    """Buscar empresas/servicios relevantes"""
    
    try:
        query_builder = db.supabase.table("Companies").select("*")
        
        # Aplicar filtros de keywords
        conditions = []
        
        all_keywords = (keywords.get("categories_keywords", []) + 
                       keywords.get("industry_keywords", []) + 
                       keywords.get("general_keywords", []))
        
        for keyword in all_keywords[:10]:  # Limitar keywords
            conditions.extend([
                f"keywords_generales.ilike.%{keyword}%",
                f"keywords_especificas.ilike.%{keyword}%",
                f"sector_categorias.ilike.%{keyword}%",
                f"descripcion_corta.ilike.%{keyword}%"
            ])
        
        # Aplicar condiciones OR
        if conditions:
            or_condition = ",".join(conditions)
            query_builder = query_builder.or_(or_condition)
        
        result = query_builder.limit(limit).execute()
        
        companies = []
        for comp in result.data:
            # Calcular relevancia
            relevance = 0.3
            
            keywords_generales = comp.get("keywords_generales", "")
            keywords_especificas = comp.get("keywords_especificas", "")
            sector = comp.get("sector_categorias", "")
            
            for keyword in all_keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in keywords_especificas.lower():
                    relevance += 0.4
                elif keyword_lower in keywords_generales.lower():
                    relevance += 0.3
                elif keyword_lower in sector.lower():
                    relevance += 0.2
            
            companies.append(CompanySearchResult(
                linkedin_url=comp.get("linkedin", ""),
                nombre=comp.get("nombre", ""),
                descripcion_corta=comp.get("descripcion_corta"),
                web_empresa=comp.get("web_empresa"),
                sector_categorias=comp.get("sector_categorias"),
                ubicacion_general=comp.get("ubicacion_general"),
                relevance_score=min(relevance, 1.0)
            ))
        
        # Ordenar por relevancia
        companies.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return companies
        
    except Exception as e:
        logger.error(f"Error in search_companies: {e}")
        return []

# ==========================================
# SEARCH ENDPOINTS
# ==========================================

@app.post("/api/v1/search/investors")
async def search_investors_endpoint(
    search_request: SearchRequest,
    current_user: UserProfileResponse = Depends(get_current_user_auth)
):
    """Buscar inversores (ángeles + fondos)"""
    
    # Verificar créditos
    if not await check_and_deduct_credits(current_user.id, "investor_search"):
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits. Please upgrade your plan or purchase more credits."
        )
    
    try:
        # Obtener proyecto y sus datos
        project = await db.get_project(search_request.project_id, current_user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Extraer keywords del query y proyecto
        project_data = {
            "categories": project.categories or [],
            "stage": project.stage,
            "description": project.description
        }
        
        query_text = search_request.query or "inversores para mi startup"
        keywords = await extract_search_keywords(query_text, project_data)
        
        # Buscar ángeles y fondos
        angels = await search_angel_investors(keywords, limit=8)  # 8 ángeles
        funds = await search_investment_funds(keywords, limit=7)  # 7 fondos
        
        # Combinar resultados (híbrido como requiere el prompt)
        results = []
        
        # Convertir ángeles a formato común
        for angel in angels:
            results.append({
                "type": "angel",
                "data": angel.dict(),
                "relevance_score": angel.relevance_score
            })
        
        # Convertir fondos a formato común
        for fund in funds:
            results.append({
                "type": "fund", 
                "data": fund,
                "relevance_score": fund["relevance_score"]
            })
        
        # Ordenar híbrido basado en stage como especifica el prompt
        stage = project.stage or ""
        if stage.lower() in ["idea", "pre-seed", "seed"]:
            # Más ángeles para etapas tempranas
            angels_to_show = 10
            funds_to_show = 5
        else:
            # Más fondos para etapas tardías  
            angels_to_show = 5
            funds_to_show = 10
        
        # Filtrar y reordenar
        angel_results = [r for r in results if r["type"] == "angel"][:angels_to_show]
        fund_results = [r for r in results if r["type"] == "fund"][:funds_to_show]
        
        final_results = angel_results + fund_results
        final_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return SearchResults(
            results=final_results,
            total_found=len(final_results),
            search_type="investors",
            criteria_used=keywords,
            has_more=len(angels) + len(funds) > 15
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.post("/api/v1/search/companies") 
async def search_companies_endpoint(
    search_request: SearchRequest,
    current_user: UserProfileResponse = Depends(get_current_user_auth)
):
    """Buscar empresas/servicios"""
    
    # Verificar créditos
    if not await check_and_deduct_credits(current_user.id, "company_search"):
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits. Please upgrade your plan or purchase more credits."
        )
    
    try:
        # Obtener proyecto
        project = await db.get_project(search_request.project_id, current_user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Extraer keywords
        project_data = {
            "categories": project.categories or [],
            "stage": project.stage,
            "description": project.description
        }
        
        query_text = search_request.query or "servicios para mi startup"
        keywords = await extract_search_keywords(query_text, project_data)
        
        # Buscar empresas
        companies = await search_companies(keywords, limit=10)
        
        return SearchResults(
            results=[{"type": "company", "data": comp.dict(), "relevance_score": comp.relevance_score} for comp in companies],
            total_found=len(companies),
            search_type="companies", 
            criteria_used=keywords,
            has_more=len(companies) >= 10
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

# ==========================================
# UPSELL SYSTEM
# ==========================================

class UpsellMessage(BaseModel):
    message: str
    message_type: str  # "upgrade_to_pro", "upgrade_to_outreach", "purchase_credits"
    cta_text: str
    cta_url: str
    show_upsell: bool

class UpsellJudge:
    """Sistema de upsell inteligente usando Gemini para generar mensajes personalizados"""
    
    def __init__(self):
        self.last_upsell_tracker = {}  # user_id -> last_upsell_message_count
        self.anti_saturation_messages = 2  # Mínimo 2 mensajes entre upsells
    
    async def should_show_upsell(self, user: UserProfileResponse, context: Dict[str, Any]) -> bool:
        """Determinar si mostrar upsell basado en contexto y anti-saturación"""
        
        user_id = str(user.id)
        
        # Sistema anti-saturación
        if user_id in self.last_upsell_tracker:
            messages_since_last = context.get("messages_since_last_upsell", 0)
            if messages_since_last < self.anti_saturation_messages:
                return False
        
        # Analizar contexto para determinar oportunidad de upsell
        opportunity_score = await self._calculate_upsell_opportunity(user, context)
        
        # Umbral alto para mostrar upsell (70%)
        return opportunity_score >= 70.0
    
    async def _calculate_upsell_opportunity(self, user: UserProfileResponse, context: Dict[str, Any]) -> float:
        """Calcular score de oportunidad de upsell usando Gemini"""
        
        context_text = f"""
        INFORMACIÓN DEL USUARIO:
        - Plan actual: {user.plan}
        - Créditos restantes: {user.credits_balance}
        - Días usando la plataforma: {context.get('days_using_platform', 0)}
        
        CONTEXTO DE LA CONVERSACIÓN:
        - Tipo de consulta: {context.get('query_type', 'general')}
        - Proyecto en stage: {context.get('project_stage', 'unknown')}
        - Ha buscado inversores: {context.get('has_searched_investors', False)}
        - Ha buscado empresas: {context.get('has_searched_companies', False)}
        - Número de proyectos: {context.get('project_count', 0)}
        
        ÚLTIMO MENSAJE DEL USUARIO: "{context.get('last_user_message', '')}"
        RESPUESTA QUE ACABAMOS DE DAR: "{context.get('our_last_response', '')}"
        """
        
        prompt = f"""
        Eres un experto en ventas B2B especializado en plataformas SaaS para startups. Tu trabajo es analizar si es una buena oportunidad para hacer upsell de planes.
        
        CONTEXTO:
        {context_text}
        
        PLANES DISPONIBLES:
        - FREE: 200 créditos, solo chat
        - PRO ($24.50/mes): 10,000 créditos, chat + búsqueda inversores + búsqueda empresas
        - OUTREACH ($94.50/mes): 29,900 créditos, todo lo anterior + automatización LinkedIn
        
        REGLAS DE UPSELL:
        1. FREE → PRO: Cuando necesite buscar inversores o empresas
        2. PRO → OUTREACH: Cuando haya encontrado inversores y necesite contactarlos
        3. Solo si es contextualmente relevante y natural
        4. No si acaba de hacer upgrade o si está en trial
        
        Analiza la situación y devuelve SOLO un número del 0 al 100 representando qué tan buena oportunidad es para hacer upsell ahora.
        
        Criterios:
        - 90-100: Oportunidad perfecta (justo pidió algo que requiere upgrade)
        - 70-89: Buena oportunidad (contexto relevante)
        - 50-69: Oportunidad moderada
        - 0-49: No es buen momento
        
        Responde SOLO con el número:
        """
        
        try:
            from chat.judge import judge
            response = judge.model.generate_content(prompt)
            score_text = response.text.strip()
            
            # Extraer número
            score_match = re.search(r'\d+', score_text)
            if score_match:
                return float(score_match.group())
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating upsell opportunity: {e}")
            return 0.0
    
    async def generate_upsell_message(self, user: UserProfileResponse, context: Dict[str, Any]) -> UpsellMessage:
        """Generar mensaje de upsell personalizado usando Gemini"""
        
        # Determinar tipo de upsell
        if user.plan == "free":
            upsell_type = "upgrade_to_pro"
            target_plan = "PRO"
            benefits = "búsqueda de inversores y empresas"
            price = "$24.50/mes"
        elif user.plan == "pro":
            upsell_type = "upgrade_to_outreach"
            target_plan = "OUTREACH"
            benefits = "automatización de LinkedIn para contactar inversores"
            price = "$94.50/mes"
        else:
            # Plan outreach - solo credits
            upsell_type = "purchase_credits"
            target_plan = "créditos adicionales"
            benefits = "más créditos para continuar usando la plataforma"
            price = "desde $19"
        
        context_text = f"""
        USUARIO:
        - Plan: {user.plan}
        - Créditos: {user.credits_balance}
        - Proyecto stage: {context.get('project_stage', 'unknown')}
        
        CONTEXTO:
        - Último mensaje: "{context.get('last_user_message', '')}"
        - Nuestra respuesta: "{context.get('our_last_response', '')}"
        - Tipo de consulta: {context.get('query_type', 'general')}"
        - Idioma preferido: {user.preferred_language}
        """
        
        language = "español" if user.preferred_language == "es" else "inglés"
        
        prompt = f"""
        Eres un experto en copywriting y ventas para 0Bullshit, una plataforma que ayuda a startups a encontrar inversores.

        CONTEXTO DEL USUARIO:
        {context_text}
        
        UPSELL TARGET:
        - Tipo: {upsell_type}
        - Plan objetivo: {target_plan}
        - Beneficios: {benefits}
        - Precio: {price}
        
        INSTRUCCIONES:
        1. Escribe en {language}
        2. Máximo 2 frases cortas y directas
        3. Personaliza según el contexto específico del usuario
        4. Usa un tono como "Y-Combinator mentor" - directo, sin rodeos
        5. Conecta naturalmente con su situación actual
        6. No seas agresivo, sé útil
        
        EJEMPLOS DEL TONO:
        - "Para tu proyecto pre-seed, con el plan PRO puedes buscar inversores ángeles relevantes."
        - "Ya que encontraste inversores, con OUTREACH puedes automatizar el contacto por LinkedIn."
        
        Genera SOLO el mensaje de upsell (sin explicaciones adicionales):
        """
        
        try:
            from chat.judge import judge
            response = judge.model.generate_content(prompt)
            message_text = response.text.strip()
            
            # Limpiar comillas si las hay
            message_text = message_text.strip('"\'')
            
            # URLs de CTA
            cta_urls = {
                "upgrade_to_pro": "/upgrade/pro",
                "upgrade_to_outreach": "/upgrade/outreach", 
                "purchase_credits": "/purchase/credits"
            }
            
            cta_texts = {
                "upgrade_to_pro": "Upgrade a PRO",
                "upgrade_to_outreach": "Upgrade a OUTREACH",
                "purchase_credits": "Comprar Créditos"
            }
            
            return UpsellMessage(
                message=message_text,
                message_type=upsell_type,
                cta_text=cta_texts[upsell_type],
                cta_url=cta_urls[upsell_type],
                show_upsell=True
            )
            
        except Exception as e:
            logger.error(f"Error generating upsell message: {e}")
            return UpsellMessage(
                message="",
                message_type=upsell_type,
                cta_text="",
                cta_url="",
                show_upsell=False
            )

# Instancia global del sistema de upsell
upsell_judge = UpsellJudge()

async def check_and_generate_upsell(
    user: UserProfileResponse, 
    context: Dict[str, Any]
) -> Optional[UpsellMessage]:
    """Verificar si mostrar upsell y generar mensaje si corresponde"""
    
    try:
        should_show = await upsell_judge.should_show_upsell(user, context)
        
        if should_show:
            upsell_message = await upsell_judge.generate_upsell_message(user, context)
            
            # Actualizar tracker anti-saturación
            upsell_judge.last_upsell_tracker[str(user.id)] = 0
            
            return upsell_message
        else:
            # Incrementar contador de mensajes desde último upsell
            user_id = str(user.id)
            if user_id in upsell_judge.last_upsell_tracker:
                upsell_judge.last_upsell_tracker[user_id] += 1
            
            return None
            
    except Exception as e:
        logger.error(f"Error in upsell system: {e}")
        return None

# ==========================================
# PROJECT ENDPOINTS
# ==========================================

@app.post("/api/v1/projects", response_model=Project)
async def create_project(
    project_data: ProjectCreate,
    current_user: UserProfileResponse = Depends(get_current_user_auth)
):
    """Crear nuevo proyecto"""
    try:
        project = await db.create_project(current_user.id, project_data)
        logger.info(f"Project created: {project.id} by user {current_user.id}")
        return project
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail="Error creating project")

@app.get("/api/v1/projects", response_model=List[Project])
async def get_user_projects(current_user: UserProfileResponse = Depends(get_current_user_auth)):
    """Obtener todos los proyectos del usuario"""
    try:
        projects = await db.get_user_projects(current_user.id)
        return projects
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        raise HTTPException(status_code=500, detail="Error getting projects")

@app.get("/api/v1/projects/{project_id}", response_model=Project)
async def get_project(
    project_id: UUID,
    current_user: UserProfileResponse = Depends(get_current_user_auth)
):
    """Obtener proyecto específico"""
    try:
        project = await db.get_project(project_id, current_user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail="Error getting project")

@app.get("/api/v1/projects/{project_id}/completeness", response_model=CompletenessResponse)
async def get_project_completeness(
    project_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Obtener análisis de completitud del proyecto"""
    try:
        completeness = await chat_system.get_project_completeness(project_id, current_user)
        return completeness
    except Exception as e:
        logger.error(f"Error getting completeness: {e}")
        raise HTTPException(status_code=500, detail="Error analyzing project completeness")

# ==========================================
# CHAT ENDPOINTS
# ==========================================

@app.post("/api/v1/chat/welcome-message/{project_id}", response_model=WelcomeMessage)
async def generate_welcome_message(
    project_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Generar mensaje de bienvenida personalizado"""
    try:
        # Obtener proyecto
        project = await db.get_project(project_id, current_user)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Verificar si es primera vez
        user_projects = await db.get_user_projects(current_user)
        is_first_time = len(user_projects) <= 1
        
        # Generar mensaje
        welcome_msg = await welcome_system.generate_welcome_message(
            project, current_user, is_first_time
        )
        
        # Guardar como conversación
        welcome_conversation = ChatResponse(
            id=uuid4(),
            project_id=project_id,
            role="assistant",
            content=welcome_msg.message,
            ai_extractions={"welcome_type": welcome_msg.message_type},
            created_at=datetime.now()
        )
        await db.save_conversation(welcome_conversation)
        
        return welcome_msg
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating welcome message: {e}")
        raise HTTPException(status_code=500, detail="Error generating welcome message")

@app.post("/api/v1/chat/message", response_model=ChatResponse)
async def send_chat_message(
    message: ChatMessage,
    current_user: UserProfileResponse = Depends(get_current_user_auth)
):
    """Enviar mensaje de chat"""
    try:
        # Verificar créditos y deducir
        if not await check_and_deduct_credits(current_user.id, "chat_message"):
            raise HTTPException(
                status_code=402, 
                detail="Insufficient credits. Please upgrade your plan or purchase more credits."
            )
        
        # Verificar que el proyecto pertenece al usuario
        project = await db.get_project(message.project_id, current_user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Procesar mensaje
        response, search_results = await chat_system.process_message(
            message.content,
            message.project_id,
            current_user.id,
            websocket_callback=lambda msg: ws_manager.send_message(
                f"{current_user.id}_{message.project_id}", msg
            )
        )
        
        # Verificar si mostrar upsell
        upsell_context = {
            "last_user_message": message.content,
            "our_last_response": response.content,
            "project_stage": project.stage,
            "query_type": "chat",
            "has_searched_investors": search_results is not None and "investors" in str(search_results),
            "has_searched_companies": search_results is not None and "companies" in str(search_results),
            "project_count": len(await db.get_user_projects(current_user.id))
        }
        
        upsell_message = await check_and_generate_upsell(current_user, upsell_context)
        
        # Añadir upsell al response si existe
        if upsell_message and upsell_message.show_upsell:
            response.ai_extractions = response.ai_extractions or {}
            response.ai_extractions["upsell"] = upsell_message.dict()
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail="Error processing message")

@app.get("/api/v1/chat/conversations/{project_id}", response_model=List[ChatResponse])
async def get_conversation_history(
    project_id: UUID,
    limit: int = 50,
    current_user: UUID = Depends(get_current_user)
):
    """Obtener historial de conversación"""
    try:
        # Verificar proyecto
        project = await db.get_project(project_id, current_user)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Obtener conversaciones
        conversations = await db.get_conversations(project_id, limit)
        return conversations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(status_code=500, detail="Error getting conversation history")

@app.get("/api/v1/chat/conversations", response_model=ConversationList)
async def get_conversation_list(current_user: UUID = Depends(get_current_user)):
    """Obtener lista de conversaciones (como ChatGPT)"""
    try:
        conversations = await db.get_conversation_titles(current_user)
        return ConversationList(
            conversations=conversations,
            total=len(conversations)
        )
    except Exception as e:
        logger.error(f"Error getting conversation list: {e}")
        raise HTTPException(status_code=500, detail="Error getting conversation list")

# ==========================================
# LINKEDIN ACCOUNT ENDPOINTS
# ==========================================

@app.get("/api/v1/linkedin/accounts")
async def get_linkedin_accounts(current_user: UUID = Depends(get_current_user)):
    """Obtener cuentas de LinkedIn del usuario"""
    try:
        accounts = await db.get_user_linkedin_accounts(current_user)
        return {
            "success": True,
            "accounts": accounts,
            "total": len(accounts)
        }
    except Exception as e:
        logger.error(f"Error getting LinkedIn accounts: {e}")
        raise HTTPException(status_code=500, detail="Error getting LinkedIn accounts")

@app.post("/api/v1/linkedin/connect")
async def connect_linkedin_account(
    success_url: str,
    failure_url: str,
    current_user: UUID = Depends(get_current_user)
):
    """Iniciar proceso de conexión de LinkedIn"""
    try:
        from integrations.unipile_client import unipile_client
        
        if not unipile_client:
            raise HTTPException(status_code=503, detail="LinkedIn integration not available")
        
        # Crear webhook URL (deberías usar tu dominio real)
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        notify_url = f"{base_url}/api/v1/webhooks/linkedin/auth-success"
        
        # Crear link de autenticación
        auth_data = await unipile_client.create_hosted_auth_link(
            user_id=str(current_user),
            success_url=success_url,
            failure_url=failure_url,
            notify_url=notify_url
        )
        
        return {
            "success": True,
            "auth_url": auth_data["url"],
            "message": "Please visit the auth_url to connect your LinkedIn account"
        }
        
    except Exception as e:
        logger.error(f"Error connecting LinkedIn account: {e}")
        raise HTTPException(status_code=500, detail="Error connecting LinkedIn account")

# ==========================================
# WEBSOCKET ENDPOINT
# ==========================================

@app.websocket("/ws/chat/{project_id}")
async def websocket_chat(websocket: WebSocket, project_id: UUID):
    """WebSocket para chat en tiempo real"""
    
    # Obtener user_id del query param o token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return
    
    try:
        from api.utils import decode_jwt_token
        user_payload = decode_jwt_token(token)
        user_id = UUID(user_payload.get("sub"))
    except Exception:
        await websocket.close(code=4001, reason="Invalid authentication token")
        return
    
    # Verificar proyecto
    try:
        project = await db.get_project(project_id, user_id)
        if not project:
            await websocket.close(code=4004, reason="Project not found")
            return
    except Exception:
        await websocket.close(code=4000, reason="Error verifying project")
        return
    
    # Conectar WebSocket
    client_id = f"{user_id}_{project_id}"
    await ws_manager.connect(websocket, client_id)
    
    try:
        # Mantener conexión viva
        while True:
            try:
                # Esperar por mensajes del cliente (keepalive)
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Echo del mensaje para keepalive
                await websocket.send_text(json.dumps({
                    "type": "keepalive",
                    "timestamp": datetime.now().isoformat()
                }))
                
            except asyncio.TimeoutError:
                # Enviar ping
                await websocket.send_text(json.dumps({"type": "ping"}))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        ws_manager.disconnect(client_id)

# ==========================================
# USER ENDPOINTS
# ==========================================

@app.get("/api/v1/user/profile", response_model=UserProfile)
async def get_user_profile(current_user: UUID = Depends(get_current_user)):
    """Obtener perfil del usuario"""
    try:
        profile = await db.get_user_profile(current_user)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail="Error getting user profile")

# ==========================================
# ADMIN/DEBUG ENDPOINTS
# ==========================================

@app.post("/api/v1/admin/force-librarian-analysis/{project_id}")
async def force_librarian_analysis(
    project_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Forzar análisis del bibliotecario (para testing)"""
    try:
        # Obtener conversaciones
        conversations = await db.get_conversations(project_id, limit=10)
        conversation_texts = [conv.content for conv in conversations]
        
        # Forzar análisis
        result = await librarian.force_analysis(project_id, current_user, conversation_texts)
        
        return ApiResponse(
            success=True,
            message="Librarian analysis completed",
            data=result.dict() if result else None
        )
        
    except Exception as e:
        logger.error(f"Error in force librarian analysis: {e}")
        raise HTTPException(status_code=500, detail="Error in librarian analysis")

@app.get("/api/v1/admin/judge-analysis/{project_id}")
async def debug_judge_analysis(
    project_id: UUID,
    message: str,
    current_user: UUID = Depends(get_current_user)
):
    """Debug: Obtener análisis del juez sin procesar mensaje"""
    try:
        project = await db.get_project(project_id, current_user)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        decision = await judge.analyze_user_intent(message, project, [])
        
        return ApiResponse(
            success=True,
            message="Judge analysis completed",
            data=decision.dict()
        )
        
    except Exception as e:
        logger.error(f"Error in judge analysis: {e}")
        raise HTTPException(status_code=500, detail="Error in judge analysis")

# ==========================================
# FEATURE FLAGS ENDPOINT
# ==========================================

@app.get("/api/v1/features")
async def get_feature_flags(current_user: UUID = Depends(get_current_user)):
    """Obtener feature flags para el usuario"""
    try:
        from api.utils import is_feature_enabled
        
        features = {
            "linkedin_outreach": is_feature_enabled("linkedin_outreach", current_user),
            "ai_message_generation": is_feature_enabled("ai_message_generation", current_user),
            "advanced_analytics": is_feature_enabled("advanced_analytics", current_user),
            "auto_follow_up": is_feature_enabled("auto_follow_up", current_user)
        }
        
        return {
            "success": True,
            "features": features
        }
        
    except Exception as e:
        logger.error(f"Error getting feature flags: {e}")
        raise HTTPException(status_code=500, detail="Error getting feature flags")

# ==========================================
# ERROR HANDLERS
# ==========================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# ==========================================
# STARTUP/SHUTDOWN EVENTS
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Eventos de inicio"""
    logger.info("🚀 0Bullshit Chat API starting up...")
    
    # Verificar conexiones
    try:
        # Test Supabase
        db.supabase.table("users").select("id").limit(1).execute()
        logger.info("✅ Supabase connection OK")
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {e}")
    
    try:
        # Test Gemini
        test_response = judge.model.generate_content("Test")
        logger.info("✅ Gemini API connection OK")
    except Exception as e:
        logger.error(f"❌ Gemini API connection failed: {e}")
    
    try:
        # Test Unipile (if configured)
        from integrations.unipile_client import unipile_client
        if unipile_client and unipile_client.api_key:
            accounts = await unipile_client.get_accounts()
            logger.info("✅ Unipile connection OK")
        else:
            logger.info("⚠️ Unipile not configured - LinkedIn features disabled")
    except Exception as e:
        logger.error(f"❌ Unipile connection failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Eventos de cierre"""
    logger.info("🛑 0Bullshit Chat API shutting down...")
    
    # Cerrar conexiones WebSocket
    for client_id in list(ws_manager.active_connections.keys()):
        ws_manager.disconnect(client_id)

# ==========================================
# INCLUDE ROUTERS
# ==========================================

# Incluir todos los routers
app.include_router(linkedin_router, prefix="/api/v1", tags=["LinkedIn"])
app.include_router(outreach_router, prefix="/api/v1", tags=["Outreach"])
app.include_router(webhooks_router, prefix="/api/v1", tags=["Webhooks"])
app.include_router(campaigns_router, prefix="/api/v1", tags=["Campaigns"])
app.include_router(payments_router, prefix="/api/v1", tags=["Payments"])

# ==========================================
# ROOT ENDPOINT
# ==========================================

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "name": "0Bullshit Chat API",
        "version": "2.0.0",
        "description": "API para el sistema de chat con IA especializado en startups con outreach automatizado",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "AI Chat System",
            "Investor Search",
            "Company Search", 
            "Y-Combinator Mentoring",
            "LinkedIn Outreach",
            "Campaign Management",
            "Real-time Analytics"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )
