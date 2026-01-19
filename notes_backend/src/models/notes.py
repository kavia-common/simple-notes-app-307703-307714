"""
Pydantic models for the Notes domain.

These schemas are designed to be used by FastAPI routers and services.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class _NoteBase(BaseModel):
    """Shared fields for note creation and updates."""

    title: str = Field(..., min_length=1, max_length=200, description="Note title")
    content: str = Field(..., description="Note content/body")


class NoteCreate(_NoteBase):
    """Request schema for creating a note."""


class NoteUpdate(BaseModel):
    """Request schema for updating a note (partial update supported)."""

    title: Optional[str] = Field(
        default=None, min_length=1, max_length=200, description="Updated note title"
    )
    content: Optional[str] = Field(default=None, description="Updated note content/body")


class Note(_NoteBase):
    """Response schema returned to clients."""

    id: int = Field(..., description="Note ID")
    created_at: datetime = Field(..., description="UTC timestamp when note was created")
    updated_at: datetime = Field(..., description="UTC timestamp when note was last updated")


class NoteInDB(Note):
    """Internal schema representing a note as stored in the DB."""
