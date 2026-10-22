"""Build the committed country vocabulary and donor-panel membership.

The intent gate's KG01 gap was declared because the donor panel's membership lived only in `data/`, which
is gitignored: a rule built on it would behave differently on a fresh clone, so the published metric would
not be reproducible. This script moves the two facts a country rule needs into `registry/`:

  * `registry/donors/<vintage>/panel.json` — the 99 members, derived from the acquisition manifest and the
    payloads it names (ISO-2 code, ISO-3 code, name), with the manifest's sha256 recorded.
  * `registry/reference/countries.json` — the ISO 3166-1 name list, generated from `pycountry` with its
    version recorded, plus the common English aliases a question is likely to use ("Russia", "South Korea",
    "Ivory Coast", …). The alias map is declared here rather than invented by a model.

Neither file carries a statistic. They are reference data, and they are committed so the gate's decision is
the same on this machine and on a fresh clone.

Usage:
    python scripts/build_country_vocabulary.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DONORS_RAW = REPO_ROOT / "data/raw/worldbank_donors"
PANEL_OUT = REPO_ROOT / "registry/donors"
COUNTRIES_OUT = REPO_ROOT / "registry/reference/countries.json"
SCHEMA_VERSION = 1

# Common English names and short forms, by ISO-3. pycountry's official names are long ("Korea, Republic
# of"), and a question asks about "South Korea". The list is deliberately small and readable: every entry
# is a name a reader would use, not a model's guess.
ALIASES: dict[str, list[str]] = {
    "ARE": ["UAE", "United Arab Emirates"],
    "BIH": ["Bosnia"],
    "BRN": ["Brunei"],
    "CAF": ["Central African Republic"],
    "COD": ["DR Congo", "DRC", "Democratic Republic of the Congo", "Congo"],
    "COG": ["Republic of the Congo", "Congo"],
    "CIV": ["Ivory Coast", "Cote d'Ivoire"],
    "CZE": ["Czech Republic"],
    "EGY": ["Egypt"],
    "GMB": ["Gambia"],
    "IRN": ["Iran"],
    "KOR": ["South Korea", "Korea"],
    "LAO": ["Laos"],
    "MDA": ["Moldova"],
    "MKD": ["North Macedonia", "Macedonia"],
    "NLD": ["Holland"],
    "PRK": ["North Korea"],
    "RUS": ["Russia"],
    "SYR": ["Syria"],
    "TUR": ["Turkey", "Turkiye"],
    "TZA": ["Tanzania"],
    "USA": ["United States", "USA"],
    "VNM": ["Vietnam"],
    "VEN": ["Venezuela"],
    "YEM": ["Yemen"],
    "BOL": ["Bolivia"],
    "TWN": ["Taiwan"],
}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def newest(pattern: str) -> Path:
    paths = sorted(REPO_ROOT.glob(pattern))
    if not paths:
        raise SystemExit(f"no files match {pattern!r} — the raw layer is not landed")
    return paths[-1]


def panel_members() -> tuple[dict, list[dict]]:
    manifest_path = newest("data/raw/worldbank_donors/*/manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    vintage = manifest_path.parent.name
    codes = set((manifest.get("donors") or {}).keys())
    if not codes:
        raise SystemExit(f"{manifest_path}: the manifest names no donors")

    members: dict[str, dict] = {}
    for payload in sorted(manifest_path.parent.glob("*/*.json")):
        rows = json.loads(payload.read_text(encoding="utf-8"))
        if not isinstance(rows, list) or len(rows) < 2 or not isinstance(rows[1], list):
            continue
        for row in rows[1]:
            code = str((row.get("country") or {}).get("id") or "")
            if code not in codes:
                continue
            members.setdefault(code, {
                "iso2": code,
                "iso3": row.get("countryiso3code"),
                "name": (row.get("country") or {}).get("value"),
            })
    missing = sorted(codes - set(members))
    if missing:
        raise SystemExit(f"the payloads do not name every donor in the manifest: {missing}")
    return {
        "manifest": manifest_path.relative_to(REPO_ROOT).as_posix(),
        "manifest_sha256": sha256_of(manifest_path),
        "vintage": vintage,
        "n_donors": len(codes),
    }, [members[code] for code in sorted(members)]


def world_list() -> tuple[dict, list[dict]]:
    try:
        import pycountry
    except ImportError as error:  # pragma: no cover - a build-time dependency only
        raise SystemExit("pycountry is required to regenerate the vocabulary: pip install pycountry") from error
    countries = []
    for country in pycountry.countries:
        name = str(getattr(country, "name", "") or "")
        if not name:
            continue
        aliases = sorted({name, *(ALIASES.get(country.alpha_3, []))})
        countries.append({
            "iso3": country.alpha_3,
            "iso2": getattr(country, "alpha_2", None),
            "name": name,
            "aliases": aliases,
        })
    countries.sort(key=lambda item: item["iso3"])
    return {
        "pycountry": getattr(pycountry, "__version__", "unknown"),
        "source": "ISO 3166-1 via pycountry",
        "n_countries": len(countries),
    }, countries


def main() -> int:
    source, members = panel_members()
    vintage = source["vintage"]
    world, countries = world_list()
    version = world["pycountry"]

    panel = {
        "schema_version": SCHEMA_VERSION,
        "layer": "donor-panel membership (Stage 5's Design C candidate set, committed for the gate)",
        "vintage": vintage,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": {
            "script": "scripts/build_country_vocabulary.py",
            "source": source["manifest"],
            "source_sha256": source["manifest_sha256"],
        },
        "counts": {"members": len(members)},
        "members": members,
    }
    panel_dir = PANEL_OUT / vintage
    panel_dir.mkdir(parents=True, exist_ok=True)
    panel_path = panel_dir / "panel.json"
    panel_path.write_text(json.dumps(panel, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8", newline="\n")

    vocabulary = {
        "schema_version": SCHEMA_VERSION,
        "layer": "country-name vocabulary for the pre-retrieval intent gate (KG01)",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": {"script": "scripts/build_country_vocabulary.py", "pycountry": version},
        "source": {"name": "ISO 3166-1", "version": version,
                   "why": "a country rule needs a list that is committed and reproducible; the donor panel's "
                          "membership is separate, in registry/donors/<vintage>/panel.json"},
        "excluded_from_refusal": [{"iso3": "NGA", "name": "Nigeria",
                                   "why": "every question in this project is about Nigeria; refusing the "
                                          "subject would refuse the corpus"}],
        "counts": {"countries": len(countries)},
        "countries": countries,
    }
    COUNTRIES_OUT.parent.mkdir(parents=True, exist_ok=True)
    COUNTRIES_OUT.write_text(json.dumps(vocabulary, indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8", newline="\n")

    print(f"panel      : {panel_path.relative_to(REPO_ROOT).as_posix()} — {len(members)} members")
    print(f"vocabulary : {COUNTRIES_OUT.relative_to(REPO_ROOT).as_posix()} — {len(countries)} countries "
          f"(ISO 3166-1 via pycountry {version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
