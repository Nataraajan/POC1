"""Two-product POC: applications to originations to CLAB to revenue,
with a vintage default overlay fitted from mock history.

Monthly engine. Quarterly is a view, not the calculation grain.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

PRODUCTS = {
    "CreditFresh": {
        "ticket": 1800.0,
        "term": 9,
        "yield": 0.98,
        "approval": 0.22,
        "apps_base": 55000,
        "lifetime_default": 0.20,
        "start_clab": 260000000,
    },
    "MoneyKey": {
        "ticket": 700.0,
        "term": 5,
        "yield": 1.52,
        "approval": 0.18,
        "apps_base": 48000,
        "lifetime_default": 0.36,
        "start_clab": 120000000,
    },
}

HIST_START = "2024-07"
HIST_MONTHS = 24
FORECAST_MONTHS = 24
SEASON = {1: 0.88, 2: 0.90, 3: 1.00, 4: 1.02, 5: 1.04, 6: 1.08, 7: 1.00, 8: 1.00, 9: 1.04, 10: 1.06, 11: 1.12, 12: 1.16}


def season_of(period: pd.Period) -> float:
    return SEASON[int(period.month)]


def default_curve(term: int, lifetime_default: float) -> np.ndarray:
    x = np.arange(term + 1)
    raw = 1.0 - np.exp(-2.2 * x / max(term, 1))
    raw = raw / raw[-1] if raw[-1] else raw
    return lifetime_default * raw


def remaining_frac(term: int) -> np.ndarray:
    return np.array([(term - k) / term for k in range(term + 1)])


@dataclass
class Drivers:
    apps_growth: float = 0.0
    approval_add: float = 0.0
    yield_add: float = 0.0
    default_add: float = 0.0


def _build_history() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    months = pd.period_range(HIST_START, periods=HIST_MONTHS, freq="M")
    rows = []
    for product, spec in PRODUCTS.items():
        true = default_curve(spec["term"], spec["lifetime_default"])
        inc_true = np.diff(true, prepend=0.0)
        rem = remaining_frac(spec["term"])
        for i, orig_m in enumerate(months):
            apps = spec["apps_base"] * (1.008 ** i) * season_of(orig_m)
            originations = apps * spec["approval"] * spec["ticket"]
            for k in range(spec["term"] + 1):
                cal = orig_m + k
                if cal > months[-1]:
                    break
                noise = 1.0 + rng.normal(0, 0.08)
                inc = max(inc_true[k] * noise, 0.0)
                nco = originations * rem[k] * inc
                surv = max(1.0 - true[k] * noise, 0.05)
                rows.append(
                    {
                        "vintage": str(orig_m),
                        "month": str(cal),
                        "product": product,
                        "mob": k,
                        "applications": apps if k == 0 else 0.0,
                        "approval_rate": spec["approval"] if k == 0 else np.nan,
                        "originations": originations if k == 0 else 0.0,
                        "clab": originations * rem[k] * surv,
                        "nco": nco,
                        "is_history": True,
                    }
                )
    return pd.DataFrame(rows)


def fit_curves(history: pd.DataFrame) -> dict:
    fitted = {}
    for product, spec in PRODUCTS.items():
        h = history[(history["product"] == product) & (history["originations"] > 0)]
        orig = h.set_index("vintage")["originations"]
        g = history[history["product"] == product].copy()
        g["orig_v"] = g["vintage"].map(orig)
        g["nco_rate"] = np.where(g["orig_v"] > 0, g["nco"] / g["orig_v"], 0.0)
        avg_inc = g.groupby("mob")["nco_rate"].mean().reindex(range(spec["term"] + 1)).fillna(0.0)
        fitted[product] = avg_inc.cumsum().clip(upper=0.85).to_numpy()
    return fitted


def run(drivers: Drivers | None = None):
    drivers = drivers or Drivers()
    history = _build_history()
    curves = fit_curves(history)
    hist_months = pd.period_range(HIST_START, periods=HIST_MONTHS, freq="M")
    all_months = pd.period_range(HIST_START, periods=HIST_MONTHS + FORECAST_MONTHS, freq="M")
    warmup = pd.period_range(pd.Period(HIST_START, freq="M") - 12, periods=12, freq="M")
    monthly = []
    clab_carry = {p: 0.0 for p in PRODUCTS}
    vintages = []
    for product, spec in PRODUCTS.items():
        term = spec["term"]
        rem = remaining_frac(term)
        curve = np.clip(curves[product] + drivers.default_add, 0, 0.85)
        inc = np.clip(np.diff(np.concatenate([[0.0], curve])), 0, None)
        yld = spec["yield"] + drivers.yield_add
        appr = min(max(spec["approval"] + drivers.approval_add, 0.05), 0.6)
        seed_months = list(warmup) + list(all_months)
        for i, m in enumerate(seed_months):
            hist_i = i - len(warmup)
            is_fc = hist_i >= HIST_MONTHS
            if hist_i < 0:
                apps = spec["apps_base"] * season_of(m)
            elif is_fc:
                growth = (1 + drivers.apps_growth) ** (hist_i - HIST_MONTHS + 1)
                apps = spec["apps_base"] * (1.008 ** (HIST_MONTHS - 1)) * growth * season_of(m)
            else:
                apps = spec["apps_base"] * (1.008 ** hist_i) * season_of(m)
            vintages.append(
                {
                    "product": product,
                    "vintage": m,
                    "originations": apps * appr * spec["ticket"],
                    "applications": apps,
                    "approval_rate": appr,
                    "term": term,
                    "rem": rem,
                    "inc": inc,
                    "curve": curve,
                    "yield": yld,
                    "is_forecast": is_fc,
                }
            )
    for m in all_months:
        is_fc = m > hist_months[-1]
        for product, spec in PRODUCTS.items():
            apps = orig = nco = clab = 0.0
            appr = spec["approval"] + drivers.approval_add
            yld = spec["yield"] + drivers.yield_add
            for v in vintages:
                if v["product"] != product:
                    continue
                k = (m - v["vintage"]).n
                if k < 0 or k > v["term"]:
                    continue
                if k == 0:
                    apps = v["applications"]
                    appr = v["approval_rate"]
                    orig = v["originations"]
                nco += v["originations"] * v["rem"][k] * v["inc"][k]
                clab += v["originations"] * v["rem"][k] * max(1.0 - v["curve"][k], 0.0)
            start = clab_carry[product]
            avg = 0.5 * (start + clab) if start else clab
            clab_carry[product] = clab
            monthly.append(
                {
                    "month": str(m),
                    "product": product,
                    "is_forecast": is_fc,
                    "applications": apps,
                    "approval_rate": appr,
                    "originations": orig,
                    "ending_clab": clab,
                    "avg_clab": avg,
                    "nco": nco,
                    "default_rate": nco / avg if avg else 0.0,
                    "yield_ann": yld,
                    "revenue": avg * yld / 12.0,
                    "season": season_of(m),
                }
            )
    triangle_rows = []
    for product, spec in PRODUCTS.items():
        fitted = curves[product]
        h = history[history["product"] == product]
        orig_map = h[h["originations"] > 0].set_index("vintage")["originations"].to_dict()
        for vintage, g in h.groupby("vintage"):
            o = orig_map.get(vintage, 0.0)
            for _, r in g.iterrows():
                triangle_rows.append(
                    {
                        "product": product,
                        "vintage": vintage,
                        "mob": int(r["mob"]),
                        "observed_nco_rate": r["nco"] / o if o else 0.0,
                        "fitted_cum_default": fitted[int(r["mob"])] if int(r["mob"]) < len(fitted) else np.nan,
                    }
                )
    return pd.DataFrame(monthly), history, pd.DataFrame(triangle_rows), curves


def company_pack(monthly: pd.DataFrame) -> pd.DataFrame:
    g = monthly.groupby(["month", "is_forecast"], as_index=False).agg(
        applications=("applications", "sum"),
        originations=("originations", "sum"),
        ending_clab=("ending_clab", "sum"),
        avg_clab=("avg_clab", "sum"),
        nco=("nco", "sum"),
        revenue=("revenue", "sum"),
    )
    g["yield_ann"] = np.where(g["avg_clab"] > 0, g["revenue"] / g["avg_clab"] * 12, 0.0)
    g["default_rate"] = np.where(g["avg_clab"] > 0, g["nco"] / g["avg_clab"], 0.0)
    return g.sort_values("month")
