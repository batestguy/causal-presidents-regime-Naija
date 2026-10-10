# Licence register — data sources

One row per source. The governing rule (design spec §10): **publish code and derived
aggregates; never commit restricted raw extracts.** A stranger with their own credentials must be
able to reproduce every aggregate.

`Redistribute?` answers: may the raw payload be committed to the public repo?
`Verified` reflects the empirical probe of 2026-10-10 (see `decisions.md` §Access findings).

| Source | Access | Licence / terms | Redistribute raw? | Verified | Notes |
|---|---|---|---|---|---|
| World Bank Indicators | keyless API | CC-BY 4.0 | **Yes**, with attribution | ✅ 200 | Attribution required on derived figures |
| IMF DataMapper | keyless API | IMF terms; attribution required | Likely yes — **confirm** | ⚠️ 403 to scripts, 200 via relay | Blocks non-browser clients |
| FRED (Brent `DCOILBRENTEU`) | free key | FRED terms; series may carry upstream restrictions | **Confirm before publishing** | 🔑 400 without key | Brent originates with the US EIA — check the EIA terms too |
| NBS (GDP, CPI, unemployment, state IGR, FAAC reports) | manual download | Nigerian government publication | Public documents; cite NBS | ✅ 200 | No API; PDF/HTML parsing |
| CBN (FX, reserves) | manual download | Nigerian government publication | Public documents; cite CBN | ✅ 200 | No API |
| ~~OAGF / Open Treasury (FAAC per state)~~ | ~~open portal~~ | — | — | ❌ **unreachable** | Source substitution required (see decision X-01) |
| DHS / NDHS | registration | DHS terms of use | **No** — republication prohibited | — not probed (account) | Aggregate indicators only; no cluster/microdata |
| MICS (UNICEF) | free | UNICEF terms | Confirm per dataset | — not probed | |
| UN IGME | free | UN terms; **modelled** estimates | Likely yes — confirm | — not probed | Modelled ≠ observed; label as such |
| UNESCO UIS | free API | CC-BY-SA style; attribution | Likely yes — confirm | ⚠️ 400 (endpoint moved) | Verify current endpoint first |
| NEMIS / NEDI | manual portal | Nigerian government publication | Confirm | — not probed | Patchy coverage |
| ACLED | registration + key | **ACLED terms of use** | **No** — redistribution restricted; free tier has a 12-month embargo | ❌ host no longer resolves | **Confirm the new API host before building any client** |
| UCDP GED | free token | CC-BY 4.0 | Yes, with attribution | 🔑 401 without token | Distinct conflict definition from ACLED — do not splice the two silently |
| Nigeria DHIS2 (HMIS) | institutional credentials | Ministry of Health / DHIS2 terms | **Confirm** | ⚠️ tenant unverified | Do not design a model on it until access is confirmed |

## Open licensing questions to resolve before publishing anything

1. **FRED/Brent** — does the EIA upstream licence permit redistribution of the series we store?
2. **IMF** — redistribution terms for DataMapper series.
3. **UNIGME and MICS** — modelled estimates: redistribution and required labelling.
4. **DHIS2** — whether any extracted aggregate may be published at state level.
5. **ACLED** — the current licence text, plus whether derived counts are themselves restricted.

Until each is resolved, the default is the safe one: **derived aggregates only, raw never committed.**
