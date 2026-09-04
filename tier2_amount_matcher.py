from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


class Tier2AmountMatcher:
    """Primary Tier 2 Matcher: Evaluates gross vs net amount discrepancies and partial refunds."""

    def match(
        self, pg_row: pd.Series, df_bank: pd.DataFrame, amount_tolerance: float, base_curr: str = "inr"
    ) -> Optional[Dict[str, Any]]:
        utr = pg_row["utr"]
        gross_amt_base = pg_row[f"amount_{base_curr.lower()}"]
        net_amt_base = pg_row[f"expected_net_{base_curr.lower()}"]

        utr_matches = df_bank[df_bank["utr"] == utr]
        if not utr_matches.empty:
            b_row = utr_matches.iloc[0]
            b_id = b_row["bank_statement_id"]
            credit_col = f"credit_amount_{base_curr.lower()}"
            b_amt_base = b_row[credit_col]

            if np.isclose(b_amt_base, gross_amt_base, atol=amount_tolerance):
                tier_label = "Tier 2: Gross Amount Mismatch (Unadjusted Fee/Tax)"
            else:
                tier_label = "Tier 2: Partial Refund / Fee Discrepancy"

            return {
                "transaction_id": pg_row["transaction_id"],
                "bank_statement_id": b_id,
                "match_tier": tier_label,
                "match_type_tag": "rule-based",
                "confidence_score": 0.85,
                "notes": f"Expected net base {net_amt_base}, bank recorded credit of {b_amt_base}"
            }

        return None