"""
Authentication endpoints for InstaAI API.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
import secrets

from ..database import get_db
from ..database.models import User
from ..utils.email import send_verification_email, send_password_reset_email

router = APIRouter()

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
MAX_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCK_DURATION_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    subscription_tier: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class TokenData(BaseModel):
    email: Optional[str] = None


# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure current user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Endpoints
@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        is_active=True,
        is_verified=False,
        subscription_tier="free"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Generate and send verification email (non-blocking — never fails registration)
    verify_token = secrets.token_urlsafe(32)
    _verify_tokens[verify_token] = (
        db_user.id,
        datetime.utcnow() + timedelta(hours=VERIFY_TOKEN_EXPIRE_HOURS),
    )
    import asyncio
    asyncio.create_task(
        send_verification_email(db_user.email, verify_token, db_user.full_name)
    )

    # Create access token
    access_token = create_access_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": db_user
    }


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with email and password."""
    # Find user
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is locked
    if user.account_locked_until and user.account_locked_until > datetime.utcnow():
        time_remaining = (user.account_locked_until - datetime.utcnow()).total_seconds() / 60
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked. Try again in {int(time_remaining)} minutes.",
        )

    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        # Increment failed login attempts
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

        # Lock account if max attempts exceeded
        if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.account_locked_until = datetime.utcnow() + timedelta(minutes=ACCOUNT_LOCK_DURATION_MINUTES)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account locked due to too many failed login attempts. Try again in {ACCOUNT_LOCK_DURATION_MINUTES} minutes.",
            )

        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect email or password. {MAX_LOGIN_ATTEMPTS - user.failed_login_attempts} attempts remaining.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reset failed login attempts and update last login
    user.failed_login_attempts = 0
    user.account_locked_until = None
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Create access token
    access_token = create_access_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user profile."""
    return current_user


@router.post("/google", response_model=Token)
async def google_auth(google_token: str, db: Session = Depends(get_db)):
    """
    Authenticate with Google OAuth token.
    TODO: Implement Google token verification.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google OAuth not yet implemented"
    )


# ---------------------------------------------------------------------------
# Token stores (in-memory — single-instance; swap for Redis in multi-instance)
# ---------------------------------------------------------------------------

# email_verify:{token} → (user_id, expires_at)
_verify_tokens: dict[str, tuple[int, datetime]] = {}

VERIFY_TOKEN_EXPIRE_HOURS = 24

# reset:{token} → (email, expires_at)
_reset_tokens: dict[str, tuple[str, datetime]] = {}  # token → (email, expires_at)

RESET_TOKEN_EXPIRE_MINUTES = 30


# ---------------------------------------------------------------------------
# Email verification endpoints
# ---------------------------------------------------------------------------

class ResendVerificationRequest(BaseModel):
    email: EmailStr


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Confirm an email address using the token from the verification email.
    Called by the frontend after the user clicks the link.
    """
    entry = _verify_tokens.get(token)
    if not entry:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user_id, expires_at = entry
    if datetime.utcnow() > expires_at:
        del _verify_tokens[token]
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    if user.is_verified:
        del _verify_tokens[token]
        return {"message": "Email already verified"}

    user.is_verified = True
    db.commit()
    del _verify_tokens[token]

    return {"message": "Email verified successfully"}


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(
    request: ResendVerificationRequest,
    db: Session = Depends(get_db),
):
    """
    Re-send the verification email. Always returns 200 to avoid leaking
    which emails are registered. Throttles to one token per user (replaces old one).
    """
    user = db.query(User).filter(User.email == request.email).first()
    if user and not user.is_verified:
        # Invalidate any existing tokens for this user
        expired = [t for t, (uid, _) in _verify_tokens.items() if uid == user.id]
        for t in expired:
            del _verify_tokens[t]

        token = secrets.token_urlsafe(32)
        _verify_tokens[token] = (
            user.id,
            datetime.utcnow() + timedelta(hours=VERIFY_TOKEN_EXPIRE_HOURS),
        )
        import asyncio
        asyncio.create_task(
            send_verification_email(user.email, token, user.full_name)
        )

    return {"message": "If that email is registered and unverified, a new link has been sent."}


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Generate and email a password reset token. Always returns 200 so we
    don't leak which emails are registered.
    """
    user = db.query(User).filter(User.email == request.email).first()
    if user:
        token = secrets.token_urlsafe(32)
        expires = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
        _reset_tokens[token] = (user.email, expires)
        import asyncio
        asyncio.create_task(
            send_password_reset_email(user.email, token, user.full_name)
        )

    return {"message": "If that email is registered you will receive a reset link."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Exchange a valid reset token for a new password."""
    entry = _reset_tokens.get(request.token)
    if not entry:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    email, expires_at = entry
    if datetime.utcnow() > expires_at:
        del _reset_tokens[request.token]
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if len(request.new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    user.hashed_password = pwd_context.hash(request.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    del _reset_tokens[request.token]
    return {"message": "Password updated successfully"}
