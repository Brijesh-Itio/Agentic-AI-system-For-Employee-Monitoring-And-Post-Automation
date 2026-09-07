"""MODULE 26 — SEO Agentic AI: CMS integration and free-tier data pulls.

Lives under automation/ (not ai/) for the same reason automation/linkedin
and automation/email do: this package's job is calling real external
services (a CMS's REST API, Google's free SEO-adjacent APIs) and handling
their failures — automation, not model inference. ai/seo_master_agent.py
(module 25.6) is what will eventually schedule and orchestrate calls into
this package as real pipeline nodes.
"""
