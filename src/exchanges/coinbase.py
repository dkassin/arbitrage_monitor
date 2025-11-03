import websockets
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncIterator, Optional
from src.models.types import OrderBookUpdate
from src.exchanges.base import ExchangeAdapter

class CoinbaseAdapter(ExchangeAdapter):
    COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"
    PRODUCT_ID = "BTC-USD"

    def __init__(self):
        super().__init__("coinbase")
        self.ws = None
        self.best_bid_price: Optional[Decimal] = None
        self.best_bid_volume: Optional[Decimal] = None
        self.best_ask_price: Optional[Decimal] = None
        self.best_ask_volume: Optional[Decimal] = None
        self.best_bid_needs_refresh = False
        self.best_ask_needs_refresh = False

    async def connect(self) -> None:
        self.ws = await websockets.connect(
            self.COINBASE_WS_URL,
            max_size=10 * 1024 * 1024
            )

        subscribe_message = {
            "type": "subscribe",
            "channels": ["level2_batch"],
            "product_ids": [self.PRODUCT_ID],
            
        }
        await self.ws.send(json.dumps(subscribe_message))
    
    async def listen(self) -> AsyncIterator[OrderBookUpdate]:
        async for message in self.ws:
            try:
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type not in ["snapshot", "l2update"]:
                    print(f"[Coinbase] Full message: {data}")

                if msg_type == "snapshot":
                    best_bid = data["bids"][0]
                    self.best_bid_price = Decimal(str(best_bid[0]))
                    self.best_bid_volume = Decimal(str(best_bid[1]))
                    best_ask = data["asks"][0]
                    self.best_ask_price = Decimal(str(best_ask[0]))
                    self.best_ask_volume = Decimal(str(best_ask[1]))
                    timestamp = datetime.now(timezone.utc)

                    yield OrderBookUpdate(
                        exchange=self.exchange_name,
                        timestamp=timestamp,
                        side="bid",
                        price=self.best_bid_price,
                        volume=self.best_bid_volume
                    )
                    yield OrderBookUpdate(
                        exchange=self.exchange_name,
                        timestamp=timestamp,
                        side="ask",
                        price=self.best_ask_price,
                        volume=self.best_ask_volume
                    )
                elif msg_type == "l2update":
                    changes = data.get("changes", [])
                    timestamp = datetime.now(timezone.utc)

                    bid_changed = False
                    ask_changed = False
                    for change in changes:
                        side = change[0]
                        price = Decimal(str(change[1]))
                        size = Decimal(str(change[2]))

                        if size == Decimal("0"):
                           # Mark that we need to refresh our cached best price
                            if side == "buy" and price == self.best_bid_price:
                                self.best_bid_price = None
                                self.best_bid_volume = None
                                self.best_bid_needs_refresh = True
                            elif side == "sell" and price == self.best_ask_price:
                                self.best_ask_price = None
                                self.best_ask_volume = None
                                self.best_ask_needs_refresh = True
                            continue

                        if side == "buy":
                            if self.best_bid_needs_refresh:
                                # First update after removal - silently refresh internal state
                                self.best_bid_price = price
                                self.best_bid_volume = size
                                self.best_bid_needs_refresh = False
                                bid_changed = False 
                            # If better than current best bid, update
                            elif self.best_bid_price is None or price > self.best_bid_price:
                                self.best_bid_price = price
                                self.best_bid_volume = size
                                bid_changed = True
                            # If same price, update volume
                            elif price == self.best_bid_price:
                                self.best_bid_volume = size
                                bid_changed = True
                        elif side == "sell":
                            if self.best_ask_needs_refresh:
                                # First update after removal - silently refresh internal state
                                self.best_ask_price = price
                                self.best_ask_volume = size
                                self.best_ask_needs_refresh = False
                                ask_changed = False
                            # If better than current best ask, update
                            elif self.best_ask_price is None or price < self.best_ask_price:
                                self.best_ask_price = price
                                self.best_ask_volume = size
                                ask_changed = True
                            # If same price, update volume
                            elif price == self.best_ask_price:
                                self.best_ask_volume = size
                                ask_changed = True
                    if bid_changed:
                        # print(f"[COINBASE] Yielding bid: ${self.best_bid_price}")
                        ## I left this bc it was informative for some of the issues I encountered,
                        ## I wanted to be sure the bids and bid movement made sense
                        yield OrderBookUpdate(
                            exchange=self.exchange_name,
                            timestamp=timestamp,
                            side="bid",
                            price=self.best_bid_price,
                            volume=self.best_bid_volume,
                        )
                    
                    if ask_changed:
                        yield OrderBookUpdate(
                            exchange=self.exchange_name,
                            timestamp=timestamp,
                            side="ask",
                            price=self.best_ask_price,
                            volume=self.best_ask_volume,
                        )

            except (json.JSONDecodeError, KeyError, IndexError) as e:
                print(f"[Coinbase] Error parsing message: {e}")
                continue
            except Exception as e:
                print(f"[Coinbase] Unexpected error: {e}")
                continue
    
    async def close(self) -> None:
        if self.ws:
            await self.ws.close()