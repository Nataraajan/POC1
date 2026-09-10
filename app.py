"""Product revenue dashboard — same visual language as the SaaS revenue tool."""

import plotly.graph_objects as go
import streamlit as st

from revenue_model import company_pack, forecast, load_actuals

st.set_page_config(page_title="Product Revenue Model", layout="wide")

NAVY = "#163A63"
LINE = "#E2E8F0"
BLUE = "#2563EB"
GREY = "#94A3B8"

PRODUCT_COLORS = {
    "CreditFresh": "#163A63",
    "MoneyKey": "#2563EB",
    "Fora": "#0F766E",
    "QuidMarket": "#7C3AED",
    "LaaS": "#D97706",
}

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
h1.main-title { color: #163A63 !important; font-weight: 700 !important; font-size: 28px !important; line-height: 1.15 !important; margin-bottom: 2px !important; }
.header-block { margin-bottom: 12px; padding-bottom: 12px; border-bottom: 2px solid #E2E8F0; }
.header-block .tagline { color: #64748B; font-size: 13px; line-height: 1.4; margin: 0; }
div[data-testid="stMetric"] { background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important; border-radius: 10px !important; padding: 16px 20px !important; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important; }
div[data-testid="stMetricLabel"] p { font-size: 12px !important; color: #64748B !important; font-weight: 500 !important; }
div[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 700 !important; color: #172033 !important; }
.stSlider label p { font-size: 12px !important; font-weight: 500 !important; color: #334155 !important; }
.stMainBlockContainer { padding-top: 1rem !important; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="header-block">
  <h1 class="main-title">Product Revenue Model</h1>
  <p class="tagline">Illustrative 24-month book by product. Actuals are locked. Forecast moves drivers only. Not Propel data.</p>
</div>
""",
    unsafe_allow_html=True,
)

actuals = load_actuals()

with st.sidebar:
    st.markdown("**Forecast drivers**")
    horizon = st.slider("Horizon (months)", 3, 12, 6)
    orig_g = st.slider("Origination growth add", -0.03, 0.05, 0.00, 0.005, format="%.3f")
    def_add = st.slider("Default / NCO add", 0.00, 0.03, 0.00, 0.002, format="%.3f")
    yld_add = st.slider("Yield add (annual)", -0.20, 0.20, 0.00, 0.02, format="%.2f")
    st.caption("Starts from last-three-month product rates.")

book = forecast(actuals, months=horizon, orig_growth_add=orig_g, default_add=def_add, yield_add=yld_add)
base = forecast(actuals, months=horizon)
co = company_pack(book)
co_base = company_pack(base)
last_act = co[~co["is_forecast"]].iloc[-1]
last_fc = co[co["is_forecast"]].iloc[-1]
base_end = co_base[co_base["is_forecast"]].iloc[-1]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Ending CLAB", f"${last_act['ending_clab']/1e6:.0f}M")
c2.metric("Last month revenue", f"${last_act['revenue']/1e6:.1f}M")
c3.metric("New customers", f"{int(last_act['customers_new']):,}")
c4.metric("On-book yield", f"{last_act['yield_ann']*100:.0f}%")
c5.metric(
    "Forecast CLAB",
    f"${last_fc['ending_clab']/1e6:.0f}M",
    delta=f"{(last_fc['ending_clab']-base_end['ending_clab'])/1e6:+.1f}M vs base",
)

fig = go.Figure()
fig.add_bar(
    x=co["month"].astype(str),
    y=co["revenue"] / 1e6,
    marker_color=[GREY if not f else BLUE for f in co["is_forecast"]],
    name="Revenue",
)
fig.update_layout(
    title=dict(text="Revenue ($M)", font=dict(color=NAVY, size=16)),
    height=320,
    margin=dict(l=10, r=10, t=40, b=10),
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="#FFFFFF",
    yaxis=dict(gridcolor=LINE, title=None),
    xaxis=dict(tickangle=-45),
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    fig2 = go.Figure()
    onbook = book[book["on_book"]]
    for product, color in PRODUCT_COLORS.items():
        sl = onbook[onbook["product"] == product]
        if sl.empty:
            continue
        fig2.add_scatter(
            x=sl["month"].astype(str),
            y=sl["ending_clab"] / 1e6,
            stackgroup="clab",
            name=product,
            line=dict(color=color, width=0.5),
            fillcolor=color,
        )
    fig2.update_layout(
        title=dict(text="CLAB by product ($M)", font=dict(color=NAVY, size=16)),
        height=340,
        margin=dict(l=10, r=10, t=40, b=40),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        yaxis=dict(gridcolor=LINE),
        legend=dict(orientation="h", y=-0.22),
    )
    st.plotly_chart(fig2, use_container_width=True)

with right:
    fig3 = go.Figure()
    for product, color in PRODUCT_COLORS.items():
        sl = book[book["product"] == product]
        fig3.add_bar(
            x=sl["month"].astype(str),
            y=sl["revenue"] / 1e6,
            name=product,
            marker_color=color,
        )
    fig3.update_layout(
        barmode="stack",
        title=dict(text="Revenue by product ($M)", font=dict(color=NAVY, size=16)),
        height=340,
        margin=dict(l=10, r=10, t=40, b=40),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        yaxis=dict(gridcolor=LINE),
        legend=dict(orientation="h", y=-0.22),
    )
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("**Last actual month**")
last_m = actuals["month"].max()
show = actuals[actuals["month"] == last_m][
    ["product", "on_book", "customers_new", "originations", "ending_clab", "revenue", "nco", "yield_ann"]
].copy()
show["originations"] = (show["originations"] / 1e6).round(1)
show["ending_clab"] = (show["ending_clab"] / 1e6).round(1)
show["revenue"] = (show["revenue"] / 1e6).round(2)
show["nco"] = (show["nco"] / 1e6).round(2)
show["yield_ann"] = (show["yield_ann"] * 100).round(0)
show = show.rename(
    columns={
        "customers_new": "new customers",
        "originations": "orig $M",
        "ending_clab": "CLAB $M",
        "revenue": "rev $M",
        "nco": "NCO $M",
        "yield_ann": "yield %",
    }
)
st.dataframe(show, use_container_width=True, hide_index=True)
st.caption("On-book revenue = average CLAB × yield. LaaS is a fee and is not in CLAB.")
