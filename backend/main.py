"""
main.py — FastAPI application entry point.
Routers for scraping, ML, and frontend serving will be
registered here in later milestones.
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from config import settings, ensure_data_dirs


# ── Bootstrap local data directories on startup ──────────────────────────────
ensure_data_dirs()

# ── App factory ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Keyless Steam & Epic scraper with Weighted KNN recommendations.",
)

# ── CORS (permissive for local dev; tighten for production) ──────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files & Jinja2 templates ──────────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR / "static")),
    name="static",
)

templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "data_root": str(settings.DATA_ROOT),
    }


# ── Root — serves the frontend shell (Milestone 4 will populate it) ──────────
@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})