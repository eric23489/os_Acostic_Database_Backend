"""OAuth related Pydantic schemas."""

from pydantic import BaseModel


class GoogleAuthUrl(BaseModel):
    """Response for Google OAuth authorization URL."""

    authorization_url: str


class OAuthCallbackResponse(BaseModel):
    """Response after successful OAuth callback."""

    access_token: str
    token_type: str = "bearer"
    is_new_user: bool = False


class OAuthLinkRequest(BaseModel):
    """Request to link OAuth account (using authorization code)."""

    code: str


class OAuthLinkResponse(BaseModel):
    """Response after linking OAuth account."""

    message: str
    oauth_provider: str


class OAuthUnlinkResponse(BaseModel):
    """Response after unlinking OAuth account."""

    message: str


class SetPasswordRequest(BaseModel):
    """Request to set password for OAuth-only account."""

    password: str


class SetPasswordResponse(BaseModel):
    """Response after setting password."""

    message: str
