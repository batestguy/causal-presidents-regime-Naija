-- Base spec section 9 has the models use party-by-tenure dummies. If a dummy column and the stratum name
-- ever disagreed, one model would estimate PDP_second while another called the same months PDP_first, and
-- no other check in this project would catch it — the two would simply produce different numbers.
select
    metric_id,
    period_month,
    tenure_stratum,
    pdp_first,
    pdp_second,
    apc_first,
    apc_second
from {{ ref('fact_metric') }}
where (
        coalesce(pdp_first, false)::INT
      + coalesce(pdp_second, false)::INT
      + coalesce(apc_first, false)::INT
      + coalesce(apc_second, false)::INT
      ) > 1
   or (tenure_stratum = 'PDP_first' and not coalesce(pdp_first, false))
   or (tenure_stratum = 'PDP_second' and not coalesce(pdp_second, false))
   or (tenure_stratum = 'APC_first' and not coalesce(apc_first, false))
   or (tenure_stratum = 'APC_second' and not coalesce(apc_second, false))
