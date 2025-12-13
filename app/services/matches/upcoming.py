"""
Service for scraping HLTV upcoming matches.
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from lxml import etree

from app.services.base import HLTVBase
from app.utils.utils import trim


@dataclass
class HLTVUpcomingMatches(HLTVBase):
    """
    Scraper for HLTV upcoming matches page.
    """

    def __post_init__(self):
        self.URL = "https://www.hltv.org/matches"
        import time
        import random
        time.sleep(random.uniform(0.5, 1.5))
        self.page = self.request_url_page()

    def _extract_match_id(self, url: Optional[str]) -> Optional[str]:
        """Extract match ID from match URL."""
        if not url:
            return None
        match = re.search(r'/matches/(\d+)/', url)
        return match.group(1) if match else None

    def _extract_team_id(self, url: Optional[str]) -> Optional[str]:
        """Extract team ID from team URL."""
        if not url:
            return None
        match = re.search(r'/team/(\d+)/', url)
        return match.group(1) if match else None

    def get_upcoming(self, limit: int = 50) -> Dict[str, Any]:
        """
        Get upcoming matches from the matches page.

        Args:
            limit: Maximum number of matches to return

        Returns:
            dict: Contains upcoming matches list.
        """
        matches = []

        # Find all match links on the page
        match_links = self.page.xpath("//a[contains(@href,'/matches/2')]/@href")
        seen_ids = set()

        for link in match_links:
            match_id = self._extract_match_id(link)
            if not match_id or match_id in seen_ids:
                continue
            seen_ids.add(match_id)

            matches.append({
                "match_id": match_id,
                "match_url": f"https://www.hltv.org{link}",
            })

            if len(matches) >= limit:
                break

        self.response = {
            "matches": matches,
            "total_count": len(matches),
        }

        return self.response


@dataclass
class HLTVMatchLineup(HLTVBase):
    """
    Scraper for getting player lineups from a match page.
    Works for both upcoming and completed matches.
    """
    match_id: str

    def __post_init__(self):
        self.URL = f"https://www.hltv.org/matches/{self.match_id}/_"
        import time
        import random
        time.sleep(random.uniform(0.5, 1.5))
        self.page = self.request_url_page()

        # Get canonical URL
        canonical = self.page.xpath("//link[@rel='canonical']/@href")
        if canonical:
            self.URL = canonical[0]

    def _extract_player_id(self, url: Optional[str]) -> Optional[str]:
        """Extract player ID from player URL."""
        if not url:
            return None
        match = re.search(r'/player/(\d+)/', url)
        return match.group(1) if match else None

    def _extract_team_id(self, url: Optional[str]) -> Optional[str]:
        """Extract team ID from team URL."""
        if not url:
            return None
        match = re.search(r'/team/(\d+)/', url)
        return match.group(1) if match else None

    def _get_team_lineup(self, team_num: int) -> Dict[str, Any]:
        """Extract lineup for a team (1 or 2)."""
        team_xpath = f"//div[contains(@class,'team{team_num}-gradient')]"

        # Get team info from header
        team_name = self.page.xpath(f"{team_xpath}//div[@class='teamName']/text()")
        team_link = self.page.xpath(f"{team_xpath}//a/@href")
        team_logo = self.page.xpath(f"{team_xpath}//img[contains(@class,'logo')]/@src")

        players = []

        # Method 1: Standard lineup box (upcoming non-live matches)
        lineup_boxes = self.page.xpath("//div[@class='lineup standard-box']")
        if len(lineup_boxes) >= team_num:
            box = lineup_boxes[team_num - 1]
            player_names = box.xpath(".//td[@class='player']//div[@class='text-ellipsis']/text()")
            player_links = box.xpath(".//td[@class='player']//a/@href")
            player_flags = box.xpath(".//td[@class='player']//img/@title")

            for i, name in enumerate(player_names):
                link = player_links[i] if i < len(player_links) else None
                flag = player_flags[i] if i < len(player_flags) else None
                players.append({
                    "player_id": self._extract_player_id(link),
                    "player_name": trim(name),
                    "country": trim(flag) if flag else None,
                })

        # Method 2: Stats table (completed matches)
        if not players:
            stats_tables = self.page.xpath("//table[contains(@class,'totalstats')]")
            if len(stats_tables) >= team_num:
                table = stats_tables[team_num - 1]
                player_rows = table.xpath(".//tr[not(@class='header-row')]")
                for row in player_rows:
                    player_link = row.xpath(".//td[@class='players']//a/@href")
                    player_name = row.xpath(".//span[@class='player-nick']/text()")
                    player_flag = row.xpath(".//img[@class='flag']/@title")

                    if player_name:
                        players.append({
                            "player_id": self._extract_player_id(player_link[0] if player_link else None),
                            "player_name": trim(player_name[0]),
                            "country": trim(player_flag[0]) if player_flag else None,
                        })

        # Method 3: Lineups compare container (live matches)
        if not players:
            side = "left" if team_num == 1 else "right"
            container = self.page.xpath(f"//div[@class='lineups-compare-{side}']")
            if container:
                player_links = container[0].xpath(".//a[contains(@href,'/player/')]")
                for p in player_links:
                    href = p.get("href", "")
                    # Extract name from href slug
                    name = href.split("/")[-1].replace("-", " ").title() if href else None
                    name_elem = p.xpath(".//div/text()")
                    if name_elem:
                        name = trim(name_elem[0])
                    flag = p.xpath(".//img/@title")

                    if name:
                        players.append({
                            "player_id": self._extract_player_id(href),
                            "player_name": name,
                            "country": trim(flag[0]) if flag else None,
                        })

        return {
            "team_id": self._extract_team_id(team_link[0] if team_link else None),
            "team_name": trim(team_name[0]) if team_name else "Unknown",
            "team_logo": team_logo[0] if team_logo else None,
            "players": players,
        }

    def get_lineups(self) -> Dict[str, Any]:
        """
        Get player lineups for both teams.

        Returns:
            dict: Match info with team lineups.
        """
        # Get basic match info
        event_name = self.page.xpath("//a[@class='event']//div[contains(@class,'event-name')]/text()")
        match_time = self.page.xpath("//div[@class='time']/@data-unix")
        match_date = self.page.xpath("//div[@class='date']/text()")
        match_format = self.page.xpath("//div[contains(@class,'preformatted-text')]/text()")

        # Check if match is live
        is_live = bool(self.page.xpath("//*[contains(@class,'countdown')]") == [])
        live_indicator = self.page.xpath("//div[contains(@class,'liveMatch')]")
        if live_indicator:
            is_live = True

        # Get lineups
        team1 = self._get_team_lineup(1)
        team2 = self._get_team_lineup(2)

        self.response = {
            "match_id": self.match_id,
            "match_url": self.URL,
            "event_name": trim(event_name[0]) if event_name else None,
            "match_time_unix": int(match_time[0]) if match_time else None,
            "match_date": trim(match_date[0]) if match_date else None,
            "match_format": trim(match_format[0]) if match_format else None,
            "is_live": is_live,
            "team1": team1,
            "team2": team2,
        }

        return self.response
