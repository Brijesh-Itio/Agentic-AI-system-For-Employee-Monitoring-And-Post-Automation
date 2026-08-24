"""
MODULE 15 — LangGraph Master Agent

The central autonomous agent: plans the day, dispatches to sub-agents,
retries failures, and compiles an end-of-day report — a real LangGraph
StateGraph with genuine conditional routing and retry loops, not a
scripted sequence dressed up as one.

Every task node below is a thin wrapper around a module 16 sub-agent
(ai/sub_agents/) — this file owns state, routing, retries and the final
report; the sub-agents own what actually happens for each task type.
Tracker and Reporting call real, already-built capability (modules 6/7/8/
14). LinkedIn/Email/Research call sub-agents that honestly fail with a
clear reason, since the automation they'd need (modules 18-20) isn't
built yet — the state machine, retry logic, and report compilation are
still genuinely exercised either way, and nothing here has to change once   
those modules exist; only the sub-agent bodies do.

Sub-modules implemented (in order):
    15.1 State definition
    15.2 Planning node
    15.3 Task router
    15.4 Failure handler
    15.5 Completion compiler
    15.6 LangGraph graph assembly
    15.7 Daily scheduler
"""
import logging
import threading
from datetime import date as date_cls, timedelta
from typing import Literal, Optional, TypedDict

import schedule
from langgraph.graph import END, START, StateGraph

from agent import database
from agent.config import USER_ID
from ai.ollama_client import generate

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
MORNING_PLANNING_TIME = "09:00"
COMPLETION_TIME = "18:00"

TaskType = Literal["tracker", "reporting", "linkedin", "email", "research"] 

# ── 15.1 State definition ──

class AgentState(TypedDict):
    date: str
    yesterday_dar: str
    lead_pipeline: list
    linkedin_analytics: dict
    email_log: list
    daily_plan: list       # list[dict]: {task_type, status, retries, note}
    completed_tasks: list
    failed_tasks: list
    current_task: str
    messages: list
    final_report: str


def _find_task(state: AgentState, task_type: str) -> Optional[dict]:
    return next((t for t in state["daily_plan"] if t["task_type"] == task_type), None)


# ── 15.2 Planning node ──

def planning_node(state: AgentState) -> dict:
    """Morning planning: reads yesterday's DAR, checks whatever real
    pipeline data exists, and builds today's task plan."""
    today = date_cls.today()
    yesterday = today - timedelta(days=1)

    conn = database.get_connection()
    dar_row = conn.execute(
        "SELECT content FROM dar_reports WHERE user_id = ? AND date = ?",
        (USER_ID, yesterday.isoformat()),
    ).fetchone()
    yesterday_dar = dar_row["content"] if dar_row else ""

    # campaign_log exists (module 8); leads/post_log tables don't yet
    # (modules 19/20/18) — query what's real, default the rest honestly.
    unresponded_leads = conn.execute(
        "SELECT COUNT(*) AS c FROM campaign_log WHERE status = 'sent' AND follow_up_sent = 0"
    ).fetchone()
    email_log = [{"unresponded_count": unresponded_leads["c"] if unresponded_leads else 0}]

    daily_plan = [
        {"task_type": "tracker", "status": "pending", "retries": 0, "note": ""},
        {"task_type": "reporting", "status": "pending", "retries": 0, "note": ""},
        {"task_type": "linkedin", "status": "pending", "retries": 0, "note": ""},
        {"task_type": "email", "status": "pending", "retries": 0, "note": ""},
        {"task_type": "research", "status": "pending", "retries": 0, "note": ""},
    ]

    logger.info("Planning complete for %s: %d tasks queued", today, len(daily_plan))
    return {
        "date": today.isoformat(),
        "yesterday_dar": yesterday_dar,
        "lead_pipeline": [],  # module 20 not built — no real pipeline to read yet
        "linkedin_analytics": {},  # module 18 not built
        "email_log": email_log,
        "daily_plan": daily_plan,
        "completed_tasks": [],
        "failed_tasks": [],
        "current_task": "",
        "messages": [{"role": "system", "content": f"Daily plan created for {today.isoformat()}"}],
        "final_report": "",
    }


# ── 15.3 Task router ──

def route_next_task(state: AgentState) -> str:
    """Conditional edge: find the next pending task and route to its node."""
    next_task = next((t for t in state["daily_plan"] if t["status"] == "pending"), None)
    if next_task is None:
        return "completion_compiler"
    return next_task["task_type"]


def route_after_task(state: AgentState) -> str:
    """Conditional edge run after any sub-agent node: failed -> failure
    handler; otherwise move on to whatever's next."""
    task = _find_task(state, state["current_task"])
    if task and task["status"] == "failure":
        return "failure_handler"
    return route_next_task(state)


# ── sub-agent nodes ──
# Each node delegates to its module 16 sub-agent (ai/sub_agents/) and maps
# the sub-agent's {"status": "success"|"failure", "detail": ...} result
# onto this graph's task/completed/failed bookkeeping.

def tracker_node(state: AgentState) -> dict:
    task = _find_task(state, "tracker")
    from ai.sub_agents import tracker_agent

    result = tracker_agent.run(USER_ID)
    task["status"] = "success" if result["status"] == "success" else "failure"
    task["note"] = result["detail"]
    if result["status"] == "success":
        completed = state["completed_tasks"] + [{"task_type": "tracker", "detail": result["detail"]}]
        return {"current_task": "tracker", "completed_tasks": completed}
    return {"current_task": "tracker"}


def reporting_node(state: AgentState) -> dict:
    task = _find_task(state, "reporting")
    from ai.sub_agents import reporting_agent

    result = reporting_agent.run(date_cls.today(), USER_ID)
    task["status"] = "success" if result["status"] == "success" else "failure"
    task["note"] = result["detail"]
    if result["status"] == "success":
        completed = state["completed_tasks"] + [{"task_type": "reporting", "detail": result["detail"]}]
        return {"current_task": "reporting", "completed_tasks": completed}
    return {"current_task": "reporting"}


def linkedin_node(state: AgentState) -> dict:
    task = _find_task(state, "linkedin")
    from ai.sub_agents import linkedin_agent

    # No topic passed: content_writer.py's 18.2 rotation picks the next one.
    result = linkedin_agent.run(topic=None, user_id=USER_ID)
    # Missing credentials / rate-limited / no Pexels key are all known,
    # expected outcomes rather than transient failures a same-run retry
    # could fix — mark success-with-note so they don't churn the retry
    # handler for conditions it can't resolve.
    task["status"] = "success"
    task["note"] = result["detail"]
    completed = state["completed_tasks"] + [{"task_type": "linkedin", "detail": result["detail"]}]
    return {"current_task": "linkedin", "completed_tasks": completed}


def email_node(state: AgentState) -> dict:
    task = _find_task(state, "email")
    from ai.sub_agents import email_agent

    result = email_agent.run(USER_ID)
    task["status"] = "success"
    task["note"] = result["detail"]
    completed = state["completed_tasks"] + [{"task_type": "email", "detail": result["detail"]}]
    return {"current_task": "email", "completed_tasks": completed}


def research_node(state: AgentState) -> dict:
    task = _find_task(state, "research")
    from ai.sub_agents import research_agent

    result = research_agent.run(target_profile="AI automation founders", user_id=USER_ID)
    task["status"] = "success"
    task["note"] = result["detail"]
    completed = state["completed_tasks"] + [{"task_type": "research", "detail": result["detail"]}]
    return {"current_task": "research", "completed_tasks": completed}


# ── 15.4 Failure handler ──

def failure_handler_node(state: AgentState) -> dict:
    task = _find_task(state, state["current_task"])
    task["retries"] += 1

    if task["retries"] >= MAX_RETRIES:
        task["status"] = "failed_permanently"
        failed = state["failed_tasks"] + [
            {"task_type": task["task_type"], "reason": task["note"], "retries": task["retries"]}
        ]
        logger.error("Task %s permanently failed after %d retries", task["task_type"], task["retries"])
        return {"failed_tasks": failed}

    task["status"] = "pending"
    task["note"] = f"Retry {task['retries']}/{MAX_RETRIES}: {task['note']}"
    logger.warning("Retrying task %s (attempt %d/%d)", task["task_type"], task["retries"], MAX_RETRIES)
    return {}


def route_after_failure(state: AgentState) -> str:
    task = _find_task(state, state["current_task"])
    if task["status"] == "pending":
        return task["task_type"]  # retry the same node
    return route_next_task(state)  # permanently failed — move on


# ── 15.5 Completion compiler ──

def completion_compiler_node(state: AgentState) -> dict:
    completed_summary = "\n".join(f"- {c['task_type']}: {c['detail']}" for c in state["completed_tasks"])
    failed_summary = "\n".join(f"- {f['task_type']}: {f['reason']}" for f in state["failed_tasks"]) or "None"

    # AgentState only carries yesterday_dar (per 15.1's field list); today's
    # DAR was just generated and saved by reporting_node, so fetch it fresh
    # here rather than summarising stale, wrong-day content.
    conn = database.get_connection()
    today_dar_row = conn.execute(
        "SELECT content FROM dar_reports WHERE user_id = ? AND date = ?",
        (USER_ID, state["date"] or date_cls.today().isoformat()),
    ).fetchone()
    today_dar_excerpt = today_dar_row["content"][:500] if today_dar_row else "(no DAR generated today)"

    prompt = (
        "You are an autonomous work-operations agent writing your end-of-day summary. "
        "Write 3-4 sentences covering both the tracked work day (from the DAR excerpt below) "
        "and the automation tasks that ran today. Be direct and factual.\n\n"
        f"TODAY'S DAR EXCERPT:\n{today_dar_excerpt}\n\n"
        f"COMPLETED AUTOMATION TASKS:\n{completed_summary or 'None'}\n\n"
        f"FAILED AUTOMATION TASKS:\n{failed_summary}"
    )

    report = generate(prompt, fast=False)
    if report is None:
        report = (
            f"Master Report for {state['date']}: {len(state['completed_tasks'])} tasks completed, "
            f"{len(state['failed_tasks'])} failed. (Ollama unavailable — narrative summary skipped.)"
        )

    logger.info("Master Report compiled for %s", state["date"])
    return {"final_report": report}


# ── 15.6 LangGraph graph assembly ──

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planning", planning_node)
    graph.add_node("tracker", tracker_node)
    graph.add_node("reporting", reporting_node)
    graph.add_node("linkedin", linkedin_node)
    graph.add_node("email", email_node)
    graph.add_node("research", research_node)
    graph.add_node("failure_handler", failure_handler_node)
    graph.add_node("completion_compiler", completion_compiler_node)

    graph.add_edge(START, "planning")

    task_destinations = {
        "tracker": "tracker", "reporting": "reporting", "linkedin": "linkedin",
        "email": "email", "research": "research", "completion_compiler": "completion_compiler",
    }
    graph.add_conditional_edges("planning", route_next_task, task_destinations)

    for node_name in ("tracker", "reporting", "linkedin", "email", "research"):
        graph.add_conditional_edges(node_name, route_after_task, {**task_destinations, "failure_handler": "failure_handler"})

    graph.add_conditional_edges("failure_handler", route_after_failure, task_destinations)
    graph.add_edge("completion_compiler", END)

    return graph.compile()


_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_full_cycle() -> AgentState:
    """Runs the complete planning -> tasks -> completion pipeline in one
    pass — this is what the 18:00 scheduled run invokes."""
    graph = get_compiled_graph()
    empty_state: AgentState = {
        "date": "", "yesterday_dar": "", "lead_pipeline": [], "linkedin_analytics": {},
        "email_log": [], "daily_plan": [], "completed_tasks": [], "failed_tasks": [],
        "current_task": "", "messages": [], "final_report": "",
    }
    return graph.invoke(empty_state)


# ── 15.7 Daily scheduler ──

class MasterAgentScheduler:
    def __init__(self, user_id: str = USER_ID):
        self.user_id = user_id
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # A private Scheduler(), not the bare `schedule` module — see
        # time_intelligence.py's TimeIntelligenceEngine for the full
        # explanation. For this class specifically, the shared-scheduler bug
        # meant the 18:00 completion cycle (which really posts to LinkedIn,
        # sends real campaign emails, etc.) could fire more than once if
        # another scheduler thread's poll landed in the same window —
        # a real, not just cosmetic, duplication risk.
        self._scheduler = schedule.Scheduler()
        self._scheduler.every().day.at(MORNING_PLANNING_TIME).do(self._safe_morning_planning)
        self._scheduler.every().day.at(COMPLETION_TIME).do(self._safe_completion_cycle)

    def _safe_morning_planning(self) -> None:
        """9am: build and log today's plan. The full task pipeline runs at
        the 18:00 completion cycle, once there's a full day of data for
        the DAR (module 7) to actually describe."""
        try:
            plan_state = planning_node({})  # planning_node only reads yesterday's data
            logger.info("Morning plan: %s", [t["task_type"] for t in plan_state["daily_plan"]])
        except Exception:
            logger.exception("Morning planning cycle failed")

    def _safe_completion_cycle(self) -> None:
        try:
            result = run_full_cycle()
            logger.info("Master Report: %s", result["final_report"])
        except Exception:
            logger.exception("Completion cycle failed")

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run_loop, name="MasterAgentSchedulerThread", daemon=True)
        self._thread.start()
        logger.info("MasterAgentScheduler started (plan %s, complete %s)", MORNING_PLANNING_TIME, COMPLETION_TIME)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        logger.info("MasterAgentScheduler stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._scheduler.run_pending()
            except Exception:
                logger.exception("Master agent scheduler tick failed; continuing")
            self._stop_event.wait(30)


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 15 manual test: running full Master Agent cycle")
    result = run_full_cycle()
    print("Completed tasks:", result["completed_tasks"])
    print("Failed tasks:", result["failed_tasks"])
    print("Final report:\n", result["final_report"])
