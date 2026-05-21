from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from config import settings, ensure_data_dirs
from routers.recommend import router as recommend_router

ensure_data_dirs()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Keyless Steam & Epic scraper with Weighted KNN recommendations.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))

app.include_router(recommend_router)

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }

@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})