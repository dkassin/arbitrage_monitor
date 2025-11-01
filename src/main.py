import asyncio
from src.exchanges.kraken import KrakenAdapter
from src.exchanges.coinbase import CoinbaseAdapter
from src.core.order_book import OrderBookManager
from src.core.signal_detector import SignalDetector
from src.core.statistics import StreamingStats
from src.core.executor import OrderExecutor

async def process_exchange_feed(adapter,order_book_manager,stats,signal_detector,executor):
    try:
        await adapter.connect()
        print(f"[{adapter.exchange_name.upper()}] Connected")
    except Exception as e:
        print(f"[{adapter.exchange_name.upper()}] Failed to connect: {e}")
        print(f"[{adapter.exchange_name.upper()}] Continuing without this exchange...")
        return
        
    async for update in adapter.listen():
        # Update Orderbook with new price/volume
        order_book_manager.update(update)
        # Update stats (only for bid updates)
        if update.side == "bid":
            stats.update_bid(update.price, update.volume)

        # Check for arb signal
        kraken_state = order_book_manager.get_state("kraken")
        coinbase_state = order_book_manager.get_state("coinbase")

        signal = signal_detector.check_signal(kraken_state, coinbase_state)

        if signal:
            await executor.execute_arbitrage(signal)
        
async def main():
    # Main Orchestrator
    print("starting BTC/USD arbitrage monitor...")

    order_book_manager = OrderBookManager()
    signal_detector = SignalDetector()
    executor = OrderExecutor()

    kraken_stats = StreamingStats("kraken")
    coinbase_stats = StreamingStats("coinbase")

    kraken = KrakenAdapter()
    coinbase = CoinbaseAdapter()

    try:
        kraken_task = asyncio.create_task(
            process_exchange_feed(
                kraken,
                order_book_manager,
                kraken_stats,
                signal_detector,
                executor
            )
        )

        coinbase_task = asyncio.create_task(
            process_exchange_feed(
                coinbase,
                order_book_manager,
                coinbase_stats,
                signal_detector,
                executor
            )
        )

        # Wait for both tasks, (runs indefinitely until Ctrl+C)
        await asyncio.gather(kraken_task, coinbase_task)
    
    except KeyboardInterrupt:
        print("\n\nShutting down...")

    finally:
        await kraken.close()
        await coinbase.close()
        await executor.close()

        print("\n=== FINAL STATISTICS ===")
        print(f"Kraken: {kraken_stats.get_stats()}")
        print(f"Coinbase: {coinbase_stats.get_stats()}")

if __name__ == "__main__":
    asyncio.run(main())