"""
SQLAlchemy models for HLTV match data.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Text, ForeignKey, Index, BigInteger
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Match(Base):
    """Match metadata table."""
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String(50), unique=True, nullable=False, index=True)
    match_url = Column(Text)
    team1_id = Column(String(50), index=True)
    team1_name = Column(String(255))
    team1_score = Column(Integer)
    team2_id = Column(String(50), index=True)
    team2_name = Column(String(255))
    team2_score = Column(Integer)
    event_id = Column(String(50), index=True)
    event_name = Column(String(255))
    event_url = Column(Text)
    date = Column(String(50), index=True)
    time_unix = Column(BigInteger)
    match_format = Column(Text)
    format_type = Column(String(50))
    winner = Column(String(255))
    final_score = Column(String(20))
    scraped_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    maps = relationship("Map", back_populates="match", cascade="all, delete-orphan")
    player_stats = relationship("PlayerStat", back_populates="match", cascade="all, delete-orphan")
    match_players = relationship("MatchPlayer", back_populates="match", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_match_date", "date"),
        Index("idx_match_teams", "team1_id", "team2_id"),
    )


class Map(Base):
    """Map results per match."""
    __tablename__ = "maps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String(50), ForeignKey("matches.match_id", ondelete="CASCADE"), nullable=False, index=True)
    map_number = Column(Integer)
    map_name = Column(String(50), index=True)
    team1_score = Column(Integer)
    team2_score = Column(Integer)
    team1_ct_score = Column(Integer)
    team1_t_score = Column(Integer)
    team2_ct_score = Column(Integer)
    team2_t_score = Column(Integer)
    winner = Column(String(255))

    # Relationships
    match = relationship("Match", back_populates="maps")


class PlayerStat(Base):
    """Player statistics per match."""
    __tablename__ = "player_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String(50), ForeignKey("matches.match_id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(String(50), index=True)
    player_id = Column(String(50), index=True)
    player_name = Column(String(255))
    player_nick = Column(String(255))
    country = Column(String(100))
    kills = Column(Integer)
    deaths = Column(Integer)
    kd_diff = Column(Integer)
    adr = Column(Float)
    kast = Column(Float)
    rating = Column(Float)
    swing = Column(Float)

    # Relationships
    match = relationship("Match", back_populates="player_stats")


class MatchPlayer(Base):
    """Players participating in a match (roster snapshot)."""
    __tablename__ = "match_players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String(50), ForeignKey("matches.match_id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(String(50), index=True)
    team_name = Column(String(255))
    player_id = Column(String(50), index=True)
    player_nick = Column(String(255))
    country = Column(String(100))

    # Relationships
    match = relationship("Match", back_populates="match_players")


class Team(Base):
    """Team metadata (deduplicated)."""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String(50), unique=True, nullable=False, index=True)
    team_name = Column(String(255))
    team_logo_url = Column(Text)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Player(Base):
    """Player metadata (deduplicated)."""
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(50), unique=True, nullable=False, index=True)
    player_name = Column(String(255))
    player_nick = Column(String(255))
    country = Column(String(100))
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
