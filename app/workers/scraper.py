"""
Historical match scraper worker for batch processing HLTV matches.
"""
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from app.services.matches.details import HLTVMatchDetails
from app.services.matches.results import HLTVMatchResults

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ScraperProgress:
    """Track scraping progress for resume capability."""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    current_offset: int = 0
    total_matches_found: int = 0
    total_matches_scraped: int = 0
    failed_matches: List[str] = field(default_factory=list)
    last_match_id: Optional[str] = None
    started_at: Optional[str] = None
    last_updated: Optional[str] = None
    completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "current_offset": self.current_offset,
            "total_matches_found": self.total_matches_found,
            "total_matches_scraped": self.total_matches_scraped,
            "failed_matches": self.failed_matches,
            "last_match_id": self.last_match_id,
            "started_at": self.started_at,
            "last_updated": self.last_updated,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScraperProgress":
        return cls(
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            current_offset=data.get("current_offset", 0),
            total_matches_found=data.get("total_matches_found", 0),
            total_matches_scraped=data.get("total_matches_scraped", 0),
            failed_matches=data.get("failed_matches", []),
            last_match_id=data.get("last_match_id"),
            started_at=data.get("started_at"),
            last_updated=data.get("last_updated"),
            completed=data.get("completed", False),
        )


class HistoricalMatchScraper:
    """
    Worker for scraping historical HLTV matches.

    Features:
    - Paginate through results with date filtering
    - Rate limiting to avoid bans
    - Progress tracking for resume capability
    - Error handling with retry logic
    - Callback support for data persistence
    """

    def __init__(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        output_dir: str = "./data",
        delay_seconds: float = 2.0,
        max_retries: int = 3,
        on_match_scraped: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_batch_complete: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
    ):
        """
        Initialize the historical scraper.

        Args:
            start_date: Start date for filtering (YYYY-MM-DD)
            end_date: End date for filtering (YYYY-MM-DD)
            output_dir: Directory for output files and progress
            delay_seconds: Delay between requests (rate limiting)
            max_retries: Maximum retries for failed requests
            on_match_scraped: Callback for each scraped match
            on_batch_complete: Callback for completed batches
        """
        self.start_date = start_date
        self.end_date = end_date
        self.output_dir = Path(output_dir)
        self.delay_seconds = delay_seconds
        self.max_retries = max_retries
        self.on_match_scraped = on_match_scraped
        self.on_batch_complete = on_batch_complete

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Progress file
        self.progress_file = self.output_dir / "scraper_progress.json"

        # Load or create progress
        self.progress = self._load_progress()

    def _load_progress(self) -> ScraperProgress:
        """Load progress from file or create new."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r") as f:
                    data = json.load(f)
                    progress = ScraperProgress.from_dict(data)
                    # Only resume if same date range
                    if (progress.start_date == self.start_date and
                        progress.end_date == self.end_date and
                        not progress.completed):
                        logger.info(f"Resuming from offset {progress.current_offset}")
                        return progress
            except Exception as e:
                logger.warning(f"Could not load progress: {e}")

        # Start fresh
        return ScraperProgress(
            start_date=self.start_date,
            end_date=self.end_date,
            started_at=datetime.now().isoformat(),
        )

    def _save_progress(self):
        """Save current progress to file."""
        self.progress.last_updated = datetime.now().isoformat()
        with open(self.progress_file, "w") as f:
            json.dump(self.progress.to_dict(), f, indent=2)

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
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)

        logger.error(f"All attempts failed for match {match_id}")
        return None

    def _get_all_match_ids(self) -> List[str]:
        """Get all match IDs from paginated results."""
        all_ids = []
        offset = self.progress.current_offset
        has_more = True

        logger.info(f"Fetching match IDs starting from offset {offset}...")

        while has_more:
            try:
                results = HLTVMatchResults(
                    offset=offset,
                    start_date=self.start_date,
                    end_date=self.end_date,
                )
                data = results.get_results()

                matches = data.get("matches", [])
                ids = [m["match_id"] for m in matches]
                all_ids.extend(ids)

                has_more = data.get("has_more", False)
                offset = data.get("next_offset", offset + 100)

                logger.info(f"Fetched {len(matches)} matches (total: {len(all_ids)}, offset: {offset})")

                # Rate limiting
                time.sleep(self.delay_seconds)

            except Exception as e:
                logger.error(f"Error fetching results at offset {offset}: {e}")
                has_more = False

        self.progress.total_matches_found = len(all_ids)
        self._save_progress()

        return all_ids

    def scrape_all(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Scrape all historical matches.

        Args:
            batch_size: Number of matches per batch before saving

        Returns:
            dict: Summary of scraping results
        """
        logger.info(f"Starting historical scrape: {self.start_date} to {self.end_date}")

        # Get all match IDs first
        match_ids = self._get_all_match_ids()
        logger.info(f"Found {len(match_ids)} total matches to scrape")

        if not match_ids:
            logger.warning("No matches found")
            return {"status": "no_matches", "total": 0}

        # Scrape each match
        batch = []
        scraped_count = self.progress.total_matches_scraped

        for i, match_id in enumerate(match_ids):
            # Skip already scraped
            if scraped_count > i:
                continue

            logger.info(f"Scraping match {match_id} ({i + 1}/{len(match_ids)})")

            match_data = self._scrape_match_with_retry(match_id)

            if match_data:
                batch.append(match_data)
                self.progress.total_matches_scraped += 1
                self.progress.last_match_id = match_id

                # Callback for individual match
                if self.on_match_scraped:
                    try:
                        self.on_match_scraped(match_data)
                    except Exception as e:
                        logger.error(f"Error in on_match_scraped callback: {e}")
            else:
                self.progress.failed_matches.append(match_id)

            # Save progress and call batch callback
            if len(batch) >= batch_size:
                self._save_progress()
                if self.on_batch_complete:
                    try:
                        self.on_batch_complete(batch)
                    except Exception as e:
                        logger.error(f"Error in on_batch_complete callback: {e}")
                batch = []

            # Rate limiting
            time.sleep(self.delay_seconds)

        # Final batch
        if batch and self.on_batch_complete:
            try:
                self.on_batch_complete(batch)
            except Exception as e:
                logger.error(f"Error in final on_batch_complete callback: {e}")

        # Mark complete
        self.progress.completed = True
        self._save_progress()

        summary = {
            "status": "completed",
            "total_found": self.progress.total_matches_found,
            "total_scraped": self.progress.total_matches_scraped,
            "failed": len(self.progress.failed_matches),
            "failed_ids": self.progress.failed_matches,
        }

        logger.info(f"Scraping complete: {summary}")
        return summary

    def get_status(self) -> Dict[str, Any]:
        """Get current scraping status."""
        return {
            "progress": self.progress.to_dict(),
            "output_dir": str(self.output_dir),
            "delay_seconds": self.delay_seconds,
        }


def main():
    """Main entry point for running the scraper."""
    import argparse
    import os

    from app.storage.csv_storage import CSVStorage

    parser = argparse.ArgumentParser(description="HLTV Historical Match Scraper")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--output-dir", default=os.getenv("CSV_OUTPUT_DIR", "./data"), help="Output directory")
    parser.add_argument("--delay", type=float, default=float(os.getenv("SCRAPER_DELAY_SECONDS", "2.0")), help="Delay between requests")
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("SCRAPER_BATCH_SIZE", "100")), help="Batch size")
    args = parser.parse_args()

    # Initialize CSV storage
    storage = CSVStorage(data_dir=args.output_dir)
    logger.info(f"Using CSV storage at: {args.output_dir}")
    logger.info(f"Existing matches in storage: {storage.get_match_count()}")

    def save_match_to_csv(match_data: Dict[str, Any]):
        """Save individual match to CSV storage."""
        match_id = match_data.get("match_id")
        if storage.match_exists(match_id):
            logger.info(f"Match {match_id} already exists, skipping")
            return

        if storage.save_match(match_data):
            logger.info(f"Saved match {match_id} to CSV")
        else:
            logger.warning(f"Failed to save match {match_id}")

    def on_batch_complete(matches: List[Dict[str, Any]]):
        """Log batch completion."""
        logger.info(f"Batch of {len(matches)} matches completed")
        stats = storage.get_statistics()
        logger.info(f"Total matches in storage: {stats['total_matches']}")

    scraper = HistoricalMatchScraper(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
        delay_seconds=args.delay,
        on_match_scraped=save_match_to_csv,
        on_batch_complete=on_batch_complete,
    )

    result = scraper.scrape_all(batch_size=args.batch_size)

    # Print final statistics
    final_stats = storage.get_statistics()
    result["storage_stats"] = final_stats
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
