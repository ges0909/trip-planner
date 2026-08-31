"""Pydantic schemas for public HTTP request bodies."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload for starting or continuing a chat session."""

    message: str = Field(min_length=1, max_length=10_000)
    session_id: str | None = Field(default=None, min_length=1, max_length=200)
    language: Literal["de", "en"] = "de"


class CreateTourRequest(BaseModel):
    """Payload for saving a generated tour."""

    markdown: str = Field(min_length=1, max_length=200_000)
    tour_type: Literal["bike", "road"]
    gpx: str | None = Field(default=None, max_length=10_000_000)
    session_id: str | None = Field(default=None, min_length=1, max_length=200)


class LastViewedTourRequest(BaseModel):
    """Payload for updating the last viewed tour reference."""

    tour_id: str = Field(min_length=1, max_length=200)


class TourMetrics(BaseModel):
    """Typed metrics for a planned tour."""

    distance_km: float | None = None
    elevation_gain_m: float | None = None
    duration_hours: float | None = None
    point_count: int = 0
    difficulty: Literal["easy", "moderate", "challenging"] | None = None
    route_type: str | None = None
    start_location: str | None = None


class TourDetailResponse(BaseModel):
    """Full tour details including markdown, GPX availability, and metrics."""

    id: str
    title: str
    tour_type: Literal["bike", "road"]
    slug: str
    summary: str | None = None
    created_at: str
    updated_at: str
    markdown: str | None = None
    has_gpx: bool = False
    metrics: TourMetrics = Field(default_factory=TourMetrics)
