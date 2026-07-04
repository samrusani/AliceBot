"""LongMemEval harness for Alice.

Scores Alice's real capture + retrieval pipeline on LongMemEval (Wu et al.,
ICLR 2025): each question's haystack sessions are ingested into an isolated
SQLite store through ``alicebot_api.vnext_capture``, answered from a context
pack compiled by ``alicebot_api.vnext_retrieval``, and judged with the
benchmark's official LLM-judge prompts.

Entry point: ``python scripts/run_longmemeval.py --help`` (repo root).
Design notes and env-var contract: ``docs/plans/longmemeval.md``.
"""
