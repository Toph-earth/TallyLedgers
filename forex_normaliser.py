from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Tuple
import pandas as pd
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('FXNormaliser')


class CurrencyConverter:
    """
    Domain service for normalising multi-currency transaction amounts to a single 
    base currency using live API exchange rates with an offline fallback mechanism.
    """
    def __init__(
            self, 
            base_currency: str = 'INR',
            fallback_rate: Optional[Dict[str, float]] = None,
            timeout: float = 3.0,
    ):
        self.base_currency = base_currency.upper()
        self.timeout = timeout
        self.is_live = False

        # Offline fallback rate table relative to USD base
        self.fallback_rate_table_usd: Dict[str, Decimal] = {
            "USD": Decimal("1.000000"),
            "EUR": Decimal("1.085000"),
            "GBP": Decimal("1.272000"),
            "CAD": Decimal("0.735000"),
            "JPY": Decimal("0.006500"),
            "INR": Decimal("0.011900"),
            "AUD": Decimal("0.655000"),
            "CHF": Decimal("1.125000"),
            "CNY": Decimal("0.138500"),
            "SGD": Decimal("0.740000"),
            "HKD": Decimal("0.128000"),
            "NZD": Decimal("0.610000"),
        }

        # Derive initial fallback rates relative to self.base_currency
        self.fallback_rate_table: Dict[str, Decimal] = {}
        base_to_usd = self.fallback_rate_table_usd.get(self.base_currency, Decimal("1.0"))
        for ccy, usd_rate in self.fallback_rate_table_usd.items():
            self.fallback_rate_table[ccy] = usd_rate / base_to_usd

        if fallback_rate:
            for ccy, rate in fallback_rate.items():
                self.fallback_rate_table[ccy.upper()] = Decimal(str(rate))

        self.rate_table = self.fallback_rate_table.copy()
        self._load_live_rates()

    def _load_live_rates(self) -> None:
        """Fetch live exchange rates relative to self.base_currency from open.er-api.com."""
        api_url = f"https://open.er-api.com/v6/latest/{self.base_currency}"
        try:
            response = requests.get(api_url, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                if data.get("result") == "success":
                    rates = data.get("rates", {})
                    live_table = self.fallback_rate_table.copy()
                    
                    for ccy, rate in rates.items():
                        if ccy == self.base_currency:
                            live_table[ccy] = Decimal("1.000000")
                        elif rate > 0:
                            live_table[ccy.upper()] = Decimal("1.0") / Decimal(str(rate))
                    
                    self.rate_table = live_table
                    self.is_live = True
                    logger.info(f"✅ Successfully fetched live FX rates for base '{self.base_currency}'.")
                    return
        except Exception as e:
            logger.warning(f"⚠️ FX API error ({e}). Operating in OFFLINE mode.")

        self.is_live = False
        self.rate_table = self.fallback_rate_table.copy()

    def get_rate_to_base(self, source_currency: str) -> Decimal:
        src = source_currency.upper()
        if src == self.base_currency:
            return Decimal("1.000000")
        if src in self.rate_table:
            return self.rate_table[src]
        if src in self.fallback_rate_table:
            return self.fallback_rate_table[src]
        raise ValueError(f"Unsupported currency: '{src}'.")

    def convert_to_base(self, amount: float, currency: str) -> Decimal:
        rate = self.get_rate_to_base(currency)
        amount_dec = Decimal(str(amount))
        converted = amount_dec * rate
        return converted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def is_fx_match(
            self,
            ledger_amount: float,
            ledger_currency: str,
            bank_amount: float,
            bank_currency: str,
            base_tolerance_pct: float = 0.015,
    ) -> Tuple[bool, float, float]:
        l_converted = self.convert_to_base(ledger_amount, ledger_currency)
        b_converted = self.convert_to_base(bank_amount, bank_currency)
        l_base, b_base = float(l_converted), float(b_converted)
        delta = abs(l_base - b_base)
        allowed_tolerance = l_base * base_tolerance_pct
        return delta <= allowed_tolerance, l_base, b_base

    def get_rates_summary(self) -> pd.DataFrame:
        """Get a summary of all exchange rates as a DataFrame."""
        df = pd.DataFrame({
            'Currency': list(self.rate_table.keys()),
            f'Rate to {self.base_currency}': [float(v) for v in self.rate_table.values()]
        })
        return df.sort_values('Currency')

    # Alias for convenience
    # get_rate_summary = get_rates_summary

def normalise_dataframe_amounts(
    df: pd.DataFrame, converter: CurrencyConverter, currency_col: str = "currency", amount_col: str = "amount"
) -> pd.DataFrame:
    df_norm = df.copy()
    if currency_col not in df_norm.columns:
        df_norm[currency_col] = converter.base_currency
    else:
        df_norm[currency_col] = df_norm[currency_col].fillna(converter.base_currency)

    target_col = f"{amount_col}_{converter.base_currency.lower()}"

    normalized_amounts = []
    for _, row in df_norm.iterrows():
        amt = row[amount_col]
        ccy = str(row[currency_col])
        norm_amt = float(converter.convert_to_base(amt, ccy))
        normalized_amounts.append(norm_amt)

    df_norm[target_col] = normalized_amounts
    return df_norm