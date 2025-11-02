from decimal import Decimal
from typing import Optional

class StreamingStats:
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.max_bid_price_change = Decimal("0")
        self.total_volume_at_best_bid = Decimal("0")
        self.max_bid_price = Decimal("0")
        self.previous_best_bid = None

    def update_bid(self, price, volume) -> None:
        # Validate inputs - never process None or invalid values
        if price is None or volume is None or price <= 0 or volume <= 0:
            return
        # Updates max bid price
        if price > self.max_bid_price:
            self.max_bid_price = price
        # Calculates and updates max price change
        if self.previous_best_bid is not None:
            price_change = abs(price - self.previous_best_bid)
            if price_change > Decimal("50"):  # Log big jumps
                print(f"[{self.exchange_name}] BIG JUMP: ${self.previous_best_bid} -> ${price} (${price_change})")
            if price_change > self.max_bid_price_change:
                self.max_bid_price_change = price_change
        # Adds volume to overall total
        self.total_volume_at_best_bid += volume
        # Updates previous best bid for future calcs
        self.previous_best_bid = price

    def get_stats(self) -> dict:
        return {
            "exchange": self.exchange_name,
            "max_bid_price_change": float(self.max_bid_price_change),
            "total_volume_at_best_bid": float(self.total_volume_at_best_bid),
            "max_bid_price": float(self.max_bid_price)
        }

    