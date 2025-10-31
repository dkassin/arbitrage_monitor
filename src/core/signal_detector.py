from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone
from src.models.types import OrderBookState, ArbitrageSignal

class SignalDetector:
    def __init__(self, threshold_pct=Decimal(".001")):
        self.threshold = threshold_pct
        self.last_kraken_bid = None
        self.last_kraken_ask = None
        self.last_coinbase_bid = None
        self.last_coinbase_ask = None

    def check_signal(self, kraken_state, coinbase_state) -> Optional[ArbitrageSignal]:
        pass

    def _should_trigger(self, kraken_state, coinbase_state) -> bool:
        pass