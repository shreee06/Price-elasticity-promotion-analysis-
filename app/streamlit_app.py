import streamlit as st

from common import CAVEAT, load

st.set_page_config(page_title="Price elasticity and promotions", layout="wide")
st.title("Price elasticity and promotion analysis")
st.caption("dunnhumby The Complete Journey (grocery, 2,500 households). " + CAVEAT)
tr = load("elasticity_train.json")
p = tr["primary"]["ppml"]
st.metric("Primary association (Poisson, product and week fixed effects)", f"{p['estimate']:.2f}",
          help=f"95% CI {p['ci_low']:.2f} to {p['ci_high']:.2f}; a 1% lower price paid goes with about {abs(p['estimate']):.2f}% more units.")
st.write("Use the **Results** page for estimates, robustness and out-of-sample checks, and **What if** for the promotion simulator.")
