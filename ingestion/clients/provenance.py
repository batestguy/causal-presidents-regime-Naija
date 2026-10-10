"""Shared provenance primitives for ingestion clients.

Every client lands payloads byte-for-byte and records how to prove it::

    <raw_root>/<source>/<vintage>/<dataset_id>/page-0001.json
    <raw_root>/<source>/<vintage>/manifest.json

Three rules this module enforces:

1. **Payloads are never transformed**, only stored, so a recorded ``sha256`` always
   reproduces the bytes the source returned.
2. **Secrets never reach the manifest.** URLs and parameter maps are redacted, so a
   manifest is safe to commit even for key-authenticated sources.
3. **Paths are stored POSIX-style**, because Windows backslash paths break on the
   Linux CI runners the plan schedules against (found the hard way — see decisions.md C-16).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Substrings that mark a parameter as credential-bearing.
SECRET_MARKERS = (
    "api_key",
    "apikey",
    "token",
    "access_token",
    "subscription-key",
    "authorization",
    "password",
)

REDACTED = "***redacted***"


class MissingCredential(RuntimeError):
    """Raised when a source needs a credential that is absent from the environment."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_of(payloads) -> str:
    digest = hashlib.sha256()
    for payload in payloads:
        digest.update(payload)
    return digest.hexdigest()


def _is_secret(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in SECRET_MARKERS)


def redact(params: dict | None) -> dict:
    """Return a copy of ``params`` with credential-looking values masked."""
    return {
        key: (REDACTED if _is_secret(key) else value) for key, value in (params or {}).items()
    }


def redact_url(url: str) -> str:
    """Mask credential-looking query parameters in a URL."""
    base, separator, query = url.partition("?")
    if not separator:
        return url
    masked = []
    for chunk in query.split("&"):
        name, _, _ = chunk.partition("=")
        masked.append(f"{name}={REDACTED}" if _is_secret(name) else chunk)
    return f"{base}?{'&'.join(masked)}"


@dataclass
class Retrieval:
    """One dataset fetch, with everything needed to prove where it came from."""

    source: str
    dataset_id: str
    dataset_name: str
    url: str
    params: dict
    retrieved_at: str
    http_status: int
    page_count: int
    row_count: int
    payload_bytes: int
    sha256: str
    payloads: list = field(default_factory=list)

    def manifest_entry(self, **extra) -> dict:
        """The provenance record. Payload bytes travel as separate files; secrets are masked."""
        entry = {
            "source": self.source,
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "url": redact_url(self.url),
            "params": redact(self.params),
            "retrieved_at": self.retrieved_at,
            "http_status": self.http_status,
            "page_count": self.page_count,
            "row_count": self.row_count,
            "payload_bytes": self.payload_bytes,
            "sha256": self.sha256,
        }
        entry.update(extra)
        return entry


def build(
    source: str,
    dataset_id: str,
    dataset_name: str,
    url: str,
    params: dict,
    http_status: int,
    payloads: list[bytes],
    row_count: int,
) -> Retrieval:
    """Assemble a Retrieval from already-fetched payloads."""
    return Retrieval(
        source=source,
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        url=url,
        params=params,
        retrieved_at=utc_now(),
        http_status=http_status,
        page_count=len(payloads),
        row_count=row_count,
        payload_bytes=sum(len(payload) for payload in payloads),
        sha256=sha256_of(payloads),
        payloads=list(payloads),
    )


def write_pages(dataset_dir: Path, payloads, repo_root: Path) -> list[str]:
    """Write each payload as an untouched file, returning repo-relative POSIX paths."""
    dataset_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for index, payload in enumerate(payloads, start=1):
        path = dataset_dir / f"page-{index:04d}.json"
        path.write_bytes(payload)
        written.append(path.relative_to(repo_root).as_posix())
    return written


def write_manifest(
    vintage_dir: Path,
    vintage_date: str,
    source: str,
    entries: list[dict],
    failures: list[dict],
    extra: dict | None = None,
) -> dict:
    """Write ``manifest.json`` for a vintage. One schema for every source."""
    vintage_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "vintage_date": vintage_date,
        "generated_at": utc_now(),
        "source": source,
        "n_datasets_succeeded": len(entries),
        "n_failures": len(failures),
        "failures": failures,
        "retrievals": entries,
    }
    if extra:
        manifest.update(extra)
    (vintage_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
