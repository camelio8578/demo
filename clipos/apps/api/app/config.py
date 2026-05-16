from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://clipos:clipos@localhost:5432/clipos"
    REDIS_URL: str = "redis://localhost:6379/0"
    DATA_DIR: str = "/data"
    SECRET_KEY: str = "change-me-in-production"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""
    WHISPER_MODEL: str = "base"
    LLM_PROVIDER: str = "openai"  # openai|anthropic|none
    MAX_CLIP_DURATION: int = 120
    MIN_CLIP_DURATION: int = 30
    SCORING_VERSION: str = "1.0"
    AUTO_RENDER: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
