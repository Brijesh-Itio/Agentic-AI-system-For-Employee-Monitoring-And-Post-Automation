"""HR-customisable outbound email template routes.

Not in DEVELOPMENT.md's original module list — added on request so HR can
set a different email format for each kind of outbound email (DAR reports,
each alert type, holiday announcements) instead of the fixed formats module
8 shipped with. automation/email/sender.py owns the actual default
templates and $variable substitution (`render_template`); this file is just
CRUD + a preview around agent/database.py's email_templates table.

HR/admin-only, same authority as the holiday calendar (api/routes/holidays.py).
"""
import logging
from string import Template

from fastapi import APIRouter, Depends, HTTPException

from agent import database as agent_db
from api.auth import require_hr
from api.database import User
from api.schemas import EmailTemplateOut, EmailTemplatePreview, EmailTemplateUpdate
from automation.email.sender import ALERT_TYPES, DEFAULT_TEMPLATES, render_template, send_raw_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/email-templates", tags=["email-templates"])

# Realistic stand-in values so HR can see roughly what an email will look
# like without needing a real DAR/alert to exist first. Keyed by the same
# template_key as DEFAULT_TEMPLATES (e.g. "alert_focus"), built from the
# bare alert_type names in ALERT_TYPES ("focus") — not from DEFAULT_TEMPLATES'
# own keys, which are already prefixed and would double up to "alert_alert_focus".
_PREVIEW_VARIABLES: dict[str, dict[str, str]] = {
    "dar_report": {"date": "2026-01-15", "score": "82%", "content": "(the day's full DAR content goes here)"},
    **{
        f"alert_{alert_type}": {
            "alert_type": alert_type,
            "message": "This is a sample alert message.",
            "time": "2026-01-15 14:32:00",
            "dashboard_url": "http://localhost:5173",
        }
        for alert_type in ALERT_TYPES
    },
}


def _to_out(template_key: str) -> EmailTemplateOut:
    default = DEFAULT_TEMPLATES[template_key]
    custom = agent_db.get_email_template(template_key)
    return EmailTemplateOut(
        template_key=template_key,
        label=default["label"],
        subject=custom["subject_template"] if custom else default["subject"],
        body=custom["body_template"] if custom else default["body"],
        variables=default["variables"],
        is_custom=custom is not None,
        updated_by=custom["updated_by"] if custom else None,
        updated_at=custom["updated_at"] if custom else None,
    )


@router.get("", response_model=list[EmailTemplateOut])
def list_templates(_: User = Depends(require_hr)):
    return [_to_out(key) for key in DEFAULT_TEMPLATES]


@router.put("/{template_key}", response_model=EmailTemplateOut)
def update_template(template_key: str, payload: EmailTemplateUpdate, current_user: User = Depends(require_hr)):
    if template_key not in DEFAULT_TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Unknown template_key. Must be one of {list(DEFAULT_TEMPLATES)}")
    agent_db.set_email_template(template_key, payload.subject, payload.body, current_user.id)
    return _to_out(template_key)


@router.post("/{template_key}/reset", response_model=EmailTemplateOut)
def reset_template(template_key: str, _: User = Depends(require_hr)):
    if template_key not in DEFAULT_TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Unknown template_key. Must be one of {list(DEFAULT_TEMPLATES)}")
    agent_db.reset_email_template(template_key)
    return _to_out(template_key)


@router.post("/{template_key}/preview", response_model=EmailTemplatePreview)
def preview_template(template_key: str, payload: EmailTemplateUpdate, _: User = Depends(require_hr)):
    """Renders the *unsaved* subject/body currently in the editor against
    sample data, so HR sees the real result before committing it."""
    if template_key not in DEFAULT_TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Unknown template_key. Must be one of {list(DEFAULT_TEMPLATES)}")
    variables = _PREVIEW_VARIABLES.get(template_key, {})
    subject = Template(payload.subject).safe_substitute(**variables)
    body = Template(payload.body).safe_substitute(**variables)
    return EmailTemplatePreview(subject=subject, body=body)


@router.post("/{template_key}/send-test")
def send_test(template_key: str, current_user: User = Depends(require_hr)):
    """Actually sends the current (saved-or-default) template to HR's own
    address via the real pipeline — the only way to verify formatting
    survives a real mail client, not just the in-app preview."""
    if template_key not in DEFAULT_TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Unknown template_key. Must be one of {list(DEFAULT_TEMPLATES)}")
    if not current_user.email:
        raise HTTPException(status_code=400, detail="Your account has no email address to send a test to")

    variables = _PREVIEW_VARIABLES.get(template_key, {})
    subject, body = render_template(template_key, **variables)
    sent = send_raw_email(current_user.email, f"[TEST] {subject}", body)
    if not sent:
        raise HTTPException(status_code=502, detail="Send failed — check Gmail is configured (Module 8)")
    return {"sent": True, "to": current_user.email}
