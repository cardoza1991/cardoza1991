from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://aerorisk:aerorisk_secure_2024@localhost:5432/aerorisk"
    secret_key: str = "aerorisk-demo-secret"
    seed_on_startup: bool = True

    # Supplier intel agent
    intel_live_feeds: bool = False           # if False, only bundled fixtures are used (deterministic demo)
    intel_match_threshold: float = 86.0      # rapidfuzz token_set_ratio threshold (0..100)
    intel_refresh_interval_minutes: int = 30
    intel_http_timeout_seconds: float = 8.0

    class Config:
        env_file = ".env"

settings = Settings()
