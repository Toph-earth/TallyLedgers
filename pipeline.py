import time
from typing import Dict, List, Any, Tuple, Optional
import pandas as pd

from forex_normaliser import CurrencyConverter, normalise_dataframe_amounts
from tier1_exact_matcher import Tier1ExactMatcher
from tier2_amount_matcher import Tier2AmountMatcher
from tier3_semantic_matcher import Tier3SemanticMatcher
from exception_handler import ExceptionHandler
from metrics import PerformanceMetricsEvaluator
from schema_resolver import standardize_dataframe_schema

class ReconciliationPipeline:
    def __init__(self, base_currency: str = "INR"):
        self.converter = CurrencyConverter(base_currency=base_currency)
        self.tier1 = Tier1ExactMatcher()
        self.tier2 = Tier2AmountMatcher()
        self.tier3 = Tier3SemanticMatcher()
        self.exception_handler = ExceptionHandler()

    def run(
        self, 
        df_pg: pd.DataFrame, 
        df_bank: pd.DataFrame,
        amount_tolerance: float,
        date_window_days: int,
        semantic_threshold: float,
        ground_truth: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[Dict[str, Any]], pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any], pd.DataFrame]:
        
        start_time = time.perf_counter()
        df_pg = standardize_dataframe_schema(df_pg, entity_type="pg")
        df_bank = standardize_dataframe_schema(df_bank, entity_type="bank")
        base_curr = self.converter.base_currency.lower()

        # Step 1: Forex Normalization
        norm_pg = normalise_dataframe_amounts(df_pg, self.converter, currency_col="currency", amount_col="amount")
        norm_pg = normalise_dataframe_amounts(norm_pg, self.converter, currency_col="currency", amount_col="fee")
        norm_pg = normalise_dataframe_amounts(norm_pg, self.converter, currency_col="currency", amount_col="tax")
        
        norm_pg[f"expected_net_{base_curr}"] = (
            norm_pg[f"amount_{base_curr}"] - norm_pg[f"fee_{base_curr}"] - norm_pg[f"tax_{base_curr}"]
        ).round(2)

        norm_bank = normalise_dataframe_amounts(df_bank, self.converter, currency_col="currency", amount_col="credit_amount")

        # Step 2: Embeddings for description matching
        pg_embeddings = self.tier3.model.encode(norm_pg["description"].tolist(), normalize_embeddings=True)
        bank_embeddings = self.tier3.model.encode(norm_bank["description"].tolist(), normalize_embeddings=True)

        matches = []
        for pg_idx, pg_row in norm_pg.iterrows():
            res = self.tier1.match(pg_row, norm_bank, amount_tolerance, date_window_days, base_curr)
            if res:
                matches.append(res)
                continue

            res = self.tier2.match(pg_row, norm_bank, amount_tolerance, base_curr)
            if res:
                matches.append(res)
                continue

            res = self.tier3.match_duplicate_utr(pg_row, norm_bank)
            if res:
                matches.append(res)
                continue

            res = self.tier3.match_semantic_fallback(
                pg_row, pg_embeddings[pg_idx], norm_bank, bank_embeddings, semantic_threshold
            )
            matches.append(res)

        end_time = time.perf_counter()

        # Step 3: Exception Queue Audit Processing
        df_exceptions = self.exception_handler.process_exceptions(norm_pg, norm_bank, matches, semantic_threshold)

        # Handle optional ground truth evaluation safely
        gt_data = ground_truth if ground_truth is not None else []

        # Step 4: Performance & Ground Truth Metrics Computation
        metrics_summary, df_eval = PerformanceMetricsEvaluator.evaluate(matches, gt_data, start_time, end_time)

        return matches, norm_pg, norm_bank, df_exceptions, metrics_summary, df_eval