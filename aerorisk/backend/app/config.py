from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://aerorisk:aerorisk_secure_2024@localhost:5432/aerorisk"
    secret_key: str = "aerorisk-demo-secret"
    seed_on_startup: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
