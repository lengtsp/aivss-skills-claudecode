"""Ten worked design-review use cases — one per AIVSS core risk — each in a
banking/fintech context matching this project's IT Audit domain, per the
user's request (2026-07-28) to "design use cases matching these 10
scenarios, with the thinking method [วิธีคิด]."

Distinct from `aivss_worked_examples.py` (3 scenarios, audit-chain /
`assemble_audit_deliverable`, 3rd-line retrospective) in two ways:
- **Coverage**: all 10 core risks, one dedicated use case each, vs. 3.
- **Chain**: the *design-review* chain (`aivss_design_review.py`
  `generate_design_recommendations` / `assemble_design_review`), a 1st/2nd
  line proactive "what should we build" perspective — chosen because the
  user's phrasing emphasized "ออกแบบ" (design) specifically.

Each `RiskUseCase.factor_hints` is grounded in `aivss_kg.RISK_FACTOR_MATRIX`
for that risk's own amplifying factors (set high/realistic), not copied
verbatim from the OWASP calculator's own illustrative scenarios
(`test_aivss_owasp_calculator_cross_validation.py`) — those are deliberately
near-maximum across most factors to be worst-case illustrations, whereas
these are meant to read as plausible, varied banking systems where the
target risk is the dominant (not the only) concern, same shape as the
existing 3 scenarios in `aivss_worked_examples.py`.

`reasoning_th` on each use case is the "วิธีคิด" the user asked for: a short
Thai paragraph connecting the system's actual capabilities to the specific
amplifying factors that make this risk apply, written before running any
skill — the point is to show the reasoning that *justifies* the
`factor_hints` values, not just assert them.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from aivss_assessment_skills import (
    AssessmentScope,
    intake_assessment_scope,
    triage_applicable_risks,
)
from aivss_design_review import (
    DesignReviewDeliverable,
    assemble_design_review,
    build_design_review_synthesis_prompt,
    generate_design_recommendations,
    render_design_review_markdown,
)

PLAYBOOK_SCHEMA = "rag.aivss-ten-risk-design-playbook.v1"

OUTPUT_DIR = Path(__file__).resolve().parent / "design_playbook"


@dataclass(frozen=True)
class RiskUseCase:
    risk_key: str
    role: str
    system_name: str
    ai_capability_summary: str
    regulatory_context: tuple[str, ...]
    factor_hints: dict[str, float]
    reasoning_th: str
    original_question: str


RISK_USE_CASES: tuple[RiskUseCase, ...] = (
    RiskUseCase(
        risk_key="tool_misuse",
        role="AI Security Lead",
        system_name="AI Treasury Dealing Assistant",
        ai_capability_summary=(
            "รับคำสั่งจาก trader ผ่าน chat/เสียงเป็นภาษาธรรมชาติ แล้วเรียกใช้เครื่องมือซื้อขาย "
            "หลายตัวโดยอัตโนมัติ (FX pricing API, bond trading API, market-data MCP server) "
            "เพื่อยิง order เข้าตลาดโดยไม่ต้องรอ trader ยืนยันซ้ำ"
        ),
        regulatory_context=("BOT market conduct / dealing room guideline", "SEC Thailand", "PDPA"),
        factor_hints={
            "autonomy": 1.0, "tools": 1.0, "language": 1.0, "context": 0.5,
            "non_determinism": 0.5, "opacity": 0.5, "persistence": 0.0,
            "identity": 0.0, "multi_agent": 0.0, "self_mod": 0.0,
        },
        reasoning_th=(
            "วิธีคิด: tool_misuse ถูกขยายด้วย autonomy + tools + language (RISK_FACTOR_MATRIX) "
            "ระบบนี้ตรงทั้ง 3 ข้อพอดี — ยิง order เอง (autonomy=1), เรียกเครื่องมือซื้อขายได้หลายตัว "
            "ซึ่งเป็น external tool control surface ที่กว้าง (tools=1), และรับคำสั่งทั้งหมดผ่านภาษา "
            "ธรรมชาติจาก trader (language=1) — ช่องทางนี้เองที่เปิดให้เกิด tool squatting "
            "(เครื่องมือปลอมแอบอ้างเป็น market-data provider จริง) หรือ metadata injection ที่หลอกให้ "
            "agent เรียก tool ผิดขอบเขต"
        ),
        original_question="ควรออกแบบระบบนี้อย่างไรให้ปลอดภัยจากความเสี่ยงด้าน AI agentic?",
    ),
    RiskUseCase(
        risk_key="access_control",
        role="AI Security Lead",
        system_name="AI Case-Management Agent for KYC/AML Investigation",
        ai_capability_summary=(
            "สืบสวนเคส AML/KYC ที่น่าสงสัยโดยใช้ identity ของผู้สืบสวนคนเดียวกันข้าม case-management, "
            "core banking, และ watchlist screening system ตลอดระยะเวลาสืบสวนหลายสัปดาห์ต่อเนื่อง"
        ),
        regulatory_context=("AMLO customer due diligence", "BOT IT risk", "PDPA"),
        factor_hints={
            "autonomy": 0.5, "tools": 1.0, "language": 0.0, "context": 0.5,
            "non_determinism": 0.0, "opacity": 0.0, "persistence": 1.0,
            "identity": 0.5, "multi_agent": 0.0, "self_mod": 0.0,
        },
        reasoning_th=(
            "วิธีคิด: access_control ถูกขยายด้วย tools + identity + persistence ระบบนี้ถือ "
            "credential เดียวเข้าหลายระบบพร้อมกัน (tools=1, external tool control surface กว้าง) "
            "ใช้ identity เดิมต่อเนื่องยาวนานหลาย session ของเคสเดียว (persistence=1) และมีการสวม "
            "บทบาทตามเคสที่ได้รับมอบหมายบางส่วน (identity=0.5) — โครงสร้างนี้เข้าเงื่อนไข temporal "
            "permission drift และ confused-deputy pattern ได้ง่ายถ้าไม่มี re-authorization ต่อระบบ"
        ),
        original_question="ควรออกแบบระบบนี้อย่างไรให้ปลอดภัยจากความเสี่ยงด้าน AI agentic?",
    ),
    RiskUseCase(
        risk_key="cascading_failures",
        role="AI Security Lead",
        system_name="Multi-Branch AI Teller Orchestration Network",
        ai_capability_summary=(
            "เครือข่าย AI teller agent ประจำแต่ละสาขา อนุมัติธุรกรรมวงเงินเล็กได้เองอัตโนมัติ "
            "และรายงานสถานะ/บริบทให้ orchestrator กลางที่เชื่อข้อมูลจาก peer agent ทุกตัวโดยไม่ตรวจสอบซ้ำ"
        ),
        regulatory_context=("BOT IT risk / operational resilience guideline", "PDPA"),
        factor_hints={
            "autonomy": 1.0, "tools": 0.5, "language": 0.0, "context": 0.5,
            "non_determinism": 0.5, "opacity": 1.0, "persistence": 0.0,
            "identity": 0.0, "multi_agent": 1.0, "self_mod": 0.0,
        },
        reasoning_th=(
            "วิธีคิด: cascading_failures ถูกขยายด้วย autonomy + multi_agent + non_determinism + "
            "opacity — สาขาหนึ่งที่ถูกโจมตี/รายงานข้อมูลเท็จ จะลามไปยัง orchestrator กลางที่เชื่อ peer "
            "ทุกตัว (multi_agent=1) และตัดสินใจเองต่อทันทีไม่รอคน (autonomy=1) โดยมองไม่เห็นเหตุผล "
            "เบื้องหลังการตัดสินใจของสาขาต้นทาง (opacity=1) — ผลกระทบขยายเกินจุดที่ถูกโจมตีครั้งแรก"
        ),
        original_question="ควรออกแบบระบบนี้อย่างไรให้ปลอดภัยจากความเสี่ยงด้าน AI agentic?",
    ),
    RiskUseCase(
        risk_key="orchestration",
        role="AI Security Lead",
        system_name="Multi-Agent Loan Origination Pipeline",
        ai_capability_summary=(
            "pipeline พิจารณาสินเชื่อประกอบด้วย document-intake agent → credit-scoring agent → "
            "approval agent ส่งต่องานและ context ระหว่างกัน โดย agent ปลายทางกระทำการในนามของ "
            "agent ต้นทางที่มอบหมายงานมา"
        ),
        regulatory_context=("BOT lending / responsible-lending guideline", "PDPA"),
        factor_hints={
            "autonomy": 1.0, "tools": 0.5, "language": 0.0, "context": 1.0,
            "non_determinism": 0.5, "opacity": 0.5, "persistence": 0.0,
            "identity": 1.0, "multi_agent": 1.0, "self_mod": 0.0,
        },
        reasoning_th=(
            "วิธีคิด: orchestration ถูกขยายด้วย autonomy + identity + multi_agent + context — "
            "pipeline นี้มี agent หลายตัวประสานงานกัน (multi_agent=1) โดย agent ปลายทางกระทำการ "
            "'ในนามของ' agent ต้นทาง คือการมอบอำนาจแบบพลวัต (identity=1) และใช้บริบทเดียวกันส่งต่อกัน "
            "ทั้ง pipeline (context=1) — จุดอ่อนคือการปลอมแปลง message หรือแทรกแซงการมอบหมายงาน "
            "ระหว่าง agent"
        ),
        original_question="ควรออกแบบระบบนี้อย่างไรให้ปลอดภัยจากความเสี่ยงด้าน AI agentic?",
    ),
    RiskUseCase(
        risk_key="identity_impersonation",
        role="AI Security Lead",
        system_name="AI Voice-Banking Authentication & Support Agent",
        ai_capability_summary=(
            "ยืนยันตัวตนลูกค้าด้วย voice biometric ผสมกับบทสนทนาภาษาธรรมชาติ แล้วดำเนินการเปลี่ยนแปลง "
            "บัญชี (เปลี่ยนเบอร์โทร, ปลดล็อกบัญชี) ในนามลูกค้าที่ 'ยืนยันแล้ว' โดยไม่ผ่านเจ้าหน้าที่"
        ),
        regulatory_context=("BOT KYC/CDD guideline", "PDPA"),
        factor_hints={
            "autonomy": 0.5, "tools": 0.5, "language": 1.0, "context": 0.0,
            "non_determinism": 0.0, "opacity": 1.0, "persistence": 0.0,
            "identity": 1.0, "multi_agent": 0.0, "self_mod": 0.0,
        },
        reasoning_th=(
            "วิธีคิด: identity_impersonation ถูกขยายด้วย identity + opacity + language — agent "
            "ตัดสินใจ 'ใครคือใคร' ผ่านเสียง/บทสนทนาล้วน (language=1) โดยไม่สามารถตรวจสอบย้อนกลับได้ "
            "ว่าทำไมถึงเชื่อว่าเป็นลูกค้าจริง (opacity=1) แล้วกระทำการในนามลูกค้าคนนั้นต่อ (identity=1) "
            "— ช่องทางนี้เสี่ยงต่อ voice deepfake และ human impersonation โดยตรง"
        ),
        original_question="ควรออกแบบระบบนี้อย่างไรให้ปลอดภัยจากความเสี่ยงด้าน AI agentic?",
    ),
    RiskUseCase(
        risk_key="memory_context",
        role="AI Security Lead",
        system_name="AI Relationship Manager with Long-Term Customer Memory",
        ai_capability_summary=(
            "จำบทสนทนาและความชอบของลูกค้า wealth-management ไว้ใน vector database ข้ามหลายเดือน "
            "เพื่อปรับคำแนะนำการลงทุนให้ตรงกับ 'สิ่งที่คุยกันไว้ก่อนหน้า' ในทุกครั้งที่ลูกค้าติดต่อกลับมา"
        ),
        regulatory_context=("SEC Thailand investment advisory guideline", "PDPA"),
        factor_hints={
            "autonomy": 0.0, "tools": 0.0, "language": 0.5, "context": 1.0,
            "non_determinism": 0.0, "opacity": 1.0, "persistence": 1.0,
            "identity": 0.0, "multi_agent": 0.0, "self_mod": 0.0,
        },
        reasoning_th=(
            "วิธีคิด: memory_context ถูกขยายด้วย persistence + context + opacity — ความจำระยะยาว "
            "ข้าม session (persistence=1) ที่ดึงบริบทกว้างจากประวัติสนทนาทั้งหมดมาใช้ (context=1) "
            "โดยตรวจสอบไม่ได้ว่าทำไมถึงแนะนำแบบนั้น (opacity=1) — เสี่ยง memory poisoning หรือ "
            "cross-customer memory contamination ถ้า memory store ไม่แยกตาม tenant อย่างเข้มงวด"
        ),
        original_question="ควรออกแบบระบบนี้อย่างไรให้ปลอดภัยจากความเสี่ยงด้าน AI agentic?",
    ),
    RiskUseCase(
        risk_key="critical_systems",
        role="AI Security Lead",
        system_name="AI Core Banking Configuration Agent",
        ai_capability_summary=(
            "ปรับพารามิเตอร์ core banking (สูตรคิดดอกเบี้ย, ตารางค่าธรรมเนียม) โดยอัตโนมัติตาม "
            "feedback การใช้งาน และสามารถแก้ไข automation script ของตัวเองเพื่อปรับปรุงประสิทธิภาพ"
        ),
        regulatory_context=("BOT IT risk / change-management guideline", "ISO 27001"),
        factor_hints={
            "autonomy": 1.0, "tools": 1.0, "language": 0.0, "context": 0.5,
            "non_determinism": 0.0, "opacity": 0.5, "persistence": 0.0,
            "identity": 0.0, "multi_agent": 0.0, "self_mod": 1.0,
        },
        reasoning_th=(
            "วิธีคิด: critical_systems ถูกขยายด้วย autonomy + tools + context + self_mod — "
            "agent เข้าถึง core banking โดยตรง (tools=1), ตัดสินใจปรับ config เองไม่รอคน "
            "(autonomy=1), และแก้ไข logic/script ของตัวเองได้ (self_mod=1) — สามคุณสมบัตินี้รวมกัน "
            "คือคำนิยามของ critical_systems พอดี ผิดพลาดครั้งเดียวกระทบระบบ mission-critical ทั้งธนาคาร"
        ),
        original_question="ควรออกแบบระบบนี้อย่างไรให้ปลอดภัยจากความเสี่ยงด้าน AI agentic?",
    ),
    RiskUseCase(
        risk_key="supply_chain",
        role="AI Security Lead",
        system_name="Bank's AI Agent Platform (Foundation Model + Plugin Marketplace)",
        ai_capability_summary=(
            "แพลตฟอร์มกลางที่ agent ทุกตัวในธนาคารพึ่งพา สร้างบน third-party foundation model API "
            "ภายนอก บวก marketplace ของ MCP tool plugin แบบเปิด และ model registry ที่อัปเดตผ่าน "
            "CI/CD pipeline อัตโนมัติ"
        ),
        regulatory_context=("BOT third-party risk management guideline", "PDPA"),
        factor_hints={
            "autonomy": 0.5, "tools": 1.0, "language": 0.5, "context": 0.5,
            "non_determinism": 0.5, "opacity": 0.5, "persistence": 0.5,
            "identity": 0.5, "multi_agent": 0.5, "self_mod": 0.5,
        },
        reasoning_th=(
            "วิธีคิด: supply_chain เป็นความเสี่ยงเดียวที่ RISK_FACTOR_MATRIX ผูกกับ amplifying "
            "factor ครบทั้ง 10 ตัว เพราะไม่ได้ผูกกับพฤติกรรม agent ตัวใดตัวหนึ่ง แต่ผูกกับ 'รากฐาน' "
            "ที่ agent ทุกตัวในระบบพึ่งพา (model, library, vendor, plugin) — ถ้า foundation model "
            "หรือ MCP plugin ตัวใดตัวหนึ่งถูกแทรกแซง ผลกระทบจะกระจายไปยังทุก use case ข้างต้นพร้อมกัน "
            "จึงตั้งทุก factor ไว้ระดับปานกลาง-สูงสม่ำเสมอ แทนที่จะเน้นตัวใดตัวหนึ่งเป็นพิเศษ "
            "หมายเหตุจาก triage heuristic: เพราะต้องเฉลี่ยครบทั้ง 10 factor ระบบที่ 'สมจริง' "
            "(ไม่ได้ maxed ทุกค่าเป็น 1.0 แบบ worst-case) มักได้ applicability เป็น medium ไม่ใช่ high "
            "แม้จะเป็นความเสี่ยงที่ควรให้ความสำคัญจริงจังก็ตาม — นี่คือความแตกต่างเชิงโครงสร้างของ "
            "supply_chain เทียบกับอีก 9 ความเสี่ยง ไม่ใช่ข้อบกพร่องของ use case นี้"
        ),
        original_question="ควรออกแบบระบบนี้อย่างไรให้ปลอดภัยจากความเสี่ยงด้าน AI agentic?",
    ),
    RiskUseCase(
        risk_key="untraceability",
        role="AI Security Lead",
        system_name="AI Compliance Monitoring Agent Across Core Banking + Digital Channels",
        ai_capability_summary=(
            "สแกนธุรกรรมข้าม core banking, mobile banking, และ internet banking หาความผิดปกติ "
            "โดยสวมบทบาท (role) ต่างกันเพื่อ query แต่ละระบบ และให้คะแนนความเสี่ยงด้วย ML model "
            "ที่ผลลัพธ์เปลี่ยนไปตามเวอร์ชันโมเดล"
        ),
        regulatory_context=("BOT AML/CFT monitoring guideline", "AMLO", "PDPA"),
        factor_hints={
            "autonomy": 0.5, "tools": 0.5, "language": 0.0, "context": 0.5,
            "non_determinism": 1.0, "opacity": 1.0, "persistence": 0.0,
            "identity": 1.0, "multi_agent": 0.0, "self_mod": 0.0,
        },
        reasoning_th=(
            "วิธีคิด: untraceability ถูกขยายด้วย opacity + identity + non_determinism — agent "
            "สวมบทบาทต่างกันในแต่ละระบบ (identity=1, dynamic identity), ให้คะแนนที่ไม่ deterministic "
            "เปลี่ยนไปตาม model version (non_determinism=1), และมองไม่เห็นเหตุผลภายในการให้คะแนน "
            "(opacity=1) — รวมกันแล้วตรวจสอบย้อนกลับไม่ได้ว่าทำไมธุรกรรมหนึ่งถูกปล่อยผ่านหรือถูกบล็อก"
        ),
        original_question="ควรออกแบบระบบนี้อย่างไรให้ปลอดภัยจากความเสี่ยงด้าน AI agentic?",
    ),
    RiskUseCase(
        risk_key="goal_instruction",
        role="AI Security Lead",
        system_name="AI Customer Complaint & Goodwill Compensation Agent",
        ai_capability_summary=(
            "อ่านอีเมล/แชทร้องเรียนของลูกค้าเป็นภาษาธรรมชาติ ประเมิน sentiment และบริบทของเรื่อง "
            "ร้องเรียน แล้วอนุมัติเงินชดเชย (goodwill compensation) ให้ลูกค้าโดยอัตโนมัติโดยไม่ต้อง "
            "รอเจ้าหน้าที่ตรวจสอบก่อน"
        ),
        regulatory_context=("BOT market conduct / fair treatment of customers guideline", "PDPA"),
        factor_hints={
            "autonomy": 1.0, "tools": 0.5, "language": 1.0, "context": 1.0,
            "non_determinism": 0.5, "opacity": 0.0, "persistence": 0.0,
            "identity": 0.0, "multi_agent": 0.0, "self_mod": 0.0,
        },
        reasoning_th=(
            "วิธีคิด: goal_instruction ถูกขยายด้วย language + autonomy + non_determinism + "
            "context — agent รับคำสั่ง/บริบททั้งหมดผ่านภาษาธรรมชาติจากข้อความร้องเรียนของลูกค้า "
            "โดยตรง (language=1) ซึ่งเป็นช่องให้ prompt injection ฝังอยู่ในอีเมลร้องเรียนได้ "
            "แล้วตัดสินใจอนุมัติเงินชดเชยเอง (autonomy=1) โดยใช้บริบทกว้างจากเนื้อหาที่ลูกค้าเขียนมา "
            "(context=1) — ตรงนิยาม goal_instruction พอดี เสี่ยงถูกชักจูงให้จ่ายชดเชยเกินจริง"
        ),
        original_question="ควรออกแบบระบบนี้อย่างไรให้ปลอดภัยจากความเสี่ยงด้าน AI agentic?",
    ),
)

_USE_CASE_BY_KEY: dict[str, RiskUseCase] = {uc.risk_key: uc for uc in RISK_USE_CASES}


def get_use_case(risk_key: str) -> RiskUseCase | None:
    return _USE_CASE_BY_KEY.get(str(risk_key).strip())


def build_scope_and_triage(use_case: RiskUseCase) -> tuple[AssessmentScope, list]:
    scope = intake_assessment_scope(
        role=use_case.role,
        system_name=use_case.system_name,
        ai_capability_summary=use_case.ai_capability_summary,
        regulatory_context=use_case.regulatory_context,
        factor_hints=use_case.factor_hints,
    )
    triage_rows = triage_applicable_risks(scope)
    return scope, triage_rows


def build_design_review(use_case: RiskUseCase, *, top_n: int = 5) -> DesignReviewDeliverable:
    scope, triage_rows = build_scope_and_triage(use_case)
    sections = generate_design_recommendations(triage_rows, top_n=top_n)
    return assemble_design_review(scope=scope, sections=sections)


def build_all_design_reviews(*, top_n: int = 5) -> dict[str, DesignReviewDeliverable]:
    return {uc.risk_key: build_design_review(uc, top_n=top_n) for uc in RISK_USE_CASES}


def target_risk_applicability(use_case: RiskUseCase) -> str:
    """The use case's own target risk's triage applicability
    ("high"/"medium"/"low"/"needs_scoping") — used to verify each scenario's
    factor_hints actually make its intended risk stand out, not just
    asserted."""

    _scope, triage_rows = build_scope_and_triage(use_case)
    by_key = {row.risk_key: row for row in triage_rows}
    return by_key[use_case.risk_key].applicability


def render_use_case_markdown(use_case: RiskUseCase, deliverable: DesignReviewDeliverable) -> str:
    lines: list[str] = [
        f"# วิธีคิด (Reasoning) — {use_case.system_name}",
        "",
        use_case.reasoning_th,
        "",
        "---",
        "",
        render_design_review_markdown(deliverable),
        "",
        "---",
        "",
        "## LLM synthesis prompt (ready to hand to a narrating LLM)",
        "",
        "```",
        build_design_review_synthesis_prompt(
            deliverable, original_question=use_case.original_question
        ),
        "```",
    ]
    return "\n".join(lines)


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    for use_case in RISK_USE_CASES:
        deliverable = build_design_review(use_case)
        markdown = render_use_case_markdown(use_case, deliverable)
        path = OUTPUT_DIR / f"{use_case.risk_key}.md"
        path.write_text(markdown, encoding="utf-8")
        applicability = target_risk_applicability(use_case)
        print(f"wrote {path} (target risk applicability: {applicability})")
    return 0


__all__ = [
    "PLAYBOOK_SCHEMA",
    "RiskUseCase",
    "RISK_USE_CASES",
    "get_use_case",
    "build_scope_and_triage",
    "build_design_review",
    "build_all_design_reviews",
    "target_risk_applicability",
    "render_use_case_markdown",
]


if __name__ == "__main__":
    raise SystemExit(main())
