import json
import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field

# Same fixed dataset as the Hono app, loaded once at startup.
with open(os.environ.get("PRODUCTS_PATH", "/app/data/products.json")) as f:
    PRODUCTS = json.load(f)

WORKERS = int(os.environ.get("WORKERS", "1"))
POOL_SIZE = max(1, int(os.environ.get("DB_POOL_TOTAL", "20")) // WORKERS)


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0)
    tags: list[str] = Field(default_factory=list, max_length=20)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=POOL_SIZE, max_size=POOL_SIZE
    )
    yield
    await app.state.pool.close()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
async def health():
    return ORJSONResponse({"ok": True})


@app.get("/static")
async def static():
    # Serialized on every request, like c.json() in Hono.
    return ORJSONResponse(PRODUCTS)


@app.post("/items", status_code=201)
async def create_item(item: ItemIn):
    row_id = await app.state.pool.fetchval(
        "INSERT INTO items (name, price, tags) VALUES ($1, $2, $3) RETURNING id",
        item.name,
        item.price,
        item.tags,
    )
    return ORJSONResponse({"id": row_id}, status_code=201)
