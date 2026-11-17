"""Batch archives for other systems: each finished batch is packed into <exports_dir>/<unix seconds>.tar.gz.

An archive unpacks into one folder named after its timestamp, holding manifest.json plus the batch's files:

    1763350000/
        manifest.json
        ...

Next to each archive, <unix seconds>.json holds its index entry (size, checksums, manifest), so listing archives
never has to open them. The timestamp is when the archive was written; if two batches finish in the same second,
the later one takes the next free second, so names stay unique and sortable.

The same module is used by every app in this repo (each keeps its own copy, as apps share no code).
"""

import hashlib
import io
import json
import os
import re
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.config import settings

NAME_RE = re.compile(r"^[0-9]{1,12}$")
SUFFIX = ".tar.gz"


def exports_dir() -> Path:
    path = Path(settings.exports_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def archive_path(timestamp: int) -> Path:
    return exports_dir() / f"{timestamp}{SUFFIX}"


def _index_path(timestamp: int) -> Path:
    return exports_dir() / f"{timestamp}.json"


def _reserve() -> tuple[int, Path]:
    """Pick a free timestamp and create its temp file atomically, so concurrent batches never share a name."""
    timestamp = int(time.time())
    while True:
        tmp = exports_dir() / f".{timestamp}{SUFFIX}.tmp"
        if not archive_path(timestamp).exists():
            try:
                os.close(os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return timestamp, tmp
            except FileExistsError:
                pass
        timestamp += 1


def _checksums(path: Path) -> tuple[str, str]:
    md5, sha256 = hashlib.md5(), hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            md5.update(chunk)
            sha256.update(chunk)
    return md5.hexdigest(), sha256.hexdigest()


def write_archive(files: list[tuple[Path, str]], manifest: dict) -> dict:
    """Pack (source file, path inside the batch folder) pairs plus manifest.json; return the index entry.

    Blocking (it compresses the whole batch): call it from a thread.
    """
    timestamp, tmp = _reserve()
    created_at = datetime.now(timezone.utc).isoformat()
    manifest = {"timestamp": timestamp, "created_at": created_at, **manifest}
    try:
        with tarfile.open(tmp, "w:gz", compresslevel=6) as tar:
            data = json.dumps(manifest, ensure_ascii=False, indent=2).encode()
            info = tarfile.TarInfo(f"{timestamp}/manifest.json")
            info.size, info.mtime = len(data), int(time.time())
            tar.addfile(info, io.BytesIO(data))
            for source, name in files:
                tar.add(source, f"{timestamp}/{name}", recursive=False)
        md5, sha256 = _checksums(tmp)
        entry = {
            "timestamp": timestamp,
            "name": f"{timestamp}{SUFFIX}",
            "created_at": created_at,
            "bytes": tmp.stat().st_size,
            "files": len(files),
            "md5": md5,
            "sha256": sha256,
            "manifest": manifest,
        }
        _index_path(timestamp).write_text(json.dumps(entry, ensure_ascii=False, indent=2))
        tmp.replace(archive_path(timestamp))  # last, so an archive is only visible once complete
    except BaseException:
        tmp.unlink(missing_ok=True)
        _index_path(timestamp).unlink(missing_ok=True)
        raise
    return entry


def load(timestamp: int) -> dict | None:
    index = _index_path(timestamp)
    if not archive_path(timestamp).exists() or not index.exists():
        return None
    return json.loads(index.read_text())


def list_all(since: int | None = None) -> list[dict]:
    """Index entries, newest first, without their manifests; `since` keeps only archives with a later timestamp."""
    entries = []
    for index in exports_dir().glob("*.json"):
        if not NAME_RE.match(index.stem) or (since is not None and int(index.stem) <= since):
            continue
        entry = load(int(index.stem))
        if entry is not None:
            entry.pop("manifest", None)
            entries.append(entry)
    entries.sort(key=lambda e: e["timestamp"], reverse=True)
    return entries


def delete(timestamp: int) -> bool:
    found = archive_path(timestamp).exists()
    archive_path(timestamp).unlink(missing_ok=True)
    _index_path(timestamp).unlink(missing_ok=True)
    return found


# ---- API: GET /api/exports, GET /api/exports/{timestamp}, GET /api/exports/{timestamp}.tar.gz ----------

router = APIRouter(prefix="/api/exports", tags=["exports"])


def _get(timestamp: int) -> dict:
    entry = load(timestamp)
    if entry is None:
        raise HTTPException(404, "Archive not found")
    return entry


@router.get("")
def list_exports(since: int | None = Query(None, description="Only archives with a later timestamp (for polling).")):
    """Batch archives, newest first: name, size, md5/sha256 and file count (no manifests)."""
    return list_all(since)


# Declared before /{timestamp} so "<ts>.tar.gz" is never read as a timestamp.
@router.get("/{timestamp}.tar.gz", response_class=FileResponse)
def download_export(timestamp: int):
    """The archive itself. It unpacks into <timestamp>/ with manifest.json and the batch's files."""
    _get(timestamp)
    return FileResponse(archive_path(timestamp), media_type="application/gzip", filename=f"{timestamp}{SUFFIX}")


@router.get("/{timestamp}")
def get_export(timestamp: int):
    """One archive's index entry, including its manifest."""
    return _get(timestamp)


@router.delete("/{timestamp}", status_code=204)
def delete_export(timestamp: int):
    _get(timestamp)
    delete(timestamp)
