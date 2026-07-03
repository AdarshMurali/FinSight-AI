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
    DB_ODBC_DRIVER: str = "ODBC Driver 17 for SQL Server"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://frontend-sandy-seven-21.vercel.app",
    ]

    @property
    def database_url(self) -> str:
        is_azure = "database.windows.net" in self.DB_SERVER
        connection_string = (
            f"Driver={{{self.DB_ODBC_DRIVER}}};"
            f"Server={self.DB_SERVER},{self.DB_PORT};"
            f"Database={self.DB_NAME};"
            f"UID={self.DB_USER};"
            f"PWD={self.DB_PASSWORD};"
        )
        if is_azure:
            connection_string += "Encrypt=yes;TrustServerCertificate=no;"

        return "mssql+pyodbc:///?odbc_connect=" + quote_plus(connection_string)

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
