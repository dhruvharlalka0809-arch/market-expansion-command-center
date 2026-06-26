from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).parent / ".packages"
if PACKAGE_DIR.exists():
    sys.path.insert(0, str(PACKAGE_DIR))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.model import Assumptions, build_strategy_memo, format_currency, score_markets


BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "sample_markets.csv"


st.set_page_config(
    page_title="AI Market Expansion Command Center",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    :root {
        --ink: #17202a;
        --muted: #5d6d7e;
        --line: #d8dee6;
        --blue: #2563eb;
        --green: #0f766e;
        --amber: #b45309;
        --surface: #ffffff;
        --soft: #f6f8fb;
    }
    .stApp {
        background: linear-gradient(180deg, #f7f9fc 0%, #eef3f8 100%);
        color: var(--ink);
    }
    h1, h2, h3 { letter-spacing: 0 !important; color: var(--ink); }
    h1 { font-size: 2.1rem !important; margin-bottom: 0.1rem !important; }
    h2 { font-size: 1.25rem !important; margin-top: 1.35rem !important; }
    div[data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 8px 20px rgba(23,32,42,0.04);
    }
    div[data-testid="stMetricLabel"] p {
        color: var(--muted);
        font-size: 0.85rem;
    }
    div[data-testid="stMetricValue"] {
        color: var(--ink);
        font-size: 1.45rem;
    }
    .section {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 18px;
        margin-top: 12px;
        box-shadow: 0 8px 20px rgba(23,32,42,0.04);
    }
    .memo {
        background: #fbfcfe;
        border-left: 4px solid var(--blue);
        padding: 16px 18px;
        border-radius: 6px;
        color: var(--ink);
    }
    .small-note {
        color: var(--muted);
        font-size: 0.88rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_markets() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


st.title("AI Market Expansion Command Center")
st.caption("Decision model for market entry prioritization, pipeline forecasting, financial viability, and executive recommendations.")

raw_markets = load_markets()

with st.sidebar:
    st.header("Assumptions")
    setup_cost = st.number_input("Setup cost", min_value=0, max_value=500000, value=85000, step=5000, format="%d")
    annual_fixed_cost = st.number_input("Annual fixed cost", min_value=0, max_value=300000, value=42000, step=3000, format="%d")
    marketing_budget = st.number_input("Marketing budget", min_value=0, max_value=250000, value=24000, step=2000, format="%d")
    target_payback = st.slider("Target payback months", min_value=6, max_value=36, value=18, step=1)
    region_filter = st.multiselect(
        "Region",
        options=sorted(raw_markets["region"].unique()),
        default=sorted(raw_markets["region"].unique()),
    )
    confidence_floor = st.slider("Minimum data confidence", min_value=0.50, max_value=0.95, value=0.60, step=0.01)

    st.divider()
    st.caption("Scoring weights")
    weights_view = pd.DataFrame(
        {
            "Driver": [
                "Market size",
                "Growth",
                "Profitability",
                "Pipeline",
                "Strategic fit",
                "Channel access",
                "Risk",
                "Confidence",
            ],
            "Weight": ["18%", "14%", "18%", "14%", "12%", "10%", "10%", "4%"],
        }
    )
    st.dataframe(weights_view, use_container_width=True, hide_index=True)

assumptions = Assumptions(
    setup_cost=float(setup_cost),
    annual_fixed_cost=float(annual_fixed_cost),
    marketing_budget=float(marketing_budget),
    target_payback_months=int(target_payback),
)

filtered = raw_markets[
    raw_markets["region"].isin(region_filter) & (raw_markets["data_confidence"] >= confidence_floor)
].copy()

if filtered.empty:
    st.error("No markets match the selected filters.")
    st.stop()

scored = score_markets(filtered, assumptions)
top = scored.iloc[0]

metric_cols = st.columns(5)
metric_cols[0].metric("Top Market", top["market"], f"{top['market_score']:.1f}/100")
metric_cols[1].metric("12M Revenue", money(top["forecast_revenue"]), f"{top['expected_customers']:.1f} expected wins")
metric_cols[2].metric("Net Contribution", money(top["net_contribution"]), pct(top["avg_contract_margin_pct"]))
metric_cols[3].metric("Payback", f"{top['payback_months']:.1f} mo", f"Target {assumptions.target_payback_months} mo")
metric_cols[4].metric("Risk Index", f"{top['risk_index']:.1f}/10", f"Confidence {top['data_confidence']:.0%}")

left, right = st.columns([1.35, 1])

with left:
    st.subheader("Market Priority Ranking")
    ranking = scored[["market", "market_score", "recommendation_tier", "forecast_revenue", "net_contribution", "payback_months"]]
    fig_rank = px.bar(
        ranking,
        x="market_score",
        y="market",
        color="recommendation_tier",
        orientation="h",
        text=ranking["market_score"].map(lambda x: f"{x:.1f}"),
        color_discrete_map={
            "Enter Now": "#0f766e",
            "Prioritize": "#2563eb",
            "Test": "#b45309",
            "Watch": "#64748b",
        },
        labels={"market_score": "Market score", "market": ""},
    )
    fig_rank.update_layout(height=360, margin=dict(l=10, r=20, t=10, b=20), legend_title_text="")
    fig_rank.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig_rank, use_container_width=True)

with right:
    st.subheader("Score Drivers")
    driver_cols = [
        "market_size_score",
        "growth_score",
        "profitability_score",
        "pipeline_score",
        "strategic_fit_score",
        "channel_access_score",
        "risk_score",
        "confidence_score",
    ]
    driver_labels = [
        "Market Size",
        "Growth",
        "Profitability",
        "Pipeline",
        "Strategic Fit",
        "Channel Access",
        "Risk",
        "Confidence",
    ]
    radar = go.Figure()
    for _, row in scored.head(3).iterrows():
        radar.add_trace(
            go.Scatterpolar(
                r=[row[c] * 100 for c in driver_cols],
                theta=driver_labels,
                fill="toself",
                name=row["market"],
            )
        )
    radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=360,
        margin=dict(l=20, r=20, t=10, b=20),
        legend=dict(orientation="h", y=-0.1),
    )
    st.plotly_chart(radar, use_container_width=True)

finance_col, pipeline_col = st.columns(2)

with finance_col:
    st.subheader("Financial Viability")
    finance_view = scored.sort_values("net_contribution", ascending=False)
    fig_finance = go.Figure()
    fig_finance.add_bar(
        x=finance_view["market"],
        y=finance_view["gross_profit"],
        name="Gross profit",
        marker_color="#0f766e",
    )
    fig_finance.add_bar(
        x=finance_view["market"],
        y=finance_view["market_entry_cost"],
        name="Entry cost",
        marker_color="#b45309",
    )
    fig_finance.update_layout(
        barmode="group",
        yaxis_title="USD",
        height=360,
        margin=dict(l=10, r=20, t=10, b=20),
        legend=dict(orientation="h", y=1.08),
    )
    st.plotly_chart(fig_finance, use_container_width=True)

with pipeline_col:
    st.subheader("Sales Pipeline Forecast")
    pipeline_view = scored[["market", "leads", "expected_customers", "forecast_revenue", "sales_cycle_days"]]
    fig_pipeline = px.scatter(
        pipeline_view,
        x="expected_customers",
        y="forecast_revenue",
        size="leads",
        color="sales_cycle_days",
        text="market",
        color_continuous_scale="Tealrose",
        labels={
            "expected_customers": "Expected wins",
            "forecast_revenue": "Forecast revenue",
            "sales_cycle_days": "Sales cycle days",
        },
    )
    fig_pipeline.update_traces(textposition="top center")
    fig_pipeline.update_layout(height=360, margin=dict(l=10, r=20, t=10, b=20))
    st.plotly_chart(fig_pipeline, use_container_width=True)

st.subheader("Market Detail")
detail = scored[
    [
        "market",
        "region",
        "sam_m",
        "expected_growth_pct",
        "forecast_revenue",
        "gross_profit",
        "net_contribution",
        "payback_months",
        "risk_index",
        "data_confidence",
        "recommendation_tier",
    ]
].copy()
detail["sam_m"] = detail["sam_m"].map(lambda x: f"${x:,.0f}M")
detail["expected_growth_pct"] = detail["expected_growth_pct"].map(lambda x: f"{x:.1f}%")
detail["forecast_revenue"] = detail["forecast_revenue"].map(format_currency)
detail["gross_profit"] = detail["gross_profit"].map(format_currency)
detail["net_contribution"] = detail["net_contribution"].map(format_currency)
detail["payback_months"] = detail["payback_months"].map(lambda x: f"{x:.1f}")
detail["risk_index"] = detail["risk_index"].map(lambda x: f"{x:.1f}/10")
detail["data_confidence"] = detail["data_confidence"].map(lambda x: f"{x:.0%}")
st.dataframe(detail, use_container_width=True, hide_index=True)

st.subheader("Executive Memo")
st.markdown(f"<div class='memo'>{build_strategy_memo(scored, assumptions).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

st.markdown(
    "<p class='small-note'>Sample data for portfolio demonstration. Replace the CSV with real CRM, finance, logistics, and market research inputs before making live decisions.</p>",
    unsafe_allow_html=True,
)
