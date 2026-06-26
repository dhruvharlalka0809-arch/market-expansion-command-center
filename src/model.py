from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict

import pandas as pd


WEIGHTS: Dict[str, float] = {
    "market_size": 0.18,
    "growth": 0.14,
    "profitability": 0.18,
    "pipeline": 0.14,
    "strategic_fit": 0.12,
    "channel_access": 0.10,
    "risk": 0.10,
    "confidence": 0.04,
}


@dataclass(frozen=True)
class Assumptions:
    setup_cost: float = 85000
    annual_fixed_cost: float = 42000
    marketing_budget: float = 24000
    planning_horizon_months: int = 12
    target_payback_months: int = 18


def format_currency(value: float) -> str:
    rounded = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"${rounded:,.0f}"


def _normalize(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    minimum = series.min()
    maximum = series.max()
    if maximum == minimum:
        return pd.Series([0.5] * len(series), index=series.index)
    score = (series - minimum) / (maximum - minimum)
    return score if higher_is_better else 1 - score


def score_markets(markets: pd.DataFrame, assumptions: Assumptions) -> pd.DataFrame:
    df = markets.copy()

    df["sam_m"] = df["tam_m"] * df["serviceable_share_pct"] / 100
    df["expected_customers"] = df["leads"] * df["qualified_rate"] * df["win_rate"]
    df["forecast_revenue"] = df["expected_customers"] * df["avg_contract_value"]
    df["gross_profit"] = df["forecast_revenue"] * df["avg_contract_margin_pct"]
    df["market_entry_cost"] = assumptions.setup_cost + assumptions.annual_fixed_cost + assumptions.marketing_budget
    df["net_contribution"] = df["gross_profit"] - df["market_entry_cost"]
    df["payback_months"] = df["market_entry_cost"] / (df["gross_profit"] / 12)
    df["payback_months"] = df["payback_months"].replace([float("inf"), -float("inf")], 999)

    df["unit_margin_pct"] = (df["expected_price_per_unit"] - df["unit_cogs"]) / df["expected_price_per_unit"]
    df["landed_cost_pct"] = df["logistics_cost_pct"] + df["tariff_pct"]
    df["risk_index"] = (
        df["competition_intensity"] * 0.25
        + df["regulatory_complexity"] * 0.25
        + df["fx_risk"] * 0.20
        + _normalize(df["payment_cycle_days"], higher_is_better=False).rsub(1) * 10 * 0.15
        + _normalize(df["landed_cost_pct"], higher_is_better=False).rsub(1) * 10 * 0.15
    )

    df["market_size_score"] = _normalize(df["sam_m"])
    df["growth_score"] = _normalize(df["expected_growth_pct"])
    df["profitability_score"] = _normalize(df["net_contribution"])
    df["pipeline_score"] = _normalize(df["forecast_revenue"])
    df["strategic_fit_score"] = df["strategic_fit"] / 10
    df["channel_access_score"] = df["channel_access"] / 10
    df["risk_score"] = _normalize(df["risk_index"], higher_is_better=False)
    df["confidence_score"] = df["data_confidence"]

    df["market_score"] = (
        df["market_size_score"] * WEIGHTS["market_size"]
        + df["growth_score"] * WEIGHTS["growth"]
        + df["profitability_score"] * WEIGHTS["profitability"]
        + df["pipeline_score"] * WEIGHTS["pipeline"]
        + df["strategic_fit_score"] * WEIGHTS["strategic_fit"]
        + df["channel_access_score"] * WEIGHTS["channel_access"]
        + df["risk_score"] * WEIGHTS["risk"]
        + df["confidence_score"] * WEIGHTS["confidence"]
    ) * 100

    df["recommendation_tier"] = pd.cut(
        df["market_score"],
        bins=[0, 55, 70, 85, 100],
        labels=["Watch", "Test", "Prioritize", "Enter Now"],
        include_lowest=True,
    )
    return df.sort_values("market_score", ascending=False).reset_index(drop=True)


def build_strategy_memo(scored: pd.DataFrame, assumptions: Assumptions) -> str:
    top = scored.iloc[0]
    second = scored.iloc[1] if len(scored) > 1 else top
    payback_view = (
        f"{top.payback_months:.1f} months"
        if top.payback_months < 60
        else "outside the current planning horizon"
    )

    risk_note = "manageable" if top.risk_index <= scored["risk_index"].median() else "above-average"
    return f"""# Market Entry Recommendation: {top.market}

## Decision
Prioritize {top.market} as the next expansion market. It ranks first with a market score of {top.market_score:.1f}/100, ahead of {second.market} at {second.market_score:.1f}/100.

## Why This Market Wins
- Serviceable market: ${top.sam_m:,.0f}M from a ${top.tam_m:,.0f}M TAM.
- Revenue potential: {format_currency(top.forecast_revenue)} in modeled 12-month pipeline value.
- Gross profit: {format_currency(top.gross_profit)} before market entry costs.
- Profit potential: {format_currency(top.net_contribution)} net contribution after setup, fixed, and marketing costs.
- Payback: {payback_view} against a target of {assumptions.target_payback_months} months.
- Commercial access: {top.channel_access:.0f}/10 channel access and {top.strategic_fit:.0f}/10 strategic fit.

## Main Risk
The market carries a {risk_note} risk profile. The biggest watch items are competition intensity, regulation, logistics cost, tariff exposure, FX risk, and payment cycle length.

## Recommended Next Steps
1. Validate 15-20 priority buyers and confirm buying triggers.
2. Run a 30-day outbound test using 2-3 value propositions.
3. Negotiate logistics and payment terms before scaling.
4. Convert this model into a weekly operating dashboard once the first live opportunities enter CRM.
"""
