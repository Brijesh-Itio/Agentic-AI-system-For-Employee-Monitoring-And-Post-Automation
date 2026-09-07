"""
MODULE 25.6 — SEO Master Agent (skeleton).
MODULE 33 — real pipeline nodes + autonomous daily scheduling.

A separate LangGraph StateGraph from ai/master_agent.py, not bolted onto
the existing daily Master Agent — SEO pipelines need cadences (nightly
crawl, 7am monitoring, on-publish content, monthly audits) that don't fit
that agent's single 09:00/18:00 daily cycle.

Module 25.6 built only the skeleton: a planning node and a completion
compiler, with no real pipeline task nodes since no pipeline existed yet.
Module 33 fills that in — five task nodes wired into the graph, one call
per active site per day, each independently idempotent via seo_job_runs
(agent/database.py's start_job_run/finish_job_run — the same UNIQUE
(site_id, job_type, run_date) guarantee module 25 built and every manual
endpoint in api/routes/seo.py already relies on):

    technical_audit -> gsc_pull -> ga4_pull -> pagespeed_check -> digest

Each node is graceful-degrade, matching every other external-call site in
this codebase: a failure logs, marks that job_run failed, and the graph
continues to the next node rather than aborting the whole site's cycle
over one bad step. Deliberately excluded from this automated cycle:
social content generation/posting and backlink outreach drafting/sending
— those stay human-triggered (drafts still require an explicit Approve
before anything is posted or sent), since auto-publishing to a real
LinkedIn account or a real inbox on a schedule is a materially different
risk than crawling a site or pulling read-only analytics.

api/main.py's lifespan starts an APScheduler BackgroundScheduler (a real
OS thread, independent of FastAPI's asyncio loop — every function this
module calls is synchronous `requests`-based, same as the rest of
automation/seo) that fires run_full_cycle() once a day at
settings.SEO_AUTOMATION_HOUR, when settings.SEO_AUTOMATION_ENABLED. A
manual POST /api/seo/jobs/run-daily-cycle exists for on-demand testing
without waiting for the schedule — it calls this exact same function.

Sub-modules implemented (in order):
    25.6.1 State definition
    25.6.2 Planning node
    25.6.3 Completion compiler
    25.6.4 LangGraph graph assembly
    33.1 Per-site task nodes (technical audit, GSC, GA4, PageSpeed, digest)
    33.2 Multi-site orchestration (run_full_cycle)
"""
import json
import logging
from datetime import date as date_cls, timedelta
from typing import Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from agent import database
from ai.llm.factory import get_provider
from ai.seo.daily_digest import generate_daily_digest
from api.config import settings
from automation.seo.crawler import crawl_site, fetch_sitemap_urls
from automation.seo.ga4_client import fetch_traffic_by_page
from automation.seo.gsc_client import fetch_search_analytics
from automation.seo.pagespeed_client import fetch_page_speed
from automation.seo.slack_notifier import send_slack_message
from automation.seo.technical_audit import run_all_detectors

logger = logging.getLogger(__name__)

# ── 25.6.1 State definition ──


class SeoAgentState(TypedDict):
    date: str
    active_site_ids: list
    # list[dict]: {job_type, site_id, status, retries, note} — always
    # empty until module 26 registers real job types and their nodes.
    daily_plan: list
    completed_tasks: list
    failed_tasks: list
    current_task: str
    final_report: str
    # 33.1 — the one site this graph invocation runs its pipeline for.
    # None during the (unused) multi-site planning_node/completion_compiler
    # path kept for the module 25.6 skeleton test — see run_full_cycle.
    site: Optional[dict]


# ── 25.6.2 Planning node ──


def planning_node(state: SeoAgentState) -> dict:
    """Reads the active site registry and builds today's plan. Retained
    from the module 25.6 skeleton for the no-pipeline test case; the real
    per-site pipeline (module 33) is driven by run_full_cycle below,
    which invokes the graph once per site rather than through this node."""
    sites = database.get_active_seo_sites()
    site_ids = [s["id"] for s in sites]

    logger.info("SEO planning: %d active site(s)", len(site_ids))
    return {
        "date": date_cls.today().isoformat(),
        "active_site_ids": site_ids,
        "daily_plan": [],
        "completed_tasks": [],
        "failed_tasks": [],
        "current_task": "",
        "final_report": "",
    }


# ── 33.1 Per-site task nodes ──
# Each node follows the same shape: skip cleanly if today's run for this
# (site_id, job_type) already exists (idempotent — a duplicate scheduler
# tick or a manual re-run is routine, not an error), otherwise do the
# real work inside a try/except that finishes the job_run as
# failed-but-non-fatal on any exception, exactly like every manual
# endpoint in api/routes/seo.py already does for the same call.


def _effective_gsc_url(site: dict) -> Optional[str]:
    """Mirrors api/routes/seo.py's helper of the same name — .env's
    GSC_SITE_URL only unambiguously describes 'the one site' when
    there's exactly one active site. Verified live that this matters:
    with a second site registered and no per-site override, gsc_pull
    silently pulled and stored the FIRST site's real data under the
    second site's id, reporting "success" throughout."""
    if site.get("gsc_site_url"):
        return site["gsc_site_url"]
    return settings.GSC_SITE_URL if database.count_active_seo_sites() <= 1 else None


def _effective_ga4_property(site: dict) -> Optional[str]:
    if site.get("ga4_property_id"):
        return site["ga4_property_id"]
    return settings.GA4_PROPERTY_ID if database.count_active_seo_sites() <= 1 else None


def _run_job(state: SeoAgentState, job_type: str, work) -> dict:
    site = state["site"]
    site_id = site["id"]
    run_date = date_cls.today()

    run_id = database.start_job_run(site_id, job_type, run_date)
    if run_id is None:
        logger.info("SEO %s already ran today for site %s — skipping", job_type, site_id)
        return {"completed_tasks": state["completed_tasks"] + [f"{job_type}:skipped"]}

    try:
        work(site, run_date)
        database.finish_job_run(run_id, "success")
        return {"completed_tasks": state["completed_tasks"] + [job_type]}
    except Exception as exc:
        logger.exception("SEO %s failed for site %s", job_type, site_id)
        database.finish_job_run(run_id, "failed", error=str(exc))
        return {"failed_tasks": state["failed_tasks"] + [job_type]}


def technical_audit_node(state: SeoAgentState) -> dict:
    def work(site: dict, run_date):
        pages = crawl_site(site["base_url"], max_pages=100)
        if not pages:
            raise RuntimeError("crawl_site returned no pages")
        known_urls = fetch_sitemap_urls(site["base_url"])
        issues = run_all_detectors(pages, known_urls=known_urls, base_url=site["base_url"])
        database.upsert_technical_issues(site["id"], run_date, issues)

    return _run_job(state, "technical_audit", work)


def gsc_pull_node(state: SeoAgentState) -> dict:
    def work(site: dict, run_date):
        start_date = run_date - timedelta(days=7)
        rows = fetch_search_analytics(start_date, run_date, site_url=_effective_gsc_url(site))
        if rows is None:
            raise RuntimeError("fetch_search_analytics failed — see server logs")
        database.upsert_gsc_query_rows(site["id"], run_date, rows)

    return _run_job(state, "gsc_pull", work)


def ga4_pull_node(state: SeoAgentState) -> dict:
    def work(site: dict, run_date):
        rows = fetch_traffic_by_page(property_id=_effective_ga4_property(site))
        if rows is None:
            raise RuntimeError("fetch_traffic_by_page failed — see server logs")
        database.upsert_ga4_page_rows(site["id"], run_date, rows)

    return _run_job(state, "ga4_pull", work)


def pagespeed_node(state: SeoAgentState) -> dict:
    def work(site: dict, run_date):
        result = fetch_page_speed(site["base_url"], strategy="mobile")
        if result is None:
            raise RuntimeError("fetch_page_speed failed — see server logs")
        database.upsert_pagespeed_result(
            site_id=site["id"],
            url=result.url,
            strategy=result.strategy,
            run_date=run_date,
            performance_score=result.performance_score,
            lcp_ms=result.lcp_ms,
            cls=result.cls,
            inp_ms=result.inp_ms,
            ttfb_ms=result.ttfb_ms,
            fcp_ms=result.fcp_ms,
            raw_json=json.dumps(result.raw),
        )

    return _run_job(state, "pagespeed_check", work)


def digest_node(state: SeoAgentState) -> dict:
    def work(site: dict, run_date):
        digest = generate_daily_digest(site["id"], site["name"])
        stats_json = json.dumps(
            {
                "pending_issues": digest.stats.pending_issues,
                "critical_issues": digest.stats.critical_issues,
                "latest_performance_score": digest.stats.latest_performance_score,
                "top_gsc_queries": digest.stats.top_gsc_queries,
                "top_ga4_pages": digest.stats.top_ga4_pages,
                "recent_job_failures": digest.stats.recent_job_failures,
            }
        )
        slack_delivered = send_slack_message(f"*SEO Digest — {site['name']}*\n{digest.narrative}")
        database.save_daily_digest(site["id"], run_date, digest.narrative, stats_json, slack_delivered)

    return _run_job(state, "daily_digest", work)


# ── 25.6.3 Completion compiler ──


def completion_compiler_node(state: SeoAgentState) -> dict:
    site = state["site"]
    if site is None:
        prompt = (
            "You are an autonomous SEO operations agent writing a one-sentence "
            "status note for today's cycle. No SEO pipelines are wired up yet "
            f"(foundation-only build); {len(state['active_site_ids'])} site(s) are "
            "registered and ready for future pipelines. Be direct and factual."
        )
        fallback = (
            f"SEO cycle for {state['date']}: {len(state['active_site_ids'])} active site(s), "
            "no pipelines run yet (foundation build; LLM unavailable for summary)."
        )
    else:
        prompt = (
            "You are an autonomous SEO operations agent. Write one factual sentence "
            f"summarising today's automated pipeline run for \"{site['name']}\": "
            f"{len(state['completed_tasks'])} step(s) completed ({state['completed_tasks']}), "
            f"{len(state['failed_tasks'])} step(s) failed ({state['failed_tasks']})."
        )
        fallback = (
            f"SEO cycle for {site['name']} on {state['date']}: "
            f"{len(state['completed_tasks'])} step(s) completed, {len(state['failed_tasks'])} failed."
        )

    result = get_provider(task="seo_report").generate(prompt, fast=True)
    report = result.text if result.ok else fallback
    logger.info("SEO Master Agent report compiled for %s", state["date"])
    return {"final_report": report}


# ── 25.6.4 / 33.1 LangGraph graph assembly ──


def build_graph():
    graph = StateGraph(SeoAgentState)
    graph.add_node("planning", planning_node)
    graph.add_node("technical_audit", technical_audit_node)
    graph.add_node("gsc_pull", gsc_pull_node)
    graph.add_node("ga4_pull", ga4_pull_node)
    graph.add_node("pagespeed_check", pagespeed_node)
    graph.add_node("daily_digest", digest_node)
    graph.add_node("completion_compiler", completion_compiler_node)

    graph.add_edge(START, "planning")
    graph.add_edge("planning", "technical_audit")
    graph.add_edge("technical_audit", "gsc_pull")
    graph.add_edge("gsc_pull", "ga4_pull")
    graph.add_edge("ga4_pull", "pagespeed_check")
    graph.add_edge("pagespeed_check", "daily_digest")
    graph.add_edge("daily_digest", "completion_compiler")
    graph.add_edge("completion_compiler", END)
    return graph.compile()


_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def _empty_state(site: Optional[dict] = None) -> SeoAgentState:
    return {
        "date": "",
        "active_site_ids": [],
        "daily_plan": [],
        "completed_tasks": [],
        "failed_tasks": [],
        "current_task": "",
        "final_report": "",
        "site": site,
    }


def run_full_cycle() -> SeoAgentState:
    """Module 25.6's original single-invocation skeleton test — planning
    reads the site registry, then straight to the completion compiler
    with no site selected. Kept for backward compatibility with that
    module's manual test; module 33's real automated cycle is
    run_daily_cycle_for_all_sites below, which is what the scheduler and
    the manual /jobs/run-daily-cycle endpoint actually call."""
    graph = get_compiled_graph()
    return graph.invoke(_empty_state())


# ── 33.2 Multi-site orchestration ──


def run_daily_cycle_for_all_sites() -> list:
    """The real module-33 entry point: runs the full 5-step pipeline for
    every active site, one at a time (sequential by design — a polite,
    rate-limited crawl and shared external API quotas make concurrent
    multi-site runs a real cost, not a speed win worth the complexity).
    Never raises — a bad site or a mid-cycle exception logs and moves to
    the next site rather than aborting every other site's run, same
    convention as _run_job's per-step degrade."""
    sites = database.get_active_seo_sites()
    graph = get_compiled_graph()
    results = []

    logger.info("SEO daily cycle starting for %d active site(s)", len(sites))
    for site in sites:
        site_dict = dict(site)
        try:
            final_state = graph.invoke(_empty_state(site=site_dict))
            logger.info(
                "SEO daily cycle finished for site %s: completed=%s failed=%s",
                site_dict["id"], final_state["completed_tasks"], final_state["failed_tasks"],
            )
            results.append(final_state)
        except Exception:
            logger.exception("SEO daily cycle crashed for site %s — continuing to next site", site_dict["id"])

    return results


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 33 manual test: running the real daily cycle for all active sites")
    cycle_results = run_daily_cycle_for_all_sites()
    for state in cycle_results:
        print(f"Site {state['site']['id']} ({state['site']['name']}):")
        print("  completed:", state["completed_tasks"])
        print("  failed:", state["failed_tasks"])
        print("  report:", state["final_report"])
