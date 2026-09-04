from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


class Tier1ExactMatcher:
    """Primary Tier 1 Matcher: Exact UTR/ID Match -> Amount within tolerance -> Date window check."""

    def match(
        self, pg_row: pd.Series, df_bank: pd.DataFrame, amount_tolerance: float, date_window_days: int, base_curr: str = "inr"
    ) -> Optional[Dict[str, Any]]:
        utr = pg_row["utr"]
        net_amt_base = pg_row[f"expected_net_{base_curr.lower()}"]
        pg_time = pg_row["timestamp"]

        utr_candidates = df_bank[df_bank["utr"] == utr]
        if utr_candidates.empty:
            return None

        credit_col = f"credit_amount_{base_curr.lower()}"
        amount_matches = utr_candidates[
            np.isclose(utr_candidates[credit_col], net_amt_base, atol=amount_tolerance)
        ]

        if not amount_matches.empty:
            for _, b_row in amount_matches.iterrows():
                time_diff_days = abs((b_row["timestamp"] - pg_time).total_seconds()) / 86400.0

                if time_diff_days <= date_window_days:
                    is_same_day = time_diff_days <= 1.0
                    tier_label = "Tier 1: Deterministic Exact Match" if is_same_day else f"Tier 1: Date-Shifted (T+{int(np.ceil(time_diff_days))} Days)"
                    match_type = "exact" if is_same_day else "rule-based"

                    return {
                        "transaction_id": pg_row["transaction_id"],
                        "bank_statement_id": b_row["bank_statement_id"],
                        "match_tier": tier_label,
                        "match_type_tag": match_type,
                        "confidence_score": 1.0 if is_same_day else 0.95,
                        "notes": f"Matched UTR {utr} within tolerance and {round(time_diff_days, 1)}-day window"
                    }

        return None