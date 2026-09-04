import pandas as pd
import pandera as pa
from pandera.typing import Series
from typing import Tuple, Dict, Any

# -----------------------------------------------------------------------------
# 1. Pandera DataFrame Schemas
# -----------------------------------------------------------------------------

class LedgerInputSchema(pa.DataFrameModel):
    ledger_id: Series[str] = pa.Field(
        nullable=False,
        unique=True,
        description="Unique internal transaction ID"
    )
    date: Series[str] = pa.Field(
        str_matches=r"^\d{4}-\d{2}-\d{2}$",
        description="Date in YYYY-MM-DD format"
    )
    amount: Series[float] = pa.Field(
        gt=0,
        description="Gross transaction amount (must be positive)"
    )
    description: Series[str] = pa.Field(
        nullable=False,
        description="Ledger line item description"
    )

    class Config:
        strict = False  # Allows additional metadata columns without failing
        coerce = True   # Automatically coerces types where possible (e.g., int to float)


class BankInputSchema(pa.DataFrameModel):
    bank_id: Series[str] = pa.Field(
        nullable=False,
        unique=True,
        description="Unique bank feed statement reference ID"
    )
    date: Series[str] = pa.Field(
        str_matches=r"^\d{4}-\d{2}-\d{2}$",
        description="Settlement date in YYYY-MM-DD format"
    )
    amount: Series[float] = pa.Field(
        gt=0,
        description="Net bank settlement amount (must be positive)"
    )
    description: Series[str] = pa.Field(
        nullable=False,
        description="Raw bank statement text string"
    )

    class Config:
        strict = False
        coerce = True


# -----------------------------------------------------------------------------
# 2. Validation Handler Function
# -----------------------------------------------------------------------------

def validate_reconciliation_inputs(
    df_ledger: pd.DataFrame, df_bank: pd.DataFrame
) -> Tuple[bool, Dict[str, Any], pd.DataFrame, pd.DataFrame]:
    """
    Validates ledger and bank DataFrames against Pandera schemas.
    
    :return: (is_valid, validation_report, validated_df_ledger, validated_df_bank)
    """
    errors = []
    validated_ledger = df_ledger.copy()
    validated_bank = df_bank.copy()

    # Validate Store Ledger
    try:
        validated_ledger = LedgerInputSchema.validate(df_ledger, lazy=True)
    except pa.errors.SchemaErrors as err:
        errors.append({
            "target": "Store Ledger CSV",
            "error_count": len(err.failure_cases),
            "details": err.failure_cases[["schema_context", "column", "check", "failure_case"]]
        })

    # Validate Bank Statement
    try:
        validated_bank = BankInputSchema.validate(df_bank, lazy=True)
    except pa.errors.SchemaErrors as err:
        errors.append({
            "target": "Bank Statement CSV",
            "error_count": len(err.failure_cases),
            "details": err.failure_cases[["schema_context", "column", "check", "failure_case"]]
        })

    is_valid = len(errors) == 0
    report = {
        "is_valid": is_valid,
        "errors": errors
    }

    return is_valid, report, validated_ledger, validated_bank


# -----------------------------------------------------------------------------
# 3. Local Test / Verification
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Test with corrupted data to prove error detection
    corrupted_ledger = pd.DataFrame([
        {"ledger_id": "TXN-001", "date": "2026-08-20", "amount": 100.0, "description": "Valid row"},
        {"ledger_id": "TXN-001", "date": "08/20/2026", "amount": -50.0, "description": "Corrupted date & amount"},
    ])

    corrupted_bank = pd.DataFrame([
        {"bank_id": "BNK-001", "date": "2026-08-22", "amount": 97.0, "description": "Valid bank row"},
    ])

    is_valid, report, _, _ = validate_reconciliation_inputs(corrupted_ledger, corrupted_bank)
    
    print(f"Validation Status: {'PASSED' if is_valid else 'FAILED'}\n")
    if not is_valid:
        for err in report["errors"]:
            print(f"--- Errors in {err['target']} ---")
            print(err["details"])