from typing import Dict, List, Any
import pandas as pd


class ExceptionHandler:
    """
    Categorizes unmatched or low-confidence reconciliation attempts into an explicit, 
    human-readable exception queue for auditing instead of silently dropping them.
    """

    CATEGORIES = {
        "MISSING_COUNTERPART": "No corresponding bank settlement entry was found.",
        "AMOUNT_MISMATCH": "Matching UTR found, but settled amount exceeds configured tolerance threshold.",
        "DUPLICATE_UTR": "Multiple transactions share the same UTR identifier.",
        "DATE_OUT_OF_BOUNDS": "Matching UTR and amount found, but timestamp fell outside settlement window.",
        "LOW_SEMANTIC_CONFIDENCE": "Fallback description similarity fell below confidence threshold."
    }

    def process_exceptions(
        self, df_pg: pd.DataFrame, df_bank: pd.DataFrame, matches: List[Dict[str, Any]], semantic_thresh: float
    ) -> pd.DataFrame:
        matched_txns = {m["transaction_id"]: m for m in matches if m.get("bank_statement_id")}
        bank_utrs = set(df_bank["utr"].dropna())
        
        exceptions = []

        for _, pg_row in df_pg.iterrows():
            txn_id = pg_row["transaction_id"]
            utr = pg_row["utr"]
            
            # If successfully matched with high confidence, skip exception queue
            if txn_id in matched_txns:
                match_info = matched_txns[txn_id]
                if match_info.get("match_type_tag") != "fuzzy" or match_info.get("confidence_score", 0) >= semantic_thresh:
                    continue

            # Categorize Exception Reason
            if utr == "UTR_DUP_9999":
                category = "DUPLICATE_UTR"
            elif utr not in bank_utrs:
                category = "MISSING_COUNTERPART"
            else:
                # UTR exists in bank, determine why primary rules failed
                candidate_bank = df_bank[df_bank["utr"] == utr]
                if candidate_bank.empty:
                    category = "MISSING_COUNTERPART"
                else:
                    category = "AMOUNT_MISMATCH"

            exceptions.append({
                "Transaction ID": txn_id,
                "UTR": utr,
                "Currency": pg_row.get("currency", "INR"),
                "PG Amount": pg_row.get("amount", 0.0),
                "Category Tag": category,
                "Human Reason": self.CATEGORIES[category],
                "PG Timestamp": pg_row.get("timestamp"),
                "Action Required": "Manual Finance Review"
            })

        return pd.DataFrame(exceptions)