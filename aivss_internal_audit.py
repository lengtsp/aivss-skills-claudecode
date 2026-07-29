"""Codex-curated IT Internal Audit lens for AIVSS scenario questions.

This module is an analytical planning layer.  AIVSS page evidence remains the
authority for AIVSS facts, while COBIT practice endpoints are verified against
the local LLM-enriched reference table before they are injected into chat.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any


AUDIT_LENS_SCHEMA = "rag.aivss-it-internal-audit-lens.v1"
COBIT_SOURCE_TABLE = "paradedb.rag_cobit_full1"
COBIT_KG_GROUP_ID = 204

AUDIT_TOPICS: tuple[dict[str, Any], ...] = (
    {
        "id": "governance_risk",
        "label": "AI governance, risk appetite และ ISMS",
        "keywords": (
            "governance", "risk appetite", "risk profile", "isms", "board",
            "กำกับดูแล", "ความเสี่ยงองค์กร", "นโยบาย ai",
        ),
        "risk_keys": ("goal_instruction", "critical_systems", "supply_chain"),
        "cobit_codes": ("EDM03.01", "APO12.03", "APO13.01"),
        "audit_focus": "governance ownership, risk appetite, AI risk profile, ISMS scope, and oversight",
        "evidence": (
            "AI governance charter and accountable-owner/RACI",
            "approved risk appetite, AI risk register, and treatment decisions",
            "board or risk-committee oversight and ISMS scope records",
        ),
        "tests": (
            "trace selected AIVSS risks into the approved enterprise risk profile",
            "inspect design approval and sample operating oversight evidence",
        ),
    },
    {
        "id": "privileged_tools_iam",
        "label": "Privileged tools, IAM, SoD และ machine identity",
        "keywords": (
            "privileged", "tool", "mcp", "iam", "access", "identity", "service account",
            "สิทธิ", "ตัวตน", "เครื่องมือ", "sod",
        ),
        "risk_keys": ("tool_misuse", "access_control", "identity_impersonation"),
        "cobit_codes": ("DSS05.04", "DSS06.03"),
        "audit_focus": "least privilege, machine identity lifecycle, segregation of duties, and tool-call authorization",
        "evidence": (
            "agent/service-account and privileged-tool inventory",
            "authorization matrix, access reviews, and SoD exception register",
            "approved tool-call logs and revoked-access samples",
        ),
        "tests": (
            "sample joiner/mover/leaver and privilege-escalation events",
            "reperform denied and approved privileged tool calls against policy",
        ),
    },
    {
        "id": "memory_data_governance",
        "label": "Agent memory, data lifecycle, retention และ deletion",
        "keywords": (
            "memory", "context", "retention", "deletion", "data lifecycle", "privacy",
            "ความจำ", "บริบท", "เก็บรักษา", "ลบข้อมูล", "ข้อมูลส่วนบุคคล",
        ),
        "risk_keys": ("memory_context", "untraceability"),
        "cobit_codes": ("APO14.08", "DSS06.02"),
        "audit_focus": "memory provenance, tenant segregation, retention, deletion, processing integrity, and replay risk",
        "evidence": (
            "memory-store schema, lineage, tenant-boundary, and encryption configuration",
            "retention/deletion standard with executed deletion samples",
            "memory poisoning, replay, and integrity-monitoring test results",
        ),
        "tests": (
            "trace one memory item from creation through use, retention, and deletion",
            "test cross-session and cross-tenant isolation with authorized synthetic data",
        ),
    },
    {
        "id": "multi_agent_architecture",
        "label": "Multi-agent orchestration และ trust boundaries",
        "keywords": (
            "multi-agent", "orchestration", "agent to agent", "trust boundary",
            "ประสานงาน", "หลาย agent", "ระหว่างเอเจนต์", "agent อื่น",
        ),
        "risk_keys": ("orchestration", "access_control", "critical_systems"),
        "cobit_codes": ("BAI03.02", "DSS05.02"),
        "audit_focus": "agent topology, inter-agent authentication, message integrity, delegated authority, and blast radius",
        "evidence": (
            "agent topology, data-flow, and trust-boundary diagrams",
            "inter-agent authentication/authorization and delegated-scope configuration",
            "message integrity, replay protection, and orchestration test results",
        ),
        "tests": (
            "trace delegated authority across a complete multi-agent transaction",
            "test replay, identity substitution, and boundary failure controls",
        ),
    },
    {
        "id": "third_party_supply_chain",
        "label": "Third-party model/tool และ AI supply chain",
        "keywords": (
            "vendor", "supplier", "third party", "third-party", "supply chain",
            "llm api", "dependency", "ผู้ขาย", "ผู้ให้บริการ", "บุคคลภายนอก",
        ),
        "risk_keys": ("supply_chain", "tool_misuse"),
        "cobit_codes": ("APO10.04", "APO10.05"),
        "audit_focus": "AI component inventory, due diligence, contractual controls, monitoring, concentration risk, and exit",
        "evidence": (
            "AI component/SBOM and critical-supplier inventory",
            "supplier risk assessments, contracts, right-to-audit, and incident clauses",
            "performance/compliance monitoring, change notices, and tested exit plan",
        ),
        "tests": (
            "sample critical suppliers from onboarding through monitoring and renewal",
            "inspect one material model/tool change and one exit or substitution exercise",
        ),
    },
    {
        "id": "change_release",
        "label": "Prompt/model/tool change, release และ post-implementation review",
        "keywords": (
            "change", "release", "deployment", "prompt version", "model update",
            "เปลี่ยนแปลง", "ขึ้น production", "เวอร์ชัน", "นำขึ้นใช้งาน",
        ),
        "risk_keys": ("goal_instruction", "tool_misuse", "orchestration"),
        "cobit_codes": ("BAI06.01", "BAI07.05", "BAI07.08"),
        "audit_focus": "authorized changes, acceptance criteria, adversarial testing, release evidence, rollback, and PIR",
        "evidence": (
            "versioned prompts/models/tools and approved change tickets",
            "acceptance, security, and adversarial test evidence",
            "release/rollback records and post-implementation review",
        ),
        "tests": (
            "sample normal and emergency AI changes from approval through deployment",
            "reconcile production versions to approved baselines and PIR actions",
        ),
    },
    {
        "id": "logging_traceability",
        "label": "Logging, end-to-end traceability และ accountability",
        "keywords": (
            "log", "logging", "trace", "traceability", "audit trail", "accountability",
            "ตรวจสอบย้อนกลับ", "ร่องรอย", "บันทึกเหตุการณ์",
        ),
        "risk_keys": ("untraceability", "goal_instruction", "tool_misuse"),
        "cobit_codes": ("DSS06.05", "MEA01.03"),
        "audit_focus": "attributable and time-consistent audit trails across user, agent, model, memory, and tool boundaries",
        "evidence": (
            "logging standard, event schema, retention, and time-synchronization evidence",
            "SIEM/source coverage and protected log-access records",
            "end-to-end transaction reconstruction with correlation identifiers",
        ),
        "tests": (
            "reconstruct samples from user intent through agent decision and tool outcome",
            "test log completeness, tamper protection, clock alignment, and exception follow-up",
        ),
    },
    {
        "id": "incident_response",
        "label": "AI incident classification, investigation และ escalation",
        "keywords": (
            "incident", "alert", "investigate", "escalat", "response", "เหตุการณ์",
            "อุบัติการณ์", "แจ้งเตือน", "สืบสวน", "ส่งต่อ",
        ),
        "risk_keys": ("untraceability", "cascading_failures", "critical_systems"),
        "cobit_codes": ("DSS02.02", "DSS02.04", "MEA01.03"),
        "audit_focus": "AI incident taxonomy, severity, ownership, investigation, escalation, evidence preservation, and lessons learned",
        "evidence": (
            "AI incident taxonomy, severity matrix, playbooks, and escalation tree",
            "incident tickets, investigation records, preserved logs, and communications",
            "metrics, root-cause, remediation, and repeat-event monitoring",
        ),
        "tests": (
            "sample incidents for classification, response time, escalation, and closure evidence",
            "trace high-impact events into risk, problem, change, and governance reporting",
        ),
    },
    {
        "id": "resilience_bcp",
        "label": "Cascading failure, resilience, BCP/DR และ recovery",
        "keywords": (
            "cascad", "resilien", "bcp", "dr", "continuity", "recovery", "failover",
            "ต่อเนื่อง", "กู้คืน", "ล้มเหลว", "สำรอง",
        ),
        "risk_keys": ("cascading_failures", "critical_systems", "orchestration"),
        "cobit_codes": ("DSS04.04", "BAI04.04"),
        "audit_focus": "critical dependencies, capacity thresholds, graceful degradation, continuity exercises, and recoverability",
        "evidence": (
            "BIA, service dependency map, RTO/RPO, and failure-mode analysis",
            "capacity/circuit-breaker/failover configuration and alerts",
            "BCP/DR exercise results, recovery evidence, and tracked remediation",
        ),
        "tests": (
            "inspect one dependency-failure exercise against approved RTO/RPO",
            "verify remediation from the latest continuity test through closure",
        ),
    },
    {
        "id": "assurance_effectiveness",
        "label": "Design effectiveness, operating effectiveness และ finding",
        "keywords": (
            "design effectiveness", "operating effectiveness", "assurance", "finding",
            "test of design", "test of operating", "ประสิทธิผลการออกแบบ",
            "ประสิทธิผลการปฏิบัติ", "ข้อสังเกต", "ผลการตรวจ",
        ),
        "risk_keys": ("tool_misuse", "access_control", "untraceability"),
        "cobit_codes": ("MEA04.06", "MEA04.07"),
        "audit_focus": "criteria, population, sample, design adequacy, operating evidence, exceptions, cause, impact, and follow-up",
        "evidence": (
            "approved control design, owner, frequency, population, and evidence standard",
            "complete population plus reproducible sample and operating evidence",
            "exceptions, root cause, impact assessment, action owner, and due date",
        ),
        "tests": (
            "separate test of design from test of operating effectiveness",
            "form a finding only from verified condition evidence against approved criteria",
        ),
    },
)

OUTPUT_OPTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "risk_assessment",
        "label": "AIVSS risk assessment",
        "description": "ระบุ risks/factors และคำนวณคะแนนเมื่อมี input ครบ",
    },
    {
        "id": "control_crosswalk",
        "label": "Risk-control-evidence crosswalk",
        "description": "เชื่อม AIVSS กับ ISO/NIST/COBIT พร้อม PBC และ evidence gap",
    },
    {
        "id": "audit_program",
        "label": "Audit program",
        "description": "objective, scope, risk, control, PBC, test, owner และ pass/fail",
    },
    {
        "id": "assurance_assessment",
        "label": "Design/operating assessment",
        "description": "แยกประสิทธิผลการออกแบบและการปฏิบัติงานจากหลักฐานจริง",
    },
    {
        "id": "gap_action_plan",
        "label": "Gap and action plan",
        "description": "แยก verified fact, gap, risk implication และข้อเสนอแนะ",
    },
)


def _normalized_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())


def rank_aivss_audit_topics(
    question: str | None,
    *,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Return deterministic audit-topic recommendations for the question."""

    text = _normalized_text(question)
    generic_assurance_markers = {
        "design effectiveness",
        "operating effectiveness",
        "finding",
        "test of design",
        "test of operating",
        "ประสิทธิผลการออกแบบ",
        "ประสิทธิผลการปฏิบัติ",
        "ข้อสังเกต",
        "ผลการตรวจ",
    }
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, topic in enumerate(AUDIT_TOPICS):
        score = 0
        for keyword in topic["keywords"]:
            marker = _normalized_text(keyword)
            if marker and marker in text:
                # These terms are common output requirements across every
                # audit domain. Keep them useful for an assurance-only query,
                # but do not let them outrank an explicit business topic.
                score += (
                    1
                    if marker in generic_assurance_markers
                    else max(2, min(len(marker.split()) + 1, 4))
                )
        for risk_key in topic["risk_keys"]:
            marker = risk_key.replace("_", " ")
            if marker in text:
                score += 3
        scored.append((score, -index, topic))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected = [row[2] for row in scored if row[0] > 0][: max(1, int(limit))]
    if not selected:
        default_ids = {
            "governance_risk",
            "privileged_tools_iam",
            "logging_traceability",
            "assurance_effectiveness",
        }
        selected = [topic for topic in AUDIT_TOPICS if topic["id"] in default_ids]
    return [dict(topic) for topic in selected[: max(1, int(limit))]]


@lru_cache(maxsize=1)
def validate_aivss_audit_catalog() -> dict[str, Any]:
    """Verify every COBIT endpoint against the current local table."""

    from sqlalchemy import bindparam, text

    from database import SessionLocal

    codes = sorted(
        {
            str(code)
            for topic in AUDIT_TOPICS
            for code in topic["cobit_codes"]
        }
    )
    statement = text(
        """
        SELECT sub_practice, title_en, title_th
        FROM paradedb.rag_cobit_full1
        WHERE sub_practice IN :codes
        ORDER BY sub_practice
        """
    ).bindparams(bindparam("codes", expanding=True))
    db = SessionLocal()
    try:
        rows = db.execute(statement, {"codes": codes}).mappings().all()
    finally:
        db.close()
    endpoints = {
        str(row["sub_practice"]): {
            "code": str(row["sub_practice"]),
            "title_en": str(row.get("title_en") or ""),
            "title_th": str(row.get("title_th") or ""),
        }
        for row in rows
    }
    missing = sorted(set(codes) - set(endpoints))
    return {
        "status": "ready" if not missing else "not_ready",
        "source_table": COBIT_SOURCE_TABLE,
        "kg_group_id": COBIT_KG_GROUP_ID,
        "expected_count": len(codes),
        "verified_count": len(endpoints),
        "missing_codes": missing,
        "endpoints": endpoints,
        "llm_enriched_reference": True,
    }


def build_aivss_internal_audit_context(
    question: str | None,
    *,
    max_topics: int = 4,
    max_chars: int = 9000,
) -> dict[str, Any]:
    """Build a bounded, endpoint-verified audit-planning prompt packet."""

    verification = validate_aivss_audit_catalog()
    if verification["status"] != "ready":
        return {
            "enabled": True,
            "status": "not_ready",
            "context": "",
            "error": f"missing COBIT endpoints: {verification['missing_codes']}",
            "topics": [],
            "verification": verification,
        }
    topics = rank_aivss_audit_topics(question, limit=max_topics)
    endpoints = verification["endpoints"]
    lines = [
        "[AIVSS IT Internal Audit Scenario Lens]",
        f"schema: {AUDIT_LENS_SCHEMA}",
        "creator: Codex",
        "authority: analytical audit-planning aid only",
        f"COBIT endpoint source: {COBIT_SOURCE_TABLE}; KG group {COBIT_KG_GROUP_ID}",
        "COBIT provenance: local LLM-enriched reference; verify against licensed/approved source when high-stakes precision is required",
        "proof_boundary: AIVSS pages support AIVSS facts; this lens and its COBIT relationships do not prove control design, operation, compliance, or a finding",
        "answer_contract: separate objective, scope, criteria, risk, control, PBC/evidence, test of design, test of operating effectiveness, owner, pass/fail, evidence gap, and recommendation",
        "mandatory_endpoint_rule: when exact COBIT practice IDs are requested, include every verified endpoint listed for the highest-ranked selected audit topic before adding secondary risk-crosswalk controls",
        "finding_contract: do not state a finding without verified condition evidence and approved criteria",
        "",
        "Selected audit topics:",
    ]
    for topic in topics:
        lines.append(f"- topic_id: {topic['id']}")
        lines.append(f"  label: {topic['label']}")
        lines.append(f"  AIVSS risk candidates: {', '.join(topic['risk_keys'])}")
        cobit_text = []
        for code in topic["cobit_codes"]:
            endpoint = endpoints[str(code)]
            title = endpoint["title_en"] or endpoint["title_th"]
            cobit_text.append(f"{code} {title}")
        lines.append(f"  verified COBIT endpoints: {'; '.join(cobit_text)}")
        lines.append(f"  audit focus: {topic['audit_focus']}")
        lines.append(f"  PBC/evidence: {'; '.join(topic['evidence'])}")
        lines.append(f"  suggested tests: {'; '.join(topic['tests'])}")
    context = "\n".join(lines).strip()
    if len(context) > max_chars:
        context = context[: max_chars - 3].rstrip() + "..."
    return {
        "enabled": True,
        "status": "ready",
        "context": context,
        "topics": [str(topic["id"]) for topic in topics],
        "cobit_codes": sorted(
            {
                str(code)
                for topic in topics
                for code in topic["cobit_codes"]
            }
        ),
        "verification": {
            key: value
            for key, value in verification.items()
            if key != "endpoints"
        },
    }


def build_missing_audit_endpoint_appendix(
    answer: str | None,
    topic_ids: list[str] | tuple[str, ...] | None,
) -> dict[str, Any]:
    """Build verified endpoint and evidence-boundary completion notes."""

    selected_ids = [str(item or "").strip() for item in (topic_ids or [])]
    topic_map = {str(topic["id"]): topic for topic in AUDIT_TOPICS}
    primary = next(
        (topic_map[topic_id] for topic_id in selected_ids if topic_id in topic_map),
        None,
    )
    if not primary:
        return {"needed": False, "appendix": "", "missing_codes": []}
    verification = validate_aivss_audit_catalog()
    if verification["status"] != "ready":
        return {
            "needed": False,
            "appendix": "",
            "missing_codes": [],
            "error": f"COBIT endpoint catalog not ready: {verification['missing_codes']}",
        }
    text = _normalized_text(answer)
    missing_codes = [
        str(code)
        for code in primary["cobit_codes"]
        if _normalized_text(code) not in text
    ]
    proof_boundary_present = any(
        marker in text
        for marker in (
            "ไม่ใช่หลักฐาน",
            "ไม่ใช่ผลการตรวจ",
            "ห้ามสรุป",
            "ไม่สามารถสรุป",
            "does not prove",
            "not proof",
            "analytical candidate only",
            "source-backed limitation",
            "ยังไม่มี finding",
        )
    )
    physical_page_present = bool(
        re.search(
            r"(?:physical\s+)?p(?:age)?\.?\s*\d+|"
            r"หน้า(?:อ้างอิง)?\s*[:.]?\s*\d+|"
            r"evidence\s+gap|ช่องว่างหลักฐาน|ไม่พบหลักฐาน",
            str(answer or ""),
            re.IGNORECASE,
        )
    )
    if not missing_codes and proof_boundary_present and physical_page_present:
        return {
            "needed": False,
            "appendix": "",
            "missing_codes": [],
            "topic_id": str(primary["id"]),
        }
    endpoints = verification["endpoints"]
    lines: list[str] = []
    if missing_codes:
        lines.extend(
            [
                "### Verified audit endpoint reference",
                "",
                (
                    f"หัวข้อหลัก `{primary['label']}` มี COBIT endpoints ที่ตรวจจาก "
                    f"`{COBIT_SOURCE_TABLE}` และยังไม่ปรากฏในคำตอบข้างต้น:"
                ),
            ]
        )
        for code in missing_codes:
            endpoint = endpoints[code]
            title = endpoint["title_en"] or endpoint["title_th"]
            lines.append(f"- **{code}** — {title}")
    if not proof_boundary_present or not physical_page_present:
        if lines:
            lines.append("")
        lines.extend(
            [
                "### Evidence / proof boundary",
                "",
                (
                    "AIVSS page evidence และ condition evidence ของระบบจริง "
                    "เป็นหลักฐานที่ต้องใช้ก่อนสรุปผล; risk score, knowledge graph, "
                    "framework mapping และรายการ endpoint นี้ไม่ใช่หลักฐานว่า control "
                    "ถูกออกแบบหรือปฏิบัติอย่างมีประสิทธิผล และไม่ใช่ข้อสรุป "
                    "finding/compliance"
                ),
            ]
        )
        if not physical_page_present:
            lines.append(
                "- Evidence gap: ยังไม่มี AIVSS physical-page anchor "
                "ที่ตรวจย้อนกลับได้ในคำตอบส่วนหลัก"
            )
    lines.extend(
        [
            "",
            (
                "รายการนี้เป็น Codex-curated analytical audit-planning reference "
                "จาก local LLM-enriched COBIT table; สำหรับ high-stakes claims "
                "ต้องยืนยันกับ approved/licensed source และหลักฐานขององค์กร"
            ),
        ]
    )
    return {
        "needed": True,
        "appendix": "\n".join(lines),
        "missing_codes": missing_codes,
        "topic_id": str(primary["id"]),
        "source_table": COBIT_SOURCE_TABLE,
        "proof_boundary_added": not proof_boundary_present,
        "physical_page_gap_added": not physical_page_present,
    }


def enrich_aivss_clarification(
    clarification: dict[str, object],
    question: str | None,
) -> dict[str, object]:
    """Add user-facing IT-audit choices to an existing clarification result."""

    if not clarification.get("needed"):
        return dict(clarification)
    recommended = rank_aivss_audit_topics(question, limit=4)
    topic_lines = [
        f"{index}. {topic['label']} — COBIT {', '.join(topic['cobit_codes'])}"
        for index, topic in enumerate(recommended, start=1)
    ]
    output_lines = [
        f"{chr(65 + index)}. {row['label']}"
        for index, row in enumerate(OUTPUT_OPTIONS)
    ]
    missing = list(clarification.get("missing_information") or [])
    base_feedback = {
        "comparison_target": "ยังไม่ชัดว่าต้องการเปรียบเทียบ framework, control หรือระบบใด",
        "comparison_scope": "ยังไม่ชัดว่าต้องการเทียบด้าน governance, risk, control หรือ evidence",
        "audit_subject_or_process": "ยังไม่ระบุระบบ/กระบวนการ AI ที่จะตรวจ",
        "audit_period_or_population": "ยังไม่ระบุช่วงเวลาและ population ที่จะทดสอบ",
        "scope_or_subject": "ยังไม่ระบุระบบ กระบวนการ หรือ scenario ของ AI",
        "expected_output": "ยังไม่ระบุรูปแบบผลลัพธ์ที่ต้องการ",
        "intent": "ยังไม่ชัดว่าต้องการประเมิน risk, control, evidence หรือ assurance",
        "scope": "ยังไม่ระบุขอบเขตหลักฐานหรือ framework",
    }
    feedback_lines = [
        f"- {base_feedback[item]}"
        for item in missing
        if item in base_feedback
    ] or ["- คำถามยังไม่พอสำหรับกำหนด audit objective และ evidence scope อย่างปลอดภัย"]
    result = dict(clarification)
    result.update(
        {
            "feedback_mode": "aivss_it_internal_audit",
            "clarification_options": {
                "topics": [
                    {
                        "id": str(topic["id"]),
                        "label": str(topic["label"]),
                        "cobit_codes": list(topic["cobit_codes"]),
                        "risk_keys": list(topic["risk_keys"]),
                    }
                    for topic in AUDIT_TOPICS
                ],
                "outputs": [dict(row) for row in OUTPUT_OPTIONS],
            },
            "recommended_option_ids": [
                str(topic["id"]) for topic in recommended
            ],
            "question": (
                "ผมยังไม่ชัวร์ว่าคำถามนี้ต้องการตรวจสอบเรื่องใดครับ\n"
                + "\n".join(feedback_lines)
                + "\n\nหัวข้อที่แนะนำให้เลือก:\n"
                + "\n".join(topic_lines)
                + "\n\nรูปแบบผลลัพธ์ที่เลือกได้:\n"
                + "\n".join(output_lines)
                + "\n\nตอบสั้น ๆ เช่น “หัวข้อ 2 + รูปแบบ C, ระบบ AI Credit, งวดปี 2569” "
                "หรือระบุหัวข้อ/ขอบเขตอื่นที่ต้องการได้ไหม?"
            ),
        }
    )
    return result
