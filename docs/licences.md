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
| FRED (Brent `DCOILBRENTEU`) | free key — **key registered 2026-10-11** | FRED terms; series may carry upstream restrictions | **Confirm before publishing** | ✅ 200 with key (was 🔑 400) | Brent originates with the US EIA — check the EIA terms too. The key is stored in a gitignored `.env` and redacted from every manifest (I-07) |
| NBS (GDP, CPI, unemployment, state IGR, FAAC reports) | manual download | Nigerian government publication | Public documents; cite NBS | ✅ 200 | No API; PDF/HTML parsing. **FAAC republication landed 2026-10-16** (91 monthly XLSX reports, 2016-12 → 2024-07) |
| CBN (FX, reserves) | manual download | Nigerian government publication | Public documents; cite CBN | ✅ 200 | No API |
| OAGF — Office of the Accountant General of the Federation (FAAC per state) | free, no key | Nigerian government publication | Public documents; cite OAGF | ✅ **reachable 2026-10-16** — 83 monthly PDFs crawled (2019-04 → 2026-06) | **Corrected**: the Open Treasury portal is unreachable, but the OAGF's own site publishes the monthly workbooks under `/wp-content/uploads/`. This is D1's primary source, so no substitution was needed. The payloads are the publishers' own documents and are cited rather than redistributed wholesale |
| DHS / NDHS | registration | DHS terms of use | **No** — republication prohibited | — not probed (account) | Aggregate indicators only; no cluster/microdata |
| MICS (UNICEF) | free | UNICEF terms | Confirm per dataset | — not probed | |
| UN IGME | free | UN terms; **modelled** estimates | Likely yes — confirm | — not probed | Modelled ≠ observed; label as such |
| UNESCO UIS | free API | CC-BY-SA style; attribution | Likely yes — confirm | ⚠️ 400 (endpoint moved) | Verify current endpoint first |
| NEMIS / NEDI | manual portal | Nigerian government publication | Confirm | — not probed | Patchy coverage |
| ACLED | registration + key | **ACLED terms of use** | **No** — redistribution restricted; free tier has a 12-month embargo | ❌ host no longer resolves | **Confirm the new API host before building any client** |
| UCDP GED | **bulk archive: keyless** (the API alone needs a token) | CC-BY 4.0 | **Yes**, with attribution | ✅ **200, 29,307,888 bytes, no credential (2026-10-17)**; API 401 on 25.1/24.1/23.1 | **Landed 2026-10-17** as the state-attributed security outcome (C-45). `https://ucdp.uu.se/downloads/ged/ged251-csv.zip`; attribution is carried on the manifest and in `docs/estimates.md`. Distinct conflict definition from ACLED — do not splice the two silently |
| Nigeria DHIS2 (HMIS) | institutional credentials | Ministry of Health / DHIS2 terms | **Confirm** | ⚠️ tenant unverified | Do not design a model on it until access is confirmed |

## Open licensing questions to resolve before publishing anything

1. **FRED/Brent** — does the EIA upstream licence permit redistribution of the series we store?
2. **IMF** — redistribution terms for DataMapper series.
3. **UNIGME and MICS** — modelled estimates: redistribution and required labelling.
4. **DHIS2** — whether any extracted aggregate may be published at state level.
5. **ACLED** — the current licence text, plus whether derived counts are themselves restricted. **No
   longer blocking**: the security domain is answered from UCDP GED, which is CC-BY and keyless to
   acquire, so ACLED's terms can stay unresolved without a hole in the design (C-45).

Until each is resolved, the default is the safe one: **derived aggregates only, raw never committed.**
The UCDP case is the interesting one, because it is a *resolved* question rather than an exception: the
licence permits redistribution with attribution, the attribution is recorded on the manifest and cited
on the derived aggregate, and the raw archive is still not committed — not because it is forbidden but
because 29 MB of every-country events is not needed to reproduce a Nigeria state-month series.
