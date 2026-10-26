import pandas as pd
import streamlit as st

from common import CAVEAT
from price_elasticity.simulator import simulate, top_reliable, load_tables

st.title("Promotion what-if")
st.caption(CAVEAT)
t = load_tables()
dept = st.selectbox("Department", sorted(t.department.unique()))
labels = sorted(t[t.department == dept].index)
label = st.selectbox("Commodity (anonymised label)", labels)
row = t.loc[label]
lo, hi = float(row.p05), float(row.p95)
depth = st.slider("Discount depth", min_value=round(lo, 3), max_value=round(hi, 3), value=round(min(max(0.2, lo), hi), 3), step=0.005,
                  help="Restricted to the 5th-95th percentile of depths observed for this commodity.")
depth = min(max(depth, lo), hi)
r = simulate(label, depth, t)
st.write(f"Elasticity (shrunk): {r['elasticity']:.2f}, 95% interval {r['elasticity_ci'][0]:.2f} to {r['elasticity_ci'][1]:.2f}. "
         f"Observed depth range {lo:.1%} to {hi:.1%}.")
if not r["reliable"]:
    st.warning("Not reliable: the elasticity is non-negative or its interval includes 0. No prediction is shown and this commodity is not ranked.")
else:
    c1, c2 = st.columns(2)
    c1.metric("Change in units vs no discount", f"{r['units_change_pct']:+.1f}%",
              help=f"95% interval {r['units_change_pct_ci'][0]:+.1f}% to {r['units_change_pct_ci'][1]:+.1f}%")
    c2.metric("Change in revenue vs no discount", f"{r['revenue_change_pct']:+.1f}%",
              help=f"95% interval {r['revenue_change_pct_ci'][0]:+.1f}% to {r['revenue_change_pct_ci'][1]:+.1f}%")
    st.write(f"Units {r['units_change_pct_ci'][0]:+.1f}% to {r['units_change_pct_ci'][1]:+.1f}%; revenue "
             f"{r['revenue_change_pct_ci'][0]:+.1f}% to {r['revenue_change_pct_ci'][1]:+.1f}% (interval from the elasticity's 95% interval).")
st.subheader("Most reliable commodities (example at 20% depth, clipped to each range)")
ex = pd.DataFrame(top_reliable(t, 5))
st.dataframe(ex[["label", "department", "depth", "elasticity", "units_change_pct", "revenue_change_pct"]].round(2), hide_index=True)
st.caption("Constant-elasticity formula: units x (1-d)^e, revenue x (1-d)^(1+e). Associations, not a forecast of what a promotion would do.")
