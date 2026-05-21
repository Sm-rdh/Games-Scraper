"""
pipeline.py — Loads game data, encodes it, and runs the recommender.
This is the single entry point the FastAPI router will call.
"""

import logging
import pandas as pd

from ml.encoder       import load_all_games, encode_games
from ml.knn_recommender import recommend

logger = logging.getLogger(__name__)

# Module-level cache so we only encode once per server run
_matrix:   pd.DataFrame | None = None
_metadata: list | None         = None


def _load_or_cache() -> tuple:
    global _matrix, _metadata
    if _matrix is None or _metadata is None:
        logger.info("Loading and encoding game data...")
        games = load_all_games()
        if not games:
            logger.error("No games found — run the scraper first")
            return pd.DataFrame(), []
        _matrix, _metadata = encode_games(games)
    return _matrix, _metadata


def get_recommendations(answers: dict, top_n: int = 10) -> list:
    """
    Main function called by the API router.

    answers: {
        "genre":       "action" | "rpg" | ...
        "pacing":      "fast" | "medium" | "slow"
        "art_style":   "realistic" | "cartoon" | ...
        "multiplayer": "solo" | "co-op" | "competitive" | "any"
    }
    """
    matrix, metadata = _load_or_cache()
    return recommend(answers, matrix, metadata, top_n=top_n)


def reload_data() -> dict:
    """Force a fresh reload of game data (call after re-scraping)."""
    global _matrix, _metadata
    _matrix, _metadata = None, None
    matrix, metadata = _load_or_cache()
    return {"games_loaded": len(metadata)}