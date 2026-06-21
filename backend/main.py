import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import test_connection
from routers import portfolios, securities, market_events, analysis
from routers.ws import router as ws_router, run_price_simulator, run_kafka_consumer

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    print("Starting FinSight AI API...")
    if test_connection():
        print("[OK]   Database connected")
    else:
        print("[FAIL] Database disconnected — check SQL Server")

    # Launch WebSocket background tasks
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
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(portfolios.router,    prefix="/api/portfolios",    tags=["Portfolios"])
app.include_router(securities.router,    prefix="/api/securities",    tags=["Securities"])
app.include_router(market_events.router, prefix="/api/market-events", tags=["Market Events"])
app.include_router(analysis.router,      prefix="/api/analysis",      tags=["Analysis"])
app.include_router(ws_router,            tags=["WebSocket"])          # /ws  (no prefix)


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
