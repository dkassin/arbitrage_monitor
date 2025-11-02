import pytest
from decimal import Decimal
from datetime import datetime, timezone
from src.core.signal_detector import SignalDetector
from src.models.types import OrderBookState


def create_state(exchange, bid_price, bid_vol, ask_price, ask_vol):
    # Helper to create test order book states
    return OrderBookState(
        exchange=exchange,
        best_bid_price=Decimal(str(bid_price)),
        best_bid_volume=Decimal(str(bid_vol)),
        best_ask_price=Decimal(str(ask_price)),
        best_ask_volume=Decimal(str(ask_vol)),
        timestamp=datetime.now(timezone.utc)
    )


class TestSignalDetector:
    def test_triggers_on_kraken_bid_exceeds_coinbase_ask(self):
        detector = SignalDetector(threshold_pct=Decimal("0.001"))
        
        kraken = create_state("kraken", 110200, 1.0, 110250, 1.0)
        coinbase = create_state("coinbase", 109900, 1.0, 110000, 1.0)
        
        signal = detector.check_signal(kraken, coinbase)
        
        assert signal is not None
        assert signal.buy_exchange == "coinbase"
        assert signal.sell_exchange == "kraken"
    
    def test_triggers_on_coinbase_bid_exceeds_kraken_ask(self):
        detector = SignalDetector(threshold_pct=Decimal("0.001"))
        
        kraken = create_state("kraken", 109900, 1.0, 110000, 1.0)
        coinbase = create_state("coinbase", 110200, 1.0, 110250, 1.0)
        
        signal = detector.check_signal(kraken, coinbase)
        
        assert signal is not None
        assert signal.buy_exchange == "kraken"
        assert signal.sell_exchange == "coinbase"
    
    def test_no_signal_when_spread_below_threshold(self):
        detector = SignalDetector(threshold_pct=Decimal("0.001"))
        
        # Small spread of ~0.05%
        kraken = create_state("kraken", 110050, 1.0, 110100, 1.0)
        coinbase = create_state("coinbase", 110000, 1.0, 110000, 1.0)
        
        signal = detector.check_signal(kraken, coinbase)
        assert signal is None
    
    def test_deduplication_same_prices(self):
        detector = SignalDetector(threshold_pct=Decimal("0.001"))
        
        kraken = create_state("kraken", 110200, 1.0, 110250, 1.0)
        coinbase = create_state("coinbase", 109900, 1.0, 110000, 1.0)
        
        signal1 = detector.check_signal(kraken, coinbase)
        signal2 = detector.check_signal(kraken, coinbase)  # Same prices
        
        assert signal1 is not None
        assert signal2 is None 
    
    def test_retriggers_on_price_change(self):
        detector = SignalDetector(threshold_pct=Decimal("0.001"))
        
        kraken1 = create_state("kraken", 110200, 1.0, 110250, 1.0)
        coinbase1 = create_state("coinbase", 109900, 1.0, 110000, 1.0)
        signal1 = detector.check_signal(kraken1, coinbase1)
        
        # Price changes
        kraken2 = create_state("kraken", 110300, 1.0, 110350, 1.0)
        coinbase2 = create_state("coinbase", 109900, 1.0, 110000, 1.0)
        signal2 = detector.check_signal(kraken2, coinbase2)
        
        assert signal1 is not None
        assert signal2 is not None 
    
    def test_uses_minimum_volume_for_size(self):
        detector = SignalDetector(threshold_pct=Decimal("0.001"))
        
        kraken = create_state("kraken", 110200, 5.0, 110250, 5.0)
        coinbase = create_state("coinbase", 109900, 2.5, 110000, 2.5)
        
        signal = detector.check_signal(kraken, coinbase)
        
        assert signal.size == Decimal("2.5")
    
    def test_handles_none_states(self):
        detector = SignalDetector()
        
        assert detector.check_signal(None, None) is None
        
    def test_handles_invalid_prices(self):
        detector = SignalDetector()
        
        kraken = create_state("kraken", 0, 1.0, 110050, 1.0)
        coinbase = create_state("coinbase", 110000, 1.0, 110050, 1.0)
        
        assert detector.check_signal(kraken, coinbase) is None