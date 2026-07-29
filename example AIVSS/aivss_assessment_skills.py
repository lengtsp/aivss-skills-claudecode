"""Deterministic AIVSS/AIVSS assessment-authoring skills for IT Internal Audit.

This module is an authoring layer on top of the two existing AIVSS modules —
it does not duplicate their data or scoring logic:

- `aivss_kg.py` is the source-grounded AIVSS v0.8 fact base: the 10 core
  Risks, the 10 Risk Factors, the `RISK_FACTOR_MATRIX` (which factors amplify
  which risk), and the deterministic `calculate_aivss()` calculator.
- `aivss_internal_audit.py` is the Codex-curated IT Internal Audit lens: 10
  audit topics mapped to risk keys, verified COBIT 2019 endpoints, and the 5
  output formats an audit deliverable can take.

What was missing before this module: a way to turn a specific engagement
(a role + a named AI-embedded system) into an actual fill-in-the-blank
questionnaire and a scored, assembled deliverable. This module adds that as
a 5-step skill chain:

    intake_assessment_scope
        -> triage_applicable_risks
        -> generate_risk_questionnaire
        -> score_finding (per confirmed finding, reuses aivss_kg.calculate_aivss)
        -> assemble_audit_deliverable

IT Internal Audit is not one of the 10 roles AIVSS itself defines (those are
1st/2nd-line: AI Security Lead/Assessor, Agent Dev/Eng/DS, SecOps, GRC,
Risk/Compliance Officer, System Owner, CISO, AI RPE, AI Governance Board, AI
Risk Classification Committee). This chain is built for Internal Audit to run
an independent (3rd-line) re-assessment, not to merely consume someone else's
score — every skill assumes the auditor gathers the evidence directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from aivss_kg import (
    FACTOR_DEFINITIONS,
    RISK_DEFINITIONS,
    RISK_FACTOR_MATRIX,
    calculate_aivss,
)
from aivss_internal_audit import AUDIT_TOPICS, OUTPUT_OPTIONS
from aivss_synthesis_prompt import build_synthesis_prompt


ASSESSMENT_SCHEMA = "rag.aivss-assessment-skills.v1"

# Concise Codex-authored paraphrases of each AIVSS core risk (not verbatim
# source text) — used to give questionnaire sections readable framing.
RISK_SUMMARIES: dict[str, str] = {
    "goal_instruction": (
        "การชักจูง/บิดเบือน goal หรือ instruction ของ agent ให้เบี่ยงไปจาก"
        "วัตถุประสงค์ที่ตั้งใจ เช่น prompt injection ผ่านอินพุตหรือบริบทแวดล้อม"
    ),
    "tool_misuse": (
        "agent ถูกหลอกหรือถูกใช้ให้เรียก tool/API ภายนอกในทางที่เป็นอันตราย "
        "เกินขอบเขตที่ตั้งใจ หรือโดยไม่ได้รับอนุญาต"
    ),
    "access_control": (
        "agent เข้าถึงหรือกระทำการเกินสิทธิ์ที่ควรได้รับ รวมถึงการยกระดับสิทธิ์ "
        "(privilege escalation) หรือข้ามขอบเขตการอนุญาตที่กำหนดไว้"
    ),
    "cascading_failures": (
        "ช่องโหว่ใน agent หนึ่งตัวลุกลามส่งผลกระทบต่อระบบ/บริการอื่นที่เชื่อมต่อกัน "
        "ขยายผลกระทบเกินจุดที่ถูกโจมตีครั้งแรก"
    ),
    "orchestration": (
        "การโจมตีที่มุ่งเป้าไปที่การประสานงาน/สื่อสารระหว่าง agent หลายตัว "
        "เช่น การปลอมแปลง message หรือแทรกแซงการมอบหมายงานระหว่าง agent"
    ),
    "identity_impersonation": (
        "agent แอบอ้าง/สวมรอยเป็นบุคคลหรือระบบที่ได้รับอนุญาตจริง (หรือถูกปลอมตัว "
        "โดยผู้โจมตี) จนก่อให้เกิดผลเสียหาย"
    ),
    "memory_context": (
        "การโจมตีที่มุ่งเป้าไปที่วิธีที่ agent จัดเก็บ/คงไว้/ใช้ข้อมูลบริบทและความจำ "
        "ทั้งในและข้าม session"
    ),
    "critical_systems": (
        "agent เชื่อมต่อ/สั่งการกับ environment ระบบ หรืออุปกรณ์ที่สำคัญ "
        "(critical infra, IaaS/SaaS, IoT) โดยไม่มีการควบคุมที่เพียงพอ"
    ),
    "supply_chain": (
        "ความเสี่ยงที่ความมั่นคง/integrity ของ agent ถูกโจมตีผ่านช่องโหว่ใน "
        "component พื้นฐานหรือ dependency ที่ agent พึ่งพา (model, library, vendor, plugin)"
    ),
    "untraceability": (
        "ไม่สามารถระบุลำดับเหตุการณ์ ตัวตน และการอนุญาตที่นำไปสู่การกระทำของ agent "
        "ได้ครบถ้วน (ช่องว่างด้าน visibility/audit trail)"
    ),
}

PROOF_BOUNDARY_NOTE = (
    "AIVSS graph/score และ audit-lens นี้เป็นเครื่องมือวางแผนตรวจสอบเชิงวิเคราะห์ "
    "(Codex-curated) ไม่ใช่หลักฐานว่า control ถูกออกแบบหรือปฏิบัติงานอย่างมีประสิทธิผล "
    "และไม่ใช่ข้อสรุป finding/compliance ด้วยตัวเอง ต้องมี condition evidence ของระบบ"
    "จริงก่อนสรุปผลเสมอ"
)

_FACTOR_KEYS: tuple[str, ...] = tuple(row["key"] for row in FACTOR_DEFINITIONS)
_FACTOR_BY_KEY: dict[str, dict[str, Any]] = {row["key"]: row for row in FACTOR_DEFINITIONS}
_RISK_BY_KEY: dict[str, dict[str, Any]] = {row["key"]: row for row in RISK_DEFINITIONS}
_OUTPUT_IDS: tuple[str, ...] = tuple(row["id"] for row in OUTPUT_OPTIONS)


def _topics_for_risk(risk_key: str) -> tuple[dict[str, Any], ...]:
    return tuple(topic for topic in AUDIT_TOPICS if risk_key in topic["risk_keys"])


def _normalize_factor_key(key: object) -> str:
    return str(key).strip().casefold().replace("-", "_").replace(" ", "_")


# ===================== Skill 1: scope intake =====================


@dataclass(frozen=True)
class AssessmentScope:
    role: str
    system_name: str
    ai_capability_summary: str
    regulatory_context: tuple[str, ...] = ()
    factor_hints: dict[str, float] = field(default_factory=dict)


def intake_assessment_scope(
    *,
    role: str,
    system_name: str,
    ai_capability_summary: str,
    regulatory_context: Iterable[str] = (),
    factor_hints: dict[str, float] | None = None,
) -> AssessmentScope:
    """Capture who is asking, what system is in scope, and any already-known
    agentic characteristics (factor_hints). factor_hints may be partial or
    empty — unknown factors simply drive scoping questions in skill 2/3."""

    role_text = str(role or "").strip()
    system_text = str(system_name or "").strip()
    capability_text = str(ai_capability_summary or "").strip()
    if not role_text:
        raise ValueError("role is required (e.g. 'IT Internal Audit')")
    if not system_text:
        raise ValueError("system_name is required")
    if not capability_text:
        raise ValueError("ai_capability_summary is required")

    normalized_hints: dict[str, float] = {}
    for raw_key, raw_value in (factor_hints or {}).items():
        key = _normalize_factor_key(raw_key)
        if key not in _FACTOR_KEYS:
            raise ValueError(
                f"unknown factor key: {raw_key!r}; expected one of {_FACTOR_KEYS}"
            )
        value = float(raw_value)
        if value not in (0.0, 0.5, 1.0):
            raise ValueError(
                f"factor {key} must be scored 0, 0.5, or 1 (got {raw_value!r})"
            )
        normalized_hints[key] = value

    return AssessmentScope(
        role=role_text,
        system_name=system_text,
        ai_capability_summary=capability_text,
        regulatory_context=tuple(
            str(item).strip() for item in regulatory_context if str(item).strip()
        ),
        factor_hints=normalized_hints,
    )


# ===================== Skill 2: risk triage =====================


@dataclass(frozen=True)
class RiskTriageRow:
    risk_key: str
    name: str
    summary: str
    amplifying_factors: tuple[str, ...]
    known_factor_levels: dict[str, float]
    unscoped_factors: tuple[str, ...]
    applicability: str  # "needs_scoping" | "high" | "medium" | "low"
    audit_topic_ids: tuple[str, ...]
    cobit_codes: tuple[str, ...]


def triage_applicable_risks(scope: AssessmentScope) -> list[RiskTriageRow]:
    """Rank the 10 AIVSS core risks for this scope using RISK_FACTOR_MATRIX.

    A risk is "needs_scoping" while any of its amplifying factors is still
    unknown (auditor must run the scoping questions from skill 3 first).
    Once every amplifying factor is known, applicability is a deterministic
    average of those factor levels: >=0.7 high, >=0.35 medium, else low.
    This is a triage heuristic to prioritize fieldwork, not a substitute for
    the AIVSS score itself (skill 4 scores confirmed findings, not risks).
    """

    rows: list[RiskTriageRow] = []
    for risk in RISK_DEFINITIONS:
        key = risk["key"]
        factors = RISK_FACTOR_MATRIX.get(key, ())
        known = {f: scope.factor_hints[f] for f in factors if f in scope.factor_hints}
        unscoped = tuple(f for f in factors if f not in scope.factor_hints)
        topics = _topics_for_risk(key)
        cobit_codes = tuple(sorted({code for t in topics for code in t["cobit_codes"]}))

        if unscoped:
            applicability = "needs_scoping"
        else:
            average = sum(known.values()) / len(known) if known else 0.0
            applicability = "high" if average >= 0.7 else "medium" if average >= 0.35 else "low"

        rows.append(
            RiskTriageRow(
                risk_key=key,
                name=risk["name"],
                summary=RISK_SUMMARIES.get(key, ""),
                amplifying_factors=factors,
                known_factor_levels=known,
                unscoped_factors=unscoped,
                applicability=applicability,
                audit_topic_ids=tuple(t["id"] for t in topics),
                cobit_codes=cobit_codes,
            )
        )

    order = {"needs_scoping": 0, "high": 1, "medium": 2, "low": 3}
    rows.sort(key=lambda row: (order[row.applicability], -len(row.known_factor_levels), row.risk_key))
    return rows


# ===================== Skill 3: questionnaire generation =====================


@dataclass(frozen=True)
class RiskQuestionnaireSection:
    risk_key: str
    name: str
    summary: str
    scoping_questions: tuple[str, ...]
    control_questions: tuple[str, ...]
    evidence_requests: tuple[str, ...]
    suggested_tests: tuple[str, ...]
    cobit_codes: tuple[str, ...]
    audit_topic_ids: tuple[str, ...]


def generate_risk_questionnaire(
    risk_keys: Iterable[str],
) -> list[RiskQuestionnaireSection]:
    """Build one questionnaire section per requested risk key.

    Scoping questions come from RISK_FACTOR_MATRIX + FACTOR_DEFINITIONS (pin
    down the 0/0.5/1 level for each amplifying factor). Control questions,
    evidence/PBC requests, suggested tests, and COBIT codes are pulled from
    the matching topics already curated in aivss_internal_audit.AUDIT_TOPICS
    — this reuses that catalog rather than re-authoring it.
    """

    sections: list[RiskQuestionnaireSection] = []
    seen: set[str] = set()
    for raw_key in risk_keys:
        key = str(raw_key).strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        risk = _RISK_BY_KEY.get(key)
        if risk is None:
            raise ValueError(f"unknown AIVSS risk key: {raw_key!r}")

        factors = RISK_FACTOR_MATRIX.get(key, ())
        scoping_questions = tuple(
            (
                f"{_FACTOR_BY_KEY[f]['name']} ({_FACTOR_BY_KEY[f]['description']}) "
                f"สำหรับ '{risk['name']}' ในระบบนี้อยู่ระดับใด: "
                "ไม่มี (0) / มีบางส่วน-จำกัด (0.5) / เต็มรูปแบบ-ไม่จำกัด (1)? "
                "ระบุหลักฐานประกอบ (design doc, config, log, interview)"
            )
            for f in factors
        )

        topics = _topics_for_risk(key)
        control_questions = tuple(dict.fromkeys(t["audit_focus"] for t in topics))
        evidence_requests = tuple(dict.fromkeys(item for t in topics for item in t["evidence"]))
        suggested_tests = tuple(dict.fromkeys(item for t in topics for item in t["tests"]))
        cobit_codes = tuple(sorted({code for t in topics for code in t["cobit_codes"]}))

        sections.append(
            RiskQuestionnaireSection(
                risk_key=key,
                name=risk["name"],
                summary=RISK_SUMMARIES.get(key, ""),
                scoping_questions=scoping_questions,
                control_questions=control_questions,
                evidence_requests=evidence_requests,
                suggested_tests=suggested_tests,
                cobit_codes=cobit_codes,
                audit_topic_ids=tuple(t["id"] for t in topics),
            )
        )
    return sections


# ===================== Skill 4: scoring a confirmed finding =====================


def score_finding(
    *,
    risk_key: str,
    finding_description: str,
    cvss_base: float,
    factor_levels: dict[str, float],
    threat_multiplier: float = 0.97,
    mitigation_factor: float = 1.0,
) -> dict[str, Any]:
    """Score one confirmed finding against a specific AIVSS risk.

    This is a thin, audit-labelled wrapper around aivss_kg.calculate_aivss —
    it does not reimplement the AARS/AIVSS formulas. Scoring is per-finding,
    not per-risk-in-general: AIVSS augments a real underlying technical
    vulnerability's CVSS_Base, so cvss_base/factor_levels/threat_multiplier/
    mitigation_factor must reflect that specific confirmed finding.
    """

    key = str(risk_key).strip().casefold()
    if key not in _RISK_BY_KEY:
        raise ValueError(f"unknown AIVSS risk key: {risk_key!r}")

    result = calculate_aivss(
        cvss_base=cvss_base,
        factors=factor_levels,
        threat_multiplier=threat_multiplier,
        mitigation_factor=mitigation_factor,
    )
    result["risk_key"] = key
    result["risk_name"] = _RISK_BY_KEY[key]["name"]
    result["finding_description"] = str(finding_description or "").strip()
    result["audit_topic_ids"] = tuple(t["id"] for t in _topics_for_risk(key))
    return result


# Chat-text parser for score_finding, mirroring the style/convention of
# aivss_kg.py's CALC_*_RE / parse_aivss_calculation_request (same optional
# "=" | ":" | "คือ" separator, same named "value" group) — but extended to
# the 10 named per-factor levels score_finding needs instead of one
# aggregate Factor_Sum.
_FINDING_RISK_RE = re.compile(
    r"\brisk(?:_key)?\s*(?:=|:|คือ)\s*(?P<value>[a-z][a-z_]*)\b",
    re.IGNORECASE,
)
_FINDING_CVSS_RE = re.compile(
    r"\b(?:cvss(?:_base|\s+base)?|คะแนน\s*cvss)\s*(?:=|:|คือ)?\s*"
    r"(?P<value>10(?:\.0+)?|[0-9](?:\.[0-9]+)?)\b",
    re.IGNORECASE,
)
_FINDING_THM_RE = re.compile(
    r"\b(?:thm|threat[_\s-]*multiplier)\s*(?:=|:|คือ)?\s*"
    r"(?P<value>0\.50|0\.5|0\.97|1(?:\.0+)?)\b",
    re.IGNORECASE,
)
_FINDING_MITIGATION_RE = re.compile(
    r"\b(?:mitigation[_\s-]*factor|mitigation)\s*(?:=|:|คือ)?\s*"
    r"(?P<value>0\.67|0\.83|1(?:\.0+)?)\b",
    re.IGNORECASE,
)
_FINDING_DESCRIPTION_RE = re.compile(
    r'\bfinding(?:_description)?\s*(?:=|:)\s*"(?P<value>[^"]+)"',
    re.IGNORECASE,
)
_FINDING_FACTOR_RES: dict[str, re.Pattern[str]] = {
    key: re.compile(
        rf"\b{key.replace('_', r'[_\s-]*')}\s*(?:=|:|คือ)?\s*"
        r"(?P<value>0\.5|0|1(?:\.0+)?)\b",
        re.IGNORECASE,
    )
    for key in _FACTOR_KEYS
}


def parse_finding_score_request(text: str) -> dict[str, Any] | None:
    """Parse a chat message carrying a full per-finding scoring request, e.g.:

        risk=goal_instruction finding="prompt injection auto fund-switch"
        cvss=2.4 autonomy=1 tools=1 language=1 context=1 non_determinism=0.5
        opacity=1 persistence=0.5 identity=0.5 multi_agent=0.5 self_mod=0
        thm=0.97 mitigation=1.0

    Returns the score_finding() result dict, or None if the message is
    missing risk=, cvss=, an unknown risk key, or any of the 10 factor keys —
    this never guesses or scores from a partial/ambiguous message.
    """

    source = str(text or "")
    risk_match = _FINDING_RISK_RE.search(source)
    cvss_match = _FINDING_CVSS_RE.search(source)
    if not risk_match or not cvss_match:
        return None

    risk_key = risk_match.group("value").strip().casefold()
    if risk_key not in _RISK_BY_KEY:
        return None

    factor_levels: dict[str, float] = {}
    for key, pattern in _FINDING_FACTOR_RES.items():
        match = pattern.search(source)
        if not match:
            return None
        factor_levels[key] = float(match.group("value"))

    thm_match = _FINDING_THM_RE.search(source)
    mitigation_match = _FINDING_MITIGATION_RE.search(source)
    description_match = _FINDING_DESCRIPTION_RE.search(source)

    result = score_finding(
        risk_key=risk_key,
        finding_description=(
            description_match.group("value")
            if description_match
            else "AIVSS finding (no description provided in chat message)"
        ),
        cvss_base=float(cvss_match.group("value")),
        factor_levels=factor_levels,
        threat_multiplier=float(thm_match.group("value")) if thm_match else 0.97,
        mitigation_factor=(
            float(mitigation_match.group("value")) if mitigation_match else 1.0
        ),
    )
    result["defaults_applied"] = {
        "threat_multiplier": not bool(thm_match),
        "mitigation_factor": not bool(mitigation_match),
    }
    return result


# Chat-text parser for skills 1+2 (intake_assessment_scope -> triage_applicable_risks),
# same convention family as parse_finding_score_request above: quoted-string capture
# for free-text fields, one regex per factor key. Unlike the finding-score parser,
# factor levels here are all optional — a partial (or empty) factor_hints set is valid
# input to intake_assessment_scope; unscoped factors simply surface as needs_scoping.
_SCOPE_ROLE_RE = re.compile(r'\brole\s*(?:=|:|คือ)\s*"(?P<value>[^"]+)"', re.IGNORECASE)
_SCOPE_SYSTEM_RE = re.compile(
    r'\bsystem(?:_name)?\s*(?:=|:|คือ)\s*"(?P<value>[^"]+)"', re.IGNORECASE
)
_SCOPE_CAPABILITY_RE = re.compile(
    r'\b(?:capability|ai_capability_summary)\s*(?:=|:|คือ)\s*"(?P<value>[^"]+)"',
    re.IGNORECASE,
)
_SCOPE_REGULATORY_RE = re.compile(
    r'\bregulatory(?:_context)?\s*(?:=|:|คือ)\s*"(?P<value>[^"]+)"', re.IGNORECASE
)
_SCOPE_FACTOR_RES: dict[str, re.Pattern[str]] = {
    key: re.compile(
        rf"\b{key.replace('_', r'[_\s-]*')}\s*(?:=|:|คือ)?\s*"
        r"(?P<value>0\.5|0|1(?:\.0+)?)\b",
        re.IGNORECASE,
    )
    for key in _FACTOR_KEYS
}


def parse_scope_triage_request(text: str) -> dict[str, Any] | None:
    """Parse a chat message carrying a scope-intake request, e.g.:

        role="IT Internal Audit" system="Mobile Banking - AI Investment Advisory"
        capability="Chat-based robo-advisor ... backed by a third-party LLM."
        regulatory="SEC Thailand robo-advisor guideline, BOT IT risk, PDPA"
        autonomy=1 tools=1 language=1 context=1 persistence=0.5

    Runs intake_assessment_scope() -> triage_applicable_risks() and returns a
    JSON-safe dict (scope fields + a list of triage rows as plain dicts), or
    None if role/system/capability are missing — this never guesses a scope
    from partial/ambiguous text. Factor hints may be partial or entirely
    absent (unlike parse_finding_score_request, which requires all 10) —
    unscoped factors simply surface as needs_scoping in the triage output.
    """

    source = str(text or "")
    role_match = _SCOPE_ROLE_RE.search(source)
    system_match = _SCOPE_SYSTEM_RE.search(source)
    capability_match = _SCOPE_CAPABILITY_RE.search(source)
    if not role_match or not system_match or not capability_match:
        return None

    regulatory_match = _SCOPE_REGULATORY_RE.search(source)
    regulatory_context = (
        [item.strip() for item in regulatory_match.group("value").split(",") if item.strip()]
        if regulatory_match
        else []
    )

    factor_hints: dict[str, float] = {}
    for key, pattern in _SCOPE_FACTOR_RES.items():
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
    except ValueError:
        return None

    return {
        "role": scope.role,
        "system_name": scope.system_name,
        "ai_capability_summary": scope.ai_capability_summary,
        "regulatory_context": list(scope.regulatory_context),
        "factor_hints": dict(scope.factor_hints),
        "triage": [
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
        ],
    }


# ===================== Skill 5: audit deliverable assembly =====================


@dataclass(frozen=True)
class AuditDeliverable:
    schema: str
    output_id: str
    role: str
    system_name: str
    objective: str
    scope_summary: str
    regulatory_context: tuple[str, ...]
    risks: tuple[dict[str, Any], ...]
    findings: tuple[dict[str, Any], ...]
    proof_boundary: str


def assemble_audit_deliverable(
    *,
    scope: AssessmentScope,
    triage_rows: Iterable[RiskTriageRow],
    questionnaire_sections: Iterable[RiskQuestionnaireSection],
    scored_findings: Iterable[dict[str, Any]] = (),
    output_id: str = "audit_program",
) -> AuditDeliverable:
    """Assemble scope + triage + questionnaire + scored findings into one of
    the 5 existing OUTPUT_OPTIONS formats (validated against that catalog)."""

    output = str(output_id).strip()
    if output not in _OUTPUT_IDS:
        raise ValueError(f"unknown output_id {output_id!r}; expected one of {_OUTPUT_IDS}")

    questionnaire_by_key = {section.risk_key: section for section in questionnaire_sections}
    risks: list[dict[str, Any]] = []
    for row in triage_rows:
        section = questionnaire_by_key.get(row.risk_key)
        risks.append(
            {
                "risk_key": row.risk_key,
                "name": row.name,
                "applicability": row.applicability,
                "cobit_codes": row.cobit_codes,
                "audit_topic_ids": row.audit_topic_ids,
                "control_questions": section.control_questions if section else (),
                "evidence_requests": section.evidence_requests if section else (),
                "suggested_tests": section.suggested_tests if section else (),
            }
        )

    return AuditDeliverable(
        schema=ASSESSMENT_SCHEMA,
        output_id=output,
        role=scope.role,
        system_name=scope.system_name,
        objective=(
            f"ประเมินความเสี่ยง AIVSS-amplified ของ '{scope.system_name}' "
            f"ในมุมมองของ {scope.role} (independent re-assessment)"
        ),
        scope_summary=scope.ai_capability_summary,
        regulatory_context=scope.regulatory_context,
        risks=tuple(risks),
        findings=tuple(scored_findings),
        proof_boundary=PROOF_BOUNDARY_NOTE,
    )


def render_deliverable_markdown(deliverable: AuditDeliverable) -> str:
    lines: list[str] = [
        f"# AIVSS Assessment — {deliverable.system_name}",
        f"role: {deliverable.role} | output: {deliverable.output_id} | schema: {deliverable.schema}",
        "",
        f"**Objective:** {deliverable.objective}",
        f"**Scope:** {deliverable.scope_summary}",
    ]
    if deliverable.regulatory_context:
        lines.append(f"**Regulatory context:** {', '.join(deliverable.regulatory_context)}")
    lines.append("")
    lines.append("## Risks")
    for risk in deliverable.risks:
        lines.append(f"### {risk['name']} ({risk['risk_key']}) — {risk['applicability']}")
        if risk["cobit_codes"]:
            lines.append(f"- COBIT: {', '.join(risk['cobit_codes'])}")
        for question in risk["control_questions"]:
            lines.append(f"- Control focus: {question}")
        for item in risk["evidence_requests"]:
            lines.append(f"- PBC/Evidence: {item}")
        for test in risk["suggested_tests"]:
            lines.append(f"- Test: {test}")
        lines.append("")

    if deliverable.findings:
        lines.append("## Scored findings")
        for finding in deliverable.findings:
            lines.append(
                f"- [{finding.get('risk_name')}] {finding.get('finding_description')} "
                f"-> AIVSS {finding.get('aivss')} ({finding.get('severity')}), "
                f"CVSS_Base {finding.get('cvss_base')}, Factor_Sum {finding.get('factor_sum')}"
            )
        lines.append("")

    lines.append("## Proof boundary")
    lines.append(deliverable.proof_boundary)
    return "\n".join(lines)


def build_audit_deliverable_synthesis_prompt(
    deliverable: AuditDeliverable,
    *,
    original_question: str = "",
    answer_language: str = "Thai",
) -> str:
    """Turn this audit deliverable into an LLM-ready prompt for a narrative
    answer, instead of handing the caller raw markdown. See
    `aivss_synthesis_prompt.build_synthesis_prompt` docstring for why this
    exists — found missing during a live quality test on the sibling
    `aivss_design_review` module (README.md "Live quality test", 2026-07-28);
    applied here too since `assemble_audit_deliverable` has the same
    "raw markdown reads as a checklist, not an answer" shape."""

    return build_synthesis_prompt(
        grounded_markdown=render_deliverable_markdown(deliverable),
        original_question=original_question,
        answer_language=answer_language,
        audience_hint="an IT Internal Audit stakeholder reviewing this engagement",
    )


def render_questionnaire_markdown(
    sections: Iterable[RiskQuestionnaireSection],
    *,
    title: str = "AIVSS Assessment Scoping Questionnaire",
) -> str:
    """Render generate_risk_questionnaire() output as a fillable markdown
    document — the skill-3 counterpart to render_deliverable_markdown()
    (skill 5's renderer). Scoping questions become a fill-in checklist;
    control questions / evidence requests / suggested tests / COBIT codes
    are reused as-is from the existing aivss_internal_audit catalog, not
    re-authored here.
    """

    lines: list[str] = [f"# {title}"]
    for section in sections:
        lines.append("")
        lines.append(f"## {section.name} ({section.risk_key})")
        if section.summary:
            lines.append(section.summary)
        if section.cobit_codes:
            lines.append(f"- COBIT: {', '.join(section.cobit_codes)}")
        if section.scoping_questions:
            lines.append("")
            lines.append("### Scoping questions")
            for question in section.scoping_questions:
                lines.append(f"- [ ] {question}")
        if section.control_questions:
            lines.append("")
            lines.append("### Control focus")
            for question in section.control_questions:
                lines.append(f"- {question}")
        if section.evidence_requests:
            lines.append("")
            lines.append("### PBC / Evidence requests")
            for item in section.evidence_requests:
                lines.append(f"- {item}")
        if section.suggested_tests:
            lines.append("")
            lines.append("### Suggested tests")
            for test in section.suggested_tests:
                lines.append(f"- {test}")
    return "\n".join(lines)


__all__ = [
    "ASSESSMENT_SCHEMA",
    "RISK_SUMMARIES",
    "PROOF_BOUNDARY_NOTE",
    "AssessmentScope",
    "intake_assessment_scope",
    "RiskTriageRow",
    "triage_applicable_risks",
    "RiskQuestionnaireSection",
    "generate_risk_questionnaire",
    "score_finding",
    "parse_finding_score_request",
    "parse_scope_triage_request",
    "AuditDeliverable",
    "assemble_audit_deliverable",
    "render_deliverable_markdown",
    "build_audit_deliverable_synthesis_prompt",
    "render_questionnaire_markdown",
]
