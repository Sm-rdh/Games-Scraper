"""
config.py — Central application settings via pydantic-settings.
All paths are resolved relative to the project root so the app
works regardless of where it is launched from.
"""
from pathlib import Path
from pydantic_settings import BaseSettings


# Absolute path to the project root (one level above /backend)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # App metadata
    APP_NAME: str = "games-scraper"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Local data directories (gitignored)
    DATA_ROOT: Path = PROJECT_ROOT / "project_data"
    STEAM_DATA_DIR: Path = PROJECT_ROOT / "project_data" / "steam"
    EPIC_DATA_DIR: Path = PROJECT_ROOT / "project_data" / "epic"
    PROCESSED_DATA_DIR: Path = PROJECT_ROOT / "project_data" / "processed"

    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton — import this everywhere
settings = Settings()


def ensure_data_dirs() -> None:
    """Create all local data directories if they don't exist yet."""
    for directory in [
        settings.DATA_ROOT,
        settings.STEAM_DATA_DIR,
        settings.EPIC_DATA_DIR,
        settings.PROCESSED_DATA_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)