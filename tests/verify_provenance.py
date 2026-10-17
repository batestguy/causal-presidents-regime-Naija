"""Verify the provenance chain of a raw vintage, for every source.

Checks that the sha256 recorded in ``manifest.json`` reproduces from the page files on
disk — i.e. that the stored raw payload is byte-identical to what the API returned when
the manifest was written. Exits non-zero if any retrieval fails.

Every source under ``data/raw/`` is verified, each at its latest vintage unless one is named.
This is deliberate: there is one provenance implementation shared by every client
(decisions.md I-06), so there is one verifier that walks all of them rather than one per source.

Usage:
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_provenance.py
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_provenance.py --source worldbank
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_provenance.py --vintage 2026-10-11
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_provenance.py 2026-10-11   # legacy
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPO_ROOT / "data" / "raw"


def latest_vintage(source_dir: Path) -> str:
    vintages = sorted(p.name for p in source_dir.iterdir() if p.is_dir())
    if not vintages:
        raise SystemExit(f"no vintages under {source_dir}")
    return vintages[-1]


def verify(source: str, vintage: str) -> list[str]:
    """Verify one source's vintage. Returns a list of problems (empty means clean)."""
    vintage_dir = RAW_ROOT / source / vintage
    manifest_path = vintage_dir / "manifest.json"
    if not manifest_path.exists():
        return [f"{source}/{vintage}: no manifest at {manifest_path}"]

    failures: list[str] = []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Accept either the shared schema's key or the original World Bank-specific one.
    n_datasets = manifest.get("n_datasets_succeeded", manifest.get("n_indicators_succeeded", 0))
    print(f"{source} @ {vintage}: {n_datasets} retrievals, {manifest.get('n_failures', 0)} failures")

    for retrieval in manifest["retrievals"]:
        digest = hashlib.sha256()
        try:
            for page_file in retrieval["page_files"]:
                digest.update((REPO_ROOT / page_file).read_bytes())
        except FileNotFoundError as exc:
            failures.append(f"{retrieval['metric_id']}: missing page file ({exc})")
            continue

        matches = digest.hexdigest() == retrieval["sha256"]
        if not matches:
            failures.append(
                f"{retrieval['metric_id']}: sha256 mismatch "
                f"(manifest {retrieval['sha256'][:12]}, on disk {digest.hexdigest()[:12]})"
            )
        print(
            f"  {'ok  ' if matches else 'FAIL'} {retrieval['metric_id']:<20} "
            f"pages={retrieval['page_count']} rows={retrieval['row_count']:<5} "
            f"status={retrieval['http_status']} sha256={retrieval['sha256'][:12]}"
        )

    for failure in manifest.get("failures", []):
        failures.append(f"retrieval failure: {failure['metric_id']} ({failure['error']})")

    # Orphan check: a page file on disk that no manifest entry references means the vintage
    # is no longer fully accounted for — exactly what happens when a metric is dropped from
    # the catalogue after its payload has already landed.
    # Any extension, not just ``.json``: a document source lands ``page-0001.pdf`` or
    # ``page-0001.xlsx`` under the same layout (see ``provenance.write_blobs``), and a glob pinned to
    # ``.json`` would leave those payloads outside the orphan check — so the check would keep passing
    # while silently covering less of the vintage than it claims to.
    referenced = {
        page.replace("\\", "/")
        for retrieval in manifest["retrievals"]
        for page in retrieval["page_files"]
    }
    on_disk = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in vintage_dir.rglob("page-*")
        if path.is_file()
    }
    unreferenced = sorted(on_disk - referenced)
    if unreferenced:
        failures.extend(f"orphaned page file (not in manifest): {path}" for path in unreferenced)
    print(f"  page files on disk: {len(on_disk)}, referenced: {len(referenced)}, "
          f"orphaned: {len(unreferenced)}")
    missing = sorted(referenced - on_disk)
    if missing:
        failures.extend(f"referenced page file absent from disk: {path}" for path in missing)
    return failures


def parse_args(argv: list[str]) -> tuple[list[str], str | None]:
    """``--source`` (repeatable) and ``--vintage``; a bare positional is the legacy vintage form."""
    sources: list[str] = []
    vintage: str | None = None
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--source":
            index += 1
            sources.append(argv[index])
        elif arg.startswith("--source="):
            sources.append(arg.split("=", 1)[1])
        elif arg == "--vintage":
            index += 1
            vintage = argv[index]
        elif arg.startswith("--vintage="):
            vintage = arg.split("=", 1)[1]
        else:
            vintage = arg  # legacy positional form
        index += 1
    return sources, vintage


def main() -> int:
    if not RAW_ROOT.exists():
        raise SystemExit(f"no raw data at {RAW_ROOT}")

    requested, vintage = parse_args(sys.argv[1:])
    available = sorted(p.name for p in RAW_ROOT.iterdir() if p.is_dir())
    sources = requested or available
    unknown = [s for s in sources if s not in available]
    if unknown:
        raise SystemExit(f"unknown source(s) {unknown}; available: {available}")
    if not sources:
        raise SystemExit(f"nothing to verify under {RAW_ROOT}")

    all_failures: list[str] = []
    for index, source in enumerate(sources):
        if index:
            print()
        resolved = vintage or latest_vintage(RAW_ROOT / source)
        all_failures.extend(f"{source}: {problem}" for problem in verify(source, resolved))

    print()
    if all_failures:
        print(f"FAILED — {len(all_failures)} problem(s):")
        for problem in all_failures:
            print(f"  - {problem}")
        return 1
    print(f"PASS — every stored payload reproduces its recorded sha256 "
          f"across {len(sources)} source(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
