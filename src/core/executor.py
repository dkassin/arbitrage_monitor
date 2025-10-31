import aiohttp
from src.models.types import ArbitrageSignal

class OrderExecutor:
    def __init__(self):
        self.session = None

    async def execute_arbitrage(self, signal: ArbitrageSignal) -> None:
        print(f"\n[ARBITRAGE SIGNAL DETECTED]")
        print(f"Buy {signal.size} BTC on {signal.buy_exchange} at ${signal.buy_price}")
        print(f"Sell {signal.size} BTC on {signal.sell_exchange} at ${signal.sell_price}")
        print(f"Spread: {float(signal.spread_pct) * 100:.3f}%")

        if self.session is None:
            self.session = aiohttp.ClientSession()

        buy_url, buy_payload = self._get_order_params(
            signal.buy_exchange, "buy", float(signal.size)
        )
        sell_url, sell_payload = self._get_order_params(
            signal.sell_exchange, "sell", float(signal.size)
        )

        try:
            async with self.session.post(buy_url, json=buy_payload) as response:
                print(f"[{signal.buy_exchange.upper()}] Buy order: HTTP {response.status} (expected 401/403)")
        except Exception as e:
            print(f"[{signal.buy_exchange.upper()}] Buy order error: {e}")

        try:
            async with self.session.post(sell_url, json=sell_payload) as response:
                print(f"[{signal.sell_exchange.upper()}] Sell order: HTTP {response.status} (expected 401/403)")
        except Exception as e:
            print(f"[{signal.sell_exchange.upper()}] Sell order error: {e}")

    def _get_order_params(self, exchange: str, side: str, size: float):
        if exchange == "kraken":
            url = "https://api.kraken.com/0/private/AddOrder"
            payload = {
                "pair": "XBTUSD",
                "type": side,
                "ordertype": "market",
                "volume": str(size),
            }
        else:
            url = "https://api.exchange.coinbase.com/orders"
            payload = {
                "product_id": "BTC-USD",
                "side": side,
                "type": "market",
                "size": str(size)
            }
        return url, payload

    async def close(self) -> None:
        if self.session:
            await self.session.close()