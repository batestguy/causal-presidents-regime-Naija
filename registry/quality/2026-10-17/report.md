# Vintage quality report — 2026-10-17

Stage 3 gate results for every series in the raw layer. Generated 2026-10-18T08:05:44+00:00 by `ingestion/flows/check_quality.py` from `analysis/specs/quality.yml`.

**Study window:** 1999-01-01 → open. Gates for gaps and spikes are evaluated *inside* this window only.

**Thresholds:** gap_max_months=3, spike_pct=50.0, spike_points=10.0, revision_tolerance_pct=1.0, revision_tolerance_abs=1e-06.

**Sources:** `faac` @ 2026-10-16-correction, `fred` @ 2026-10-11, `ucdp` @ 2026-10-17, `worldbank` @ 2026-10-11, `worldbank_donors` @ 2026-10-11.

**Series gated:** 242 — ok 60, flagged 182, empty 0.

## Flagged series

| Source | Metric | Scope | Grain | Gate | Detail |
|---|---|---|---|---|---|
| fred | `oil` | — | monthly | spike | 2020-04 → 2020-05: **+59.9%** — accepted_as_real_event |
| worldbank | `measles_imm` | NGA | annual | spike | 2007 → 2008: **+12.00 points** — **UNADJUDICATED** |
| worldbank | `measles_imm` | NGA | annual | spike | 2008 → 2009: **+11.00 points** — **UNADJUDICATED** |
| worldbank | `measles_imm` | NGA | annual | spike | 2011 → 2012: **-12.00 points** — **UNADJUDICATED** |
| worldbank | `cpi_yoy` | NGA | annual | spike | 2000 → 2001: **+11.94 points** — **UNADJUDICATED** |
| worldbank | `cpi_yoy` | NGA | annual | spike | 2024 → 2025: **-10.23 points** — explained_by_definition_break |
| worldbank | `primary_completion` | NGA | annual | gap | longest hole **36 months** across 1 run(s) |
| worldbank | `primary_completion` | NGA | annual | spike | 2006 → 2007: **-10.19 points** — **UNADJUDICATED** |
| worldbank | `primary_completion` | NGA | annual | spike | 2007 → 2008: **-10.45 points** — **UNADJUDICATED** |
| worldbank | `ner_primary` | NGA | annual | gap | longest hole **36 months** across 1 run(s) |
| worldbank | `adult_literacy` | NGA | annual | gap | longest hole **108 months** across 4 run(s) |
| worldbank | `literacy_youth` | NGA | annual | gap | longest hole **48 months** across 6 run(s) |
| worldbank | `homicides` | NGA | annual | gap | longest hole **36 months** across 2 run(s) |
| worldbank | `skilled_birth` | NGA | annual | gap | longest hole **48 months** across 6 run(s) |
| worldbank | `immun_penta3` | NGA | annual | spike | 2007 → 2008: **+11.00 points** — **UNADJUDICATED** |
| worldbank | `immun_penta3` | NGA | annual | spike | 2011 → 2012: **-17.00 points** — **UNADJUDICATED** |
| worldbank | `immun_penta3` | NGA | annual | spike | 2015 → 2016: **+11.00 points** — **UNADJUDICATED** |
| worldbank | `fx` | NGA | annual | spike | 2022 → 2023: **+51.5%** — explained_by_definition_break |
| worldbank | `fx` | NGA | annual | spike | 2023 → 2024: **+129.2%** — explained_by_definition_break |
| worldbank | `donor_oda` | NGA | annual | spike | 2001 → 2002: **+78.5%** — **UNADJUDICATED** |
| worldbank | `donor_oda` | NGA | annual | spike | 2003 → 2004: **+86.8%** — **UNADJUDICATED** |
| worldbank | `donor_oda` | NGA | annual | spike | 2004 → 2005: **+1006.1%** — accounting_artefact |
| worldbank | `donor_oda` | NGA | annual | spike | 2005 → 2006: **+78.6%** — accounting_artefact |
| worldbank | `donor_oda` | NGA | annual | spike | 2006 → 2007: **-82.9%** — accounting_artefact |
| worldbank | `donor_oda` | NGA | annual | spike | 2010 → 2011: **+68.9%** — **UNADJUDICATED** |
| worldbank | `oil_rents` | NGA | annual | spike | 1999 → 2000: **+11.94 points** — **UNADJUDICATED** |
| worldbank_donors | `gdp_growth` | AO | annual | spike | 2002 → 2003: **-10.18 points** — **UNADJUDICATED** |
| worldbank_donors | `gdp_growth` | CI | annual | spike | 2010 → 2011: **-12.22 points** — **UNADJUDICATED** |
| worldbank_donors | `gdp_growth` | CI | annual | spike | 2011 → 2012: **+12.99 points** — **UNADJUDICATED** |
| worldbank_donors | `gdp_growth` | CO | annual | spike | 2019 → 2020: **-10.37 points** — **UNADJUDICATED** |
| worldbank_donors | `gdp_growth` | CO | annual | spike | 2020 → 2021: **+17.99 points** — **UNADJUDICATED** |
| worldbank_donors | `gdp_growth` | EC | annual | spike | 2020 → 2021: **+18.67 points** — **UNADJUDICATED** |
| worldbank_donors | `gdp_growth` | VE | annual | spike | 2001 → 2002: **-12.14 points** — **UNADJUDICATED** |
| worldbank_donors | `gdp_growth` | VE | annual | spike | 2003 → 2004: **+25.96 points** — **UNADJUDICATED** |
| worldbank_donors | `gdp_growth` | VE | annual | spike | 2015 → 2016: **-10.93 points** — **UNADJUDICATED** |
| worldbank_donors | `gdp_growth` | VE | annual | spike | 2020 → 2021: **+30.45 points** — **UNADJUDICATED** |
| worldbank_donors | `gdp_growth` | ZA | annual | spike | 2020 → 2021: **+11.03 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | AO | annual | spike | 1999 → 2000: **+76.80 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | AO | annual | spike | 2000 → 2001: **-172.44 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | AO | annual | spike | 2001 → 2002: **-43.66 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | AO | annual | spike | 2002 → 2003: **-10.67 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | AO | annual | spike | 2003 → 2004: **-54.68 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | AO | annual | spike | 2004 → 2005: **-20.59 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | AO | annual | spike | 2015 → 2016: **+21.34 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | AO | annual | spike | 2017 → 2018: **-10.22 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | AO | annual | spike | 2023 → 2024: **+14.60 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | EC | annual | spike | 1999 → 2000: **+43.85 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | EC | annual | spike | 2000 → 2001: **-58.42 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | EC | annual | spike | 2001 → 2002: **-25.19 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | GH | annual | spike | 1999 → 2000: **+35.38 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | GH | annual | spike | 2001 → 2002: **-32.15 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | GH | annual | spike | 2002 → 2003: **+20.41 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | GH | annual | spike | 2003 → 2004: **-11.73 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | GH | annual | spike | 2021 → 2022: **+21.28 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | GH | annual | spike | 2023 → 2024: **-15.26 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | ID | annual | spike | 1999 → 2000: **-16.79 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | KE | annual | spike | 2007 → 2008: **+16.48 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | KE | annual | spike | 2008 → 2009: **-17.01 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | KE | annual | spike | 2010 → 2011: **+10.06 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | VE | annual | spike | 2012 → 2013: **+19.57 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | VE | annual | spike | 2013 → 2014: **+21.53 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | VE | annual | spike | 2014 → 2015: **+59.57 points** — **UNADJUDICATED** |
| worldbank_donors | `cpi_yoy` | VE | annual | spike | 2015 → 2016: **+133.21 points** — **UNADJUDICATED** |
| worldbank_donors | `oil_rents` | AO | annual | spike | 1999 → 2000: **+18.99 points** — **UNADJUDICATED** |
| worldbank_donors | `oil_rents` | AO | annual | spike | 2000 → 2001: **-14.92 points** — **UNADJUDICATED** |
| worldbank_donors | `oil_rents` | AO | annual | spike | 2001 → 2002: **-10.83 points** — **UNADJUDICATED** |
| worldbank_donors | `oil_rents` | AO | annual | spike | 2008 → 2009: **-22.32 points** — **UNADJUDICATED** |
| worldbank_donors | `oil_rents` | GA | annual | spike | 1999 → 2000: **+21.66 points** — **UNADJUDICATED** |
| worldbank_donors | `oil_rents` | GA | annual | spike | 2000 → 2001: **-15.13 points** — **UNADJUDICATED** |
| worldbank_donors | `oil_rents` | GA | annual | spike | 2008 → 2009: **-12.61 points** — **UNADJUDICATED** |
| worldbank_donors | `oil_rents` | GA | annual | spike | 2014 → 2015: **-12.18 points** — **UNADJUDICATED** |
| worldbank_donors | `oil_rents` | VE | annual | spike | 2008 → 2009: **-12.72 points** — **UNADJUDICATED** |
| worldbank_donors | `oil_rents` | VE | annual | spike | 2010 → 2011: **+11.45 points** — **UNADJUDICATED** |

### Document sources, aggregated by period

| Source | Metric | Period | Gate | Series flagged | Largest move |
|---|---|---|---|---|---|
| faac | `faac_gross_total` | 2017-01 | spike | 1 of 37 | 92.6% |
| faac | `faac_gross_total` | 2017-07 | spike | 37 of 37 | 86.1% |
| faac | `faac_gross_total` | 2017-09 | spike | 2 of 37 | 62.8% |
| faac | `faac_gross_total` | 2020-08 | spike | 3 of 37 | 66.2% |
| faac | `faac_gross_total` | 2021-07 | spike | 37 of 37 | 133.5% |
| faac | `faac_gross_total` | 2021-08 | spike | 1 of 37 | 83.2% |
| faac | `faac_gross_total` | 2021-09 | spike | 1 of 37 | 54.2% |
| faac | `faac_gross_total` | 2021-10 | spike | 4 of 37 | 76.6% |
| faac | `faac_gross_total` | 2021-11 | spike | 4 of 37 | 56.5% |
| faac | `faac_gross_total` | 2021-12 | spike | 5 of 37 | 110.1% |
| faac | `faac_gross_total` | 2022-02 | spike | 28 of 37 | 50.7% |
| faac | `faac_gross_total` | 2022-04 | spike | 5 of 37 | 70.0% |
| faac | `faac_gross_total` | 2022-07 | spike | 32 of 37 | 82.0% |
| faac | `faac_gross_total` | 2022-10 | spike | 2 of 37 | 59.8% |
| faac | `faac_gross_total` | 2022-12 | spike | 36 of 37 | 98.3% |
| faac | `faac_gross_total` | 2023-02 | spike | 1 of 37 | 50.9% |
| faac | `faac_gross_total` | 2023-05 | spike | 3 of 37 | 95.3% |
| faac | `faac_gross_total` | 2023-06 | spike | 28 of 37 | 54.4% |
| faac | `faac_gross_total` | 2023-10 | spike | 5 of 37 | 89.3% |
| faac | `faac_gross_total` | 2023-11 | spike | 4 of 37 | 54.7% |
| faac | `faac_gross_total` | 2023-12 | spike | 3 of 37 | 81.9% |
| faac | `faac_gross_total` | 2024-02 | spike | 1 of 37 | 61.0% |
| faac | `faac_gross_total` | 2024-03 | spike | 30 of 37 | 96.6% |
| faac | `faac_gross_total` | 2024-04 | spike | 30 of 37 | 1722.2% |
| faac | `faac_gross_total` | 2024-11 | spike | 1 of 37 | 50.3% |
| faac | `faac_gross_total` | 2024-12 | spike | 37 of 37 | 606.1% |
| faac | `faac_gross_total` | 2025-01 | spike | 1 of 37 | 51.5% |
| faac | `faac_gross_total` | 2025-02 | spike | 35 of 37 | 117.3% |
| ucdp | `fatalities` | 1999-02 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 1999-03 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 1999-04 | spike | 2 of 39 | 10400.0% |
| ucdp | `fatalities` | 1999-05 | spike | 3 of 39 | 102.9% |
| ucdp | `fatalities` | 1999-06 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 1999-07 | spike | 2 of 39 | 913.0% |
| ucdp | `fatalities` | 1999-10 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 1999-11 | spike | 2 of 39 | 10000.0% |
| ucdp | `fatalities` | 2000-02 | spike | 4 of 39 | 30733.3% |
| ucdp | `fatalities` | 2000-03 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2000-06 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2000-07 | spike | 2 of 39 | 3200.0% |
| ucdp | `fatalities` | 2001-05 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2001-06 | spike | 2 of 39 | 455.6% |
| ucdp | `fatalities` | 2001-07 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2001-10 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities` | 2001-11 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities` | 2001-12 | spike | 6 of 39 | 1500.0% |
| ucdp | `fatalities` | 2002-02 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2002-06 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2002-07 | spike | 2 of 39 | 491.7% |
| ucdp | `fatalities` | 2002-08 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2002-09 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2002-10 | spike | 2 of 39 | 1200.0% |
| ucdp | `fatalities` | 2002-11 | spike | 2 of 39 | 750.0% |
| ucdp | `fatalities` | 2002-12 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2003-01 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2003-02 | spike | 3 of 39 | 2080.0% |
| ucdp | `fatalities` | 2003-03 | spike | 5 of 39 | 600.0% |
| ucdp | `fatalities` | 2003-04 | spike | 5 of 39 | 1700.0% |
| ucdp | `fatalities` | 2003-05 | spike | 11 of 39 | 100.0% |
| ucdp | `fatalities` | 2003-06 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2003-07 | spike | 2 of 39 | 380.0% |
| ucdp | `fatalities` | 2003-08 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2003-11 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2003-12 | spike | 2 of 39 | 2000.0% |
| ucdp | `fatalities` | 2004-01 | spike | 2 of 39 | 2000.0% |
| ucdp | `fatalities` | 2004-02 | spike | 4 of 39 | 237.3% |
| ucdp | `fatalities` | 2004-03 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2004-04 | spike | 4 of 39 | 1057.1% |
| ucdp | `fatalities` | 2004-05 | spike | 4 of 39 | 837.0% |
| ucdp | `fatalities` | 2004-06 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities` | 2004-07 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities` | 2004-08 | spike | 2 of 39 | 326.7% |
| ucdp | `fatalities` | 2004-09 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2004-10 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities` | 2004-11 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities` | 2005-02 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2005-03 | spike | 2 of 39 | 700.0% |
| ucdp | `fatalities` | 2005-04 | spike | 2 of 39 | 1425.0% |
| ucdp | `fatalities` | 2005-07 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2006-01 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities` | 2006-02 | spike | 2 of 39 | 1410.0% |
| ucdp | `fatalities` | 2006-05 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2006-10 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities` | 2007-02 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2007-03 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities` | 2007-04 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2007-05 | spike | 2 of 39 | 200.0% |
| ucdp | `fatalities` | 2007-07 | spike | 2 of 39 | 2150.0% |
| ucdp | `fatalities` | 2007-08 | spike | 2 of 39 | 86.7% |
| ucdp | `fatalities` | 2007-09 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities` | 2007-10 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities` | 2007-11 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2007-12 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2008-01 | spike | 2 of 39 | 233.3% |
| ucdp | `fatalities` | 2008-02 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2008-03 | spike | 1 of 39 | 66.7% |
| ucdp | `fatalities` | 2008-04 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2008-05 | spike | 3 of 39 | 142.9% |
| ucdp | `fatalities` | 2008-06 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2008-07 | spike | 1 of 39 | 700.0% |
| ucdp | `fatalities` | 2008-08 | spike | 4 of 39 | 200.0% |
| ucdp | `fatalities` | 2008-09 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2008-12 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2009-01 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2009-02 | spike | 2 of 39 | 3600.0% |
| ucdp | `fatalities` | 2009-03 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2009-04 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2009-05 | spike | 2 of 39 | 250.0% |
| ucdp | `fatalities` | 2009-06 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2009-07 | spike | 2 of 39 | 42200.0% |
| ucdp | `fatalities` | 2010-01 | spike | 2 of 39 | 1569.7% |
| ucdp | `fatalities` | 2010-02 | spike | 2 of 39 | 99.3% |
| ucdp | `fatalities` | 2010-03 | spike | 4 of 39 | 4325.0% |
| ucdp | `fatalities` | 2010-04 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2010-05 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2010-06 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2010-07 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2010-08 | spike | 1 of 39 | 88.9% |
| ucdp | `fatalities` | 2010-09 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2010-10 | spike | 2 of 39 | 327.3% |
| ucdp | `fatalities` | 2010-11 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2010-12 | spike | 2 of 39 | 9700.0% |
| ucdp | `fatalities` | 2011-01 | spike | 1 of 39 | 63.6% |
| ucdp | `fatalities` | 2011-02 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2011-03 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2011-04 | spike | 7 of 39 | 2623.3% |
| ucdp | `fatalities` | 2011-05 | spike | 16 of 39 | 100.0% |
| ucdp | `fatalities` | 2011-06 | spike | 5 of 39 | 1250.0% |
| ucdp | `fatalities` | 2011-07 | spike | 5 of 39 | 477.8% |
| ucdp | `fatalities` | 2011-08 | spike | 3 of 39 | 160.0% |
| ucdp | `fatalities` | 2011-09 | spike | 7 of 39 | 400.0% |
| ucdp | `fatalities` | 2011-10 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2011-11 | spike | 7 of 39 | 1038.9% |
| ucdp | `fatalities` | 2011-12 | spike | 7 of 39 | 150.0% |
| ucdp | `fatalities` | 2012-01 | spike | 11 of 39 | 2614.3% |
| ucdp | `fatalities` | 2012-02 | spike | 9 of 39 | 691.4% |
| ucdp | `fatalities` | 2012-03 | spike | 11 of 39 | 1000.0% |
| ucdp | `fatalities` | 2012-04 | spike | 8 of 39 | 422.2% |
| ucdp | `fatalities` | 2012-05 | spike | 7 of 39 | 1266.7% |
| ucdp | `fatalities` | 2012-06 | spike | 11 of 39 | 2500.0% |
| ucdp | `fatalities` | 2012-07 | spike | 10 of 39 | 487.5% |
| ucdp | `fatalities` | 2012-08 | spike | 9 of 39 | 466.7% |
| ucdp | `fatalities` | 2012-09 | spike | 7 of 39 | 211.8% |
| ucdp | `fatalities` | 2012-10 | spike | 7 of 39 | 3000.0% |
| ucdp | `fatalities` | 2012-11 | spike | 5 of 39 | 650.0% |
| ucdp | `fatalities` | 2012-12 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2013-01 | spike | 5 of 39 | 170.8% |
| ucdp | `fatalities` | 2013-02 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2013-03 | spike | 5 of 39 | 650.0% |
| ucdp | `fatalities` | 2013-04 | spike | 9 of 39 | 1050.0% |
| ucdp | `fatalities` | 2013-05 | spike | 7 of 39 | 550.0% |
| ucdp | `fatalities` | 2013-06 | spike | 11 of 39 | 2000.0% |
| ucdp | `fatalities` | 2013-07 | spike | 5 of 39 | 6300.0% |
| ucdp | `fatalities` | 2013-08 | spike | 9 of 39 | 300.0% |
| ucdp | `fatalities` | 2013-09 | spike | 4 of 39 | 5200.0% |
| ucdp | `fatalities` | 2013-10 | spike | 7 of 39 | 100.0% |
| ucdp | `fatalities` | 2013-11 | spike | 6 of 39 | 800.0% |
| ucdp | `fatalities` | 2013-12 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2014-01 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2014-02 | spike | 8 of 39 | 334.8% |
| ucdp | `fatalities` | 2014-03 | spike | 6 of 39 | 2450.0% |
| ucdp | `fatalities` | 2014-04 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2014-05 | spike | 12 of 39 | 1375.0% |
| ucdp | `fatalities` | 2014-06 | spike | 7 of 39 | 533.3% |
| ucdp | `fatalities` | 2014-07 | spike | 10 of 39 | 100.0% |
| ucdp | `fatalities` | 2014-08 | spike | 9 of 39 | 2366.7% |
| ucdp | `fatalities` | 2014-09 | spike | 3 of 39 | 300.0% |
| ucdp | `fatalities` | 2014-10 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2014-11 | spike | 9 of 39 | 3066.7% |
| ucdp | `fatalities` | 2014-12 | spike | 7 of 39 | 680.0% |
| ucdp | `fatalities` | 2015-01 | spike | 9 of 39 | 170.0% |
| ucdp | `fatalities` | 2015-02 | spike | 9 of 39 | 1400.0% |
| ucdp | `fatalities` | 2015-03 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2015-04 | spike | 12 of 39 | 100.0% |
| ucdp | `fatalities` | 2015-05 | spike | 9 of 39 | 611.1% |
| ucdp | `fatalities` | 2015-06 | spike | 9 of 39 | 588.9% |
| ucdp | `fatalities` | 2015-07 | spike | 5 of 39 | 537.5% |
| ucdp | `fatalities` | 2015-08 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2015-09 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities` | 2015-10 | spike | 7 of 39 | 560.0% |
| ucdp | `fatalities` | 2015-11 | spike | 5 of 39 | 200.0% |
| ucdp | `fatalities` | 2015-12 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities` | 2016-01 | spike | 7 of 39 | 3100.0% |
| ucdp | `fatalities` | 2016-02 | spike | 14 of 39 | 4166.7% |
| ucdp | `fatalities` | 2016-03 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities` | 2016-04 | spike | 7 of 39 | 900.0% |
| ucdp | `fatalities` | 2016-05 | spike | 4 of 39 | 1450.0% |
| ucdp | `fatalities` | 2016-06 | spike | 11 of 39 | 606.7% |
| ucdp | `fatalities` | 2016-07 | spike | 7 of 39 | 100.0% |
| ucdp | `fatalities` | 2016-08 | spike | 6 of 39 | 1900.0% |
| ucdp | `fatalities` | 2016-09 | spike | 7 of 39 | 100.0% |
| ucdp | `fatalities` | 2016-10 | spike | 6 of 39 | 633.3% |
| ucdp | `fatalities` | 2016-11 | spike | 3 of 39 | 131.6% |
| ucdp | `fatalities` | 2016-12 | spike | 4 of 39 | 4400.0% |
| ucdp | `fatalities` | 2017-01 | spike | 7 of 39 | 313.7% |
| ucdp | `fatalities` | 2017-02 | spike | 6 of 39 | 160.0% |
| ucdp | `fatalities` | 2017-03 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2017-04 | spike | 4 of 39 | 416.7% |
| ucdp | `fatalities` | 2017-05 | spike | 5 of 39 | 300.0% |
| ucdp | `fatalities` | 2017-06 | spike | 8 of 39 | 1181.8% |
| ucdp | `fatalities` | 2017-07 | spike | 7 of 39 | 100.0% |
| ucdp | `fatalities` | 2017-08 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities` | 2017-09 | spike | 4 of 39 | 2800.0% |
| ucdp | `fatalities` | 2017-10 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities` | 2017-11 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2017-12 | spike | 3 of 39 | 700.0% |
| ucdp | `fatalities` | 2018-01 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2018-02 | spike | 8 of 39 | 100.0% |
| ucdp | `fatalities` | 2018-03 | spike | 9 of 39 | 2633.3% |
| ucdp | `fatalities` | 2018-04 | spike | 6 of 39 | 341.2% |
| ucdp | `fatalities` | 2018-05 | spike | 7 of 39 | 1283.3% |
| ucdp | `fatalities` | 2018-06 | spike | 7 of 39 | 6700.0% |
| ucdp | `fatalities` | 2018-07 | spike | 7 of 39 | 100.0% |
| ucdp | `fatalities` | 2018-08 | spike | 7 of 39 | 100.0% |
| ucdp | `fatalities` | 2018-09 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2018-10 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities` | 2018-11 | spike | 7 of 39 | 100.0% |
| ucdp | `fatalities` | 2018-12 | spike | 4 of 39 | 816.7% |
| ucdp | `fatalities` | 2019-01 | spike | 7 of 39 | 750.0% |
| ucdp | `fatalities` | 2019-02 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities` | 2019-03 | spike | 11 of 39 | 100.0% |
| ucdp | `fatalities` | 2019-04 | spike | 10 of 39 | 500.0% |
| ucdp | `fatalities` | 2019-05 | spike | 8 of 39 | 100.0% |
| ucdp | `fatalities` | 2019-06 | spike | 8 of 39 | 160.0% |
| ucdp | `fatalities` | 2019-07 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2019-08 | spike | 6 of 39 | 300.0% |
| ucdp | `fatalities` | 2019-09 | spike | 9 of 39 | 361.5% |
| ucdp | `fatalities` | 2019-10 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities` | 2019-11 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2019-12 | spike | 2 of 39 | 1450.0% |
| ucdp | `fatalities` | 2020-01 | spike | 9 of 39 | 150.0% |
| ucdp | `fatalities` | 2020-02 | spike | 9 of 39 | 100.0% |
| ucdp | `fatalities` | 2020-03 | spike | 9 of 39 | 2000.0% |
| ucdp | `fatalities` | 2020-04 | spike | 6 of 39 | 791.7% |
| ucdp | `fatalities` | 2020-05 | spike | 9 of 39 | 281.6% |
| ucdp | `fatalities` | 2020-06 | spike | 8 of 39 | 100.0% |
| ucdp | `fatalities` | 2020-07 | spike | 7 of 39 | 677.8% |
| ucdp | `fatalities` | 2020-08 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities` | 2020-09 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2020-10 | spike | 6 of 39 | 1700.0% |
| ucdp | `fatalities` | 2020-11 | spike | 8 of 39 | 100.0% |
| ucdp | `fatalities` | 2020-12 | spike | 7 of 39 | 100.0% |
| ucdp | `fatalities` | 2021-01 | spike | 8 of 39 | 200.0% |
| ucdp | `fatalities` | 2021-02 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities` | 2021-03 | spike | 7 of 39 | 100.0% |
| ucdp | `fatalities` | 2021-04 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities` | 2021-05 | spike | 15 of 39 | 500.0% |
| ucdp | `fatalities` | 2021-06 | spike | 12 of 39 | 1300.0% |
| ucdp | `fatalities` | 2021-07 | spike | 10 of 39 | 100.0% |
| ucdp | `fatalities` | 2021-08 | spike | 10 of 39 | 1060.0% |
| ucdp | `fatalities` | 2021-09 | spike | 3 of 39 | 118.3% |
| ucdp | `fatalities` | 2021-10 | spike | 7 of 39 | 200.0% |
| ucdp | `fatalities` | 2021-11 | spike | 8 of 39 | 100.0% |
| ucdp | `fatalities` | 2021-12 | spike | 8 of 39 | 274.5% |
| ucdp | `fatalities` | 2022-01 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2022-02 | spike | 10 of 39 | 1300.0% |
| ucdp | `fatalities` | 2022-03 | spike | 8 of 39 | 175.0% |
| ucdp | `fatalities` | 2022-04 | spike | 6 of 39 | 300.0% |
| ucdp | `fatalities` | 2022-05 | spike | 12 of 39 | 200.0% |
| ucdp | `fatalities` | 2022-06 | spike | 12 of 39 | 1150.0% |
| ucdp | `fatalities` | 2022-07 | spike | 14 of 39 | 100.0% |
| ucdp | `fatalities` | 2022-08 | spike | 7 of 39 | 214.3% |
| ucdp | `fatalities` | 2022-09 | spike | 7 of 39 | 145.7% |
| ucdp | `fatalities` | 2022-10 | spike | 10 of 39 | 333.3% |
| ucdp | `fatalities` | 2022-11 | spike | 9 of 39 | 100.0% |
| ucdp | `fatalities` | 2022-12 | spike | 7 of 39 | 100.0% |
| ucdp | `fatalities` | 2023-01 | spike | 9 of 39 | 433.3% |
| ucdp | `fatalities` | 2023-02 | spike | 5 of 39 | 3300.0% |
| ucdp | `fatalities` | 2023-03 | spike | 12 of 39 | 3100.0% |
| ucdp | `fatalities` | 2023-04 | spike | 10 of 39 | 860.0% |
| ucdp | `fatalities` | 2023-05 | spike | 12 of 39 | 590.5% |
| ucdp | `fatalities` | 2023-06 | spike | 11 of 39 | 163.6% |
| ucdp | `fatalities` | 2023-07 | spike | 4 of 39 | 2550.0% |
| ucdp | `fatalities` | 2023-08 | spike | 10 of 39 | 100.0% |
| ucdp | `fatalities` | 2023-09 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities` | 2023-10 | spike | 12 of 39 | 2100.0% |
| ucdp | `fatalities` | 2023-11 | spike | 10 of 39 | 199.2% |
| ucdp | `fatalities` | 2023-12 | spike | 8 of 39 | 100.0% |
| ucdp | `fatalities` | 2024-01 | spike | 6 of 39 | 1150.0% |
| ucdp | `fatalities` | 2024-02 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities` | 2024-03 | spike | 10 of 39 | 658.3% |
| ucdp | `fatalities` | 2024-04 | spike | 15 of 39 | 1300.0% |
| ucdp | `fatalities` | 2024-05 | spike | 9 of 39 | 280.0% |
| ucdp | `fatalities` | 2024-06 | spike | 9 of 39 | 200.0% |
| ucdp | `fatalities` | 2024-07 | spike | 9 of 39 | 500.0% |
| ucdp | `fatalities` | 2024-08 | spike | 9 of 39 | 575.0% |
| ucdp | `fatalities` | 2024-09 | spike | 8 of 39 | 568.8% |
| ucdp | `fatalities` | 2024-10 | spike | 10 of 39 | 375.0% |
| ucdp | `fatalities` | 2024-11 | spike | 6 of 39 | 700.0% |
| ucdp | `fatalities` | 2024-12 | spike | 6 of 39 | 275.0% |
| ucdp | `fatalities_civilians` | 1999-02 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 1999-03 | spike | 2 of 39 | 80.0% |
| ucdp | `fatalities_civilians` | 1999-04 | spike | 2 of 39 | 700.0% |
| ucdp | `fatalities_civilians` | 1999-05 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 1999-10 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2000-02 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2000-06 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2000-07 | spike | 2 of 39 | 3000.0% |
| ucdp | `fatalities_civilians` | 2001-06 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2001-11 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2001-12 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2002-01 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2002-02 | spike | 2 of 39 | 500.0% |
| ucdp | `fatalities_civilians` | 2002-06 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2002-08 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2002-10 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2002-12 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2003-02 | spike | 2 of 39 | 850.0% |
| ucdp | `fatalities_civilians` | 2003-03 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2003-04 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2003-05 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2003-08 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2003-12 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2004-02 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2004-04 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2004-06 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2004-08 | spike | 2 of 39 | 200.0% |
| ucdp | `fatalities_civilians` | 2004-09 | spike | 2 of 39 | 83.3% |
| ucdp | `fatalities_civilians` | 2004-10 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2005-02 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2005-03 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2005-04 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2006-01 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2006-10 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2007-09 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2007-11 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2007-12 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2008-05 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2008-06 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2008-08 | spike | 3 of 39 | 200.0% |
| ucdp | `fatalities_civilians` | 2008-09 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2008-12 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2009-01 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2009-02 | spike | 2 of 39 | 200.0% |
| ucdp | `fatalities_civilians` | 2009-03 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2009-04 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2009-06 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2009-07 | spike | 2 of 39 | 400.0% |
| ucdp | `fatalities_civilians` | 2010-04 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2010-05 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2010-11 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2011-01 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2011-02 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2011-03 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2011-05 | spike | 2 of 39 | 300.0% |
| ucdp | `fatalities_civilians` | 2011-06 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2011-07 | spike | 2 of 39 | 625.0% |
| ucdp | `fatalities_civilians` | 2011-08 | spike | 1 of 39 | 96.6% |
| ucdp | `fatalities_civilians` | 2011-09 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2011-10 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2011-11 | spike | 3 of 39 | 1266.7% |
| ucdp | `fatalities_civilians` | 2011-12 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2012-01 | spike | 4 of 39 | 1000.0% |
| ucdp | `fatalities_civilians` | 2012-02 | spike | 7 of 39 | 1846.2% |
| ucdp | `fatalities_civilians` | 2012-03 | spike | 7 of 39 | 150.0% |
| ucdp | `fatalities_civilians` | 2012-04 | spike | 4 of 39 | 600.0% |
| ucdp | `fatalities_civilians` | 2012-05 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2012-06 | spike | 3 of 39 | 162.5% |
| ucdp | `fatalities_civilians` | 2012-07 | spike | 3 of 39 | 400.0% |
| ucdp | `fatalities_civilians` | 2012-08 | spike | 6 of 39 | 150.0% |
| ucdp | `fatalities_civilians` | 2012-09 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2012-10 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2012-11 | spike | 3 of 39 | 216.7% |
| ucdp | `fatalities_civilians` | 2012-12 | spike | 1 of 39 | 96.7% |
| ucdp | `fatalities_civilians` | 2013-01 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2013-02 | spike | 4 of 39 | 225.0% |
| ucdp | `fatalities_civilians` | 2013-03 | spike | 4 of 39 | 600.0% |
| ucdp | `fatalities_civilians` | 2013-04 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2013-05 | spike | 2 of 39 | 400.0% |
| ucdp | `fatalities_civilians` | 2013-06 | spike | 3 of 39 | 210.0% |
| ucdp | `fatalities_civilians` | 2013-07 | spike | 2 of 39 | 312.9% |
| ucdp | `fatalities_civilians` | 2013-08 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2013-09 | spike | 3 of 39 | 220.8% |
| ucdp | `fatalities_civilians` | 2013-10 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2013-11 | spike | 2 of 39 | 70.5% |
| ucdp | `fatalities_civilians` | 2013-12 | spike | 2 of 39 | 66.3% |
| ucdp | `fatalities_civilians` | 2014-01 | spike | 2 of 39 | 322.9% |
| ucdp | `fatalities_civilians` | 2014-02 | spike | 3 of 39 | 295.7% |
| ucdp | `fatalities_civilians` | 2014-03 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2014-04 | spike | 2 of 39 | 60.0% |
| ucdp | `fatalities_civilians` | 2014-05 | spike | 5 of 39 | 162.5% |
| ucdp | `fatalities_civilians` | 2014-06 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2014-07 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2014-08 | spike | 6 of 39 | 249.4% |
| ucdp | `fatalities_civilians` | 2014-09 | spike | 2 of 39 | 85.9% |
| ucdp | `fatalities_civilians` | 2014-10 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2014-11 | spike | 3 of 39 | 440.0% |
| ucdp | `fatalities_civilians` | 2014-12 | spike | 7 of 39 | 189.9% |
| ucdp | `fatalities_civilians` | 2015-01 | spike | 6 of 39 | 313.4% |
| ucdp | `fatalities_civilians` | 2015-02 | spike | 3 of 39 | 87.5% |
| ucdp | `fatalities_civilians` | 2015-03 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2015-04 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2015-05 | spike | 3 of 39 | 350.0% |
| ucdp | `fatalities_civilians` | 2015-06 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2015-07 | spike | 4 of 39 | 475.0% |
| ucdp | `fatalities_civilians` | 2015-08 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2015-09 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2015-10 | spike | 2 of 39 | 320.0% |
| ucdp | `fatalities_civilians` | 2015-11 | spike | 3 of 39 | 87.9% |
| ucdp | `fatalities_civilians` | 2015-12 | spike | 5 of 39 | 1170.6% |
| ucdp | `fatalities_civilians` | 2016-01 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2016-02 | spike | 3 of 39 | 233.3% |
| ucdp | `fatalities_civilians` | 2016-03 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2016-04 | spike | 1 of 39 | 82.6% |
| ucdp | `fatalities_civilians` | 2016-05 | spike | 3 of 39 | 178.6% |
| ucdp | `fatalities_civilians` | 2016-06 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2016-07 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2016-08 | spike | 2 of 39 | 106.2% |
| ucdp | `fatalities_civilians` | 2016-11 | spike | 2 of 39 | 71.4% |
| ucdp | `fatalities_civilians` | 2016-12 | spike | 1 of 39 | 75.0% |
| ucdp | `fatalities_civilians` | 2017-01 | spike | 3 of 39 | 716.7% |
| ucdp | `fatalities_civilians` | 2017-02 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2017-03 | spike | 3 of 39 | 163.6% |
| ucdp | `fatalities_civilians` | 2017-04 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2017-05 | spike | 2 of 39 | 106.9% |
| ucdp | `fatalities_civilians` | 2017-06 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2017-07 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2017-08 | spike | 2 of 39 | 125.3% |
| ucdp | `fatalities_civilians` | 2017-09 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2017-10 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2017-11 | spike | 2 of 39 | 365.2% |
| ucdp | `fatalities_civilians` | 2017-12 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2018-01 | spike | 2 of 39 | 325.0% |
| ucdp | `fatalities_civilians` | 2018-02 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2018-03 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2018-04 | spike | 2 of 39 | 243.8% |
| ucdp | `fatalities_civilians` | 2018-05 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2018-06 | spike | 3 of 39 | 372.7% |
| ucdp | `fatalities_civilians` | 2018-07 | spike | 1 of 39 | 69.2% |
| ucdp | `fatalities_civilians` | 2018-08 | spike | 5 of 39 | 180.0% |
| ucdp | `fatalities_civilians` | 2018-09 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2018-10 | spike | 2 of 39 | 436.8% |
| ucdp | `fatalities_civilians` | 2018-11 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2018-12 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2019-01 | spike | 2 of 39 | 278.3% |
| ucdp | `fatalities_civilians` | 2019-02 | spike | 2 of 39 | 150.0% |
| ucdp | `fatalities_civilians` | 2019-03 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2019-04 | spike | 4 of 39 | 400.0% |
| ucdp | `fatalities_civilians` | 2019-05 | spike | 4 of 39 | 155.6% |
| ucdp | `fatalities_civilians` | 2019-06 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2019-07 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2019-08 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2019-09 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2019-10 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2019-11 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2019-12 | spike | 2 of 39 | 2600.0% |
| ucdp | `fatalities_civilians` | 2020-01 | spike | 4 of 39 | 103.7% |
| ucdp | `fatalities_civilians` | 2020-02 | spike | 4 of 39 | 200.0% |
| ucdp | `fatalities_civilians` | 2020-03 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2020-04 | spike | 2 of 39 | 183.3% |
| ucdp | `fatalities_civilians` | 2020-05 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2020-06 | spike | 5 of 39 | 440.7% |
| ucdp | `fatalities_civilians` | 2020-07 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2020-08 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2020-09 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2020-10 | spike | 4 of 39 | 1100.0% |
| ucdp | `fatalities_civilians` | 2020-11 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2020-12 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2021-01 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2021-02 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2021-03 | spike | 3 of 39 | 128.6% |
| ucdp | `fatalities_civilians` | 2021-04 | spike | 3 of 39 | 133.3% |
| ucdp | `fatalities_civilians` | 2021-05 | spike | 7 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2021-06 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2021-07 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2021-08 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2021-09 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2021-10 | spike | 3 of 39 | 271.4% |
| ucdp | `fatalities_civilians` | 2021-11 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2021-12 | spike | 4 of 39 | 1150.0% |
| ucdp | `fatalities_civilians` | 2022-01 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2022-02 | spike | 5 of 39 | 540.0% |
| ucdp | `fatalities_civilians` | 2022-03 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2022-04 | spike | 4 of 39 | 144.4% |
| ucdp | `fatalities_civilians` | 2022-05 | spike | 5 of 39 | 1866.7% |
| ucdp | `fatalities_civilians` | 2022-06 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2022-07 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2022-08 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2022-09 | spike | 1 of 39 | 87.5% |
| ucdp | `fatalities_civilians` | 2022-10 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2022-11 | spike | 3 of 39 | 760.0% |
| ucdp | `fatalities_civilians` | 2022-12 | spike | 1 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2023-01 | spike | 6 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2023-02 | spike | 2 of 39 | 700.0% |
| ucdp | `fatalities_civilians` | 2023-03 | spike | 8 of 39 | 3600.0% |
| ucdp | `fatalities_civilians` | 2023-04 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2023-05 | spike | 5 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2023-06 | spike | 4 of 39 | 440.0% |
| ucdp | `fatalities_civilians` | 2023-07 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2023-08 | spike | 8 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2023-09 | spike | 3 of 39 | 114.3% |
| ucdp | `fatalities_civilians` | 2023-10 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2023-11 | spike | 4 of 39 | 880.0% |
| ucdp | `fatalities_civilians` | 2023-12 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2024-01 | spike | 5 of 39 | 800.0% |
| ucdp | `fatalities_civilians` | 2024-02 | spike | 4 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2024-03 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2024-04 | spike | 5 of 39 | 500.0% |
| ucdp | `fatalities_civilians` | 2024-05 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2024-06 | spike | 3 of 39 | 300.0% |
| ucdp | `fatalities_civilians` | 2024-07 | spike | 3 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2024-08 | spike | 4 of 39 | 265.2% |
| ucdp | `fatalities_civilians` | 2024-09 | spike | 4 of 39 | 2475.0% |
| ucdp | `fatalities_civilians` | 2024-10 | spike | 10 of 39 | 1200.0% |
| ucdp | `fatalities_civilians` | 2024-11 | spike | 2 of 39 | 100.0% |
| ucdp | `fatalities_civilians` | 2024-12 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 1999-02 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 1999-03 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 1999-04 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 1999-05 | spike | 3 of 39 | 200.0% |
| ucdp | `incidents` | 1999-06 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 1999-07 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 1999-10 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 1999-11 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 2000-02 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2000-03 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2000-06 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2000-07 | spike | 2 of 39 | 300.0% |
| ucdp | `incidents` | 2001-05 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2001-06 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 2001-07 | spike | 2 of 39 | 200.0% |
| ucdp | `incidents` | 2001-10 | spike | 2 of 39 | 300.0% |
| ucdp | `incidents` | 2001-11 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2001-12 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2002-02 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2002-06 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2002-07 | spike | 1 of 39 | 150.0% |
| ucdp | `incidents` | 2002-08 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2002-09 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 2002-10 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2002-11 | spike | 2 of 39 | 800.0% |
| ucdp | `incidents` | 2002-12 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2003-01 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2003-02 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2003-03 | spike | 5 of 39 | 200.0% |
| ucdp | `incidents` | 2003-04 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2003-05 | spike | 13 of 39 | 100.0% |
| ucdp | `incidents` | 2003-06 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2003-07 | spike | 2 of 39 | 500.0% |
| ucdp | `incidents` | 2003-08 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2003-11 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 2003-12 | spike | 2 of 39 | 300.0% |
| ucdp | `incidents` | 2004-01 | spike | 2 of 39 | 175.0% |
| ucdp | `incidents` | 2004-02 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2004-03 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 2004-04 | spike | 4 of 39 | 200.0% |
| ucdp | `incidents` | 2004-05 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2004-06 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2004-07 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2004-08 | spike | 2 of 39 | 500.0% |
| ucdp | `incidents` | 2004-09 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2004-10 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2004-11 | spike | 2 of 39 | 300.0% |
| ucdp | `incidents` | 2005-02 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2005-03 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2005-04 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 2005-07 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2005-12 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2006-01 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 2006-02 | spike | 2 of 39 | 1200.0% |
| ucdp | `incidents` | 2006-05 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2006-10 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 2007-02 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 2007-03 | spike | 2 of 39 | 200.0% |
| ucdp | `incidents` | 2007-04 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2007-05 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2007-07 | spike | 2 of 39 | 200.0% |
| ucdp | `incidents` | 2007-09 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 2007-10 | spike | 2 of 39 | 200.0% |
| ucdp | `incidents` | 2007-11 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2007-12 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2008-01 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2008-02 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2008-03 | spike | 1 of 39 | 100.0% |
| ucdp | `incidents` | 2008-04 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2008-05 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2008-06 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2008-07 | spike | 1 of 39 | 200.0% |
| ucdp | `incidents` | 2008-08 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2008-09 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2008-12 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2009-01 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2009-02 | spike | 2 of 39 | 400.0% |
| ucdp | `incidents` | 2009-03 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2009-04 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2009-05 | spike | 3 of 39 | 150.0% |
| ucdp | `incidents` | 2009-06 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2009-07 | spike | 3 of 39 | 800.0% |
| ucdp | `incidents` | 2010-01 | spike | 2 of 39 | 900.0% |
| ucdp | `incidents` | 2010-02 | spike | 2 of 39 | 90.0% |
| ucdp | `incidents` | 2010-03 | spike | 4 of 39 | 200.0% |
| ucdp | `incidents` | 2010-04 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2010-05 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2010-06 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2010-07 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2010-08 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2010-09 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2010-10 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2010-11 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2010-12 | spike | 3 of 39 | 200.0% |
| ucdp | `incidents` | 2011-01 | spike | 2 of 39 | 166.7% |
| ucdp | `incidents` | 2011-02 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2011-03 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2011-04 | spike | 6 of 39 | 250.0% |
| ucdp | `incidents` | 2011-05 | spike | 17 of 39 | 200.0% |
| ucdp | `incidents` | 2011-06 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2011-07 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2011-08 | spike | 4 of 39 | 300.0% |
| ucdp | `incidents` | 2011-09 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2011-10 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2011-11 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2011-12 | spike | 8 of 39 | 100.0% |
| ucdp | `incidents` | 2012-01 | spike | 12 of 39 | 300.0% |
| ucdp | `incidents` | 2012-02 | spike | 7 of 39 | 400.0% |
| ucdp | `incidents` | 2012-03 | spike | 5 of 39 | 200.0% |
| ucdp | `incidents` | 2012-04 | spike | 10 of 39 | 150.0% |
| ucdp | `incidents` | 2012-05 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2012-06 | spike | 8 of 39 | 400.0% |
| ucdp | `incidents` | 2012-07 | spike | 6 of 39 | 260.0% |
| ucdp | `incidents` | 2012-08 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2012-09 | spike | 7 of 39 | 100.0% |
| ucdp | `incidents` | 2012-10 | spike | 6 of 39 | 1200.0% |
| ucdp | `incidents` | 2012-11 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2012-12 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2013-01 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2013-02 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2013-03 | spike | 7 of 39 | 300.0% |
| ucdp | `incidents` | 2013-04 | spike | 5 of 39 | 200.0% |
| ucdp | `incidents` | 2013-05 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2013-06 | spike | 7 of 39 | 100.0% |
| ucdp | `incidents` | 2013-07 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2013-08 | spike | 10 of 39 | 100.0% |
| ucdp | `incidents` | 2013-09 | spike | 4 of 39 | 400.0% |
| ucdp | `incidents` | 2013-10 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2013-11 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2013-12 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2014-01 | spike | 4 of 39 | 300.0% |
| ucdp | `incidents` | 2014-02 | spike | 4 of 39 | 450.0% |
| ucdp | `incidents` | 2014-03 | spike | 6 of 39 | 113.3% |
| ucdp | `incidents` | 2014-04 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2014-05 | spike | 9 of 39 | 100.0% |
| ucdp | `incidents` | 2014-06 | spike | 6 of 39 | 350.0% |
| ucdp | `incidents` | 2014-07 | spike | 11 of 39 | 300.0% |
| ucdp | `incidents` | 2014-08 | spike | 7 of 39 | 800.0% |
| ucdp | `incidents` | 2014-09 | spike | 2 of 39 | 200.0% |
| ucdp | `incidents` | 2014-10 | spike | 7 of 39 | 200.0% |
| ucdp | `incidents` | 2014-11 | spike | 10 of 39 | 350.0% |
| ucdp | `incidents` | 2014-12 | spike | 8 of 39 | 133.3% |
| ucdp | `incidents` | 2015-01 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2015-02 | spike | 7 of 39 | 200.0% |
| ucdp | `incidents` | 2015-03 | spike | 5 of 39 | 400.0% |
| ucdp | `incidents` | 2015-04 | spike | 10 of 39 | 100.0% |
| ucdp | `incidents` | 2015-05 | spike | 7 of 39 | 300.0% |
| ucdp | `incidents` | 2015-06 | spike | 9 of 39 | 300.0% |
| ucdp | `incidents` | 2015-07 | spike | 7 of 39 | 100.0% |
| ucdp | `incidents` | 2015-08 | spike | 5 of 39 | 300.0% |
| ucdp | `incidents` | 2015-09 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2015-10 | spike | 6 of 39 | 350.0% |
| ucdp | `incidents` | 2015-11 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2015-12 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2016-01 | spike | 6 of 39 | 300.0% |
| ucdp | `incidents` | 2016-02 | spike | 9 of 39 | 1000.0% |
| ucdp | `incidents` | 2016-03 | spike | 7 of 39 | 100.0% |
| ucdp | `incidents` | 2016-04 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2016-05 | spike | 4 of 39 | 200.0% |
| ucdp | `incidents` | 2016-06 | spike | 11 of 39 | 100.0% |
| ucdp | `incidents` | 2016-07 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2016-08 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2016-09 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2016-10 | spike | 4 of 39 | 200.0% |
| ucdp | `incidents` | 2016-11 | spike | 4 of 39 | 200.0% |
| ucdp | `incidents` | 2016-12 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2017-01 | spike | 8 of 39 | 300.0% |
| ucdp | `incidents` | 2017-02 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2017-03 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2017-04 | spike | 2 of 39 | 600.0% |
| ucdp | `incidents` | 2017-05 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2017-06 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2017-07 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2017-08 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2017-09 | spike | 4 of 39 | 200.0% |
| ucdp | `incidents` | 2017-10 | spike | 3 of 39 | 266.7% |
| ucdp | `incidents` | 2017-11 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2017-12 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2018-01 | spike | 5 of 39 | 1600.0% |
| ucdp | `incidents` | 2018-02 | spike | 7 of 39 | 100.0% |
| ucdp | `incidents` | 2018-03 | spike | 7 of 39 | 600.0% |
| ucdp | `incidents` | 2018-04 | spike | 4 of 39 | 733.3% |
| ucdp | `incidents` | 2018-05 | spike | 6 of 39 | 400.0% |
| ucdp | `incidents` | 2018-06 | spike | 4 of 39 | 700.0% |
| ucdp | `incidents` | 2018-07 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2018-08 | spike | 7 of 39 | 900.0% |
| ucdp | `incidents` | 2018-09 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2018-10 | spike | 2 of 39 | 100.0% |
| ucdp | `incidents` | 2018-11 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2018-12 | spike | 5 of 39 | 300.0% |
| ucdp | `incidents` | 2019-01 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2019-02 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2019-03 | spike | 8 of 39 | 100.0% |
| ucdp | `incidents` | 2019-04 | spike | 6 of 39 | 400.0% |
| ucdp | `incidents` | 2019-05 | spike | 9 of 39 | 150.0% |
| ucdp | `incidents` | 2019-06 | spike | 7 of 39 | 100.0% |
| ucdp | `incidents` | 2019-07 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2019-08 | spike | 3 of 39 | 200.0% |
| ucdp | `incidents` | 2019-09 | spike | 10 of 39 | 200.0% |
| ucdp | `incidents` | 2019-10 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2019-11 | spike | 8 of 39 | 500.0% |
| ucdp | `incidents` | 2019-12 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2020-01 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2020-02 | spike | 7 of 39 | 100.0% |
| ucdp | `incidents` | 2020-03 | spike | 6 of 39 | 400.0% |
| ucdp | `incidents` | 2020-04 | spike | 3 of 39 | 100.0% |
| ucdp | `incidents` | 2020-05 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2020-06 | spike | 9 of 39 | 100.0% |
| ucdp | `incidents` | 2020-07 | spike | 7 of 39 | 350.0% |
| ucdp | `incidents` | 2020-08 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2020-09 | spike | 4 of 39 | 100.0% |
| ucdp | `incidents` | 2020-10 | spike | 8 of 39 | 200.0% |
| ucdp | `incidents` | 2020-11 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2020-12 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2021-01 | spike | 7 of 39 | 500.0% |
| ucdp | `incidents` | 2021-02 | spike | 5 of 39 | 200.0% |
| ucdp | `incidents` | 2021-03 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2021-04 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2021-05 | spike | 12 of 39 | 800.0% |
| ucdp | `incidents` | 2021-06 | spike | 10 of 39 | 100.0% |
| ucdp | `incidents` | 2021-07 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2021-08 | spike | 10 of 39 | 300.0% |
| ucdp | `incidents` | 2021-09 | spike | 3 of 39 | 200.0% |
| ucdp | `incidents` | 2021-10 | spike | 7 of 39 | 271.4% |
| ucdp | `incidents` | 2021-11 | spike | 10 of 39 | 100.0% |
| ucdp | `incidents` | 2021-12 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2022-01 | spike | 6 of 39 | 200.0% |
| ucdp | `incidents` | 2022-02 | spike | 10 of 39 | 400.0% |
| ucdp | `incidents` | 2022-03 | spike | 7 of 39 | 133.3% |
| ucdp | `incidents` | 2022-04 | spike | 6 of 39 | 100.0% |
| ucdp | `incidents` | 2022-05 | spike | 13 of 39 | 200.0% |
| ucdp | `incidents` | 2022-06 | spike | 12 of 39 | 200.0% |
| ucdp | `incidents` | 2022-07 | spike | 11 of 39 | 100.0% |
| ucdp | `incidents` | 2022-08 | spike | 6 of 39 | 400.0% |
| ucdp | `incidents` | 2022-09 | spike | 7 of 39 | 100.0% |
| ucdp | `incidents` | 2022-10 | spike | 7 of 39 | 200.0% |
| ucdp | `incidents` | 2022-11 | spike | 9 of 39 | 300.0% |
| ucdp | `incidents` | 2022-12 | spike | 6 of 39 | 400.0% |
| ucdp | `incidents` | 2023-01 | spike | 8 of 39 | 300.0% |
| ucdp | `incidents` | 2023-02 | spike | 8 of 39 | 250.0% |
| ucdp | `incidents` | 2023-03 | spike | 10 of 39 | 200.0% |
| ucdp | `incidents` | 2023-04 | spike | 8 of 39 | 600.0% |
| ucdp | `incidents` | 2023-05 | spike | 10 of 39 | 100.0% |
| ucdp | `incidents` | 2023-06 | spike | 10 of 39 | 225.0% |
| ucdp | `incidents` | 2023-07 | spike | 5 of 39 | 500.0% |
| ucdp | `incidents` | 2023-08 | spike | 7 of 39 | 100.0% |
| ucdp | `incidents` | 2023-09 | spike | 7 of 39 | 100.0% |
| ucdp | `incidents` | 2023-10 | spike | 10 of 39 | 400.0% |
| ucdp | `incidents` | 2023-11 | spike | 9 of 39 | 100.0% |
| ucdp | `incidents` | 2023-12 | spike | 7 of 39 | 100.0% |
| ucdp | `incidents` | 2024-01 | spike | 4 of 39 | 250.0% |
| ucdp | `incidents` | 2024-02 | spike | 5 of 39 | 100.0% |
| ucdp | `incidents` | 2024-03 | spike | 8 of 39 | 350.0% |
| ucdp | `incidents` | 2024-04 | spike | 13 of 39 | 200.0% |
| ucdp | `incidents` | 2024-05 | spike | 9 of 39 | 200.0% |
| ucdp | `incidents` | 2024-06 | spike | 7 of 39 | 100.0% |
| ucdp | `incidents` | 2024-07 | spike | 9 of 39 | 112.5% |
| ucdp | `incidents` | 2024-08 | spike | 8 of 39 | 200.0% |
| ucdp | `incidents` | 2024-09 | spike | 5 of 39 | 300.0% |
| ucdp | `incidents` | 2024-10 | spike | 7 of 39 | 150.0% |
| ucdp | `incidents` | 2024-11 | spike | 5 of 39 | 200.0% |
| ucdp | `incidents` | 2024-12 | spike | 8 of 39 | 100.0% |

A month flagged in every unit is a movement of the distribution, not a per-unit extraction error: the source documents are reconciled against their own published Total row by `tests/verify_faac.py`, so a swing shared by all 36 states is what the documents say. These flags are review prompts and are **not** adjudicated in the spec, because a verdict without evidence would be worse than the prompt.

## Empty series (nothing inside the study window)

None.

## Definition breaks carried into the window

- `oil` — 2020-04-01 · **WTI negative-price episode**: Brent is quoted here, not WTI, so no negative print reaches this series. The annotation is carried because the two benchmarks are routinely conflated when the 2020 window is discussed.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `gdp_per_capita` — 2014-04-06 · **GDP rebasing**: Same rebasing as gdp_growth; the per-capita level shifts with the denominator.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.
- `unemp` — 2014-01-01 · **Labour-force methodology change**: NBS moved to the ILO-aligned definition, lifting measured unemployment substantially. The series is not comparable across this date.
- `unemp` — 2023-03-01 · **Methodology revision**: NBS revised the definition again; the level steps down.
- `fx` — 2016-06-20 · **Naira floated**: The CBN abandoned the pegged rate for a managed float. The official rate series steps, and the premium over the parallel rate narrows sharply. A single official series understates the effective rate before this date.
- `fx` — 2023-06-14 · **FX unification**: Multiple official windows were collapsed into a single rate, producing an immediate large step. Classified as a definitional break rather than a data error, which is why it is annotated here and not merely flagged by the spike gate.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `gdp_growth` — 2014-04-06 · **GDP rebasing**: Nigeria rebased GDP to a 2010 base year, roughly doubling measured nominal GDP and shifting the level of the series. Level comparisons across April 2014 are not meaningful.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.
- `cpi_yoy` — 2025-01-01 · **CPI rebasing (2024 base year)**: The NBS rebased the Consumer Price Index in January 2025 — the first rebasing since 2009 — on a new 2024 base year with an updated basket. Headline inflation fell from 34.80% in December 2024 to 24.48% in January 2025, largely because of the rebasing rather than a change in prices (Reuters, 2025-02-18; NBS release). The World Bank's annual averages inherit this: 33.24% for 2024 against 23.01% for 2025. Comparison across January 2025 mixes disinflation with a measurement change and must be annotated, not smoothed.

## What a flag means

A flag is a review prompt, not a verdict. A gap flag means the series has a hole the models
must not silently interpolate across. A spike flag means the move is either a documented event
or a probable data error, and `spike_adjudications` in `analysis/specs/quality.yml` records
which — an unadjudicated flag is printed as such rather than dropped.
