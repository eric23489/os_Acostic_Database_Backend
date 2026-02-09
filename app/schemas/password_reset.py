"""Password reset related Pydantic schemas."""


from pydantic import BaseModel, EmailStr


class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset."""

    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Response after initiating password reset."""

    message: str
    has_google_oauth: bool = False


class ResetPasswordRequest(BaseModel):
    """Request to reset password using token."""

    token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    """Response after resetting password."""

    message: str
