from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class DailyBar:
    """
    The daily information for a single symbol,
    as returned by the Yahoo Finance API.
    """
    symbol: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adj_close: Decimal
    volume: int
    source: str = "yahoo"

@dataclass(frozen=True)
class OutboxEvent:
    """An event to be delivered. `payload` is the complete JSON envelope."""

    id: UUID
    event_type: str
    payload: str
    occurred_at: datetime


@dataclass(frozen=True)
class OutboxMessage:
    """An outbox row claimed by the dispatcher."""

    id: UUID
    event_type: str
    payload: str
    attempts: int