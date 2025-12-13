"""
CSV storage backend for match data.
"""
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
import threading

from .base import StorageBackend


class CSVStorage(StorageBackend):
    """
    CSV-based storage backend for match data.

    Stores data in separate CSV files:
    - matches.csv: Match metadata
    - maps.csv: Map results per match
    - player_stats.csv: Player statistics per match
    - teams.csv: Team metadata (deduplicated)
    - players.csv: Player metadata (deduplicated)
    """

    def __init__(self, data_dir: str = "./data"):
        """
        Initialize CSV storage.

        Args:
            data_dir: Directory to store CSV files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.matches_file = self.data_dir / "matches.csv"
        self.maps_file = self.data_dir / "maps.csv"
        self.player_stats_file = self.data_dir / "player_stats.csv"
        self.match_players_file = self.data_dir / "match_players.csv"
        self.teams_file = self.data_dir / "teams.csv"
        self.players_file = self.data_dir / "players.csv"

        # Thread safety
        self._lock = threading.Lock()

        # Cache of scraped match IDs
        self._match_ids: Set[str] = set()
        self._load_match_ids()

        # Initialize CSV files with headers if they don't exist
        self._init_csv_files()

    def _init_csv_files(self):
        """Initialize CSV files with headers if they don't exist."""
        files_headers = {
            self.matches_file: [
                "match_id", "match_url", "team1_id", "team1_name", "team1_score",
                "team2_id", "team2_name", "team2_score", "event_id", "event_name",
                "event_url", "date", "time_unix", "match_format", "format_type",
                "winner", "final_score", "scraped_at"
            ],
            self.maps_file: [
                "match_id", "map_number", "map_name", "team1_score", "team2_score",
                "team1_ct_score", "team1_t_score", "team2_ct_score", "team2_t_score",
                "winner"
            ],
            self.player_stats_file: [
                "match_id", "team_id", "player_id", "player_name", "player_nick",
                "country", "kills", "deaths", "kd_diff", "adr", "kast", "rating", "swing"
            ],
            self.match_players_file: [
                "match_id", "team_id", "team_name", "player_id", "player_nick", "country"
            ],
            self.teams_file: [
                "team_id", "team_name", "team_logo_url", "last_updated"
            ],
            self.players_file: [
                "player_id", "player_name", "player_nick", "country", "last_updated"
            ],
        }

        for file_path, headers in files_headers.items():
            if not file_path.exists():
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)

    def _load_match_ids(self):
        """Load existing match IDs into cache."""
        if self.matches_file.exists():
            with open(self.matches_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "match_id" in row:
                        self._match_ids.add(row["match_id"])

    def _append_row(self, file_path: Path, row: List[Any]):
        """Append a row to a CSV file."""
        with open(file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)

    def _extract_match_row(self, match_data: Dict[str, Any]) -> List[Any]:
        """Extract match row data from match dictionary."""
        team1 = match_data.get("team1", {})
        team2 = match_data.get("team2", {})

        return [
            match_data.get("match_id"),
            match_data.get("match_url"),
            team1.get("team_id"),
            team1.get("name"),
            team1.get("score"),
            team2.get("team_id"),
            team2.get("name"),
            team2.get("score"),
            match_data.get("event_id"),
            match_data.get("event_name"),
            match_data.get("event_url"),
            match_data.get("date"),
            match_data.get("time_unix"),
            match_data.get("match_format"),
            match_data.get("format_type"),
            match_data.get("winner"),
            match_data.get("final_score"),
            datetime.now().isoformat(),
        ]

    def _extract_map_rows(self, match_data: Dict[str, Any]) -> List[List[Any]]:
        """Extract map rows from match dictionary."""
        match_id = match_data.get("match_id")
        maps = match_data.get("maps", [])

        rows = []
        for map_data in maps:
            rows.append([
                match_id,
                map_data.get("map_number"),
                map_data.get("map_name"),
                map_data.get("team1_score"),
                map_data.get("team2_score"),
                map_data.get("team1_ct_score"),
                map_data.get("team1_t_score"),
                map_data.get("team2_ct_score"),
                map_data.get("team2_t_score"),
                map_data.get("winner"),
            ])

        return rows

    def _extract_match_players_rows(self, match_data: Dict[str, Any]) -> List[List[Any]]:
        """Extract match_players rows - which players played for which team in this match."""
        match_id = match_data.get("match_id")
        rows = []

        for team_key in ["team1_stats", "team2_stats"]:
            team_stats = match_data.get(team_key)
            if not team_stats:
                continue

            team_id = team_stats.get("team_id")
            team_name = team_stats.get("team_name")
            players = team_stats.get("players", [])

            for player in players:
                rows.append([
                    match_id,
                    team_id,
                    team_name,
                    player.get("player_id"),
                    player.get("player_nick"),
                    player.get("country"),
                ])

        return rows

    def _extract_player_stats_rows(self, match_data: Dict[str, Any]) -> List[List[Any]]:
        """Extract player stats rows from match dictionary."""
        match_id = match_data.get("match_id")
        rows = []

        for team_key in ["team1_stats", "team2_stats"]:
            team_stats = match_data.get(team_key)
            if not team_stats:
                continue

            team_id = team_stats.get("team_id")
            players = team_stats.get("players", [])

            for player in players:
                rows.append([
                    match_id,
                    team_id,
                    player.get("player_id"),
                    player.get("player_name"),
                    player.get("player_nick"),
                    player.get("country"),
                    player.get("kills"),
                    player.get("deaths"),
                    player.get("kd_diff"),
                    player.get("adr"),
                    player.get("kast"),
                    player.get("rating"),
                    player.get("swing"),
                ])

        return rows

    def _extract_team_row(self, team_data: Dict[str, Any]) -> Optional[List[Any]]:
        """Extract team metadata row."""
        team_id = team_data.get("team_id")
        if not team_id:
            return None

        return [
            team_id,
            team_data.get("name") or team_data.get("team_name"),
            team_data.get("logo_url") or team_data.get("team_logo_url"),
            datetime.now().isoformat(),
        ]

    def _extract_player_row(self, player_data: Dict[str, Any]) -> Optional[List[Any]]:
        """Extract player metadata row."""
        player_id = player_data.get("player_id")
        if not player_id:
            return None

        return [
            player_id,
            player_data.get("player_name"),
            player_data.get("player_nick"),
            player_data.get("country"),
            datetime.now().isoformat(),
        ]

    def save_match(self, match_data: Dict[str, Any]) -> bool:
        """Save a single match with all its data."""
        match_id = match_data.get("match_id")
        if not match_id:
            return False

        with self._lock:
            # Check for duplicate
            if match_id in self._match_ids:
                return False

            try:
                # Save match
                match_row = self._extract_match_row(match_data)
                self._append_row(self.matches_file, match_row)

                # Save maps
                map_rows = self._extract_map_rows(match_data)
                for row in map_rows:
                    self._append_row(self.maps_file, row)

                # Save player stats
                stats_rows = self._extract_player_stats_rows(match_data)
                for row in stats_rows:
                    self._append_row(self.player_stats_file, row)

                # Save match_players (roster for this specific match)
                match_players_rows = self._extract_match_players_rows(match_data)
                for row in match_players_rows:
                    self._append_row(self.match_players_file, row)

                # Save team metadata (deduplicated separately if needed)
                team1 = match_data.get("team1", {})
                team2 = match_data.get("team2", {})
                for team in [team1, team2]:
                    if team.get("team_id"):
                        team_row = self._extract_team_row(team)
                        if team_row:
                            self._append_row(self.teams_file, team_row)

                # Save player metadata
                for team_key in ["team1_stats", "team2_stats"]:
                    team_stats = match_data.get(team_key)
                    if team_stats:
                        for player in team_stats.get("players", []):
                            player_row = self._extract_player_row(player)
                            if player_row:
                                self._append_row(self.players_file, player_row)

                # Update cache
                self._match_ids.add(match_id)

                return True

            except Exception as e:
                print(f"Error saving match {match_id}: {e}")
                return False

    def save_matches(self, matches: List[Dict[str, Any]]) -> int:
        """Save multiple matches (batch operation)."""
        saved = 0
        for match_data in matches:
            if self.save_match(match_data):
                saved += 1
        return saved

    def match_exists(self, match_id: str) -> bool:
        """Check if a match already exists in storage."""
        return match_id in self._match_ids

    def get_last_scraped_date(self) -> Optional[datetime]:
        """Get the date of the most recently scraped match."""
        if not self.matches_file.exists():
            return None

        last_date = None
        with open(self.matches_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                scraped_at = row.get("scraped_at")
                if scraped_at:
                    try:
                        dt = datetime.fromisoformat(scraped_at)
                        if last_date is None or dt > last_date:
                            last_date = dt
                    except ValueError:
                        pass

        return last_date

    def get_match_count(self) -> int:
        """Get total number of matches in storage."""
        return len(self._match_ids)

    def get_scraped_match_ids(self) -> List[str]:
        """Get list of all scraped match IDs."""
        return list(self._match_ids)

    def export_to_csv(self, output_dir: str) -> Dict[str, str]:
        """Export all data to CSV files (returns current file paths)."""
        return {
            "matches": str(self.matches_file),
            "maps": str(self.maps_file),
            "player_stats": str(self.player_stats_file),
            "match_players": str(self.match_players_file),
            "teams": str(self.teams_file),
            "players": str(self.players_file),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        stats = {
            "total_matches": self.get_match_count(),
            "last_scraped": None,
            "files": self.export_to_csv(str(self.data_dir)),
        }

        last_date = self.get_last_scraped_date()
        if last_date:
            stats["last_scraped"] = last_date.isoformat()

        # Count rows in each file
        for name, path in stats["files"].items():
            if Path(path).exists():
                with open(path, "r", encoding="utf-8") as f:
                    # Subtract 1 for header
                    row_count = sum(1 for _ in f) - 1
                    stats[f"{name}_rows"] = max(0, row_count)

        return stats
