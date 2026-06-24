from typing import Optional
from uuid import UUID
from pydantic import BaseModel, model_validator


class CreatePaymentRequest(BaseModel):
    order_id: UUID
    company_id: Optional[UUID] = None
    method: str = "mobile_money"
    operator: str


class SubmitProofRequest(BaseModel):
    transaction_ref: str
    sender_phone: str

    @model_validator(mode="after")
    def validate_ref(self):
        if not self.transaction_ref.strip():
            raise ValueError("La référence de transaction est obligatoire")
        return self


class ConfirmPaymentRequest(BaseModel):
    confirmed: bool
    reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_reason(self):
        if not self.confirmed and not (self.reason and self.reason.strip()):
            raise ValueError("La raison du rejet est obligatoire")
        return self


class PaymentResponse(BaseModel):
    id: str
    payment_number: str
    order_id: str
    company_id: str
    amount_xof: int
    method: str
    operator: str
    status: str
    transaction_ref: Optional[str] = None
    sender_phone: Optional[str] = None
    submitted_at: Optional[str] = None
    confirmed_at: Optional[str] = None

    class Config:
        from_attributes = True
