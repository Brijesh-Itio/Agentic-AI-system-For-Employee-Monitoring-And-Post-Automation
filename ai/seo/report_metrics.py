"""
The metrics an AI report (daily digest or weekly/monthly/custom roll-up)
can be told to cover. Single source of truth: the routes validate against
it, the digest generators build their prompts from it, and the frontend's
picker is fed from GET /api/seo/digest/metrics rather than keeping its own
copy that could drift.

None (rather than a list) always means "everything" — the default every
existing caller, including the daily automation and the scheduled
roll-ups, keeps using, so adding a metric here never changes what they do.
"""
from typing import Optional

REPORT_METRICS: dict[str, dict[str, str]] = {
    "issues": {
        "label": "Technical SEO issues",
        "hint": "Open and critical issues found by the audit",
    },
    "performance": {
        "label": "PageSpeed score",
        "hint": "Latest mobile performance score",
    },
    "search_queries": {
        "label": "Top search queries",
        "hint": "The queries bringing the most clicks (Search Console)",
    },
    "traffic_pages": {
        "label": "Top traffic pages",
        "hint": "The pages with the most sessions (Analytics)",
    },
    "rankings": {
        "label": "Ranking changes",
        "hint": "Keywords that fell out of the top 10 and the biggest movers",
    },
    "meta_opportunities": {
        "label": "Meta rewrite opportunities",
        "hint": "Pages with high impressions but low CTR",
    },
    "job_failures": {
        "label": "Automation job failures",
        "hint": "Recent failed pipeline steps",
    },
}


def validate_metrics(metrics: Optional[list[str]]) -> Optional[list[str]]:
    """Returns the de-duplicated list in the caller's order, or None for
    "everything". ValueError (the route turns it into a 400) for an empty
    list or an unknown key — a report about nothing isn't a report."""
    if metrics is None:
        return None
    if not metrics:
        raise ValueError("Pick at least one metric for the report.")
    unknown = [m for m in metrics if m not in REPORT_METRICS]
    if unknown:
        raise ValueError(f"Unknown report metric(s): {', '.join(unknown)}")
    return list(dict.fromkeys(metrics))


def metric_labels(metrics: Optional[list[str]]) -> list[str]:
    return [REPORT_METRICS[m]["label"] for m in (metrics or REPORT_METRICS)]
