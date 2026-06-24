from typing import Optional
from uuid import UUID
from pydantic import BaseModel, field_validator


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class CategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str
    category_id: Optional[UUID] = None
    description: Optional[str] = None
    barcode: Optional[str] = None
    sku: Optional[str] = None
    unit: str = "piece"
    price_xof: int
    compare_price_xof: Optional[int] = None
    is_available: bool = True
    track_stock: bool = False
    stock_quantity: int = 0
    stock_alert_qty: int = 5

    @field_validator("price_xof")
    @classmethod
    def price_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Le prix ne peut pas être négatif")
        return v


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price_xof: Optional[int] = None
    compare_price_xof: Optional[int] = None
    is_available: Optional[bool] = None
    stock_quantity: Optional[int] = None
    stock_alert_qty: Optional[int] = None
    description: Optional[str] = None
    category_id: Optional[UUID] = None


class ProductResponse(BaseModel):
    id: str
    name: str
    price_xof: int
    compare_price_xof: Optional[int] = None
    is_available: bool
    track_stock: bool
    stock_quantity: int
    stock_reserved: int
    stock_alert_qty: int
    barcode: Optional[str] = None
    sku: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class StockAdjustRequest(BaseModel):
    quantity_change: int
    notes: Optional[str] = None
    reason: str = "manual"
