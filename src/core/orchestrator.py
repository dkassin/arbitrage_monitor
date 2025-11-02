import asyncio
import logging
from decimal import Decimal
from datetime import datetime
from src.exchanges.kraken import KrakenAdapter
from src.exchanges.coinbase import CoinbaseAdapter
from src.core.order_book import OrderBookManager
from src.core.signal_detector import SignalDetector
from src.core.statistics import StreamingStats
from src.core.executor import OrderExecutor
from src.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        """Initialize all components"""
        # Core components
        self.order_book_manager = OrderBookManager()
        self.signal_detector = SignalDetector()
        self.executor = OrderExecutor()
        
        # Stats trackers
        self.kraken_stats = StreamingStats("kraken")
        self.coinbase_stats = StreamingStats("coinbase")
        
        # Exchange adapters
        self.kraken = KrakenAdapter()
        self.coinbase = CoinbaseAdapter()

    async def process_exchange_feed(self, adapter, stats):
        """Process updates from one exchange"""
        try:
            await retry_with_backoff(adapter.connect, max_retries=3)
            print(f"[{adapter.exchange_name.upper()}] Connected")
        except Exception as e:
            print(f"[{adapter.exchange_name.upper()}] Failed to connect: {e}")
            print(f"[{adapter.exchange_name.upper()}] Continuing without this exchange...")
            return

        async for update in adapter.listen():
            # Update Orderbook with new price/volume
            self.order_book_manager.update(update)
            
            # Update stats (only for bid updates)
            if update.side == "bid":
                stats.update_bid(update.price, update.volume)

            # Check for arb signal
            kraken_state = self.order_book_manager.get_state("kraken")
            coinbase_state = self.order_book_manager.get_state("coinbase")

            signal = self.signal_detector.check_signal(kraken_state, coinbase_state)

            if signal:
                await self.executor.execute_arbitrage(signal)

    async def periodic_stats_logger(self, interval):
        """Log stats every N seconds"""
        while True:
            await asyncio.sleep(interval)
            
            print(f"\n{'='*60}")
            print(f"=== {interval}s UPDATE @ {datetime.now().strftime('%H:%M:%S')} ===")
            
            kraken_state = self.order_book_manager.get_state("kraken")
            coinbase_state = self.order_book_manager.get_state("coinbase")
            
            if kraken_state:
                print(f"Kraken:")
                print(f"  Current: Bid ${kraken_state.best_bid_price:,.2f} | Ask ${kraken_state.best_ask_price:,.2f}")
                print(f"  Stats:   Max Δ ${self.kraken_stats.max_bid_price_change:,.2f} | "
                    f"Total Vol {self.kraken_stats.total_volume_at_best_bid:,.8f} BTC | "
                    f"Max Bid ${self.kraken_stats.max_bid_price:,.2f}")
                
            if coinbase_state:
                print(f"Coinbase:")
                print(f"  Current: Bid ${coinbase_state.best_bid_price:,.2f} | Ask ${coinbase_state.best_ask_price:,.2f}")
                print(f"  Stats:   Max Δ ${self.coinbase_stats.max_bid_price_change:,.2f} | "
                    f"Total Vol {self.coinbase_stats.total_volume_at_best_bid:,.8f} BTC | "
                    f"Max Bid ${self.coinbase_stats.max_bid_price:,.2f}")
            
            print(f"{'='*60}\n")

    async def run(self):
        """Main orchestration - run all tasks concurrently"""
        try:
            # Create concurrent tasks for both exchanges
            kraken_task = asyncio.create_task(
                self.process_exchange_feed(self.kraken, self.kraken_stats)
            )

            coinbase_task = asyncio.create_task(
                self.process_exchange_feed(self.coinbase, self.coinbase_stats)
            )

            # Periodic stats logging tasks
        
            stats_30s_task = asyncio.create_task(
                self.periodic_stats_logger(30)
            )

            # Wait for all tasks (runs indefinitely until Ctrl+C)
            await asyncio.gather(kraken_task, coinbase_task, stats_30s_task)
        
        except KeyboardInterrupt:
            print("\n\nShutting down...")

        finally:
            # Cleanup
            await self.kraken.close()
            await self.coinbase.close()
            await self.executor.close()

            # Print final stats
            print("\n=== FINAL STATISTICS ===")
            print(f"Kraken: {self.kraken_stats.get_stats()}")
            print(f"Coinbase: {self.coinbase_stats.get_stats()}")