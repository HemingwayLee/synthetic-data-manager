from datetime import datetime
from typing import Any

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import models
from app.bizdoc import batches, generator
from app.bizdoc.schema import DOC_TYPES, RANDOM, SECTIONS, find_doc_type, validate_settings
from app.claude import MODELS
from app.config import settings
from app.db import get_db

router = APIRouter(prefix="/api/bizdoc", tags=["bizdoc"])


class GenerateRequest(BaseModel):
    settings: dict[str, Any] = {}
    model: str | None = None


BATCH_SIZES = [2, 5, 10, 20, 50]


class BatchGenerateRequest(GenerateRequest):
    count: int = Field(ge=1, le=max(BATCH_SIZES))


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_type: str
    batch_id: int | None
    status: str
    model: str
    settings: dict[str, Any]
    title: str | None
    labels: dict[str, Any] | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class BatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_type: str
    count: int
    status: str
    export: int | None = Field(description="Timestamp of the batch's archive: GET /api/exports/{export}.tar.gz")
    error: str | None
    created_at: datetime
    finished_at: datetime | None


def _get_doc_type(doc_type_id: str) -> dict[str, Any]:
    doc_type = find_doc_type(doc_type_id)
    if doc_type is None:
        raise HTTPException(status_code=404, detail="Unknown document type")
    return doc_type


def _get_document(db: Session, document_id: int) -> models.GeneratedDocument:
    doc = db.get(models.GeneratedDocument, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/doc-types")
def list_doc_types():
    return {"doc_types": DOC_TYPES, "sections": SECTIONS, "random": RANDOM}


@router.get("/{doc_type_id}/documents", response_model=list[DocumentRead])
def list_documents(doc_type_id: str, db: Session = Depends(get_db)):
    _get_doc_type(doc_type_id)
    stmt = (
        select(models.GeneratedDocument)
        .where(models.GeneratedDocument.doc_type == doc_type_id)
        .order_by(models.GeneratedDocument.id.desc())
    )
    return db.scalars(stmt).all()


def _queue_documents(
    db: Session, doc_type_id: str, payload: GenerateRequest, count: int, batch: bool = False
) -> list[models.GeneratedDocument]:
    doc_type = _get_doc_type(doc_type_id)
    model = payload.model or settings.claude_default_model
    if model not in {m["id"] for m in MODELS}:
        raise HTTPException(status_code=422, detail=f"Unknown model {model!r}")
    try:
        clean = validate_settings(doc_type, payload.settings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    batch_id = None
    if batch:
        record = models.BizDocBatch(doc_type=doc_type_id, count=count)
        db.add(record)
        db.flush()
        batch_id = record.id
    # Each document resolves "random" choices independently, so a batch varies.
    docs = [
        models.GeneratedDocument(
            doc_type=doc_type_id,
            batch_id=batch_id,
            status="queued",
            model=model,
            settings=generator.resolve_settings(doc_type, clean),
        )
        for _ in range(count)
    ]
    db.add_all(docs)
    db.commit()
    for doc in docs:
        db.refresh(doc)
        generator.start_generation(doc)
    return docs


@router.post("/{doc_type_id}/documents", response_model=DocumentRead, status_code=202)
async def generate_document(doc_type_id: str, payload: GenerateRequest, db: Session = Depends(get_db)):
    return _queue_documents(db, doc_type_id, payload, 1)[0]


@router.get("/batch-sizes")
def batch_sizes():
    return {"sizes": BATCH_SIZES}


@router.post("/{doc_type_id}/documents/batch", response_model=list[DocumentRead], status_code=202)
async def generate_batch(doc_type_id: str, payload: BatchGenerateRequest, db: Session = Depends(get_db)):
    """Queue `count` documents as one batch. When all have finished, the batch is archived (see GET /api/exports)."""
    return _queue_documents(db, doc_type_id, payload, payload.count, batch=True)


@router.get("/batches", response_model=list[BatchRead])
def list_batches(db: Session = Depends(get_db)):
    return db.scalars(select(models.BizDocBatch).order_by(models.BizDocBatch.id.desc())).all()


@router.get("/batches/{batch_id}", response_model=BatchRead)
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.get(models.BizDocBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


@router.post("/{doc_type_id}/documents/cancel-queued")
async def cancel_queued(doc_type_id: str, db: Session = Depends(get_db)):
    """Cancel documents still waiting for a slot; ones already being written finish normally."""
    _get_doc_type(doc_type_id)
    rows = db.execute(
        update(models.GeneratedDocument)
        .where(models.GeneratedDocument.doc_type == doc_type_id, models.GeneratedDocument.status == "queued")
        .values(status="cancelled")
        .returning(models.GeneratedDocument.batch_id)
    ).all()
    db.commit()
    # Batches whose last pending documents were just cancelled are complete now.
    for batch_id in {row.batch_id for row in rows if row.batch_id is not None}:
        await asyncio.to_thread(batches.finish_if_complete, batch_id)
    return {"cancelled": len(rows)}


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, db: Session = Depends(get_db)):
    return _get_document(db, document_id)


@router.get("/documents/{document_id}/pdf")
def get_document_pdf(document_id: int, download: bool = False, db: Session = Depends(get_db)):
    doc = _get_document(db, document_id)
    pdf = generator.document_dir(doc) / "document.pdf"
    if doc.status != "done" or not pdf.exists():
        raise HTTPException(status_code=404, detail="PDF not available")
    return FileResponse(
        pdf,
        media_type="application/pdf",
        filename=f"{doc.doc_type}-{doc.id}.pdf",
        content_disposition_type="attachment" if download else "inline",
    )


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    doc = _get_document(db, document_id)
    if doc.status in ("queued", "running"):
        raise HTTPException(status_code=409, detail="Wait for generation to finish before deleting")
    generator.delete_files(doc)
    db.delete(doc)
    db.commit()
