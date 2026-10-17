-- The 37 state-level units: the 36 states plus the Federal Capital Territory.
--
-- This exists at Stage 4 even though the state panel's dose columns are empty, because the *unit of
-- analysis* is not in question — Family A's estimand is a state-month dose response and the 37 units
-- are a fact about the country, not a data acquisition. Declaring them now means the moment a FAAC
-- parser lands, the panel is a join rather than a schema change, and Stage 5's dose-variation check has
-- the correct denominator to report against.
--
-- `zone` is the geopolitical zone (NC/NE/NW/SE/SS/SW), which the specification curve may use as a
-- regional clustering axis; it comes from the standard six-zone classification, not from the data.
select
    state_id,
    state_name,
    zone
from {{ ref('raw_state') }}
