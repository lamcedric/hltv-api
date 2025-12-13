"""
Service for scraping individual HLTV match details.
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from lxml import etree

from app.services.base import HLTVBase
from app.utils.xpath import Matches
from app.utils.utils import trim, extract_from_url


@dataclass
class HLTVMatchDetails(HLTVBase):
    """
    Scraper for individual HLTV match page.

    Args:
        match_id: The HLTV match ID (e.g., '2388127')
    """
    match_id: str

    def __post_init__(self):
        self.URL = f"https://www.hltv.org/matches/{self.match_id}/_"
        self.page = self.request_url_page()
        # Get the canonical URL (proper match URL with slug)
        canonical = self.page.xpath("//link[@rel='canonical']/@href")
        if canonical:
            self.URL = canonical[0]

    def _extract_team_id(self, url: Optional[str]) -> Optional[str]:
        """Extract team ID from team URL like '/team/8297/furia'."""
        if not url:
            return None
        match = re.search(r'/team/(\d+)/', url)
        return match.group(1) if match else None

    def _extract_event_id(self, url: Optional[str]) -> Optional[str]:
        """Extract event ID from event URL like '/events/8045/...'."""
        if not url:
            return None
        match = re.search(r'/events?/(\d+)/', url)
        return match.group(1) if match else None

    def _extract_player_id(self, url: Optional[str]) -> Optional[str]:
        """Extract player ID from player URL like '/player/15631/kscerato'."""
        if not url:
            return None
        match = re.search(r'/player/(\d+)/', url)
        return match.group(1) if match else None

    def _parse_format_type(self, format_str: Optional[str]) -> Optional[str]:
        """Parse format string like 'Best of 3 (LAN)' to 'bo3'."""
        if not format_str:
            return None
        format_lower = format_str.lower()
        if "best of 1" in format_lower:
            return "bo1"
        elif "best of 3" in format_lower:
            return "bo3"
        elif "best of 5" in format_lower:
            return "bo5"
        return None

    def _parse_kd(self, kd_str: Optional[str]) -> tuple[Optional[int], Optional[int]]:
        """Parse K-D string like '47-50' into (kills, deaths)."""
        if not kd_str:
            return None, None
        try:
            parts = kd_str.split("-")
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            pass
        return None, None

    def _get_team_info(self, team_num: int) -> Dict[str, Any]:
        """Extract team information (team1 or team2)."""
        xp = Matches.MatchPage

        if team_num == 1:
            name_xpath = xp.TEAM1_NAME
            link_xpath = xp.TEAM1_LINK
            logo_xpath = xp.TEAM1_LOGO
            won_xpath = xp.TEAM1_SCORE_WON
            lost_xpath = xp.TEAM1_SCORE_LOST
        else:
            name_xpath = xp.TEAM2_NAME
            link_xpath = xp.TEAM2_LINK
            logo_xpath = xp.TEAM2_LOGO
            won_xpath = xp.TEAM2_SCORE_WON
            lost_xpath = xp.TEAM2_SCORE_LOST

        name = self.get_text_by_xpath(name_xpath)
        link = self.get_text_by_xpath(link_xpath)
        logo = self.get_text_by_xpath(logo_xpath)

        # Score is either from 'won' or 'lost' div
        score_won = self.get_text_by_xpath(won_xpath)
        score_lost = self.get_text_by_xpath(lost_xpath)
        score = score_won or score_lost

        return {
            "team_id": self._extract_team_id(link),
            "name": name or "Unknown",
            "logo_url": logo,
            "score": int(score) if score and score.isdigit() else None,
        }

    def _get_map_results(self) -> List[Dict[str, Any]]:
        """Extract map results from all map holders."""
        xp = Matches.MapResults
        map_holders = self.page.xpath(Matches.MatchPage.MAP_HOLDERS)

        maps = []
        for i, mh in enumerate(map_holders, 1):
            # Get map name
            map_name_elems = mh.xpath(xp.MAP_NAME)
            map_name = trim(map_name_elems[0]) if map_name_elems else None

            if not map_name or map_name.lower() == "tba":
                continue

            # Get scores
            t1_score_elems = mh.xpath(xp.TEAM1_SCORE)
            t2_score_elems = mh.xpath(xp.TEAM2_SCORE)

            t1_score = None
            t2_score = None

            if t1_score_elems:
                score_text = trim(t1_score_elems[0])
                score_match = re.search(r'(\d+)', score_text)
                if score_match:
                    t1_score = int(score_match.group(1))

            if t2_score_elems:
                score_text = trim(t2_score_elems[0])
                score_match = re.search(r'(\d+)', score_text)
                if score_match:
                    t2_score = int(score_match.group(1))

            # Get half scores
            t1_ct = mh.xpath(xp.TEAM1_CT_SCORE)
            t1_t = mh.xpath(xp.TEAM1_T_SCORE)
            t2_ct = mh.xpath(xp.TEAM2_CT_SCORE)
            t2_t = mh.xpath(xp.TEAM2_T_SCORE)

            # Determine winner
            winner = None
            t1_won = mh.xpath(xp.TEAM1_WON)
            t2_won = mh.xpath(xp.TEAM2_WON)
            if t1_won:
                winner = "team1"
            elif t2_won:
                winner = "team2"

            maps.append({
                "map_number": i,
                "map_name": map_name,
                "team1_score": t1_score,
                "team2_score": t2_score,
                "team1_ct_score": int(trim(t1_ct[0])) if t1_ct else None,
                "team1_t_score": int(trim(t1_t[0])) if t1_t else None,
                "team2_ct_score": int(trim(t2_ct[0])) if t2_ct else None,
                "team2_t_score": int(trim(t2_t[0])) if t2_t else None,
                "winner": winner,
            })

        return maps

    def _get_player_stats(self) -> tuple[Optional[Dict], Optional[Dict]]:
        """Extract player statistics from both teams' stats tables."""
        xp = Matches.PlayerStats
        stats_tables = self.page.xpath(xp.STATS_TABLES)

        team_stats = []

        for table in stats_tables[:2]:  # Max 2 teams
            # Get team info from header
            header = table.xpath(xp.HEADER_ROW)
            if not header:
                continue

            header_elem = header[0]
            team_name_elems = header_elem.xpath(xp.TEAM_NAME)
            team_link_elems = header_elem.xpath(xp.TEAM_LINK)
            team_logo_elems = header_elem.xpath(xp.TEAM_LOGO)

            team_name = trim(team_name_elems[0]) if team_name_elems else "Unknown"
            team_link = team_link_elems[0] if team_link_elems else None
            team_logo = team_logo_elems[0] if team_logo_elems else None

            # Get player rows
            player_rows = table.xpath(xp.PLAYER_ROWS)
            players = []

            for row in player_rows:
                # Player info
                player_link_elems = row.xpath(xp.PLAYER_LINK)
                player_nick_elems = row.xpath(xp.PLAYER_NICK)
                player_flag_elems = row.xpath(xp.PLAYER_FLAG)

                player_link = player_link_elems[0] if player_link_elems else None
                player_nick = trim(player_nick_elems[0]) if player_nick_elems else None
                player_country = player_flag_elems[0] if player_flag_elems else None

                if not player_nick:
                    continue

                # Stats
                kd_elems = row.xpath(xp.KD)
                adr_elems = row.xpath(xp.ADR)
                kast_elems = row.xpath(xp.KAST)
                rating_elems = row.xpath(xp.RATING)
                swing_elems = row.xpath(xp.SWING)

                kd_str = trim(kd_elems[0]) if kd_elems else None
                kills, deaths = self._parse_kd(kd_str)

                adr_str = trim(adr_elems[0]) if adr_elems else None
                kast_str = trim(kast_elems[0]) if kast_elems else None
                rating_str = trim(rating_elems[0]) if rating_elems else None
                swing_str = trim(swing_elems[0]) if swing_elems else None

                players.append({
                    "player_id": self._extract_player_id(player_link),
                    "player_name": player_nick,
                    "player_nick": player_nick,
                    "country": player_country,
                    "team_id": self._extract_team_id(team_link),
                    "kills": kills,
                    "deaths": deaths,
                    "kd_diff": (kills - deaths) if kills is not None and deaths is not None else None,
                    "adr": float(adr_str) if adr_str else None,
                    "kast": float(kast_str.replace("%", "")) if kast_str else None,
                    "rating": float(rating_str) if rating_str else None,
                    "swing": float(swing_str.replace("%", "").replace("+", "")) if swing_str else None,
                })

            team_stats.append({
                "team_id": self._extract_team_id(team_link),
                "team_name": team_name,
                "team_logo_url": team_logo,
                "players": players,
            })

        # Return team1_stats and team2_stats
        team1_stats = team_stats[0] if len(team_stats) > 0 else None
        team2_stats = team_stats[1] if len(team_stats) > 1 else None

        return team1_stats, team2_stats

    def get_match_details(self) -> Dict[str, Any]:
        """
        Get complete match details including teams, maps, and player stats.

        Returns:
            dict: Match details with teams, maps, and player statistics.
        """
        xp = Matches.MatchPage

        # Team info
        team1 = self._get_team_info(1)
        team2 = self._get_team_info(2)

        # Event info
        event_link = self.get_text_by_xpath(xp.EVENT_LINK)
        event_name = self.get_text_by_xpath(xp.EVENT_NAME)

        # Date/time
        date = self.get_text_by_xpath(xp.DATE)
        time_unix = self.get_text_by_xpath(xp.TIME_UNIX)

        # Format
        match_format = self.get_text_by_xpath(xp.MATCH_FORMAT)
        format_type = self._parse_format_type(match_format)

        # Map results
        maps = self._get_map_results()

        # Determine winner and final score
        winner = None
        final_score = None
        if team1.get("score") is not None and team2.get("score") is not None:
            t1_score = team1["score"]
            t2_score = team2["score"]
            final_score = f"{t1_score}-{t2_score}"
            if t1_score > t2_score:
                winner = "team1"
            elif t2_score > t1_score:
                winner = "team2"

        # Player stats
        team1_stats, team2_stats = self._get_player_stats()

        self.response = {
            "match_id": self.match_id,
            "match_url": self.URL,
            "team1": team1,
            "team2": team2,
            "event_id": self._extract_event_id(event_link),
            "event_name": event_name,
            "event_url": f"https://www.hltv.org{event_link}" if event_link else None,
            "date": date,
            "time_unix": int(time_unix) if time_unix else None,
            "match_format": match_format,
            "format_type": format_type,
            "winner": winner,
            "final_score": final_score,
            "maps": maps,
            "team1_stats": team1_stats,
            "team2_stats": team2_stats,
        }

        return self.response
