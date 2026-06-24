from typing import Optional
from pydantic import BaseModel


class ReceiptResponse(BaseModel):
    id: str
    receipt_number: str
    company_id: str
    order_id: str
    customer_id: str
    payment_id: str
    amount_xof: int
    verification_code: str
    pdf_url: Optional[str] = None
    html_content: Optional[str] = None
    issued_at: str

    class Config:
        from_attributes = True


class ReceiptListItem(BaseModel):
    id: str
    receipt_number: str
    amount_xof: int
    issued_at: str
    has_pdf: bool
    verification_code: str

    class Config:
        from_attributes = True


class VerifyReceiptResponse(BaseModel):
    valid: bool
    status: str  # "valid" | "not_found" | "already_used"
    receipt_number: Optional[str] = None
    order_number: Optional[str] = None
    amount_xof: Optional[int] = None
    items_count: Optional[int] = None
    message: Optional[str] = None
