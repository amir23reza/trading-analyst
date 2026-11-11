"""Composition root: the only place that wires concrete adapters together."""
from __future__ import annotations

import threading
from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.domain.ports import UnitOfWorkFactory
from app.config import Settings, get_database_url
from app.infrastrcuture.sql_repositories import SqlUnitOfWork


@dataclass
class Container:
    engine: Engine # The SQLAlchemy Engine is the starting point for any SQLAlchemy application. 
    #It manages the connection pool and provides a source of database connections. 
    # In this context, it is used to create sessions for interacting with the database.
    uow_factory: UnitOfWorkFactory
    # refresh_service: RefreshService
    # dispatcher: OutboxDispatcher
    # sender: HttpSender
    refresh_lock: threading.Lock

def build_container(settings: Settings) -> Container:
    """
    Build the dependency container.
    This function creates and configures the application's dependencies (adapters), 
    such as the database engine, unit of work factory, refresh service, 
    outbox dispatcher, and HTTP sender. It returns a Container object 
    that holds these dependencies (adapters) for use throughout the application.
    """
    database_url = get_database_url()
    engine = create_engine(database_url, pool_pre_ping = True)

    def uow_factory() -> SqlUnitOfWork:
        # expire_on_commit=False prevents SQLAlchemy from expiring (invalidating) 
        # the attributes of instances after a commit.
        return SqlUnitOfWork(sessionmaker(engine, expire_on_commit=False))
    # refresh_service = RefreshService(uow_factory)
    # sender = HttpSender()
    # dispatcher = OutboxDispatcher(uow_factory, sender)
    return Container(
        engine=engine,
        uow_factory=uow_factory,
        # refresh_service=refresh_service,
        # dispatcher=dispatcher,
        # sender=sender,
        refresh_lock=threading.Lock(), # A threading.Lock is a synchronization primitive that can 
        # be used to protect shared resources from being accessed by multiple threads simultaneously. 
        # In this context, it is used to ensure that only one thread can perform the refresh operation 
        # at a time, preventing race conditions and ensuring data consistency.
    )