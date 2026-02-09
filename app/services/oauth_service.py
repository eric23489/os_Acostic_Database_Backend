"""OAuth service for Google authentication."""

from datetime import UTC, datetime
from urllib.parse import urlencode

import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import UserInfo

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class OAuthService:
    """Service for handling Google OAuth authentication."""

    def __init__(self, db: Session):
        self.db = db

    def get_google_authorization_url(self, state: str | None = None) -> str:
        """Generate Google OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection.

        Returns:
            Google OAuth authorization URL.
        """
        if not settings.google_oauth_client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth is not configured",
            )

        params = {
            "client_id": settings.google_oauth_client_id,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
        }
        if state:
            params["state"] = state

        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange authorization code for access tokens.

        Args:
            code: Authorization code from Google.

        Returns:
            Token response from Google.
        """
        client_id = settings.google_oauth_client_id
        client_secret = settings.google_oauth_client_secret
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth is not configured",
            )

        response = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_oauth_redirect_uri,
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to exchange authorization code",
            )

        return response.json()

    def get_google_user_info(self, access_token: str) -> dict:
        """Fetch user info from Google.

        Args:
            access_token: Google access token.

        Returns:
            User info from Google.
        """
        response = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to fetch user info from Google",
            )

        return response.json()

    def authenticate_with_google(self, code: str) -> tuple[UserInfo, bool]:
        """Authenticate user with Google OAuth.

        This handles:
        1. New user registration via Google
        2. Existing user login via Google
        3. Auto-linking Google to existing local account with same email

        Args:
            code: Authorization code from Google.

        Returns:
            Tuple of (user, is_new_user).
        """
        # Exchange code for tokens
        tokens = self.exchange_code_for_tokens(code)
        access_token = tokens.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No access token in response",
            )

        # Get user info from Google
        google_user = self.get_google_user_info(access_token)
        google_sub = google_user.get("sub")
        email = google_user.get("email")
        name = google_user.get("name")

        if not google_sub or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user info from Google",
            )

        # Check if user with this Google sub already exists
        existing_oauth_user = (
            self.db.query(UserInfo)
            .filter(
                UserInfo.oauth_provider == "google",
                UserInfo.oauth_sub == google_sub,
                UserInfo.is_deleted.is_(False),
            )
            .first()
        )

        if existing_oauth_user:
            # Existing Google user - update last login
            existing_oauth_user.last_login_at = datetime.now(UTC)
            self.db.commit()
            return existing_oauth_user, False

        # Check if user with this email already exists (local account)
        existing_email_user = (
            self.db.query(UserInfo)
            .filter(
                UserInfo.email == email,
                UserInfo.is_deleted.is_(False),
            )
            .first()
        )

        if existing_email_user:
            # Auto-link Google to existing local account
            existing_email_user.oauth_provider = "google"
            existing_email_user.oauth_sub = google_sub
            existing_email_user.is_verified = True
            existing_email_user.last_login_at = datetime.now(UTC)
            self.db.commit()
            return existing_email_user, False

        # Check for soft-deleted user with same email
        deleted_user = (
            self.db.query(UserInfo)
            .filter(
                UserInfo.email == email,
                UserInfo.is_deleted.is_(True),
            )
            .first()
        )

        if deleted_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This account has been deactivated. Please contact support.",
            )

        # Create new user
        new_user = UserInfo(
            email=email,
            full_name=name,
            oauth_provider="google",
            oauth_sub=google_sub,
            is_verified=True,  # Google OAuth auto-verifies
            password_hash=None,
        )

        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        return new_user, True

    def link_google_account(self, user: UserInfo, code: str) -> UserInfo:
        """Link Google account to existing user.

        Args:
            user: Current logged-in user.
            code: Authorization code from Google.

        Returns:
            Updated user.
        """
        # Check if already linked
        if user.oauth_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account already linked to Google",
            )

        # Exchange code and get Google user info
        tokens = self.exchange_code_for_tokens(code)
        access_token = tokens.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No access token in response",
            )

        google_user = self.get_google_user_info(access_token)
        google_sub = google_user.get("sub")

        if not google_sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user info from Google",
            )

        # Check if this Google account is already linked to another user
        existing_oauth_user = (
            self.db.query(UserInfo)
            .filter(
                UserInfo.oauth_provider == "google",
                UserInfo.oauth_sub == google_sub,
                UserInfo.is_deleted.is_(False),
                UserInfo.id != user.id,
            )
            .first()
        )

        if existing_oauth_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This Google account is already linked to another user",
            )

        # Link the account
        user.oauth_provider = "google"
        user.oauth_sub = google_sub
        self.db.commit()
        self.db.refresh(user)

        return user

    def unlink_google_account(self, user: UserInfo) -> UserInfo:
        """Unlink Google account from user.

        Args:
            user: Current logged-in user.

        Returns:
            Updated user.
        """
        # Check if linked
        if not user.oauth_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is not linked to Google",
            )

        # Check if user has password (required to unlink)
        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please set a password before unlinking Google account",
            )

        # Unlink
        user.oauth_provider = None
        user.oauth_sub = None
        self.db.commit()
        self.db.refresh(user)

        return user


def create_jwt_for_user(user: UserInfo) -> str:
    """Create JWT access token for user.

    Args:
        user: User to create token for.

    Returns:
        JWT access token.
    """
    return create_access_token({"sub": user.email})
