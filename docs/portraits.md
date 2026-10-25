# Portraits on the cover — sourcing, licence and file rules

The cover's five frames are **empty by design** until this procedure has been followed for a given president.
Nothing is downloaded by a build, a test or the site. A photograph is an asset with a licence, and this repo
already treats a licence as a decision (`docs/licences.md`, redistribution column), not a footnote.

**The rule this page exists to enforce:** a portrait may be committed only when there is a row for it in
`docs/licences.md` **and** an entry in `site/assets/presidents/manifest.json`, and the build fails if a supplied
file has either missing. A wrong or unlicensed portrait is a factual/legal error of the same weight as a wrong
number.

---

## 1. Sourcing hierarchy

Take the first category that yields an image whose licence permits redistribution:

| Rank | Source | Usable when | Attribution |
|---|---|---|---|
| 1 | **A file on Wikimedia Commons with a machine-readable free licence** (CC0, public domain, CC-BY, CC-BY-SA) | the file page states the licence and the author | the file page's required attribution string, verbatim, plus the licence URL |
| 2 | **An official government portrait** (State House / presidency / ministry press page) | the publisher's terms explicitly permit reuse, or the work is stated to be in the public domain | publisher and terms URL |
| 3 | **A free-licence photograph from another archive** (e.g. an agency releasing under CC) | the release states the licence and covers commercial reuse and modification | author, licence, licence URL |
| — | Anything else — press photos, agency images with "all rights reserved", campaign material, social-media images, AI reconstructions | **never** | — |

Non-negotiable exclusions, whatever the licence says:

- no campaign or party-branded imagery (a portrait on the cover of an analysis is not an endorsement);
- no image of a president in a private or family setting;
- no composite or "restored" face produced by upscaling or generation — a likeness that did not exist is worse
  than an empty frame;
- no image whose licence requires a share-alike term that the repository cannot satisfy for the site as a whole
  (CC-BY-SA is acceptable only for the image file itself, clearly separated and attributed, not for the page).

---

## 2. Where to look, per president

This table names the *place*, not a file, because a file's licence must be read at the moment of use and a URL
written here would be a claim nobody re-checked.

| Slug | President | Where to look first |
|---|---|---|
| `obasanjo` | Olusegun Obasanjo | Wikimedia Commons category for the person; official portraits from his 1999–2007 tenure |
| `yaradua` | Umaru Musa Yar'Adua | Wikimedia Commons; 2007–2010 official portrait |
| `jonathan` | Goodluck Jonathan | Wikimedia Commons; 2010–2015 official portrait |
| `buhari` | Muhammadu Buhari | Wikimedia Commons; 2015–2023 official portrait |
| `tinubu` | Bola Ahmed Tinubu | Wikimedia Commons; the current official portrait (2023–) |

For each candidate, record on the file page: the **author**, the **licence name and version**, the **licence URL**,
the **source URL**, the **retrieval date**, and — where the file page states it — the **original** it was derived
from. If any of those six is missing, the candidate is not usable; move to the next.

---

## 3. File specification

| Property | Value | Why |
|---|---|---|
| Format | PNG or JPEG (JPEG for photographs) | the build copies the file; it does not transcode |
| Crop | 3:4 portrait, head and shoulders, eyes on the upper third | the frames are 3:4; a mismatch would letterbox a face |
| Size | 600 × 750 px (1200 × 1500 acceptable) | sharp on retina at the rendered size, small enough for a static page |
| Colour | sRGB, JPEG quality ≈ 85 | consistent across five images |
| Weight | ≤ 200 KB each | the cover is the first page a reader loads |
| Metadata | EXIF stripped except a copyright field if the licence requires it | no camera GPS or software strings on a public page |
| Path | `site/assets/presidents/<slug>.jpg` (or `.png`) | one file per slug, no versions in the name |
| Alteration | crop and resize only | anything else changes the likeness |

---

## 4. The manifest

`site/assets/presidents/manifest.json` is the machine-readable half of the licence register. One entry per
**supplied** portrait:

```json
{
  "schema_version": "0.1.0",
  "portraits": [
    {
      "slug": "obasanjo",
      "file": "site/assets/presidents/obasanjo.jpg",
      "sha256": "<64 hex chars>",
      "source_url": "…",
      "author": "…",
      "licence": "CC BY 4.0",
      "licence_url": "…",
      "retrieved": "2026-10-25",
      "crop_note": "cropped to 3:4, resized to 600x750, EXIF removed",
      "attribution_text": "…as the licence requires, verbatim…",
      "reviewer": "<who checked the licence against the file page>",
      "decided_on": "2026-10-25"
    }
  ]
}
```

**Invariants the build and `tests/verify_site.py` enforce:**

1. Every `file` exists, and its `sha256` matches the manifest (a swapped image fails the build).
2. Every supplied portrait has a matching row in `docs/licences.md` whose `redistribution permitted` cell is `y`.
3. Every `slug` matches an administration's `slug` in `registry/reference/administrations.json`.
4. `attribution_text` appears in the site footer of any page that shows the portrait.
5. `portrait_status` in the administrations reference is `supplied` **iff** the manifest has an entry.

A portrait that breaks any of those is a build failure, not a warning — the same treatment the registry gives a
card whose vintage disagrees with its index.

---

## 5. The licence-register row, verbatim

Add to `docs/licences.md`, in its existing column order:

| Field | Content |
|---|---|
| source | `Wikimedia Commons — <file title>` (or the official publisher) |
| access path | direct file download, one-off, not automated |
| licence / terms | `CC BY 4.0` (or as stated), with the licence URL |
| redistribution permitted | `y` |
| attribution text | the string the licence requires, verbatim |
| notes | date retrieved, reviewer, and any crop applied |

---

## 6. What ships before the images

Until a portrait is supplied, the build writes the **placeholder frame**: a 3:4 panel in the page's own palette
carrying the president's initials, the text **"image not supplied"**, and no invented likeness. The placeholder
is generated by `site/build.py`, so it is identical on every machine, and it disappears the moment a supplied
file and its two records exist.

This is deliberate: an empty frame that says so is a stated absence, which is how this project handles every
other missing thing (a card without a number names its reason; a series with no observation is shaded and
labelled). A stock photograph would be the portrait equivalent of a typed coefficient.

---

## 7. Decision needed from the requester

The build does not need the images to proceed — five placeholder frames are a complete cover. To go from
placeholder to photograph, the requester needs to answer one question per president: **may this file be
redistributed?** The answer must come from the licence on the file page, not from the fact that the person is a
public figure. Until then, `portrait_status` stays `not_supplied` and the page says so.
