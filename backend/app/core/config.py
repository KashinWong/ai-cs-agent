from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM 网关
    llm_gateway_base_url: str = "http://localhost/v1"
    llm_gateway_api_key: str = "sk-none"
    llm_chat_model: str = "deepseek-v4-flash"
    # embedding 走网关（本环境无法下载本地 fastembed 模型）
    embedding_model: str = "nova-2-multimodal-embeddings-v1:0"
    embedding_dim: int = 3072

    # 基础设施
    mysql_dsn: str = "mysql+aiomysql://ai:ai@localhost:3306/ai_cs"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "kb_items"

    # seed 坐席
    seed_agent_username: str = "agent"
    seed_agent_password: str = "agent123"

    # 安全
    jwt_secret: str = "change-me-please"
    jwt_expire_hours: int = 8

    # 检索 / 引擎默认
    default_retrieval_threshold: float = 0.35
    default_top_k: int = 5

    # 开关
    enable_tenant_provisioning: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
