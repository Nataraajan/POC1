"""Loan-level vintage analysis.
Collapse millions of loans to a curve. Forecast imports the curve.
"""
from __future__ import annotations
from pathlib import Path
from time import perf_counter
import numpy as np
import pandas as pd
from model import HIST_MONTHS, HIST_START, PRODUCTS, default_curve

OVERLAY = Path(__file__).parent / "data" / "overlay_curve.csv"

def _draw_default_mob(n, curve, rng):
    inc = np.diff(np.concatenate([[0.0], curve]))
    inc = np.clip(inc, 0, None)
    survive = max(1.0 - curve[-1], 0.0)
    p = np.concatenate([inc, [survive]])
    p = p / p.sum()
    return rng.choice(np.arange(len(p)), size=n, p=p)

def analyze_loans(customers_per_month=20000, seed=7):
    t0 = perf_counter()
    rng = np.random.default_rng(seed)
    months = pd.period_range(HIST_START, periods=HIST_MONTHS, freq="M")
    mix = {"CreditFresh": 0.58, "MoneyKey": 0.42}
    parts = []
    for product, spec in PRODUCTS.items():
        curve = default_curve(spec["term"], spec["lifetime_default"])
        n_m = max(int(customers_per_month * mix[product]), 1)
        for i, vintage in enumerate(months):
            n = n_m
            mob = _draw_default_mob(n, curve, rng)
            defaulted = mob <= spec["term"]
            parts.append(pd.DataFrame({
                "loan_id": np.arange(n) + i * 10000000 + (0 if product == "CreditFresh" else 5000000),
                "product": product,
                "vintage": str(vintage),
                "ticket": spec["ticket"],
                "default_mob": np.where(defaulted, mob, -1),
            }))
    loans = pd.concat(parts, ignore_index=True)
    n_loans = len(loans)
    rows = []
    for product, spec in PRODUCTS.items():
        sl = loans[loans["product"] == product]
        orig = sl.groupby("vintage").size()
        for vintage, g in sl.groupby("vintage"):
            o = int(orig.loc[vintage])
            for k in range(spec["term"] + 1):
                nco = int((g["default_mob"] == k).sum())
                rows.append({"product": product, "vintage": vintage, "mob": k, "originations": o, "nco": nco, "nco_rate": nco / o if o else 0.0})
    triangle = pd.DataFrame(rows)
    triangle["observed_cum"] = triangle.groupby(["product", "vintage"])["nco_rate"].cumsum()
    overlay_rows = []
    curves = {}
    for product, spec in PRODUCTS.items():
        avg = triangle[triangle["product"] == product].groupby("mob")["nco_rate"].mean().reindex(range(spec["term"] + 1)).fillna(0.0)
        cum = avg.cumsum().clip(upper=0.85)
        curves[product] = cum.to_numpy()
        for k, val in cum.items():
            overlay_rows.append({"product": product, "mob": int(k), "cum_default": float(val)})
    overlay = pd.DataFrame(overlay_rows)
    OVERLAY.parent.mkdir(exist_ok=True)
    overlay.to_csv(OVERLAY, index=False)
    sample = loans.sample(min(15, len(loans)), random_state=seed).reset_index(drop=True)
    elapsed = perf_counter() - t0
    return {"n_loans": n_loans, "seconds": elapsed, "vintages": HIST_MONTHS, "products": 2, "curve_points": len(overlay), "sample": sample, "triangle": triangle, "overlay": overlay, "curves": curves}
