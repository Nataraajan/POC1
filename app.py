"""Forecast dashboard."""

import plotly.graph_objects as go
import streamlit as st

from model import Drivers, PRODUCTS, company_pack, run
from ui import BLUE, CHART, CSS, GREY, LINE, NAVY, header

st.set_page_config(page_title="Forecast", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    header(
        "Forecast",
        "Applications to originations to CLAB to revenue. Two products. Monthly. Not Propel data.",
    ),
    unsafe_allow_html=True,
)

with st.sidebar:
    apps_g = st.slider("Applications growth / month", -0.02, 0.03, 0.0, 0.005, format="%.3f")
    appr = st.slider("Approval rate add", -0.05, 0.05, 0.0, 0.01, format="%.2f")
    yld = st.slider("Yield add (annual)", -0.20, 0.20, 0.0, 0.02, format="%.2f")
    dflt = st.slider("Lifetime default add", 0.0, 0.15, 0.0, 0.01, format="%.2f")


@st.cache_data(show_spinner=False)
def _run(apps_g, appr, yld, dflt):
    return run(Drivers(apps_growth=apps_g, approval_add=appr, yield_add=yld, default_add=dflt))


monthly, _, _, _ = _run(apps_g, appr, yld, dflt)
co = company_pack(monthly)
last_act = co[~co["is_forecast"]].iloc[-1]

a, b, c, d, e = st.columns(5)
a.metric("Ending CLAB", f"${last_act['ending_clab']/1e6:.0f}M")
b.metric("Last month revenue", f"${last_act['revenue']/1e6:.1f}M")
c.metric("Applications", f"{last_act['applications']/1000:.0f}k")
d.metric("On-book yield", f"{last_act['yield_ann']*100:.0f}%")
e.metric("Monthly default", f"{last_act['default_rate']*100:.1f}%")

fig = go.Figure()
fig.add_bar(x=co["month"], y=co["revenue"] / 1e6, marker_color=[GREY if not f else BLUE for f in co["is_forecast"]])
fig.update_layout(title=dict(text="Revenue ($M)", font=dict(color=NAVY, size=16)), height=280, margin=dict(l=10, r=10, t=36, b=10), plot_bgcolor="#fff", paper_bgcolor="#fff", yaxis=dict(gridcolor=LINE), xaxis=dict(dtick=6), showlegend=False)
st.plotly_chart(fig, use_container_width=True, config=CHART)

left, right = st.columns(2)
with left:
    fig2 = go.Figure()
    for product, color in zip(PRODUCTS, [NAVY, BLUE]):
        sl = monthly[monthly["product"] == product]
        fig2.add_scatter(x=sl["month"], y=sl["ending_clab"] / 1e6, name=product, line=dict(color=color))
    fig2.update_layout(title=dict(text="CLAB ($M)", font=dict(color=NAVY, size=16)), height=300, margin=dict(l=10, r=10, t=36, b=20), plot_bgcolor="#fff", paper_bgcolor="#fff", yaxis=dict(gridcolor=LINE), xaxis=dict(dtick=6), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig2, use_container_width=True, config=CHART)
with right:
    fig3 = go.Figure()
    for product, color in zip(PRODUCTS, [NAVY, BLUE]):
        sl = monthly[monthly["product"] == product]
        fig3.add_bar(x=sl["month"], y=sl["originations"] / 1e6, name=product, marker_color=color)
    fig3.update_layout(barmode="stack", title=dict(text="Originations ($M)", font=dict(color=NAVY, size=16)), height=300, margin=dict(l=10, r=10, t=36, b=20), plot_bgcolor="#fff", paper_bgcolor="#fff", yaxis=dict(gridcolor=LINE), xaxis=dict(dtick=6), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig3, use_container_width=True, config=CHART)

show = monthly[monthly["month"] == last_act["month"]][["product", "applications", "approval_rate", "originations", "ending_clab", "revenue", "nco", "yield_ann", "default_rate"]].copy()
show["applications"] = show["applications"].round(0).astype(int)
show["approval_rate"] = (show["approval_rate"] * 100).round(1)
for col in ["originations", "ending_clab", "revenue", "nco"]:
    show[col] = (show[col] / 1e6).round(2)
show["yield_ann"] = (show["yield_ann"] * 100).round(0)
show["default_rate"] = (show["default_rate"] * 100).round(1)
st.dataframe(show, use_container_width=True, hide_index=True)
st.caption("Applications x approval x ticket = originations. Revenue = avg CLAB x yield.")
