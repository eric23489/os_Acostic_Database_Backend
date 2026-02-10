"""OAuth API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.oauth import GoogleAuthUrl, OAuthCallbackResponse
from app.services.oauth_service import OAuthService, create_jwt_for_user

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/google/authorize", response_model=GoogleAuthUrl)
def google_authorize(
    state: str | None = Query(default=None, description="Optional state for CSRF"),
    db: Session = Depends(get_db),
):
    """Get Google OAuth authorization URL.

    Returns the URL to redirect the user to for Google OAuth consent.
    """
    service = OAuthService(db)
    auth_url = service.get_google_authorization_url(state)
    return GoogleAuthUrl(authorization_url=auth_url)


@router.get("/google/callback", response_model=OAuthCallbackResponse)
def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str | None = Query(default=None, description="State parameter"),
    db: Session = Depends(get_db),
):
    """Handle Google OAuth callback.

    Exchanges the authorization code for tokens and authenticates/registers the user.

    Returns:
        JWT access token and whether this is a new user.
    """
    service = OAuthService(db)
    user, is_new_user = service.authenticate_with_google(code)

    # Create JWT token
    access_token = create_jwt_for_user(user)

    return OAuthCallbackResponse(
        access_token=access_token,
        is_new_user=is_new_user,
    )
