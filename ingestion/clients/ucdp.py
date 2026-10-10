"""UCDP GED client — organised-violence fatalities, for the security domain.

The security domain has no usable World Bank series (``homicides`` has 3 observations, see
decisions.md C-10), and ACLED's raw data cannot be redistributed. UCDP is CC-BY licenced, so
it can be both analysed **and published**.

Requires a free access token in the environment::

    UCDP_ACCESS_TOKEN=<token>

Register at https://ucdp.uu.se/. The token is sent as the header ``x-ucdp-access-token``
(confirmed 2026-10-10: an unauthenticated request returned 401 naming that header). The API
root serves Swagger UI at https://ucdpapi.pcr.uu.se/index.html.

Caveat: UCDP's conflict definition differs from ACLED's. Never splice the two series into one
without saying so on the model card.
"""

from __future__ import annotations

import json
import os

import requests

from ingestion.clients.provenance import MissingCredential, Retrieval, build

BASE_URL = "https://ucdpapi.pcr.uu.se/api/gedevents"
USER_AGENT = "causal-presidents/0.1 (low-volume public-data access)"
TIMEOUT_SECONDS = 60
ENV_VAR = "UCDP_ACCESS_TOKEN"
# UCDP country code for Nigeria.
NIGERIA = 475
MAX_ATTEMPTS = 3


def get_token() -> str:
    token = (os.environ.get(ENV_VAR) or "").strip()
    if not token:
        raise MissingCredential(
            f"{ENV_VAR} is not set. Register for a free token at https://ucdp.uu.se/ "
            "and export it; the API expects it in the x-ucdp-access-token header."
        )
    return token


def fetch_events(
    version: str = "24.1",
    country: int = NIGERIA,
    pagesize: int = 1000,
    session: requests.Session | None = None,
) -> tuple[Retrieval, list[dict]]:
    """Fetch every page of GED events for one country. Returns ``(retrieval, events)``."""
    session = session or requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "x-ucdp-access-token": get_token()})
    url = f"{BASE_URL}/{version}"

    payloads: list[bytes] = []
    events: list[dict] = []
    page = 1
    page_count = 1
    last_status = 0

    while page <= page_count:
        params = {"pagesize": pagesize, "page": page, "Country": country}
        response = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            response = session.get(url, params=params, timeout=TIMEOUT_SECONDS)
            if response.status_code != 401 or attempt == MAX_ATTEMPTS:
                break
        last_status = response.status_code
        if response.status_code == 401:
            raise MissingCredential(
                f"UCDP rejected the token (HTTP 401): {response.text[:160]}"
            )
        if response.status_code != 200:
            raise RuntimeError(f"UCDP: HTTP {response.status_code} — {response.text[:200]}")

        raw = response.content
        body = json.loads(raw)
        if page == 1:
            page_count = int(body.get("PageCount") or 1)
        payloads.append(raw)
        events.extend(body.get("Result") or [])
        page += 1

    retrieval = build(
        source="ucdp",
        dataset_id=f"gedevents-{version}",
        dataset_name=f"UCDP GED events, country {country}",
        url=url,
        params={"pagesize": pagesize, "Country": country, "page_count": page_count},
        http_status=last_status,
        payloads=payloads,
        row_count=len(events),
    )
    return retrieval, events
