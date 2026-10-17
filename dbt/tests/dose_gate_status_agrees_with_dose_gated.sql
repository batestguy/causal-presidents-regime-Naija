-- `dose_gated` is a claim about a gate result, so it must agree with the status that carries it.
--
-- Two ways it can lie: saying gated while carrying no status (the boolean and the evidence disagree),
-- or saying ungated while carrying a status (a gate result exists and the panel is pretending it does
-- not). Both are cheap to state and impossible to notice by reading the panel, which is why they are a
-- test rather than a comment.
select
    state_id,
    state_name,
    period_month,
    dose_gated,
    dose_gate_status,
    dose_gate_vintage
from {{ ref('state_panel') }}
where (dose_gated and dose_gate_status is null)
   or (not dose_gated and dose_gate_status is not null)
   or (dose_gated and dose_gate_vintage is null)

union all

-- The checks above are all satisfied by a join that matched nothing: every row would say ungated with no
-- status, which is internally consistent and wrong. Stage 3 gates one series per state, so the panel must
-- show 36 gated units and the FCT — the 37th, which is not a beneficiary of this distribution — ungated.
-- What the status *says* is deliberately not asserted here: it is the gate's finding, and pinning it in a
-- test would make the next honest gate result look like a regression.
select
    state_id,
    state_name,
    period_month,
    dose_gated,
    dose_gate_status,
    dose_gate_vintage
from {{ ref('state_panel') }}
where (state_name = 'FCT' and dose_gated)
   or (state_name <> 'FCT' and not dose_gated)
   or (state_name <> 'FCT' and dose_gate_status is null)
