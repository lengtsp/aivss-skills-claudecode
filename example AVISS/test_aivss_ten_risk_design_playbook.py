#!/usr/bin/env python3
"""Deterministic contract tests for aivss_ten_risk_design_playbook.py.

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

from aivss_kg import FACTOR_DEFINITIONS, RISK_DEFINITIONS  # noqa: E402
from aivss_ten_risk_design_playbook import (  # noqa: E402
    RISK_USE_CASES,
    build_design_review,
    get_use_case,
    render_use_case_markdown,
    target_risk_applicability,
)

# supply_chain is the one risk keyed on all 10 amplifying factors (see
# RISK_FACTOR_MATRIX) — a realistic, non-maxed-out factor profile for it
# structurally averages below the "high" (>=0.7) bar even though the risk is
# still real and worth flagging. Every other risk's own matrix is narrower
# (3-4 factors), so a use case whose factor_hints target those specific
# factors reliably clears "high". See the module's supply_chain
# reasoning_th for the full explanation.
_EXPECTED_MIN_APPLICABILITY = {"supply_chain": "medium"}


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_all_ten_risks_have_a_use_case() -> None:
    expected_keys = {row["key"] for row in RISK_DEFINITIONS}
    actual_keys = {uc.risk_key for uc in RISK_USE_CASES}
    _assert(actual_keys == expected_keys, (actual_keys, expected_keys))
    _assert(len(RISK_USE_CASES) == 10, len(RISK_USE_CASES))


def test_every_use_case_has_required_fields() -> None:
    valid_factor_keys = {row["key"] for row in FACTOR_DEFINITIONS}
    for uc in RISK_USE_CASES:
        _assert(uc.role.strip(), uc.risk_key)
        _assert(uc.system_name.strip(), uc.risk_key)
        _assert(uc.ai_capability_summary.strip(), uc.risk_key)
        _assert(uc.regulatory_context, f"{uc.risk_key} has no regulatory_context")
        _assert(uc.reasoning_th.strip(), f"{uc.risk_key} has no reasoning_th (วิธีคิด)")
        _assert(uc.original_question.strip(), uc.risk_key)
        _assert(set(uc.factor_hints.keys()) == valid_factor_keys, (uc.risk_key, uc.factor_hints.keys()))
        for value in uc.factor_hints.values():
            _assert(value in (0.0, 0.5, 1.0), (uc.risk_key, value))


def test_target_risk_applicability_matches_design_intent() -> None:
    # For 9 of 10 risks, the use case's factor_hints are designed so the
    # target risk itself triages as "high" — verified here, not assumed.
    # supply_chain is the documented exception (see module note above).
    weak: list[str] = []
    for uc in RISK_USE_CASES:
        applicability = target_risk_applicability(uc)
        expected = _EXPECTED_MIN_APPLICABILITY.get(uc.risk_key, "high")
        if applicability != expected:
            weak.append(f"{uc.risk_key}: expected {expected!r}, got {applicability!r}")
    _assert(not weak, "\n".join(weak))


def test_build_design_review_produces_grounded_sections() -> None:
    for uc in RISK_USE_CASES:
        deliverable = build_design_review(uc, top_n=3)
        _assert(len(deliverable.sections) == 3, (uc.risk_key, len(deliverable.sections)))
        target_section = next(
            (s for s in deliverable.sections if s["risk_key"] == uc.risk_key), None
        )
        # every non-supply_chain use case's own target risk must be
        # prominent enough to land in its own top-3 design sections
        if uc.risk_key != "supply_chain":
            _assert(target_section is not None, f"{uc.risk_key} not in its own top-3 sections")
        if target_section is not None:
            _assert(target_section["mitigations"], uc.risk_key)
            _assert(target_section["factor_design_guidance"], uc.risk_key)


def test_render_use_case_markdown_includes_reasoning_and_synthesis_prompt() -> None:
    uc = get_use_case("goal_instruction")
    _assert(uc is not None, "expected goal_instruction use case")
    deliverable = build_design_review(uc, top_n=3)
    markdown = render_use_case_markdown(uc, deliverable)
    _assert("วิธีคิด" in markdown, markdown[:200])
    _assert(uc.reasoning_th in markdown, "reasoning_th must appear verbatim")
    _assert(uc.system_name in markdown, markdown[:200])
    _assert("LLM synthesis prompt" in markdown, markdown)
    _assert(uc.original_question in markdown, "original_question must flow into the synthesis prompt")


def test_get_use_case_fails_closed_on_unknown_key() -> None:
    _assert(get_use_case("not_a_real_risk") is None, "unknown risk key must return None")


def main() -> int:
    tests = (
        test_all_ten_risks_have_a_use_case,
        test_every_use_case_has_required_fields,
        test_target_risk_applicability_matches_design_intent,
        test_build_design_review_produces_grounded_sections,
        test_render_use_case_markdown_includes_reasoning_and_synthesis_prompt,
        test_get_use_case_fails_closed_on_unknown_key,
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
