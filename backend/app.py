"""FastAPI backend for the Pricedrop monitor.

Endpoints:
    GET    /health                      — health check
    GET    /products                    — list all tracked products
    POST   /products                    — add (scrape + save) a product by URL
    GET    /products/{product_id}       — one product with latest price
    GET    /products/{product_id}/history — full price history
    DELETE /products/{product_id}       — stop tracking
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.database import (
    init_db,
    list_products,
    get_product,
    get_history,
    delete_product,
)
from backend.models import (
    ProductCreate,
    ProductOut,
    PriceHistoryEntry,
    HealthResponse,
)
from worker.scraper import scrape_and_save
from worker.sites.base import ScrapeFailed
from worker.utils.logger import get_logger

log = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run once on startup, once on shutdown."""
    init_db()
    log.info("api_started")
    yield
    log.info("api_stopped")


app = FastAPI(
    title="Pricedrop API",
    version="1.0.0",
    lifespan=lifespan,
)

# Chrome extensions call from chrome-extension://<id> — a different origin.
# For development, allow everything. Restrict in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok", "db": "connected"}


@app.get("/products", response_model=list[ProductOut])
def api_list_products():
    return list_products()


@app.post("/products", response_model=ProductOut)
def api_create_product(payload: ProductCreate):
    url = str(payload.url)
    log.info("api_add_product", extra={"extra": {"url": url}})
    try:
        result = scrape_and_save(url)
    except ScrapeFailed as e:
        log.error(
            "api_scrape_failed",
            extra={"extra": {"url": url, "error": str(e)}},
        )
        raise HTTPException(status_code=400, detail=f"Scrape failed: {e}")

    product = get_product(result["product_id"])
    if not product:
        raise HTTPException(status_code=500, detail="Product saved but not found in DB")
    return product


@app.get("/products/{product_id}", response_model=ProductOut)
def api_get_product(product_id: int):
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return product


@app.get("/products/{product_id}/history", response_model=list[PriceHistoryEntry])
def api_get_history(product_id: int):
    if not get_product(product_id):
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return get_history(product_id)


@app.delete("/products/{product_id}")
def api_delete_product(product_id: int):
    if not delete_product(product_id):
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return {"deleted": True, "id": product_id}