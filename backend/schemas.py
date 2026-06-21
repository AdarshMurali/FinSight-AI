from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


class CustomerBase(BaseModel):
    customer_name: str
    institution_type: Optional[str] = None
    aum: Optional[Decimal] = None
    risk_profile: Optional[str] = None


class CustomerResponse(CustomerBase):
    customer_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortfolioBase(BaseModel):
    portfolio_name: str
    currency: Optional[str] = "USD"
    strategy_type: Optional[str] = None


class PortfolioResponse(PortfolioBase):
    portfolio_id: int
    customer_id: int
    total_value: Optional[Decimal] = None
    cash_balance: Optional[Decimal] = None
    inception_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class SecurityBase(BaseModel):
    ticker_symbol: str
    security_name: Optional[str] = None
    security_type: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None


class SecurityResponse(SecurityBase):
    security_id: int
    exchange: Optional[str] = None
    currency: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PositionBase(BaseModel):
    quantity: Decimal
    avg_cost_basis: Decimal
    current_price: Decimal
    position_type: str


class PositionResponse(PositionBase):
    position_id: int
    portfolio_id: int
    security_id: int
    market_value: Optional[Decimal] = None
    weight: Optional[Decimal] = None
    opened_date: Optional[date] = None
    last_updated: datetime
    security: Optional[SecurityResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionBase(BaseModel):
    transaction_type: str
    quantity: Decimal
    price: Decimal
    fees: Optional[Decimal] = 0


class TransactionResponse(TransactionBase):
    transaction_id: int
    portfolio_id: int
    security_id: int
    transaction_date: datetime
    notes: Optional[str] = None
    security: Optional[SecurityResponse] = None

    model_config = ConfigDict(from_attributes=True)


class PerformanceResponse(BaseModel):
    performance_id: int
    portfolio_id: int
    as_of_date: date
    total_value: Optional[Decimal] = None
    daily_return: Optional[Decimal] = None
    mtd_return: Optional[Decimal] = None
    ytd_return: Optional[Decimal] = None
    volatility: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class MarketEventResponse(BaseModel):
    event_id: int
    event_date: datetime
    event_type: Optional[str] = None
    event_title: Optional[str] = None
    event_description: Optional[str] = None
    affected_sectors: Optional[str] = None
    affected_regions: Optional[str] = None
    impact_level: Optional[str] = None
    source_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PositionChangeLogResponse(BaseModel):
    log_id: int
    portfolio_id: int
    security_id: int
    change_date: datetime
    change_type: Optional[str] = None
    old_weight: Optional[Decimal] = None
    new_weight: Optional[Decimal] = None
    reason: Optional[str] = None
    related_event_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioDetailsResponse(PortfolioResponse):
    customer: Optional[CustomerResponse] = None
    positions_count: int = 0
    total_positions_value: Decimal = Decimal(0)


class PortfolioStateAnalysisRequest(BaseModel):
    portfolio_id: int
    as_of_date: Optional[date] = None


class PositionChangesRequest(BaseModel):
    portfolio_id: int
    start_date: date
    end_date: date
    threshold_percent: float = 5.0


class EventImpactRequest(BaseModel):
    event_id: int
    portfolio_ids: Optional[List[int]] = None


class RecommendationRequest(BaseModel):
    portfolio_id: int
    risk_tolerance: Optional[str] = None
    optimization_goal: Optional[str] = "balanced"


# ── Task 3.2: AI Analysis Request Schemas ─────────────────────────────────────

class AIPortfolioExplainRequest(BaseModel):
    portfolio_id: int
    as_of_date: Optional[date] = None
    question: Optional[str] = "Explain the current state and key drivers of this portfolio."


class AIChangeNarrateRequest(BaseModel):
    portfolio_id: int
    start_date: date
    end_date: date
    threshold_percent: Optional[float] = 5.0


class AIEventAnalyzeRequest(BaseModel):
    event_id: int
    portfolio_ids: Optional[List[int]] = None
    depth: Optional[str] = "deep"


class AIRecommendationRequest(BaseModel):
    portfolio_id: int
    risk_tolerance: Optional[str] = None
    optimization_goal: Optional[str] = "balanced"
