"""Proactive, design-time AIVSS/AIVSS review skills — a 1st/2nd-line
counterpart to `aivss_assessment_skills.py`'s 3rd-line (Internal Audit) chain.

`aivss_assessment_skills.py` answers "what IS this already-built system's
risk level" for an independent re-assessment. This module answers a
different, earlier question for a System Owner / AI Security Lead / Agent
Developer designing a system that does not exist yet (or is being changed):
"what should we build so each AIVSS factor lands low, and what design
controls does the spec's documented attack surface for this risk call for?"

Reuses rather than duplicates:
- `aivss_kg.py`: RISK_DEFINITIONS, FACTOR_DEFINITIONS, RISK_FACTOR_MATRIX.
- `aivss_assessment_skills.py`: AssessmentScope, intake_assessment_scope,
  RiskTriageRow, triage_applicable_risks, RISK_SUMMARIES — scope intake and
  risk triage are identical regardless of which role/purpose is downstream,
  so this module calls them rather than re-implementing.
- `aivss_spec_search.py`: cite_spec_reference() grounds each risk's
  DESIGN_MITIGATIONS entries with an actual OCR'd spec page, on demand
  (search is dynamic — no hand-transcribed quotes baked into this module).

Important honesty note about DESIGN_MITIGATIONS: the AIVSS v0.8 spec's Part
1 risk sections (verified by reading pages 8-44 of the OCR'd text during
authoring, 2026-07-28) contain DESCRIPTION + "KEY RISKS" (attack-surface
manifestations) + diagram + "EXAMPLE ATTACK SCENARIOS" — there is no
dedicated "Prevention and Mitigation Strategies" subsection per risk in this
version (Section 3.4.1's "Mitigation Factor" is about *scoring* mitigation
strength, not a controls catalog). DESIGN_MITIGATIONS below is therefore
Codex-authored practical design guidance that responds directly to the
specific KEY RISKS manifestations documented for each risk (same
"paraphrase, not verbatim source text" convention already used for
RISK_SUMMARIES in aivss_assessment_skills.py) — not a transcription of a
spec mitigations list that does not yet exist in v0.8. Treat it as a
starting checklist for an architect, not an authoritative/complete control
catalog. (See `aivss_spec_provenance.py` for confirmed version/publication-
date provenance — v0.8 is a released publication, not a draft, verified
2026-07-28 against the official OWASP AIVSS site.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from aivss_kg import FACTOR_DEFINITIONS, RISK_DEFINITIONS

from aivss_assessment_skills import (
    RISK_SUMMARIES,
    AssessmentScope,
    RiskTriageRow,
    intake_assessment_scope,
    triage_applicable_risks,
)
from aivss_spec_search import cite_spec_reference
from aivss_synthesis_prompt import build_synthesis_prompt

DESIGN_REVIEW_SCHEMA = "rag.aivss-design-review-skills.v1"

_FACTOR_BY_KEY: dict[str, dict[str, Any]] = {row["key"]: row for row in FACTOR_DEFINITIONS}
_RISK_BY_KEY: dict[str, dict[str, Any]] = {row["key"]: row for row in RISK_DEFINITIONS}

DESIGN_REVIEW_PROOF_BOUNDARY_NOTE = (
    "การประเมินนี้เป็นข้อเสนอแนะเชิงออกแบบ (Codex-curated design guidance) "
    "อ้างอิงจากรูปแบบการโจมตี (KEY RISKS) ที่มีการบันทึกไว้ใน AIVSS v0.8 เท่านั้น "
    "ไม่ใช่ control ที่ผ่านการตรวจสอบ ทดสอบ หรือยืนยันประสิทธิผลแล้ว — ทีมออกแบบต้อง "
    "implement, test, และ threat-model แต่ละมาตรการเองก่อนถือว่าความเสี่ยงลดลงจริง "
    "และห้ามใช้ผลลัพธ์นี้แทนการตรวจสอบโดย AI Security Lead / Internal Audit"
)

# Codex-authored design-time countermeasures, one tuple per AIVSS core risk.
# Each entry responds to a specific documented KEY RISKS manifestation for
# that risk (verified against the OCR'd spec pages during authoring — see
# module docstring) rather than being generic OWASP boilerplate.
DESIGN_MITIGATIONS: dict[str, tuple[str, ...]] = {
    "tool_misuse": (
        "รักษา authoritative tool/registry inventory เดียว ป้องกัน tool squatting/impersonation "
        "และ deceptive registration",
        "ตรวจสอบ/sanitize tool metadata (description, schema) ก่อนส่งให้ agent ตีความ "
        "ป้องกัน covert-instruction injection ผ่าน metadata",
        "รัน tool execution ใน sandbox/secure enclave ที่แยกจาก core agent process",
        "มี reliable kill switch / emergency termination ที่ agent เองสั่งปิดไม่ได้",
        "log และ DLP-inspect ทุก tool call พร้อม runtime escalation control สำหรับ high-impact tool",
    ),
    "access_control": (
        "ออกแบบ least-privilege + time-boxed role ต่องาน ป้องกัน temporal permission drift และ "
        "orphaned account persistence",
        "ใช้ cryptographic role attestation (signed token) แทนการให้ agent อ้างสิทธิ์ด้วยคำสั่งข้อความ "
        "ป้องกัน forged role assertion",
        "ตรวจสิทธิ์ซ้ำ (re-authorize) ทุกครั้งที่ agent หนึ่งขอให้อีก agent กระทำการแทน "
        "ป้องกัน confused-deputy / multi-agent permission mismatch",
        "แยก credential/token store ต่อ agent พร้อม rotation ป้องกัน credential/token mismanagement",
        "ปิด session/role อัตโนมัติเมื่อ task จบ ป้องกัน cross-context privilege bleed ระหว่าง environment",
    ),
    "cascading_failures": (
        "ใส่ circuit breaker / blast-radius containment ระหว่าง agent แต่ละตัว ไม่ให้ compromise "
        "หนึ่งจุดลามทั้งเครือข่าย",
        "ตรวจสอบความน่าเชื่อถือของข้อมูลที่ agent อื่นรายงานก่อนนำไปตัดสินใจ (cross-validation) "
        "ป้องกัน data poisoning ที่ทำให้เกิด cascading decision ผิดพลาด",
        "จำกัด implicit trust ระหว่างระบบที่เชื่อมต่อกัน (SaaS-to-SaaS, cross-system) ด้วย explicit "
        "authorization ทุกจุดเชื่อมต่อ",
        "ตรวจสอบความสอดคล้อง (consistency check) ก่อนส่งต่อผลลัพธ์ agent หนึ่งเป็น input ให้ agent อื่น "
        "ป้องกัน hallucination propagation",
    ),
    "orchestration": (
        "เข้ารหัส + ยืนยันตัวตนทุก inter-agent channel พร้อม message-integrity check "
        "ป้องกัน communication interception/injection",
        "ควบคุม integrity ของ shared memory/RAG/knowledge base ที่หลาย agent ใช้ร่วมกัน "
        "ป้องกัน shared knowledge poisoning",
        "ผูก session/message กับ nonce หรือ timestamp ที่ตรวจ replay ได้ ป้องกัน session fixation/replay",
        "ตรวจสอบ capability/schema ของ agent ใหม่ก่อนขึ้นทะเบียนใน orchestrator registry "
        "ป้องกัน capability drift / rogue autonomy",
    ),
    "identity_impersonation": (
        "ให้แต่ละ agent มี cryptographic identity เฉพาะตัว ห้ามใช้ shared service account/API key ร่วมกัน",
        "ตรวจสอบและยืนยัน agent card/capability declaration ก่อนเชื่อถือ ป้องกัน misleading agent card",
        "ควบคุม provenance/consent สำหรับการ clone เสียง/หน้า/ลายมือ (voice, face, writing style) "
        "ป้องกัน unauthorized cloning",
        "เสริม human-verification channel (เช่น callback ผ่านช่องทางที่ยืนยันแล้ว) เพื่อลดผลจาก "
        "deepfake-based human impersonation",
    ),
    "memory_context": (
        "แยก memory store ต่อ tenant/ต่อ user อย่างเข้มงวด ป้องกัน cross-session/cross-user "
        "memory contamination",
        "กำหนด retention/deletion policy ที่ purge residual memory หลังหมดอายุการใช้งาน "
        "ป้องกัน residual memory exploitation",
        "ตรวจสอบ integrity ของ context/memory ก่อนใช้งาน (checksum/signature) ป้องกัน context poisoning",
        "ติดตาม drift ของพฤติกรรม agent เทียบ baseline เพื่อจับ context drift exploit แต่เนิ่น ๆ",
    ),
    "critical_systems": (
        "บังคับ human-in-the-loop gate สำหรับ action ที่ irreversible หรือกระทบ critical system",
        "แบ่ง network segmentation ระหว่าง agent กับ critical infrastructure ป้องกัน SSRF/direct access",
        "จำกัดสิทธิ์ deployment-bot ใน CI/CD pipeline เฉพาะ scope ที่จำเป็น ป้องกัน pipeline tampering",
        "ต้องมี validation + rollback path ก่อน apply การเปลี่ยนแปลงบน production จริง",
    ),
    "supply_chain": (
        "เก็บ signed provenance/SBOM ของ model และ dependency ทุกตัว ป้องกัน model/registry tampering",
        "ปิด write access ที่ไม่จำเป็นบน model registry/artifact store ป้องกัน unauthorized model swap",
        "ตรวจสอบ (vet) MCP server/marketplace app ของบุคคลที่สามก่อนติดตั้ง ป้องกัน malicious dependency",
        "pin เวอร์ชัน dependency ที่ผ่านการ review แล้ว ไม่ auto-update โดยไม่มี change control",
    ),
    "untraceability": (
        "ใช้ centralized, tamper-evident logging พร้อม correlation ID ตลอด transaction เดียว "
        "ข้าม cloud/on-prem/SaaS",
        "ผูกทุก action กลับไปยัง accountable identity ต้นทาง (human หรือ agent) ป้องกัน "
        "loss of chain-of-action",
        "ป้องกัน log tampering/poisoning ด้วย write-once storage หรือ external SIEM ที่ agent เข้าถึงไม่ได้",
        "ตรวจสอบ integrity ของ explainability artifact (SHAP/LIME) แยกจาก inference pipeline หลัก",
    ),
    "goal_instruction": (
        "กรอง input/output เพื่อจับ instruction ที่ฝังมาใน content ภายนอก (indirect injection) "
        "ก่อนถึง agent",
        "แยก instruction source: content ที่ดึงมาจากภายนอก (RAG, email, website) ต้องไม่ถูกตีความเป็น "
        "คำสั่งระดับเดียวกับ system/developer instruction",
        "บังคับ human-confirmation gate สำหรับ action ที่มีผลกระทบสูง (fund transfer, account reset) "
        "แม้ agent จะ \"เชื่อ\" ว่าถูกสั่งให้ทำ",
        "จำกัด loop/recursion depth และ resource quota ต่อ task ป้องกัน resource exhaustion "
        "via goal looping",
    ),
}

_DESIGN_MITIGATION_SPEC_QUERY: dict[str, str] = {
    "tool_misuse": "tool squatting metadata manipulation kill switch",
    "access_control": "permission escalation role inheritance confused deputy",
    "cascading_failures": "cross-system exploitation lateral movement hallucination propagation",
    "orchestration": "inter-agent communication shared knowledge poisoning session fixation",
    "identity_impersonation": "agent impersonation shared identity pools cloning",
    "memory_context": "cross-session data leakage residual memory context drift",
    "critical_systems": "physical system manipulation IoT direct critical system access",
    "supply_chain": "development chain attack dependency exploitation MCP server",
    "untraceability": "log tampering chain-of-action explainability artifact poisoning",
    "goal_instruction": "prompt injection indirect instruction injection goal hijacking",
}


@dataclass(frozen=True)
class DesignRiskSection:
    risk_key: str
    name: str
    summary: str
    applicability: str
    amplifying_factors: tuple[str, ...]
    factor_design_guidance: tuple[str, ...]
    mitigations: tuple[str, ...]
    spec_citations: tuple[dict[str, Any], ...]


def generate_design_recommendations(
    triage_rows: Iterable[RiskTriageRow],
    *,
    top_n: int | None = None,
    citations_per_risk: int = 2,
) -> list[DesignRiskSection]:
    """Build one design-review section per triaged risk.

    Unlike `aivss_assessment_skills.generate_risk_questionnaire` (asks "what
    IS the current level, show evidence"), this asks "what SHOULD the design
    do about this risk" — factor_design_guidance restates each amplifying
    factor's own definition (from aivss_kg.FACTOR_DEFINITIONS — not
    re-authored) as a design target, and mitigations pulls from
    DESIGN_MITIGATIONS. spec_citations grounds the risk with real OCR'd spec
    pages via aivss_spec_search.cite_spec_reference — dynamic search, not a
    hand-pinned quote, so it stays correct if the source pages are re-OCR'd.

    top_n limits to the first N rows in triage_rows' existing order (the
    caller already ranked them — e.g. by triage_applicable_risks); None means
    every row. Unknown risk keys are skipped defensively rather than raising,
    since triage_rows should already only contain the 10 valid keys.
    """

    rows = list(triage_rows)
    if top_n is not None:
        rows = rows[: max(0, int(top_n))]

    sections: list[DesignRiskSection] = []
    for row in rows:
        key = row.risk_key
        if key not in _RISK_BY_KEY:
            continue
        factor_guidance = tuple(
            f"{_FACTOR_BY_KEY[f]['name']}: {_FACTOR_BY_KEY[f]['description']}"
            for f in row.amplifying_factors
            if f in _FACTOR_BY_KEY
        )
        query = _DESIGN_MITIGATION_SPEC_QUERY.get(key, row.name)
        citations = tuple(cite_spec_reference(query, limit=citations_per_risk))
        sections.append(
            DesignRiskSection(
                risk_key=key,
                name=row.name,
                summary=RISK_SUMMARIES.get(key, row.summary),
                applicability=row.applicability,
                amplifying_factors=row.amplifying_factors,
                factor_design_guidance=factor_guidance,
                mitigations=DESIGN_MITIGATIONS.get(key, ()),
                spec_citations=citations,
            )
        )
    return sections


@dataclass(frozen=True)
class DesignReviewDeliverable:
    schema: str
    role: str
    system_name: str
    objective: str
    scope_summary: str
    regulatory_context: tuple[str, ...]
    sections: tuple[dict[str, Any], ...]
    proof_boundary: str


def assemble_design_review(
    *,
    scope: AssessmentScope,
    sections: Iterable[DesignRiskSection],
) -> DesignReviewDeliverable:
    """Assemble scope + per-risk design sections into one design-review
    deliverable. No output_id catalog like assemble_audit_deliverable — a
    design review is always the same shape (risk-by-risk recommendations),
    unlike an audit engagement which can target 5 different report formats."""

    return DesignReviewDeliverable(
        schema=DESIGN_REVIEW_SCHEMA,
        role=scope.role,
        system_name=scope.system_name,
        objective=(
            f"ทบทวนการออกแบบ '{scope.system_name}' เทียบกับ AIVSS core risks ก่อน/ระหว่างพัฒนา "
            f"ในมุมมองของ {scope.role} (proactive design-time review)"
        ),
        scope_summary=scope.ai_capability_summary,
        regulatory_context=scope.regulatory_context,
        sections=tuple(
            {
                "risk_key": section.risk_key,
                "name": section.name,
                "summary": section.summary,
                "applicability": section.applicability,
                "amplifying_factors": list(section.amplifying_factors),
                "factor_design_guidance": list(section.factor_design_guidance),
                "mitigations": list(section.mitigations),
                "spec_citations": list(section.spec_citations),
            }
            for section in sections
        ),
        proof_boundary=DESIGN_REVIEW_PROOF_BOUNDARY_NOTE,
    )


def render_design_review_markdown(deliverable: DesignReviewDeliverable) -> str:
    lines: list[str] = [
        f"# AIVSS Design Review — {deliverable.system_name}",
        f"role: {deliverable.role} | schema: {deliverable.schema}",
        "",
        f"**Objective:** {deliverable.objective}",
        f"**Scope:** {deliverable.scope_summary}",
    ]
    if deliverable.regulatory_context:
        lines.append(f"**Regulatory context:** {', '.join(deliverable.regulatory_context)}")
    lines.append("")
    lines.append("## Risk-by-risk design recommendations")
    for section in deliverable.sections:
        lines.append(f"### {section['name']} ({section['risk_key']}) — {section['applicability']}")
        if section["summary"]:
            lines.append(section["summary"])
        if section["factor_design_guidance"]:
            lines.append("")
            lines.append("Design targets for amplifying factors:")
            for guidance in section["factor_design_guidance"]:
                lines.append(f"- {guidance}")
        if section["mitigations"]:
            lines.append("")
            lines.append("Recommended design mitigations:")
            for mitigation in section["mitigations"]:
                lines.append(f"- {mitigation}")
        if section["spec_citations"]:
            lines.append("")
            lines.append(
                "Spec grounding for this risk's description above (AIVSS v0.8, "
                "page + snippet) — describes the attack pattern, NOT a per-mitigation "
                "citation; do not attribute an individual mitigation to a specific page "
                "unless the snippet itself demonstrates it:"
            )
            for citation in section["spec_citations"]:
                lines.append(
                    f"- p.{citation['page']} ({citation['confidence']}): {citation['snippet']}"
                )
        lines.append("")

    lines.append("## Proof boundary")
    lines.append(deliverable.proof_boundary)
    return "\n".join(lines)


def build_design_review_synthesis_prompt(
    deliverable: DesignReviewDeliverable,
    *,
    original_question: str = "",
    answer_language: str = "Thai",
) -> str:
    """Turn this design review into an LLM-ready prompt for a narrative
    answer, instead of handing the caller raw markdown. See
    `aivss_synthesis_prompt.build_synthesis_prompt` docstring for why this
    exists — found missing during a live quality test (README.md "Live
    quality test", 2026-07-28)."""

    return build_synthesis_prompt(
        grounded_markdown=render_design_review_markdown(deliverable),
        original_question=original_question,
        answer_language=answer_language,
        audience_hint="a business/design audience evaluating a system that is being designed or changed",
    )


# Chat-text parser, same regex convention as
# aivss_assessment_skills.parse_scope_triage_request (quoted-string capture
# for free-text fields, optional per-factor "key=0/0.5/1" tokens). Runs the
# full intake -> triage -> generate_design_recommendations -> assemble chain
# and returns a JSON-safe dict, or None if role/system/capability is missing
# — never a guessed scope. Not wired into routes_chat.py: per README.md's
# hard scope rule, that file is out of bounds for work done in this folder.
_DESIGN_ROLE_RE = re.compile(r'\brole\s*(?:=|:|คือ)\s*"(?P<value>[^"]+)"', re.IGNORECASE)
_DESIGN_SYSTEM_RE = re.compile(
    r'\bsystem(?:_name)?\s*(?:=|:|คือ)\s*"(?P<value>[^"]+)"', re.IGNORECASE
)
_DESIGN_CAPABILITY_RE = re.compile(
    r'\b(?:capability|ai_capability_summary|design)\s*(?:=|:|คือ)\s*"(?P<value>[^"]+)"',
    re.IGNORECASE,
)
_DESIGN_REGULATORY_RE = re.compile(
    r'\bregulatory(?:_context)?\s*(?:=|:|คือ)\s*"(?P<value>[^"]+)"', re.IGNORECASE
)
_FACTOR_KEYS: tuple[str, ...] = tuple(row["key"] for row in FACTOR_DEFINITIONS)
_DESIGN_FACTOR_RES: dict[str, re.Pattern[str]] = {
    key: re.compile(
        rf"\b{key.replace('_', r'[_\s-]*')}\s*(?:=|:|คือ)?\s*"
        r"(?P<value>0\.5|0|1(?:\.0+)?)\b",
        re.IGNORECASE,
    )
    for key in _FACTOR_KEYS
}


def parse_design_review_request(text: str) -> dict[str, Any] | None:
    """Parse a chat message carrying a design-review request, e.g.:

        role="AI Security Lead" system="New Collections Agent (planned)"
        design="Autonomous agent that will negotiate settlement offers via
        chat and can commit a payment-plan change without human review."
        regulatory="BOT debt collection guideline, PDPA"
        autonomy=1 tools=1 persistence=1

    Mirrors parse_scope_triage_request's shape/convention but returns a
    design-review deliverable instead of an audit triage. Returns None if
    role/system/capability("design") is missing — never a guessed scope.
    """

    source = str(text or "")
    role_match = _DESIGN_ROLE_RE.search(source)
    system_match = _DESIGN_SYSTEM_RE.search(source)
    capability_match = _DESIGN_CAPABILITY_RE.search(source)
    if not role_match or not system_match or not capability_match:
        return None

    regulatory_match = _DESIGN_REGULATORY_RE.search(source)
    regulatory_context = (
        [item.strip() for item in regulatory_match.group("value").split(",") if item.strip()]
        if regulatory_match
        else []
    )

    factor_hints: dict[str, float] = {}
    for key, pattern in _DESIGN_FACTOR_RES.items():
        match = pattern.search(source)
        if match:
            factor_hints[key] = float(match.group("value"))

    try:
        scope = intake_assessment_scope(
            role=role_match.group("value"),
            system_name=system_match.group("value"),
            ai_capability_summary=capability_match.group("value"),
            regulatory_context=regulatory_context,
            factor_hints=factor_hints,
        )
        triage_rows = triage_applicable_risks(scope)
        sections = generate_design_recommendations(triage_rows)
        deliverable = assemble_design_review(scope=scope, sections=sections)
    except ValueError:
        return None

    return {
        "schema": deliverable.schema,
        "role": deliverable.role,
        "system_name": deliverable.system_name,
        "objective": deliverable.objective,
        "scope_summary": deliverable.scope_summary,
        "regulatory_context": list(deliverable.regulatory_context),
        "sections": list(deliverable.sections),
        "proof_boundary": deliverable.proof_boundary,
    }


__all__ = [
    "DESIGN_REVIEW_SCHEMA",
    "DESIGN_REVIEW_PROOF_BOUNDARY_NOTE",
    "DESIGN_MITIGATIONS",
    "DesignRiskSection",
    "generate_design_recommendations",
    "DesignReviewDeliverable",
    "assemble_design_review",
    "render_design_review_markdown",
    "build_design_review_synthesis_prompt",
    "parse_design_review_request",
]
