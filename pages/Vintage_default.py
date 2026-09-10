"""Vintage default dashboard."""

import plotly.graph_objects as go
import streamlit as st

from model import Drivers, PRODUCTS, run
from ui import CHART, CSS, GREY, LINE, NAVY, TEAL, header

st.set_page_config(page_title="Vintage default", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    header(
        "Vintage default",
        "Observed charge-off paths by origination month. Average = the curve overlaid on new originations.",
    ),
    unsafe_allow_html=True,
)

with st.sidebar:
    dflt = st.slider("Lifetime default add", 0.0, 0.15, 0.0, 0.01, format="%.2f")


@st.cache_data(show_spinner=False)
def _run(dflt):
    return run(Drivers(default_add=dflt))


_, _, triangle, _ = _run(dflt)
product = st.radio("Product", list(PRODUCTS), horizontal=True)
t = triangle[triangle["product"] == product].copy()
t["observed_cum"] = t.groupby("vintage")["observed_nco_rate"].cumsum()
latest = list(dict.fromkeys(t["vintage"].tolist()))[-6:]

fig = go.Figure()
for v in latest:
    sl = t[t["vintage"] == v]
    fig.add_scatter(x=sl["mob"], y=sl["observed_cum"] * 100, mode="lines", line=dict(color=GREY, width=1), name=v)
fit = t.drop_duplicates("mob").sort_values("mob")
fig.add_scatter(x=fit["mob"], y=fit["fitted_cum_default"] * 100, mode="lines+markers", line=dict(color=TEAL, width=3), name="Fitted overlay")
fig.update_layout(title=dict(text=f"{product} vintages vs fitted curve", font=dict(color=NAVY, size=16)), height=360, margin=dict(l=10, r=10, t=36, b=10), plot_bgcolor="#fff", paper_bgcolor="#fff", xaxis_title="Months on book", yaxis_title="Cumulative default %", yaxis=dict(gridcolor=LINE), legend=dict(orientation="h", y=-0.2))
st.plotly_chart(fig, use_container_width=True, config=CHART)
pivot = t[t["vintage"].isin(latest)].pivot_table(index="vintage", columns="mob", values="observed_cum", aggfunc="last")
st.dataframe((pivot * 100).round(1), use_container_width=True)
st.caption("Grey = history. Teal = curve used in the forecast.")
