# api/auth.py
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
import logging

from database.database import db

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# ==========================================
# PYDANTIC MODELS
# ==========================================

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenRefresh(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    plan: str
    credits: int
    daily_credits_remaining: int
    created_at: datetime
    subscription: Optional[Dict[str, Any]] = None

class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class MessageResponse(BaseModel):
    message: str

# ==========================================
# AUTHENTICATION UTILS
# ==========================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token (longer expiration)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)  # 30 days for refresh token
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UUID:
    """Get current user from JWT token"""
    try:
        payload = verify_token(credentials.credentials, "access")
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # Verify user exists in database
        user = await db.get_user_by_id(UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return UUID(user_id)
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# ==========================================
# AUTHENTICATION ENDPOINTS
# ==========================================

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegister):
    """Register new user"""
    try:
        # Check if user already exists
        existing_user = await db.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Create user
        user_id = uuid4()
        user_dict = {
            "id": str(user_id),
            "email": user_data.email,
            "password": hashed_password,
            "name": user_data.name,
            "plan": "free",
            "credits": 200,  # Free plan initial credits
            "daily_credits_used": 0,
            "last_credit_reset": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        result = db.supabase.table("users").insert(user_dict).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        created_user = result.data[0]
        
        # Create tokens
        token_data = {"sub": str(user_id), "email": user_data.email}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Store refresh token
        await db.store_refresh_token(user_id, refresh_token)
        
        # Prepare response
        user_response = UserResponse(
            id=user_id,
            email=created_user["email"],
            name=created_user["name"],
            plan=created_user["plan"],
            credits=created_user["credits"],
            daily_credits_remaining=_calculate_daily_credits_remaining(created_user),
            created_at=datetime.fromisoformat(created_user["created_at"])
        )
        
        logger.info(f"User registered successfully: {user_data.email}")
        
        return AuthResponse(
            user=user_response,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=JWT_EXPIRATION_HOURS * 3600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/login", response_model=AuthResponse)
async def login_user(user_data: UserLogin):
    """User login"""
    try:
        # Get user by email
        user = await db.get_user_by_email(user_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(user_data.password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Update last login
        await db.update_user_last_login(UUID(user["id"]))
        
        # Create tokens
        token_data = {"sub": user["id"], "email": user["email"]}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Store refresh token
        await db.store_refresh_token(UUID(user["id"]), refresh_token)
        
        # Get subscription info if exists
        subscription = await db.get_user_subscription(UUID(user["id"]))
        
        # Prepare response
        user_response = UserResponse(
            id=UUID(user["id"]),
            email=user["email"],
            name=user["name"],
            plan=user["plan"],
            credits=user["credits"],
            daily_credits_remaining=_calculate_daily_credits_remaining(user),
            created_at=datetime.fromisoformat(user["created_at"]),
            subscription=subscription
        )
        
        logger.info(f"User logged in successfully: {user_data.email}")
        
        return AuthResponse(
            user=user_response,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=JWT_EXPIRATION_HOURS * 3600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token_data: TokenRefresh):
    """Refresh access token"""
    try:
        # Verify refresh token
        payload = verify_token(token_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if refresh token is stored and valid
        is_valid = await db.is_refresh_token_valid(UUID(user_id), token_data.refresh_token)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Get user info
        user = await db.get_user_by_id(UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new tokens
        new_token_data = {"sub": user_id, "email": user["email"]}
        new_access_token = create_access_token(new_token_data)
        new_refresh_token = create_refresh_token(new_token_data)
        
        # Store new refresh token and invalidate old one
        await db.store_refresh_token(UUID(user_id), new_refresh_token)
        await db.invalidate_refresh_token(UUID(user_id), token_data.refresh_token)
        
        logger.info(f"Token refreshed for user: {user['email']}")
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=JWT_EXPIRATION_HOURS * 3600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UUID = Depends(get_current_user)):
    """Get current user information"""
    try:
        user = await db.get_user_by_id(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get subscription info if exists
        subscription = await db.get_user_subscription(current_user)
        
        return UserResponse(
            id=current_user,
            email=user["email"],
            name=user["name"],
            plan=user["plan"],
            credits=user["credits"],
            daily_credits_remaining=_calculate_daily_credits_remaining(user),
            created_at=datetime.fromisoformat(user["created_at"]),
            subscription=subscription
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/logout", response_model=MessageResponse)
async def logout_user(
    token_data: TokenRefresh,
    current_user: UUID = Depends(get_current_user)
):
    """User logout - invalidate refresh token"""
    try:
        # Invalidate refresh token
        await db.invalidate_refresh_token(current_user, token_data.refresh_token)
        
        logger.info(f"User logged out: {current_user}")
        
        return MessageResponse(message="Successfully logged out")
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def _calculate_daily_credits_remaining(user: Dict[str, Any]) -> int:
    """Calculate remaining daily credits for user"""
    plan = user.get("plan", "free")
    daily_credits_used = user.get("daily_credits_used", 0)
    last_reset = user.get("last_credit_reset")
    
    # Daily credit limits by plan
    daily_limits = {
        "free": 50,
        "pro": 150,
        "outreach": 200
    }
    
    daily_limit = daily_limits.get(plan, 50)
    
    # Check if credits should reset (new day)
    if last_reset:
        last_reset_date = datetime.fromisoformat(last_reset).date()
        today = datetime.now().date()
        
        if today > last_reset_date:
            # Reset daily credits
            daily_credits_used = 0
    
    return max(0, daily_limit - daily_credits_used)

# ==========================================
# OPTIONAL: PASSWORD RESET (BASIC)
# ==========================================

@router.post("/request-password-reset")
async def request_password_reset(email: EmailStr):
    """Request password reset (placeholder - implement with email service)"""
    try:
        user = await db.get_user_by_email(email)
        if not user:
            # Don't reveal if email exists or not
            return MessageResponse(message="If the email exists, a reset link has been sent")
        
        # TODO: Implement email service integration
        # - Generate secure reset token
        # - Store token with expiration
        # - Send email with reset link
        
        logger.info(f"Password reset requested for: {email}")
        return MessageResponse(message="If the email exists, a reset link has been sent")
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )