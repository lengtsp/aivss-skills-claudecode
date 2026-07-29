#!/usr/bin/env python3
"""Deterministic contract tests for aivss_assessment_skills.py.

Exercises the full 5-skill chain against a worked example: an IT Internal
Audit engagement over a mobile-banking AI investment-advisory feature.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aivss_assessment_skills import (  # noqa: E402
    AssessmentScope,
    RiskQuestionnaireSection,
    RiskTriageRow,
    assemble_audit_deliverable,
    build_audit_deliverable_synthesis_prompt,
    generate_risk_questionnaire,
    intake_assessment_scope,
    parse_finding_score_request,
    parse_scope_triage_request,
    render_deliverable_markdown,
    render_questionnaire_markdown,
    score_finding,
    triage_applicable_risks,
)
from aivss_banking_taxonomy import (  # noqa: E402
    BANKING_SYSTEM_ARCHETYPES,
    classify_banking_system,
    get_archetype,
)
from aivss_kg import FACTOR_DEFINITIONS, RISK_DEFINITIONS  # noqa: E402
from aivss_internal_audit import OUTPUT_OPTIONS  # noqa: E402


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_intake_validates_input_and_factor_hints() -> None:
    scope = intake_assessment_scope(
        role="IT Internal Audit",
        system_name="Mobile Banking - AI Investment Advisory",
        ai_capability_summary=(
            "Chat-based robo-advisor embedded in the mobile banking app; "
            "reads customer KYC/suitability profile and portfolio data; "
            "can call a fund-switch API; backed by a third-party LLM."
        ),
        regulatory_context=["SEC Thailand robo-advisor guideline", "BOT IT risk", "PDPA"],
        factor_hints={"autonomy": 1.0, "self_mod": 0},
    )
    _assert(scope.role == "IT Internal Audit", scope)
    _assert(scope.factor_hints == {"autonomy": 1.0, "self_mod": 0.0}, scope.factor_hints)
    _assert(len(scope.regulatory_context) == 3, scope.regulatory_context)

    for bad_kwargs, bad_field in (
        ({"role": "", "system_name": "x", "ai_capability_summary": "x"}, "role"),
        ({"role": "x", "system_name": "", "ai_capability_summary": "x"}, "system_name"),
        ({"role": "x", "system_name": "x", "ai_capability_summary": ""}, "ai_capability_summary"),
    ):
        try:
            intake_assessment_scope(**bad_kwargs)
            raise AssertionError(f"expected ValueError for missing {bad_field}")
        except ValueError:
            pass

    try:
        intake_assessment_scope(
            role="x", system_name="x", ai_capability_summary="x",
            factor_hints={"not_a_real_factor": 1.0},
        )
        raise AssertionError("expected ValueError for unknown factor key")
    except ValueError:
        pass

    try:
        intake_assessment_scope(
            role="x", system_name="x", ai_capability_summary="x",
            factor_hints={"autonomy": 0.3},
        )
        raise AssertionError("expected ValueError for non 0/0.5/1 factor value")
    except ValueError:
        pass


def _mobile_banking_scope() -> AssessmentScope:
    # Deliberately partial: mimics an auditor who has confirmed some
    # characteristics via document review but must still ask scoping
    # questions (skill 3) to pin down the rest.
    return intake_assessment_scope(
        role="IT Internal Audit",
        system_name="Mobile Banking - AI Investment Advisory",
        ai_capability_summary=(
            "Chat-based robo-advisor embedded in the mobile banking app; "
            "reads customer KYC/suitability profile and portfolio data; "
            "can call a fund-switch API; backed by a third-party LLM."
        ),
        regulatory_context=["SEC Thailand robo-advisor guideline", "BOT IT risk", "PDPA"],
        factor_hints={
            "autonomy": 1.0,
            "tools": 1.0,
            "language": 1.0,
            "context": 1.0,
            "persistence": 0.5,
        },
    )


def test_triage_orders_by_scoping_need_then_applicability() -> None:
    scope = _mobile_banking_scope()
    rows = triage_applicable_risks(scope)
    _assert(len(rows) == len(RISK_DEFINITIONS) == 10, len(rows))
    _assert(all(isinstance(row, RiskTriageRow) for row in rows), rows)

    by_key = {row.risk_key: row for row in rows}

    # goal_instruction's factors (language, autonomy, non_determinism,
    # context) are only partially known here (non_determinism missing) ->
    # must still be "needs_scoping".
    _assert(by_key["goal_instruction"].applicability == "needs_scoping", by_key["goal_instruction"])
    _assert("non_determinism" in by_key["goal_instruction"].unscoped_factors, by_key["goal_instruction"])

    # tool_misuse's factors (autonomy, tools, language) are all known and
    # all == 1.0 -> deterministically "high".
    _assert(by_key["tool_misuse"].applicability == "high", by_key["tool_misuse"])
    _assert(by_key["tool_misuse"].unscoped_factors == (), by_key["tool_misuse"])

    # supply_chain requires all 10 factors -> still needs scoping since
    # several factors (opacity, non_determinism, identity, multi_agent,
    # self_mod) were never provided.
    _assert(by_key["supply_chain"].applicability == "needs_scoping", by_key["supply_chain"])

    # Every row carries a COBIT/audit-topic crosswalk pulled from the
    # existing aivss_internal_audit lens, not re-authored here.
    _assert(all(row.audit_topic_ids for row in rows), [row.risk_key for row in rows if not row.audit_topic_ids])

    # needs_scoping rows must sort before fully-scoped rows.
    seen_scoped = False
    for row in rows:
        if row.applicability != "needs_scoping":
            seen_scoped = True
        elif seen_scoped:
            raise AssertionError(f"needs_scoping row {row.risk_key} sorted after a scoped row")


def test_questionnaire_reuses_audit_topics_catalog() -> None:
    sections = generate_risk_questionnaire(
        ["goal_instruction", "tool_misuse", "identity_impersonation", "goal_instruction"]
    )
    # duplicate risk key collapsed
    _assert(len(sections) == 3, [s.risk_key for s in sections])
    _assert(all(isinstance(s, RiskQuestionnaireSection) for s in sections), sections)

    by_key = {s.risk_key: s for s in sections}
    goal = by_key["goal_instruction"]
    _assert(len(goal.scoping_questions) == 4, goal.scoping_questions)  # language, autonomy, non_determinism, context
    _assert(goal.control_questions, "expected at least one control question")
    _assert(goal.evidence_requests, "expected at least one PBC/evidence request")
    _assert(goal.suggested_tests, "expected at least one suggested test")
    _assert(goal.cobit_codes, "expected at least one COBIT code")

    try:
        generate_risk_questionnaire(["not_a_real_risk"])
        raise AssertionError("expected ValueError for unknown risk key")
    except ValueError:
        pass


def test_score_finding_matches_expected_aivss_worked_example() -> None:
    # Exact factor set used in the AIVSS design writeup: autonomy, tools,
    # language, context, opacity = 1.0; non_determinism, persistence,
    # identity, multi_agent = 0.5; self_mod = 0.0 -> Factor_Sum = 7.0.
    factor_levels = {
        "autonomy": 1.0,
        "tools": 1.0,
        "language": 1.0,
        "context": 1.0,
        "non_determinism": 0.5,
        "opacity": 1.0,
        "persistence": 0.5,
        "identity": 0.5,
        "multi_agent": 0.5,
        "self_mod": 0.0,
    }
    finding_text = (
        "Prompt injection can steer the advisor into auto-submitting a "
        "portfolio shift to a higher-risk fund with no human-confirmation gate."
    )

    before = score_finding(
        risk_key="goal_instruction",
        finding_description=finding_text,
        cvss_base=2.4,
        factor_levels=factor_levels,
        threat_multiplier=0.97,
        mitigation_factor=1.00,
    )
    _assert(before["factor_sum"] == 7.0, before)
    _assert(before["aivss"] == 7.6, before)
    _assert(before["severity"] == "High", before)
    _assert(before["risk_name"] == "Agent Goal and Instruction Manipulation", before)
    _assert(before["audit_topic_ids"], "expected matched audit topics")

    after = score_finding(
        risk_key="goal_instruction",
        finding_description=finding_text,
        cvss_base=2.4,
        factor_levels=factor_levels,
        threat_multiplier=0.97,
        mitigation_factor=0.67,
    )
    _assert(after["aivss"] == 5.1, after)
    _assert(after["severity"] == "Medium", after)

    try:
        score_finding(
            risk_key="not_a_real_risk",
            finding_description="x",
            cvss_base=1.0,
            factor_levels=factor_levels,
        )
        raise AssertionError("expected ValueError for unknown risk key")
    except ValueError:
        pass


def test_parse_finding_score_request_full_and_partial() -> None:
    full_message = (
        'risk=goal_instruction finding="prompt injection auto fund-switch"\n'
        "cvss=2.4 autonomy=1 tools=1 language=1 context=1 non_determinism=0.5\n"
        "opacity=1 persistence=0.5 identity=0.5 multi_agent=0.5 self_mod=0\n"
        "thm=0.97 mitigation=1.0"
    )
    parsed = parse_finding_score_request(full_message)
    _assert(parsed is not None, "expected a parsed result for a complete message")
    _assert(parsed["risk_key"] == "goal_instruction", parsed)
    _assert(parsed["factor_sum"] == 7.0, parsed)
    _assert(parsed["aivss"] == 7.6, parsed)
    _assert(parsed["severity"] == "High", parsed)
    _assert(
        parsed["finding_description"] == "prompt injection auto fund-switch",
        parsed,
    )
    _assert(
        parsed["defaults_applied"] == {"threat_multiplier": False, "mitigation_factor": False},
        parsed,
    )

    # defaults_applied should reflect when thm/mitigation are omitted
    defaults_message = full_message.replace("thm=0.97 mitigation=1.0", "")
    parsed_defaults = parse_finding_score_request(defaults_message)
    _assert(parsed_defaults is not None, "expected a parsed result without thm/mitigation")
    _assert(parsed_defaults["threat_multiplier"] == 0.97, parsed_defaults)
    _assert(parsed_defaults["mitigation_factor"] == 1.0, parsed_defaults)
    _assert(
        parsed_defaults["defaults_applied"] == {"threat_multiplier": True, "mitigation_factor": True},
        parsed_defaults,
    )

    # missing one of the 10 factor keys -> fails closed (None), never a partial score
    missing_factor_message = full_message.replace("self_mod=0", "")
    _assert(parse_finding_score_request(missing_factor_message) is None, missing_factor_message)

    # unknown risk key -> None
    unknown_risk_message = full_message.replace("goal_instruction", "not_a_real_risk")
    _assert(parse_finding_score_request(unknown_risk_message) is None, unknown_risk_message)

    # missing cvss entirely -> None
    no_cvss_message = full_message.replace("cvss=2.4", "")
    _assert(parse_finding_score_request(no_cvss_message) is None, no_cvss_message)

    # ordinary prose mentioning "risk" and "context" must not false-positive
    prose = "what is the context and risk of this system in general"
    _assert(parse_finding_score_request(prose) is None, prose)
    _assert(parse_finding_score_request("") is None, "empty string")
    _assert(parse_finding_score_request(None) is None, "None input")


def test_parse_scope_triage_request_full_and_partial() -> None:
    full_message = (
        'role="IT Internal Audit" system="Mobile Banking - AI Investment Advisory" '
        'capability="Chat-based robo-advisor embedded in the mobile banking app; '
        'reads customer KYC/suitability profile and portfolio data; can call a '
        'fund-switch API; backed by a third-party LLM."\n'
        'regulatory="SEC Thailand robo-advisor guideline, BOT IT risk, PDPA"\n'
        "autonomy=1 tools=1 language=1 context=1 persistence=0.5"
    )
    parsed = parse_scope_triage_request(full_message)
    _assert(parsed is not None, "expected a parsed result for a complete scope message")
    _assert(parsed["role"] == "IT Internal Audit", parsed)
    _assert(parsed["system_name"] == "Mobile Banking - AI Investment Advisory", parsed)
    _assert(len(parsed["regulatory_context"]) == 3, parsed["regulatory_context"])
    _assert(
        parsed["factor_hints"]
        == {"autonomy": 1.0, "tools": 1.0, "language": 1.0, "context": 1.0, "persistence": 0.5},
        parsed["factor_hints"],
    )
    _assert(len(parsed["triage"]) == len(RISK_DEFINITIONS) == 10, parsed["triage"])

    by_key = {row["risk_key"]: row for row in parsed["triage"]}
    # Same expectations as test_triage_orders_by_scoping_need_then_applicability,
    # but exercised through the chat-text parser's plain-dict output.
    _assert(by_key["goal_instruction"]["applicability"] == "needs_scoping", by_key["goal_instruction"])
    _assert(
        "non_determinism" in by_key["goal_instruction"]["unscoped_factors"],
        by_key["goal_instruction"],
    )
    _assert(by_key["tool_misuse"]["applicability"] == "high", by_key["tool_misuse"])
    _assert(by_key["tool_misuse"]["unscoped_factors"] == [], by_key["tool_misuse"])
    _assert(by_key["supply_chain"]["applicability"] == "needs_scoping", by_key["supply_chain"])

    seen_scoped = False
    for row in parsed["triage"]:
        if row["applicability"] != "needs_scoping":
            seen_scoped = True
        elif seen_scoped:
            raise AssertionError(f"needs_scoping row {row['risk_key']} sorted after a scoped row")

    # no regulatory context / factor hints at all -> still parses; every risk
    # falls back to needs_scoping since nothing is known yet.
    minimal_message = (
        'role="IT Internal Audit" system="Mobile Banking - AI Investment Advisory" '
        'capability="Chat-based robo-advisor backed by a third-party LLM."'
    )
    minimal = parse_scope_triage_request(minimal_message)
    _assert(minimal is not None, "expected a parsed result with no factor hints")
    _assert(minimal["regulatory_context"] == [], minimal["regulatory_context"])
    _assert(minimal["factor_hints"] == {}, minimal["factor_hints"])
    _assert(
        all(row["applicability"] == "needs_scoping" for row in minimal["triage"]),
        [row["risk_key"] for row in minimal["triage"] if row["applicability"] != "needs_scoping"],
    )

    # missing role/system/capability -> fails closed (None), never a guessed scope
    missing_role_message = (
        'system="Mobile Banking - AI Investment Advisory" '
        'capability="Chat-based robo-advisor backed by a third-party LLM." autonomy=1'
    )
    _assert(parse_scope_triage_request(missing_role_message) is None, missing_role_message)

    missing_system_message = (
        'role="IT Internal Audit" '
        'capability="Chat-based robo-advisor backed by a third-party LLM." autonomy=1'
    )
    _assert(parse_scope_triage_request(missing_system_message) is None, missing_system_message)

    missing_capability_message = (
        'role="IT Internal Audit" system="Mobile Banking - AI Investment Advisory" autonomy=1'
    )
    _assert(
        parse_scope_triage_request(missing_capability_message) is None,
        missing_capability_message,
    )

    # ordinary prose mentioning "role" and "context" must not false-positive
    prose = "what role does context play in this system's risk"
    _assert(parse_scope_triage_request(prose) is None, prose)
    _assert(parse_scope_triage_request("") is None, "empty string")
    _assert(parse_scope_triage_request(None) is None, "None input")


def test_assemble_and_render_audit_program() -> None:
    scope = _mobile_banking_scope()
    triage_rows = triage_applicable_risks(scope)
    top_keys = [row.risk_key for row in triage_rows[:4]]
    sections = generate_risk_questionnaire(top_keys)

    finding = score_finding(
        risk_key="goal_instruction",
        finding_description="Prompt injection can steer auto fund-switch with no human confirmation.",
        cvss_base=2.4,
        factor_levels={
            "autonomy": 1.0, "tools": 1.0, "language": 1.0, "context": 1.0,
            "non_determinism": 0.5, "opacity": 1.0, "persistence": 0.5,
            "identity": 0.5, "multi_agent": 0.5, "self_mod": 0.0,
        },
        threat_multiplier=0.97,
        mitigation_factor=1.00,
    )

    deliverable = assemble_audit_deliverable(
        scope=scope,
        triage_rows=triage_rows,
        questionnaire_sections=sections,
        scored_findings=[finding],
        output_id="audit_program",
    )
    _assert(deliverable.output_id == "audit_program", deliverable)
    _assert(deliverable.role == "IT Internal Audit", deliverable)
    _assert(len(deliverable.risks) == 10, deliverable.risks)
    _assert(len(deliverable.findings) == 1, deliverable.findings)
    _assert("does not prove" not in deliverable.proof_boundary, deliverable.proof_boundary)

    markdown = render_deliverable_markdown(deliverable)
    _assert("AIVSS Assessment" in markdown, markdown[:200])
    _assert("Proof boundary" in markdown, markdown)
    _assert("7.6" in markdown, "expected the scored finding's AIVSS value in the rendered markdown")

    valid_ids = {row["id"] for row in OUTPUT_OPTIONS}
    for output_id in valid_ids:
        assemble_audit_deliverable(
            scope=scope,
            triage_rows=triage_rows,
            questionnaire_sections=sections,
            output_id=output_id,
        )

    try:
        assemble_audit_deliverable(
            scope=scope,
            triage_rows=triage_rows,
            questionnaire_sections=sections,
            output_id="not_a_real_output",
        )
        raise AssertionError("expected ValueError for unknown output_id")
    except ValueError:
        pass


def test_build_audit_deliverable_synthesis_prompt_grounds_and_carries_question() -> None:
    scope = _mobile_banking_scope()
    triage_rows = triage_applicable_risks(scope)
    top_keys = [row.risk_key for row in triage_rows[:3]]
    sections = generate_risk_questionnaire(top_keys)
    deliverable = assemble_audit_deliverable(
        scope=scope, triage_rows=triage_rows, questionnaire_sections=sections,
        output_id="audit_program",
    )
    prompt = build_audit_deliverable_synthesis_prompt(
        deliverable, original_question="ระบบนี้มีความเสี่ยงอะไรบ้าง?"
    )
    _assert("ระบบนี้มีความเสี่ยงอะไรบ้าง?" in prompt, prompt[:200])
    _assert(scope.system_name in prompt, "grounded markdown must be embedded in the prompt")
    _assert(deliverable.proof_boundary in prompt, "proof boundary must be embedded verbatim")
    for term in scope.regulatory_context:
        _assert(term in prompt, f"expected regulatory term {term!r} to survive into the prompt")


def test_render_questionnaire_markdown_contains_all_sections() -> None:
    sections = generate_risk_questionnaire(["goal_instruction", "tool_misuse"])
    markdown = render_questionnaire_markdown(sections)
    _assert("AIVSS Assessment Scoping Questionnaire" in markdown, markdown[:200])

    by_key = {s.risk_key: s for s in sections}
    for section in by_key.values():
        _assert(section.name in markdown, f"missing risk name {section.name!r} in rendered markdown")
        for question in section.scoping_questions:
            _assert(f"- [ ] {question}" in markdown, "expected scoping question as a checklist item")
        for code in section.cobit_codes:
            _assert(code in markdown, f"missing COBIT code {code!r} in rendered markdown")

    custom = render_questionnaire_markdown(sections, title="Custom Title")
    _assert(custom.startswith("# Custom Title"), custom[:50])


def test_banking_taxonomy_classification_and_defaults() -> None:
    from aivss_worked_examples import (
        credit_scoring_underwriting,
        fraud_detection_transaction_monitoring,
        mobile_banking_investment_advisor,
    )

    _assert(len(BANKING_SYSTEM_ARCHETYPES) == 5, BANKING_SYSTEM_ARCHETYPES)
    valid_factor_keys = {row["key"] for row in FACTOR_DEFINITIONS}
    for archetype in BANKING_SYSTEM_ARCHETYPES:
        _assert(
            set(archetype.default_factor_hints) <= valid_factor_keys,
            f"{archetype.key} has unknown factor keys",
        )
        _assert(get_archetype(archetype.key) is archetype, archetype.key)

    # classify_banking_system() must agree with the real, regression-tested
    # worked-example scenarios — not just be internally consistent.
    for deliverable, expected_key in (
        (mobile_banking_investment_advisor(), "robo_advisor"),
        (fraud_detection_transaction_monitoring(), "fraud_transaction_monitoring"),
        (credit_scoring_underwriting(), "credit_scoring_underwriting"),
    ):
        combined = f"{deliverable.system_name} {deliverable.scope_summary}"
        _assert(
            classify_banking_system(combined) == expected_key,
            (expected_key, classify_banking_system(combined), combined),
        )

    # unrelated prose -> fails closed (None), never a guessed archetype
    _assert(classify_banking_system("what is the weather today") is None, "unrelated prose")
    _assert(classify_banking_system("") is None, "empty string")
    _assert(classify_banking_system(None) is None, "None input")
    _assert(get_archetype("not_a_real_archetype") is None, "unknown archetype key")

    # full round-trip smoke test on a new (non-worked-example) archetype
    archetype = get_archetype("kyc_onboarding_chatbot")
    _assert(archetype is not None, "expected kyc_onboarding_chatbot archetype")
    scope = intake_assessment_scope(
        role="IT Internal Audit",
        system_name="Digital Onboarding - KYC Chatbot",
        ai_capability_summary=archetype.description,
        regulatory_context=archetype.default_regulatory_context,
        factor_hints=archetype.default_factor_hints,
    )
    triage_rows = triage_applicable_risks(scope)
    _assert(len(triage_rows) == 10, triage_rows)
    top_keys = [row.risk_key for row in triage_rows[:3]]
    sections = generate_risk_questionnaire(top_keys)
    markdown = render_questionnaire_markdown(sections)
    _assert(markdown.strip(), "expected non-empty rendered questionnaire")
    _assert("Scoping questions" in markdown, markdown[:200])


def test_all_ten_risks_have_summaries_and_matrix_entries() -> None:
    from aivss_assessment_skills import RISK_SUMMARIES
    from aivss_kg import RISK_FACTOR_MATRIX

    for risk in RISK_DEFINITIONS:
        key = risk["key"]
        _assert(key in RISK_SUMMARIES and RISK_SUMMARIES[key], f"missing summary for {key}")
        _assert(key in RISK_FACTOR_MATRIX, f"missing RISK_FACTOR_MATRIX entry for {key}")
        for factor_key in RISK_FACTOR_MATRIX[key]:
            _assert(
                factor_key in {row["key"] for row in FACTOR_DEFINITIONS},
                f"{key} references unknown factor {factor_key}",
            )


def test_mobile_banking_worked_example_module() -> None:
    from aivss_worked_examples import mobile_banking_investment_advisor

    deliverable = mobile_banking_investment_advisor()
    high = {r["risk_key"] for r in deliverable.risks if r["applicability"] == "high"}
    _assert(
        high
        == {
            "tool_misuse",
            "cascading_failures",
            "orchestration",
            "identity_impersonation",
            "memory_context",
            "critical_systems",
            "supply_chain",
            "goal_instruction",
        },
        high,
    )
    finding = deliverable.findings[0]
    _assert(finding["risk_key"] == "goal_instruction", finding)
    _assert(finding["aivss"] == 7.6, finding)
    _assert(finding["severity"] == "High", finding)


def test_fraud_detection_worked_example() -> None:
    from aivss_worked_examples import fraud_detection_transaction_monitoring

    deliverable = fraud_detection_transaction_monitoring()
    high = {r["risk_key"] for r in deliverable.risks if r["applicability"] == "high"}
    _assert(high == {"cascading_failures", "critical_systems", "memory_context"}, high)
    _assert(len(deliverable.findings) == 1, deliverable.findings)
    finding = deliverable.findings[0]
    _assert(finding["risk_key"] == "memory_context", finding)
    _assert(finding["factor_sum"] == 6.0, finding)
    _assert(finding["aivss"] == 4.5, finding)
    _assert(finding["severity"] == "Medium", finding)


def test_credit_scoring_worked_example() -> None:
    from aivss_worked_examples import credit_scoring_underwriting

    deliverable = credit_scoring_underwriting()
    high = {r["risk_key"] for r in deliverable.risks if r["applicability"] == "high"}
    _assert(high == {"goal_instruction", "identity_impersonation", "memory_context"}, high)
    _assert(len(deliverable.findings) == 1, deliverable.findings)
    finding = deliverable.findings[0]
    _assert(finding["risk_key"] == "goal_instruction", finding)
    _assert(finding["factor_sum"] == 6.0, finding)
    _assert(finding["aivss"] == 7.1, finding)
    _assert(finding["severity"] == "High", finding)


def main() -> int:
    tests = (
        test_intake_validates_input_and_factor_hints,
        test_triage_orders_by_scoping_need_then_applicability,
        test_questionnaire_reuses_audit_topics_catalog,
        test_score_finding_matches_expected_aivss_worked_example,
        test_parse_finding_score_request_full_and_partial,
        test_parse_scope_triage_request_full_and_partial,
        test_assemble_and_render_audit_program,
        test_build_audit_deliverable_synthesis_prompt_grounds_and_carries_question,
        test_render_questionnaire_markdown_contains_all_sections,
        test_banking_taxonomy_classification_and_defaults,
        test_all_ten_risks_have_summaries_and_matrix_entries,
        test_mobile_banking_worked_example_module,
        test_fraud_detection_worked_example,
        test_credit_scoring_worked_example,
    )
    results: list[dict[str, object]] = []
    for test in tests:
        try:
            test()
            results.append({"test": test.__name__, "passed": True})
        except Exception as exc:
            results.append(
                {
                    "test": test.__name__,
                    "passed": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
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
