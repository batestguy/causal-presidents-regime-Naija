"""Build the site's copy of the administration spine.

`dbt/seeds/raw_administration.csv` is the source of truth for who governed when. The app may not open DuckDB
or read dbt seeds, so this script writes the five rows into `registry/reference/administrations.json` with the
seed's sha256 recorded beside them: a seed edited without a rebuild fails the site verifier rather than quietly
serving dates the base no longer holds.

What this file deliberately does not contain: an outcome, an estimate, a verdict, or a sentence about a
presidency. Those live on cards. This is a spine.

Run:
    python scripts/build_administrations.py
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED = REPO_ROOT / "dbt" / "seeds" / "raw_administration.csv"
OUT = REPO_ROOT / "registry" / "reference" / "administrations.json"
PORTRAIT_DIR = "site/assets/presidents"

# The seed carries a president's name; the site needs a stable anchor for URLs, filenames and the portrait
# manifest. Typing five slugs is the one thing this script must be told, because a slug derived by lowercasing
# a name with an apostrophe ("Yar'Adua") is the kind of cleverness that breaks a URL later.
SLUGS = {
    1: "obasanjo",
    2: "yaradua",
    3: "jonathan",
    4: "buhari",
    5: "tinubu",
}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    rows = list(csv.DictReader(SEED.open(encoding="utf-8", newline="")))
    if len(rows) != len(SLUGS):
        raise SystemExit(f"seed has {len(rows)} administrations, expected {len(SLUGS)}")

    administrations = []
    for row in sorted(rows, key=lambda r: r["start_date"]):
        admin_id = int(row["admin_id"])
        slug = SLUGS[admin_id]
        end_date = (row.get("end_date") or "").strip() or None
        supplied = any((REPO_ROOT / PORTRAIT_DIR / f"{slug}{ext}").exists() for ext in (".jpg", ".jpeg", ".png"))
        administrations.append(
            {
                "admin_id": admin_id,
                "slug": slug,
                "president": row["president"].strip(),
                "party": row["party"].strip(),
                "start_date": row["start_date"].strip(),
                "end_date": end_date,
                "n_terms": int(row["n_terms"]),
                "note": (row.get("notes") or "").strip() or None,
                "portrait_path": f"{PORTRAIT_DIR}/{slug}.jpg",
                "portrait_status": "supplied" if supplied else "not_supplied",
            }
        )

    open_ended = sum(1 for a in administrations if a["end_date"] is None)
    if open_ended > 1:
        raise SystemExit("more than one open-ended administration: the seed is wrong, not the input")

    payload = {
        "schema_version": "0.1.0",
        "layer": "the five administrations of the study window, as the cover reads them",
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "generator": {"script": "scripts/build_administrations.py"},
        "source": {
            "path": "dbt/seeds/raw_administration.csv",
            "sha256": sha256_of(SEED),
            "why": "the base's spine is the seed; the site's copy exists so the app never opens DuckDB or dbt, "
                   "and the hash is recorded so a seed edit without a rebuild fails the site verifier",
        },
        "counts": {"administrations": len(administrations), "open_ended": open_ended},
        "administrations": administrations,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(REPO_ROOT)} — {len(administrations)} administrations, {open_ended} open-ended")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
