from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # App identity
    # ------------------------------------------------------------------
    app_name: str = Field(default="youtube-emotionscope")
    app_version: str = Field(default="0.1.0")
    app_env: str = Field(default="development")

    # ------------------------------------------------------------------
    # Demo / live access behavior
    # ------------------------------------------------------------------
    demo_mode_enabled: bool = Field(default=True)
    live_mode_enabled: bool = Field(default=True)
    app_access_token: str = Field(default="change-me")
    live_request_limit: int = Field(default=3, ge=1)

    # ------------------------------------------------------------------
    # External APIs
    # ------------------------------------------------------------------
    openai_api_key: str = Field(default="")
    youtube_api_key: str = Field(default="")

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------
    generation_provider: str = Field(default="openai")
    classification_model: str = Field(default="gpt-4o-mini")
    description_model: str = Field(default="gpt-4o-mini")

    # ------------------------------------------------------------------
    # Fetch settings
    # ------------------------------------------------------------------
    fetch_all_comments: bool = Field(default=True)
    max_comments_to_fetch: int = Field(default=1000, ge=50)
    youtube_comment_order: str = Field(default="relevance")

    # ------------------------------------------------------------------
    # Preprocessing / sampling settings
    # ------------------------------------------------------------------
    sample_size: int = Field(default=80, ge=10)
    random_seed: int = Field(default=42)
    min_text_length: int = Field(default=2, ge=1)
    deduplicate_comments: bool = Field(default=True)

    # ------------------------------------------------------------------
    # Batch classification settings
    # ------------------------------------------------------------------
    classification_batch_size: int = Field(default=20, ge=1, le=100)

    # ------------------------------------------------------------------
    # Aggregation settings
    # ------------------------------------------------------------------
    top_primary_emotions_limit: int = Field(default=5, ge=1, le=8)
    top_nuanced_emotions_limit: int = Field(default=5, ge=1, le=20)
    representative_comments_limit: int = Field(default=8, ge=1, le=50)
    timeline_bucket_count: int = Field(default=8, ge=2, le=50)
    min_nuanced_emotion_frequency: int = Field(default=2, ge=1)

    # ------------------------------------------------------------------
    # Artifact and cache settings
    # ------------------------------------------------------------------
    save_artifacts: bool = Field(default=True)
    use_cache: bool = Field(default=True)

    cache_dir: str = Field(default="data/cache")
    raw_cache_dir: str = Field(default="data/cache/raw")
    analysis_cache_dir: str = Field(default="data/cache/analysis")

    artifacts_dir: str = Field(default="data/artifacts")
    raw_artifacts_dir: str = Field(default="data/artifacts/raw")
    cleaned_artifacts_dir: str = Field(default="data/artifacts/cleaned")
    sampled_artifacts_dir: str = Field(default="data/artifacts/sampled")
    classified_artifacts_dir: str = Field(default="data/artifacts/classified")
    final_artifacts_dir: str = Field(default="data/artifacts/final")

    demo_data_path: str = Field(default="data/demo/demo_video_analysis.json")

    # ------------------------------------------------------------------
    # Tracing
    # ------------------------------------------------------------------
    langsmith_tracing: bool = Field(default=False)
    langsmith_project: str = Field(default="youtube-emotionscope-dev")
    langsmith_api_key: str = Field(default="")

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------
    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cache_path(self) -> Path:
        return BASE_DIR / self.cache_dir

    @property
    def raw_cache_path(self) -> Path:
        return BASE_DIR / self.raw_cache_dir

    @property
    def analysis_cache_path(self) -> Path:
        return BASE_DIR / self.analysis_cache_dir

    @property
    def artifacts_path(self) -> Path:
        return BASE_DIR / self.artifacts_dir

    @property
    def raw_artifacts_path(self) -> Path:
        return BASE_DIR / self.raw_artifacts_dir

    @property
    def cleaned_artifacts_path(self) -> Path:
        return BASE_DIR / self.cleaned_artifacts_dir

    @property
    def sampled_artifacts_path(self) -> Path:
        return BASE_DIR / self.sampled_artifacts_dir

    @property
    def classified_artifacts_path(self) -> Path:
        return BASE_DIR / self.classified_artifacts_dir

    @property
    def final_artifacts_path(self) -> Path:
        return BASE_DIR / self.final_artifacts_dir

    @property
    def demo_file_path(self) -> Path:
        return BASE_DIR / self.demo_data_path

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def validate_required_keys_for_live_mode(self) -> None:
        if self.live_mode_enabled and self.generation_provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when live mode is enabled.")

        if self.live_mode_enabled and not self.youtube_api_key:
            raise ValueError("YOUTUBE_API_KEY is required when live mode is enabled.")

    def ensure_directories(self) -> None:
        paths = [
            self.cache_path,
            self.raw_cache_path,
            self.analysis_cache_path,
            self.artifacts_path,
            self.raw_artifacts_path,
            self.cleaned_artifacts_path,
            self.sampled_artifacts_path,
            self.classified_artifacts_path,
            self.final_artifacts_path,
            self.demo_file_path.parent,
        ]
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings


settings = get_settings()