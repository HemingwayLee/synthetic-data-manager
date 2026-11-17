from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, engine, get_db
from app.models import Item


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience: create tables on startup. Swap for Alembic migrations later.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    root_path=settings.root_path,
    # Everything lives under /api so nginx can route /<app>/api/* here and the rest to the frontend.
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    lifespan=lifespan,
)


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ItemOut(ItemIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    database = db.execute(text("SELECT current_database()")).scalar_one()
    return {"status": "ok", "app": settings.app_name, "database": database}


@app.get("/api/items", response_model=list[ItemOut])
def list_items(db: Session = Depends(get_db)):
    return db.scalars(select(Item).order_by(Item.id.desc())).all()


@app.post("/api/items", response_model=ItemOut, status_code=201)
def create_item(body: ItemIn, db: Session = Depends(get_db)):
    item = Item(name=body.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
