"""Discovery readiness smoke test: PCMCI on the native monthly national system.

Exploratory only, nothing committed. Native monthly series only (oil, CPI, FAAC, UCDP); the 20 annual
series are deliberately excluded because their monthly fills manufacture edges.
"""
import sys

import duckdb
import numpy as np
import pandas as pd
from tigramite import data_processing as pp
from tigramite.pcmci import PCMCI
from tigramite.independence_tests.parcorr import ParCorr

sys.stdout.reconfigure(encoding="utf-8")

con = duckdb.connect("data/analytics.duckdb", read_only=True)

oil = con.execute("""
    select period_month, value from main_analytics.fact_metric
    where metric_id = 'oil' and value is not null
""").df().rename(columns={"value": "oil"})
cpi = con.execute("""
    select period_month, cpi_yoy_pct as cpi from main_analytics.nbs_cpi_national_monthly
""").df()
faac = con.execute("""
    select period_month, gross_total_naira as faac from main_analytics.faac_national_monthly
""").df()
ucdp = con.execute("""
    select period_month, fatalities, incidents from main_analytics.ucdp_national_monthly
""").df()

frame = (oil.merge(cpi, on="period_month").merge(faac, on="period_month").merge(ucdp, on="period_month")
         .sort_values("period_month").reset_index(drop=True))
print("native monthly overlap:", len(frame), "months,", frame.period_month.min(), "to", frame.period_month.max())

data = pd.DataFrame({
    "oil_ret": np.log(frame.oil).diff(),
    "cpi_yoy": frame.cpi,
    "faac_growth": np.log(frame.faac).diff(),
    "fatalities": frame.fatalities,
    "incidents": frame.incidents,
}).dropna().reset_index(drop=True)
print("rows after differencing:", len(data))
print(data.describe().round(2).to_string())

df = pp.DataFrame(data.to_numpy(), var_names=list(data.columns))
pcmci = PCMCI(dataframe=df, cond_ind_test=ParCorr(), verbosity=0)
results = pcmci.run_pcmci(tau_min=0, tau_max=3, pc_alpha=0.05)

print("\nPCMCI significant links (alpha 0.05, up to 3 lags):")
links = []
for i in range(len(data.columns)):
    for j in range(len(data.columns)):
        for tau in range(0, 4):
            if results["p_matrix"][i, j, tau] < 0.05 and results["val_matrix"][i, j, tau] != 0:
                links.append((f"{data.columns[j]}(t-{tau})", f"{data.columns[i]}(t)",
                              round(float(results['val_matrix'][i, j, tau]), 3),
                              round(float(results['p_matrix'][i, j, tau]), 4)))
for link in sorted(links, key=lambda x: x[3]):
    print(f"  {link[0]:>18} -> {link[1]:<18} coef={link[2]:>7} p={link[3]}")
print("\nlinks found:", len(links))
