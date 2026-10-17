# Vintage quality report — 2026-10-16

Stage 3 gate results for every series in the raw layer. Generated 2026-10-17T02:23:27+00:00 by `ingestion/flows/check_quality.py` from `analysis/specs/quality.yml`.

**Study window:** 1999-01-01 → open. Gates for gaps and spikes are evaluated *inside* this window only.

**Thresholds:** gap_max_months=3, spike_pct=50.0, spike_points=10.0, revision_tolerance_pct=1.0, revision_tolerance_abs=1e-06.

**Sources:** `faac` @ 2026-10-16-correction, `fred` @ 2026-10-11, `worldbank` @ 2026-10-11, `worldbank_donors` @ 2026-10-11.

**Series gated:** 125 — ok 60, flagged 65, empty 0.

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
