"""Fake document-generation API used while recording.

Generation takes real time and uses Claude plan limits, so the recording intercepts the document
endpoints and serves a sample invoice instead. Scenes advance the fake jobs explicitly
(queued -> running -> done) so the video is the same on every run. Everything else (document types,
models, the UI itself) comes from the real running app.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ASSETS = Path(__file__).parent / "assets"

# Fictional sample generated earlier with this app.
SAMPLE_HTML = (ASSETS / "sample-invoice.html").read_text(encoding="utf-8")
SAMPLE = json.loads((ASSETS / "sample-labels.json").read_text(encoding="utf-8"))
SAMPLE_TITLE = "請求書（有限会社青嵐プランニング → 株式会社ハルカゼ食品）"
MODEL = "claude-opus-5-5"


def _now(offset_seconds: float = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


class MockDocuments:
    def __init__(self, concurrency: int = 2):
        self.docs: list[dict] = []
        self.concurrency = concurrency
        self._next_id = 101

    # --- state changes driven by the scenes -----------------------------------------------

    def _new(self, doc_type: str) -> dict:
        doc = {
            "id": self._next_id,
            "doc_type": doc_type,
            "status": "queued",
            "model": MODEL,
            "settings": SAMPLE["settings"],
            "title": None,
            "labels": None,
            "error": None,
            "created_at": _now(),
            "started_at": None,
            "finished_at": None,
        }
        self._next_id += 1
        self.docs.insert(0, doc)
        return doc

    def _start_queued(self) -> None:
        running = sum(d["status"] == "running" for d in self.docs)
        for doc in reversed(self.docs):  # oldest first
            if running >= self.concurrency:
                break
            if doc["status"] == "queued":
                doc.update(status="running", started_at=_now(-3))
                running += 1

    def finish_running(self, count: int = 1) -> None:
        for doc in [d for d in reversed(self.docs) if d["status"] == "running"][:count]:
            doc.update(status="done", title=SAMPLE_TITLE, labels=SAMPLE["labels"], finished_at=_now())
        self._start_queued()

    # --- HTTP handling --------------------------------------------------------------------

    def install(self, page) -> None:
        page.route(re.compile(r".*/api/bizdoc/.*"), self._handle)

    def _json(self, route, body, status: int = 200) -> None:
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body, ensure_ascii=False))

    def _handle(self, route) -> None:
        request = route.request
        path = request.url.split("/api/bizdoc", 1)[1].split("?")[0]
        method = request.method

        if m := re.fullmatch(r"/([\w-]+)/documents", path):
            if method == "GET":
                return self._json(route, [d for d in self.docs if d["doc_type"] == m[1]])
            doc = self._new(m[1])
            self._start_queued()
            return self._json(route, doc, 202)

        if (m := re.fullmatch(r"/([\w-]+)/documents/batch", path)) and method == "POST":
            count = json.loads(request.post_data or "{}").get("count", 1)
            docs = [self._new(m[1]) for _ in range(count)]
            self._start_queued()
            return self._json(route, docs, 202)

        if (m := re.fullmatch(r"/([\w-]+)/documents/cancel-queued", path)) and method == "POST":
            cancelled = 0
            for doc in self.docs:
                if doc["doc_type"] == m[1] and doc["status"] == "queued":
                    doc["status"] = "cancelled"
                    cancelled += 1
            return self._json(route, {"cancelled": cancelled})

        if re.fullmatch(r"/documents/\d+/pdf", path):
            # Headless Chromium has no built-in PDF viewer, so show the same document as HTML.
            return route.fulfill(status=200, content_type="text/html; charset=utf-8", body=SAMPLE_HTML)

        # Document types, batch sizes, etc. come from the real backend.
        return route.continue_()
