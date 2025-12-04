"""
OAuth Authentication Routes for InstaAI Studio
Handles Google, Facebook, and Apple Sign In callbacks
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx
import jwt
from typing import Optional
import os

from ...database import get_db
from ...database.models import User
from ..auth import create_access_token, get_password_hash
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["oauth"])

# OAuth callback request models
class GoogleCallbackRequest(BaseModel):
    code: str
    redirectUri: str
    codeVerifier: Optional[str] = None

class FacebookCallbackRequest(BaseModel):
    code: str
    redirectUri: str

class AppleCallbackRequest(BaseModel):
    code: Optional[str] = None
    identityToken: Optional[str] = None
    authorizationCode: Optional[str] = None
    user: Optional[str] = None
    fullName: Optional[dict] = None
    email: Optional[str] = None

# OAuth Configuration from environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", os.getenv("INSTAGRAM_APP_ID"))
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", os.getenv("INSTAGRAM_APP_SECRET"))
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "com.instaai.studio")
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID")
APPLE_KEY_ID = os.getenv("APPLE_KEY_ID")


@router.post("/google/callback")
async def google_oauth_callback(
    request: GoogleCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback
    Exchange authorization code for access token and create/login user
    """
    try:
        # Exchange authorization code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": request.code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": request.redirectUri,
                    "grant_type": "authorization_code",
                    "code_verifier": request.codeVerifier,
                }
            )

            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to exchange authorization code for access token"
                )

            tokens = token_response.json()
            access_token = tokens.get("access_token")

            # Get user info from Google
            user_info_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if user_info_response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to get user info from Google"
                )

            user_info = user_info_response.json()

        # Find or create user
        user = db.query(User).filter(User.email == user_info["email"]).first()

        if not user:
            # Create new user
            user = User(
                email=user_info["email"],
                full_name=user_info.get("name", ""),
                hashed_password=get_password_hash("oauth_user"),  # Placeholder password
                subscription_tier="free",
                created_at=datetime.utcnow(),
                oauth_provider="google",
                oauth_id=user_info["id"]
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update OAuth info if not set
            if not user.oauth_provider:
                user.oauth_provider = "google"
                user.oauth_id = user_info["id"]
                db.commit()

        # Create JWT token for the user
        app_access_token = create_access_token(data={"sub": user.email})

        return {
            "access_token": app_access_token,
            "token_type": "bearer",
            "refresh_token": tokens.get("refresh_token"),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.full_name,
                "picture": user_info.get("picture"),
            }
        }

    except Exception as e:
        print(f"Google OAuth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/facebook/callback")
async def facebook_oauth_callback(
    request: FacebookCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    Handle Facebook OAuth callback
    Exchange authorization code for access token and create/login user
    """
    try:
        # Exchange authorization code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "client_id": FACEBOOK_APP_ID,
                    "client_secret": FACEBOOK_APP_SECRET,
                    "redirect_uri": request.redirectUri,
                    "code": request.code,
                }
            )

            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to exchange authorization code for access token"
                )

            tokens = token_response.json()
            access_token = tokens.get("access_token")

            # Get user info from Facebook
            user_info_response = await client.get(
                "https://graph.facebook.com/me",
                params={
                    "fields": "id,name,email,picture",
                    "access_token": access_token
                }
            )

            if user_info_response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to get user info from Facebook"
                )

            user_info = user_info_response.json()

        # Find or create user
        user = db.query(User).filter(User.email == user_info.get("email", "")).first()

        if not user and user_info.get("email"):
            # Create new user
            user = User(
                email=user_info["email"],
                full_name=user_info.get("name", ""),
                hashed_password=get_password_hash("oauth_user"),
                subscription_tier="free",
                created_at=datetime.utcnow(),
                oauth_provider="facebook",
                oauth_id=user_info["id"]
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        elif user:
            # Update OAuth info if not set
            if not user.oauth_provider:
                user.oauth_provider = "facebook"
                user.oauth_id = user_info["id"]
                db.commit()

        if not user:
            raise HTTPException(
                status_code=400,
                detail="Email not provided by Facebook"
            )

        # Create JWT token for the user
        app_access_token = create_access_token(data={"sub": user.email})

        return {
            "access_token": app_access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.full_name,
                "picture": user_info.get("picture", {}).get("data", {}).get("url"),
            }
        }

    except Exception as e:
        print(f"Facebook OAuth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apple/callback")
async def apple_oauth_callback(
    request: AppleCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    Handle Apple Sign In callback
    Verify identity token and create/login user
    """
    try:
        # Decode the identity token (simplified - in production, verify signature)
        identity_token = request.identityToken

        if not identity_token:
            raise HTTPException(
                status_code=400,
                detail="Identity token is required"
            )

        # Decode JWT (without verification for now - add verification in production)
        decoded = jwt.decode(identity_token, options={"verify_signature": False})

        apple_user_id = decoded.get("sub")
        email = request.email or decoded.get("email")

        if not email:
            raise HTTPException(
                status_code=400,
                detail="Email not provided by Apple"
            )

        # Find or create user
        user = db.query(User).filter(User.email == email).first()

        if not user:
            # Create new user
            full_name = ""
            if request.fullName:
                first = request.fullName.get("givenName", "")
                last = request.fullName.get("familyName", "")
                full_name = f"{first} {last}".strip()

            user = User(
                email=email,
                full_name=full_name or "Apple User",
                hashed_password=get_password_hash("oauth_user"),
                subscription_tier="free",
                created_at=datetime.utcnow(),
                oauth_provider="apple",
                oauth_id=apple_user_id
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update OAuth info if not set
            if not user.oauth_provider:
                user.oauth_provider = "apple"
                user.oauth_id = apple_user_id
                db.commit()

        # Create JWT token for the user
        app_access_token = create_access_token(data={"sub": user.email})

        return {
            "access_token": app_access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.full_name,
            }
        }

    except jwt.DecodeError as e:
        print(f"Apple JWT decode error: {e}")
        raise HTTPException(status_code=400, detail="Invalid identity token")
    except Exception as e:
        print(f"Apple OAuth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
