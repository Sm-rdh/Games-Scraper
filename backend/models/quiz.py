"""
quiz.py — Data models for the onboarding quiz.

The quiz asks 4 questions. Each answer maps to a
feature vector that gets compared against the game database.
"""

from enum import Enum
from pydantic import BaseModel


# ── Question Option Enums ─────────────────────────────────────────────────────

class Genre(str, Enum):
    ACTION      = "action"
    RPG         = "rpg"
    STRATEGY    = "strategy"
    HORROR      = "horror"
    SPORTS      = "sports"
    PUZZLE      = "puzzle"
    ADVENTURE   = "adventure"
    SIMULATION  = "simulation"


class Pacing(str, Enum):
    FAST        = "fast"
    MEDIUM      = "medium"
    SLOW        = "slow"


class ArtStyle(str, Enum):
    REALISTIC   = "realistic"
    CARTOON     = "cartoon"
    PIXEL       = "pixel"
    ANIME       = "anime"
    ABSTRACT    = "abstract"


class MultiplayerPref(str, Enum):
    SOLO        = "solo"
    COOP        = "co-op"
    COMPETITIVE = "competitive"
    ANY         = "any"


# ── Quiz Submission Model ─────────────────────────────────────────────────────

class QuizAnswers(BaseModel):
    """Submitted by the user from the frontend quiz screen."""
    genre:       Genre
    pacing:      Pacing
    art_style:   ArtStyle
    multiplayer: MultiplayerPref
    top_n:       int = 10


# ── Quiz Question Definitions (sent to frontend) ──────────────────────────────

QUIZ_QUESTIONS = [
    {
        "id":       "genre",
        "question": "What kind of games do you enjoy most?",
        "options": [
            {"value": "action",     "label": "Action"},
            {"value": "rpg",        "label": "RPG"},
            {"value": "strategy",   "label": "Strategy"},
            {"value": "horror",     "label": "Horror"},
            {"value": "sports",     "label": "Sports"},
            {"value": "puzzle",     "label": "Puzzle"},
            {"value": "adventure",  "label": "Adventure"},
            {"value": "simulation", "label": "Simulation"},
        ],
    },
    {
        "id":       "pacing",
        "question": "How fast do you like your games?",
        "options": [
            {"value": "fast",   "label": "Fast & intense"},
            {"value": "medium", "label": "Balanced"},
            {"value": "slow",   "label": "Slow & thoughtful"},
        ],
    },
    {
        "id":       "art_style",
        "question": "Which art style appeals to you?",
        "options": [
            {"value": "realistic", "label": "Realistic"},
            {"value": "cartoon",   "label": "Cartoon"},
            {"value": "pixel",     "label": "Pixel art"},
            {"value": "anime",     "label": "Anime"},
            {"value": "abstract",  "label": "Abstract"},
        ],
    },
    {
        "id":       "multiplayer",
        "question": "How do you prefer to play?",
        "options": [
            {"value": "solo",        "label": "Solo only"},
            {"value": "co-op",       "label": "With friends"},
            {"value": "competitive", "label": "Competitive PvP"},
            {"value": "any",         "label": "No preference"},
        ],
    },
]