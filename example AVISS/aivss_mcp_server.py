"""MCP tool server exposing the AIVSS assessment skill set to any
MCP-capable client (Claude, GPT, Qwen via llama-server, ...), per
`SKILLS_ROADMAP.md` idea #5.

Mirrors the `excel-mcp-server` (negokaz) pattern already documented in the
project root `CLAUDE.md`: a deterministic tool server any MCP-compatible
agent can call directly, opt-in via `mcpServers` in `.claude/settings.json`,
instead of only being reachable through `routes_chat.py`'s regex-parsing
chat injectors. This module does not touch `.claude/settings.json` itself —
see README.md "AIVSS MCP server (2026-07-28)" for the opt-in registration
snippet; registering it is a separate, explicit user action.

Design: every `@mcp.tool()` function is a thin wrapper around a plain
`_tool_*` business-logic function so tests can call the logic directly
without spinning up an MCP client/transport (FastMCP keeps decorated
functions directly callable — verified during authoring). No tool holds
state across calls, matching the rest of this folder's "stateless,
single-message" convention: a caller that wants the 5-skill chain's
intermediate objects (AssessmentScope, RiskTriageRow, ...) re-supplies them
as plain JSON on every call rather than the server remembering a session.

Every tool here wraps only what already exists elsewhere in this folder
(`aivss_assessment_skills.py`, `aivss_banking_taxonomy.py`,
`aivss_spec_search.py`, `aivss_design_review.py`, `aivss_threat_intel.py`,
`aivss_finding_rationale.py`, `aivss_spec_provenance.py`,
`aivss_knowledge_graph.py`) — no new scoring/classification logic lives in
this file.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from aivss_assessment_skills import (  # noqa: E402
    assemble_audit_deliverable,
    build_audit_deliverable_synthesis_prompt,
    generate_risk_questionnaire,
    intake_assessment_scope,
    render_deliverable_markdown,
    render_questionnaire_markdown,
    score_finding,
    triage_applicable_risks,
)
from aivss_banking_taxonomy import classify_banking_system, get_archetype  # noqa: E402
from aivss_design_review import (  # noqa: E402
    assemble_design_review,
    build_design_review_synthesis_prompt,
    generate_design_recommendations,
    render_design_review_markdown,
)
from aivss_spec_search import cite_spec_reference, search_spec  # noqa: E402
from aivss_threat_intel import triage_threat_alert  # noqa: E402
from aivss_finding_rationale import (  # noqa: E402
    build_finding_rationale_synthesis_prompt,
    draft_finding_rationale_context,
)
from aivss_spec_provenance import catalog_provenance_report  # noqa: E402
from aivss_knowledge_graph import (  # noqa: E402
    export_kg_shape,
    find_blind_spot_risks,
    related_risks,
)

MCP_SERVER_SCHEMA = "rag.aivss-mcp-server.v1"

mcp = FastMCP("aivss-assessment-skills")


# ===================== business logic (plain, directly testable) =====================


def _triage_rows_to_dicts(triage_rows) -> list[dict[str, Any]]:
    return [
        {
            "risk_key": row.risk_key,
            "name": row.name,
            "summary": row.summary,
            "applicability": row.applicability,
            "amplifying_factors": list(row.amplifying_factors),
            "known_factor_levels": dict(row.known_factor_levels),
            "unscoped_factors": list(row.unscoped_factors),
            "audit_topic_ids": list(row.audit_topic_ids),
            "cobit_codes": list(row.cobit_codes),
        }
        for row in triage_rows
    ]


def _tool_intake_and_triage(
    *,
    role: str,
    system_name: str,
    ai_capability_summary: str,
    regulatory_context: list[str] | None = None,
    factor_hints: dict[str, float] | None = None,
) -> dict[str, Any]:
    scope = intake_assessment_scope(
        role=role,
        system_name=system_name,
        ai_capability_summary=ai_capability_summary,
        regulatory_context=regulatory_context or (),
        factor_hints=factor_hints or {},
    )
    triage_rows = triage_applicable_risks(scope)
    return {
        "role": scope.role,
        "system_name": scope.system_name,
        "ai_capability_summary": scope.ai_capability_summary,
        "regulatory_context": list(scope.regulatory_context),
        "factor_hints": dict(scope.factor_hints),
        "triage": _triage_rows_to_dicts(triage_rows),
    }


def _tool_generate_questionnaire(risk_keys: list[str]) -> dict[str, Any]:
    sections = generate_risk_questionnaire(risk_keys)
    return {
        "sections": [
            {
                "risk_key": s.risk_key,
                "name": s.name,
                "summary": s.summary,
                "scoping_questions": list(s.scoping_questions),
                "control_questions": list(s.control_questions),
                "evidence_requests": list(s.evidence_requests),
                "suggested_tests": list(s.suggested_tests),
                "cobit_codes": list(s.cobit_codes),
                "audit_topic_ids": list(s.audit_topic_ids),
            }
            for s in sections
        ],
        "markdown": render_questionnaire_markdown(sections),
    }


def _tool_score_finding(
    *,
    risk_key: str,
    finding_description: str,
    cvss_base: float,
    factor_levels: dict[str, float],
    threat_multiplier: float = 0.97,
    mitigation_factor: float = 1.0,
) -> dict[str, Any]:
    result = score_finding(
        risk_key=risk_key,
        finding_description=finding_description,
        cvss_base=cvss_base,
        factor_levels=factor_levels,
        threat_multiplier=threat_multiplier,
        mitigation_factor=mitigation_factor,
    )
    result["audit_topic_ids"] = list(result["audit_topic_ids"])
    return result


def _tool_assemble_audit_deliverable(
    *,
    role: str,
    system_name: str,
    ai_capability_summary: str,
    regulatory_context: list[str] | None = None,
    factor_hints: dict[str, float] | None = None,
    top_n: int | None = None,
    scored_findings: list[dict[str, Any]] | None = None,
    output_id: str = "audit_program",
    original_question: str = "",
    answer_language: str = "Thai",
) -> dict[str, Any]:
    scope = intake_assessment_scope(
        role=role,
        system_name=system_name,
        ai_capability_summary=ai_capability_summary,
        regulatory_context=regulatory_context or (),
        factor_hints=factor_hints or {},
    )
    triage_rows = triage_applicable_risks(scope)
    selected_rows = triage_rows[: max(0, int(top_n))] if top_n is not None else triage_rows
    sections = generate_risk_questionnaire([row.risk_key for row in selected_rows])

    findings: list[dict[str, Any]] = []
    for raw in scored_findings or []:
        findings.append(
            score_finding(
                risk_key=raw["risk_key"],
                finding_description=raw.get("finding_description", ""),
                cvss_base=float(raw["cvss_base"]),
                factor_levels=raw["factor_levels"],
                threat_multiplier=float(raw.get("threat_multiplier", 0.97)),
                mitigation_factor=float(raw.get("mitigation_factor", 1.0)),
            )
        )

    deliverable = assemble_audit_deliverable(
        scope=scope,
        triage_rows=triage_rows,
        questionnaire_sections=sections,
        scored_findings=findings,
        output_id=output_id,
    )
    return {
        "schema": deliverable.schema,
        "output_id": deliverable.output_id,
        "role": deliverable.role,
        "system_name": deliverable.system_name,
        "objective": deliverable.objective,
        "scope_summary": deliverable.scope_summary,
        "regulatory_context": list(deliverable.regulatory_context),
        "risks": list(deliverable.risks),
        "findings": list(deliverable.findings),
        "proof_boundary": deliverable.proof_boundary,
        "markdown": render_deliverable_markdown(deliverable),
        "narrative_prompt": build_audit_deliverable_synthesis_prompt(
            deliverable, original_question=original_question, answer_language=answer_language
        ),
    }


def _tool_classify_banking_system(text: str) -> dict[str, Any] | None:
    key = classify_banking_system(text)
    if key is None:
        return None
    archetype = get_archetype(key)
    if archetype is None:
        return None
    return {
        "archetype_key": archetype.key,
        "label": archetype.label,
        "description": archetype.description,
        "default_factor_hints": dict(archetype.default_factor_hints),
        "default_regulatory_context": list(archetype.default_regulatory_context),
    }


def _tool_design_review(
    *,
    role: str,
    system_name: str,
    ai_capability_summary: str,
    regulatory_context: list[str] | None = None,
    factor_hints: dict[str, float] | None = None,
    top_n: int | None = None,
    original_question: str = "",
    answer_language: str = "Thai",
) -> dict[str, Any]:
    scope = intake_assessment_scope(
        role=role,
        system_name=system_name,
        ai_capability_summary=ai_capability_summary,
        regulatory_context=regulatory_context or (),
        factor_hints=factor_hints or {},
    )
    triage_rows = triage_applicable_risks(scope)
    sections = generate_design_recommendations(triage_rows, top_n=top_n)
    deliverable = assemble_design_review(scope=scope, sections=sections)
    return {
        "schema": deliverable.schema,
        "role": deliverable.role,
        "system_name": deliverable.system_name,
        "objective": deliverable.objective,
        "scope_summary": deliverable.scope_summary,
        "regulatory_context": list(deliverable.regulatory_context),
        "sections": list(deliverable.sections),
        "proof_boundary": deliverable.proof_boundary,
        "markdown": render_design_review_markdown(deliverable),
        "narrative_prompt": build_design_review_synthesis_prompt(
            deliverable, original_question=original_question, answer_language=answer_language
        ),
    }


def _tool_draft_finding_rationale(
    *,
    risk_key: str,
    finding_description: str,
    cvss_base: float,
    factor_levels: dict[str, float],
    threat_multiplier: float = 0.97,
    mitigation_factor: float = 1.0,
    org_controls: dict[str, list[str]] | None = None,
    spec_citations_limit: int = 2,
    original_question: str = "",
    answer_language: str = "Thai",
) -> dict[str, Any]:
    scored = score_finding(
        risk_key=risk_key,
        finding_description=finding_description,
        cvss_base=cvss_base,
        factor_levels=factor_levels,
        threat_multiplier=threat_multiplier,
        mitigation_factor=mitigation_factor,
    )
    context = draft_finding_rationale_context(
        scored,
        org_controls=org_controls,
        spec_citations_limit=spec_citations_limit,
    )
    context["narrative_prompt"] = build_finding_rationale_synthesis_prompt(
        context, original_question=original_question, answer_language=answer_language
    )
    return context


def _tool_spec_provenance_report(citations_per_entry: int = 2) -> dict[str, Any]:
    return catalog_provenance_report(citations_per_entry=citations_per_entry)


# ===================== MCP tool registration (thin wrappers) =====================


@mcp.tool()
def aivss_intake_and_triage(
    role: str,
    system_name: str,
    ai_capability_summary: str,
    regulatory_context: list[str] | None = None,
    factor_hints: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Scope an AI-embedded system and triage the 10 AIVSS core risks against it (skills 1+2)."""

    return _tool_intake_and_triage(
        role=role,
        system_name=system_name,
        ai_capability_summary=ai_capability_summary,
        regulatory_context=regulatory_context,
        factor_hints=factor_hints,
    )


@mcp.tool()
def aivss_generate_questionnaire(risk_keys: list[str]) -> dict[str, Any]:
    """Generate a fillable scoping/control questionnaire for the given AIVSS risk keys (skill 3)."""

    return _tool_generate_questionnaire(risk_keys)


@mcp.tool()
def aivss_score_finding(
    risk_key: str,
    finding_description: str,
    cvss_base: float,
    factor_levels: dict[str, float],
    threat_multiplier: float = 0.97,
    mitigation_factor: float = 1.0,
) -> dict[str, Any]:
    """Score one confirmed finding against a specific AIVSS risk (skill 4, wraps aivss_kg.calculate_aivss)."""

    return _tool_score_finding(
        risk_key=risk_key,
        finding_description=finding_description,
        cvss_base=cvss_base,
        factor_levels=factor_levels,
        threat_multiplier=threat_multiplier,
        mitigation_factor=mitigation_factor,
    )


@mcp.tool()
def aivss_assemble_audit_deliverable(
    role: str,
    system_name: str,
    ai_capability_summary: str,
    regulatory_context: list[str] | None = None,
    factor_hints: dict[str, float] | None = None,
    top_n: int | None = None,
    scored_findings: list[dict[str, Any]] | None = None,
    output_id: str = "audit_program",
    original_question: str = "",
    answer_language: str = "Thai",
) -> dict[str, Any]:
    """Run the full intake->triage->questionnaire->assemble chain, render an audit deliverable (skill 5), and include a ready-to-use LLM synthesis prompt (narrative_prompt) grounded only in this deliverable's facts."""

    return _tool_assemble_audit_deliverable(
        role=role,
        system_name=system_name,
        ai_capability_summary=ai_capability_summary,
        regulatory_context=regulatory_context,
        factor_hints=factor_hints,
        top_n=top_n,
        scored_findings=scored_findings,
        output_id=output_id,
        original_question=original_question,
        answer_language=answer_language,
    )


@mcp.tool()
def aivss_classify_banking_system(text: str) -> dict[str, Any] | None:
    """Classify free text against the 5 curated banking-system AI archetypes, or null if no match."""

    return _tool_classify_banking_system(text)


@mcp.tool()
def aivss_search_spec(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Deterministic keyword search over the 98 OCR'd AIVSS v0.8 source pages."""

    return search_spec(query, limit=limit)


@mcp.tool()
def aivss_cite_spec_reference(key_or_query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Cite AIVSS v0.8 spec pages for a risk key, factor key, or freeform topic."""

    return cite_spec_reference(key_or_query, limit=limit)


@mcp.tool()
def aivss_design_review(
    role: str,
    system_name: str,
    ai_capability_summary: str,
    regulatory_context: list[str] | None = None,
    factor_hints: dict[str, float] | None = None,
    top_n: int | None = None,
    original_question: str = "",
    answer_language: str = "Thai",
) -> dict[str, Any]:
    """Proactive design-time review: risk-by-risk design mitigations + spec citations for a system being designed, plus a ready-to-use LLM synthesis prompt (narrative_prompt) so a caller doesn't have to hand raw markdown to the end user."""

    return _tool_design_review(
        role=role,
        system_name=system_name,
        ai_capability_summary=ai_capability_summary,
        regulatory_context=regulatory_context,
        factor_hints=factor_hints,
        top_n=top_n,
        original_question=original_question,
        answer_language=answer_language,
    )


@mcp.tool()
def aivss_triage_threat_alert(alert_text: str, limit: int = 3) -> dict[str, Any] | None:
    """Map a threat-intel/news alert to the AIVSS risks it plausibly concerns, or null if no match."""

    return triage_threat_alert(alert_text, limit=limit)


@mcp.tool()
def aivss_draft_finding_rationale(
    risk_key: str,
    finding_description: str,
    cvss_base: float,
    factor_levels: dict[str, float],
    threat_multiplier: float = 0.97,
    mitigation_factor: float = 1.0,
    org_controls: dict[str, list[str]] | None = None,
    spec_citations_limit: int = 2,
    original_question: str = "",
    answer_language: str = "Thai",
) -> dict[str, Any]:
    """Score a finding then assemble organization-context rationale grounding for it (skill 4 + skill 3 + spec citations + caller-supplied org evidence), plus a ready-to-use LLM synthesis prompt (narrative_prompt)."""

    return _tool_draft_finding_rationale(
        risk_key=risk_key,
        finding_description=finding_description,
        cvss_base=cvss_base,
        factor_levels=factor_levels,
        threat_multiplier=threat_multiplier,
        mitigation_factor=mitigation_factor,
        org_controls=org_controls,
        spec_citations_limit=spec_citations_limit,
        original_question=original_question,
        answer_language=answer_language,
    )


@mcp.tool()
def aivss_spec_provenance_report(citations_per_entry: int = 2) -> dict[str, Any]:
    """Verify every AIVSS risk/factor catalog entry against the OCR'd spec pages and report drift/verification gaps."""

    return _tool_spec_provenance_report(citations_per_entry=citations_per_entry)


@mcp.tool()
def aivss_related_risks(risk_key: str, limit: int = 5) -> list[dict[str, Any]]:
    """Find other AIVSS risks structurally connected to risk_key via shared amplifying factors and/or shared audit topics, ranked by connection weight."""

    return related_risks(risk_key, limit=limit)


@mcp.tool()
def aivss_find_blind_spot_risks(
    triaged_risk_keys: list[str], limit: int = 3
) -> list[dict[str, Any]]:
    """Given risk keys already surfaced by a triage/design review, find OTHER risks strongly connected to that set (via shared factors/topics) that might be a blind spot worth a second look."""

    return find_blind_spot_risks(triaged_risk_keys, limit=limit)


@mcp.tool()
def aivss_graph_export(risk_keys: list[str] | None = None) -> dict[str, Any]:
    """Export the AIVSS taxonomy graph (or a one-hop subgraph scoped to the given risk keys) as nodes/relations, in a shape compatible with the main app's real Knowledge Graph tables."""

    return export_kg_shape(risk_keys)


if __name__ == "__main__":
    mcp.run()


__all__ = [
    "MCP_SERVER_SCHEMA",
    "mcp",
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
]
