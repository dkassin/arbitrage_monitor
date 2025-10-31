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
    CHANNEL = "level2"

    def __init__(self):
        super().__init__("coinbase")
        self.ws = None
        self.best_bid_price: Optional[Decimal] = None
        self.best_bid_volume: Optional[Decimal] = None
        self.best_ask_price: Optional[Decimal] = None
        self.best_ask_volume: Optional[Decimal] = None

    async def connect(self) -> None:
        self.ws = await websockets.connect(self.COINBASE_WS_URL)

        subscribe_message = {
            "type": "subscribe",
            "product_ids": [self.PRODUCT_ID],
            "channels": [self.CHANNEL],
        }
        await self.ws.send(json.dumps(subscribe_message))
    
    async def listen(self) -> AsyncIterator[OrderBookUpdate]:
        async for message in self.ws:
            try:
                data = json.loads(message)
                msg_type = data.get("type")
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
                        if side == "buy":
                            # If better than current best bid, update
                            if self.best_bid_price is None or price > self.best_bid_price:
                                self.best_bid_price = price
                                self.best_bid_volume = size
                                bid_changed = True
                            # If same price, update volume
                            elif price == self.best_bid_price:
                                self.best_bid_volume = size
                                bid_changed = True
                        elif side == "sell":
                            # If better than current best ask, update
                            if self.best_ask_price is None or price < self.best_ask_price:
                                self.best_ask_price = price
                                self.best_ask_volume = size
                                ask_changed = True
                            # If same price, update volume
                            elif price == self.best_ask_price:
                                self.best_ask_volume = size
                                ask_changed = True
                    if bid_changed:
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