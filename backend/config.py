from pydantic_settings import BaseSettings
from typing import List
import os
from urllib.parse import quote_plus


class Settings(BaseSettings):
    DB_SERVER: str = "localhost"
    DB_PORT: int = 1433
    DB_NAME: str = "FinSight_AI"
    DB_USER: str = "sa"
    DB_PASSWORD: str = ""

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True

    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @property
    def database_url(self) -> str:
        connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={self.DB_SERVER},{self.DB_PORT};"
            f"Database={self.DB_NAME};"
            f"UID={self.DB_USER};"
            f"PWD={self.DB_PASSWORD};"
        )

        return "mssql+pyodbc:///?odbc_connect=" + quote_plus(connection_string)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
