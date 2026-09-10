"""Build 24 months of illustrative product-level actuals.

Not Propel's books. Totals are scaled to sit near publicly reported
quarterly ranges so the demo feels like their shape, not their file.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

MONTHS = pd.period_range("2024-07", "2026-06", freq="M")

PRODUCTS = {
    "CreditFresh": {
        "start_clab": 260_000_000,
        "ticket": 1800,
        "term": 9,
        "yield": 0.98,
        "nco_m": 0.032,
        "orig_base": 20_000_000,
        "orig_growth": 0.008,
        "from_month": "2024-07",
    },
    "MoneyKey": {
        "start_clab": 120_000_000,
        "ticket": 700,
        "term": 5,
        "yield": 1.52,
        "nco_m": 0.055,
        "orig_base": 11_000_000,
        "orig_growth": 0.006,
        "from_month": "2024-07",
    },
    "Fora": {
        "start_clab": 22_000_000,
        "ticket": 2000,
        "term": 12,
        "yield": 0.40,
        "nco_m": 0.014,
        "orig_base": 2_000_000,
        "orig_growth": 0.015,
        "from_month": "2024-07",
    },
    "QuidMarket": {
        "start_clab": 0,
        "ticket": 850,
        "term": 5,
        "yield": 1.15,
        "nco_m": 0.034,
        "orig_base": 5_500_000,
        "orig_growth": 0.028,
        "from_month": "2024-11",
    },
}

LAAS_FEE_RATE = 0.09
LAAS_ORIG_START = 2_000_000
LAAS_ORIG_GROWTH = 0.08


def month_season(i: int) -> float:
    m = (i % 12) + 1
    if m in (1, 2):
        return 0.90
    if m in (11, 12):
        return 1.12
    if m == 6:
        return 1.06
    return 1.00


def main() -> pd.DataFrame:
    rows = []
    clab = {p: spec["start_clab"] for p, spec in PRODUCTS.items()}

    for i, month in enumerate(MONTHS):
        season = month_season(i)
        for product, spec in PRODUCTS.items():
            live = str(month) >= spec["from_month"]
            if not live:
                rows.append(
                    {
                        "month": str(month),
                        "product": product,
                        "on_book": True,
                        "customers_new": 0,
                        "originations": 0.0,
                        "paydowns": 0.0,
                        "nco": 0.0,
                        "ending_clab": 0.0,
                        "avg_clab": 0.0,
                        "yield_ann": spec["yield"],
                        "revenue": 0.0,
                        "laas_fees": 0.0,
                        "is_forecast": False,
                    }
                )
                continue

            orig = spec["orig_base"] * ((1 + spec["orig_growth"]) ** i) * season
            if product == "QuidMarket":
                months_live = i - list(MONTHS).index(pd.Period("2024-11"))
                orig = spec["orig_base"] * ((1 + spec["orig_growth"]) ** max(months_live, 0)) * season

            customers = int(round(orig / spec["ticket"]))
            start = clab[product]
            nco = start * spec["nco_m"] * (0.95 + 0.08 * (season - 1))
            paydown = start * (1.0 / spec["term"]) * 0.55
            end = max(start + orig - paydown - nco, 0.0)
            avg = 0.5 * (start + end)
            rev = avg * spec["yield"] / 12.0
            clab[product] = end
            rows.append(
                {
                    "month": str(month),
                    "product": product,
                    "on_book": True,
                    "customers_new": customers,
                    "originations": orig,
                    "paydowns": paydown,
                    "nco": nco,
                    "ending_clab": end,
                    "avg_clab": avg,
                    "yield_ann": spec["yield"],
                    "revenue": rev,
                    "laas_fees": 0.0,
                    "is_forecast": False,
                }
            )

        laas_orig = LAAS_ORIG_START * ((1 + LAAS_ORIG_GROWTH) ** i) * season
        laas_fees = laas_orig * LAAS_FEE_RATE
        rows.append(
            {
                "month": str(month),
                "product": "LaaS",
                "on_book": False,
                "customers_new": int(round(laas_orig / 1500)),
                "originations": laas_orig,
                "paydowns": 0.0,
                "nco": 0.0,
                "ending_clab": 0.0,
                "avg_clab": 0.0,
                "yield_ann": 0.0,
                "revenue": laas_fees,
                "laas_fees": laas_fees,
                "is_forecast": False,
            }
        )

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "monthly_actuals.csv", index=False)
    print("Wrote", OUT / "monthly_actuals.csv")


if __name__ == "__main__":
    main()
