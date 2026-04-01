from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str  # plain str to accept internal domains like .local
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
