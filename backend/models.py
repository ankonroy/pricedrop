"""Pydantic models for the FastAPI backend.

These define the exact JSON shape clients (the Chrome extension,
the dashboard) send and receive.
"""

from typing import Optional
from pydantic import BaseModel, HttpUrl, Field


class ProductCreate(BaseModel):
    """Body for POST /products."""
    url: HttpUrl = Field(..., description="Full URL of the product page")


class ProductOut(BaseModel):
    """One product as returned by GET /products."""
    id: int
    url: str
    name: str
    created_at: str
    price: Optional[float] = None
    currency: Optional[str] = None
    in_stock: Optional[bool] = None
    scraped_at: Optional[str] = None


class PriceHistoryEntry(BaseModel):
    """One row of price_history as returned by GET /products/{id}/history."""
    id: int
    price: float
    currency: str
    in_stock: bool
    scraped_at: str


class HealthResponse(BaseModel):
    """Response for GET /health."""
    status: str
    db: str