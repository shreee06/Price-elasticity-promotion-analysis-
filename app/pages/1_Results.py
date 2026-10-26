import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import CAVEAT, load

st.title("Results")
st.caption(CAVEAT)
tr, val, oos, test = load("elasticity_train.json"), load("elasticity_validation_stability.json"), load("oos_validation.json"), load("test_final.json")


def ci(c):
    return f"{c['estimate']:.3f} ({c['ci_low']:.3f} to {c['ci_high']:.3f})"


st.header("Elasticity of units to price paid (train weeks 8-85)")
s = tr["sample"]
st.write(f"{s['primary_products']:,} products, {s['primary_rows']:,} product-weeks.")
B = tr["bootstrap"]
st.table(pd.DataFrame([
    {"Estimator": "Poisson (PPML)", "Estimate (clustered 95% CI)": ci(tr["primary"]["ppml"]),
     "Bootstrap 95% CI": f"{B['primary_ppml']['terms']['lp']['lo']:.3f} to {B['primary_ppml']['terms']['lp']['hi']:.3f}"},
    {"Estimator": "Log-log OLS", "Estimate (clustered 95% CI)": ci(tr["primary"]["ols"]),
     "Bootstrap 95% CI": f"{B['primary_ols']['terms']['lp']['lo']:.3f} to {B['primary_ols']['terms']['lp']['hi']:.3f}"}]))
st.subheader("Regular price vs promotional discount (PPML)")
st.table(pd.DataFrame([{"Term": "Regular (shelf) price", "Estimate": ci(tr["secondary"]["ppml"]["x_base"])},
                       {"Term": "Promotional discount", "Estimate": ci(tr["secondary"]["ppml"]["x_promo"])}]))
st.warning("The regular-price coefficient did not hold up on the validation weeks; make no claim about it.")

st.header("Commodity elasticities by department")
d = pd.DataFrame(tr["commodity_by_department"])
d = d[d.n >= 5].sort_values("median_shrunk")
fig = go.Figure(go.Bar(x=d["median_shrunk"], y=d["department"], orientation="h", marker_color="#2a6fb0",
                       text=[f"{v:.2f}" for v in d["median_shrunk"]], textposition="outside",
                       customdata=d[["n", "q25_shrunk", "q75_shrunk"]],
                       hovertemplate="%{y}<br>median %{x:.3f}<br>n=%{customdata[0]}, IQR %{customdata[1]:.2f} to %{customdata[2]:.2f}<extra></extra>"))
fig.update_layout(height=380, margin=dict(l=10, r=30, t=10, b=10), xaxis_title="Median shrunk elasticity", yaxis_title=None, showlegend=False)
st.plotly_chart(fig, use_container_width=True)
ce = tr["commodity_each"]
st.write(f"Departments with at least 5 commodities. {ce['commodities_fitted']} commodities; {ce['wrong_sign_and_extremes']['positive_point_estimates']} "
         f"have a positive point estimate, shown as found.")
st.dataframe(d.rename(columns={"median_unshrunk": "median (unshrunk)", "median_shrunk": "median (shrunk)"})[
    ["department", "n", "median (unshrunk)", "median (shrunk)", "q25_shrunk", "q75_shrunk"]], hide_index=True)

st.header("Robustness (PPML, change vs comparator)")
rob = pd.DataFrame([r for r in tr["robustness"] if r["estimator"] == "ppml" and "estimate" in r])
st.dataframe(rob[["variant", "term", "estimate", "se", "n_obs", "comparator_estimate", "change"]].round(3), hide_index=True)

st.header("Stability on validation weeks 86-93")
st.dataframe(pd.DataFrame(val["comparison"])[["name", "train", "val", "diff", "z", "verdict"]].round(3), hide_index=True)
st.write(f"{val['n_stable']} of {val['n_total']} compared coefficients are stable.")

st.header("Out-of-sample check with frozen train elasticities")
rows = []
for lvl in ["product", "commodity"]:
    for g, gn in [("all", "all"), ("promo_change_gt_10pct", "promo change > 10%"), ("no_promo_change", "no promo change")]:
        for nm, r in [("validation", oos), ("test", test["test"])]:
            m = r[lvl][g]["metrics"]
            rows.append({"level": lvl, "rows": gn, "window": nm, "correlation": round(m["corr_model"]["est"], 3),
                         "MAE gain vs zero": round(m["mae_gain_vs_zero"]["est"], 4),
                         "direction right": round(m["dir_model"]["est"], 3)})
st.dataframe(pd.DataFrame(rows), hide_index=True)
st.write("Test-week stability of the primary coefficients: " + "; ".join(
    f"{r['name']} {r['window']:.3f} ({r['verdict']})" for r in test["stability_test"]["comparison"]))
