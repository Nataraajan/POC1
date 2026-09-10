"""Forecast tool — monthly pack, changeable drivers."""

import streamlit as st

from model import Drivers, company_pack, run
from ui import CSS, header

st.set_page_config(page_title="Forecast", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    header("Forecast", "Monthly pack. Change a driver, the next 24 months move. Not Propel data."),
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("**Drivers**")
    apps_g = st.slider("Applications growth / month", -0.02, 0.03, 0.0, 0.005, format="%.3f")
    appr = st.slider("Approval rate add", -0.05, 0.05, 0.0, 0.01, format="%.2f")
    yld = st.slider("Yield add (annual)", -0.20, 0.20, 0.0, 0.02, format="%.2f")
    dflt = st.slider("Lifetime default add", 0.0, 0.15, 0.0, 0.01, format="%.2f")
    st.caption("Fixed: seasonality, ticket, product mix. You move demand, underwriting, price, credit.")


@st.cache_data(show_spinner=False)
def _run(apps_g, appr, yld, dflt):
    return run(Drivers(apps_growth=apps_g, approval_add=appr, yield_add=yld, default_add=dflt))


monthly, _, _, _ = _run(apps_g, appr, yld, dflt)
co = company_pack(monthly)
last_act = co[~co["is_forecast"]].iloc[-1]
last_fc = co[co["is_forecast"]].iloc[-1]

a, b, c, d, e = st.columns(5)
a.metric("Last actual CLAB", f"${last_act['ending_clab']/1e6:.0f}M")
b.metric("Last actual revenue", f"${last_act['revenue']/1e6:.1f}M")
c.metric("Applications", f"{int(last_act['applications']):,}")
d.metric("Forecast end CLAB", f"${last_fc['ending_clab']/1e6:.0f}M")
e.metric("Forecast end revenue / mo", f"${last_fc['revenue']/1e6:.1f}M")

st.markdown("**Company monthly**")
view = co.copy()
view["month"] = view["month"].astype(str)
out = view[["month", "is_forecast", "applications", "originations", "ending_clab", "revenue", "nco", "yield_ann", "default_rate"]].copy()
out["applications"] = out["applications"].round(0).astype(int)
out["originations"] = (out["originations"] / 1e6).round(2)
out["ending_clab"] = (out["ending_clab"] / 1e6).round(1)
out["revenue"] = (out["revenue"] / 1e6).round(2)
out["nco"] = (out["nco"] / 1e6).round(2)
out["yield_ann"] = (out["yield_ann"] * 100).round(0)
out["default_rate"] = (out["default_rate"] * 100).round(1)
out = out.rename(columns={"is_forecast": "forecast", "originations": "orig $M", "ending_clab": "CLAB $M", "revenue": "rev $M", "nco": "NCO $M", "yield_ann": "yield %", "default_rate": "default %"})
st.dataframe(out, use_container_width=True, hide_index=True, height=420)

chart = co.set_index(co["month"].astype(str))[["revenue", "ending_clab"]] / 1e6
c1, c2 = st.columns(2)
with c1:
    st.caption("Revenue $M")
    st.line_chart(chart["revenue"], height=240)
with c2:
    st.caption("CLAB $M")
    st.line_chart(chart["ending_clab"], height=240)

st.caption("Applications x approval x ticket = originations. CLAB = surviving vintages. Revenue = avg CLAB x yield.")
