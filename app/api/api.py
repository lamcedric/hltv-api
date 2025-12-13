from fastapi import APIRouter

from app.api.endpoints import players
from app.api.endpoints import events
from app.api.endpoints import matches

api_router = APIRouter()

api_router.include_router(players.router, prefix="/players", tags=["Players"])

api_router.include_router(events.router, prefix="/events", tags=["Events"])

api_router.include_router(matches.router, prefix="/matches", tags=["Matches"]) 