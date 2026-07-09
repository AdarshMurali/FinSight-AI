from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Customer(Base):
    __tablename__ = "Customers"

    customer_id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(255), nullable=False)
    institution_type = Column(String(100))
    aum = Column(DECIMAL(20, 2))
    risk_profile = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    portfolios = relationship("Portfolio", back_populates="customer")


class Portfolio(Base):
    __tablename__ = "Portfolios"

    portfolio_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("Customers.customer_id"))
    portfolio_name = Column(String(255), nullable=False)
    total_value = Column(DECIMAL(20, 2))
    cash_balance = Column(DECIMAL(20, 2))
    currency = Column(String(10))
    inception_date = Column(Date)
    strategy_type = Column(String(100))

    customer = relationship("Customer", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio")
    transactions = relationship("Transaction", back_populates="portfolio")
    performance = relationship("PortfolioPerformance", back_populates="portfolio")


class Security(Base):
    __tablename__ = "Securities"

    security_id = Column(Integer, primary_key=True, index=True)
    ticker_symbol = Column(String(20), nullable=False, unique=True)
    security_name = Column(String(255))
    security_type = Column(String(50))
    sector = Column(String(100))
    industry = Column(String(100))
    country = Column(String(100))
    exchange = Column(String(100))
    currency = Column(String(10))
    current_price = Column(DECIMAL(18, 4))

    positions = relationship("Position", back_populates="security")
    transactions = relationship("Transaction", back_populates="security")


class Position(Base):
    __tablename__ = "Positions"

    position_id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("Portfolios.portfolio_id"))
    security_id = Column(Integer, ForeignKey("Securities.security_id"))
    quantity = Column(DECIMAL(20, 4))
    avg_cost_basis = Column(DECIMAL(20, 4))
    current_price = Column(DECIMAL(20, 4))
    market_value = Column(DECIMAL(20, 2))
    weight = Column(DECIMAL(5, 2))
    position_type = Column(String(20))
    opened_date = Column(Date)
    last_updated = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="positions")
    security = relationship("Security", back_populates="positions")


class Transaction(Base):
    __tablename__ = "Transactions"

    transaction_id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("Portfolios.portfolio_id"))
    security_id = Column(Integer, ForeignKey("Securities.security_id"))
    transaction_type = Column(String(50))
    quantity = Column(DECIMAL(20, 4))
    price = Column(DECIMAL(20, 4))
    transaction_date = Column(DateTime)
    fees = Column(DECIMAL(20, 2))
    notes = Column(Text)

    portfolio = relationship("Portfolio", back_populates="transactions")
    security = relationship("Security", back_populates="transactions")


class PortfolioPerformance(Base):
    __tablename__ = "Portfolio_Performance"

    performance_id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("Portfolios.portfolio_id"))
    as_of_date = Column(Date)
    total_value = Column(DECIMAL(20, 2))
    daily_return = Column(DECIMAL(10, 4))
    mtd_return = Column(DECIMAL(10, 4))
    ytd_return = Column(DECIMAL(10, 4))
    volatility = Column(DECIMAL(10, 4))
    sharpe_ratio = Column(DECIMAL(10, 4))
    max_drawdown = Column(DECIMAL(10, 4))

    portfolio = relationship("Portfolio", back_populates="performance")


class MarketEvent(Base):
    __tablename__ = "Market_Events"

    event_id = Column(Integer, primary_key=True, index=True)
    event_date = Column(DateTime)
    event_type = Column(String(100))
    event_title = Column(String(500))
    event_description = Column(Text)
    affected_sectors = Column(Text)
    affected_regions = Column(Text)
    impact_level = Column(String(50))
    source_url = Column(String(500))


class PositionChangeLog(Base):
    __tablename__ = "Position_Changes_Log"

    log_id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("Portfolios.portfolio_id"))
    security_id = Column(Integer, ForeignKey("Securities.security_id"))
    change_date = Column(DateTime)
    change_type = Column(String(100))
    old_weight = Column(DECIMAL(5, 2))
    new_weight = Column(DECIMAL(5, 2))
    reason = Column(Text)
    related_event_id = Column(Integer, ForeignKey("Market_Events.event_id"), nullable=True)


class RiskMetric(Base):
    __tablename__ = "Risk_Metrics"

    metric_id    = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("Portfolios.portfolio_id"), nullable=False)
    computed_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    var_data     = Column(Text)   # JSON
    stress_data  = Column(Text)   # JSON
    factor_data  = Column(Text)   # JSON
    price_date   = Column(Date)
    status       = Column(String(50), default="completed")

    portfolio = relationship("Portfolio")


class Alert(Base):
    __tablename__ = "Alerts"

    alert_id     = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("Portfolios.portfolio_id"), nullable=True)
    alert_type   = Column(String(50), nullable=False)   # threshold | event | ai
    severity     = Column(String(20), nullable=False)   # critical | warning | info
    title        = Column(String(255), nullable=False)
    message      = Column(Text, nullable=False)
    is_read      = Column(Integer, default=0)           # 0=unread, 1=read
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    portfolio = relationship("Portfolio")
