#!/usr/bin/env python
"""Evaluate retrieval routing against JSON scenario fixtures (no LLM)."""

import argparse
import json
import os
import sys
from pathlib import Path

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from services.graphrag.retrieval_profile import resolve_retrieval_profile
from services.langchain import streaming

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "tests" / "evaluation" / "scenarios"


def _top_source(chunks) -> str:
    for chunk in chunks:
        source = (chunk.source or "").strip()
        if source:
            return source
    return ""


def run_case(client_id: str, case: dict) -> tuple[bool, str]:
    question = case["question"]
    profile = resolve_retrieval_profile(client_id, question)
    chunks = streaming._retrieve_chunks(client_id, question, profile)

    if case.get("expect_domain_in"):
        if profile.domain not in case["expect_domain_in"]:
            return False, f"domain={profile.domain} not in {case['expect_domain_in']}"

    top = _top_source(chunks).lower()
    expect_suffix = case.get("expect_top_source_suffix")
    if expect_suffix and not top.endswith(expect_suffix.lower()):
        return False, f"top source {top!r} does not end with {expect_suffix}"

    forbid = case.get("forbid_source_suffix")
    if forbid and top.endswith(forbid.lower()):
        return False, f"top source {top!r} forbidden suffix {forbid}"

    return True, f"domain={profile.domain} top={top or 'n/a'}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run mixed-client retrieval scenarios")
    parser.add_argument("client_id", help="Neo4j client UUID")
    parser.add_argument(
        "--scenario",
        default="mixed_client_narrative_pdf.json",
        help="Scenario file under tests/evaluation/scenarios/",
    )
    args = parser.parse_args()

    path = SCENARIOS_DIR / args.scenario
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    passed = 0
    for i, case in enumerate(cases, 1):
        ok, detail = run_case(args.client_id, case)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {i}: {detail}")
        print(f"       Q: {case['question'][:80]}")
        if ok:
            passed += 1
    print(f"\n{passed}/{len(cases)} passed")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
