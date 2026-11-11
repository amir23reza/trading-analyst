from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.container import build_container

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    An asynchronous context manager is
    an object in Python that handles the 
    non-blocking allocation and release of resources. 
    While a standard context manager uses with along
    with __enter__ and __exit__, an async context manager
    is invoked using async with and implements __aenter__ 
    and __aexit__.

    lifespan is the application’s startup-and-shutdown context. 
    It lets you initialize resources before the app handles 
    requests and release them when the app shuts down.

    explanation of this lifespan function:
    Before yield (startup): it loads settings, 
    builds the dependency container, and stores it 
    on app.state so routes can access it.
    
    At yield: control passes to FastAPI, 
    which serves requests while the lifespan context 
    remains active.
    
    After yield (shutdown): it signals the stop event, 
    joins the worker thread if one was started, 
    closes the sender, and disposes the database engine.
    """
    settings = get_settings()
    container = build_container(settings)
    # app.state is shared application-level storage; routes can retrieve this container from it.
    app.state.container = container

    stop = threading.Event()
    thread = None
    if settings.dispatcher_enabled:
        # thread = threading.Thread(
        #     target=run_dispatcher,
        #     args=(container.dispatcher, stop, settings.dispatcher_poll_seconds),
        #     name="outbox-dispatcher",
        #     daemon=True,
        # )
        # thread.start()
        pass
    yield
    stop.set()
    # If a thread was started for the dispatcher, 
    # we wait for it to finish with a timeout of 5 seconds. 
    # This ensures that the application doesn't hang 
    # indefinitely during shutdown if the thread is still running.
    if thread:
        thread.join(timeout=5)
    container.sender.close()
    container.engine.dispose()

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.include_router(router)
    logging.info(f"Starting {settings.app_name} v{settings.app_version}")
    return app

app = create_app()