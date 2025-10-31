from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

Exchange = Literal["kraken", "coinbase"]
Side = Literal["bid", "ask"]

@dataclass
class OrderBookState:
    exchange: Exchange
    best_bid_price: Decimal
    best_bid_volume: Decimal
    best_ask_price: Decimal
    best_ask_volume: Decimal
    timestamp: datetime

@dataclass
class OrderBookUpdate:
    exchange: Exchange
    timestamp: datetime
    side: Side
    price: Decimal
    volume: Decimal

@dataclass
class ArbitrageSignal:
    buy_exchange: Exchange
    sell_exchange: Exchange
    buy_price: Decimal
    sell_price: Decimal
    size: Decimal
    spread_pct: Decimal
    timestamp: datetime
