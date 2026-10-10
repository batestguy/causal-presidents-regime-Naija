"""World Bank Indicators API client.

Stage 2 contract: this module acquires data and records provenance. It does not
transform. Payloads are kept as the exact bytes received, so the ``sha256`` recorded
in the manifest always reproduces what the API returned.

Endpoint: ``https://api.worldbank.org/v2/country/{country}/indicator/{indicator}``
Verified 2026-10-10: keyless, paginated JSON of shape ``[metadata, rows]``.
"""

from __future__ import annotations

import json
import time

import requests

from ingestion.clients.provenance import Retrieval, build

BASE_URL = "https://api.worldbank.org/v2"
# Identify the client honestly and keep volume low; public data, no credentials needed.
USER_AGENT = "causal-presidents/0.1 (low-volume public-data access)"
TIMEOUT_SECONDS = 30
PER_PAGE = 1000
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 3


class WorldBankError(RuntimeError):
    """Raised when the API does not return the documented ``[metadata, rows]`` shape."""


# ``Retrieval`` and its manifest schema now live in ingestion.clients.provenance, shared by
# every source so there is one provenance implementation rather than one per client.


def _get(session: requests.Session, url: str, params: dict) -> requests.Response:
    """GET with bounded retries. Retries transport errors and 5xx; returns 4xx as-is."""
    last_error: object = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = session.get(url, params=params, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.status_code < 500:
                return response
            last_error = WorldBankError(f"HTTP {response.status_code}")
        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF_SECONDS * attempt)
    raise WorldBankError(f"failed after {MAX_ATTEMPTS} attempts: {url} ({last_error})")


def fetch_indicator(
    indicator_id: str,
    indicator_name: str = "",
    country: str = "NG",
    session: requests.Session | None = None,
    per_page: int = PER_PAGE,
) -> tuple[Retrieval, list[dict]]:
    """Fetch every page of one indicator. Returns ``(retrieval, rows)``.

    ``rows`` is for convenience only; the authoritative artifact is the raw payload.
    """
    session = session or requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    url = f"{BASE_URL}/country/{country}/indicator/{indicator_id}"

    payloads: list[bytes] = []
    rows: list[dict] = []
    page = 1
    total_pages = 1
    total_rows = 0
    last_status = 0

    while page <= total_pages:
        params = {"format": "json", "per_page": per_page, "page": page}
        response = _get(session, url, params)
        last_status = response.status_code
        raw = response.content  # bytes exactly as received
        body = json.loads(raw)

        # Gotcha (VERIFIED 2026-10-10): the API signals an invalid indicator with HTTP 200
        # and an error envelope, *not* a 4xx. Left unchecked this looks like "no data" and
        # silently manufactures a coverage gap, so it is caught explicitly here.
        envelope = body[0] if isinstance(body, list) and body else body
        if isinstance(envelope, dict) and "message" in envelope:
            details = envelope.get("message")
            raise WorldBankError(f"{indicator_id}: API rejected the request — {details}")

        if not isinstance(body, list) or len(body) != 2:
            raise WorldBankError(f"{indicator_id}: unexpected payload shape on page {page}")
        meta, data = body[0], body[1]
        if page == 1:
            total_pages = int(meta.get("pages") or 1)
            total_rows = int(meta.get("total") or 0)
        payloads.append(raw)
        rows.extend(data or [])
        page += 1

    # Row-count assertion: catches silent truncation from pagination.
    if total_rows and len(rows) != total_rows:
        raise WorldBankError(
            f"{indicator_id}: expected {total_rows} rows from metadata but received {len(rows)}"
        )

    retrieval = build(
        source="worldbank",
        dataset_id=indicator_id,
        dataset_name=indicator_name,
        url=url,
        params={"format": "json", "per_page": per_page, "country": country},
        http_status=last_status,
        payloads=payloads,
        row_count=len(rows),
    )
    return retrieval, rows
