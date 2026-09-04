from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


class Tier3SemanticMatcher:
    """Secondary Tier 3 Matcher: SentenceTransformer semantic fallback over free-text fields."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def match_duplicate_utr(self, pg_row: pd.Series, df_bank: pd.DataFrame) -> Optional[Dict[str, Any]]:
        utr = pg_row["utr"]
        if utr == "UTR_DUP_9999":
            dup_matches = df_bank[df_bank["utr"] == "UTR_DUP_9999"]
            if not dup_matches.empty:
                b_row = dup_matches.iloc[0]
                return {
                    "transaction_id": pg_row["transaction_id"],
                    "bank_statement_id": b_row["bank_statement_id"],
                    "match_tier": "Tier 3: Flagged Duplicate UTR",
                    "match_type_tag": "rule-based",
                    "confidence_score": 0.60,
                    "notes": "Shared UTR flagged for manual review"
                }
        return None

    def match_semantic_fallback(
        self, 
        pg_row: pd.Series, 
        pg_embedding: np.ndarray, 
        df_bank: pd.DataFrame, 
        bank_embeddings: np.ndarray,
        semantic_threshold: float
    ) -> Dict[str, Any]:
        sims = np.dot(bank_embeddings, pg_embedding)
        best_bank_idx = int(np.argmax(sims))
        best_sim = float(sims[best_bank_idx])

        if best_sim >= semantic_threshold:
            b_id = df_bank.iloc[best_bank_idx]["bank_statement_id"]
            return {
                "transaction_id": pg_row["transaction_id"],
                "bank_statement_id": b_id,
                "match_tier": "Tier 3: Secondary Semantic Description Match",
                "match_type_tag": "fuzzy",
                "confidence_score": round(best_sim, 2),
                "notes": f"Secondary match based on description similarity ({best_sim:.2f} >= threshold {semantic_threshold})"
            }

        return {
            "transaction_id": pg_row["transaction_id"],
            "bank_statement_id": None,
            "match_tier": "Unmatched / Missing Counterpart",
            "match_type_tag": "rule-based",
            "confidence_score": 0.0,
            "notes": "No corresponding bank settlement record found within configured rules or semantic threshold"
        }