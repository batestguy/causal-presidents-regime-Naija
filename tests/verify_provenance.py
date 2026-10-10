"""Verify the provenance chain of a raw vintage.

Checks that the sha256 recorded in ``manifest.json`` reproduces from the page files on
disk — i.e. that the stored raw payload is byte-identical to what the API returned when
the manifest was written. Exits non-zero if any retrieval fails.

Usage:
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_provenance.py [vintage]
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPO_ROOT / "data" / "raw" / "worldbank"


def latest_vintage() -> str:
    vintages = sorted(p.name for p in RAW_ROOT.iterdir() if p.is_dir())
    if not vintages:
        raise SystemExit(f"no vintages under {RAW_ROOT}")
    return vintages[-1]


def main() -> int:
    vintage = sys.argv[1] if len(sys.argv) > 1 else latest_vintage()
    vintage_dir = RAW_ROOT / vintage
    manifest_path = vintage_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"no manifest at {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Accept either the shared schema's key or the original World Bank-specific one.
    n_datasets = manifest.get("n_datasets_succeeded", manifest.get("n_indicators_succeeded", 0))
    print(f"vintage {vintage}: {n_datasets} retrievals, {manifest.get('n_failures', 0)} failures")

    failures: list[str] = []
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
            f"pages={retrieval['page_count']} rows={retrieval['row_count']:<4} "
            f"status={retrieval['http_status']} sha256={retrieval['sha256'][:12]}"
        )

    if manifest.get("failures"):
        failures.extend(
            f"retrieval failure: {f['metric_id']} ({f['error']})" for f in manifest["failures"]
        )

    # Orphan check: a page file on disk that no manifest entry references means the vintage
    # is no longer fully accounted for — exactly what happens when a metric is dropped from
    # the catalogue after its payload has already landed.
    referenced = {
        page.replace("\\", "/")
        for retrieval in manifest["retrievals"]
        for page in retrieval["page_files"]
    }
    on_disk = {path.relative_to(REPO_ROOT).as_posix() for path in vintage_dir.rglob("page-*.json")}
    unreferenced = sorted(on_disk - referenced)
    if unreferenced:
        failures.extend(f"orphaned page file (not in manifest): {path}" for path in unreferenced)
    print(f"  page files on disk: {len(on_disk)}, referenced: {len(referenced)}, orphaned: {len(unreferenced)}")

    print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures:
            print(f"  - {problem}")
        return 1
    print("PASS — every stored payload reproduces its recorded sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
