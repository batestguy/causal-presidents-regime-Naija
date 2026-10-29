"""UCDP GED client — the state-attributed security outcome Family A was missing.

**No credential is needed for this route, and that is the reason it exists.** The UCDP *API* answers
401 without an `x-ucdp-access-token` header (verified 2026-10-17 against versions 25.1, 24.1 and 23.1),
which is what the catalogue recorded as C-14. The **bulk archive** is a plain HTTPS download on the
same host, tens of MB zipped (39 MB in release 26.1), and it answers a GET with no credential at all.
The dataset therefore stops being credential-blocked, and the project does not need an ACLED OAuth app
for the security outcome.

Licence: UCDP GED is **CC-BY 4.0** — redistributable with attribution, unlike ACLED's terms (C-13).
See `docs/licences.md`. The attribution string travels on the manifest entry.

The payload is a ZIP of one 250 MB CSV covering every country since 1989. It is landed **byte for
byte** and filtered to Nigeria by the parser, never by this client: the contract in
:mod:`ingestion.clients.provenance` is that payloads are stored untransformed, so a recorded
`sha256` always reproduces what UCDP served.
"""

from __future__ import annotations

import requests

from ingestion.clients.provenance import Retrieval, build

BASE_URL = "https://ucdp.uu.se/downloads/ged"
USER_AGENT = "causal-presidents/0.1 (low-volume public-data access)"
TIMEOUT_SECONDS = 300

# Version -> archive file name. `version` is UCDP's release label and is part of the dataset id, so a
# new release lands as a new dataset rather than overwriting the one already parsed.
ARCHIVES = {
    "26.1": "ged261-csv.zip",
    "25.1": "ged251-csv.zip",
    "24.1": "ged241-csv.zip",
    "23.1": "ged231-csv.zip",
}

# 26.1 adds the 2025 calendar year (Nigeria: 7,418 -> 8,255 events, last month 2024-12 -> 2025-12)
# and the column set is unchanged at 49, so the parser reads it without an adapter.
#
# **`ADOPTED` is the release this project's chain lands by default, and it is deliberately not the
# newest one.** 26.1 is in `ARCHIVES` and can be fetched by name, but it is not adopted: it revises 173
# historical state-month cells inside Design A's estimation window (+1.55% fatalities, +2.41%
# incidents), so adopting it re-fits every design on revised history and is its own accountable pass.
# See docs/decisions.md C-77. Keeping the *default* on the adopted release also matters operationally:
# `scripts/verify.sh` calls `pull_ucdp.py` with no arguments in the weekly `data` job, and a default of
# "newest" would have made that job adopt 26.1 against a registry that describes 25.1.
#
# Adoption is still recorded by which raw vintage was parsed into `data/staging` and echoed in
# `registry/quality/<vintage>/report.json -> source_vintages`; this constant only decides what a bare
# run fetches. Moving it to "26.1" is the first step of the adoption pass, not a side effect of it.
ADOPTED = "25.1"


def attribution(version: str) -> str:
    """The CC-BY attribution for *this* release.

    A module constant pinned to one release was wrong the moment a second version could be landed: a
    re-fetch of 24.1 would have carried "version 26.1" on its manifest, which is a licence statement
    about the wrong file.
    """
    return (
        f"UCDP Georeferenced Event Dataset (GED) Global version {version}, Uppsala Conflict Data "
        "Program, Uppsala University — CC-BY 4.0. https://ucdp.uu.se/downloads/"
    )

NOTE = (
    "UCDP GED bulk archive, landed untransformed. The parser filters to Nigeria and aggregates to "
    "state-month; the archive itself is the payload because a filtered extract would not reproduce "
    "the publisher's bytes."
)


class UcdpError(RuntimeError):
    """Raised when the bulk archive cannot be discovered or does not look like the archive."""


def archive_url(version: str = ADOPTED) -> str:
    if version not in ARCHIVES:
        raise UcdpError(f"unknown GED version {version!r}; known: {sorted(ARCHIVES)}")
    return f"{BASE_URL}/{ARCHIVES[version]}"


def fetch_archive(
    version: str = ADOPTED, session: requests.Session | None = None
) -> tuple[Retrieval, bytes]:
    """Download the bulk archive. Returns ``(retrieval, payload)``.

    The ZIP magic is checked before anything is written: these hosts have been observed to answer with
    an HTML error page under a 200, and a mislabelled payload would fail three stages later as a parse
    error rather than here as a retrieval error.
    """
    session = session or requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    url = archive_url(version)

    response = session.get(url, timeout=TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise UcdpError(f"{url}: HTTP {response.status_code} — {response.text[:200]}")
    payload = response.content
    if not payload.startswith(b"PK"):
        head = payload[:80].decode("utf-8", errors="replace").replace("\n", " ")
        raise UcdpError(f"{url}: not a ZIP archive (starts {head!r})")

    retrieval = build(
        source="ucdp",
        dataset_id=f"ged-{version}",
        dataset_name=f"UCDP GED {version} (bulk CSV archive)",
        url=url,
        params={"version": version, "files": ARCHIVES[version]},
        http_status=response.status_code,
        payloads=[payload],
        row_count=0,  # filled by the flow once the archive is counted
    )
    return retrieval, payload
