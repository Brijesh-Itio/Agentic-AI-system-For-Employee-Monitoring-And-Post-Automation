"""MODULE 25 — Generic LLM provider layer for the SEO Agentic AI system.

ai.llm.factory.get_provider(task) is the one entry point every SEO
pipeline (module 26+) uses to talk to an LLM. Everything else in this
package exists to make the provider behind that call swappable — local
Ollama today, Claude/OpenAI/whatever else later — without any pipeline
code changing.
"""
