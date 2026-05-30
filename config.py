"""
配置管理模块
集中管理所有配置项，支持环境变量覆盖
"""
import os
from datetime import timedelta

# ============ 数据库配置 ============
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "108045")
DB_NAME = os.getenv("DB_NAME", "product_db")

# ============ JWT 配置 ============
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "720"))  # 12小时

# ============ API Keys ============
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")

# ============ 向量数据库配置 ============
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./my_vectordb")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

# ============ Redis 配置 (可选) ============
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# ============ 分页配置 ============
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# ============ CORS 配置 ============
CORS_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:8080",
    "http://120.55.95.8:8000",
    "http://120.55.95.8:8080",
    "*",
]
