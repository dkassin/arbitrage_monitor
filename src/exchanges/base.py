from abc import ABC, abstractmethod
from typing import AsyncIterator
from src.models.types import OrderBookUpdate

class ExchangeAdapter(ABC):
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def listen(self) -> AsyncIterator[OrderBookUpdate]:
        pass            

    @abstractmethod
    async def close(self) -> None:
        pass
    