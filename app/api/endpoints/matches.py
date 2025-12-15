"""
API endpoints for HLTV match data.
"""
from typing import Optional

from fastapi import APIRouter, Query, BackgroundTasks

from app.schemas.matches import (
    MatchDetails,
    MatchResultsPage,
)
from app.services.matches import (
    HLTVMatchDetails,
    HLTVMatchResults,
)
from app.services.matches.upcoming import (
    HLTVUpcomingMatches,
    HLTVMatchLineup,
)
from app.storage.postgres_storage import PostgresStorage
from app.workers.scraper import HistoricalMatchScraper
from app.workers.incremental import IncrementalScraper

router = APIRouter()

# Global scraper instances for status tracking
_scraper_instance: Optional[HistoricalMatchScraper] = None
_incremental_instance: Optional[IncrementalScraper] = None


# ============================================================
# Static Routes (must come before /{match_id} routes)
# ============================================================


@router.get(
    "/results",
    response_model=MatchResultsPage,
    response_model_exclude_none=True,
    summary="Get paginated match results",
    description="Fetches match results from HLTV with optional date filtering and pagination.",
)
def get_match_results(
    offset: int = Query(default=0, ge=0, description="Pagination offset (increments of 100)"),
    start_date: Optional[str] = Query(
        default=None,
        description="Start date filter (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    end_date: Optional[str] = Query(
        default=None,
        description="End date filter (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
):
    """
    Get a paginated list of match results.

    - **offset**: Pagination offset (0, 100, 200, etc.)
    - **start_date**: Optional start date filter (YYYY-MM-DD)
    - **end_date**: Optional end date filter (YYYY-MM-DD)

    Returns a list of matches with basic info (teams, scores, event).
    """
    hltv = HLTVMatchResults(
        offset=offset,
        start_date=start_date,
        end_date=end_date,
    )
    return hltv.get_results()


@router.get(
    "/upcoming",
    response_model_exclude_none=True,
    summary="Get upcoming matches",
    description="Fetches upcoming matches from HLTV.",
)
def get_upcoming_matches(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum matches to return")
):
    """
    Get upcoming matches.

    - **limit**: Maximum number of matches to return (default 50)

    Returns a list of upcoming match IDs and URLs.
    """
    hltv = HLTVUpcomingMatches()
    return hltv.get_upcoming(limit=limit)


# ============================================================
# Scraping Endpoints (static routes)
# ============================================================


def _run_historical_scrape(
    start_date: Optional[str],
    end_date: Optional[str],
    delay: float,
    batch_size: int,
):
    """Background task for historical scraping."""
    global _scraper_instance

    storage = PostgresStorage()

    _scraper_instance = HistoricalMatchScraper(
        start_date=start_date,
        end_date=end_date,
        delay_seconds=delay,
        on_match_scraped=lambda m: storage.save_match(m),
    )

    _scraper_instance.scrape_all(batch_size=batch_size)


@router.post(
    "/scrape/historical",
    summary="Start historical match scraping",
    description="Triggers background scraping of historical matches to PostgreSQL.",
)
def start_historical_scrape(
    background_tasks: BackgroundTasks,
    start_date: Optional[str] = Query(
        default=None,
        description="Start date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    end_date: Optional[str] = Query(
        default=None,
        description="End date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    delay: float = Query(default=2.0, ge=0.5, description="Delay between requests (seconds)"),
    batch_size: int = Query(default=100, ge=10, description="Batch size for progress tracking"),
):
    """
    Start historical match scraping in the background.

    - **start_date**: Start date filter (YYYY-MM-DD)
    - **end_date**: End date filter (YYYY-MM-DD)
    - **delay**: Delay between requests (rate limiting)
    - **batch_size**: Number of matches per batch for progress tracking

    Returns immediately. Use /scrape/status to monitor progress.
    """
    background_tasks.add_task(
        _run_historical_scrape,
        start_date,
        end_date,
        delay,
        batch_size,
    )

    return {
        "status": "started",
        "message": "Historical scraping started in background",
        "config": {
            "start_date": start_date,
            "end_date": end_date,
            "delay": delay,
            "batch_size": batch_size,
        },
    }


@router.get(
    "/scrape/status",
    summary="Get scraping status",
    description="Check the current status of historical scraping.",
)
def get_scrape_status():
    """
    Get the current status of the historical scraper.

    Returns progress information including:
    - Total matches found
    - Matches scraped so far
    - Failed matches
    - Completion status
    """
    global _scraper_instance

    if _scraper_instance is None:
        return {
            "status": "idle",
            "message": "No scraping job running",
        }

    return {
        "status": "running" if not _scraper_instance.progress.completed else "completed",
        **_scraper_instance.get_status(),
    }


@router.get(
    "/storage/stats",
    summary="Get storage statistics",
    description="Get statistics about stored match data in PostgreSQL.",
)
def get_storage_stats():
    """
    Get statistics about the PostgreSQL storage.

    Returns:
    - Total matches stored
    - Total maps, player stats, teams, players
    - Last scraped date
    """
    storage = PostgresStorage()
    return storage.get_statistics()


def _run_incremental_update(
    delay: float,
    lookback_days: int,
):
    """Background task for incremental updates."""
    global _incremental_instance

    storage = PostgresStorage()

    _incremental_instance = IncrementalScraper(
        storage=storage,
        delay_seconds=delay,
        lookback_days=lookback_days,
    )

    _incremental_instance.update()


@router.post(
    "/scrape/incremental",
    summary="Start incremental update",
    description="Updates with new matches since last scrape.",
)
def start_incremental_update(
    background_tasks: BackgroundTasks,
    delay: float = Query(default=2.0, ge=0.5, description="Delay between requests"),
    lookback_days: int = Query(default=7, ge=1, description="Days to look back"),
):
    """
    Start incremental update in the background.

    Only scrapes new matches that aren't already in storage.

    - **delay**: Delay between requests
    - **lookback_days**: Number of days to look back for new matches
    """
    background_tasks.add_task(
        _run_incremental_update,
        delay,
        lookback_days,
    )

    return {
        "status": "started",
        "message": "Incremental update started in background",
        "config": {
            "delay": delay,
            "lookback_days": lookback_days,
        },
    }


# ============================================================
# Dynamic Routes (/{match_id} patterns - must come last)
# ============================================================


@router.get(
    "/{match_id}/details",
    response_model=MatchDetails,
    response_model_exclude_none=True,
    summary="Get match details",
    description="Fetches detailed information for a specific match including maps and player stats.",
)
def get_match_details(match_id: str):
    """
    Get detailed information for a specific match.

    - **match_id**: The HLTV match ID (e.g., '2388127')

    Returns match details including:
    - Team information (names, logos, scores)
    - Event information
    - Map results with scores
    - Player statistics (kills, deaths, ADR, rating, etc.)
    """
    hltv = HLTVMatchDetails(match_id=match_id)
    return hltv.get_match_details()


@router.get(
    "/{match_id}/maps",
    response_model_exclude_none=True,
    summary="Get match map results",
    description="Fetches only the map results for a specific match.",
)
def get_match_maps(match_id: str):
    """
    Get map results for a specific match.

    - **match_id**: The HLTV match ID

    Returns a list of map results with scores and winner.
    """
    hltv = HLTVMatchDetails(match_id=match_id)
    details = hltv.get_match_details()
    return {
        "match_id": match_id,
        "maps": details.get("maps", []),
    }


@router.get(
    "/{match_id}/stats",
    response_model_exclude_none=True,
    summary="Get match player statistics",
    description="Fetches player statistics for a specific match.",
)
def get_match_stats(match_id: str):
    """
    Get player statistics for a specific match.

    - **match_id**: The HLTV match ID

    Returns player statistics for both teams.
    """
    hltv = HLTVMatchDetails(match_id=match_id)
    details = hltv.get_match_details()
    return {
        "match_id": match_id,
        "team1_stats": details.get("team1_stats"),
        "team2_stats": details.get("team2_stats"),
    }


@router.get(
    "/{match_id}/lineup",
    response_model_exclude_none=True,
    summary="Get match lineup/roster",
    description="Fetches player lineups for a match (works for upcoming and completed matches).",
)
def get_match_lineup(match_id: str):
    """
    Get player lineups for a specific match.

    - **match_id**: The HLTV match ID

    Returns:
    - Team information (names, logos)
    - Player lineups with names and IDs
    - Match time and event info

    Works for both upcoming and completed matches.
    """
    hltv = HLTVMatchLineup(match_id=match_id)
    return hltv.get_lineups()
