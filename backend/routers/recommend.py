"""
recommend.py — FastAPI router for the recommendation endpoint.
"""
import json
from fastapi.responses import JSONResponse
from config import settings
from scrapers.scraper_runner import run_all_scrapers
from fastapi import APIRouter, HTTPException
from models.quiz     import QuizAnswers, QUIZ_QUESTIONS
from ml.pipeline     import get_recommendations, reload_data

router = APIRouter(prefix="/api", tags=["Recommendations"])


@router.get("/questions")
async def get_questions():
    """Returns the quiz questions and options for the frontend."""
    return {"questions": QUIZ_QUESTIONS}


@router.post("/recommend")
async def get_game_recommendations(answers: QuizAnswers):
    """
    Accepts quiz answers, returns ranked game recommendations.
    """
    try:
        results = get_recommendations(
            answers=answers.model_dump(),
            top_n=answers.top_n,
        )
        return {
            "count":   len(results),
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_game_data():
    """Force reload of scraped data into the recommender cache."""
    summary = reload_data()
    return {"status": "reloaded", **summary}

@router.get("/manifest")
async def get_manifest():
    """Returns stats from the last scrape run."""
    manifest_path = settings.PROCESSED_DATA_DIR / "scrape_manifest.json"
    if not manifest_path.exists():
        return {"steam_count": 0, "epic_count": 0, "scraped_at": None}
    with open(manifest_path) as f:
        return json.load(f)


@router.post("/scrape")
async def trigger_scrape():
    """Re-runs the full scraper pipeline."""
    try:
        manifest = run_all_scrapers()
        return manifest
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))