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
    # IMPORTANT: these must match yt-dlp's actual registered IE_NAME
    # values exactly, not just "the platform name". Several platforms
    # split single-video extraction across multiple differently-named
    # extractor classes (verified against yt_dlp.extractor.gen_extractor_classes()
    # — don't guess names here, check the registry if adding a platform):
    #   - Facebook Reels are a SEPARATE extractor ("facebook:reel") from
    #     regular Facebook videos ("facebook") — this was silently
    #     broken (every /reel/ link failed) until this was added.
    #   - Twitch has NO bare "twitch" extractor at all — VODs and clips
    #     are "twitch:vod" / "twitch:clips" respectively. The old bare
    #     "twitch" entry matched nothing, ever.
    #   - Snapchat's only single-video extractor is "SnapchatSpotlight"
    #     — the old bare "snapchat" entry matched nothing, ever.
    allowed_extractors: str = (
        "youtube,twitter,instagram,instagram:story,facebook,facebook:reel,"
        "tiktok,reddit,vimeo,dailymotion,twitch:vod,twitch:clips,"
        "pinterest,linkedin,SnapchatSpotlight,streamable"
    )

    # Optional: path to a Netscape-format cookies.txt file, exported
    # from a real logged-in browser session. Only needed if the
    # player_client fallback in ytdlp_service.py isn't enough for a
    # particular video. See README for export instructions. Leave
    # empty to skip — most public videos don't need this.
    cookies_file: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_extractors_list(self) -> list[str]:
        return [e.strip() for e in self.allowed_extractors.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
