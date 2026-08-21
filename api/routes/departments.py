"""MODULE 7 extension (7.5) — Departments & custom DAR field templates.

Fully admin-driven: departments and their custom fields are created here at
runtime, nothing is hardcoded. Each department has at most one template
(fields_json), and a NULL-department template row acts as the default/base
template applied when a department has none of its own.
"""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import DarTemplate, Department, get_db
from api.schemas import DarTemplateOut, DarTemplateUpdate, DepartmentCreate, DepartmentOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).order_by(Department.name.asc()).all()


@router.post("", response_model=DepartmentOut, status_code=201)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db)):
    if db.query(Department).filter(Department.name == payload.name).first() is not None:
        raise HTTPException(status_code=409, detail=f"Department {payload.name!r} already exists")
    row = Department(name=payload.name, created_at=datetime.now())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{department_id}", status_code=204)
def delete_department(department_id: int, db: Session = Depends(get_db)):
    row = db.query(Department).filter(Department.id == department_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No department {department_id}")
    db.delete(row)
    db.commit()


def _template_out(row: DarTemplate | None, department_id: int | None) -> DarTemplateOut:
    if row is None:
        return DarTemplateOut(department_id=department_id, fields=[], updated_at=None)
    return DarTemplateOut(
        department_id=row.department_id,
        fields=json.loads(row.fields_json),
        updated_at=row.updated_at,
    )


@router.get("/{department_id}/template", response_model=DarTemplateOut)
def get_department_template(department_id: int, db: Session = Depends(get_db)):
    """Falls back to the default (NULL-department) template when this
    department has never defined its own, so callers always get something
    usable instead of a 404."""
    if db.query(Department).filter(Department.id == department_id).first() is None:
        raise HTTPException(status_code=404, detail=f"No department {department_id}")

    row = db.query(DarTemplate).filter(DarTemplate.department_id == department_id).first()
    if row is None:
        row = db.query(DarTemplate).filter(DarTemplate.department_id.is_(None)).first()
    return _template_out(row, department_id)


@router.put("/{department_id}/template", response_model=DarTemplateOut)
def set_department_template(
    department_id: int, payload: DarTemplateUpdate, db: Session = Depends(get_db)
):
    if db.query(Department).filter(Department.id == department_id).first() is None:
        raise HTTPException(status_code=404, detail=f"No department {department_id}")

    keys = [f.key for f in payload.fields]
    if len(keys) != len(set(keys)):
        raise HTTPException(status_code=422, detail="Field keys must be unique within a template")

    row = db.query(DarTemplate).filter(DarTemplate.department_id == department_id).first()
    fields_json = json.dumps([f.model_dump() for f in payload.fields])
    if row is None:
        row = DarTemplate(department_id=department_id, fields_json=fields_json, updated_at=datetime.now())
        db.add(row)
    else:
        row.fields_json = fields_json
        row.updated_at = datetime.now()
    db.commit()
    db.refresh(row)
    return _template_out(row, department_id)


@router.get("/default/template", response_model=DarTemplateOut)
def get_default_template(db: Session = Depends(get_db)):
    row = db.query(DarTemplate).filter(DarTemplate.department_id.is_(None)).first()
    return _template_out(row, None)


@router.put("/default/template", response_model=DarTemplateOut)
def set_default_template(payload: DarTemplateUpdate, db: Session = Depends(get_db)):
    keys = [f.key for f in payload.fields]
    if len(keys) != len(set(keys)):
        raise HTTPException(status_code=422, detail="Field keys must be unique within a template")

    row = db.query(DarTemplate).filter(DarTemplate.department_id.is_(None)).first()
    fields_json = json.dumps([f.model_dump() for f in payload.fields])
    if row is None:
        row = DarTemplate(department_id=None, fields_json=fields_json, updated_at=datetime.now())
        db.add(row)
    else:
        row.fields_json = fields_json
        row.updated_at = datetime.now()
    db.commit()
    db.refresh(row)
    return _template_out(row, None)
