"""NBS monthly CPI — the client.

**One workbook carries the whole history.** A monthly NBS "CPI and Inflation Report" ships an XLSX whose
Table 1 is the composite index from **1995-01 to the report's own month**, so a single document is a complete
monthly series and its vintage is the report's month. That is why this client lands one workbook per vintage
rather than 90 of them: the publisher already did the collation, and re-collating it here would be a second
computation of the same table.

**What this source cannot give, and it matters.** The elibrary's CPI listing stops at **2024-10** (measured
2026-10-29 — 152 CPI documents, 149 distinct months, 2012-03 to 2024-10, no 2025 or 2026 title at all), so the
January-2025 rebasing that C-27 records is **not** in this source. The series therefore ends on the 2009 base
and contains no definition break of its own — the opposite problem to the one C-27 warned about, and better:
a monthly inflation outcome that stops before the rebasing cannot silently mix two bases.

Licence: NBS publications are public documents (see `docs/licences.md`), redistributable with attribution.
"""

from __future__ import annotations

import re

import requests

from ingestion.clients.provenance import Retrieval, build

ELIBRARY_URL = "https://www.nigerianstat.gov.ng/elibrary"
REPORT_URL = "https://nigerianstat.gov.ng/elibrary/read/{report_id}"
USER_AGENT = "causal-presidents/0.1 (low-volume public-data access)"
TIMEOUT_SECONDS = 180

# The month the series currently ends, and the report that carries it. A later report would be a new
# release of the same series and lands as a new vintage (X-07), never as an edit to this one.
LATEST_PERIOD = "2024-10"
KNOWN_REPORTS = {"2024-10": "1241583"}

MONTH_NUMBERS = {
    "january": 1, "february": 2, "febuary": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
_ROWS = re.compile(r"<tr>(.*?)</tr>", re.DOTALL)
_TITLE_CELL = re.compile(r"<td>([^<]*)</td>")
_REPORT_LINK = re.compile(r"/elibrary/read/(\d+)")
_RESOURCE = re.compile(r"https://nigerianstat\.gov\.ng/resource/[^\"']+", re.IGNORECASE)
_MONTH_YEAR = re.compile(r"([A-Za-z]{3,9})[\s,]+(\d{4})")

NOTE = (
    "NBS CPI and Inflation Report, landed untransformed. Table 1 of the workbook is the composite index from "
    "1995-01 to the report's own month, so the workbook is the payload and the series is read from one document "
    "rather than collated from many. The parser filters nothing out; it reads the table as published."
)

ATTRIBUTION = (
    "National Bureau of Statistics (Nigeria), CPI and Inflation Report, National Bureau of Statistics — "
    "public document, cited to NBS. https://nigerianstat.gov.ng/elibrary"
)


class NbsCpiError(RuntimeError):
    """Raised when the listing, the report page or the workbook is not what it claims to be."""


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def discover(period: str, session: requests.Session | None = None) -> dict:
    """The elibrary row for one month, read **row by row**.

    The listing comments some cells out, so a lazy regex over the whole page can pair a title with the *next*
    row's report link — the pairing has to be confined to a ``<tr>``. A row with no link is skipped rather than
    shifted, and a title with no month-and-year is skipped rather than guessed.
    """
    session = session or _session()
    try:
        page = session.get(ELIBRARY_URL, timeout=TIMEOUT_SECONDS).text
    except requests.RequestException as exc:  # pragma: no cover - network
        raise NbsCpiError(f"{ELIBRARY_URL}: {exc}") from exc

    for row in _ROWS.findall(page):
        title_cell = _TITLE_CELL.search(row)
        link = _REPORT_LINK.search(row)
        if not title_cell or not link:
            continue
        title = " ".join(title_cell.group(1).split())
        if "cpi" not in title.lower() and "consumer price" not in title.lower():
            continue
        periods = [
            f"{int(year):04d}-{MONTH_NUMBERS[name.lower()]:02d}"
            for name, year in _MONTH_YEAR.findall(title)
            if name.lower() in MONTH_NUMBERS
        ]
        if period not in periods:
            continue
        return {
            "period": period,
            "report_id": link.group(1),
            "title": title,
            "url": REPORT_URL.format(report_id=link.group(1)),
        }
    raise NbsCpiError(f"the elibrary lists no CPI report for {period}")


def resolve_workbook(report: dict, session: requests.Session | None = None) -> dict:
    """The spreadsheet on a report page. XLSX where the publisher ships one, XLS for the 2016-2020 months."""
    session = session or _session()
    try:
        page = session.get(report["url"], timeout=TIMEOUT_SECONDS).text
    except requests.RequestException as exc:  # pragma: no cover - network
        raise NbsCpiError(f"{report['url']}: {exc}") from exc
    urls = [url for url in _RESOURCE.findall(page) if url.lower().endswith((".xlsx", ".xls"))]
    if not urls:
        raise NbsCpiError(
            f"{report['url']}: no spreadsheet. The elibrary's pre-2017 CPI reports carry none (55 of the 149 "
            f"listed months), which is a fact about the source, not a fetch failure"
        )
    # A page can carry a second workbook (PMS/fuel tables); the CPI table is the one named for it.
    urls.sort(key=lambda url: 0 if "cpi" in url.lower() else 1)
    url = urls[0]
    suffix = ".xlsx" if url.lower().endswith(".xlsx") else ".xls"
    return {"url": url, "file_name": f"NBS-CPI-{report['period']}{suffix}",
            "suffix": suffix, "n_candidates": len(urls)}


def fetch_workbook(report: dict, workbook: dict, session: requests.Session | None = None) -> tuple[Retrieval, bytes]:
    """Download the workbook and verify it is the container it claims to be before anything is written."""
    session = session or _session()
    try:
        response = session.get(workbook["url"], timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:  # pragma: no cover - network
        raise NbsCpiError(f"{workbook['url']}: {exc}") from exc
    if response.status_code != 200:
        raise NbsCpiError(f"{workbook['url']}: HTTP {response.status_code}")
    payload = response.content
    magic = b"PK" if workbook["suffix"] == ".xlsx" else b"\xd0\xcf\x11\xe0"
    if not payload.startswith(magic):
        raise NbsCpiError(
            f"{workbook['url']}: not a {workbook['suffix']} workbook (starts {payload[:8]!r}) — these hosts "
            f"have been seen to answer with an HTML page under a 200"
        )
    retrieval = build(
        source="nbs_cpi",
        dataset_id=f"nbs-cpi-{report['period']}",
        dataset_name=f"NBS CPI and Inflation Report {report['period']}",
        url=workbook["url"],
        params={"period": report["period"], "report_id": report["report_id"], "title": report["title"]},
        http_status=response.status_code,
        payloads=[payload],
        row_count=0,  # the flow fills this from the coverage read
    )
    return retrieval, payload
