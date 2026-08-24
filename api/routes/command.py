"""MODULE 17 — Command Mode.

17.1 Command parser: rule-based regex, per DEVELOPMENT.md's explicit "never
     AI parser for reliability" instruction.
17.2 Command router: dispatches by parsed action.
17.3 Background job runner: each command runs in its own thread; state is
     persisted to the jobs table (not just an in-memory dict) so status
     survives across requests and is inspectable directly in SQLite.
17.4 Job status endpoint.
17.5 Job cancel endpoint: sets a threading.Event the job thread checks
     between steps.

Every action is real end-to-end — "report" (module 7's DAR generator),
"post" (module 18's LinkedIn pipeline), "email" (module 19's campaign
runner) and "find" (module 20's research pipeline) all call real
automation. Each still degrades honestly on missing prerequisites (no
LinkedIn credentials, Google/LinkedIn blocking automated access, etc.)
rather than faking success.
"""
import json
import logging
import re
import threading
import uuid
from datetime import date as date_type, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agent import database as agent_db
from api.auth import get_current_user
from api.database import Job, User, get_db
from api.schemas import CommandRequest, JobOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/command", tags=["command"])

_cancel_events: dict[str, threading.Event] = {}
_cancel_events_lock = threading.Lock()


# ── 17.1 Command parser ──

_ACTION_PATTERNS = [
    ("report", re.compile(r"\b(report|dar|daily activity)\b", re.I)),
    ("post", re.compile(r"\bpost\b.*\b(linkedin)?\b|\blinkedin\b", re.I)),
    ("email", re.compile(r"\b(email|campaign|outreach)\b", re.I)),
    ("find", re.compile(r"\b(find|research|leads?)\b", re.I)),
]


def parse_command(text: str) -> tuple[str, dict]:
    for action, pattern in _ACTION_PATTERNS:
        if pattern.search(text):
            return action, {"raw": text}
    return "unknown", {"raw": text}


# ── job persistence (raw sqlite — shared file, safe from any thread) ──

def _create_job(job_id: str, command: str, action: str) -> None:
    with agent_db.write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO jobs (id, command, action, status, progress, logs_json, created_at)
            VALUES (?, ?, ?, 'queued', 0, '[]', ?)
            """,
            (job_id, command, action, datetime.now().isoformat(sep=" ")),
        )


def _append_log(job_id: str, message: str) -> None:
    conn = agent_db.get_connection()
    row = conn.execute("SELECT logs_json FROM jobs WHERE id = ?", (job_id,)).fetchone()
    logs = json.loads(row["logs_json"]) if row else []
    logs.append({"at": datetime.now().isoformat(sep=" "), "message": message})
    with agent_db.write_cursor() as cur:
        cur.execute("UPDATE jobs SET logs_json = ? WHERE id = ?", (json.dumps(logs), job_id))


def _update_job(job_id: str, **fields) -> None:
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with agent_db.write_cursor() as cur:
        cur.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", (*fields.values(), job_id))


# ── 17.2 Command router + 17.3 background execution ──

def _run_job(job_id: str, action: str, params: dict, user_id: str) -> None:
    cancel_event = _cancel_events[job_id]
    _update_job(job_id, status="running", progress=10)
    _append_log(job_id, f"Routing action={action!r}")

    if cancel_event.is_set():
        _update_job(job_id, status="cancelled", completed_at=datetime.now().isoformat(sep=" "))
        _append_log(job_id, "Cancelled before execution started")
        return

    try:
        if action == "report":
            _append_log(job_id, "Calling module 7's DAR generator")
            from ai.dar_generator import generate_and_save_dar

            content = generate_and_save_dar(user_id=user_id)
            if content is None:
                raise RuntimeError("Ollama unreachable or timed out during DAR generation")
            _update_job(
                job_id,
                status="completed",
                progress=100,
                result=f"DAR generated for {date_type.today().isoformat()}",
                completed_at=datetime.now().isoformat(sep=" "),
            )
            _append_log(job_id, "DAR generated and saved")

        elif action == "post":
            _append_log(job_id, "Calling module 16.3's LinkedIn sub-agent")
            from ai.sub_agents import linkedin_agent

            # topic=None was hardcoded here regardless of what the user
            # actually typed (verified live: "write the post about how
            # claude can boost our productivity" still posted about a
            # rotation-list topic instead) — the raw command text itself
            # is the topic; only fall back to rotation for a truly generic
            # command like "post to linkedin" with no topic of its own.
            requested_topic = params["raw"].strip()
            generic_trigger_only = bool(re.fullmatch(r"(post( to)?( linkedin)?|linkedin)\W*", requested_topic, re.I))
            result = linkedin_agent.run(topic=None if generic_trigger_only else requested_topic)
            if result["status"] != "success":
                raise RuntimeError(result["detail"])
            _update_job(
                job_id, status="completed", progress=100, result=result["detail"],
                completed_at=datetime.now().isoformat(sep=" "),
            )
            _append_log(job_id, result["detail"])

        elif action == "email":
            _append_log(job_id, "Calling module 19's campaign runner")
            from automation.email.campaign import run_campaign

            result = run_campaign()
            summary = (
                f"{result['attempted']} attempted, {result['sent']} sent, "
                f"{result['skipped_unpersonalisable']} skipped, {result['failed']} failed"
            )
            _update_job(
                job_id, status="completed", progress=100, result=summary,
                completed_at=datetime.now().isoformat(sep=" "),
            )
            _append_log(job_id, summary)

        elif action == "find":
            _append_log(job_id, "Calling module 16.5's research sub-agent")
            from ai.sub_agents import research_agent

            result = research_agent.run(target_profile=params["raw"])
            if result["status"] != "success":
                raise RuntimeError(result["detail"])
            _update_job(
                job_id, status="completed", progress=100, result=result["detail"],
                completed_at=datetime.now().isoformat(sep=" "),
            )
            _append_log(job_id, result["detail"])

        else:
            raise RuntimeError(
                f"Could not parse an action from: {params['raw']!r}. "
                "Try wording it around report/post/email/find."
            )

    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        _update_job(
            job_id, status="failed", result=str(exc), completed_at=datetime.now().isoformat(sep=" ")
        )
        _append_log(job_id, f"Failed: {exc}")
    finally:
        with _cancel_events_lock:
            _cancel_events.pop(job_id, None)


@router.post("", response_model=JobOut, status_code=202)
def run_command(
    payload: CommandRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    action, params = parse_command(payload.command)
    job_id = str(uuid.uuid4())
    _create_job(job_id, payload.command, action)

    with _cancel_events_lock:
        _cancel_events[job_id] = threading.Event()

    thread = threading.Thread(target=_run_job, args=(job_id, action, params, current_user.id), daemon=True)
    thread.start()

    return get_job_status(job_id, db)


# ── 17.4 Job status endpoint ──

@router.get("/status/{job_id}", response_model=JobOut)
def get_job_status(job_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.query(Job).filter(Job.id == job_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No job {job_id}")
    return JobOut(
        id=row.id,
        command=row.command,
        action=row.action,
        status=row.status,
        progress=row.progress,
        logs=json.loads(row.logs_json),
        result=row.result,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


@router.get("/history", response_model=list[JobOut])
def job_history(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(Job).order_by(Job.created_at.desc()).limit(50).all()
    return [
        JobOut(
            id=r.id,
            command=r.command,
            action=r.action,
            status=r.status,
            progress=r.progress,
            logs=json.loads(r.logs_json),
            result=r.result,
            created_at=r.created_at,
            completed_at=r.completed_at,
        )
        for r in rows
    ]


# ── 17.5 Job cancel endpoint ──

@router.post("/cancel/{job_id}", response_model=JobOut)
def cancel_job(job_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    with _cancel_events_lock:
        event = _cancel_events.get(job_id)
    if event is None:
        raise HTTPException(status_code=409, detail=f"Job {job_id} is not running or does not exist")
    event.set()
    return get_job_status(job_id, db)
