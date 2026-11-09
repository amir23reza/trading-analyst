from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request

log = logging.getLogger(__name__)
router = APIRouter()

# def _container(request: Request) -> Container:
#     return request.app.state.container

@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/health/ready")
def ready(request: Request) -> dict[str, str]:
    try:
        # with _container(request).engine.connect() as connection:
        #     connection.execute(text("SELECT 1"))
        pass
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable") from None
    return {"status": "ready"}

# def _run_refresh(container: Container) -> None:
#     try:
#         result = container.refresh_service.run()
#         log.info("Refresh finished: %s", result)
#     except Exception:
#         log.exception("Refresh failed")
#     finally:
#         container.refresh_lock.release()


@router.post("/refresh", status_code=202)
def refresh(request: Request, background_tasks: BackgroundTasks) -> dict[str, str]:
    """Start a daily refresh. Called by a CronJob in Kubernetes, or by hand locally."""
    # container = _container(request)
    # if not container.refresh_lock.acquire(blocking=False):
    #     raise HTTPException(status_code=409, detail="a refresh is already running")
    # background_tasks.add_task(_run_refresh, container)
    return {"status": "accepted"}

@router.get("/prices")
def prices(
    request: Request,
    symbols: str = Query(..., description="Comma-separated, e.g. AAPL,MSFT"),
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
) -> list[dict]:
    requested = sorted({s.strip().upper() for s in symbols.split(",") if s.strip()})
    if not requested or len(requested) > 50:
        raise HTTPException(status_code=422, detail="provide between 1 and 50 symbols")
    start = start or date(1900, 1, 1)
    end = end or date.today()
    # with _container(request).uow_factory() as uow:
    #     bars = uow.bars.get_prices(requested, start, end)
    # return [
    #     {
    #         "symbol": b.symbol, "date": b.trade_date.isoformat(), "open": float(b.open), "high": float(b.high),
    #         "low": float(b.low), "close": float(b.close), "adjClose": float(b.adj_close), "volume": b.volume,
    #     }
    #     for b in bars
    # ]