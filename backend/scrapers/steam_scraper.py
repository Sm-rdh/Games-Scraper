"""
steam_scraper.py — Keyless Steam public storefront scraper.

Endpoints used (no API key required):
  - /api/featured          → featured games list with app IDs
  - /api/appdetails?appids → full metadata per app ID
  - /api/featuredcategories → top sellers, new releases, specials

Data is saved to: project_data/steam/
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional

import requests

from config import settings

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
STEAM_BASE          = "https://store.steampowered.com"
STEAM_API_BASE      = "https://store.steampowered.com/api"
STEAM_FEATURED_URL  = f"{STEAM_API_BASE}/featured"
STEAM_CATEGORIES_URL= f"{STEAM_API_BASE}/featuredcategories"
STEAM_APPDETAILS_URL= f"{STEAM_API_BASE}/appdetails"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Polite delay between detail requests (seconds) — avoids rate limiting
REQUEST_DELAY = 0.8


# ── Helpers ──────────────────────────────────────────────────────────────────
def _get(url: str, params: dict = None) -> Optional[dict]:
    """GET with error handling. Returns parsed JSON or None."""
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"Steam request failed — {url}: {e}")
        return None


def _save(data: dict | list, filename: str) -> Path:
    """Save data as pretty-printed JSON to the steam data directory."""
    out_path = settings.STEAM_DATA_DIR / filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved → {out_path} ({len(str(data))} chars)")
    return out_path


# ── Scraper functions ─────────────────────────────────────────────────────────
def scrape_featured() -> list[dict]:
    """
    Fetch the Steam featured games list.
    Returns a flat list of game dicts with basic metadata.
    """
    logger.info("Fetching Steam featured games...")
    data = _get(STEAM_FEATURED_URL)
    if not data:
        return []

    games = []
    # Featured has multiple categories: large_capsules, featured_win, etc.
    for category_key, category_data in data.items():
        if not isinstance(category_data, dict):
            continue
        items = category_data.get("items", [])
        for item in items:
            if item.get("id"):
                games.append({
                    "app_id":       item.get("id"),
                    "name":         item.get("name", "Unknown"),
                    "discounted":   item.get("discounted", False),
                    "original_price": item.get("original_price", 0),
                    "final_price":  item.get("final_price", 0),
                    "header_image": item.get("header_image", ""),
                    "source":       "steam_featured",
                    "category":     category_key,
                })

    # Deduplicate by app_id
    seen = set()
    unique_games = []
    for g in games:
        if g["app_id"] not in seen:
            seen.add(g["app_id"])
            unique_games.append(g)

    logger.info(f"Found {len(unique_games)} unique featured games")
    _save(unique_games, "featured_games.json")
    return unique_games


def scrape_featured_categories() -> dict:
    """
    Fetch top sellers, new releases, specials, coming soon.
    Returns a dict keyed by category name.
    """
    logger.info("Fetching Steam featured categories...")
    data = _get(STEAM_CATEGORIES_URL)
    if not data:
        return {}

    categories = {}
    target_keys = ["top_sellers", "new_releases", "specials", "coming_soon"]

    for key in target_keys:
        cat_data = data.get(key, {})
        items = cat_data.get("items", [])
        categories[key] = [
            {
                "app_id":       item.get("id"),
                "name":         item.get("name", "Unknown"),
                "final_price":  item.get("final_price", 0),
                "header_image": item.get("header_image", ""),
                "source":       f"steam_{key}",
            }
            for item in items if item.get("id")
        ]
        logger.info(f"  {key}: {len(categories[key])} games")

    _save(categories, "categories.json")
    return categories


def scrape_app_details(app_ids: list[int], max_games: int = 60) -> list[dict]:
    """
    Fetch full metadata for each app_id using /api/appdetails.
    Includes genres, tags, descriptions, platforms, screenshots.

    max_games caps requests to avoid long waits during dev.
    """
    logger.info(f"Fetching details for {min(len(app_ids), max_games)} apps...")
    detailed_games = []

    for i, app_id in enumerate(app_ids[:max_games]):
        data = _get(STEAM_APPDETAILS_URL, params={"appids": app_id, "cc": "us", "l": "en"})
        time.sleep(REQUEST_DELAY)

        if not data:
            continue

        app_data = data.get(str(app_id), {})
        if not app_data.get("success"):
            continue

        game = app_data.get("data", {})
        if game.get("type") not in ("game", "dlc"):
            continue

        # Extract genres as a flat list of strings
        genres = [g.get("description", "") for g in game.get("genres", [])]

        # Extract categories (multiplayer, co-op, etc.)
        cats = [c.get("description", "") for c in game.get("categories", [])]

        # Extract platform support
        platforms = game.get("platforms", {})

        detailed_games.append({
            "app_id":           app_id,
            "name":             game.get("name", ""),
            "type":             game.get("type", ""),
            "short_description":game.get("short_description", ""),
            "header_image":     game.get("header_image", ""),
            "developers":       game.get("developers", []),
            "publishers":       game.get("publishers", []),
            "genres":           genres,
            "categories":       cats,
            "platforms": {
                "windows": platforms.get("windows", False),
                "mac":     platforms.get("mac", False),
                "linux":   platforms.get("linux", False),
            },
            "release_date":     game.get("release_date", {}).get("date", ""),
            "price_usd":        game.get("price_overview", {}).get("final_formatted", "Free"),
            "metacritic_score": game.get("metacritic", {}).get("score", None),
            "recommendations":  game.get("recommendations", {}).get("total", 0),
            "achievements_total": game.get("achievements", {}).get("total", 0),
            "screenshots":      [
                s.get("path_thumbnail", "")
                for s in game.get("screenshots", [])[:3]
            ],
            "source": "steam_appdetails",
        })

        if (i + 1) % 10 == 0:
            logger.info(f"  Progress: {i+1}/{min(len(app_ids), max_games)}")

    logger.info(f"Scraped details for {len(detailed_games)} games")
    _save(detailed_games, "game_details.json")
    return detailed_games


def run_steam_scraper(max_games: int = 60) -> list[dict]:
    """
    Full Steam scrape pipeline:
      1. Fetch featured games
      2. Fetch category lists (top sellers, new releases, etc.)
      3. Merge all app IDs
      4. Fetch full details for each
    Returns the final detailed game list.
    """
    logger.info("=" * 50)
    logger.info("Starting Steam scrape pipeline")
    logger.info("=" * 50)

    # Step 1 & 2: Collect app IDs from multiple sources
    featured   = scrape_featured()
    categories = scrape_featured_categories()

    all_ids = {g["app_id"] for g in featured}
    for cat_games in categories.values():
        for g in cat_games:
            if g.get("app_id"):
                all_ids.add(g["app_id"])

    logger.info(f"Total unique app IDs collected: {len(all_ids)}")

    # Step 3: Fetch full details
    detailed = scrape_app_details(list(all_ids), max_games=max_games)

    logger.info("Steam scrape pipeline complete.")
    return detailed