from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class AddToCartRequest(BaseModel):
    product_id: UUID
    quantity: int


class CreateOrderRequest(BaseModel):
    store_id: UUID
    company_id: UUID
    order_type: str = "click_collect"
    notes: Optional[str] = None
    delivery_address: Optional[dict] = None


class ScanGoOrderRequest(BaseModel):
    store_id: UUID
    company_id: UUID
    items: list[dict]  # [{product_id, quantity}]


class UpdateOrderStatusRequest(BaseModel):
    status: str
    reason: Optional[str] = None


class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price_xof: int
    total_price_xof: int
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: str
    order_number: str
    company_id: str
    store_id: str
    customer_id: str
    type: str
    status: str
    total_xof: int
    items_count: int
    notes: Optional[str] = None
    delivery_address: Optional[dict] = None
    created_at: str

    class Config:
        from_attributes = True
