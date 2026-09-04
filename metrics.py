# metrics.py
import pandas as pd
from typing import List, Dict, Any, Tuple
import re

class PerformanceMetricsEvaluator:
    @staticmethod
    def _find_key(dictionary: Dict[str, Any], aliases: List[str]) -> Any:
        """Finds value in a dictionary regardless of casing or spacing in keys."""
        norm_keys = {re.sub(r'[\s_]+', '', str(k).lower()): k for k in dictionary.keys()}
        for alias in aliases:
            norm_alias = re.sub(r'[\s_]+', '', alias.lower())
            if norm_alias in norm_keys:
                return dictionary[norm_keys[norm_alias]]
        return None

    @staticmethod
    def evaluate(
        matches: List[Dict[str, Any]], 
        ground_truth: List[Dict[str, Any]], 
        start_time: float, 
        end_time: float
    ) -> Tuple[Dict[str, Any], pd.DataFrame]:
        
        execution_time = round(end_time - start_time, 4)
        df_eval = pd.DataFrame(matches)

        if df_eval.empty:
            return {
                "precision_pct": 0.0, "recall_pct": 0.0, 
                "f1_score": 0.0, "fpr_pct": 0.0, 
                "elapsed_seconds": execution_time
            }, df_eval

        # 1. Dynamically extract the actual matched bank ID key
        if "actual_bank_id" not in df_eval.columns:
            possible_keys = ["matched_bank_id", "bank_statement_id", "utr", "bank_id", "matched_utr"]
            found_col = None
            for key in possible_keys:
                if key in df_eval.columns:
                    found_col = key
                    break
            
            if found_col:
                df_eval["actual_bank_id"] = df_eval[found_col].astype(str).replace({"nan": "None", "None": "None", "": "None"})
            else:
                df_eval["actual_bank_id"] = "None"

        has_gt = ground_truth is not None and len(ground_truth) > 0

        if has_gt:
            # 2. Build Ground Truth Mapping dictionary dynamically
            gt_map = {}
            for item in ground_truth:
                tx_id = PerformanceMetricsEvaluator._find_key(item, ["transaction_id", "pg_id", "id", "txn_id"])
                exp_id = PerformanceMetricsEvaluator._find_key(item, ["expected_bank_id", "bank_statement_id", "bank_id", "expected_id", "utr"])
                
                if tx_id is not None:
                    gt_map[str(tx_id).strip()] = str(exp_id).strip() if exp_id is not None else "None"

            df_eval["expected_bank_id"] = df_eval["transaction_id"].astype(str).str.strip().map(gt_map).fillna("None")

            tp, fp, fn, tn = 0, 0, 0, 0
            status_list = []

            # 3. Compute Metrics based on exact values
            for _, row in df_eval.iterrows():
                expected = str(row["expected_bank_id"]).strip()
                actual = str(row["actual_bank_id"]).strip()

                if expected != "None" and actual == expected:
                    tp += 1
                    status_list.append("PASS (True Positive)")
                elif expected == "None" and actual != "None":
                    fp += 1
                    status_list.append("FAIL (False Positive)")
                elif expected != "None" and (actual == "None" or actual != expected):
                    fn += 1
                    status_list.append("FAIL (False Negative)")
                else:
                    tn += 1
                    status_list.append("PASS (True Negative)")

            df_eval["evaluation_status"] = status_list

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

            summary = {
                "precision_pct": round(precision * 100, 2),
                "recall_pct": round(recall * 100, 2),
                "f1_score": round(f1, 4),
                "fpr_pct": round(fpr * 100, 2),
                "elapsed_seconds": execution_time
            }
        else:
            summary = {
                "precision_pct": 0.0, "recall_pct": 0.0, 
                "f1_score": 0.0, "fpr_pct": 0.0, 
                "elapsed_seconds": execution_time
            }

        display_cols = ["transaction_id", "expected_bank_id", "actual_bank_id", "evaluation_status", "match_tier", "confidence_score", "reason"] if has_gt else ["transaction_id", "actual_bank_id", "match_tier", "confidence_score", "reason"]
        existing_cols = [c for c in display_cols if c in df_eval.columns]
        return summary, df_eval[existing_cols]