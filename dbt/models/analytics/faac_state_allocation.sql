-- The state × month FAAC allocation, with **one** publisher chosen per state-month and the dose
-- columns computed. This is the table Family A's dose comes from and the table Stage 5's dose
-- validation reads.
--
-- ## Which column is the dose
--
-- `gross_total` — the state's statutory allocation plus its 13% derivation share. It is the dose
-- because it is the **only** per-state figure that every one of the 174 documents publishes in the
-- same place under the same name, and that property was arrived at by rejecting the alternatives
-- against the documents rather than assumed:
--
--   * `total_gross_amount` (the full share: statutory + derivation + VAT + EMTL + ecology +
--     augmentation) exists only from 2024. Its own column-number row declares how it is built
--     ("21=6+13+14+15+18"), but the referenced indices do not survive extraction on every layout —
--     2024-01 extracts a duplicated `Gross VAT Allocation` column — so reading it back was wrong by
--     hundreds of millions on several months instead of failing outright.
--   * Summing the named gross channels instead was short by a *different* amount on the same months,
--     which is the signature of a channel the header row does not name at all.
--   * The 2020-2023 layouts publish no total column, so neither approach covers them anyway.
--
-- The decomposition columns beside the dose are incomplete, and it matters that this is not read as
-- "the document published nothing there": 541 of the workbook's header cells across the 174 documents do
-- not resolve, and they are enumerated in `data/staging/faac_parse_report.json`. The dose column is not
-- among them — `gross_total` resolves in every document and every document reconciles to its own Total
-- row — but a NULL `derivation_13pct` means "not resolved", not "zero". See `harmonisation.yml`
-- `faac_dose.item_set_caveat`.
--
-- `gross_total` is gross rather than net deliberately: the state-specific federal charges (external
-- debt, ISPO contractual obligation) that turn it into `total_net_amount` are themselves fiscal
-- outcomes of the state's own borrowing, and netting them out would put part of the response on the
-- left-hand side. `total_net_amount` is carried alongside for the robustness axis.
--
-- ## Which publication is the series
--
-- Two offices publish the same workbook and the project lands both. The rule is declared, not implied:
--
--     1. **OAGF** — the primary. The workbook originates in the Office of the Accountant General of the
--        Federation, the office base spec §5 names for exposure metric D1, and it is the longer of the
--        two series.
--     2. **NBS** — the fallback, used only where the primary has no document for that month. It is a
--        republication of the same workbook, not a second measurement.
--
-- The fallback is not silent: `publisher` carries which publication supplied each row, so a month read
-- from the fallback is visible in the base rather than indistinguishable from a primary month.
--
-- **The cross-check does not currently corroborate.** `is_cross_checked`, `other_publisher` and
-- `cross_check_rel_diff` measure the two publications against each other on every month both carry, and
-- they are carried on the row rather than tested here, because the finding is not what the design
-- expected: for most overlapping state-months the two publications do **not** agree, and on some they
-- differ by more than 40%. Each document reconciles exactly against its own published Total row, so the
-- disagreement is between the publications and not between a document and the parser — see
-- `docs/decisions.md` C-39 for the finding and its magnitude: 2,124 of 2,160 overlapping state-months
-- (98.3%) agree to within a naira and 59 of the 60 overlapping months agree at every state, and the one
-- month that does not (2023-04) differs at every state. A verifier that failed on that difference would
-- be failing on a fact about the sources, so the difference is carried and reported instead, and the
-- publisher choice is exposed as a robustness axis in `analysis/specs/harmonisation.yml`.
--
-- ## Why the FCT is absent
--
-- Table III distributes the Federation Account among **36 beneficiaries**; the FCT's line is funded from
-- the federal share. The parser excludes that 37th line as well as the FCT, because the published label
-- for it is not stable (`FCT ABUJA` in the 2026 documents, `SOKU` in the 2024 ones) and a label that
-- differs between publications is not an identity. So the panel carries 36 doses and the FCT has none,
-- which `state_panel` records as a declared status rather than as a missing month. `n_beneficiaries`
-- travels with every row so the 36 is visible rather than implied.
--
-- ## Why `share_of_state_pool` says "state"
--
-- The denominator is the sum across the 36 states, not the whole distributable pool, because the
-- remaining beneficiaries (the FGN, the FCT and the 774 local governments) are distributed by tables
-- this parser does not read. Naming it a share of the Federation Account would overstate the
-- denominator by roughly half.
with typed as (
    select * from {{ ref('stg_faac_allocation') }}
),

pivoted as (
    select
        state_id,
        state_name,
        period_month,
        publisher,
        max(case when item = 'gross_total' then amount_naira end) as gross_total,
        max(case when item = 'gross_statutory_allocation' then amount_naira end) as gross_statutory_allocation,
        max(case when item = 'derivation_13pct' then amount_naira end) as derivation_13pct,
        max(case when item = 'net_statutory_allocation' then amount_naira end) as net_statutory_allocation,
        max(case when item = 'gross_vat_allocation' then amount_naira end) as gross_vat_allocation,
        max(case when item = 'total_gross_amount' then amount_naira end) as total_gross_amount,
        max(case when item = 'total_net_amount' then amount_naira end) as total_net_amount,
        max(case when item = 'emtl' then amount_naira end) as emtl,
        max(case when item = 'exchange_gain' then amount_naira end) as exchange_gain,
        max(case when item = 'n_lgcs' then amount_naira end) as n_lgcs,
        max(source_dataset_id) as source_dataset_id,
        max(source_file) as source_file,
        max(source_sha256) as source_sha256,
        max(source_location) as source_location
    from typed
    group by 1, 2, 3, 4
),

preferred as (
    select
        *,
        case publisher when 'oagf' then 1 else 2 end as preference
    from pivoted
),

ranked as (
    select
        *,
        row_number() over (partition by state_id, period_month order by preference) as rank_in_month
    from preferred
),

chosen as (
    select * from ranked where rank_in_month = 1
),

-- The other publication's figure for the same state-month, where there is one.
other as (
    select
        p.state_id,
        p.period_month,
        max(p.gross_total) as other_gross_total,
        max(p.publisher) as other_publisher
    from preferred p
    join chosen c
        on c.state_id = p.state_id
       and c.period_month = p.period_month
    where p.publisher <> c.publisher
    group by 1, 2
),

month_total as (
    select
        period_month,
        sum(gross_total) as month_state_pool,
        count(*) as n_beneficiaries
    from chosen
    group by 1
)

select
    c.state_id,
    c.state_name,
    c.period_month,
    c.publisher,
    c.gross_total,
    c.gross_statutory_allocation,
    c.derivation_13pct,
    c.net_statutory_allocation,
    c.gross_vat_allocation,
    c.total_gross_amount,
    c.total_net_amount,
    c.emtl,
    c.exchange_gain,
    c.n_lgcs,
    m.month_state_pool,
    m.n_beneficiaries,
    case
        when m.month_state_pool is null or m.month_state_pool = 0 then null
        else c.gross_total / m.month_state_pool
    end as share_of_state_pool,
    (o.other_gross_total is not null) as is_cross_checked,
    o.other_publisher,
    o.other_gross_total,
    case
        when o.other_gross_total is null or o.other_gross_total = 0 then null
        else abs(c.gross_total - o.other_gross_total) / o.other_gross_total
    end as cross_check_rel_diff,
    c.source_dataset_id,
    c.source_file,
    c.source_sha256,
    c.source_location
from chosen c
left join other o
    on o.state_id = c.state_id
   and o.period_month = c.period_month
left join month_total m
    on m.period_month = c.period_month
