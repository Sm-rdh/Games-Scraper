"""
scraper_runner.py — Orchestrates Steam + Epic scrapers.

Run directly:  python -m scrapers.scraper_runner
Or import:     from scrapers.scraper_runner import run_all_scrapers
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from config import settings, ensure_data_dirs
from scrapers.steam_scraper import run_steam_scraper
from scrapers.epic_scraper  import run_epic_scraper

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def run_all_scrapers(max_steam_games: int = 60) -> dict:
    """
    Run both scrapers and save a combined manifest to project_data/processed/.
    Returns a summary dict.
    """
    ensure_data_dirs()

    logger.info("━" * 60)
    logger.info("  games-scraper — Full Scrape Run")
    logger.info(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("━" * 60)

    # ── Steam ─────────────────────────────────────────────────────────────────
    steam_games = run_steam_scraper(max_games=max_steam_games)

    # ── Epic ──────────────────────────────────────────────────────────────────
    epic_games  = run_epic_scraper()

    # ── Save combined manifest ────────────────────────────────────────────────
    manifest = {
        "scraped_at":   datetime.now().isoformat(),
        "steam_count":  len(steam_games),
        "epic_count":   len(epic_games),
        "total_count":  len(steam_games) + len(epic_games),
        "steam_file":   str(settings.STEAM_DATA_DIR / "game_details.json"),
        "epic_file":    str(settings.EPIC_DATA_DIR   / "all_games.json"),
    }

    manifest_path = settings.PROCESSED_DATA_DIR / "scrape_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info("━" * 60)
    logger.info(f"  ✅ Steam games scraped : {manifest['steam_count']}")
    logger.info(f"  ✅ Epic games scraped  : {manifest['epic_count']}")
    logger.info(f"  ✅ Total               : {manifest['total_count']}")
    logger.info(f"  📄 Manifest saved      : {manifest_path}")
    logger.info("━" * 60)

    return manifest


if __name__ == "__main__":
    run_all_scrapers()