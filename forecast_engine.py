"""Fast monthly forecast. Overlay curve in, not the loan tape."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

OVERLAY = Path(__file__).parent / "data" / "overlay_curve.csv"
PRODUCTS = {
    "CreditFresh": {"apps": 28000, "ticket": 1800.0, "approval": 0.22, "yield": 0.98, "term": 9},
    "MoneyKey": {"apps": 20000, "ticket": 700.0, "approval": 0.18, "yield": 1.52, "term": 5},
}
HIST = 12
FORECAST = 24
SEASON = np.array([1.00, 1.00, 1.04, 1.06, 1.12, 1.16, 0.88, 0.90, 1.00, 1.02, 1.04, 1.08] * 4)[: HIST + FORECAST]

def load_overlay():
    if OVERLAY.exists():
        df = pd.read_csv(OVERLAY)
        return {p: g.sort_values("mob")["cum_default"].to_numpy() for p, g in df.groupby("product")}
    return {
        "CreditFresh": np.array([0, 0.05, 0.09, 0.12, 0.14, 0.16, 0.17, 0.18, 0.19, 0.20]),
        "MoneyKey": np.array([0, 0.14, 0.23, 0.29, 0.33, 0.36]),
    }

def _inc(cum):
    return np.diff(np.concatenate([[0.0], cum]))

def run(apps_mult=1.0, approval_add=0.0, yield_add=0.0):
    curves = load_overlay()
    rows = []
    carry_clab = {}
    carry_ecl = {}
    vintages = []
    warmup = 12
    for product, spec in PRODUCTS.items():
        cum = np.clip(np.array(curves.get(product, [0.0, 0.2]), dtype=float), 0, 0.85)
        if len(cum) < spec["term"] + 1:
            cum = np.concatenate([cum, np.full(spec["term"] + 1 - len(cum), cum[-1] if len(cum) else 0.2)])
        cum = cum[: spec["term"] + 1]
        inc = np.clip(_inc(cum), 0, None)
        lifetime = float(cum[-1])
        rem = np.array([(spec["term"] - k) / spec["term"] for k in range(spec["term"] + 1)])
        carry_clab[product] = 0.0
        carry_ecl[product] = 0.0
        appr = min(max(spec["approval"] + approval_add, 0.05), 0.6)
        for t in range(-warmup, HIST + FORECAST):
            season = float(SEASON[(t + warmup) % len(SEASON)])
            apps = spec["apps"] * apps_mult * season
            orig = apps * appr * spec["ticket"]
            vintages.append({"product": product, "t0": t, "orig": orig, "term": spec["term"], "rem": rem, "inc": inc, "cum": cum, "lifetime": lifetime})
    for t in range(HIST + FORECAST):
        for product, spec in PRODUCTS.items():
            yld = max(spec["yield"] + yield_add, 0.05)
            apps = orig = nco = clab = pll = 0.0
            for v in vintages:
                if v["product"] != product:
                    continue
                k = t - v["t0"]
                if k < 0 or k > v["term"]:
                    continue
                if k == 0:
                    apps = PRODUCTS[product]["apps"] * apps_mult * float(SEASON[t])
                    orig = v["orig"]
                    pll = orig * v["lifetime"]
                nco += v["orig"] * v["rem"][k] * v["inc"][k]
                clab += v["orig"] * v["rem"][k] * max(1.0 - v["cum"][k], 0.0)
            start = carry_clab[product]
            avg = 0.5 * (start + clab) if start else clab
            ecl_end = max(carry_ecl[product] + pll - nco, 0.0)
            carry_clab[product] = clab
            carry_ecl[product] = ecl_end
            rows.append({"month_idx": t, "product": product, "is_forecast": t >= HIST, "applications": apps, "approval_rate": min(max(spec["approval"] + approval_add, 0.05), 0.6), "ticket": spec["ticket"], "originations": orig, "ending_clab": clab, "avg_clab": avg, "yield_ann": yld, "revenue": avg * yld / 12.0, "pll": pll, "nco": nco, "ending_ecl": ecl_end})
    df = pd.DataFrame(rows)
    months = pd.period_range("2025-07", periods=HIST + FORECAST, freq="M")
    df["month"] = df["month_idx"].map(lambda i: str(months[i]))
    return df

def company_pack(df):
    g = df.groupby(["month", "month_idx", "is_forecast"], as_index=False).agg(applications=("applications", "sum"), originations=("originations", "sum"), ending_clab=("ending_clab", "sum"), avg_clab=("avg_clab", "sum"), revenue=("revenue", "sum"), pll=("pll", "sum"), nco=("nco", "sum"), ending_ecl=("ending_ecl", "sum"))
    g["yield_ann"] = np.where(g["avg_clab"] > 0, g["revenue"] / g["avg_clab"] * 12, 0.0)
    return g.sort_values("month_idx")
