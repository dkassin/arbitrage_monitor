from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone
from src.models.types import OrderBookState, ArbitrageSignal
import logging
logger = logging.getLogger(__name__)

class SignalDetector:
    def __init__(self, threshold_pct=Decimal(".001")):
        self.threshold = threshold_pct
        self.last_kraken_bid_coinbase_ask = None
        self.last_coinbase_bid_kraken_ask = None

    def check_signal(self, kraken_state, coinbase_state) -> Optional[ArbitrageSignal]:
        #Check for arb opps
        if kraken_state is None or coinbase_state is None:
            return None
        
        if (kraken_state.best_bid_price == Decimal("0") or
            kraken_state.best_ask_price == Decimal("0") or
            coinbase_state.best_bid_price == Decimal("0") or
            coinbase_state.best_ask_price == Decimal("0")):
            return None
        
        # Check for None (invalidated prices)
        if (kraken_state.best_bid_price is None or
            kraken_state.best_ask_price is None or
            coinbase_state.best_bid_price is None or
            coinbase_state.best_ask_price is None):
            return None

        spread_scenario_k_to_c = (kraken_state.best_bid_price / coinbase_state.best_ask_price) - Decimal("1")
        spread_scenario_c_to_k = (coinbase_state.best_bid_price / kraken_state.best_ask_price) - Decimal("1")
    
        # Buy Coinbase(at_ask), Sell Kraken(at_bid)
        if kraken_state.best_bid_price > coinbase_state.best_ask_price:
            spread = spread_scenario_k_to_c

            if spread > self.threshold:
                # Check deduplication
                current_prices = (kraken_state.best_bid_price, coinbase_state.best_ask_price)
                if self.last_kraken_bid_coinbase_ask == current_prices:
                    return None
                # Determines trade size
                size = min(coinbase_state.best_ask_volume, kraken_state.best_bid_volume)
                # Create TradeSignal
                signal = ArbitrageSignal(
                    buy_exchange="coinbase",
                    sell_exchange="kraken",
                    buy_price=coinbase_state.best_ask_price,
                    sell_price=kraken_state.best_bid_price,
                    size=size,
                    spread_pct=spread,
                    timestamp=datetime.now(timezone.utc)
                )

                self.last_kraken_bid_coinbase_ask = current_prices
                return signal

        
        if coinbase_state.best_bid_price > kraken_state.best_ask_price:
            spread = spread_scenario_c_to_k

            if spread > self.threshold:
                # Check deduplication
                current_prices = (coinbase_state.best_bid_price, kraken_state.best_ask_price)
                if self.last_coinbase_bid_kraken_ask == current_prices:
                    return None

                size = min(kraken_state.best_ask_volume, coinbase_state.best_bid_volume)
                signal = ArbitrageSignal(
                    buy_exchange="kraken",
                    sell_exchange="coinbase",
                    buy_price=kraken_state.best_ask_price,
                    sell_price=coinbase_state.best_bid_price,
                    size=size,
                    spread_pct=spread,
                    timestamp=datetime.now(timezone.utc)
                )
                self.last_coinbase_bid_kraken_ask = current_prices
                return signal
        # No opportunity found, so it returns none
        return None
