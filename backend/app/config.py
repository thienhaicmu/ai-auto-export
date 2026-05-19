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
    asset_provider: str = "mock"

    # Gemini config (only used when llm_provider=gemini)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    # Asset provider API keys (only used when asset_provider matches)
    pexels_api_key: str | None = None
    pixabay_api_key: str | None = None
    unsplash_access_key: str | None = None

    # Render limits
    max_concurrent_variants: int = 2
    max_event_buffer: int = 500

    # Timeouts (seconds)
    playwright_page_load_timeout: int = 30
    playwright_scene_ready_timeout: int = 15
    playwright_scene_capture_timeout: int = 300   # per-scene frame loop budget
    ffmpeg_scene_encode_timeout: int = 180        # per-scene clip encode
    ffmpeg_final_encode_timeout: int = 600        # full final-encode step

    # Paths
    temp_dir: str = "temp"
    output_dir: str = "output"

    # Cleanup
    temp_cleanup_ttl_hours: int = 24   # orphaned temp dirs older than this are deleted on startup
    preserve_failed_temp: bool = False  # keep temp dir on render failure for debugging


settings = Settings()
