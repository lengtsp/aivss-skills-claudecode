"""Organization-context finding-rationale grounding, per
`SKILLS_ROADMAP.md` idea #2 ("เหตุผลประกอบการประเมินในหน่วยงาน").

Not a skill that *writes* a finding's rationale — producing defensible prose
that weighs organization-specific evidence needs judgment and belongs to the
calling agent/human, not a deterministic function. This module *assembles*
everything that agent needs to write one without guessing:

- The already-computed `aivss_assessment_skills.score_finding()` result
  (never re-derives the score — just carries it through).
- The matching risk's `control_questions` / `evidence_requests` /
  `suggested_tests` from `aivss_assessment_skills.generate_risk_questionnaire`
  (skill 3) — reused, not re-authored.
- A live spec citation via `aivss_spec_search.cite_spec_reference()`.
- Whatever the caller already knows about the organization's actual
  controls (`org_controls`) — passed through as-is, never inferred or
  matched against the evidence_requests by keyword (that would be a
  judgment call this module explicitly leaves to the caller).

`evidence_gap` is the one thing this module *does* compute: True whenever
the caller supplied no organization evidence at all, so a downstream
narrator can't accidentally claim a control exists just because the
question catalog mentions one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aivss_assessment_skills import (
    RiskQuestionnaireSection,
    generate_risk_questionnaire,
)
from aivss_spec_search import cite_spec_reference
from aivss_synthesis_prompt import build_synthesis_prompt

FINDING_RATIONALE_SCHEMA = "rag.aivss-finding-rationale-context.v1"

_REQUIRED_FINDING_KEYS = (
    "risk_key",
    "risk_name",
    "aivss",
    "severity",
    "factor_sum",
    "cvss_base",
)

RATIONALE_PROOF_BOUNDARY_NOTE = (
    "ชุดข้อมูลนี้เป็นการรวบรวมข้อเท็จจริงที่คำนวณ/ค้นแล้ว (score, คำถามควบคุมจาก skill 3, "
    "spec citation) ไม่ใช่ rationale สำเร็จรูป และไม่ยืนยันว่า control ในหน่วยงานมีอยู่จริง "
    "หรือมีประสิทธิผล — ผู้เขียน rationale (agent/ผู้ตรวจสอบ) ต้องอ้างอิง organization_context "
    "ที่ได้รับมาจริงเท่านั้น ห้ามสรุปว่ามี control เพียงเพราะคำถามใน evidence_requests ถูกถามถึง"
)


@dataclass(frozen=True)
class OrgContext:
    controls_in_place: tuple[str, ...] = ()
    evidence_reviewed: tuple[str, ...] = ()
    known_gaps: tuple[str, ...] = ()


def _coerce_org_context(org_controls: dict[str, Any] | OrgContext | None) -> OrgContext:
    if org_controls is None:
        return OrgContext()
    if isinstance(org_controls, OrgContext):
        return org_controls
    return OrgContext(
        controls_in_place=tuple(
            str(item).strip()
            for item in org_controls.get("controls_in_place", ())
            if str(item).strip()
        ),
        evidence_reviewed=tuple(
            str(item).strip()
            for item in org_controls.get("evidence_reviewed", ())
            if str(item).strip()
        ),
        known_gaps=tuple(
            str(item).strip() for item in org_controls.get("known_gaps", ()) if str(item).strip()
        ),
    )


def draft_finding_rationale_context(
    scored_finding: dict[str, Any],
    *,
    org_controls: dict[str, Any] | OrgContext | None = None,
    questionnaire_section: RiskQuestionnaireSection | None = None,
    spec_citations_limit: int = 2,
) -> dict[str, Any]:
    """Assemble the grounding packet for one already-scored finding.

    `scored_finding` must be an `aivss_assessment_skills.score_finding()`
    result dict (or equivalent) — raises ValueError if it's missing any of
    the required score fields, since there is nothing sensible to assemble
    around an unscored/malformed finding. `questionnaire_section` is
    optional; if omitted, one is fetched via `generate_risk_questionnaire`
    (skill 3) for the finding's risk_key so the caller doesn't have to
    already have it on hand. `org_controls` is optional and passed through
    verbatim (as an `OrgContext`) — an empty/missing org_controls is valid
    input, it just sets `evidence_gap=True` in the result rather than
    raising, since "we haven't gathered evidence yet" is a legitimate state
    for an assessment in progress.
    """

    missing = [key for key in _REQUIRED_FINDING_KEYS if key not in scored_finding]
    if missing:
        raise ValueError(f"scored_finding missing required keys: {missing}")

    risk_key = str(scored_finding["risk_key"])

    section = questionnaire_section
    if section is None:
        sections = generate_risk_questionnaire([risk_key])
        section = sections[0] if sections else None

    org = _coerce_org_context(org_controls)
    evidence_gap = not (org.controls_in_place or org.evidence_reviewed)

    citations = cite_spec_reference(risk_key, limit=spec_citations_limit)

    return {
        "schema": FINDING_RATIONALE_SCHEMA,
        "risk_key": risk_key,
        "risk_name": scored_finding["risk_name"],
        "finding_description": scored_finding.get("finding_description", ""),
        "aivss": scored_finding["aivss"],
        "severity": scored_finding["severity"],
        "factor_sum": scored_finding["factor_sum"],
        "cvss_base": scored_finding["cvss_base"],
        "control_questions": list(section.control_questions) if section else [],
        "evidence_requests": list(section.evidence_requests) if section else [],
        "suggested_tests": list(section.suggested_tests) if section else [],
        "cobit_codes": list(section.cobit_codes) if section else [],
        "organization_context": {
            "controls_in_place": list(org.controls_in_place),
            "evidence_reviewed": list(org.evidence_reviewed),
            "known_gaps": list(org.known_gaps),
        },
        "evidence_gap": evidence_gap,
        "spec_citations": citations,
        "proof_boundary": RATIONALE_PROOF_BOUNDARY_NOTE,
    }


def render_finding_rationale_markdown(context: dict[str, Any]) -> str:
    lines: list[str] = [
        f"# Finding Rationale Context — {context['risk_name']} ({context['risk_key']})",
        f"AIVSS {context['aivss']} ({context['severity']}) | Factor_Sum {context['factor_sum']} "
        f"| CVSS_Base {context['cvss_base']}",
        "",
    ]
    if context.get("finding_description"):
        lines.append(f"**Finding:** {context['finding_description']}")
        lines.append("")

    org = context.get("organization_context") or {}
    lines.append("## Organization context")
    if context.get("evidence_gap"):
        lines.append(
            "- **evidence_gap: true** — no organization controls/evidence supplied yet"
        )
    for label, key in (
        ("Controls in place", "controls_in_place"),
        ("Evidence reviewed", "evidence_reviewed"),
        ("Known gaps", "known_gaps"),
    ):
        items = org.get(key) or []
        if items:
            lines.append(f"- {label}:")
            for item in items:
                lines.append(f"  - {item}")
    lines.append("")

    lines.append("## Grounding from skill 3 (aivss_assessment_skills)")
    for label, key in (
        ("Control focus", "control_questions"),
        ("PBC / Evidence requests", "evidence_requests"),
        ("Suggested tests", "suggested_tests"),
    ):
        items = context.get(key) or []
        if items:
            lines.append(f"### {label}")
            for item in items:
                lines.append(f"- {item}")
    if context.get("cobit_codes"):
        lines.append(f"COBIT: {', '.join(context['cobit_codes'])}")
    lines.append("")

    if context.get("spec_citations"):
        lines.append(
            "## Spec grounding for the risk itself (AIVSS v0.8, page + snippet) "
            "— describes the attack pattern, NOT the organization_context or the "
            "skill-3 control/evidence items above; do not attribute those to a "
            "specific page unless the snippet itself demonstrates it"
        )
        for citation in context["spec_citations"]:
            lines.append(
                f"- p.{citation['page']} ({citation['confidence']}): {citation['snippet']}"
            )
        lines.append("")

    lines.append("## Proof boundary")
    lines.append(context["proof_boundary"])
    return "\n".join(lines)


def build_finding_rationale_synthesis_prompt(
    context: dict[str, Any],
    *,
    original_question: str = "",
    answer_language: str = "Thai",
) -> str:
    """Turn this finding-rationale context into an LLM-ready prompt for a
    narrative rationale, instead of handing the caller raw markdown. This is
    arguably the clearest fit for the synthesis-prompt pattern in this
    folder: the module's own docstring already says its job is to assemble
    grounding for "an agent/human [to] write one defensibly" — this function
    is that "write one" step made concrete instead of left implicit. See
    `aivss_synthesis_prompt.build_synthesis_prompt` for the shared template
    and the live-test finding that motivated adding it (README.md "Live
    quality test", 2026-07-28)."""

    return build_synthesis_prompt(
        grounded_markdown=render_finding_rationale_markdown(context),
        original_question=original_question,
        answer_language=answer_language,
        audience_hint="an Internal Audit / GRC stakeholder who needs a defensible written rationale",
    )


__all__ = [
    "FINDING_RATIONALE_SCHEMA",
    "RATIONALE_PROOF_BOUNDARY_NOTE",
    "OrgContext",
    "draft_finding_rationale_context",
    "render_finding_rationale_markdown",
    "build_finding_rationale_synthesis_prompt",
]
