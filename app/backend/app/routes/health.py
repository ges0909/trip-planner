"""Health check endpoint."""

import os
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """Health check endpoint."""
    has_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))

    return {
        "status": "ok",
        "providers": {
            "openrouter": has_openrouter,
        },
    }
