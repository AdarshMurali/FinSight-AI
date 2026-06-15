from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from config import settings
from database import test_connection
from routers import portfolios, securities, market_events, analysis


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting FinSight AI API...")
    if test_connection():
        print("[SUCCESS] Database connection successful")
    else:
        print("[FAILED] Database connection failed")
    yield
    print("Shutting down FinSight AI API...")


app = FastAPI(
    title="FinSight AI API",
    description="AI-powered financial research agent for hedge funds and institutional clients",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolios.router, prefix="/api/portfolios", tags=["Portfolios"])
app.include_router(securities.router, prefix="/api/securities", tags=["Securities"])
app.include_router(market_events.router, prefix="/api/market-events", tags=["Market Events"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])


@app.get("/")
async def root():
    return {
        "message": "FinSight AI API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    db_status = test_connection()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )
