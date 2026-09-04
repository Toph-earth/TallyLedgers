from typing import Dict, List, Any
import pandas as pd

from config import AMOUNT_TOLERANCE_INR, DATE_WINDOW_DAYS, SEMANTIC_SIMILARITY_THRESHOLD
from data_generator import generate_reconciliation_dataset
from tier1_exact_matcher import Tier1ExactMatcher
from tier2_amount_matcher import Tier2AmountMatcher
from tier3_semantic_matcher import Tier3SemanticMatcher


class ReconciliationPipeline:
    def __init__(self):
        self.tier1 = Tier1ExactMatcher()
        self.tier2 = Tier2AmountMatcher()
        self.tier3 = Tier3SemanticMatcher()

    def run(self, df_pg: pd.DataFrame, df_bank: pd.DataFrame) -> List[Dict[str, Any]]:
        matches = []
        df_pg = df_pg.copy()
        df_pg["expected_net"] = (df_pg["amount"] - df_pg["fee"] - df_pg["tax"]).round(2)

        # Precompute vector embeddings exclusively for free-text description fallback
        pg_embeddings = self.tier3.model.encode(df_pg["description"].tolist(), normalize_embeddings=True)
        bank_embeddings = self.tier3.model.encode(df_bank["description"].tolist(), normalize_embeddings=True)

        for pg_idx, pg_row in df_pg.iterrows():
            # Step 1: Primary Deterministic Matcher (Exact UTR -> Amount Tolerance -> Date Window)
            res = self.tier1.match(pg_row, df_bank)
            if res:
                matches.append(res)
                continue

            # Step 2: Primary Rule Matcher (Amount Discrepancy & Partial Refund on UTR)
            res = self.tier2.match(pg_row, df_bank)
            if res:
                matches.append(res)
                continue

            # Step 3: Flag Duplicate UTRs
            res = self.tier3.match_duplicate_utr(pg_row, df_bank)
            if res:
                matches.append(res)
                continue

            # Step 4: Secondary Fallback Matcher (Description Text Semantic Similarity Only)
            res = self.tier3.match_semantic_fallback(
                pg_row, pg_embeddings[pg_idx], df_bank, bank_embeddings
            )
            matches.append(res)

        return matches


def evaluate_ground_truth(matches: List[Dict[str, Any]], ground_truth: List[Dict[str, Any]]) -> pd.DataFrame:
    gt_map = {item["transaction_id"]: item for item in ground_truth}
    eval_results = []
    correct_matches = 0
    total = len(matches)

    for m in matches:
        txn_id = m["transaction_id"]
        gt = gt_map.get(txn_id, {})
        expected_bank = gt.get("expected_bank_id")
        actual_bank = m["bank_statement_id"]
        
        is_correct = (expected_bank == actual_bank)
        if is_correct:
            correct_matches += 1

        eval_results.append({
            "transaction_id": txn_id,
            "expected_type": gt.get("expected_match_type"),
            "assigned_tier": m["match_tier"],
            "match_type_tag": m["match_type_tag"],
            "confidence_score": m["confidence_score"],
            "expected_bank_id": expected_bank,
            "actual_bank_id": actual_bank,
            "status": "PASS" if is_correct else "FAIL"
        })

    print("\n================ INSPECTABLE ENGINE THRESHOLDS ================")
    print(f"• Amount Tolerance (INR): ₹{AMOUNT_TOLERANCE_INR}")
    print(f"• Settlement Date Window: {DATE_WINDOW_DAYS} Days (T+1 to T+3)")
    print(f"• Semantic Cosine Similarity Threshold: {SEMANTIC_SIMILARITY_THRESHOLD}")
    print("=================================================================\n")

    print(f"================ GROUND TRUTH ACCURACY SCORE ================")
    print(f"Accuracy Rate: {correct_matches}/{total} ({correct_matches/total*100:.1f}%)")
    print("=============================================================\n")

    return pd.DataFrame(eval_results)


if __name__ == "__main__":
    df_pg, df_bank, ground_truth = generate_reconciliation_dataset()
    print(f"Loaded {len(df_pg)} PG records and {len(df_bank)} Bank settlement records.")

    pipeline = ReconciliationPipeline()
    results = pipeline.run(df_pg, df_bank)

    df_eval = evaluate_ground_truth(results, ground_truth)
    
    print("Summary Breakdown by Match Type Tag:")
    print(df_eval.groupby(["match_type_tag", "assigned_tier"]).size().reset_index(name="count"))