# BTC/USD Arbitrage Monitor

A real-time cryptocurrency arbitrage monitoring system that tracks BTC/USD (easily configurable for other products) prices across Kraken and Coinbase exchanges via WebSocket feeds. The system detects cross-exchange price discrepancies exceeding 0.1%, executes mock trades to exploit arbitrage opportunities, and provides streaming statistics on market microstructure.

## Features

- **Concurrent WebSocket Monitoring**: Simultaneously tracks Kraken (Ticker v2) and Coinbase (Level2) feeds using asyncio
- **Arbitrage Detection**: Identifies price discrepancies >0.1% between exchanges in real-time  
- **Mock Trade Execution**: Simulates cross-exchange order placement when opportunities arise
- **Streaming Statistics**: Memory-efficient tracking O(1) of max bid price changes, total volume, and max bid price
- **Connection Resilience**: Automatic retry with exponential backoff for failed WebSocket connections

## Requirements

- Python 3.8+ (tested with Python 3.13.7 on an M1 Mac)
- pip for dependency installation

## Installation

1. **Clone the repository**
   git clone <your-repo-url>
   cd arbitrage_monitor

2. **Create a virtual environment**
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

3. **Install dependencies**
   pip install -r requirements.txt

## Running the Bot
From the project root directory:

python -m src.main

**What you'll see:**
- Connection confirmations for both exchanges
- Periodic statistics updates every 30 seconds showing current prices and metrics
- Logs of significant bid price movements (>$50) capturing market microstructure
- Arbitrage signals when spread exceeds 0.1% with simulated execution
- Final statistics on shutdown (Ctrl+C)

**Example output:**
Starting BTC/USD arbitrage monitor...
[KRAKEN] Connected
[COINBASE] Connected

============================================================
=== 30s UPDATE @ 10:03:51 ===
Kraken:
  Current: Bid $110,076.00 | Ask $110,076.10
  Stats:   Max Δ $70.00 | Total Vol 30.98763687 BTC | Max Bid $110,377.10
Coinbase:
  Current: Bid $110,142.97 | Ask $110,146.01
  Stats:   Max Δ $88.01 | Total Vol 116.05085999 BTC | Max Bid $110,432.00
============================================================

[ARBITRAGE SIGNAL DETECTED]
Buy 0.00001232 BTC on kraken at $110010.8
Sell 0.00001232 BTC on coinbase at $110128.01
Spread: 0.107%
[KRAKEN] Buy order: HTTP 200 (expected 200/401)
[COINBASE] Sell order: HTTP 401 (expected 200/401)


## Configuration

To adjust the arbitrage threshold (useful for testing in quiet markets), modify `src/core/orchestrator.py`:

# Default: 0.1% threshold
self.signal_detector = SignalDetector(threshold_pct=Decimal("0.001"))

# For testing: 0.02% threshold to see more signals
self.signal_detector = SignalDetector(threshold_pct=Decimal("0.0002"))

To adjust the statistics logging interval, modify the `run()` method in `src/core/orchestrator.py`:

# Change from 30s to 60s
stats_30s_task = asyncio.create_task(
    self.periodic_stats_logger(60)  # Change this value
)

## Testing

Run the test suite:

# Run all tests
pytest -v

# Run specific test file
pytest tests/test_signal_detector.py -v
pytest tests/test_statistics.py -v
pytest tests/test_order_book.py -v


**Test Coverage (17 tests total):**
- **Signal Detection** (8 tests): Arbitrage trigger logic, threshold boundaries, deduplication, edge cases
- **Statistics Tracking** (6 tests): Price change tracking, volume accumulation, input validation
- **Order Book Management** (3 tests): State creation, updates, retrieval

Tests focus on core business logic and data quality validation, ensuring reliable arbitrage detection and accurate statistics reporting.

## Project Structure

arbitrage_monitor/
├── src/
│   ├── main.py                  # Entry point - sets up logging and runs orchestrator
│   ├── core/
│   │   ├── orchestrator.py      # Main orchestration logic - coordinates all components
│   │   ├── signal_detector.py   # Arbitrage signal detection and deduplication
│   │   ├── statistics.py        # Streaming statistics tracker (O(1) memory)
│   │   ├── order_book.py        # Order book state management
│   │   └── executor.py          # Mock trade execution
│   ├── exchanges/
│   │   ├── base.py              # Exchange adapter interface (abstract base class)
│   │   ├── kraken.py            # Kraken WebSocket adapter (Ticker v2)
│   │   └── coinbase.py          # Coinbase WebSocket adapter (Level2)
│   ├── models/
│   │   └── types.py             # Data models (OrderBookState,  OrderBookUpdate, ArbitrageSignal)
│   └── utils/
│       ├── logging.py           # Logging configuration
│       └── retry.py             # Connection retry with exponential backoff
├── tests/
│   ├── test_signal_detector.py  # Tests for arbitrage detection logic
│   ├── test_statistics.py       # Tests for statistics tracking
│   └── test_order_book.py       # Tests for order book state management
├── README.md
└── requirements.txt


## Technical Implementation
### Concurrency

The bot uses asyncio to handle multiple WebSocket connections at once. I'm running three main tasks concurrently:
- Processing Kraken's feed
- Processing Coinbase's feed  
- Logging stats every 30 seconds

Asyncio made sense here since we're just waiting on network I/O most of the time - no need for threading or multiprocessing overhead.

### No DB
We did not need to store any data, so there was no need to set up a DB here.
- If I were personally using this system I would most likely have it store trades in memory, and then
print these to a csv when the program shut down. This would be for my own personal logging.

### Exchange Adapters

Each exchange gets its own adapter class that handles their specific WebSocket protocol. Kraken uses their Ticker v2 channel which is pretty straightforward - they just send you best bid/ask updates. Coinbase uses the Level2_batch channel which is more complex (incremental updates with size=0 removals). We use the Level2_batch channel because the Level2 channel now has an auth requirement. Therefore it was between using the ticker channel or the Level2_batch channel. The only difference between the regular level_2 channel and the batch channel is it delivers batches every 50 milliseconds which for this situation shouldn't be an issue.

Both adapters output the same `OrderBookUpdate` format so the rest of the system doesn't need to know which exchange is which.

### Signal Detection

The signal detector calculates spreads in both directions - buying on Kraken and selling on Coinbase, or vice versa. When a spread exceeds 0.1%, it fires a signal with the trade details (which exchange to buy/sell, price, size). This spread also can be adjusted, it's fairly rare for their to be arb opportunities that are that large if the market isn't moving significantly.

I choose not to add execution fee calculations into the system because otherwise the request 0.1% spread request would not be valid since the trading fee's would be roughly 0.86% round trip.

I added deduplication so it doesn't spam signals when prices haven't changed - the assignment specifically mentioned this. So the system will wait until the bid/ask spread has at least one different component before trading.

### Statistics

Stats are tracked in O(1) memory - just keeping running totals and max values rather than storing every price update. This was a requirement since they mentioned not assuming everything fits in memory.

For each exchange I track:
- Biggest price jump between consecutive bids
- Total volume seen at the best bid
- Highest bid price observed

I also added logging of price jumps between consecutive bids that were larger than $50 since, as I found it interesting when watching the markets.

### Retry & Validation

Added simple retry logic with exponential backoff (2s, 4s, 8s) for WebSocket connections. If both exchanges fail to connect after retries, the bot continues with whichever one succeeded.

There's validation at two levels - the adapters filter out bad data, and the stats classes double-check inputs aren't None or negative. This caught some edge cases during testing.

Also, there is added functionality that will allow the system to run with only one websocket connection running after retry. It will not trade because of the validations that don't allow trading 
if there isn't valid data in all orderbooks. This was due to the fact that during development the kraken website went on maintenance for nearly all of saturday. So in order to debug the coinbase side of the system, this functionality was added.

### Edge Case: Coinbase size=0 Handling

The trickiest bug I ran into was with Coinbase's size=0 messages. They use these to signal that a price level got removed from the order book. My first approach was to just skip these messages entirely, but that caused stale prices to stick around where the system would show a $110,451 ask when the real ask had moved to $110,318. I initially added constant logging of the bid/ask spread discrepancies in order to monitor this. I was able to notice when spreads didn't make sense, and thus was able to determine I needed to go back and add some guard rails to both the statistics class and also the coinbase exchange.

The fix uses a "needs refresh" flag. When size=0 comes in for the current best price, we mark it as needing refresh and set the price to None. The next update silently refreshes our internal state without emitting an update to stats. This prevents both stale prices AND prevents massive artificial price jumps in the statistics (was seeing $13k+ jumps that weren't real).

I also found it necessary to add another check on in the statistics class. This check makes sure to not add any prices or changes to the bids when volume was zero. This proved effective in removing the weird data that I was seeing in some of the streaming statistics.

### Deduplication Logic

The requirement said "do not trigger again until the best bid or best ask changes." I track the last-emitted prices separately for each direction (Kraken to Coinbase and Coinbase to Kraken) so we don't spam signals when the same opportunity persists. 

The system will wait until one side changes prices and then executes. This seems like the best way to go about this because I noticed opportunities when, lets say there was a stale offer on kraken and the bid on coinbase kept rising. We would want our system to keep lifting the ask and hitting the bid in coinbase as the spread keeps getting better.

### Memory-Efficient Statistics

Rather than storing a history of all price updates, I just track the running max/totals. This meets the requirement about not assuming everything fits in memory. The trade-off is you can't do historical analysis, but that wasn't needed for this assignment.

### Simple File Structure and OOP Design

As with most things trading related, I feel like simple in many ways makes things both easier to debug and also more efficient. In that vein, I tried to keep everything very separated and standardized. For example, the orderbooks are both the same even though the data is received from the exchanges in different formats. 

I also felt like it was best to seperate each class into it's in own file, for both testing and debugging purpose but also to make the flow of information very easy to track and understand.

### No Full Orderbook Depth

Also for the sake of this project, I choose to look at just the top bids and asks. This is more for simplicity's sake. If I were to have more time, I would have added some order book depth, solely for the fact that it more properly mocks how I would truly trade cross exchange arbitrage. I noticed opportunities where there were consistently stale bids/offers on kraken where there was huge volume available. There would have been opportunities to buy full bitcoins.

## Notes
- I have actually traded cross exchange arbitrage before, some of the assumptions that were made here were that I have coins sitting on both exchanges, and also available USD.
- No API keys or account creation required - mock orders return 200/401 as expected
    - Kraken actually returned 200 response, for sake of time I did not investigate this
- The bot runs indefinitely until interrupted with Ctrl+C
- Both exchanges use different protocols as specified: Kraken Ticker v2 vs Coinbase Level2 batch
- BTC markets are typically efficient - actual 0.1%+ arbitrage opportunities are rare in calm markets
    - For testing purpose I used .05% or even .02% to see the arbitrage executor work more 

### Future Improvements

If deploying this for real trading, I'd add:
- **Runtime reconnection**: Detect mid-session WebSocket disconnects and automatically reconnect with state recovery
- **Health checks**: Periodic heartbeat monitoring to detect stale connections
- **Circuit breaker**: Stop trading if both feeds become unreliable
- **Full order book depth**: For better liquidity analysis and slippage calculation

## AI Usage
I primarily used claude as a development tool throughout the project.
In terms of my process, I used claude to discuss my desired initial project structure.
I also used it to discuss potential tradeoffs, making all decisions myself.

I am not a fan of using autocoders, as such all the code was written by me with claude aiding with some boilerplate code, class skeletons, and some of the elaborate print statements which AI is spectacular at creating. 

I also feel like one of the strengths of AI is using it for debugging, specifically when you have a strong understanding of what the code is doing, and where the potential bugs could be. I primarily looked to build a working project, and then went back and discussed possible areas to refactor in order to simplify and improve the code quality.



