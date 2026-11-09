from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models import DailyBar, OutboxEvent, OutboxMessage

def _naive_utc(value: datetime) -> datetime:
    """DATETIME2 columns hold naive UTC."""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value

class SqlBarRepository:
    """
    A part of Repository pattern implementation for DailyBar entities, 
    using SQLAlchemy for database interactions.

    /app/domain/models/DailyBar (data class)

    /app/domain/ports/BarRepository (a contract defining 
    what data operations are allowed)

    /app/infrastructure/sql_repositories/SqlBarRepository 
    (the implementation of the contract)
    """
    def __init__(self, session: Session) -> None:
        self._s = session

    def active_symbols(self) -> list[str]:
        """
        Retrieve a list of active symbols from the Watchlist table in the database.
        """
        _active = text("SELECT Symbol FROM Watchlist WHERE Active = 1 ORDER BY Symbol")
        return [row.Symbol for row in self._s.execute(_active)]

    def latest_trade_dates(self, symbols: Sequence[str]) -> dict[str, date]:
        """
        Retrieve the latest trade dates for a list of symbols from the DailyBar table in the database.
        Returns a dictionary mapping each symbol to its latest trade date.
        """
        _LATEST = text(
        "SELECT Symbol, MAX(TradeDate) AS LastDate FROM DailyBar WHERE Symbol IN :symbols GROUP BY Symbol"
        ).bindparams(bindparam("symbols", expanding=True))

        if not symbols:
            return {}
        rows = self._s.execute(_LATEST, {"symbols": list(symbols)}).all()
        return {row.Symbol: row.LastDate for row in rows}

    def upsert(self, bars: Sequence[DailyBar], fetched_at: datetime) -> None:
        """
        Merge (insert or update) a list of DailyBar records into the DailyBar table in the database.
        If a record with the same symbol and trade date exists, it will be updated; otherwise
        , a new record will be inserted.
        
        Idempotent Upsert Design Pattern: 
        calling it multiple times with the same data will not create duplicates.

        why WITH (HOLDLOCK)? because it prevents race conditions in concurrent
        environments by locking the target table during the merge operation. 
        """
        _upsert = text(
            """
            MERGE DailyBar WITH (HOLDLOCK) AS t
            USING (SELECT :symbol AS Symbol, :trade_date AS TradeDate) AS s
            ON t.Symbol = s.Symbol AND t.TradeDate = s.TradeDate
            WHEN MATCHED THEN UPDATE SET
                [Open] = :open, High = :high, Low = :low, [Close] = :close, AdjClose = :adj_close,
                Volume = :volume, FetchedAt = :fetched_at, Source = :source
            WHEN NOT MATCHED THEN INSERT
                (Symbol, TradeDate, [Open], High, Low, [Close], AdjClose, Volume, FetchedAt, Source)
                VALUES (:symbol, :trade_date, :open, :high, :low, :close, :adj_close, :volume, :fetched_at, :source);
            """
        )
        if not bars:
            return
        fetched = _naive_utc(fetched_at)
        params = [
            {
                "symbol": b.symbol, "trade_date": b.trade_date, "open": b.open, "high": b.high,
                "low": b.low, "close": b.close, "adj_close": b.adj_close, "volume": b.volume,
                "fetched_at": fetched, "source": b.source,
            }
            for b in bars
        ]
        # Row-by-row MERGE is fine at daily scale. Staging table + one set-based MERGE is a
        # natural optimisation exercise for the MSSQL phase.
        self._s.execute(_upsert, params)

    def get_prices(self, symbols: Sequence[str], start: date, end: date) -> list[DailyBar]:
        """
        Retrieve daily bar prices for a list of symbols within a specified date range from the 
        DailyBar table in the database.
        Returns a list of DailyBar objects containing the price data for each symbol and trade date.
        """
        _prices = text(
            """
            SELECT Symbol, TradeDate, [Open], High, Low, [Close], AdjClose, Volume, Source
            FROM DailyBar
            WHERE Symbol IN :symbols AND TradeDate >= :start AND TradeDate <= :end
            ORDER BY Symbol, TradeDate
            """
        ).bindparams(bindparam("symbols", expanding=True))
        if not symbols:
            return []
        rows = self._s.execute(_prices, {"symbols": list(symbols), "start": start, "end": end}).mappings().all()
        return [
            DailyBar(
                symbol=r["Symbol"], trade_date=r["TradeDate"], open=Decimal(r["Open"]), high=Decimal(r["High"]),
                low=Decimal(r["Low"]), close=Decimal(r["Close"]), adj_close=Decimal(r["AdjClose"]),
                volume=int(r["Volume"]), source=r["Source"],
            )
            for r in rows
        ]

class SqlOutboxRepository:
    def __init__(self, session: Session) -> None:
        """
        The constructor initializes the SqlOutboxRepository with a SQLAlchemy session.
        """
        self._s = session

    def add(self, event: OutboxEvent) -> None:
        """
        adds an OutboxEvent to the Outbox table in the database.
        """
        occurred = _naive_utc(event.occurred_at)
        self._s.execute(
            text(
                "INSERT INTO Outbox (Id, EventType, Payload, OccurredAt, Status, Attempts, NextAttemptAt) "
                "VALUES (:id, :type, :payload, :occurred, 'Pending', 0, :occurred)"
            ),
            {"id": str(event.id), "type": event.event_type, "payload": event.payload, "occurred": occurred},
        )

    def claim_due(self, now: datetime, limit: int) -> list[OutboxMessage]:
        """
        retrieves a list of due OutboxMessages from the Outbox table in the database,
        up to the specified limit. It uses UPDLOCK and READPAST hints to avoid
        locking conflicts with other transactions and to skip rows 
        that are already locked by other transactions.
        """
        # UPDLOCK + READPAST: competing dispatcher instances skip rows another one has locked.
        rows = self._s.execute(
            text(
                "SELECT TOP (:limit) Id, EventType, Payload, Attempts "
                "FROM Outbox WITH (UPDLOCK, READPAST, ROWLOCK) "
                "WHERE Status = 'Pending' AND NextAttemptAt <= :now ORDER BY OccurredAt"
            ),
            {"limit": limit, "now": _naive_utc(now)},
        ).all()
        return [OutboxMessage(UUID(str(r.Id)), r.EventType, r.Payload, int(r.Attempts)) for r in rows]

    def mark_sent(self, message_id, now: datetime) -> None:
        self._s.execute(
            text("UPDATE Outbox SET Status = 'Sent', SentAt = :now, Attempts = Attempts + 1 WHERE Id = :id"),
            {"id": str(message_id), "now": _naive_utc(now)},
        )

    def mark_failed(self, message_id, attempts: int, next_attempt_at: datetime, dead: bool) -> None:
        self._s.execute(
            text("UPDATE Outbox SET Status = :status, Attempts = :attempts, NextAttemptAt = :next WHERE Id = :id"),
            {
                "status": "Dead" if dead else "Pending", "attempts": attempts,
                "next": _naive_utc(next_attempt_at), "id": str(message_id),
            },
        )


class SqlUnitOfWork:
    """One database transaction. Leaving the block without commit() rolls back."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> SqlUnitOfWork:
        self._session = self._session_factory()
        self._committed = False
        self.bars = SqlBarRepository(self._session)
        self.outbox = SqlOutboxRepository(self._session)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is not None or not self._committed:
                self._session.rollback()
        finally:
            self._session.close()

    def commit(self) -> None:
        self._session.commit()
        self._committed = True