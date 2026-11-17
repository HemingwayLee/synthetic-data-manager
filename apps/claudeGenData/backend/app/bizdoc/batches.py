"""Batches: documents queued together by Batch Generation, archived once the last one finishes.

When no document of a batch is queued or running any more, the finished ones (document.pdf, document.html and
labels.json each) are packed into exports/<unix seconds>.tar.gz with a manifest (see app/exports.py):

    <timestamp>/
        manifest.json
        <document id>/document.pdf
        <document id>/document.html
        <document id>/labels.json
        ...

Failed and cancelled documents are left out and listed in the manifest. A batch where nothing succeeded gets no
archive (status "empty").
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select, text, update

from app import exports, models
from app.db import SessionLocal, engine

logger = logging.getLogger(__name__)

ACTIVE = ("queued", "running")
FILES = ("document.pdf", "document.html", "labels.json")


def migrate() -> None:
    """generated_documents predates batches; add its batch_id column (create_all doesn't alter existing tables)."""
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE generated_documents ADD COLUMN IF NOT EXISTS batch_id INTEGER "
            "REFERENCES bizdoc_batches(id) ON DELETE SET NULL"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_generated_documents_batch_id ON generated_documents (batch_id)"
        ))


def finish_if_complete(batch_id: int) -> None:
    """Archive the batch if none of its documents is queued or running. Safe to call repeatedly and concurrently.

    Blocking (it compresses the batch): call it from a thread.
    """
    from app.bizdoc import generator  # imported here: generator imports this module

    with SessionLocal() as session:
        active = session.scalar(
            select(func.count(models.GeneratedDocument.id)).where(
                models.GeneratedDocument.batch_id == batch_id, models.GeneratedDocument.status.in_(ACTIVE)
            )
        )
        if active:
            return
        # Claim the batch, so only one caller archives it.
        claimed = session.execute(
            update(models.BizDocBatch)
            .where(models.BizDocBatch.id == batch_id, models.BizDocBatch.status == "generating")
            .values(status="archiving")
        ).rowcount
        session.commit()
        if not claimed:
            return
        batch = session.get(models.BizDocBatch, batch_id)
        docs = session.scalars(
            select(models.GeneratedDocument)
            .where(models.GeneratedDocument.batch_id == batch_id)
            .order_by(models.GeneratedDocument.id)
        ).all()

        try:
            files, documents, skipped = [], [], []
            for doc in docs:
                folder = generator.document_dir(doc)
                if doc.status != "done" or not all((folder / name).is_file() for name in FILES):
                    skipped.append({"id": doc.id, "status": doc.status, "error": doc.error})
                    continue
                files += [(folder / name, f"{doc.id}/{name}") for name in FILES]
                documents.append({
                    "id": doc.id,
                    "folder": str(doc.id),
                    "title": doc.title,
                    "model": doc.model,
                    "settings": doc.settings,
                    "labels": doc.labels,
                })
            if not documents:
                batch.status = "empty"
            else:
                entry = exports.write_archive(files, {
                    "app": "claudeGenData",
                    "kind": "bizdoc",
                    "description": "Synthetic Japanese business documents. Each folder holds document.pdf, the "
                    "document.html it was rendered from, and labels.json ({settings, labels}: the answer key).",
                    "batch_id": batch.id,
                    "doc_type": batch.doc_type,
                    "count": len(documents),
                    "documents": documents,
                    "skipped": skipped,
                })
                batch.status, batch.export = "done", entry["timestamp"]
        except Exception as exc:
            logger.exception("Archiving batch %s failed", batch_id)
            batch.status, batch.error = "failed", str(exc)[:2000]
        batch.finished_at = datetime.now(timezone.utc)
        session.commit()


def finish_interrupted() -> None:
    """At startup (after interrupted documents are marked failed): archive batches a restart left unfinished."""
    with SessionLocal() as session:
        session.execute(
            update(models.BizDocBatch).where(models.BizDocBatch.status == "archiving").values(status="generating")
        )
        session.commit()
        pending = session.scalars(
            select(models.BizDocBatch.id).where(models.BizDocBatch.status == "generating")
        ).all()
    for batch_id in pending:
        finish_if_complete(batch_id)
