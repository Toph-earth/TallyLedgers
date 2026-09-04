import re
from typing import Dict, List, Optional
import pandas as pd

COLUMN_ALIASES: Dict[str, List[str]] = {
    "utr": [
        "utr", "rrn", "reference_no", "ref_no", "bank_ref", "txn_ref", 
        "reference", "utr_number", "bank_id", "pg_id", "payment_id", "transaction_ref"
    ],
    "amount": ["amount", "credit_amount", "credit", "settled_amount", "net_amount", "amt", "total_amount"],
    "currency": ["currency", "ccy", "curr", "currency_code"],
    "timestamp": ["timestamp", "date", "created_at", "settlement_date", "txn_date", "time"],
    "description": ["description", "desc", "narration", "remarks", "notes", "details"],
    "fee": ["fee", "fees", "commission", "pg_fee"],
    "tax": ["tax", "gst", "vat", "tax_amount"],
    "id": ["transaction_id", "bank_statement_id", "statement_id", "id", "txn_id"]
}

def resolve_column_name(df: pd.DataFrame, target_field: str) -> Optional[str]:
    columns = [str(c) for c in df.columns]
    aliases = COLUMN_ALIASES.get(target_field, [target_field])

    # 1. Exact or Normalized Match
    normalized_cols = {re.sub(r'[\s_]+', '', str(c).lower()): c for c in columns}
    for alias in aliases:
        norm_alias = re.sub(r'[\s_]+', '', alias.lower())
        if norm_alias in normalized_cols:
            return normalized_cols[norm_alias]

    # 2. Substring Match Fallback
    for alias in aliases:
        for col in columns:
            if alias.lower() in str(col).lower():
                return col

    return None

def standardize_dataframe_schema(
    df: pd.DataFrame, 
    entity_type: str = "pg",
    override_amount_col: Optional[str] = None,
    override_utr_col: Optional[str] = None
) -> pd.DataFrame:
    df_std = df.copy()

    # Determine mapped target columns (Explicit user selection > Auto Resolution)
    amount_col = override_amount_col if override_amount_col in df_std.columns else resolve_column_name(df_std, "amount")
    utr_col = override_utr_col if override_utr_col in df_std.columns else resolve_column_name(df_std, "utr")
    
    currency_col = resolve_column_name(df_std, "currency")
    timestamp_col = resolve_column_name(df_std, "timestamp")
    description_col = resolve_column_name(df_std, "description")

    target_amount_name = "amount" if entity_type == "pg" else "credit_amount"
    target_id_name = "transaction_id" if entity_type == "pg" else "bank_statement_id"
    id_col = resolve_column_name(df_std, "id") or df_std.columns[0]

    rename_map = {}
    if amount_col: rename_map[amount_col] = target_amount_name
    if utr_col: rename_map[utr_col] = "utr"
    if currency_col: rename_map[currency_col] = "currency"
    if timestamp_col: rename_map[timestamp_col] = "timestamp"
    if description_col: rename_map[description_col] = "description"
    if id_col: rename_map[id_col] = target_id_name

    if entity_type == "pg":
        fee_col = resolve_column_name(df_std, "fee")
        tax_col = resolve_column_name(df_std, "tax")
        if fee_col: rename_map[fee_col] = "fee"
        else: df_std["fee"] = 0.0
            
        if tax_col: rename_map[tax_col] = "tax"
        else: df_std["tax"] = 0.0

    df_std = df_std.rename(columns=rename_map)

    # Defaults and Guarantees
    if "currency" not in df_std.columns: df_std["currency"] = "INR"
    if "description" not in df_std.columns: df_std["description"] = "N/A"
    
    if "utr" not in df_std.columns:
        if target_id_name in df_std.columns:
            df_std["utr"] = df_std[target_id_name].astype(str)
        else:
            df_std["utr"] = df_std.index.astype(str)

    if "timestamp" in df_std.columns:
        df_std["timestamp"] = pd.to_datetime(df_std["timestamp"], errors="coerce")

    return df_std