from typing import Optional, Dict
from src.models.types import OrderBookUpdate, OrderBookState
from decimal import Decimal

class OrderBookManager:
    def __init__(self):
        self.states =  {
            "kraken": None,
            "coinbase": None,
        }
    
    def update(self, update: OrderBookUpdate) -> None:
        #Update the state for the given exchange
        exchange = update.exchange
        current_state = self.states[exchange]

        if current_state is None:
            # First update for this exchange
            if update.side == "bid":
                self.states[exchange] = OrderBookState(
                    exchange=exchange,
                    best_bid_price=update.price,
                    best_bid_volume=update.volume,
                    # The following zeroes are placeholders
                    best_ask_price=Decimal("0"),
                    best_ask_volume=Decimal("0"),
                    timestamp=update.timestamp
                )
            else:
                self.states[exchange] = OrderBookState(
                    exchange=exchange,
                    # The following zeroes are placeholders
                    best_bid_price=Decimal("0"),
                    best_bid_volume=Decimal("0"),
                    best_ask_price=update.price,
                    best_ask_volume=update.volume,
                    timestamp=update.timestamp
                )
        else:
            if update.side == "bid":
                self.states[exchange] = OrderBookState(
                    exchange=exchange,
                    best_bid_price=update.price,
                    best_bid_volume=update.volume,
                    best_ask_price=current_state.best_ask_price,
                    best_ask_volume=current_state.best_ask_volume,
                    timestamp=update.timestamp
                )
            else:
                self.states[exchange] = OrderBookState(
                    exchange=exchange,
                    best_bid_price=current_state.best_bid_price,
                    best_bid_volume=current_state.best_bid_volume,
                    best_ask_price=update.price,
                    best_ask_volume=update.volume,
                    timestamp=update.timestamp
                )

    def get_state(self, exchange:str) -> Optional[OrderBookState]:
        # Return the current state for the given exchange
        return self.states.get(exchange)