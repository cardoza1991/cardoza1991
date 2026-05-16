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

    # Autonomous trigger: when a new CRITICAL intel signal lands, auto-run the
    # impact simulator and emit a notification + persisted scenario.
    autonomous_impact_on_critical: bool = True
    autonomous_horizon_days: int = 90

    # Notification dispatchers. Leave blank to disable a channel. Console is
    # always enabled so the demo always has a visible audit trail.
    notification_webhook_url: str = ""
    notification_slack_webhook_url: str = ""
    notification_console_enabled: bool = True
    notification_http_timeout_seconds: float = 5.0

    # Sharable scenario URLs are served unauthenticated against the share_token.
    # Set a non-empty base URL so the brief includes a clickable link.
    public_base_url: str = "http://localhost:5173"

    class Config:
        env_file = ".env"

settings = Settings()
