"""
Notes CRUD routes.

This router exposes REST endpoints for creating, listing, retrieving, updating, and deleting notes.
It is mounted under the `/api` prefix by `src/api/main.py`.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Response, status

from src.dao import notes_dao
from src.models.notes import Note, NoteCreate, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get(
    "",
    response_model=List[Note],
    summary="List notes",
    description="Return all notes ordered by last update descending.",
    operation_id="list_notes",
)
def list_notes() -> List[Note]:
    """List notes."""
    notes = notes_dao.list_notes()
    # Pydantic will parse ISO timestamps from DAO into datetime fields.
    return [Note.model_validate(n) for n in notes]


@router.get(
    "/{note_id}",
    response_model=Note,
    summary="Get note",
    description="Return a single note by its ID.",
    operation_id="get_note",
)
def get_note(note_id: int) -> Note:
    """Get a note by ID."""
    note = notes_dao.get_note(note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return Note.model_validate(note)


@router.post(
    "",
    response_model=Note,
    status_code=status.HTTP_201_CREATED,
    summary="Create note",
    description="Create a new note and return the created record.",
    operation_id="create_note",
)
def create_note(payload: NoteCreate) -> Note:
    """Create a new note."""
    created = notes_dao.create_note(title=payload.title, content=payload.content)
    return Note.model_validate(created)


@router.put(
    "/{note_id}",
    response_model=Note,
    summary="Update note",
    description="Update an existing note (partial update supported) and return the updated record.",
    operation_id="update_note",
)
def update_note(note_id: int, payload: NoteUpdate) -> Note:
    """Update an existing note by ID."""
    updated = notes_dao.update_note(note_id=note_id, title=payload.title, content=payload.content)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return Note.model_validate(updated)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete note",
    description="Delete a note by its ID.",
    operation_id="delete_note",
)
def delete_note(note_id: int) -> Response:
    """Delete a note by ID."""
    deleted = notes_dao.delete_note(note_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
