"""
Incremental match scraper for updating with new matches.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set

from app.services.matches.details import HLTVMatchDetails
from app.services.matches.results import HLTVMatchResults
from app.storage.base import StorageBackend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IncrementalScraper:
    """
    Scraper for incrementally updating with new matches.

    Features:
    - Only scrapes matches not already in storage
    - Configurable lookback period
    - Deduplication using storage backend
    - Rate limiting
    """

    def __init__(
        self,
        storage: StorageBackend,
        delay_seconds: float = 2.0,
        max_retries: int = 3,
        lookback_days: int = 7,
    ):
        """
        Initialize incremental scraper.

        Args:
            storage: Storage backend for persistence and deduplication
            delay_seconds: Delay between requests
            max_retries: Max retries for failed requests
            lookback_days: Number of days to look back for new matches
        """
        self.storage = storage
        self.delay_seconds = delay_seconds
        self.max_retries = max_retries
        self.lookback_days = lookback_days

    def _scrape_match_with_retry(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Scrape a single match with retry logic."""
        for attempt in range(self.max_retries):
            try:
                scraper = HLTVMatchDetails(match_id=match_id)
                data = scraper.get_match_details()
                return data
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for match {match_id}: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self.delay_seconds * (attempt + 1)
                    time.sleep(wait_time)

        logger.error(f"All attempts failed for match {match_id}")
        return None

    def _get_date_range(self) -> tuple[str, str]:
        """Get date range for incremental scraping."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days)
        return (
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )

    def _get_new_match_ids(self) -> List[str]:
        """Get match IDs that aren't already in storage."""
        start_date, end_date = self._get_date_range()
        logger.info(f"Checking for new matches from {start_date} to {end_date}")

        # Get existing match IDs
        existing_ids: Set[str] = set(self.storage.get_scraped_match_ids())
        logger.info(f"Found {len(existing_ids)} existing matches in storage")

        # Get recent match IDs from HLTV
        all_ids = []
        offset = 0
        has_more = True

        while has_more:
            try:
                results = HLTVMatchResults(
                    offset=offset,
                    start_date=start_date,
                    end_date=end_date,
                )
                data = results.get_results()

                matches = data.get("matches", [])
                ids = [m["match_id"] for m in matches]
                all_ids.extend(ids)

                has_more = data.get("has_more", False)
                offset = data.get("next_offset", offset + 100)

                time.sleep(self.delay_seconds)

            except Exception as e:
                logger.error(f"Error fetching results at offset {offset}: {e}")
                has_more = False

        # Filter out existing matches
        new_ids = [mid for mid in all_ids if mid not in existing_ids]
        logger.info(f"Found {len(new_ids)} new matches to scrape")

        return new_ids

    def update(self) -> Dict[str, Any]:
        """
        Run incremental update.

        Returns:
            dict: Summary of update results
        """
        logger.info("Starting incremental update...")

        # Get new match IDs
        new_ids = self._get_new_match_ids()

        if not new_ids:
            logger.info("No new matches found")
            return {
                "status": "no_updates",
                "new_matches": 0,
                "failed_matches": 0,
            }

        # Scrape and save new matches
        scraped = 0
        failed = 0
        failed_ids = []

        for i, match_id in enumerate(new_ids):
            logger.info(f"Scraping match {match_id} ({i + 1}/{len(new_ids)})")

            match_data = self._scrape_match_with_retry(match_id)

            if match_data:
                if self.storage.save_match(match_data):
                    scraped += 1
                else:
                    logger.warning(f"Match {match_id} already exists (duplicate)")
            else:
                failed += 1
                failed_ids.append(match_id)

            time.sleep(self.delay_seconds)

        summary = {
            "status": "completed",
            "new_matches": scraped,
            "failed_matches": failed,
            "failed_ids": failed_ids,
            "total_in_storage": self.storage.get_match_count(),
        }

        logger.info(f"Incremental update complete: {summary}")
        return summary


