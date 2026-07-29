#!/usr/bin/env python3
"""Deterministic contract tests for aivss_mcp_server.py.

Calls the decorated @mcp.tool() functions directly (FastMCP keeps them
plain callables — verified during authoring) rather than spinning up an MCP
client/transport, so this stays a fast, no-pytest, self-contained runner
matching test_aivss_assessment_skills.py's convention. Confirms the tool
wrappers produce the same results as calling the underlying skill functions
directly, and that every tool is actually registered with the FastMCP
instance.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import aivss_mcp_server as srv  # noqa: E402


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


EXPECTED_TOOL_NAMES = {
    "aivss_intake_and_triage",
    "aivss_generate_questionnaire",
    "aivss_score_finding",
    "aivss_assemble_audit_deliverable",
    "aivss_classify_banking_system",
    "aivss_search_spec",
    "aivss_cite_spec_reference",
    "aivss_design_review",
    "aivss_triage_threat_alert",
    "aivss_draft_finding_rationale",
    "aivss_spec_provenance_report",
    "aivss_related_risks",
    "aivss_find_blind_spot_risks",
    "aivss_graph_export",
}


def test_all_tools_registered() -> None:
    names = {t.name for t in srv.mcp._tool_manager.list_tools()}
    _assert(names == EXPECTED_TOOL_NAMES, names)


def test_intake_and_triage_tool() -> None:
    result = srv.aivss_intake_and_triage(
        role="IT Internal Audit",
        system_name="Mobile Banking - AI Investment Advisory",
        ai_capability_summary=(
            "Chat-based robo-advisor embedded in the mobile banking app; "
            "can call a fund-switch API."
        ),
        regulatory_context=["PDPA"],
        factor_hints={"autonomy": 1.0, "tools": 1.0, "language": 1.0, "context": 1.0},
    )
    _assert(len(result["triage"]) == 10, result["triage"])
    by_key = {row["risk_key"]: row for row in result["triage"]}
    _assert(by_key["tool_misuse"]["applicability"] == "high", by_key["tool_misuse"])


def test_generate_questionnaire_tool() -> None:
    result = srv.aivss_generate_questionnaire(["goal_instruction", "tool_misuse"])
    _assert(len(result["sections"]) == 2, result["sections"])
    _assert("AIVSS Assessment Scoping Questionnaire" in result["markdown"], result["markdown"][:200])


def test_score_finding_tool_matches_worked_example() -> None:
    result = srv.aivss_score_finding(
        risk_key="goal_instruction",
        finding_description="prompt injection auto fund-switch",
        cvss_base=2.4,
        factor_levels={
            "autonomy": 1.0, "tools": 1.0, "language": 1.0, "context": 1.0,
            "non_determinism": 0.5, "opacity": 1.0, "persistence": 0.5,
            "identity": 0.5, "multi_agent": 0.5, "self_mod": 0.0,
        },
        threat_multiplier=0.97,
        mitigation_factor=1.0,
    )
    _assert(result["aivss"] == 7.6, result)
    _assert(result["severity"] == "High", result)
    _assert(isinstance(result["audit_topic_ids"], list), result["audit_topic_ids"])


def test_assemble_audit_deliverable_tool_full_pipeline() -> None:
    result = srv.aivss_assemble_audit_deliverable(
        role="IT Internal Audit",
        system_name="Mobile Banking - AI Investment Advisory",
        ai_capability_summary="Chat-based robo-advisor; can call a fund-switch API.",
        factor_hints={
            "autonomy": 1.0, "tools": 1.0, "language": 1.0, "context": 1.0,
            "non_determinism": 0.5, "opacity": 1.0, "persistence": 0.5,
            "identity": 0.5, "multi_agent": 0.5, "self_mod": 0.0,
        },
        top_n=3,
        scored_findings=[
            {
                "risk_key": "goal_instruction",
                "finding_description": "prompt injection auto fund-switch",
                "cvss_base": 2.4,
                "factor_levels": {
                    "autonomy": 1.0, "tools": 1.0, "language": 1.0, "context": 1.0,
                    "non_determinism": 0.5, "opacity": 1.0, "persistence": 0.5,
                    "identity": 0.5, "multi_agent": 0.5, "self_mod": 0.0,
                },
            }
        ],
        output_id="audit_program",
    )
    # skill 5 always lists every triaged risk; top_n only bounds questionnaire depth
    _assert(len(result["risks"]) == 10, len(result["risks"]))
    _assert(len(result["findings"]) == 1, result["findings"])
    _assert(result["findings"][0]["aivss"] == 7.6, result["findings"][0])
    _assert("AIVSS Assessment" in result["markdown"], result["markdown"][:200])
    _assert(result["markdown"] in result["narrative_prompt"], "narrative_prompt must embed the markdown")


def test_classify_banking_system_tool_match_and_none() -> None:
    match = srv.aivss_classify_banking_system("our robo-advisor investment advisory chatbot")
    _assert(match is not None and match["archetype_key"] == "robo_advisor", match)
    _assert(match["default_factor_hints"], match)

    _assert(srv.aivss_classify_banking_system("unrelated text about the weather") is None, "no match")


def test_search_spec_and_cite_spec_reference_tools() -> None:
    hits = srv.aivss_search_spec("prompt injection", limit=3)
    _assert(hits, "expected search hits")
    _assert(all("page" in h for h in hits), hits)

    citations = srv.aivss_cite_spec_reference("goal_instruction", limit=2)
    _assert(citations, "expected citations for a known risk key")
    _assert(srv.aivss_cite_spec_reference("") == [], "blank query must fail closed")


def test_design_review_tool() -> None:
    result = srv.aivss_design_review(
        role="AI Security Lead",
        system_name="New Collections Agent (planned)",
        ai_capability_summary="Autonomous agent negotiating settlement offers via chat.",
        factor_hints={"autonomy": 1.0, "tools": 1.0, "persistence": 1.0},
        top_n=3,
    )
    _assert(len(result["sections"]) == 3, result["sections"])
    for section in result["sections"]:
        _assert(section["mitigations"], section["risk_key"])
    _assert("AIVSS Design Review" in result["markdown"], result["markdown"][:200])
    _assert(result["markdown"] in result["narrative_prompt"], "narrative_prompt must embed the markdown")

    with_question = srv.aivss_design_review(
        role="AI Security Lead",
        system_name="New Collections Agent (planned)",
        ai_capability_summary="Autonomous agent negotiating settlement offers via chat.",
        factor_hints={"autonomy": 1.0, "tools": 1.0, "persistence": 1.0},
        top_n=3,
        original_question="ควรออกแบบระบบนี้อย่างไร?",
    )
    _assert("ควรออกแบบระบบนี้อย่างไร?" in with_question["narrative_prompt"], with_question["narrative_prompt"][:300])


def test_triage_threat_alert_tool_match_and_none() -> None:
    match = srv.aivss_triage_threat_alert(
        "New MCP tool poisoning technique combined with prompt injection was disclosed."
    )
    _assert(match is not None, "expected a match")
    _assert(set(match["matched_risk_keys"]) >= {"tool_misuse", "goal_instruction"}, match)

    _assert(srv.aivss_triage_threat_alert("unrelated text about the weather") is None, "no match")


def test_draft_finding_rationale_tool() -> None:
    result = srv.aivss_draft_finding_rationale(
        risk_key="goal_instruction",
        finding_description="prompt injection auto fund-switch",
        cvss_base=2.4,
        factor_levels={
            "autonomy": 1.0, "tools": 1.0, "language": 1.0, "context": 1.0,
            "non_determinism": 0.5, "opacity": 1.0, "persistence": 0.5,
            "identity": 0.5, "multi_agent": 0.5, "self_mod": 0.0,
        },
        org_controls={"controls_in_place": ["server-side confirm gate (planned)"]},
        original_question="ทำไม finding นี้ถึงมีคะแนนสูง?",
    )
    _assert(result["aivss"] == 7.6, result)
    _assert(result["evidence_gap"] is False, result)
    _assert(result["spec_citations"], "expected spec citations")
    _assert("narrative_prompt" in result, result.keys())
    _assert("ทำไม finding นี้ถึงมีคะแนนสูง?" in result["narrative_prompt"], result["narrative_prompt"][:300])

    no_org = srv.aivss_draft_finding_rationale(
        risk_key="goal_instruction",
        finding_description="x",
        cvss_base=2.4,
        factor_levels={
            "autonomy": 1.0, "tools": 1.0, "language": 1.0, "context": 1.0,
            "non_determinism": 0.5, "opacity": 1.0, "persistence": 0.5,
            "identity": 0.5, "multi_agent": 0.5, "self_mod": 0.0,
        },
    )
    _assert(no_org["evidence_gap"] is True, no_org)


def test_spec_provenance_report_tool() -> None:
    report = srv.aivss_spec_provenance_report()
    _assert(len(report["risks"]) == 10, report["risks"])
    _assert(len(report["factors"]) == 10, report["factors"])
    _assert(report["all_risks_verified"] is True, report["unverified_risk_keys"])
    _assert(report["all_factors_verified"] is True, report["unverified_factor_keys"])
    _assert(report["page_count_drift"] is False, report)


def test_related_risks_tool() -> None:
    rows = srv.aivss_related_risks("goal_instruction", limit=3)
    _assert(rows, "expected at least one related risk")
    keys = [row["risk_key"] for row in rows]
    _assert("goal_instruction" not in keys, keys)
    _assert(srv.aivss_related_risks("not_a_real_risk") == [], "unknown risk key must fail closed")


def test_find_blind_spot_risks_tool() -> None:
    rows = srv.aivss_find_blind_spot_risks(["tool_misuse", "access_control"], limit=2)
    _assert(rows, "expected at least one blind-spot candidate")
    _assert(rows[0]["risk_key"] == "supply_chain", rows)
    _assert(srv.aivss_find_blind_spot_risks([]) == [], "empty input must fail closed")


def test_graph_export_tool() -> None:
    full = srv.aivss_graph_export()
    _assert(full["nodes"] and full["relations"], full)

    scoped = srv.aivss_graph_export(["goal_instruction"])
    _assert(len(scoped["nodes"]) < len(full["nodes"]), "scoped export must be smaller")
    for node in scoped["nodes"][:3]:
        _assert(set(node.keys()) == {"entity_name", "entity_type", "label", "description"}, node)


def main() -> int:
    tests = (
        test_all_tools_registered,
        test_intake_and_triage_tool,
        test_generate_questionnaire_tool,
        test_score_finding_tool_matches_worked_example,
        test_assemble_audit_deliverable_tool_full_pipeline,
        test_classify_banking_system_tool_match_and_none,
        test_search_spec_and_cite_spec_reference_tools,
        test_design_review_tool,
        test_triage_threat_alert_tool_match_and_none,
        test_draft_finding_rationale_tool,
        test_spec_provenance_report_tool,
        test_related_risks_tool,
        test_find_blind_spot_risks_tool,
        test_graph_export_tool,
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
