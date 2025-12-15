"""
PostgreSQL storage backend for match data.
"""
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Set

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import insert

from .base import StorageBackend
from .models import Base, Match, Map, PlayerStat, MatchPlayer, Team, Player


class PostgresStorage(StorageBackend):
    """
    PostgreSQL-based storage backend for match data.
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize PostgreSQL storage.

        Args:
            database_url: PostgreSQL connection URL. If not provided, reads from DATABASE_URL env var.
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable or database_url parameter required")

        self.engine = create_engine(self.database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

        # Cache of scraped match IDs for fast lookup
        self._match_ids: Optional[Set[str]] = None

    def _get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def _load_match_ids(self) -> Set[str]:
        """Load all match IDs into cache."""
        if self._match_ids is None:
            with self._get_session() as session:
                result = session.query(Match.match_id).all()
                self._match_ids = {r[0] for r in result}
        return self._match_ids

    def save_match(self, match_data: Dict[str, Any]) -> bool:
        """Save a single match with all its data."""
        match_id = match_data.get("match_id")
        if not match_id:
            return False

        # Check cache first
        if self._match_ids is not None and match_id in self._match_ids:
            return False

        with self._get_session() as session:
            try:
                # Check if match exists in DB
                existing = session.query(Match.match_id).filter(Match.match_id == match_id).first()
                if existing:
                    if self._match_ids is not None:
                        self._match_ids.add(match_id)
                    return False

                # Extract team data
                team1 = match_data.get("team1", {})
                team2 = match_data.get("team2", {})

                # Create match record
                match = Match(
                    match_id=match_id,
                    match_url=match_data.get("match_url"),
                    team1_id=team1.get("team_id"),
                    team1_name=team1.get("name"),
                    team1_score=team1.get("score"),
                    team2_id=team2.get("team_id"),
                    team2_name=team2.get("name"),
                    team2_score=team2.get("score"),
                    event_id=match_data.get("event_id"),
                    event_name=match_data.get("event_name"),
                    event_url=match_data.get("event_url"),
                    date=match_data.get("date"),
                    time_unix=match_data.get("time_unix"),
                    match_format=match_data.get("match_format"),
                    format_type=match_data.get("format_type"),
                    winner=match_data.get("winner"),
                    final_score=match_data.get("final_score"),
                    scraped_at=datetime.utcnow(),
                )
                session.add(match)

                # Save maps
                for map_data in match_data.get("maps", []):
                    map_record = Map(
                        match_id=match_id,
                        map_number=map_data.get("map_number"),
                        map_name=map_data.get("map_name"),
                        team1_score=map_data.get("team1_score"),
                        team2_score=map_data.get("team2_score"),
                        team1_ct_score=map_data.get("team1_ct_score"),
                        team1_t_score=map_data.get("team1_t_score"),
                        team2_ct_score=map_data.get("team2_ct_score"),
                        team2_t_score=map_data.get("team2_t_score"),
                        winner=map_data.get("winner"),
                    )
                    session.add(map_record)

                # Save player stats and match players
                for team_key in ["team1_stats", "team2_stats"]:
                    team_stats = match_data.get(team_key)
                    if not team_stats:
                        continue

                    team_id = team_stats.get("team_id")
                    team_name = team_stats.get("team_name")

                    for player in team_stats.get("players", []):
                        # Player stats
                        stat = PlayerStat(
                            match_id=match_id,
                            team_id=team_id,
                            player_id=player.get("player_id"),
                            player_name=player.get("player_name"),
                            player_nick=player.get("player_nick"),
                            country=player.get("country"),
                            kills=player.get("kills"),
                            deaths=player.get("deaths"),
                            kd_diff=player.get("kd_diff"),
                            adr=player.get("adr"),
                            kast=player.get("kast"),
                            rating=player.get("rating"),
                            swing=player.get("swing"),
                        )
                        session.add(stat)

                        # Match player (roster snapshot)
                        match_player = MatchPlayer(
                            match_id=match_id,
                            team_id=team_id,
                            team_name=team_name,
                            player_id=player.get("player_id"),
                            player_nick=player.get("player_nick"),
                            country=player.get("country"),
                        )
                        session.add(match_player)

                        # Upsert player metadata
                        if player.get("player_id"):
                            stmt = insert(Player).values(
                                player_id=player.get("player_id"),
                                player_name=player.get("player_name"),
                                player_nick=player.get("player_nick"),
                                country=player.get("country"),
                            ).on_conflict_do_update(
                                index_elements=["player_id"],
                                set_={
                                    "player_name": player.get("player_name"),
                                    "player_nick": player.get("player_nick"),
                                    "country": player.get("country"),
                                    "last_updated": datetime.utcnow(),
                                }
                            )
                            session.execute(stmt)

                # Upsert team metadata
                for team in [team1, team2]:
                    if team.get("team_id"):
                        stmt = insert(Team).values(
                            team_id=team.get("team_id"),
                            team_name=team.get("name"),
                            team_logo_url=team.get("logo_url"),
                        ).on_conflict_do_update(
                            index_elements=["team_id"],
                            set_={
                                "team_name": team.get("name"),
                                "team_logo_url": team.get("logo_url"),
                                "last_updated": datetime.utcnow(),
                            }
                        )
                        session.execute(stmt)

                session.commit()

                # Update cache
                if self._match_ids is not None:
                    self._match_ids.add(match_id)

                return True

            except Exception as e:
                session.rollback()
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
        match_ids = self._load_match_ids()
        return match_id in match_ids

    def get_last_scraped_date(self) -> Optional[datetime]:
        """Get the date of the most recently scraped match."""
        with self._get_session() as session:
            result = session.query(func.max(Match.scraped_at)).scalar()
            return result

    def get_match_count(self) -> int:
        """Get total number of matches in storage."""
        with self._get_session() as session:
            return session.query(func.count(Match.id)).scalar() or 0

    def get_scraped_match_ids(self) -> List[str]:
        """Get list of all scraped match IDs."""
        return list(self._load_match_ids())

    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with self._get_session() as session:
            stats = {
                "total_matches": session.query(func.count(Match.id)).scalar() or 0,
                "total_maps": session.query(func.count(Map.id)).scalar() or 0,
                "total_player_stats": session.query(func.count(PlayerStat.id)).scalar() or 0,
                "total_teams": session.query(func.count(Team.id)).scalar() or 0,
                "total_players": session.query(func.count(Player.id)).scalar() or 0,
                "last_scraped": None,
                "storage_type": "postgres",
            }

            last_date = session.query(func.max(Match.scraped_at)).scalar()
            if last_date:
                stats["last_scraped"] = last_date.isoformat()

            return stats
