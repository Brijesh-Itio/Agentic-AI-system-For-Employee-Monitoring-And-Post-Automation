"""MODULE 5 — Leads routes.

Full CRUD against the leads table (schema owned by agent/database.py),
plus POST /research which triggers module 20's real Playwright pipeline
(Google search -> LinkedIn public profile -> company enrichment -> store).
Both Google and LinkedIn actively block automated access — verified
empirically (reCAPTCHA and authwall respectively) — so a 0-lead result is
an expected, honestly-reported outcome, not necessarily a bug.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import Lead, get_db
from api.schemas import LeadCreate, LeadOut, LeadUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("", response_model=list[LeadOut])
def list_leads(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Lead)
    if status:
        query = query.filter(Lead.status == status)
    return query.order_by(Lead.created_at.desc()).all()


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    row = db.query(Lead).filter(Lead.id == lead_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No lead with id {lead_id}")
    return row


@router.post("", response_model=LeadOut, status_code=201)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    """20.4's dedup rule: same name+company is an update, not a duplicate."""
    existing = None
    if payload.company:
        existing = (
            db.query(Lead)
            .filter(Lead.name == payload.name, Lead.company == payload.company)
            .first()
        )
    if existing:
        for field, value in payload.model_dump(exclude={"name", "company"}).items():
            if value is not None:
                setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    row = Lead(**payload.model_dump(), created_at=datetime.now())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)):
    row = db.query(Lead).filter(Lead.id == lead_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No lead with id {lead_id}")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    row = db.query(Lead).filter(Lead.id == lead_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No lead with id {lead_id}")
    db.delete(row)
    db.commit()


@router.post("/research")
def trigger_research(target_profile: str):
    """Synchronous, like /api/reports/dar/generate — real Playwright
    browser sessions against Google/LinkedIn, so this can take a while."""
    from ai.sub_agents import research_agent

    result = research_agent.run(target_profile=target_profile)
    if result["status"] != "success":
        raise HTTPException(status_code=502, detail=result["detail"])
    return result
