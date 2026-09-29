from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "VisionPrompt AI"
    app_version: str = "0.1.0"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    max_video_size_mb: int = 500
    vision_provider: str = "mock"
    vision_model_name: str = "Qwen2.5-VL"
    scene_change_threshold: float = 0.30
    scene_sample_interval_seconds: float = 1.0
    max_scenes: int = 100
    subject_match_threshold: float = 0.60
    max_subjects: int = 100
    audio_provider: str = "mock"
    audio_model_name: str = "small"

    model_config = ConfigDict(env_file=".env")


settings = Settings()
