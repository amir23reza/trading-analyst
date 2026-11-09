"""
Ports: what the application needs from the outside world.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime
from typing import Protocol

from app.domain.models import DailyBar, OutboxEvent, OutboxMessage


# class MarketDataProvider(Protocol):
#     def fetch_daily_bars(self, start_dates: Mapping[str, date]) -> list[DailyBar]:
#         """Return daily bars per symbol, from its start date (inclusive) up to today."""


class BarRepository(Protocol):
    """
    A part of Repository design pattern.
    A Repository Interface (A contract defining what data operations are allowed)
    The previous part is the Domain Model (the DailyBar class), which is a representation of the data.
    """
    def active_symbols(self) -> list[str]: ...

    def latest_trade_dates(self, symbols: Sequence[str]) -> dict[str, date]: ...

    def upsert(self, bars: Sequence[DailyBar], fetched_at: datetime) -> None: ...

    def get_prices(self, symbols: Sequence[str], start: date, end: date) -> list[DailyBar]: ...


class OutboxRepository(Protocol):
    def add(self, event: OutboxEvent) -> None: ...

    def claim_due(self, now: datetime, limit: int) -> list[OutboxMessage]: ...

    def mark_sent(self, message_id, now: datetime) -> None: ...

    def mark_failed(self, message_id, attempts: int, next_attempt_at: datetime, dead: bool) -> None: ...


class UnitOfWork(Protocol):
    """One transaction. Leaving the block without commit() rolls back."""

    bars: BarRepository
    outbox: OutboxRepository

    def __enter__(self) -> UnitOfWork: ...

    def __exit__(self, exc_type, exc, tb) -> None: ...

    def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
"""
It defines a factory function for creating a unit-of-work object.
The factory function takes no arguments and returns a new instance 
of the UnitOfWork class.
This allows for the creation of multiple independent unit-of-work instances, 
each with its own state and resources, which can be used to manage transactions 
and data access in a consistent and controlled manner.

That pattern is common in DDD / repository / transaction management: 
you don’t instantiate the database transaction directly in business logic; 
you get it from a factory.
"""


class Sender(Protocol):
    def send(self, url: str, body: bytes, headers: Mapping[str, str]) -> None:
        """Deliver one webhook. Raise on any failure (non-2xx, timeout, network)."""