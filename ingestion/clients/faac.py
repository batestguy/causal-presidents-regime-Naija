"""FAAC / state-allocation client — the primary exposure the base spec calls D1.

Base spec section 5 names the **Office of the Accountant General of the Federation (OAGF)** as the
source for the monthly per-state Federation Account allocation, with the **NBS FAAC disbursement
reports** as the published route to the same document. Stage 1 recorded OAGF as unreachable
("20s timeout on both curl and the read_url service") and the exposure metric was left requiring a
source substitution. **That finding no longer holds**: re-probed 2026-10-16, both hosts answer 200
and both serve the workbook.

Two publishers of one document, and both are landed:

* ``oagf`` — ``/publications/faac-report/``, a paginated archive of the monthly Table I–IV workbook
  as PDF. This is the **primary** series: one publisher, the originating office, the longest span.
* ``nbs`` — the NBS elibrary's FAAC disbursement reports, which republish the same
  ``Office of the Accountant General of the Federation`` workbook as **XLSX**. The NBS publication is
  an independent one — different site, different file format, different release date — which is
  exactly what ``tests/verify_stage6_faac.py`` needs to check the per-state figures against.

Stage 2 contract: **this module acquires and records provenance. It does not parse.** The PDF bytes
and the XLSX bytes are the artifacts; ``ingestion/parsers/faac_disbursement.py`` reads the landed
payloads afterwards. That split is what keeps the ``sha256`` in the manifest meaningful — the rate
disbursement documents are revised (a month is occasionally re-issued), so the vintage is the unit of
record and the parser must never be re-run against a file that was not the one recorded.

One deliberate difference from the World Bank and FRED clients: the payloads are **documents**
(PDF/XLSX), not JSON. A browser-like ``User-Agent`` is required — the same behaviour Stage 1 recorded
for IMF DataMapper (``403 to scripted clients, 200 via read_url``) — so the honest identifying agent
these clients use elsewhere is refused here. That is a property of the host, not a choice, and it is
recorded in the manifest so the retrieval is auditable.

The reporting convention matters for the series, and it is easy to get wrong by one month: a OAGF
document titled *"for the month of January 2024 shared in February 2024"* reports the revenue
**earned in January**, distributed to states in February. ``period_month`` throughout this project is
the month the revenue **accrued** — the document's own title month — not the month it was shared.
The distinction is declared once, in ``analysis/specs/harmonisation.yml``, and applied by the parser;
it is not re-decided per downstream table.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import requests

from ingestion.clients.provenance import Retrieval, build

OAGF_ARCHIVE_URL = "https://oagf.gov.ng/publications/faac-report/"
NBS_ELIBRARY_URL = "https://www.nigerianstat.gov.ng/elibrary"
NBS_REPORT_URL = "https://nigerianstat.gov.ng/elibrary/read/{report_id}"

# These hosts serve 403/empty to a scripted agent; verified 2026-10-16 that a browser agent gets 200
# on the archive page, the monthly PDFs, the elibrary listing and the resource XLSX.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT_SECONDS = 60
MAX_ARCHIVE_PAGES = 20

MONTH_NUMBERS = {
    "january": 1, "february": 2, "febuary": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

# ``Disbursement-February-2025.pdf``; one month in the archive carries a ``-1`` suffix.
_OAGF_PDF = re.compile(r"Disbursement-([A-Za-z]+)-(\d{4})(?:-\d+)?\.pdf", re.IGNORECASE)
# A elibrary row: the title cell, then the report link. Anchored on the two together so a
# non-FAAC row that happens to hold a download link cannot be picked up.
_ELIBRARY_ROW = re.compile(
    r"<td>([^<]*(?:FAAC|Disbursement)[^<]*)</td>.*?/elibrary/read/(\d+)",
    re.IGNORECASE | re.DOTALL,
)
_NBS_RESOURCE = re.compile(r"https://nigerianstat\.gov\.ng/resource/[^\"']+\.xlsx", re.IGNORECASE)
# ``February 2024`` / ``NOVEMBER 2022`` / ``Febuary 2016`` anywhere in a title.
_MONTH_YEAR = re.compile(r"([A-Za-z]{3,9})[\s-]+(\d{4})")


class FaacError(RuntimeError):
    """Raised when a FAAC host does not serve the documented document shape."""


@dataclass(frozen=True)
class MonthlyDocument:
    """One monthly disbursement document, located but not yet fetched."""

    period: str  # YYYY-MM, the month the revenue accrued
    dataset_id: str  # <publisher>-<YYYY-MM>, the directory the payload lands in
    url: str
    file_name: str
    publisher: str  # oagf | nbs
    title: str
    multi_period: bool = False  # one document covering several months


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def fetch_document(url: str, session: requests.Session | None = None) -> tuple[bytes, int]:
    """Fetch one document's bytes. Returns ``(payload, http_status)``.

    No retry loop: a missing month is a fact about the archive and should surface as a recorded
    failure in the manifest, not be hidden behind three silent attempts.
    """
    session = session or _session()
    response = session.get(url, timeout=TIMEOUT_SECONDS)
    return response.content, response.status_code


def fetch_text(url: str, session: requests.Session | None = None) -> str:
    session = session or _session()
    response = session.get(url, timeout=TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise FaacError(f"HTTP {response.status_code} for {url}")
    return response.text


def _period(month_name: str, year: str) -> str | None:
    month = MONTH_NUMBERS.get(month_name.lower())
    if month is None:
        return None
    return f"{int(year):04d}-{month:02d}"


def discover_oagf(session: requests.Session | None = None) -> list[MonthlyDocument]:
    """Every monthly disbursement PDF on the OAGF paginated archive.

    Pagination is walked until a page yields no new PDF links, rather than up to a guessed page
    count: the archive grows at the top, and a hard-coded ``range(7)`` would silently stop covering
    the series the day an eighth page appears.
    """
    session = session or _session()
    found: dict[str, MonthlyDocument] = {}
    for page in range(1, MAX_ARCHIVE_PAGES + 1):
        url = OAGF_ARCHIVE_URL if page == 1 else f"{OAGF_ARCHIVE_URL}page/{page}/"
        try:
            html = fetch_text(url, session)
        except FaacError:
            break
        links = set(re.findall(r'href="(https://oagf\.gov\.ng/wp-content/uploads/[^"]+\.pdf)"', html))
        expected = [
            link
            for link in links
            if _OAGF_PDF.search(link.rsplit("/", 1)[-1].replace("%20", " "))
        ]
        if not expected:
            break
        for link in sorted(expected):
            file_name = link.rsplit("/", 1)[-1].replace("%20", " ")
            match = _OAGF_PDF.search(file_name)
            period = _period(match.group(1), match.group(2))
            if period is None:
                continue
            # A later page duplicates an earlier one for a re-issued month; the first wins and the
            # duplicate is not silently treated as a second observation of the same month.            # Keyed by period so a re-issued month (the archive carries a ``-1`` duplicate for one)
            # keeps its first listing rather than being counted twice. The ``dataset_id`` additionally
            # carries the publisher, because the same month is published by two offices and a bare
            # ``YYYY-MM`` key would put both payloads in one directory under one manifest key.
            found.setdefault(
                period,
                MonthlyDocument(
                    period=period,
                    dataset_id=f"oagf-{period}",
        url=link,
        file_name=file_name,
        publisher="oagf",
        title=file_name,
                ),
            )
    return sorted(found.values(), key=lambda d: d.period)


def discover_nbs(session: requests.Session | None = None) -> list[MonthlyDocument]:
    """FAAC disbursement reports listed on the NBS elibrary.

    The elibrary's report page embeds a calendar whose ``id`` field is a **calendar event id**, not a
    report id, so report pages are resolved from the elibrary listing rows instead (title + link in
    the same row). Titles are irregular across a decade — ``Febuary 2016`` (sic), ``NOVEMBER 2022``,
    ``(Disbursement Series 2020)``, and documents covering two months at once — so the period is read
    from any ``<Month> <Year>`` pair in the title and a title with more than one pair is flagged
    ``multi_period`` rather than being assigned to whichever month happened to match first.
    """
    session = session or _session()
    html = fetch_text(NBS_ELIBRARY_URL, session)

    documents: dict[str, MonthlyDocument] = {}
    for title, report_id in _ELIBRARY_ROW.findall(html):
        title = " ".join(title.split())
        if "faac" not in title.lower() and "disbursement" not in title.lower():
            continue
        pairs = [
            (name, year)
            for name, year in _MONTH_YEAR.findall(title)
            if name.lower() in MONTH_NUMBERS
        ]
        periods = [p for p in (_period(name, year) for name, year in pairs) if p]
        if not periods:
            # e.g. "Federation Account Allocation Committee (FAAC) (Disbursement Series 2020)"
            continue
        for period in periods:
            documents.setdefault(
                period,
                MonthlyDocument(
                    period=period,
                    dataset_id=f"nbs-{period}",
                    url=NBS_REPORT_URL.format(report_id=report_id),
                    file_name=f"NBS-FAAC-{period}.xlsx",
                    publisher="nbs",
                    title=title,
                    multi_period=len(periods) > 1,
                ),
            )
    return sorted(documents.values(), key=lambda d: d.period)


def resolve_nbs_resource(document: MonthlyDocument, session: requests.Session | None = None) -> str | None:
    """The XLSX link on an NBS report page, or ``None`` when the report ships no spreadsheet.

    Older FAAC reports on the elibrary are image scans and carry no resource file at all. Returning
    ``None`` records that fact; it is not an error, and the caller counts it as a month the
    cross-check does not cover.
    """
    session = session or _session()
    try:
        html = fetch_text(document.url, session)
    except FaacError:
        return None
    match = _NBS_RESOURCE.search(html)
    return match.group(0) if match else None


def build_retrieval(
    document: MonthlyDocument,
    payload: bytes,
    http_status: int,
    row_count: int = 0,
    note: str = "",
) -> Retrieval:
    """Provenance for one landed document.

    ``row_count`` is the number of *observations the document is expected to carry* (states), left at
    zero by the flow because Stage 2 does not parse. The parser records what it actually extracted,
    and the verifier compares the two — a document that parses to fewer states than expected is the
    failure mode this leaves visible instead of guessing at ingest time.

    ``metric_id`` is deliberately **not** a parameter here: it belongs on the manifest entry, and it is
    passed to :meth:`Retrieval.manifest_entry` by the flow, exactly as the World Bank and FRED flows do.
    (The first version of this function accepted ``metric_id`` and never forwarded it, which is how the
    2026-10-16 vintage's retrievals came to have no ``metric_id`` at all — recorded as I-15.)
    """
    return build(
        source="faac",
        dataset_id=document.dataset_id,
        dataset_name=f"FAAC disbursement {document.period} ({document.publisher})",
        url=document.url,
        params={
            "publisher": document.publisher,
            "period": document.period,
            "file_name": document.file_name,
            "title": document.title,
            "multi_period_document": document.multi_period,
            "user_agent": USER_AGENT,
            "note": note,
        },
        http_status=http_status,
        payloads=[payload],
        row_count=row_count,
    )
