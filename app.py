"""Two-product revenue + vintage default POC."""

import plotly.graph_objects as go
import streamlit as st

from model import Drivers, PRODUCTS, company_pack, run

st.set_page_config(page_title="Product Revenue Model", layout="wide")

NAVY = "#163A63"
LINE = "#E2E8F0"
BLUE = "#2563EB"
GREY = "#94A3B8"
TEAL = "#0F766E"

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
h1.main-title { color: #163A63 !important; font-weight: 700 !important; font-size: 28px !important; margin-bottom: 2px !important; }
.header-block { margin-bottom: 12px; padding-bottom: 12px; border-bottom: 2px solid #E2E8F0; }
.header-block .tagline { color: #64748B; font-size: 13px; margin: 0; }
div[data-testid="stMetric"] { background: #fff !important; border: 1px solid #E2E8F0 !important; border-radius: 10px !important; padding: 16px 20px !important; box-shadow: 0 1px 3px rgba(15,23,42,.06) !important; }
div[data-testid="stMetricLabel"] p { font-size: 12px !important; color: #64748B !important; font-weight: 500 !important; }
div[data-testid="stMetricValue"] { font-size: 22px !important; font-weight: 700 !important; color: #172033 !important; }
.stMainBlockContainer { padding-top: 1rem !important; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="header-block">
  <h1 class="main-title">Product Revenue Model</h1>
  <p class="tagline">Two-product POC. Monthly engine, 24-month forecast. Vintage default curve fitted from mock history and overlaid on new originations. Illustrative — not Propel data.</p>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("**Drivers**")
    apps_g = st.slider("Applications growth / month", -0.02, 0.03, 0.0, 0.005, format="%.3f")
    appr = st.slider("Approval rate add", -0.05, 0.05, 0.0, 0.01, format="%.2f")
    yld = st.slider("Yield add (annual)", -0.20, 0.20, 0.0, 0.02, format="%.2f")
    dflt = st.slider("Lifetime default add", 0.0, 0.15, 0.0, 0.01, format="%.2f")
    st.caption("Seasonality is already in applications. Grain is monthly because vintages age by month.")

monthly, history, triangle, curves = run(
    Drivers(apps_growth=apps_g, approval_add=appr, yield_add=yld, default_add=dflt)
)
co = company_pack(monthly)
last_act = co[~co["is_forecast"]].iloc[-1]
last_fc = co[co["is_forecast"]].iloc[-1]

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Ending CLAB", f"${last_act['ending_clab']/1e6:.0f}M")
k2.metric("Last month revenue", f"${last_act['revenue']/1e6:.1f}M")
k3.metric("Applications", f"{last_act['applications']/1000:.0f}k")
k4.metric("On-book yield", f"{last_act['yield_ann']*100:.0f}%")
k5.metric("Monthly default", f"{last_act['default_rate']*100:.1f}%")

tab1, tab2 = st.tabs(["Forecast", "Vintage default"])

with tab1:
    fig = go.Figure()
    fig.add_bar(
        x=co["month"],
        y=co["revenue"] / 1e6,
        marker_color=[GREY if not f else BLUE for f in co["is_forecast"]],
    )
    fig.update_layout(
        title=dict(text="Revenue ($M) — grey actual, blue forecast", font=dict(color=NAVY, size=16)),
        height=300,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor="#fff",
        paper_bgcolor="#fff",
        yaxis=dict(gridcolor=LINE),
        xaxis=dict(dtick=3, tickangle=-45),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        fig2 = go.Figure()
        for product, color in zip(PRODUCTS, [NAVY, BLUE]):
            sl = monthly[monthly["product"] == product]
            fig2.add_scatter(x=sl["month"], y=sl["ending_clab"] / 1e6, name=product, line=dict(color=color))
        fig2.update_layout(
            title=dict(text="CLAB ($M)", font=dict(color=NAVY, size=16)),
            height=320,
            margin=dict(l=10, r=10, t=40, b=30),
            plot_bgcolor="#fff",
            paper_bgcolor="#fff",
            yaxis=dict(gridcolor=LINE),
            xaxis=dict(dtick=3),
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig2, use_container_width=True)
    with right:
        fig3 = go.Figure()
        for product, color in zip(PRODUCTS, [NAVY, BLUE]):
            sl = monthly[monthly["product"] == product]
            fig3.add_bar(x=sl["month"], y=sl["originations"] / 1e6, name=product, marker_color=color)
        fig3.update_layout(
            barmode="stack",
            title=dict(text="Originations ($M)", font=dict(color=NAVY, size=16)),
            height=320,
            margin=dict(l=10, r=10, t=40, b=30),
            plot_bgcolor="#fff",
            paper_bgcolor="#fff",
            yaxis=dict(gridcolor=LINE),
            xaxis=dict(dtick=3),
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig3, use_container_width=True)

    show = monthly[monthly["month"] == last_act["month"]][
        ["product", "applications", "approval_rate", "originations", "ending_clab", "revenue", "nco", "yield_ann", "default_rate"]
    ].copy()
    show["applications"] = show["applications"].round(0).astype(int)
    show["approval_rate"] = (show["approval_rate"] * 100).round(1)
    for c in ["originations", "ending_clab", "revenue", "nco"]:
        show[c] = (show[c] / 1e6).round(2)
    show["yield_ann"] = (show["yield_ann"] * 100).round(0)
    show["default_rate"] = (show["default_rate"] * 100).round(1)
    st.dataframe(show, use_container_width=True, hide_index=True)
    st.caption("Applications x approval x ticket = originations. Revenue = avg CLAB x yield. Default here is NCO / avg CLAB this month.")

with tab2:
    st.caption(
        "Each historical origination month is a vintage. We watch how much of that vintage charges off as it ages. "
        "Average those paths into a product curve. New forecast originations inherit that curve."
    )
    product = st.radio("Product", list(PRODUCTS), horizontal=True)
    t = triangle[triangle["product"] == product].copy()
    t["observed_cum"] = t.groupby("vintage")["observed_nco_rate"].cumsum()
    latest_vints = list(dict.fromkeys(t["vintage"].tolist()))[-8:]

    fig4 = go.Figure()
    for v in latest_vints:
        sl = t[t["vintage"] == v]
        fig4.add_scatter(
            x=sl["mob"],
            y=sl["observed_cum"] * 100,
            mode="lines",
            line=dict(color=GREY, width=1),
            name=v,
            opacity=0.7,
        )
    fit = t.drop_duplicates("mob").sort_values("mob")
    fig4.add_scatter(
        x=fit["mob"],
        y=fit["fitted_cum_default"] * 100,
        mode="lines+markers",
        line=dict(color=TEAL, width=3),
        name="Fitted overlay",
    )
    fig4.update_layout(
        title=dict(text=f"{product} — observed vintages vs fitted curve", font=dict(color=NAVY, size=16)),
        height=360,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor="#fff",
        paper_bgcolor="#fff",
        xaxis_title="Months on book",
        yaxis_title="Cumulative default %",
        yaxis=dict(gridcolor=LINE),
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig4, use_container_width=True)

    pivot = t[t["vintage"].isin(latest_vints)].pivot_table(
        index="vintage", columns="mob", values="observed_cum", aggfunc="last"
    )
    st.markdown("**Vintage triangle (cumulative default)**")
    st.dataframe((pivot * 100).round(1), use_container_width=True)
    st.caption("Grey lines are history. Teal line is what the forecast uses. Default slider shifts that teal curve.")
