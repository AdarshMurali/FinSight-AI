from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
import pyodbc


def get_pyodbc_connection():
    """Get a direct pyodbc connection for simple queries"""
    conn_str = (
        f"Driver={{ODBC Driver 17 for SQL Server}};"
        f"Server={settings.DB_SERVER},{settings.DB_PORT};"
        f"Database={settings.DB_NAME};"
        f"UID={settings.DB_USER};"
        f"PWD={settings.DB_PASSWORD};"
    )
    return pyodbc.connect(conn_str)


def get_sqlalchemy_engine():
    """Get SQLAlchemy engine for ORM operations"""
    engine = create_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    return engine


engine = get_sqlalchemy_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """Test database connectivity"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
