#!/usr/bin/env python3
"""Deterministic contract tests for aivss_finding_rationale.py.

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

from aivss_assessment_skills import score_finding  # noqa: E402
from aivss_finding_rationale import (  # noqa: E402
    OrgContext,
    build_finding_rationale_synthesis_prompt,
    draft_finding_rationale_context,
    render_finding_rationale_markdown,
)


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


_FACTOR_LEVELS = {
    "autonomy": 1.0, "tools": 1.0, "language": 1.0, "context": 1.0,
    "non_determinism": 0.5, "opacity": 1.0, "persistence": 0.5,
    "identity": 0.5, "multi_agent": 0.5, "self_mod": 0.0,
}


def _scored_finding():
    return score_finding(
        risk_key="goal_instruction",
        finding_description="prompt injection auto fund-switch",
        cvss_base=2.4,
        factor_levels=_FACTOR_LEVELS,
        threat_multiplier=0.97,
        mitigation_factor=1.0,
    )


def test_requires_a_real_scored_finding() -> None:
    try:
        draft_finding_rationale_context({"risk_key": "goal_instruction"})
        raise AssertionError("expected ValueError for missing score fields")
    except ValueError as exc:
        _assert("missing required keys" in str(exc), exc)


def test_evidence_gap_true_when_no_org_context_supplied() -> None:
    context = draft_finding_rationale_context(_scored_finding())
    _assert(context["evidence_gap"] is True, context)
    _assert(context["organization_context"] == {
        "controls_in_place": [], "evidence_reviewed": [], "known_gaps": [],
    }, context["organization_context"])


def test_evidence_gap_false_when_org_context_has_controls_or_evidence() -> None:
    with_controls = draft_finding_rationale_context(
        _scored_finding(), org_controls={"controls_in_place": ["server-side confirm gate"]}
    )
    _assert(with_controls["evidence_gap"] is False, with_controls)

    with_evidence = draft_finding_rationale_context(
        _scored_finding(), org_controls={"evidence_reviewed": ["change log sample"]}
    )
    _assert(with_evidence["evidence_gap"] is False, with_evidence)

    # only known_gaps supplied (no controls/evidence) -> still a gap
    only_gaps = draft_finding_rationale_context(
        _scored_finding(), org_controls={"known_gaps": ["no confirm gate today"]}
    )
    _assert(only_gaps["evidence_gap"] is True, only_gaps)


def test_org_context_dataclass_accepted_directly() -> None:
    org = OrgContext(controls_in_place=("a",), evidence_reviewed=(), known_gaps=("b",))
    context = draft_finding_rationale_context(_scored_finding(), org_controls=org)
    _assert(context["organization_context"]["controls_in_place"] == ["a"], context)
    _assert(context["organization_context"]["known_gaps"] == ["b"], context)
    _assert(context["evidence_gap"] is False, context)


def test_reuses_skill3_questionnaire_and_spec_citations() -> None:
    context = draft_finding_rationale_context(_scored_finding())
    _assert(context["risk_key"] == "goal_instruction", context)
    _assert(context["aivss"] == 7.6, context)
    _assert(context["severity"] == "High", context)
    _assert(context["control_questions"], "expected control questions reused from skill 3")
    _assert(context["evidence_requests"], "expected evidence requests reused from skill 3")
    _assert(context["cobit_codes"], "expected COBIT codes reused from skill 3")
    _assert(context["spec_citations"], "expected at least one spec citation")
    _assert(all("page" in c for c in context["spec_citations"]), context["spec_citations"])


def test_render_markdown_contains_all_sections() -> None:
    context = draft_finding_rationale_context(
        _scored_finding(),
        org_controls={"controls_in_place": ["x"], "known_gaps": ["y"]},
    )
    markdown = render_finding_rationale_markdown(context)
    _assert("Finding Rationale Context" in markdown, markdown[:200])
    _assert("7.6" in markdown, markdown)
    _assert("Organization context" in markdown, markdown)
    _assert("Grounding from skill 3" in markdown, markdown)
    _assert("Spec grounding" in markdown, markdown)
    _assert("Proof boundary" in markdown, markdown)
    _assert("evidence_gap: true" not in markdown, "should not flag gap when controls supplied")
    # 2026-07-28 fix — same per-citation-attribution disclaimer as
    # aivss_design_review.render_design_review_markdown, see that test's note
    _assert(
        "do not attribute those to a" in markdown,
        "expected the spec-grounding disclaimer against misattributing citations",
    )


def test_build_finding_rationale_synthesis_prompt_grounds_and_carries_question() -> None:
    context = draft_finding_rationale_context(
        _scored_finding(), org_controls={"controls_in_place": ["server-side confirm gate"]}
    )
    prompt = build_finding_rationale_synthesis_prompt(
        context, original_question="เขียน rationale ให้หน่อย"
    )
    _assert("เขียน rationale ให้หน่อย" in prompt, prompt[:200])
    _assert(context["risk_name"] in prompt, "grounded markdown must be embedded in the prompt")
    _assert(context["proof_boundary"] in prompt, "proof boundary must be embedded verbatim")
    _assert("server-side confirm gate" in prompt, "org context must survive into the prompt")


def main() -> int:
    tests = (
        test_requires_a_real_scored_finding,
        test_evidence_gap_true_when_no_org_context_supplied,
        test_evidence_gap_false_when_org_context_has_controls_or_evidence,
        test_org_context_dataclass_accepted_directly,
        test_reuses_skill3_questionnaire_and_spec_citations,
        test_render_markdown_contains_all_sections,
        test_build_finding_rationale_synthesis_prompt_grounds_and_carries_question,
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
