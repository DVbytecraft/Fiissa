"""Schemas Pydantic pour le wallet client Fiissa."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


METHOD_TYPE_VALUES = ("mobile_money", "external_loyalty_card", "bank_card", "bank_account")
MOBILE_OPERATOR_VALUES = ("wave", "orange_money", "free_money", "mtn_momo")


class WalletMethodCreateRequest(BaseModel):
    company_id: Optional[UUID] = None
    method_type: str = Field(..., pattern=r"^(mobile_money|external_loyalty_card|bank_card|bank_account)$")
    operator: Optional[str] = Field(None, pattern=r"^(wave|orange_money|free_money|mtn_momo)$")
    phone_number: Optional[str] = Field(None, max_length=20)
    display_name: str = Field(..., min_length=1, max_length=120)
    is_default: bool = False
    metadata: Optional[dict] = None

    @model_validator(mode="after")
    def validate_payload(self):
        if self.method_type == "mobile_money" and not self.phone_number:
            raise ValueError("phone_number est requis pour mobile_money")
        if self.method_type == "mobile_money" and not self.operator:
            raise ValueError("operator est requis pour mobile_money")
        return self


class WalletMethodUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=120)
    operator: Optional[str] = Field(None, pattern=r"^(wave|orange_money|free_money|mtn_momo)$")
    phone_number: Optional[str] = Field(None, max_length=20)
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None


class WalletMethodResponse(BaseModel):
    id: UUID
    customer_id: UUID
    company_id: Optional[UUID]
    method_type: str
    operator: Optional[str]
    phone_number: Optional[str]
    display_name: str
    is_default: bool
    is_active: bool
    metadata_: Optional[dict] = Field(None, serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }
