"""
记忆管理配置
"""
import os

# ============ 工作记忆配置 ============
WORKING_MEMORY_TTL = int(os.getenv("WORKING_MEMORY_TTL", "86400"))  # 24小时
MAX_WORKING_MEMORY = int(os.getenv("MAX_WORKING_MEMORY", "50"))  # 最大条数

# ============ 长期记忆配置 ============
LONG_TERM_MEMORY_LIMIT = int(os.getenv("LONG_TERM_MEMORY_LIMIT", "100"))  # 查询限制
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))  # 相似度阈值
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))  # 置信度阈值

# ============ 记忆提取配置 ============
MEMORY_EXTRACTION_MODEL = os.getenv("MEMORY_EXTRACTION_MODEL", "deepseek-chat")
MEMORY_EXTRACTION_TEMPERATURE = float(os.getenv("MEMORY_EXTRACTION_TEMPERATURE", "0.3"))

# ============ 记忆管理策略 ============
AUTO_COMPRESS = os.getenv("AUTO_COMPRESS", "true").lower() == "true"
AUTO_DECAY = os.getenv("AUTO_DECAY", "true").lower() == "true"
DECAY_DAYS = int(os.getenv("DECAY_DAYS", "30"))  # 记忆衰减天数
COMPRESS_THRESHOLD = int(os.getenv("COMPRESS_THRESHOLD", "50"))  # 压缩阈值

# ============ Redis 键前缀 ============
WORKING_MEMORY_PREFIX = "working_memory:"
USER_PROFILE_PREFIX = "user_profile:"
MEMORY_CACHE_PREFIX = "memory_cache:"
