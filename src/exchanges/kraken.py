import websockets
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncIterator
from src.models.types import OrderBookUpdate
from src.exchanges.base import ExchangeAdapter

class KrakenAdapter(ExchangeAdapter):
    KRAKEN_WS_URL = "wss://ws.kraken.com/v2"
    SYMBOL = "BTC/USD"
    CHANNEL = "ticker"

    def __init__(self):
        super().__init__("kraken")
        self.ws = None

    async def connect(self) -> None:
        self.ws = await websockets.connect(self.KRAKEN_WS_URL)

        subscribe_message = {
            "method": "subscribe",
            "params": {
                "channel": self.CHANNEL,
                "symbol": [self.SYMBOL]
            }
        }

        await self.ws.send(json.dumps(subscribe_message))
    

    async def listen(self) -> AsyncIterator[OrderBookUpdate]:
        async for message in self.ws:
            try:
                data = json.loads(message)
                if data.get("channel") != "ticker" or data.get("type") != 'update':
                    continue
                ticker = data["data"][0]
                timestamp = datetime.now(timezone.utc)
                yield OrderBookUpdate(
                    exchange=self.exchange_name,
                    timestamp=timestamp,
                    side="bid",
                    price=Decimal(str(ticker["bid"])),
                    volume=Decimal(str(ticker["bid_qty"]))
                )

                yield OrderBookUpdate(
                    exchange=self.exchange_name,
                    timestamp=timestamp,
                    side="ask",
                    price=Decimal(str(ticker["ask"])),
                    volume=Decimal(str(ticker["ask_qty"]))
                )
                
            except json.JSONDecodeError as e:
                # Invalid JSON - log and skip
                print(f"[Kraken] JSON decode error: {e}")
                continue
            
            except (KeyError, IndexError) as e:
                # Missing expected fields - log and skip
                print(f"[Kraken] Missing field in message: {e}")
                continue
                
            except Exception as e:
                # Unexpected error - log and skip
                print(f"[Kraken] Unexpected error: {e}")
                continue

    async def close(self) -> None:
        if self.ws:
            await self.ws.close()
