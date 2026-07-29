#!/usr/bin/env python3
"""Deterministic contract tests for aivss_synthesis_prompt.py.

Same no-pytest, self-contained-runner convention as
test_aivss_assessment_skills.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aivss_synthesis_prompt import build_synthesis_prompt  # noqa: E402


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_includes_grounded_markdown_verbatim() -> None:
    grounded = "# Some Deliverable\n\nfact one\nfact two"
    prompt = build_synthesis_prompt(grounded_markdown=grounded)
    _assert(grounded in prompt, "grounded markdown must appear verbatim in the prompt")


def test_original_question_included_when_given_and_omitted_when_blank() -> None:
    with_question = build_synthesis_prompt(grounded_markdown="x", original_question="ควรทำอย่างไร?")
    _assert("ควรทำอย่างไร?" in with_question, with_question)
    _assert("Original question from the user" in with_question, with_question)

    without_question = build_synthesis_prompt(grounded_markdown="x", original_question="")
    _assert("Original question from the user" not in without_question, without_question)


def test_answer_language_and_audience_hint_reflected() -> None:
    prompt = build_synthesis_prompt(
        grounded_markdown="x", answer_language="English", audience_hint="a regulator"
    )
    _assert("write the final answer in English" in prompt, prompt)
    _assert("a regulator" in prompt, prompt)


def test_instructs_no_fact_invention_and_preserves_proof_boundary() -> None:
    prompt = build_synthesis_prompt(grounded_markdown="x")
    _assert("do not invent" in prompt.lower(), prompt)
    _assert("proof-boundary" in prompt.lower(), prompt)


def test_instructs_against_per_mitigation_citation_attribution() -> None:
    # 2026-07-28 fix: a live validation run showed a model correctly declined
    # to attribute page citations to individual mitigations on its own
    # judgment; this instruction makes that explicit so it isn't left to
    # every future model to reason out the same way.
    prompt = build_synthesis_prompt(grounded_markdown="x")
    _assert("not any individual mitigation" in prompt, prompt)
    _assert("unless that exact page's snippet" in prompt, prompt)


def main() -> int:
    tests = (
        test_includes_grounded_markdown_verbatim,
        test_original_question_included_when_given_and_omitted_when_blank,
        test_answer_language_and_audience_hint_reflected,
        test_instructs_no_fact_invention_and_preserves_proof_boundary,
        test_instructs_against_per_mitigation_citation_attribution,
    )
    results: list[dict[str, object]] = []
    for test in tests:
        try:
            test()
            results.append({"test": test.__name__, "passed": True})
        except Exception as exc:
            results.append(
                {"test": test.__name__, "passed": False, "error": f"{type(exc).__name__}: {exc}"}
            )
    payload = {
        "passed": all(bool(row["passed"]) for row in results),
        "passed_count": sum(1 for row in results if row["passed"]),
        "test_count": len(results),
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
