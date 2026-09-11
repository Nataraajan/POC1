"""Vintage default tool."""
import streamlit as st
from ui import CSS, header
from vintage_engine import analyze_loans

st.set_page_config(page_title="Vintage default", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(header("Vintage default", "Loan-level file in. Small curve out. The forecast uses the curve, not the loans. Mock data."), unsafe_allow_html=True)

with st.sidebar:
    n = st.select_slider("New customers / month", options=[10000, 20000, 40000], value=20000)
    st.caption("24 months x 2 products. 40k / month is about 1M loans.")

@st.cache_data(show_spinner="Analyzing loan file...")
def _analyze(n):
    return analyze_loans(n)

out = _analyze(n)
a, b, c, d = st.columns(4)
a.metric("Loans analyzed", f"{out['n_loans']:,}")
b.metric("Runtime", f"{out['seconds']:.2f}s")
c.metric("Vintages", str(out["vintages"]))
d.metric("Overlay points", str(out["curve_points"]))

st.markdown("**1. Loan file (sample)**")
st.dataframe(out["sample"], use_container_width=True, hide_index=True)
st.caption("default_mob = month charged off. -1 = paid or still current.")

st.markdown("**2. Vintage triangle (cumulative default %)**")
product = st.radio("Product", ["CreditFresh", "MoneyKey"], horizontal=True)
tri = out["triangle"]
tri = tri[tri["product"] == product]
latest = list(dict.fromkeys(tri["vintage"].tolist()))[-8:]
pivot = tri[tri["vintage"].isin(latest)].pivot_table(index="vintage", columns="mob", values="observed_cum", aggfunc="last") * 100
st.dataframe(pivot.round(1), use_container_width=True)

st.markdown("**3. Overlay curve — this is what the forecast imports**")
ov = out["overlay"]
ov_p = ov[ov["product"] == product].set_index("mob")["cum_default"] * 100
st.line_chart(ov_p, height=240)
st.dataframe(ov.assign(cum_default=(ov["cum_default"] * 100).round(1)).rename(columns={"cum_default": "cum default %"}), use_container_width=True, hide_index=True)
st.caption("Written to data/overlay_curve.csv. 16 rows, not a million.")
