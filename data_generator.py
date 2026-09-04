from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import pandas as pd


def generate_reconciliation_dataset() -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
    """Generates 50 realistic multi-currency Razorpay PG & Bank records."""
    base_time = datetime(2026, 8, 1, 10, 0, 0)
    currencies = ["INR", "USD", "EUR", "GBP"]
    pg_records = []
    bank_records = []
    ground_truth = []

    for i in range(1, 51):
        txn_id = f"pay_{i:04d}"
        utr = f"UTR{1000 + i}"
        curr = currencies[i % len(currencies)]
        
        raw_amt = round(100.0 + (i * 15.50), 2)
        fee = round(raw_amt * 0.02, 2)
        tax = round(fee * 0.18, 2)
        timestamp = base_time + timedelta(hours=i)
        
        if i <= 30:
            match_type = "exact"
            b_amount = round(raw_amt - fee - tax, 2)
            b_utr = utr
            b_time = timestamp + timedelta(hours=2)
            b_status = "SETTLED"
            pg_status = "captured"

        elif i <= 35:
            match_type = "amount_mismatch"
            b_amount = raw_amt
            b_utr = utr
            b_time = timestamp + timedelta(hours=2)
            b_status = "SETTLED"
            pg_status = "captured"

        elif i <= 38:
            match_type = "duplicate_utr"
            b_amount = round(raw_amt - fee - tax, 2)
            b_utr = "UTR_DUP_9999"
            b_time = timestamp + timedelta(hours=1)
            b_status = "SETTLED"
            pg_status = "captured"

        elif i <= 42:
            match_type = "date_shifted"
            b_amount = round(raw_amt - fee - tax, 2)
            b_utr = utr
            b_time = timestamp + timedelta(days=2)
            b_status = "SETTLED"
            pg_status = "captured"

        elif i <= 46:
            match_type = "partial_refund"
            refund_amount = 20.00
            b_amount = round((raw_amt - fee - tax) - refund_amount, 2)
            b_utr = utr
            b_time = timestamp + timedelta(hours=4)
            b_status = "SETTLED_PARTIAL_REFUND"
            pg_status = "refunded"

        else:
            match_type = "missing_counterpart"
            pg_records.append({
                "transaction_id": txn_id,
                "utr": utr,
                "currency": curr,
                "amount": raw_amt,
                "fee": fee,
                "tax": tax,
                "timestamp": timestamp,
                "status": "failed",
                "description": f"Failed PG payment {txn_id}"
            })
            ground_truth.append({
                "transaction_id": txn_id,
                "expected_match_type": match_type,
                "expected_bank_id": None
            })
            continue

        pg_records.append({
            "transaction_id": txn_id,
            "utr": utr,
            "currency": curr,
            "amount": raw_amt,
            "fee": fee,
            "tax": tax,
            "timestamp": timestamp,
            "status": pg_status,
            "description": f"Razorpay payment {txn_id} via {utr}"
        })

        bank_id = f"bank_stmt_{i:04d}"
        bank_records.append({
            "bank_statement_id": bank_id,
            "utr": b_utr,
            "currency": curr,
            "credit_amount": b_amount,
            "timestamp": b_time,
            "status": b_status,
            "description": f"Bank credit settlement ref {b_utr}"
        })

        ground_truth.append({
            "transaction_id": txn_id,
            "expected_match_type": match_type,
            "expected_bank_id": bank_id
        })

    return pd.DataFrame(pg_records), pd.DataFrame(bank_records), ground_truth