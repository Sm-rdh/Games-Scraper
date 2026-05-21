"""
epic_scraper.py — Keyless Epic Games public GraphQL catalog scraper.

Endpoint used (no API key required):
  Epic's public storefront GraphQL API at:
  https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions
  https://catalog-public-service-prod06.ol.epicgames.com/catalog/api/shared/namespace/...

We use the publicly documented free games + catalog endpoints.
Data is saved to: project_data/epic/
"""

import json
import logging
from pathlib import Path
from typing import Optional

import requests

from config import settings

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
EPIC_FREE_GAMES_URL = (
    "https://store-site-backend-static-ipv4.ak.epicgames.com"
    "/freeGamesPromotions?locale=en-US&country=US&allowCountries=US"
)

EPIC_GRAPHQL_URL = "https://graphql.epicgames.com/graphql"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type":    "application/json",
    "Origin":          "https://store.epicgames.com",
    "Referer":         "https://store.epicgames.com/",
}

# Public GraphQL query for Epic catalog browsing (no auth required)
CATALOG_QUERY = """
query searchStoreQuery(
  $count: Int
  $country: String!
  $locale: String
  $sortBy: String
  $sortDir: String
  $start: Int
  $tag: String
  $category: String
) {
  Catalog {
    searchStore(
      count: $count
      country: $country
      locale: $locale
      sortBy: $sortBy
      sortDir: $sortDir
      start: $start
      tag: $tag
      category: $category
    ) {
      elements {
        id
        title
        description
        keyImages {
          type
          url
        }
        seller {
          name
        }
        productSlug
        urlSlug
        tags {
          id
          name
        }
        categories {
          path
        }
        price(country: $country) {
          totalPrice {
            fmtPrice(locale: $locale) {
              originalPrice
              discountPrice
            }
          }
        }
        releaseDate
        effectiveDate
        offerType
      }
      paging {
        count
        total
      }
    }
  }
}
"""


# ── Helpers ──────────────────────────────────────────────────────────────────
def _save(data: dict | list, filename: str) -> Path:
    """Save data as pretty-printed JSON to the epic data directory."""
    out_path = settings.EPIC_DATA_DIR / filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved → {out_path}")
    return out_path


def _extract_image(key_images: list, preferred_type: str = "Thumbnail") -> str:
    """Pull the best available image URL from Epic's keyImages list."""
    priority = [preferred_type, "DieselStoreFrontWide", "OfferImageWide", "VaultClosed"]
    image_map = {img["type"]: img["url"] for img in key_images if img.get("url")}
    for p in priority:
        if p in image_map:
            return image_map[p]
    return next(iter(image_map.values()), "")


# ── Scraper functions ─────────────────────────────────────────────────────────
def scrape_free_games() -> list[dict]:
    """
    Fetch Epic's current and upcoming free game promotions.
    Uses a static public endpoint — no authentication needed.
    """
    logger.info("Fetching Epic free games promotions...")
    try:
        resp = requests.get(EPIC_FREE_GAMES_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error(f"Epic free games request failed: {e}")
        return []

    elements = (
        data.get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
    )

    games = []
    for item in elements:
        promotions = item.get("promotions") or {}
        promo_offers = promotions.get("promotionalOffers", [])
        upcoming_offers = promotions.get("upcomingPromotionalOffers", [])

        is_free_now    = len(promo_offers) > 0
        is_free_soon   = len(upcoming_offers) > 0

        if not (is_free_now or is_free_soon):
            continue

        tags = [t.get("name", "") for t in item.get("tags") or [] if t.get("name")]

        games.append({
            "id":           item.get("id", ""),
            "title":        item.get("title", ""),
            "description":  item.get("description", ""),
            "seller":       (item.get("seller") or {}).get("name", ""),
            "image":        _extract_image(item.get("keyImages") or []),
            "tags":         tags,
            "release_date": item.get("effectiveDate", ""),
            "is_free_now":  is_free_now,
            "is_free_soon": is_free_soon,
            "original_price": (
                item.get("price", {})
                    .get("totalPrice", {})
                    .get("fmtPrice", {})
                    .get("originalPrice", "Free")
            ),
            "source": "epic_free_games",
        })

    logger.info(f"Found {len(games)} Epic free/upcoming games")
    _save(games, "free_games.json")
    return games


def scrape_catalog(
    count: int = 40,
    sort_by: str = "releaseDate",
    sort_dir: str = "DESC",
    category: str = "games/edition/base|bundles/games|editors",
) -> list[dict]:
    """
    Query Epic's public GraphQL catalog endpoint.
    Returns normalized game dicts.
    """
    logger.info(f"Fetching Epic catalog (count={count}, sortBy={sort_by})...")

    payload = {
        "query": CATALOG_QUERY,
        "variables": {
            "count":    count,
            "country":  "US",
            "locale":   "en-US",
            "sortBy":   sort_by,
            "sortDir":  sort_dir,
            "start":    0,
            "category": category,
        },
    }

    try:
        resp = requests.post(EPIC_GRAPHQL_URL, headers=HEADERS, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error(f"Epic GraphQL request failed: {e}")
        return []

    elements = (
        data.get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
    )

    games = []
    for item in elements:
        # Filter to actual games only
        categories = [c.get("path", "") for c in item.get("categories") or []]
        if not any("games" in c for c in categories):
            continue

        tags = [t.get("name", "") for t in item.get("tags") or [] if t.get("name")]

        price_info = (
            item.get("price", {})
                .get("totalPrice", {})
                .get("fmtPrice", {})
        )

        games.append({
            "id":             item.get("id", ""),
            "title":          item.get("title", ""),
            "description":    item.get("description", ""),
            "seller":         (item.get("seller") or {}).get("name", ""),
            "image":          _extract_image(item.get("keyImages") or []),
            "tags":           tags,
            "categories":     categories,
            "release_date":   item.get("releaseDate", ""),
            "original_price": price_info.get("originalPrice", "Free"),
            "discount_price": price_info.get("discountPrice", "Free"),
            "product_slug":   item.get("productSlug", ""),
            "source":         "epic_catalog",
        })

    logger.info(f"Scraped {len(games)} Epic catalog games")
    return games


def run_epic_scraper() -> list[dict]:
    """
    Full Epic scrape pipeline:
      1. Free games promotions
      2. Latest releases catalog
      3. Top sellers catalog
    Returns merged, deduplicated game list.
    """
    logger.info("=" * 50)
    logger.info("Starting Epic Games scrape pipeline")
    logger.info("=" * 50)

    free_games    = scrape_free_games()
    latest        = scrape_catalog(count=40, sort_by="releaseDate",   sort_dir="DESC")
    top_sellers   = scrape_catalog(count=40, sort_by="pcReleaseDate", sort_dir="DESC")

    # Merge + deduplicate by title (Epic IDs can be inconsistent)
    seen_titles: set[str] = set()
    all_games: list[dict] = []

    for game in free_games + latest + top_sellers:
        title = game.get("title", "").strip().lower()
        if title and title not in seen_titles:
            seen_titles.add(title)
            all_games.append(game)

    logger.info(f"Total unique Epic games: {len(all_games)}")
    _save(all_games, "all_games.json")

    logger.info("Epic scrape pipeline complete.")
    return all_games