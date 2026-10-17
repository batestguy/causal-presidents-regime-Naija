"""Stage 2 parser: the FAAC monthly disbursement workbook -> tidy per-state allocations.

PHASES.md Stage 2: *"Manual sources: ``ingestion/manual/inbox/`` drop zone + one parser per file
format, recording the file hash so a re-download is detectable and re-parsing never requires
re-OCRing."* This is that parser, one stage further on: the payloads are acquired by
``ingestion/flows/pull_faac.py`` rather than dropped in the inbox, because the OAGF archive turned out
to be reachable after all — but the contract is the same, and it is the reason this module takes
**bytes plus the recorded sha256** rather than a path it can silently re-read.

Reads the landed payloads of a vintage and writes::

    data/staging/faac_state_allocation.csv

one row per (period, publisher, state, item) with the amount and the sha256 of the document it came
from, plus ``data/staging/faac_parse_report.json`` — the per-document parse report, which is where the
header cells this parser could not resolve are enumerated (see the measured limit below).

Long format rather than one column per item, because **the workbook's columns drift**:

* 2019 carries 19-20 columns and no ``Electronic Money Transfer Levy`` (it did not exist);
* 2025 carries 22-23 and adds ``Augmentation``, ``13% Derivation of Augmentation`` and the ecology
  columns;
* the same month's Table III is published twice, as PDF (OAGF) and as XLSX (NBS), with the same
  header vocabulary but different cell types.

A wide schema would therefore need a column set that is wrong for most months. The long format records
what the document actually carried and leaves absent items absent, so a month that never had an EMTL
column cannot be read as a month where EMTL was zero.

**The item set is a measured subset, not the whole workbook.** Over the 174 documents of the
2026-10-16 vintage the parser resolves 11-18 items per document, and **541 header cells (136 distinct)
do not resolve**, enumerated per document in ``unmapped_header_cells``. Three kinds, and they are worth
separating because only the third is a loss:

* group headings that denote no single column (``DEDUCTIONS`` 148x, ``DEDUCTION`` 62x) — the members sit
  on the line below and *do* resolve;
* era-specific channels the documents carry for a few months (``TRANSFER OF 50% SHARE OF ECOLOGY TO
  NDDC/HYPPADEC`` 74x, ``DISTRIBUTION OF EXCESS BANK CHARGES`` 8x, the solid-mineral and forex
  equalisation distributions) — real columns, folded into the documents' own totals, not resolved as
  items;
* **interleaving garble hiding a real column** (``13% SHAR(EN OEFT D)ERIVATION`` 9x, which is
  ``13% SHARE OF DERIVATION (NET)``).

The consequence for what this table may be used for is narrow and stated rather than implied: the
**dose column is not among the losses** — ``gross_total`` resolves in all 174 documents and every one of
them reconciles against its own Total row — but the *decomposition* columns (the derivation share, the
ecology and exchange-gain channels) are incomplete for the months and eras listed in the report. A
month with no ``derivation_13pct`` item means "not resolved", which is not the same claim as "the
document published no such column".

Five refusals, each of which is a real failure mode rather than defensive padding:

1. **A document that does not yield exactly the 36 states is a failure.** A mis-located table, a
   shifted column or a truncated page all show up as "fewer than 36 states", and a partially read
   document is worse than a missing one because it looks complete.
2. **``Total Gross Amount`` and ``Total Net Amount`` must both be present.** They are the quantity the
   dose is computed from; a document whose header did not resolve is refused rather than landed with
   nulls that later read as "the state received nothing".
3. **The Table III title is what locates the table**, not a page number. Page 1 of the same PDF also
   contains the string ``Table III`` — inside ``State (see Table III)`` in the Table I summary — so a
   locator keyed on that string reads the wrong table and reports the federal government's own line
   as a state. The title line of the states distribution is the only reliable anchor.
4. **A header cell the alias table cannot resolve is reported, never silently dropped.**
   ``unmapped_header_cells`` collects every cell that carried letters and did not resolve to an item, per
   document, and the parse report is written to ``data/staging/faac_parse_report.json`` so the loss is
   durable rather than a line of console output. This exists because of a measured failure: the 11 OAGF
   documents of 2022 publish a 13% derivation column whose header the PDF text layer interleaves with a
   neighbouring line (``13% SHAR(EN OEFT D)ERIVATION`` for ``13% SHARE OF DERIVATION (NET)``), so
   ``derivation_13pct`` is genuinely absent from those months and the absence would otherwise be
   indistinguishable from the 2023-2025 layouts, where the item is a real zero-or-more column. The dose
   is not affected — it is read from ``gross_total``, which every one of those documents totals — but the
   *item set* would have been lying about what the document carried.
5. **The distribution names 36 states, and sometimes a 37th line whose label is not reliable.** The
   2026 documents call that line ``FCT ABUJA``; the 2024 ones render it ``SOKU``. Its amounts are
   included in the document's own Total row, so it is returned for reconciliation — but it is **not**
   written to the state table, because a label that differs between publications is not an identity and
   mapping it to the FCT on the strength of one document's spelling would put an invented series in the
   panel. The consequence is that the FCT has no dose, which `state_panel` records as a declared status
   rather than a gap. (This is the second version of this rule: the first asserted the line did not
   exist at all, and the total-row mismatch that followed is what disproved it.)

Amounts are read with PDF text-extraction artefacts repaired: the OAGF PDFs scatter the leading digit
or digits from the rest of a number (``4 ,187,700,320.97``, ``1 4,745,018,620.41``), so **all
whitespace is removed before the number is parsed**. This is checked rather than assumed — every
parsed amount is compared against the document's own ``Total`` row, and a month whose states do not sum
to the published total is refused. ``-`` is the document's own nil and becomes ``0.0``; an empty cell
becomes SQL NULL.

Run::

    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/parsers/faac_disbursement.py
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/parsers/faac_disbursement.py --strict-primary
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import openpyxl
import pdfplumber

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

RAW_ROOT = REPO_ROOT / "data" / "raw" / "faac"
OUT_PATH = REPO_ROOT / "data" / "staging" / "faac_state_allocation.csv"

# The 36 beneficiaries of Table III, in the order the document lists them. The FCT is deliberately
# absent: it is not a state in this distribution (see the module docstring).
STATES = [
    "ABIA", "ADAMAWA", "AKWA IBOM", "ANAMBRA", "BAUCHI", "BAYELSA", "BENUE", "BORNO", "CROSS RIVER",
    "DELTA", "EBONYI", "EDO", "EKITI", "ENUGU", "GOMBE", "IMO", "JIGAWA", "KADUNA", "KANO", "KATSINA",
    "KEBBI", "KOGI", "KWARA", "LAGOS", "NASSARAWA", "NIGER", "OGUN", "ONDO", "OSUN", "OYO", "PLATEAU",
    "RIVERS", "SOKOTO", "TARABA", "YOBE", "ZAMFARA",
]
# The published spellings, mapped to the seed's ``state_name``. Only the one that actually differs is
# listed: the documents write NASSARAWA where the seed writes Nasarawa, and a silent mismatch there
# would drop a state from the panel without any row saying so.
STATE_ALIASES = {"NASSARAWA": "Nasarawa"}
STATE_IDS = {
    "Abia": 1, "Adamawa": 2, "Akwa Ibom": 3, "Anambra": 4, "Bauchi": 5, "Bayelsa": 6, "Benue": 7,
    "Borno": 8, "Cross River": 9, "Delta": 10, "Ebonyi": 11, "Edo": 12, "Ekiti": 13, "Enugu": 14,
    "FCT": 15, "Gombe": 16, "Imo": 17, "Jigawa": 18, "Kaduna": 19, "Kano": 20, "Katsina": 21,
    "Kebbi": 22, "Kogi": 23, "Kwara": 24, "Lagos": 25, "Nasarawa": 26, "Niger": 27, "Ogun": 28,
    "Ondo": 29, "Osun": 30, "Oyo": 31, "Plateau": 32, "Rivers": 33, "Sokoto": 34, "Taraba": 35,
    "Yobe": 36, "Zamfara": 37,
}

# The items the dose and its decomposition need, plus the era-specific gross channels that were
# findable from the documents' own totals, with the header spellings that denote each. Matched as
# prefixes against the longest alias first, because ``NET STATUTORY ALLOCATION`` and
# ``STATUTORY ALLOCATION`` both exist in the same header row and a shortest-first match would put one in
# the other's column. This is **not** every column the workbook carries: see the measured item-set limit
# in the module docstring, and ``unmapped_header_cells`` in the parse report for what was not resolved.
ITEM_HEADERS: list[tuple[str, tuple[str, ...]]] = [
    ("n_lgcs", ("NO. OF LGCS", "NO OF LGCS")),
    ("gross_statutory_allocation", ("GROSS STATUTORY ALLOCATION", "STATUTORY ALLOCATION")),
    ("derivation_13pct", ("13% SHARE OF DERIVATION", "13 SHARE OF DERIVATION")),
    ("gross_total", ("GROSS TOTAL",)),
    ("deduction_external_debt", ("EXTERNAL DEBT",)),
    ("deduction_contractual_obligation", ("CONTRACTUAL OBLIGATION", "DEDUCTIONS CONTRACTUAL")),
    ("deduction_other", ("OTHER DEDUCTIONS",)),
    ("net_statutory_allocation", ("NET STATUTORY ALLOCATION",)),
    # Two genuinely different quantities: the ₦214bn augmentation itself, and the state's total of it
    # once the 13% derivation share is added. Mapping both to one item would leave whichever column
    # was read last, which is how a parser reports a number that is not wrong-looking but is wrong.
    ("augmentation", ("AUGMENTATION",)),
    ("augmentation_total", ("TOTAL AUGMENTATION",)),
    ("emtl", ("ELECTRONIC MONEY TRANSFER LEVY", "EMTL")),
    ("ecology_gross_statutory", ("GROSS STATUTORY ALLOCATION (ECOLOGY)",)),
    ("ecology_total_share", ("TOTAL SHARE OF ECOLOGY",)),
    ("ecology_net_share", ("NET SHARE OF ECOLOGY",)),
    # ``FOREX Equalisation Fund`` and ``Exchange Gain`` are separate columns in the 2019-2020 layout
    # and collapse into one by 2025; they are kept apart so a month that carries both does not
    # silently lose one of them.
    ("forex_equalisation", ("FOREX EQUALISATION",)),
    ("exchange_gain", ("EXCHANGE GAIN", "DISTRIBUTION OF EXCHANGE")),
    ("exchange_rate_differential", ("EXCHANGE RATE DIFFERENTIAL", "EXCHANGE GAIN DIFFERENCE")),
    ("total_exchange_gain", ("TOTAL EXCHANGE GAIN",)),
    # The remaining gross channels are era-specific: they exist for a few years and then disappear,
    # and each is named differently in each layout. They are listed because the documents' own totals
    # include them, which is how each was found — see `gross_channels`.
    ("good_and_value_consideration", ("GOOD & VALUE CONSIDERATION", "GOOD AND VALUE CONSIDERATION")),
    ("additional_funds_nnpc", ("ADDITIONAL FUNDS FROM NNPC", "ADDITIONAL FUND FROM NNPC", "ADDITIONAL FUNDS")),
    ("gross_vat_allocation", ("GROSS VAT ALLOCATION", "VAT GROSS")),
    ("vat_deduction", ("VAT DEDUCTION", "VAT DEDUCT", "DEDUCTION(VAT)")),
    ("net_vat_allocation", ("NET VAT ALLOCATION", "NET VAT")),
    # One figure, two spellings across layout eras: "Total Gross Amount" (2019-2024 and 2026) and
    # "Total Gross Allocation" (2025). Both aliases map to the one item, so no ambiguity is created.
    ("total_gross_amount", ("TOTAL GROSS AMOUNT", "TOTAL GROSS ALLOCATION")),
    ("total_net_amount", ("TOTAL NET AMOUNT", "TOTAL NET ALLOCATION")),
]

# The quantity the exposure is measured on. ``Gross Total`` — the statutory allocation plus the 13%
# derivation share — is the **only** per-state figure that every layout publishes in the same place and
# under the same name, across all 174 documents. That property is worth more than width here, and it was
# not assumed: three other candidates were tried and rejected against the documents themselves.
#
#   * ``Total Gross Amount`` (the full share: statutory + derivation + VAT + EMTL + ecology +
#     augmentation) exists only from 2024. Its own column-number row declares how it is built
#     ("21=6+13+14+15+18"), but the referenced indices do not survive extraction on every layout —
#     2024-01 extracts a duplicated ``Gross VAT Allocation`` column — so reading it back was wrong by
#     hundreds of millions on several months rather than failing outright.
#   * Summing the gross channels instead was short by a *different* amount on the same months, which is
#     the signature of a channel the header does not name at all.
#   * The 2020-2023 layouts publish no total column whatsoever, so neither approach covers them anyway.
#
# ``Total Gross Amount`` is still extracted wherever a document carries it, because it is the natural
# robustness axis, and every month it exists it is carried on the row with its provenance. It is simply
# not the dose.

# A few columns wear the same name in every era but sit behind an era-specific prefix ("Distribution of
# ₦100 billion from Non-Oil Excess Account"), so prefix matching cannot see them and they are matched on
# a distinctive phrase instead. Longest phrase first, for the same reason as the aliases above.
ITEM_CONTAINS: list[tuple[str, tuple[str, ...]]] = [
    ("non_oil_excess", ("NON-OIL EXCESS",)),
]

# ``Gross Total`` (statutory allocation + the 13% derivation share) is present in every layout and is
# what a document is reconciled on. Its absence means the header did not resolve, which is a document
# the parser cannot read — and a partially read month is worse than a missing one because it looks
# complete.
REQUIRED_ITEMS = ("gross_total",)
# The whitespace repair is the parser's one real assumption, so its check is tight: the repaired
# per-state amounts must reproduce the document's own published total to within a billionth of it
# (and a naira, for the small months). The observed agreement is ~0.04 naira on a ₦718bn month; a
# single mis-repaired digit moves the sum by orders of magnitude more than this allows.
TOTAL_RELATIVE_TOLERANCE = 1e-9
TOTAL_ABSOLUTE_TOLERANCE = 1.0

# Longest alias wins, so the table is order-independent.
_ALIAS_ORDER = sorted(
    ((alias, item) for item, aliases in ITEM_HEADERS for alias in aliases),
    key=lambda pair: len(pair[0]),
    reverse=True,
)
_CONTAINS_ORDER = sorted(
    ((phrase, item) for item, phrases in ITEM_CONTAINS for phrase in phrases),
    key=lambda pair: len(pair[0]),
    reverse=True,
)

TITLE_ANCHOR = "REVENUE ALLOCATION TO STATE GOVERNMENTS"
_NIL = {"-", "–", "—", ""}
# Header cells that carry no column name, so an unresolved one of these is not a lost column.
_HEADER_NOISE = {"", "S/N", "S/N.", "SN", "BENEFICIARIES", "₦", "N"}
_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")


class FaacParseError(RuntimeError):
    """Raised when a document does not carry the Table III structure the parser requires."""


@dataclass
class Document:
    dataset_id: str
    publisher: str
    period: str
    payload_path: Path
    sha256: str
    page_files: list[str]
    http_status: int

    @property
    def file_name(self) -> str:
        return self.page_files[0] if self.page_files else self.payload_path.name


def normalise_name(value) -> str:
    return " ".join(str(value or "").upper().split())


# A header cell sometimes carries the workbook's own column reference in front of the name, e.g.
# ``21=6+13+14+15+18 Total Gross Amount`` (the 2025-06 layout) or ``4 Statutory Allocation``. The
# reference is stripped before matching. The rule requires the reference to be digits, arithmetic
# signs and spaces followed by whitespace, which is what keeps it away from a name that legitimately
# begins with a number: ``13% Share of Derivation`` is untouched, because ``%`` is not in the class
# and so the required trailing space never appears.
_COLUMN_REFERENCE = re.compile(r"^\d[\d\s=+()\-.]*\s+")


def normalise_header(value) -> str:
    """Header text as the document means it: the column reference stripped, upper-case, collapsed."""
    collapsed = " ".join(str(value or "").upper().split())
    return _COLUMN_REFERENCE.sub("", collapsed)


def item_for_header(header: str) -> str | None:
    for phrase, item in _CONTAINS_ORDER:
        if phrase in header:
            return item
    for alias, item in _ALIAS_ORDER:
        if header.startswith(alias):
            return item
    return None


def parse_amount(value) -> float | None:
    """One cell as a naira amount.

    ``None``/empty -> NONE (the cell is not there). ``-`` -> 0.0 (the document's own nil). Everything
    else has whitespace removed first: the PDFs split numbers across the text layer.
    """
    if value is None:
        return None
    text = str(value).strip()
    if text in _NIL:
        return None if text == "" else 0.0
    cleaned = re.sub(r"\s+", "", text.replace("₦", "").replace(",", ""))
    if not _NUMBER.match(cleaned):
        return None
    return float(cleaned)


_ANCHOR_BARE = re.sub(r"\s+", "", TITLE_ANCHOR)


def page_has_title(page) -> bool:
    """Whether a page carries the Table III title.

    Matched **whitespace-insensitively on both sides**. The title wraps across lines in several of the
    monthly documents (and the page text is laid out in columns), so a whitespace-sensitive comparison
    against a one-line anchor misses documents that plainly carry the title — which is exactly the bug
    this function was written to fix, in the other direction: stripping the whitespace from the page
    but not from the anchor makes the test unsatisfiable, and every document then scans all 36 pages
    before failing.
    """
    text = (page.extract_text() or "").upper()
    return _ANCHOR_BARE in re.sub(r"\s+", "", text)


def rows_from_pdf(payload: bytes) -> tuple[str, list[list]]:
    """The Table III rows of an OAGF PDF, and where they were found.

    Pages are scanned in order until the title is found, and the scan is stopped there: the state
    distribution is Table III and the local-government and ecology tables follow it, so the document
    runs to 36 pages that never need parsing. Per-page parsing, not the number of pages opened, is what
    this costs — hence the `--jobs` pool in :func:`main` rather than a narrower page bound here.
    """
    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            if not page_has_title(page):
                continue
            tables = page.extract_tables()
            if not tables:
                raise FaacParseError(f"Table III title on page {index} but no table extracted")
            return f"page-{index:04d}", tables[0]
        raise FaacParseError(f"no page carries the Table III title ({TITLE_ANCHOR})")


def rows_from_xlsx(payload: bytes) -> tuple[str, list[list]]:
    """The Table III rows of an NBS XLSX: the sheet whose header names the beneficiaries."""
    book = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    try:
        for name in book.sheetnames:
            rows = [list(row) for row in book[name].iter_rows(values_only=True)]
            if not rows:
                continue
            head = " | ".join(normalise_header(cell) for row in rows[:15] for cell in row)
            if "BENEFICIARIES" in head and "TOTAL GROSS AMOUNT" in head:
                return f"sheet:{name}", rows
    finally:
        book.close()
    raise FaacParseError("no sheet carries the Table III header (Beneficiaries + Total Gross Amount)")


def extract_state_rows(
    rows: list[list],
) -> tuple[
    dict[str, dict[str, float | None]],
    list[tuple[str, dict[str, float | None]]],
    list[str],
    dict[str, list[int]],
]:
    """Map a Table III row block to ``({state: {item: amount}}, extra_rows, ignored_labels)``.

    ``extra_rows`` are data rows that carry amounts but are **not** one of the 36 states — the
    distribution's own 37th beneficiary line. It exists in the documents and its published label is
    not reliable: the 2026 documents name it ``FCT ABUJA`` and the 2024 ones render it ``SOKU``. It is
    therefore **kept out of the state table** (a garbled label is not an identity, and mapping it to the
    FCT on the strength of one document's spelling would put an invented series in the panel) while
    being **returned for reconciliation**, because the document's own Total row does include it — which
    is how the mismatch that first exposed this was found.

    ``ignored_labels`` records everything else that was present: header fragments, the ₦ unit row and
    the Total row itself.
    """
    header_index = None
    for index, row in enumerate(rows):
        if any(normalise_header(cell) == "BENEFICIARIES" for cell in row):
            header_index = index
            break
    if header_index is None:
        raise FaacParseError("no header row naming the beneficiaries")

    # The header may run over several rows (a group header "Deductions" with its three members on the
    # next line), so the column map is built from the header row and every non-data row beneath it
    # until the first state row.
    header_row = rows[header_index]
    column_item: dict[int, str] = {}
    # Every header cell that carried letters and resolved to nothing. Recorded rather than dropped,
    # because "the document has no such column" and "the header did not resolve" are different facts and
    # the item set is only honest if it distinguishes them (see refusal 4 in the module docstring).
    unmapped_headers: list[str] = []

    def absorb(row: list) -> None:
        for column, cell in enumerate(row):
            if column in column_item:
                continue
            text = normalise_header(cell)
            if not text or text in _HEADER_NOISE or not any(ch.isalpha() for ch in text):
                continue
            item = item_for_header(text)
            if item is None:
                unmapped_headers.append(text)
            else:
                column_item[column] = item

    absorb(header_row)
    if not column_item:
        raise FaacParseError("header row resolved to no known items")

    for row in rows[header_index + 1:]:
        if any(normalise_name(cell) in STATES for cell in row[:2]):
            break
        absorb(row)

    unmapped_headers = list(dict.fromkeys(unmapped_headers))

    # Two columns resolving to one item is a header pair the alias table cannot tell apart, and letting
    # the second overwrite the first is invisible afterwards. Where it happens among the items the dose
    # needs, the document is refused: a required figure that could be either of two columns is not a
    # figure. Where it happens in an optional column, the **first** column is kept and the duplicate is
    # reported — the 2024-01 layout genuinely prints "Gross VAT Allocation" over two different columns,
    # which is a defect in the published workbook and not something a parser can resolve by guessing.
    collisions: dict[str, list[int]] = {}
    for column, item in sorted(column_item.items()):
        collisions.setdefault(item, []).append(column)
    ambiguous = {item: columns for item, columns in collisions.items() if len(columns) > 1}
    required_ambiguous = {item: columns for item, columns in ambiguous.items() if item in REQUIRED_ITEMS}
    if required_ambiguous:
        raise FaacParseError(
            f"required columns cannot be told apart: {required_ambiguous} — add an alias for the "
            "header text rather than letting one column overwrite the other"
        )
    for item, columns in ambiguous.items():
        for column in columns[1:]:
            del column_item[column]

    missing = [item for item in REQUIRED_ITEMS if item not in column_item.values()]
    if missing:
        raise FaacParseError(
            f"header did not resolve {missing}; resolved {sorted(column_item.values())}"
        )

    name_column = next(
        column for column, cell in enumerate(header_row) if normalise_header(cell) == "BENEFICIARIES"
    )

    extracted: dict[str, dict[str, float | None]] = {}
    extra_rows: list[tuple[str, dict[str, float | None]]] = []
    ignored: list[str] = []
    for row in rows[header_index + 1:]:
        if name_column >= len(row):
            continue
        label = normalise_name(row[name_column])
        if not label:
            continue
        values: dict[str, float | None] = {}
        for column, item in column_item.items():
            cell = row[column] if column < len(row) else None
            values[item] = parse_amount(cell)
        carries_amount = any(
            amount for item, amount in values.items() if item != "n_lgcs"
        )
        if label not in STATES:
            if label.startswith("TOTAL") or not carries_amount:
                # The Total row, the ₦ unit row, header fragments, and any zero-filled stray line.
                if label not in {"", "₦"}:
                    ignored.append(label)
                continue
            extra_rows.append((label, values))
            continue
        state = STATE_ALIASES.get(label, label.title())
        if state in extracted:
            raise FaacParseError(f"{state} appears twice in one Table III")
        extracted[state] = values
    return extracted, extra_rows, ignored, ambiguous, unmapped_headers


def published_total(rows: list[list], item: str) -> float | None:
    """The document's own ``Total (States)`` for the gross column, through the same column map.

    A cross-check on the whitespace repair: if the repaired per-state amounts do not reproduce the
    document's published total, the repair was wrong somewhere and the month is refused rather than
    landed with a plausible-looking wrong number.

    The Total row does **not** put its label in the first column (it reads ``Total (States)`` under
    ``Beneficiaries`` with an empty S/n), and it totals a *different* column depending on the layout —
    which is why the row is mapped through the header resolution rather than read positionally.

    The Total row **includes the distribution's own 37th beneficiary line**, so the caller reconciles
    the states plus that line against it. Reconcile on ``gross_total``: it is the one column every layout
    carries, whereas the layouts of 2020-2023 publish no total column at all.
    """
    header_index = None
    for index, row in enumerate(rows):
        if any(normalise_header(cell) == "BENEFICIARIES" for cell in row):
            header_index = index
            break
    if header_index is None:
        return None

    header_row = rows[header_index]
    target = next(
        (
            column
            for column, cell in enumerate(header_row)
            if item_for_header(normalise_header(cell)) == item
        ),
        None,
    )
    if target is None:
        return None

    for row in rows[header_index + 1:]:
        labels = [normalise_header(cell) for cell in row[:2]]
        if any(label.startswith("TOTAL") for label in labels):
            return parse_amount(row[target]) if target < len(row) else None
    return None


def parse_document(document: Document, vintage: str) -> tuple[list[dict], dict]:
    """Parse one landed payload. Returns ``(rows, report)``."""
    payload = document.payload_path.read_bytes()
    if document.publisher == "oagf":
        location, rows = rows_from_pdf(payload)
    else:
        location, rows = rows_from_xlsx(payload)

    extracted, extra_rows, ignored, ambiguous, unmapped_headers = extract_state_rows(rows)
    unknown = [state for state in extracted if state not in STATE_IDS]
    if unknown:
        raise FaacParseError(f"states not in the seed's 37 units: {unknown}")

    def tolerance_for(value: float) -> float:
        return max(TOTAL_ABSOLUTE_TOLERANCE, abs(value) * TOTAL_RELATIVE_TOLERANCE)

    # 1. Reconcile ``gross_total`` — the column every layout carries and every Total row totals.
    #    This is the check that guards the whitespace repair, and it includes the 37th beneficiary line
    #    because the document's own Total does (leaving it out is what once made 47 correct documents
    #    look like failed arithmetic).
    total = published_total(rows, "gross_total")
    gross_sum = sum(values["gross_total"] or 0.0 for values in extracted.values())
    extra_gross_sum = sum(values["gross_total"] or 0.0 for _, values in extra_rows)
    if total is not None and abs((gross_sum + extra_gross_sum) - total) > tolerance_for(total):
        raise FaacParseError(
            f"per-beneficiary gross total sums to {gross_sum + extra_gross_sum:,.2f} "
            f"(states {gross_sum:,.2f} + other lines {extra_gross_sum:,.2f}) but the document "
            f"publishes {total:,.2f} (tolerance {tolerance_for(total):,.2f})"
        )

    # 2. Cross-check on the documents the layout *does* total: the sum of ``total_gross_amount`` must
    #    match the Total row's own value for it. Not a gate for the dose — the dose is ``gross_total`` —
    #    but it is the widest available check on the whitespace repair, and it runs on the layouts that
    #    can support it.
    published_share = published_total(rows, "total_gross_amount")
    share_sum = sum(v.get("total_gross_amount") or 0.0 for v in extracted.values())
    share_sum += sum(v.get("total_gross_amount") or 0.0 for _, v in extra_rows)
    if published_share is not None and abs(share_sum - published_share) > tolerance_for(published_share):
        raise FaacParseError(
            f"per-beneficiary gross share sums to {share_sum:,.2f} but the document publishes "
            f"{published_share:,.2f} (tolerance {tolerance_for(published_share):,.2f})"
        )

    out: list[dict] = []
    n_items = 0
    for state, values in extracted.items():
        # `value_source` is carried on every row and is `document` throughout: nothing here is derived,
        # summed or estimated, and the column exists so that a future addition of a derived figure has to
        # say so on the row rather than blend into the published ones.
        emitted = dict(values)
        n_items = max(n_items, len(emitted))
        for item, amount in emitted.items():
            out.append(
                {
                    "vintage": vintage,
                    "period_month": document.period,
                    "publisher": document.publisher,
                    "state_id": STATE_IDS[state],
                    "state_name": state,
                    "state_name_published": state.upper(),
                    "item": item,
                    "amount_naira": amount,
                    "value_source": "document",
                    "source_dataset_id": document.dataset_id,
                    "source_file": document.file_name,
                    "source_sha256": document.sha256,
                    "source_location": location,
                }
            )

    report = {
        "dataset_id": document.dataset_id,
        "publisher": document.publisher,
        "period": document.period,
        "n_states": len(extracted),
        "n_items": n_items,
        "location": location,
        "gross_sum": gross_sum,
        "gross_total_published": total,
        "gross_share_published": published_share is not None,
        "other_beneficiary_sum": extra_gross_sum,
        "other_beneficiary_labels": sorted({label for label, _ in extra_rows}),
        "ambiguous_columns": ambiguous,
        "unmapped_header_cells": unmapped_headers,
        "ignored_labels": sorted(set(ignored)),
        "sha256": document.sha256,
    }
    return out, report


def documents_for(vintage: str) -> list[Document]:
    """The payloads of a vintage, straight from the manifest — paths come from the record, not a glob."""
    vintage_dir = RAW_ROOT / vintage
    manifest = json.loads((vintage_dir / "manifest.json").read_text(encoding="utf-8"))
    documents = []
    for retrieval in manifest["retrievals"]:
        entry = retrieval.get("params") or {}
        page_files = retrieval["page_files"]
        if not page_files:
            raise FaacParseError(f"{retrieval['dataset_id']}: manifest references no payload")
        documents.append(
            Document(
                dataset_id=retrieval["dataset_id"],
                publisher=entry.get("publisher", retrieval["dataset_id"].split("-")[0]),
                period=entry.get("period", retrieval["dataset_id"].split("-", 1)[-1]),
                payload_path=REPO_ROOT / page_files[0],
                sha256=retrieval["sha256"],
                page_files=page_files,
                http_status=retrieval["http_status"],
            )
        )
    return sorted(documents, key=lambda d: (d.period, d.publisher))


def parse_one(arguments: tuple[Document, str]) -> tuple[list[dict] | None, dict | None, str | None]:
    """Parse one document and return ``(rows, report, failure_reason)``.

    Top-level and argument-tupled so it can run in a worker process: ``pdfplumber`` spends ~5s per
    document reconstructing page layout, and that is CPU work in a library, not a property of the
    data (the whole analytical base is ~20k rows). 174 documents serially do not fit in a reasonable
    single command; the same 174 across a small pool do. The pool changes nothing about the result,
    only how long it takes, which is why every refusal below is still reported per document.
    """
    document, vintage = arguments
    try:
        rows, report = parse_document(document, vintage)
    except (FaacParseError, OSError, ValueError, KeyError) as exc:
        return None, None, f"{document.dataset_id}: {exc}"
    if report["n_states"] != len(STATES):
        return (
            None,
            None,
            f"{document.dataset_id}: parsed {report['n_states']} states, expected {len(STATES)}",
        )
    return rows, report, None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse the landed FAAC documents into a tidy table.")
    parser.add_argument("--vintage", default=None, help="vintage label (default: latest)")
    parser.add_argument(
        "--out",
        default=str(OUT_PATH),
        help="destination CSV (default: data/staging/faac_state_allocation.csv)",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=min(6, os.cpu_count() or 1),
        help="worker processes for the per-document parse (default: min(6, cpus))",
    )
    parser.add_argument(
        "--strict-primary",
        action="store_true",
        help="exit non-zero if any OAGF document fails to parse (the primary series)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if not RAW_ROOT.exists():
        print(f"REFUSED  no raw FAAC payloads at {RAW_ROOT.relative_to(REPO_ROOT)}")
        return 1

    vintages = sorted(p.name for p in RAW_ROOT.iterdir() if p.is_dir())
    if not vintages:
        print("REFUSED  no vintages under data/raw/faac")
        return 1
    vintage = args.vintage or vintages[-1]
    if vintage not in vintages:
        print(f"REFUSED  unknown vintage {vintage}; available {vintages}")
        return 1

    documents = documents_for(vintage)
    print(f"vintage: {vintage}")
    print(f"documents: {len(documents)}")

    rows: list[dict] = []
    reports: list[dict] = []
    failures: list[str] = []
    primary_failures = 0

    def handle(document: Document, document_rows, report, failure):
        if failure is not None:
            failures.append(failure)
            if document.publisher == "oagf":
                nonlocal primary_failures
                primary_failures += 1
            print(f"  FAIL  {document.publisher:<5} {document.period}  {failure}")
            return
        rows.extend(document_rows)
        reports.append(report)
        print(
            f"  ok    {document.publisher:<5} {document.period}  states={report['n_states']} "
            f"items={report['n_items']} {report['location']:<20} "
            f"gross={report['gross_sum'] / 1e9:>10,.2f}bn"
            + (" share:document" if report["gross_share_published"] else " share:not_published")
            + (" AMBIGUOUS" if report["ambiguous_columns"] else "")
        )

    if args.jobs > 1:
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            for document, (document_rows, report, failure) in zip(
                documents, pool.map(parse_one, [(d, vintage) for d in documents])
            ):
                handle(document, document_rows, report, failure)
    else:
        for document in documents:
            handle(document, *parse_one((document, vintage)))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # `vintage` travels on every row so a parsed table can be traced to the raw vintage it came from
    # without re-reading the manifest, and so a base built from one vintage can never be mistaken for
    # one built from another (X-07: a correction creates a new vintage, never an edit).
    fieldnames = [
        "vintage", "period_month", "publisher", "state_id", "state_name", "state_name_published",
        "item", "amount_naira", "value_source", "source_dataset_id", "source_file",
        "source_sha256", "source_location",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["period_month"], r["publisher"], r["state_id"], r["item"])))

    periods = sorted({report["period"] for report in reports})
    publishers: dict[str, int] = {}
    for report in reports:
        publishers[report["publisher"]] = publishers.get(report["publisher"], 0) + 1

    # The parse report is persisted, not printed and discarded. Two things in it exist only here: the
    # header cells the alias table could not resolve, and the per-document reconciliation against the
    # document's own Total row. Both are claims the docs make, so both need an artifact a verifier can
    # read rather than a console line nobody kept.
    header_losses: dict[str, list[str]] = {}
    for report in reports:
        if report["unmapped_header_cells"]:
            header_losses[report["dataset_id"]] = report["unmapped_header_cells"]
    report_path = out_path.with_name("faac_parse_report.json")
    report_path.write_text(
        json.dumps(
            {
                "vintage": vintage,
                "n_documents_parsed": len(reports),
                "n_documents_failed": len(failures),
                "n_rows": len(rows),
                "publishers": publishers,
                "first_period": periods[0] if periods else None,
                "last_period": periods[-1] if periods else None,
                "n_documents_with_unmapped_header_cells": len(header_losses),
                "unmapped_header_cells": header_losses,
                "documents": sorted(reports, key=lambda r: (r["period"], r["publisher"])),
                "failures": failures,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"parsed: {len(reports)} documents, {len(rows)} rows")
    print("publishers: " + ", ".join(f"{k}={v}" for k, v in sorted(publishers.items())))
    if periods:
        print(f"periods: {periods[0]} -> {periods[-1]} ({len(periods)} months)")
    print(f"table: {out_path.relative_to(REPO_ROOT)}")
    print(f"report: {report_path.relative_to(REPO_ROOT)}")
    if header_losses:
        lost = sorted({cell for cells in header_losses.values() for cell in cells})
        print(
            f"header cells that resolved to no item: {sum(len(v) for v in header_losses.values())} "
            f"across {len(header_losses)} document(s) — see the report's unmapped_header_cells"
        )
        for cell in lost[:12]:
            print(f"  - {cell}")

    if failures:
        print()
        print(f"{len(failures)} document(s) did not parse:")
        for failure in failures:
            print(f"  - {failure}")
    if args.strict_primary and primary_failures:
        print()
        print(f"FAILED — {primary_failures} primary (OAGF) document(s) did not parse")
        return 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
