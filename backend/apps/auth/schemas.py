from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
import re


class CustomerRegisterRequest(BaseModel):
    phone: str
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    preferred_language: str = "fr"
    marketing_opt_in: bool = False

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^\+?[1-9]\d{7,14}$", cleaned):
            raise ValueError("Numéro de téléphone invalide")
        return cleaned

    @field_validator("preferred_language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        allowed = {"fr", "en", "wo", "bm", "ha", "yo", "ig"}
        if v not in allowed:
            return "fr"
        return v


class CustomerLoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        return v


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 6:
            raise ValueError("Le code OTP doit contenir 6 chiffres")
        return v


class StaffLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # secondes
    user: "UserInfo"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserInfo(BaseModel):
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: str
    last_name: str
    full_name: str
    role: Optional[str] = None
    company_id: Optional[str] = None


TokenResponse.model_rebuild()


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        return v


class OTPSentResponse(BaseModel):
    message: str
    destination: str
    # En dev : retourner le code pour les tests
    debug_code: Optional[str] = None


# ── Identity ─────────────────────────────────────────────────────────────────

class RequestEmailVerificationResponse(BaseModel):
    message: str
    debug_token: Optional[str] = None  # Uniquement en dev/test


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    debug_token: Optional[str] = None  # Uniquement en dev/test


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        return v


class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_language: Optional[str] = None
    marketing_opt_in: Optional[bool] = None
