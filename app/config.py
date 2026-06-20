"""Application configuration loaded from environment variables / .env file."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./contract_mgmt.db"
    upload_dir: str = "./uploads"
    secret_key: str = "change-me-in-production"
    session_ttl_hours: int = 24
    max_upload_size_mb: int = 10
    base_path: str = "/projects/contract-mgmt"
    app_version: str = "0.0.3"
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
