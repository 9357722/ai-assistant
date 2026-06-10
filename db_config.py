"""Shared database connection settings for scripts and tests."""
import os

from dotenv import load_dotenv

load_dotenv()


def _port() -> int:
    return int(os.getenv("DB_PORT", "3306"))


def get_pymysql_config() -> dict:
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": _port(),
        "user": os.getenv("DB_USER", "app_user"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "product_db"),
        "charset": "utf8mb4",
    }


def get_aiomysql_config() -> dict:
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": _port(),
        "user": os.getenv("DB_USER", "app_user"),
        "password": os.getenv("DB_PASSWORD", ""),
        "db": os.getenv("DB_NAME", "product_db"),
        "charset": "utf8mb4",
    }
