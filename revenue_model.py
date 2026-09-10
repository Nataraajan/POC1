"""Forecast from the 24-month product file.

Actuals stay frozen. Forecast months apply product-level drivers:
originations growth, yield, nco rate, paydown rate.
LaaS stays off-book: fee = originations × fee rate.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent / "data" / "monthly_actuals.csv"


def load_actuals() -> pd.DataFrame:
    df = pd.read_csv(DATA)
    df["month"] = pd.PeriodIndex(df["month"], freq="M")
    return df


def last_rates(actuals: pd.DataFrame) -> pd.DataFrame:
    tail = actuals[actuals["month"] >= actuals["month"].max() - 2]
    rows = []
    for product, g in tail.groupby("product"):
        on_book = bool(g["on_book"].iloc[-1])
        avg_clab = g["avg_clab"].replace(0, pd.NA)
        nco_rate = float((g["nco"] / avg_clab).median()) if on_book else 0.0
        pay_rate = float((g["paydowns"] / avg_clab).median()) if on_book else 0.0
        if pd.isna(nco_rate):
            nco_rate = 0.0
        if pd.isna(pay_rate):
            pay_rate = 0.0
        orig_growth = 0.0
        o = g.sort_values("month")["originations"].tolist()
        if len(o) >= 2 and o[0]:
            orig_growth = (o[-1] / o[0]) ** (1 / (len(o) - 1)) - 1
        rows.append(
            {
                "product": product,
                "on_book": on_book,
                "yield_ann": float(g["yield_ann"].iloc[-1]),
                "nco_rate": nco_rate,
                "paydown_rate": pay_rate,
                "orig_growth": max(min(orig_growth, 0.04), -0.02),
                "fee_rate": float((g["laas_fees"] / g["originations"]).median()) if not on_book else 0.0,
                "ticket": float((g["originations"] / g["customers_new"].replace(0, pd.NA)).median())
                if g["customers_new"].sum()
                else 1000.0,
            }
        )
    return pd.DataFrame(rows)


def forecast(
    actuals: pd.DataFrame,
    months: int = 6,
    orig_growth_add: float = 0.0,
    default_add: float = 0.0,
    yield_add: float = 0.0,
) -> pd.DataFrame:
    rates = last_rates(actuals)
    last_month = actuals["month"].max()
    last_slice = actuals[actuals["month"] == last_month].set_index("product")
    frames = [actuals.copy()]
    clab = last_slice["ending_clab"].to_dict()
    last_orig = last_slice["originations"].to_dict()

    for step in range(1, months + 1):
        m = last_month + step
        for _, r in rates.iterrows():
            p = r["product"]
            orig = last_orig[p] * ((1 + r["orig_growth"] + orig_growth_add) ** step)
            if r["on_book"]:
                start = clab[p]
                nco = start * max(r["nco_rate"] + default_add, 0.0)
                pay = start * r["paydown_rate"]
                end = max(start + orig - pay - nco, 0.0)
                avg = 0.5 * (start + end)
                yld = max(r["yield_ann"] + yield_add, 0.05)
                rev = avg * yld / 12.0
                clab[p] = end
                rows = {
                    "month": m,
                    "product": p,
                    "on_book": True,
                    "customers_new": int(round(orig / max(r["ticket"], 1))),
                    "originations": orig,
                    "paydowns": pay,
                    "nco": nco,
                    "ending_clab": end,
                    "avg_clab": avg,
                    "yield_ann": yld,
                    "revenue": rev,
                    "laas_fees": 0.0,
                    "is_forecast": True,
                }
            else:
                fee_rate = r["fee_rate"] if r["fee_rate"] == r["fee_rate"] else 0.09
                fees = orig * fee_rate
                rows = {
                    "month": m,
                    "product": p,
                    "on_book": False,
                    "customers_new": int(round(orig / max(r["ticket"], 1))),
                    "originations": orig,
                    "paydowns": 0.0,
                    "nco": 0.0,
                    "ending_clab": 0.0,
                    "avg_clab": 0.0,
                    "yield_ann": 0.0,
                    "revenue": fees,
                    "laas_fees": fees,
                    "is_forecast": True,
                }
            frames.append(pd.DataFrame([rows]))

    out = pd.concat(frames, ignore_index=True)
    if "is_forecast" not in actuals.columns:
        out["is_forecast"] = out["is_forecast"].fillna(False)
    out["is_forecast"] = out["is_forecast"].fillna(False).astype(bool)
    return out


def company_pack(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["month", "is_forecast"], as_index=False).agg(
        originations=("originations", "sum"),
        customers_new=("customers_new", "sum"),
        ending_clab=("ending_clab", "sum"),
        avg_clab=("avg_clab", "sum"),
        revenue=("revenue", "sum"),
        nco=("nco", "sum"),
        laas_fees=("laas_fees", "sum"),
        onbook_orig=("originations", "sum"),
    )
    onbook = (
        df[df["on_book"]]
        .groupby("month", as_index=False)["originations"]
        .sum()
        .rename(columns={"originations": "onbook_originations"})
    )
    g = g.merge(onbook, on="month", how="left")
    g["yield_ann"] = g.apply(
        lambda r: (r["revenue"] - r["laas_fees"]) / r["avg_clab"] * 12 if r["avg_clab"] else 0.0,
        axis=1,
    )
    return g.sort_values("month")
