#!/usr/bin/env python3
"""Deterministic contract tests for aivss_design_review.py.

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

from aivss_assessment_skills import (  # noqa: E402
    intake_assessment_scope,
    triage_applicable_risks,
    RiskTriageRow,
)
from aivss_design_review import (  # noqa: E402
    DESIGN_MITIGATIONS,
    DesignRiskSection,
    assemble_design_review,
    build_design_review_synthesis_prompt,
    generate_design_recommendations,
    parse_design_review_request,
    render_design_review_markdown,
)
from aivss_kg import FACTOR_DEFINITIONS, RISK_DEFINITIONS, RISK_FACTOR_MATRIX  # noqa: E402


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _full_scope():
    return intake_assessment_scope(
        role="AI Security Lead",
        system_name="New Collections Agent (planned)",
        ai_capability_summary=(
            "Autonomous agent that will negotiate settlement offers via chat "
            "and can commit a payment-plan change without human review."
        ),
        regulatory_context=["BOT debt collection guideline", "PDPA"],
        factor_hints={
            "autonomy": 1.0, "tools": 1.0, "language": 1.0, "context": 1.0,
            "non_determinism": 0.5, "opacity": 1.0, "persistence": 1.0,
            "identity": 0.5, "multi_agent": 0.0, "self_mod": 0.0,
        },
    )


def test_design_mitigations_cover_all_ten_risks_and_valid_factors() -> None:
    risk_keys = {r["key"] for r in RISK_DEFINITIONS}
    _assert(set(DESIGN_MITIGATIONS.keys()) == risk_keys, DESIGN_MITIGATIONS.keys())
    for key, mitigations in DESIGN_MITIGATIONS.items():
        _assert(mitigations, f"{key} has no mitigations")
        _assert(all(isinstance(m, str) and m.strip() for m in mitigations), key)


def test_generate_design_recommendations_shape_and_top_n() -> None:
    scope = _full_scope()
    triage_rows = triage_applicable_risks(scope)
    _assert(len(triage_rows) == 10, len(triage_rows))

    sections = generate_design_recommendations(triage_rows, top_n=3)
    _assert(len(sections) == 3, len(sections))
    _assert(all(isinstance(s, DesignRiskSection) for s in sections), sections)

    for section in sections:
        _assert(section.mitigations == DESIGN_MITIGATIONS[section.risk_key], section.risk_key)
        expected_factor_count = len(RISK_FACTOR_MATRIX.get(section.risk_key, ()))
        _assert(
            len(section.factor_design_guidance) == expected_factor_count,
            (section.risk_key, section.factor_design_guidance),
        )
        _assert(isinstance(section.spec_citations, tuple), section.spec_citations)

    all_sections = generate_design_recommendations(triage_rows)
    _assert(len(all_sections) == 10, len(all_sections))


def test_generate_design_recommendations_skips_unknown_risk_key() -> None:
    fake_row = RiskTriageRow(
        risk_key="not_a_real_risk",
        name="Not A Real Risk",
        summary="",
        amplifying_factors=(),
        known_factor_levels={},
        unscoped_factors=(),
        applicability="high",
        audit_topic_ids=(),
        cobit_codes=(),
    )
    sections = generate_design_recommendations([fake_row])
    _assert(sections == [], "unknown risk key must be skipped defensively, not raise")


def test_assemble_and_render_design_review() -> None:
    scope = _full_scope()
    triage_rows = triage_applicable_risks(scope)
    sections = generate_design_recommendations(triage_rows, top_n=4)
    deliverable = assemble_design_review(scope=scope, sections=sections)

    _assert(deliverable.role == "AI Security Lead", deliverable.role)
    _assert(deliverable.system_name == scope.system_name, deliverable.system_name)
    _assert(len(deliverable.sections) == 4, deliverable.sections)
    _assert("does not prove" not in deliverable.proof_boundary, deliverable.proof_boundary)

    markdown = render_design_review_markdown(deliverable)
    _assert("AIVSS Design Review" in markdown, markdown[:200])
    _assert(scope.system_name in markdown, markdown[:200])
    _assert("Proof boundary" in markdown, markdown)
    _assert("Recommended design mitigations" in markdown, markdown)
    # citation label must disclaim per-mitigation attribution (2026-07-28 fix,
    # found during the live quality test's validation run — the responding
    # model correctly declined to attribute page citations to individual
    # mitigations on its own; this label makes that explicit instead of
    # relying on every future model to reason it out the same way)
    _assert("NOT a per-mitigation citation" in markdown, markdown)


def test_build_design_review_synthesis_prompt_grounds_and_carries_question() -> None:
    scope = _full_scope()
    triage_rows = triage_applicable_risks(scope)
    sections = generate_design_recommendations(triage_rows, top_n=2)
    deliverable = assemble_design_review(scope=scope, sections=sections)

    prompt = build_design_review_synthesis_prompt(
        deliverable, original_question="ควรออกแบบระบบนี้อย่างไร?"
    )
    _assert("ควรออกแบบระบบนี้อย่างไร?" in prompt, prompt[:200])
    _assert(scope.system_name in prompt, "grounded markdown must be embedded in the prompt")
    _assert(deliverable.proof_boundary in prompt, "proof boundary must be embedded verbatim")
    # regulatory context terms must survive into the prompt (this is the exact
    # gap found in the 2026-07-28 live quality test: raw mitigations never
    # mention "BOT debt collection guideline" on their own, but the grounded
    # markdown embedded in the prompt carries it in the header, and the
    # prompt's own instructions tell the LLM to connect the two)
    for term in scope.regulatory_context:
        _assert(term in prompt, f"expected regulatory term {term!r} to survive into the prompt")


def test_parse_design_review_request_full_and_missing() -> None:
    full_message = (
        'role="AI Security Lead" system="New Collections Agent (planned)" '
        'design="Autonomous agent that will negotiate settlement offers via '
        'chat and can commit a payment-plan change without human review."\n'
        'regulatory="BOT debt collection guideline, PDPA"\n'
        "autonomy=1 tools=1 persistence=1"
    )
    parsed = parse_design_review_request(full_message)
    _assert(parsed is not None, "expected a parsed result for a complete design-review message")
    _assert(parsed["role"] == "AI Security Lead", parsed["role"])
    _assert(parsed["system_name"] == "New Collections Agent (planned)", parsed["system_name"])
    _assert(len(parsed["regulatory_context"]) == 2, parsed["regulatory_context"])
    _assert(len(parsed["sections"]) == 10, len(parsed["sections"]))
    for section in parsed["sections"]:
        _assert(section["mitigations"], section["risk_key"])

    missing_role = full_message.replace('role="AI Security Lead" ', "")
    _assert(parse_design_review_request(missing_role) is None, "missing role must fail closed")

    _assert(parse_design_review_request("") is None, "empty string must fail closed")
    _assert(parse_design_review_request(None) is None, "None input must fail closed")  # type: ignore[arg-type]

    prose = "what design and role does this system have"
    _assert(parse_design_review_request(prose) is None, prose)


def test_all_factor_keys_referenced_are_valid() -> None:
    valid_factor_keys = {row["key"] for row in FACTOR_DEFINITIONS}
    for risk_key, factors in RISK_FACTOR_MATRIX.items():
        for factor_key in factors:
            _assert(factor_key in valid_factor_keys, (risk_key, factor_key))


def main() -> int:
    tests = (
        test_design_mitigations_cover_all_ten_risks_and_valid_factors,
        test_generate_design_recommendations_shape_and_top_n,
        test_generate_design_recommendations_skips_unknown_risk_key,
        test_assemble_and_render_design_review,
        test_build_design_review_synthesis_prompt_grounds_and_carries_question,
        test_parse_design_review_request_full_and_missing,
        test_all_factor_keys_referenced_are_valid,
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
