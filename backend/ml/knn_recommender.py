"""
knn_recommender.py — Weighted K-Nearest Neighbours recommender.

How it works:
  1. The user's quiz answers are converted into a feature vector
     (same shape as the encoded game matrix).
  2. Feature groups are weighted so genre matters more than price.
  3. Cosine similarity finds the closest matching games.
  4. Top-N results are returned with their similarity scores.

Feature weights:
  genre      × 3.0  — most important, direct preference
  pacing     × 2.0  — second most important
  art_style  × 1.5  — noticeable but not deal-breaker
  multiplayer× 2.5  — strong preference signal
  platforms  × 1.0  — informational
  price_tier × 0.5  — least important
"""

import logging
import numpy as np
import pandas as pd

from ml.encoder import (
    ALL_GENRES, ALL_PACINGS, ALL_ART_STYLES,
    ALL_MULTIPLAYER, ALL_PLATFORMS, ALL_PRICE_TIERS,
    _one_hot,
)

logger = logging.getLogger(__name__)

# ── Weights per feature group ─────────────────────────────────────────────────
WEIGHTS = (
    [3.0] * len(ALL_GENRES)       # genre
  + [2.0] * len(ALL_PACINGS)      # pacing
  + [1.5] * len(ALL_ART_STYLES)   # art style
  + [2.5] * len(ALL_MULTIPLAYER)  # multiplayer
  + [1.0] * len(ALL_PLATFORMS)    # platforms
  + [0.5] * len(ALL_PRICE_TIERS)  # price tier
)
WEIGHT_VECTOR = np.array(WEIGHTS, dtype=float)


def _quiz_to_vector(answers: dict) -> np.ndarray:
    """
    Convert quiz answers dict into a weighted feature vector.

    answers keys: genre, pacing, art_style, multiplayer
    """
    genre       = answers.get("genre", "action")
    pacing      = answers.get("pacing", "medium")
    art_style   = answers.get("art_style", "realistic")
    multiplayer = answers.get("multiplayer", "solo")

    # "any" multiplayer = accept all — set all multiplayer bits to 1
    if multiplayer == "any":
        mp_vector = [1, 1, 1]
    else:
        mp_vector = _one_hot(multiplayer, ALL_MULTIPLAYER)

    raw_vector = np.array(
        _one_hot(genre,     ALL_GENRES)
      + _one_hot(pacing,    ALL_PACINGS)
      + _one_hot(art_style, ALL_ART_STYLES)
      + mp_vector
      + [1, 0, 0]        # assume Windows platform
      + [1, 1, 1, 1]     # accept all price tiers
    , dtype=float)

    return raw_vector * WEIGHT_VECTOR


def recommend(
    answers: dict,
    matrix: pd.DataFrame,
    metadata: list,
    top_n: int = 10,
) -> list:
    """
    Find the top_n most similar games to the user's quiz answers.

    Args:
        answers  — dict with keys: genre, pacing, art_style, multiplayer
        matrix   — encoded game DataFrame from encoder.encode_games()
        metadata — parallel list of game display dicts
        top_n    — number of results to return

    Returns:
        List of game dicts sorted by similarity (highest first),
        each with an added "match_score" field (0–100).
    """
    if matrix.empty:
        logger.warning("Game matrix is empty — returning no recommendations")
        return []

    # Weight the game matrix
    game_matrix = matrix.values.astype(float) * WEIGHT_VECTOR

    # Build user vector
    user_vec = _quiz_to_vector(answers)

    # Cosine similarity: dot(user, game) / (|user| * |game|)
    user_norm = np.linalg.norm(user_vec)
    if user_norm == 0:
        logger.warning("User vector is zero — defaulting to first results")
        return metadata[:top_n]

    game_norms = np.linalg.norm(game_matrix, axis=1)
    game_norms[game_norms == 0] = 1e-9  # avoid division by zero

    similarities = game_matrix.dot(user_vec) / (game_norms * user_norm)

    # Get top_n indices sorted by similarity descending
    top_indices = np.argsort(similarities)[::-1][:top_n]

    results = []
    for idx in top_indices:
        game = metadata[idx].copy()
        raw_score = float(similarities[idx])
        game["match_score"] = round(max(0.0, min(1.0, raw_score)) * 100, 1)
        results.append(game)

    logger.info(
        f"Returning {len(results)} recommendations "
        f"(top score: {results[0]['match_score']}%)"
    )
    return results