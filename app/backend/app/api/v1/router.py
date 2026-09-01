"""Central API v1 router module aggregator.

Combines all v1 endpoint routers (chat, sessions, tours, trash, health) into a single router.
"""

from app.routes.chat import router as chat_router
from app.routes.health import router as health_router
from app.routes.sessions import router as sessions_router
from app.routes.tours import router as tours_router
from app.routes.trash import router as trash_router
from fastapi import APIRouter

api_v1_router = APIRouter()

api_v1_router.include_router(chat_router)
api_v1_router.include_router(sessions_router)
api_v1_router.include_router(tours_router)
api_v1_router.include_router(trash_router)
api_v1_router.include_router(health_router)
