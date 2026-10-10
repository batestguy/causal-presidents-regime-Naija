"""FRED client — Brent crude (``DCOILBRENTEU``), the oil covariate Family B depends on.

Requires a free API key in the environment::

    FRED_API_KEY=<key>

Register at https://fred.stlouisfed.org/docs/api/api_key.html. The key is read from the
environment and **never written to disk** — manifests store a redacted URL and parameter map
via :mod:`ingestion.clients.provenance`.

Verified 2026-10-10: without a key the API returns HTTP 400 ``api_key is not set``.

Note for Stage 4: ``DCOILBRENTEU`` is **daily**. The daily→monthly aggregation rule must be
frozen in the transformation layer before any oil-adjusted estimate is computed, because
changing it later changes every adjusted result.
"""

from __future__ import annotations

import json
import os

import requests

from ingestion.clients.provenance import MissingCredential, Retrieval, build

BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
USER_AGENT = "causal-presidents/0.1 (low-volume public-data access)"
TIMEOUT_SECONDS = 30
ENV_VAR = "FRED_API_KEY"


def get_api_key() -> str:
    key = (os.environ.get(ENV_VAR) or "").strip()
    if not key:
        raise MissingCredential(
            f"{ENV_VAR} is not set. Create a free key at "
            "https://fred.stlouisfed.org/docs/api/api_key.html and export it."
        )
    return key


def fetch_series(
    series_id: str,
    series_name: str = "",
    observation_start: str = "1960-01-01",
    session: requests.Session | None = None,
) -> tuple[Retrieval, list[dict]]:
    """Fetch one FRED series. Returns ``(retrieval, observations)``.

    ``observations`` is for convenience; the raw payload is the authoritative artifact.
    """
    session = session or requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    params = {
        "series_id": series_id,
        "api_key": get_api_key(),
        "file_type": "json",
        "observation_start": observation_start,
    }

    response = session.get(BASE_URL, params=params, timeout=TIMEOUT_SECONDS)
    if response.status_code == 400 and "api_key" in response.text:
        raise MissingCredential(f"{series_id}: FRED rejected the API key — {response.text[:160]}")
    if response.status_code != 200:
        raise RuntimeError(f"{series_id}: HTTP {response.status_code} — {response.text[:200]}")

    body = json.loads(response.content)
    observations = body.get("observations", [])
    retrieval = build(
        source="fred",
        dataset_id=series_id,
        dataset_name=series_name or series_id,
        url=BASE_URL,
        params=params,
        http_status=response.status_code,
        payloads=[response.content],
        row_count=len(observations),
    )
    return retrieval, observations
