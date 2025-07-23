# api/auth.py
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt

from config.settings import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
from database.database import Database
from models.schemas import MessageResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize router and security
router = APIRouter()
security = HTTPBearer()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database instance
db = Database()

# ==========================================
# PYDANTIC MODELS
# ==========================================

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    plan: str
    credits: int
    daily_credits_remaining: int
    onboarding_completed: bool
    created_at: datetime

class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    expires_in: int

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

# ==========================================
# PASSWORD UTILITIES
# ==========================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

# ==========================================
# JWT UTILITIES
# ==========================================

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)  # Refresh tokens last 30 days
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# ==========================================
# AUTHENTICATION DEPENDENCY
# ==========================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UUID:
    """Get current user from JWT token"""
    try:
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        return UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format"
        )

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def _calculate_daily_credits_remaining(user_data: dict) -> int:
    """Calculate remaining daily credits for user"""
    try:
        daily_limit = user_data.get("daily_credits_limit", 200)
        daily_used = user_data.get("daily_credits_used", 0)
        last_reset = user_data.get("last_credit_reset")
        
        # Check if we need to reset daily credits
        if last_reset:
            last_reset_date = datetime.fromisoformat(last_reset).date()
            today = datetime.now().date()
            
            if today > last_reset_date:
                # Reset daily credits
                daily_used = 0
        
        return max(0, daily_limit - daily_used)
    except Exception as e:
        logger.error(f"Error calculating daily credits: {e}")
        return 0

# ==========================================
# AUTHENTICATION ENDPOINTS
# ==========================================

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegister):
    """Register new user with custom JWT auth"""
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
            "credits": 200,
            "daily_credits_used": 0,
            "daily_credits_limit": 200,
            "last_credit_reset": datetime.now().isoformat(),
            "onboarding_completed": False,
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
        
        # Create user response
        user_response = UserResponse(
            id=user_id,
            email=created_user["email"],
            name=created_user["name"],
            plan=created_user["plan"],
            credits=created_user["credits"],
            daily_credits_remaining=_calculate_daily_credits_remaining(created_user),
            onboarding_completed=created_user["onboarding_completed"],
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
async def login_user(login_data: UserLogin):
    """Login user with email/password"""
    try:
        # Get user by email
        user = await db.get_user_by_email(login_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password
        if not verify_password(login_data.password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Update last login
        await db.update_user_last_login(UUID(user["id"]))
        
        # Create tokens
        token_data = {"sub": user["id"], "email": user["email"]}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Store refresh token
        await db.store_refresh_token(UUID(user["id"]), refresh_token)
        
        # Create user response
        user_response = UserResponse(
            id=UUID(user["id"]),
            email=user["email"],
            name=user["name"],
            plan=user["plan"],
            credits=user["credits"],
            daily_credits_remaining=_calculate_daily_credits_remaining(user),
            onboarding_completed=user["onboarding_completed"],
            created_at=datetime.fromisoformat(user["created_at"])
        )
        
        logger.info(f"User logged in successfully: {login_data.email}")
        
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
    """Refresh access token using refresh token"""
    try:
        # Verify refresh token
        payload = verify_token(token_data.refresh_token, "refresh")
        user_id = UUID(payload.get("sub"))
        
        # Check if refresh token is valid in database
        if not await db.is_refresh_token_valid(user_id, token_data.refresh_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user to ensure they still exist
        user = await db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new tokens
        new_token_data = {"sub": str(user_id), "email": user["email"]}
        new_access_token = create_access_token(new_token_data)
        new_refresh_token = create_refresh_token(new_token_data)
        
        # Invalidate old refresh token and store new one
        await db.invalidate_refresh_token(user_id, token_data.refresh_token)
        await db.store_refresh_token(user_id, new_refresh_token)
        
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

@router.post("/logout")
async def logout_user(
    token_data: TokenRefresh,
    current_user: UUID = Depends(get_current_user)
):
    """Logout user by invalidating refresh token"""
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
# USER INFO ENDPOINTS
# ==========================================

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
        
        return UserResponse(
            id=current_user,
            email=user["email"],
            name=user["name"],
            plan=user["plan"],
            credits=user["credits"],
            daily_credits_remaining=_calculate_daily_credits_remaining(user),
            onboarding_completed=user["onboarding_completed"],
            created_at=datetime.fromisoformat(user["created_at"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ==========================================
# PASSWORD MANAGEMENT ENDPOINTS
# ==========================================

@router.post("/request-password-reset")
async def request_password_reset(reset_data: PasswordResetRequest):
    """Request password reset using Supabase Auth"""
    try:
        # Use Supabase Auth for password reset
        response = db.supabase.auth.reset_password_email(
            email=reset_data.email,
            options={
                "redirect_to": "https://your-frontend-domain.com/reset-password"  # Update with actual frontend URL
            }
        )
        
        logger.info(f"Password reset requested for: {reset_data.email}")
        return MessageResponse(
            message="If the email exists, a reset link has been sent to your email"
        )
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        # Don't reveal if email exists or not
        return MessageResponse(
            message="If the email exists, a reset link has been sent to your email"
        )

@router.post("/reset-password")
async def reset_password(reset_data: PasswordResetConfirm):
    """Reset password with token from email"""
    try:
        # Use Supabase Auth to update password with reset token
        response = db.supabase.auth.update_user({
            "password": reset_data.new_password
        }, access_token=reset_data.token)
        
        if response.user:
            logger.info(f"Password reset successful for user: {response.user.id}")
            return MessageResponse(message="Password has been reset successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: UUID = Depends(get_current_user)
):
    """Change user password (requires current password)"""
    try:
        # Get current user
        user = await db.get_user_by_id(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(password_data.current_password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_hashed_password = hash_password(password_data.new_password)
        
        # Update password in database
        update_data = {
            "password": new_hashed_password,
            "updated_at": datetime.now().isoformat()
        }
        
        result = db.supabase.table("users")\
            .update(update_data)\
            .eq("id", str(current_user))\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
        
        # Invalidate all refresh tokens for security
        await db.invalidate_all_refresh_tokens(current_user)
        
        logger.info(f"Password changed for user: {current_user}")
        return MessageResponse(
            message="Password changed successfully. Please log in again."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ==========================================
# UTILITY FUNCTION (for other modules)
# ==========================================

def _calculate_daily_credits_remaining(user_data: dict) -> int:
    """Calculate remaining daily credits for user"""
    try:
        daily_limit = user_data.get("daily_credits_limit", 200)
        daily_credits_used = user_data.get("daily_credits_used", 0)
        last_reset = user_data.get("last_credit_reset")
        
        if last_reset:
            last_reset_date = datetime.fromisoformat(last_reset).date()
            today = datetime.now().date()
            
            if today > last_reset_date:
                # Reset daily credits
                daily_credits_used = 0
        
        return max(0, daily_limit - daily_credits_used)
    
    except Exception as e:
        logger.error(f"Error calculating daily credits: {e}")
        return 0