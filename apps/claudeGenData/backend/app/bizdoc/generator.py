"""Generate synthetic Japanese business documents with Claude Code and render them to PDF."""

import asyncio
import json
import logging
import random
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from sqlalchemy import update
from weasyprint import HTML
from weasyprint.urls import URLFetcher

from app import models
from app.bizdoc import batches
from app.bizdoc.schema import RANDOM, find_doc_type
from app.claude import ensure_credentials
from app.config import settings
from app.db import SessionLocal

logger = logging.getLogger(__name__)

# Limits concurrent generations so a burst of clicks doesn't exhaust plan usage limits at once.
_semaphore = asyncio.Semaphore(settings.bizdoc_concurrency)
_tasks: set[asyncio.Task] = set()

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Short Japanese title, e.g. 業務委託契約書（株式会社〇〇 × 〇〇合同会社）"},
        "html": {"type": "string", "description": "The complete, self-contained HTML document"},
        "labels": {
            "type": "object",
            "properties": {
                "document_type": {"type": "string"},
                "issue_date": {"type": "string", "description": "ISO date YYYY-MM-DD, or empty if not shown"},
                "parties": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "description": "e.g. 発行者, 宛先, 甲, 乙"},
                            "name": {"type": "string"},
                            "address": {"type": "string"},
                        },
                        "required": ["role", "name"],
                    },
                },
                "amounts": {
                    "type": "array",
                    "description": "Every total, subtotal and tax amount as printed",
                    "items": {
                        "type": "object",
                        "properties": {"label": {"type": "string"}, "value": {"type": "integer"}},
                        "required": ["label", "value"],
                    },
                },
                "key_fields": {
                    "type": "array",
                    "description": "Other extractable fields (due date, registration number, term, jurisdiction, ...)",
                    "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}, "value": {"type": "string"}},
                        "required": ["name", "value"],
                    },
                },
                "planted_issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                            "evidence": {"type": "string", "description": "Exact text from the document showing the issue, or empty for an omission"},
                        },
                        "required": ["type", "description", "evidence"],
                    },
                },
            },
            "required": ["document_type", "issue_date", "parties", "amounts", "key_fields", "planted_issues"],
        },
    },
    "required": ["title", "html", "labels"],
}

SYSTEM_PROMPT = """You generate realistic synthetic Japanese business documents for training document-AI models.

Return the document as one complete HTML file plus an answer key (labels) that exactly matches it.

Realism:
- Write natural, professional Japanese as used in real business documents of this type.
- Follow every setting you are given exactly. Settings marked as planted issues must appear in the
  document; otherwise the document must be internally consistent (amounts add up, tax is correct,
  dates are in a sensible order).

Everything must be fictional:
- Invent all company, person, bank and branch names. Never use real or well-known companies, people,
  banks or brands, and avoid names that closely resemble them.
- Addresses may use real prefectures and cities, but invent the street and building details.
- Phone and fax numbers: the first digit after the area code must be 0 (e.g. 03-0123-4567), so they
  can't be real numbers. Email addresses must use the example.com domain.
- When a registration number (登録番号) is shown, use exactly the one provided.

HTML rules (it is rendered to PDF by WeasyPrint, not a browser):
- One self-contained document with an inline <style>. No JavaScript, no external URLs, fonts or images.
- Set the page with @page (A4 portrait unless the format calls for something else, e.g. a narrow POS
  receipt of about 80mm width). Long documents may span several pages.
- Use the font-family given in the settings.
- Draw seals (印影) with inline SVG in red: a square seal for 角印, a circle for 丸印, containing the
  issuer's name.
- Use CSS layout WeasyPrint supports well (block, tables, flexbox). No vertical writing-mode.

Labels:
- Every value in the labels must appear in the document as printed (except issue_date, which is ISO).
- amounts are integers in yen.
- planted_issues lists each planted issue with the exact text that shows it; empty if none were requested.
"""

FONT_FAMILIES = {
    "明朝体": "'IPAexMincho', 'Noto Serif CJK JP', serif",
    "ゴシック体": "'IPAexGothic', 'Noto Sans CJK JP', sans-serif",
}

ISSUE_PERIOD_DAYS = {
    "直近3か月": (0, 90),
    "直近1年": (0, 365),
    "1〜3年前": (365, 3 * 365),
    "3〜7年前": (3 * 365, 7 * 365),
}


def fake_registration_number() -> str:
    """A qualified-invoice registration number (T + 13 digits) whose check digit is deliberately
    wrong, so it can never be a real business's number."""
    body = [random.randint(0, 9) for _ in range(12)]
    # Corporate number check digit: 9 - (sum of digits weighted 1,2,1,2... from the right) mod 9
    weighted = sum(d * (2 if i % 2 else 1) for i, d in enumerate(reversed(body), start=1))
    valid_check = 9 - weighted % 9
    check = random.choice([d for d in range(1, 10) if d != valid_check])
    return "T" + str(check) + "".join(map(str, body))


def resolve_settings(doc_type: dict[str, Any], clean: dict[str, Any]) -> dict[str, Any]:
    """Replace every "random" choice with a concrete option and add generated values."""
    resolved = {}
    randomized = set()
    for field in doc_type["fields"]:
        value = clean[field["id"]]
        if field["type"] == "select" and value == RANDOM:
            value = random.choice(field["options"])
            randomized.add(field["id"])
        resolved[field["id"]] = value

    # Keep random picks consistent with each other: withholding tax only applies to payments to individuals.
    if resolved.get("withholding", "なし") != "なし" and resolved.get("issuer_type") != "個人事業主":
        if "issuer_type" in randomized:
            resolved["issuer_type"] = "個人事業主"
        elif "withholding" in randomized:
            resolved["withholding"] = "なし"

    if "issue_period" in resolved:
        low, high = ISSUE_PERIOD_DAYS[resolved["issue_period"]]
        resolved["issue_date"] = (date.today() - timedelta(days=random.randint(low, high))).isoformat()
    resolved["registration_number"] = fake_registration_number()
    return resolved


def build_prompt(doc_type: dict[str, Any], resolved: dict[str, Any]) -> str:
    labels = {f["id"]: f["label"] for f in doc_type["fields"]}
    lines = []
    for key, value in resolved.items():
        if key in ("extra_instructions", "registration_number", "issue_date") or value in ("", []):
            continue
        if isinstance(value, list):
            value = "、".join(value)
        lines.append(f"- {labels.get(key, key)}: {value}")

    font = FONT_FAMILIES.get(resolved.get("font", ""), FONT_FAMILIES["明朝体"])
    planted = resolved.get("planted_issues") or []
    prompt = [
        f"Create one {doc_type['ja']} ({doc_type['label'][:-1].lower()}) with these settings:",
        *lines,
        f"- Issue date (発行日 / 締結日): {resolved['issue_date']} — format it per the date format setting;"
        " use the correct era (平成 before 2019-05-01, 令和 from then).",
        f"- Registration number to use if one is shown: {resolved['registration_number']}",
        f"- CSS font-family: {font}",
        f"- Planted issues: {'、'.join(planted) if planted else 'none — the document must be fully consistent'}",
    ]
    if resolved.get("extra_instructions"):
        prompt.append(f"\nAdditional instructions from the user:\n{resolved['extra_instructions']}")
    return "\n".join(prompt)


def render_pdf(html: str, pdf_path: Path) -> None:
    # Only inline data: URIs may load; no network or local file access from generated HTML.
    HTML(string=html, url_fetcher=URLFetcher(allowed_protocols={"data"})).write_pdf(pdf_path)


def document_dir(doc: models.GeneratedDocument) -> Path:
    return Path(settings.bizdoc_data_dir) / doc.doc_type / str(doc.id)


def _update(doc_id: int, **fields: Any) -> None:
    with SessionLocal() as session:
        doc = session.get(models.GeneratedDocument, doc_id)
        if doc is None:
            return
        for key, value in fields.items():
            setattr(doc, key, value)
        session.commit()


async def _generate(doc_id: int, doc_type_id: str, model: str, resolved: dict[str, Any], out_dir: Path) -> None:
    doc_type = find_doc_type(doc_type_id)
    async with _semaphore:
        # Claim the job atomically; it may have been cancelled or deleted while waiting for a slot.
        with SessionLocal() as session:
            claimed = session.execute(
                update(models.GeneratedDocument)
                .where(models.GeneratedDocument.id == doc_id, models.GeneratedDocument.status == "queued")
                .values(status="running", started_at=datetime.now(timezone.utc))
            ).rowcount
            session.commit()
        if not claimed:
            return
        try:
            ensure_credentials()
            out_dir.mkdir(parents=True, exist_ok=True)

            options = ClaudeAgentOptions(
                model=model,
                cwd=str(out_dir),
                system_prompt=SYSTEM_PROMPT,
                # Pure generation: pre-approve nothing, so any tool call is denied.
                allowed_tools=[],
                permission_mode="dontAsk",
                output_format={"type": "json_schema", "schema": OUTPUT_SCHEMA},
                max_turns=6,
            )
            output = None
            async for message in query(prompt=build_prompt(doc_type, resolved), options=options):
                if isinstance(message, ResultMessage):
                    if message.subtype == "success" and message.structured_output:
                        output = message.structured_output
                    else:
                        raise RuntimeError(message.result or f"Claude Code returned no document ({message.subtype})")
            if output is None:
                raise RuntimeError("Claude Code finished without returning a document")

            (out_dir / "document.html").write_text(output["html"], encoding="utf-8")
            (out_dir / "labels.json").write_text(
                json.dumps({"settings": resolved, "labels": output["labels"]}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            await asyncio.to_thread(render_pdf, output["html"], out_dir / "document.pdf")

            _update(
                doc_id,
                status="done",
                title=output["title"][:300],
                labels=output["labels"],
                finished_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            logger.exception("Document generation %s failed", doc_id)
            _update(doc_id, status="failed", error=str(exc)[:2000], finished_at=datetime.now(timezone.utc))


async def _generate_and_finish(batch_id: int | None, *args: Any) -> None:
    try:
        await _generate(*args)
    finally:
        # Whatever happened to this document (done, failed, cancelled while queued), its batch may be complete now.
        if batch_id is not None:
            await asyncio.to_thread(batches.finish_if_complete, batch_id)


def start_generation(doc: models.GeneratedDocument) -> None:
    task = asyncio.create_task(
        _generate_and_finish(doc.batch_id, doc.id, doc.doc_type, doc.model, doc.settings, document_dir(doc))
    )
    _tasks.add(task)  # keep a reference so the task isn't garbage-collected mid-run
    task.add_done_callback(_tasks.discard)


def delete_files(doc: models.GeneratedDocument) -> None:
    shutil.rmtree(document_dir(doc), ignore_errors=True)


def fail_interrupted_jobs() -> None:
    """Jobs don't survive a backend restart (including hot reload); mark leftovers as failed."""
    with SessionLocal() as session:
        for doc in session.query(models.GeneratedDocument).filter(
            models.GeneratedDocument.status.in_(["queued", "running"])
        ):
            doc.status = "failed"
            doc.error = "Interrupted because the backend restarted. Generate it again."
        session.commit()
