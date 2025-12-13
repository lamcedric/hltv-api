from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.schemas.base import HLTVBaseModel, AuditMixin


class TeamInfo(HLTVBaseModel):
    """Team information within a match."""
    team_id: Optional[str] = None
    name: str
    logo_url: Optional[HttpUrl] = None
    score: Optional[int] = None


class MapResult(HLTVBaseModel):
    """Result of a single map in a match."""
    map_number: int
    map_name: str
    team1_score: Optional[int] = None
    team2_score: Optional[int] = None
    team1_ct_score: Optional[int] = None
    team1_t_score: Optional[int] = None
    team2_ct_score: Optional[int] = None
    team2_t_score: Optional[int] = None
    winner: Optional[str] = None  # 'team1', 'team2', or None if draw/not played


class PlayerMatchStats(HLTVBaseModel):
    """Player statistics for a match."""
    player_id: Optional[str] = None
    player_name: str
    player_nick: Optional[str] = None
    country: Optional[str] = None
    team_id: Optional[str] = None
    kills: Optional[int] = None
    deaths: Optional[int] = None
    kd_diff: Optional[int] = None
    adr: Optional[float] = None
    kast: Optional[float] = None
    rating: Optional[float] = None
    swing: Optional[float] = None

    @field_validator("kills", "deaths", mode="before")
    @classmethod
    def parse_kd(cls, v):
        """Parse K-D format like '47-50' into individual values."""
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str) and "-" in v:
            # Will be handled by the service layer
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    @field_validator("adr", "rating", mode="before")
    @classmethod
    def parse_float_stat(cls, v):
        """Parse float stats."""
        if v is None:
            return None
        if isinstance(v, float):
            return v
        try:
            return float(str(v).replace("%", ""))
        except (ValueError, TypeError):
            return None

    @field_validator("kast", mode="before")
    @classmethod
    def parse_kast(cls, v):
        """Parse KAST percentage."""
        if v is None:
            return None
        if isinstance(v, float):
            return v
        try:
            return float(str(v).replace("%", ""))
        except (ValueError, TypeError):
            return None

    @field_validator("swing", mode="before")
    @classmethod
    def parse_swing(cls, v):
        """Parse swing percentage like '+4.12%' or '-2.32%'."""
        if v is None:
            return None
        if isinstance(v, float):
            return v
        try:
            return float(str(v).replace("%", "").replace("+", ""))
        except (ValueError, TypeError):
            return None


class TeamMatchStats(HLTVBaseModel):
    """Team's player statistics for a match."""
    team_id: Optional[str] = None
    team_name: str
    team_logo_url: Optional[HttpUrl] = None
    players: List[PlayerMatchStats] = Field(default_factory=list)


class MatchResult(HLTVBaseModel):
    """Brief match result from the results listing page."""
    match_id: str
    match_url: str
    team1_name: str
    team2_name: str
    team1_score: Optional[int] = None
    team2_score: Optional[int] = None
    event_name: Optional[str] = None
    match_format: Optional[str] = None  # e.g., 'bo3', 'bo1'
    date: Optional[str] = None


class MatchDetails(HLTVBaseModel, AuditMixin):
    """Detailed match information from individual match page."""
    match_id: str
    match_url: Optional[HttpUrl] = None

    # Teams
    team1: TeamInfo
    team2: TeamInfo

    # Event info
    event_id: Optional[str] = None
    event_name: Optional[str] = None
    event_url: Optional[str] = None

    # Match info
    date: Optional[str] = None
    time_unix: Optional[int] = None
    match_format: Optional[str] = None  # e.g., 'Best of 3 (LAN)'
    format_type: Optional[str] = None  # e.g., 'bo3', 'bo1'

    # Results
    winner: Optional[str] = None  # 'team1', 'team2', or None
    final_score: Optional[str] = None  # e.g., '2-1'

    # Map results
    maps: List[MapResult] = Field(default_factory=list)

    # Player stats (optional, may need separate endpoint)
    team1_stats: Optional[TeamMatchStats] = None
    team2_stats: Optional[TeamMatchStats] = None


class MatchResultsPage(HLTVBaseModel, AuditMixin):
    """Paginated results from the /results page."""
    matches: List[MatchResult] = Field(default_factory=list)
    total_count: Optional[int] = None
    offset: int = 0
    has_more: bool = False
    next_offset: Optional[int] = None
