from pathlib import Path
import unittest

import pandas as pd

from src.model import Assumptions, build_strategy_memo, format_currency, score_markets


class MarketScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.markets = pd.read_csv(Path(__file__).resolve().parents[1] / "data" / "sample_markets.csv")

    def test_score_markets_ranks_highest_opportunity_first(self) -> None:
        scored = score_markets(self.markets, Assumptions())

        self.assertEqual(scored.iloc[0]["market"], "Saudi Arabia")
        self.assertTrue(scored["market_score"].is_monotonic_decreasing)
        self.assertTrue(scored["market_score"].between(0, 100).all())

    def test_financial_outputs_are_consistent_with_assumptions(self) -> None:
        assumptions = Assumptions(setup_cost=80_000, annual_fixed_cost=40_000, marketing_budget=20_000)
        scored = score_markets(self.markets, assumptions)
        top = scored.iloc[0]

        self.assertEqual(top["market_entry_cost"], 140_000)
        self.assertGreater(top["forecast_revenue"], 0)
        self.assertEqual(top["gross_profit"], top["forecast_revenue"] * top["avg_contract_margin_pct"])
        self.assertEqual(top["net_contribution"], top["gross_profit"] - top["market_entry_cost"])
        self.assertGreater(top["payback_months"], 0)

    def test_strategy_memo_uses_top_ranked_market(self) -> None:
        scored = score_markets(self.markets, Assumptions())
        memo = build_strategy_memo(scored, Assumptions())
        top = scored.iloc[0]

        self.assertTrue(memo.startswith("# Market Entry Recommendation: Saudi Arabia"))
        self.assertIn(f"Revenue potential: {format_currency(top['forecast_revenue'])}", memo)
        self.assertIn(f"Gross profit: {format_currency(top['gross_profit'])}", memo)
        self.assertIn(f"Profit potential: {format_currency(top['net_contribution'])}", memo)
        self.assertIn("Recommended Next Steps", memo)


if __name__ == "__main__":
    unittest.main()
