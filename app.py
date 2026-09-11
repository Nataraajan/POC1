"""Forecast tool. Small file. Overlay curve in, not the loan tape."""

import pandas as pd
import streamlit as st

from forecast_engine import PRODUCTS, company_pack, run
from ui import CSS, header

st.set_page_config(page_title="Forecast", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    header(
        "Forecast",
        "Apps x approval x ticket = originations. CLAB and PLL use the vintage overlay. Not the 2M loan file.",
    ),
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("**Drivers**")
    apps_m = st.slider("Applications multiplier", 0.7, 1.4, 1.0, 0.05)
    appr = st.slider("Approval rate add", -0.05, 0.05, 0.0, 0.01)
    yld = st.slider("Yield add (annual)", -0.20, 0.20, 0.0, 0.02)
    st.caption("Ticket and base approval/yield sit on the product card. Seasonality is on applications.")


@st.cache_data(show_spinner=False)
def _run(apps_m, appr, yld):
    return run(apps_mult=apps_m, approval_add=appr, yield_add=yld)


book = _run(apps_m, appr, yld)
co = company_pack(book)
act = co[~co["is_forecast"]].iloc[-1]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("CLAB", f"${act['ending_clab']/1e6:.0f}M")
c2.metric("Revenue / mo", f"${act['revenue']/1e6:.1f}M")
c3.metric("Originations", f"${act['originations']/1e6:.1f}M")
c4.metric("PLL / mo", f"${act['pll']/1e6:.1f}M")
c5.metric("Yield", f"{act['yield_ann']*100:.0f}%")

st.markdown("**Product inputs (base month)**")
st.dataframe(
    pd.DataFrame([{"product": p, "applications": s["apps"], "ticket": s["ticket"], "approval": s["approval"], "yield": s["yield"]} for p, s in PRODUCTS.items()]),
    use_container_width=True,
    hide_index=True,
)

st.markdown("**Monthly pack**")
view = co.copy()
out = view[["month", "is_forecast", "applications", "originations", "ending_clab", "revenue", "pll", "nco", "ending_ecl", "yield_ann"]].copy()
out["applications"] = out["applications"].round(0).astype(int)
for col in ["originations", "ending_clab", "revenue", "pll", "nco", "ending_ecl"]:
    out[col] = (out[col] / 1e6).round(2)
out["yield_ann"] = (out["yield_ann"] * 100).round(0)
out = out.rename(columns={"is_forecast": "forecast", "originations": "orig $M", "ending_clab": "CLAB $M", "revenue": "rev $M", "pll": "PLL $M", "nco": "NCO $M", "ending_ecl": "ECL $M", "yield_ann": "yield %"})
st.dataframe(out, use_container_width=True, hide_index=True, height=380)

chart = co.set_index("month")[["revenue", "ending_clab", "pll"]] / 1e6
a, b, c = st.columns(3)
a.caption("Revenue $M")
a.line_chart(chart["revenue"], height=200)
b.caption("CLAB $M")
b.line_chart(chart["ending_clab"], height=200)
c.caption("PLL $M")
c.line_chart(chart["pll"], height=200)
st.caption("Originations = applications x approval x ticket. CLAB = surviving originations after paydown and the overlay. PLL = originations x lifetime default. ECL_end = ECL_start + PLL - NCO.")
