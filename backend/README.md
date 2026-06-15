# FinSight AI - Backend API

AI-powered financial research agent backend for hedge funds and institutional clients.

## Features

- **Portfolio Management API**: CRUD operations for portfolios, positions, and transactions
- **Market Data API**: Access to securities and market events
- **Analysis API**: Portfolio state analysis, position change detection, event impact analysis
- **Business Logic**: Portfolio analytics, risk metrics, performance attribution, recommendations

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQL Server (localhost:1433)
- **ORM**: SQLAlchemy
- **Validation**: Pydantic v2

## Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration settings
├── database.py            # Database connection and session management
├── models.py              # SQLAlchemy ORM models
├── schemas.py             # Pydantic request/response schemas
├── requirements.txt       # Python dependencies
├── routers/              # API route handlers
│   ├── portfolios.py     # Portfolio endpoints
│   ├── securities.py     # Securities endpoints
│   ├── market_events.py  # Market events endpoints
│   └── analysis.py       # Analysis endpoints
└── services/             # Business logic layer
    ├── portfolio_analyzer.py      # Portfolio metrics & allocations
    ├── position_detector.py       # Position change detection
    ├── event_analyzer.py          # Event impact analysis
    ├── recommendation_engine.py   # Portfolio recommendations
    └── performance_attribution.py # Performance attribution
```

## Installation

1. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure database connection**:
   - Copy `.env.example` to `.env`
   - Update database credentials in `.env`

3. **Verify database connection**:
   - Ensure SQL Server is running at localhost:1433
   - Database name: `FinSight_AI`
   - Required tables: Customers, Portfolios, Positions, Securities, Transactions, Market_Events, Portfolio_Performance, Position_Changes_Log

## Running the API

**Development mode** (with auto-reload):
```bash
python main.py
```

**Production mode** (using uvicorn directly):
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## API Endpoints

### Portfolio Management

- `GET /api/portfolios` - List all portfolios
- `GET /api/portfolios/{id}` - Get portfolio details
- `GET /api/portfolios/{id}/positions` - Get current positions
- `GET /api/portfolios/{id}/performance` - Get performance metrics
- `GET /api/portfolios/{id}/history` - Get transaction history

### Securities

- `GET /api/securities` - List all securities
- `GET /api/securities/{id}` - Get security details
- `GET /api/securities/ticker/{symbol}` - Get security by ticker

### Market Events

- `GET /api/market-events` - List market events
- `GET /api/market-events/{id}` - Get event details
- `GET /api/market-events/{id}/affected-portfolios` - Get affected portfolios

### Analysis

- `POST /api/analysis/portfolio-state` - Analyze portfolio state
- `POST /api/analysis/position-changes` - Detect position changes
- `POST /api/analysis/event-impact` - Analyze event impact
- `POST /api/analysis/recommendations` - Get optimization recommendations

## Example Requests

### Get Portfolio Details
```bash
curl http://localhost:8000/api/portfolios/1
```

### Analyze Portfolio State
```bash
curl -X POST http://localhost:8000/api/analysis/portfolio-state \
  -H "Content-Type: application/json" \
  -d '{"portfolio_id": 1, "as_of_date": "2025-01-15"}'
```

### Detect Position Changes
```bash
curl -X POST http://localhost:8000/api/analysis/position-changes \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio_id": 1,
    "start_date": "2024-12-01",
    "end_date": "2025-01-15",
    "threshold_percent": 5.0
  }'
```

## Business Logic Services

### PortfolioAnalyzer
- Calculates portfolio metrics (returns, volatility, Sharpe ratio)
- Sector/region/asset allocation analysis
- Risk exposure calculations
- Concentration risk detection

### PositionChangeDetector
- Detects significant weight changes (configurable threshold)
- Identifies rebalancing events
- Tracks entry/exit positions
- Analyzes change patterns

### EventImpactAnalyzer
- Maps events to affected securities/sectors
- Calculates event-driven performance attribution
- Measures portfolio exposure to events
- Generates impact reports

### RecommendationEngine
- Portfolio optimization suggestions
- Risk-adjusted rebalancing recommendations
- Concentration risk alerts
- Performance improvement suggestions

### PerformanceAttribution
- Security selection contribution
- Sector allocation contribution
- Transaction cost analysis
- Total return calculation

## Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

## Development Notes

- All endpoints use Pydantic v2 for request/response validation
- SQLAlchemy models map to existing SQL Server tables
- Database connection pooling is enabled (pool_size=10, max_overflow=20)
- CORS is configured for frontend at http://localhost:3000

## Next Steps (Phase 3)

- [ ] AI/LLM Integration (OpenAI SDK, Claude API)
- [ ] RAG System with ChromaDB
- [ ] MCP (Model Context Protocol) Integration
- [ ] Real-time data streaming with Apache Flink

## License

Proprietary - FinSight AI
