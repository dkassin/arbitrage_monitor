import pytest
from decimal import Decimal
from datetime import datetime, timezone
from src.core.order_book import OrderBookManager
from src.models.types import OrderBookUpdate


def create_update(exchange, side, price, volume):
    # Helper to create order book updates
    return OrderBookUpdate(
        exchange=exchange,
        timestamp=datetime.now(timezone.utc),
        side=side,
        price=Decimal(str(price)),
        volume=Decimal(str(volume))
    )


class TestOrderBookManager:
    
    def test_update_creates_state_for_new_exchange(self):
        manager = OrderBookManager()
        
        update = create_update("kraken", "bid", 110000, 1.5)
        manager.update(update)
        
        state = manager.get_state("kraken")
        assert state is not None
        assert state.exchange == "kraken"
        assert state.best_bid_price == Decimal("110000")
        assert state.best_bid_volume == Decimal("1.5")
    
    def test_update_modifies_existing_state(self):
        manager = OrderBookManager()
        
        # Initial update
        update1 = create_update("coinbase", "bid", 110000, 1.0)
        manager.update(update1)
        
        # Second update should modify existing state
        update2 = create_update("coinbase", "bid", 110100, 2.0)
        manager.update(update2)
        
        state = manager.get_state("coinbase")
        assert state.best_bid_price == Decimal("110100")
        assert state.best_bid_volume == Decimal("2.0")
    
    def test_get_state_returns_none_for_unknown_exchange(self):
        manager = OrderBookManager()
        
        state = manager.get_state("binance")
        assert state is None