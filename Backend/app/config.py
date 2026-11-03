from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    approval_token_secret: str

    groq_small_model: str = "llama-3.1-8b-instant"
    groq_fallback_model: str = "openai/gpt-oss-120b"
    gemini_strong_model: str = "gemini-3.8-flash"
    gemini_vision_model: str = "gemini-3.8-flash"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "BAAI/bge-reranker-base"

    mcp_url: str = ""

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    email_from: str = "claims@claimpilot.local"

    storage_dir: str = "./storage"
    max_upload_mb: int = 10
    max_files_per_claim: int = 15
    approval_amount_limit: int = 50000
    claim_token_budget: int = 30000


settings = Settings()