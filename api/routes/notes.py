"""Notepad routes — each user's private notes, stored server-side.

The Notepad page keeps a localStorage copy for instant loading and offline
use; these endpoints are the durable copy. Notes are strictly per-user: every
query is scoped to the logged-in user's id, so nobody (managers and admins
included) can read or overwrite another user's notes.

PUT is an upsert keyed by the browser-generated note id, and only applies when
the incoming updated_at is not older than the stored one, so a stale device
can never overwrite a newer edit made elsewhere (last write wins).
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import Note, User, get_db
from api.schemas import NoteIn, NoteOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notes", tags=["notes"])


def _to_out(n: Note) -> NoteOut:
    try:
        tags = json.loads(n.tags_json or "[]")
    except ValueError:
        tags = []
    return NoteOut(
        id=n.id,
        title=n.title,
        html=n.html,
        tags=tags,
        color=n.color,
        pinned=bool(n.pinned),
        createdAt=n.created_at,
        updatedAt=n.updated_at,
    )


@router.get("", response_model=list[NoteOut])
def list_notes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Note).filter(Note.user_id == current_user.id).order_by(Note.updated_at.desc()).all()
    return [_to_out(n) for n in rows]


@router.put("/{note_id}", response_model=NoteOut)
def upsert_note(
    note_id: str,
    payload: NoteIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = db.get(Note, note_id)
    if note is not None and note.user_id != current_user.id:
        # Same answer as a missing note: don't reveal that the id exists.
        raise HTTPException(status_code=404, detail="Note not found")
    if note is None:
        note = Note(id=note_id, user_id=current_user.id, created_at=payload.createdAt, updated_at=payload.updatedAt)
        db.add(note)
    elif payload.updatedAt < note.updated_at:
        return _to_out(note)  # stale write — keep the newer stored version
    note.title = payload.title
    note.html = payload.html
    note.tags_json = json.dumps(payload.tags)
    note.color = payload.color
    note.pinned = int(payload.pinned)
    note.updated_at = payload.updatedAt
    db.commit()
    return _to_out(note)


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    note = db.get(Note, note_id)
    if note is not None and note.user_id == current_user.id:
        db.delete(note)
        db.commit()
