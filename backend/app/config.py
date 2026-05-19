from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    port: int = 8765
    host: str = "127.0.0.1"
    log_level: str = "info"
    version: str = "0.1.0"

    # Provider selection
    llm_provider: str = "gemini"
    tts_provider: str = "mock"

    # Gemini config (only used when llm_provider=gemini)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    # Render limits
    max_concurrent_variants: int = 2
    max_event_buffer: int = 500

    # Paths
    temp_dir: str = "temp"
    output_dir: str = "output"


settings = Settings()
