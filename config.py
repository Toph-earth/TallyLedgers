# Explicit, Inspectable Engine Thresholds
AMOUNT_TOLERANCE_INR: float = 0.05  # Allowed difference in normalized settlement amount (₹)
DATE_WINDOW_DAYS: int = 3           # Max allowed date shift window (Days: T+1 to T+3)
SEMANTIC_SIMILARITY_THRESHOLD: float = 0.75  # SentenceTransformer cutoff threshold
DEFAULT_BASE_CURRENCY: str = "INR"  # Default base currency for reconciliation