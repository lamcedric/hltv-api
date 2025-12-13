"""
Service for scraping HLTV match results listing page.
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from lxml import etree

from app.services.base import HLTVBase
from app.utils.xpath import Matches
from app.utils.utils import trim


@dataclass
class HLTVMatchResults(HLTVBase):
    """
    Scraper for HLTV results listing page.

    Args:
        offset: Pagination offset (default 0, increments by 100)
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
    """
    offset: int = 0
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    def __post_init__(self):
        # Build URL - only use offset parameter (date params trigger Cloudflare)
        # Date filtering is done client-side after fetching
        if self.offset > 0:
            self.URL = f"https://www.hltv.org/results?offset={self.offset}"
        else:
            self.URL = "https://www.hltv.org/results"

        import time
        import random
        # Add small random delay to avoid pattern detection
        time.sleep(random.uniform(0.5, 1.5))
        self.page = self.request_url_page()

    def _extract_match_id(self, url: Optional[str]) -> Optional[str]:
        """Extract match ID from match URL like '/matches/2388127/...'."""
        if not url:
            return None
        match = re.search(r'/matches/(\d+)/', url)
        return match.group(1) if match else None

    def _parse_format(self, format_str: Optional[str]) -> Optional[str]:
        """Normalize format string like 'bo3' or 'bo1'."""
        if not format_str:
            return None
        format_lower = format_str.lower().strip()
        if format_lower in ["bo1", "bo3", "bo5"]:
            return format_lower
        return format_lower

    def _parse_match_container(self, container: etree._Element) -> Optional[Dict[str, Any]]:
        """Parse a single match result container."""
        xp = Matches.ResultsPage

        # Get match link
        link_elems = container.xpath(xp.MATCH_LINK)
        if not link_elems:
            return None

        match_url = link_elems[0]
        match_id = self._extract_match_id(match_url)

        if not match_id:
            return None

        # Get team names
        team1_elems = container.xpath(xp.TEAM1_NAME)
        team2_elems = container.xpath(xp.TEAM2_NAME)

        team1_name = trim(team1_elems[0]) if team1_elems else "Unknown"
        team2_name = trim(team2_elems[0]) if team2_elems else "Unknown"

        # Get scores
        score1_elems = container.xpath(xp.TEAM1_SCORE)
        score2_elems = container.xpath(xp.TEAM2_SCORE)

        team1_score = None
        team2_score = None

        if score1_elems:
            try:
                team1_score = int(trim(score1_elems[0]))
            except (ValueError, TypeError):
                pass

        if score2_elems:
            try:
                team2_score = int(trim(score2_elems[0]))
            except (ValueError, TypeError):
                pass

        # Get event name
        event_elems = container.xpath(xp.EVENT_NAME)
        event_name = trim(event_elems[0]) if event_elems else None

        # Get match format
        format_elems = container.xpath(xp.MATCH_FORMAT)
        match_format = self._parse_format(trim(format_elems[0])) if format_elems else None

        return {
            "match_id": match_id,
            "match_url": f"https://www.hltv.org{match_url}",
            "team1_name": team1_name,
            "team2_name": team2_name,
            "team1_score": team1_score,
            "team2_score": team2_score,
            "event_name": event_name,
            "match_format": match_format,
            "date": None,  # Date is in section header, not per-match
        }

    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse HLTV date format like 'December 12th 2025' to 'YYYY-MM-DD'."""
        if not date_str:
            return None

        from datetime import datetime
        import re

        try:
            # Remove ordinal suffixes (st, nd, rd, th)
            clean_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
            # Handle "Results for December 12 2025" format
            clean_date = clean_date.replace("Results for ", "")
            dt = datetime.strptime(clean_date.strip(), "%B %d %Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    def _is_in_date_range(self, match_date: Optional[str]) -> bool:
        """Check if a match date is within the configured date range."""
        if not match_date:
            return True  # Include matches without dates

        parsed = self._parse_date(match_date)
        if not parsed:
            return True  # Include matches we can't parse

        if self.start_date and parsed < self.start_date:
            return False
        if self.end_date and parsed > self.end_date:
            return False
        return True

    def _is_before_start_date(self, match_date: Optional[str]) -> bool:
        """Check if a match date is before the start date (for early termination)."""
        if not match_date or not self.start_date:
            return False

        parsed = self._parse_date(match_date)
        if not parsed:
            return False

        return parsed < self.start_date

    def get_results(self) -> Dict[str, Any]:
        """
        Get paginated match results from the results page.
        Filters by date range client-side (not in URL to avoid Cloudflare).

        Returns:
            dict: Contains matches list, pagination info.
        """
        xp = Matches.ResultsPage

        matches = []
        current_date = None
        reached_before_start = False

        # Get all date sections
        date_sections = self.page.xpath(xp.DATE_SECTIONS)

        for section in date_sections:
            # Get date headline for this section
            headline_elems = section.xpath(xp.DATE_HEADLINE)
            if headline_elems:
                current_date = trim(headline_elems[0])

                # Early termination if we've gone past our date range
                if self._is_before_start_date(current_date):
                    reached_before_start = True
                    break

            # Skip sections outside our date range
            if not self._is_in_date_range(current_date):
                continue

            # Get all match containers in this section
            match_containers = section.xpath(xp.MATCH_CONTAINERS)

            for container in match_containers:
                match_data = self._parse_match_container(container)
                if match_data:
                    match_data["date"] = current_date
                    match_data["date_parsed"] = self._parse_date(current_date)
                    matches.append(match_data)

        # Check for pagination (but stop if we've reached before our start date)
        next_page_elems = self.page.xpath(xp.PAGINATION_NEXT)
        has_more = bool(next_page_elems) and not reached_before_start
        next_offset = self.offset + 100 if has_more else None

        self.response = {
            "matches": matches,
            "total_count": len(matches),
            "offset": self.offset,
            "has_more": has_more,
            "next_offset": next_offset,
            "reached_before_start": reached_before_start,
        }

        return self.response

    def get_all_match_ids(self) -> List[str]:
        """
        Get just the match IDs from the results page.

        Returns:
            list: List of match ID strings.
        """
        results = self.get_results()
        return [m["match_id"] for m in results.get("matches", [])]
