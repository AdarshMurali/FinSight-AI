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
        "https://www.fin-sightai.space",
        "https://fin-sightai.space",
    ]

    JWT_SECRET_KEY: str = "dev-only-insecure-key-override-in-env"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_MINUTES: int = 60
    JWT_REFRESH_TOKEN_DAYS: int = 7
    # Secure cookies are only ever sent over HTTPS by browsers AND curl/http clients —
    # unlike a browser's fetch(), there is no "localhost is a secure context" exception
    # here, so local HTTP dev/testing needs this off. Production (real HTTPS) must keep
    # it True — override via COOKIE_SECURE=True in the EC2 .env.
    COOKIE_SECURE: bool = True

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
