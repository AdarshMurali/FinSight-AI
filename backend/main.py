import asyncio
import logging
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import test_connection, engine
from routers import portfolios, securities, market_events, analysis
from routers.ws import router as ws_router, run_price_simulator, run_kafka_consumer
from routers.risk import router as risk_router, ensure_table
from routers.alerts import router as alerts_router, ensure_table as ensure_alerts_table

logger = logging.getLogger(__name__)

DB_WAKE_RETRIES = 5
DB_WAKE_DELAY = 30  # seconds between retries (Azure SQL cold start takes ~20-40s)


def wait_for_db():
    """Retry the initial DB ping to handle Azure SQL cold-start timeouts."""
    from sqlalchemy import text
    for attempt in range(1, DB_WAKE_RETRIES + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[OK]   Database connected (attempt {attempt})")
            return
        except Exception as e:
            if attempt < DB_WAKE_RETRIES:
                print(
                    f"[WAIT] DB ping failed (attempt {attempt}/{DB_WAKE_RETRIES}): {e}. "
                    f"Retrying in {DB_WAKE_DELAY}s..."
                )
                time.sleep(DB_WAKE_DELAY)
            else:
                print(f"[FAIL] Database unreachable after {DB_WAKE_RETRIES} attempts — check SQL Server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    print("Starting FinSight AI API...")
    wait_for_db()

    ensure_table()
    print("[OK]   Risk_Metrics table ready")
    ensure_alerts_table()
    print("[OK]   Alerts table ready")

    task_simulator = asyncio.create_task(run_price_simulator(), name="price-simulator")
    task_kafka     = asyncio.create_task(run_kafka_consumer(),  name="kafka-ws-bridge")
    print("[OK]   WebSocket background tasks started (price simulator + Kafka bridge)")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    print("Shutting down FinSight AI API...")
    task_simulator.cancel()
    task_kafka.cancel()
    await asyncio.gather(task_simulator, task_kafka, return_exceptions=True)


app = FastAPI(
    title="FinSight AI API",
    description="AI-powered financial research agent for hedge funds and institutional clients",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(portfolios.router,    prefix="/api/portfolios",    tags=["Portfolios"])
app.include_router(securities.router,    prefix="/api/securities",    tags=["Securities"])
app.include_router(market_events.router, prefix="/api/market-events", tags=["Market Events"])
app.include_router(analysis.router,      prefix="/api/analysis",      tags=["Analysis"])
app.include_router(ws_router,            tags=["WebSocket"])          # /ws  (no prefix)
app.include_router(risk_router,   prefix="/api/risk",   tags=["Risk Analytics"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])


@app.get("/")
async def root():
    return {"message": "FinSight AI API", "version": "2.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    db_ok = test_connection()
    return {
        "status":   "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )
