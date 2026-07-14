"""
Centralized application configuration, loaded from environment variables.
Keeping every tunable in one place makes the security posture auditable
at a glance instead of scattered across the codebase.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- General ---
    app_name: str = "Fetchly API"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    # --- Storage ---
    # Temp downloads live here, keyed by job id, and are swept on a TTL.
    download_dir: str = "/tmp/fetchly-downloads"
    job_ttl_seconds: int = 60 * 30  # 30 minutes — plenty to finish a download

    # --- Limits (abuse / resource protection) ---
    max_video_duration_seconds: int = 60 * 60 * 4  # 4 hours
    max_concurrent_jobs_per_ip: int = 3
    max_concurrent_jobs_global: int = 20
    rate_limit_requests_per_minute: int = 20

    # --- Security ---
    # Only these extractors are allowed to run. This is the single most
    # important safeguard in this app: yt-dlp's generic extractor will
    # attempt to fetch *any* URL you give it, which is a textbook SSRF
    # vector (e.g. a crafted URL pointing at an internal metadata service
    # or localhost admin panel). Restricting to named, known extractors
    # means yt-dlp only ever talks to the specific platforms it has
    # purpose-built parsers for.
    allowed_extractors: str = (
        "youtube,twitter,instagram,facebook,tiktok,reddit,vimeo,"
        "dailymotion,twitch,pinterest,linkedin,snapchat,streamable"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_extractors_list(self) -> list[str]:
        return [e.strip() for e in self.allowed_extractors.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
