"""
encoder.py — Turns raw scraped game JSON into a numeric
feature matrix that the KNN algorithm can work with.
"""

import json
import logging

import pandas as pd

from config import settings

logger = logging.getLogger(__name__)

# ── Mapping tables ────────────────────────────────────────────────────────────

GENRE_MAP = {
    "action":            "action",
    "action-adventure":  "action",
    "shooter":           "action",
    "fps":               "action",
    "fighting":          "action",
    "rpg":               "rpg",
    "role-playing":      "rpg",
    "jrpg":              "rpg",
    "strategy":          "strategy",
    "turn-based":        "strategy",
    "rts":               "strategy",
    "tower defense":     "strategy",
    "horror":            "horror",
    "survival horror":   "horror",
    "sports":            "sports",
    "racing":            "sports",
    "puzzle":            "puzzle",
    "puzzle-platformer": "puzzle",
    "adventure":         "adventure",
    "point & click":     "adventure",
    "visual novel":      "adventure",
    "simulation":        "simulation",
    "management":        "simulation",
    "city builder":      "simulation",
}

PACING_MAP = {
    "fast-paced":          "fast",
    "battle royale":       "fast",
    "roguelike":           "fast",
    "action":              "fast",
    "shooter":             "fast",
    "platformer":          "medium",
    "adventure":           "medium",
    "rpg":                 "medium",
    "open world":          "medium",
    "strategy":            "slow",
    "turn-based strategy": "slow",
    "simulation":          "slow",
    "puzzle":              "slow",
}

ART_STYLE_MAP = {
    "realistic":      "realistic",
    "photorealistic": "realistic",
    "3d":             "realistic",
    "cartoon":        "cartoon",
    "colorful":       "cartoon",
    "stylized":       "cartoon",
    "pixel art":      "pixel",
    "pixel":          "pixel",
    "retro":          "pixel",
    "8-bit":          "pixel",
    "anime":          "anime",
    "manga":          "anime",
    "cel-shaded":     "anime",
    "abstract":       "abstract",
    "minimalist":     "abstract",
    "low poly":       "abstract",
}

MULTIPLAYER_MAP = {
    "single-player": "solo",
    "singleplayer":  "solo",
    "multi-player":  "co-op",
    "multiplayer":   "co-op",
    "co-op":         "co-op",
    "online co-op":  "co-op",
    "local co-op":   "co-op",
    "pvp":           "competitive",
    "online pvp":    "competitive",
    "competitive":   "competitive",
}

ALL_GENRES      = ["action", "rpg", "strategy", "horror", "sports", "puzzle", "adventure", "simulation"]
ALL_PACINGS     = ["fast", "medium", "slow"]
ALL_ART_STYLES  = ["realistic", "cartoon", "pixel", "anime", "abstract"]
ALL_MULTIPLAYER = ["solo", "co-op", "competitive"]
ALL_PLATFORMS   = ["windows", "mac", "linux"]
ALL_PRICE_TIERS = ["free", "budget", "mid", "premium"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _n(text: str) -> str:
    return text.strip().lower()

def _derive_genre(tags: list, cats: list) -> list:
    found = {GENRE_MAP.get(_n(t)) for t in tags + cats if GENRE_MAP.get(_n(t))}
    return list(found) or ["action"]

def _derive_pacing(tags: list, cats: list) -> str:
    for t in tags + cats:
        m = PACING_MAP.get(_n(t))
        if m: return m
    return "medium"

def _derive_art_style(tags: list) -> str:
    for t in tags:
        m = ART_STYLE_MAP.get(_n(t))
        if m: return m
    return "realistic"

def _derive_multiplayer(cats: list) -> list:
    found = {MULTIPLAYER_MAP.get(_n(c)) for c in cats if MULTIPLAYER_MAP.get(_n(c))}
    return list(found) or ["solo"]

def _derive_price_tier(price_str: str) -> str:
    if not price_str or _n(str(price_str)) in ("free", "free to play", "$0.00"):
        return "free"
    try:
        amount = float(
            str(price_str).replace("$","").replace("£","")
                          .replace("€","").replace(",",".").strip()
        )
        if amount == 0:   return "free"
        if amount < 10:   return "budget"
        if amount < 30:   return "mid"
        return "premium"
    except ValueError:
        return "mid"

def _one_hot(values, all_values: list) -> list:
    if isinstance(values, str):
        values = [values]
    return [1 if v in values else 0 for v in all_values]


# ── Main encoder ──────────────────────────────────────────────────────────────

def load_all_games() -> list:
    games = []
    for filepath in [
        settings.STEAM_DATA_DIR / "game_details.json",
        settings.EPIC_DATA_DIR  / "all_games.json",
    ]:
        if filepath.exists():
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                games.extend(data)
            logger.info(f"Loaded {len(data)} games from {filepath.name}")
        else:
            logger.warning(f"Not found, skipping: {filepath.name}")
    return games


def encode_games(games: list) -> tuple:
    """
    Returns:
        matrix   — DataFrame of numeric feature vectors (one row per game)
        metadata — List of dicts with display info per game
    """
    rows, metadata = [], []

    for game in games:
        tags     = [_n(t) for t in game.get("tags",       []) if t]
        genres_r = [_n(g) for g in game.get("genres",     []) if g]
        cats_r   = [_n(c) for c in game.get("categories", []) if c]
        all_tags = tags + genres_r + cats_r

        genre       = _derive_genre(all_tags, cats_r)
        pacing      = _derive_pacing(all_tags, cats_r)
        art_style   = _derive_art_style(tags)
        multiplayer = _derive_multiplayer(cats_r)
        price_tier  = _derive_price_tier(
            game.get("price_usd") or game.get("original_price") or "Free"
        )

        platforms_raw = game.get("platforms", {})
        platforms = (
            [p for p in ALL_PLATFORMS if platforms_raw.get(p)]
            if isinstance(platforms_raw, dict) else ["windows"]
        )

        rows.append(
            _one_hot(genre,       ALL_GENRES)
          + _one_hot(pacing,      ALL_PACINGS)
          + _one_hot(art_style,   ALL_ART_STYLES)
          + _one_hot(multiplayer, ALL_MULTIPLAYER)
          + _one_hot(platforms,   ALL_PLATFORMS)
          + _one_hot(price_tier,  ALL_PRICE_TIERS)
        )

        metadata.append({
            "name":        game.get("name") or game.get("title") or "Unknown",
            "image":       game.get("header_image") or game.get("image") or "",
            "price":       game.get("price_usd") or game.get("original_price") or "Free",
            "source":      game.get("source", "unknown"),
            "genres":      genre,
            "pacing":      pacing,
            "art_style":   art_style,
            "multiplayer": multiplayer,
            "platforms":   platforms,
            "description": game.get("short_description") or game.get("description") or "",
            "metacritic":  game.get("metacritic_score"),
            "recommendations": game.get("recommendations", 0),
        })

    columns = (
        [f"genre_{g}"   for g in ALL_GENRES]
      + [f"pace_{p}"    for p in ALL_PACINGS]
      + [f"art_{a}"     for a in ALL_ART_STYLES]
      + [f"mp_{m}"      for m in ALL_MULTIPLAYER]
      + [f"plat_{p}"    for p in ALL_PLATFORMS]
      + [f"price_{t}"   for t in ALL_PRICE_TIERS]
    )

    matrix = pd.DataFrame(rows, columns=columns)
    logger.info(f"Encoded {len(matrix)} games into {len(columns)}-feature vectors")
    return matrix, metadata