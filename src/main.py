import asyncio
import sys
import logging
from src.core.orchestrator import Orchestrator
from src.utils.logging import setup_logging

async def main():
    setup_logging(level=logging.INFO)
    print("Starting BTC/USD arbitrage monitor...")
    
    orchestrator = Orchestrator()
    await orchestrator.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n=== Bot Stopped ===")
        sys.exit(0)