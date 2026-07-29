"""Three end-to-end worked examples of the aivss_assessment_skills 5-skill
chain, applied to different AI-embedded banking systems for IT Internal
Audit:

1. mobile_banking_investment_advisor  — chat-based robo-advisor
2. fraud_detection_transaction_monitoring — real-time auto-block/freeze agent
3. credit_scoring_underwriting — document-reading loan approval agent

Each scenario below is built from a *fully scoped* factor_hints dict (all 10
AIVSS factors known) so triage_applicable_risks resolves straight to
high/medium/low instead of needs_scoping. In a real engagement, factor_hints
usually starts partial; the scoping_questions from generate_risk_questionnaire
are what you'd take into fieldwork to fill in the gaps.

Run directly to render and save all three deliverables as markdown under
./deliverables/:

    python3 "example AVISS/aivss_worked_examples.py"
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from aivss_assessment_skills import (
    AuditDeliverable,
    assemble_audit_deliverable,
    generate_risk_questionnaire,
    intake_assessment_scope,
    render_deliverable_markdown,
    score_finding,
    triage_applicable_risks,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "deliverables"


def _high_priority_keys(triage_rows) -> list[str]:
    return [row.risk_key for row in triage_rows if row.applicability == "high"]


def mobile_banking_investment_advisor() -> AuditDeliverable:
    scope = intake_assessment_scope(
        role="IT Internal Audit",
        system_name="Mobile Banking - AI Investment Advisory",
        ai_capability_summary=(
            "Chat-based robo-advisor embedded in the mobile banking app; "
            "reads customer KYC/suitability profile and portfolio data; "
            "can call a fund-switch/rebalance API with a one-tap confirm; "
            "backed by a third-party LLM."
        ),
        regulatory_context=[
            "SEC Thailand robo-advisor guideline",
            "BOT IT risk / third-party risk management",
            "PDPA",
        ],
        factor_hints={
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
        },
    )
    triage_rows = triage_applicable_risks(scope)
    sections = generate_risk_questionnaire(_high_priority_keys(triage_rows))
    finding = score_finding(
        risk_key="goal_instruction",
        finding_description=(
            "Prompt injection can steer the advisor into auto-submitting a "
            "portfolio shift to a higher-risk fund than the customer's "
            "suitability profile allows, with no human-confirmation gate."
        ),
        cvss_base=2.4,
        factor_levels=scope.factor_hints,
        threat_multiplier=0.97,  # proof-of-concept, found via red-team test
        mitigation_factor=1.00,  # no server-side confirmation gate yet
    )
    return assemble_audit_deliverable(
        scope=scope,
        triage_rows=triage_rows,
        questionnaire_sections=sections,
        scored_findings=[finding],
        output_id="audit_program",
    )


def fraud_detection_transaction_monitoring() -> AuditDeliverable:
    scope = intake_assessment_scope(
        role="IT Internal Audit",
        system_name="Digital Channel - Real-Time Fraud/Transaction Monitoring Agent",
        ai_capability_summary=(
            "Behavioral-analytics + ML scoring agent watching transaction "
            "streams; for high-confidence scores it can auto-freeze an "
            "account, auto-block a transaction, or force step-up "
            "authentication without waiting for analyst review; coordinates "
            "with a case-management/notification agent; retains a rolling "
            "behavioral baseline per customer."
        ),
        regulatory_context=[
            "BOT IT risk / fraud-management guideline",
            "PDPA (behavioral profiling)",
        ],
        factor_hints={
            "autonomy": 1.0,          # auto-freeze/auto-block for high-confidence cases
            "tools": 1.0,             # account-freeze / transaction-block / step-up-auth APIs
            "language": 0.0,          # event/stream-triggered, not NL-instructed
            "context": 1.0,           # device, geolocation, behavior, transaction history
            "non_determinism": 0.5,   # ML score drifts across model versions
            "opacity": 1.0,           # ML fraud score is not explainable in real time
            "persistence": 1.0,       # rolling per-customer behavioral baseline
            "identity": 0.0,          # does not assume different roles/personas
            "multi_agent": 0.5,       # partial coordination with case-management agent
            "self_mod": 0.0,          # no self-modifying config in the base case
        },
    )
    triage_rows = triage_applicable_risks(scope)
    sections = generate_risk_questionnaire(_high_priority_keys(triage_rows))
    finding = score_finding(
        risk_key="memory_context",
        finding_description=(
            "An adversary can deliberately shape a customer's transaction "
            "pattern over weeks to drift the behavioral baseline (memory/"
            "context poisoning), so a later genuinely fraudulent transaction "
            "scores as normal; the inverse — injected lookalike-noise across "
            "many accounts — can trigger a mass false-positive auto-freeze "
            "event against real customers."
        ),
        cvss_base=3.5,
        factor_levels=scope.factor_hints,
        threat_multiplier=0.50,  # unreported — found via internal red-team only
        mitigation_factor=0.83,  # partial: some drift monitoring exists, not fully validated
    )
    return assemble_audit_deliverable(
        scope=scope,
        triage_rows=triage_rows,
        questionnaire_sections=sections,
        scored_findings=[finding],
        output_id="audit_program",
    )


def credit_scoring_underwriting() -> AuditDeliverable:
    scope = intake_assessment_scope(
        role="IT Internal Audit",
        system_name="Digital Lending - AI Credit Scoring / Underwriting Agent",
        ai_capability_summary=(
            "Document-reading agent (OCR + LLM) extracts income evidence "
            "from bank statements/payslips and combines it with a numeric "
            "scorecard and an external credit-bureau lookup; below a small-"
            "loan threshold it auto-approves without human review, above it "
            "the recommendation goes to a human underwriter; retains "
            "applicant profile/documents across re-application attempts."
        ),
        regulatory_context=[
            "BOT lending / responsible-lending guideline",
            "Fair-lending / adverse-action disclosure expectations",
            "PDPA",
        ],
        factor_hints={
            "autonomy": 0.5,          # auto-approve only below a small-loan threshold
            "tools": 0.5,             # read-only external credit-bureau API call
            "language": 1.0,          # heavy NL/OCR document understanding
            "context": 1.0,           # applicant financial history + bureau + KYC
            "non_determinism": 0.5,
            "opacity": 1.0,           # LLM document reasoning layered on a scorecard
            "persistence": 1.0,       # retains applicant profile/documents across attempts
            "identity": 0.5,          # auto-decision disclosure to applicant is inconsistent
            "multi_agent": 0.0,       # single-agent pipeline
            "self_mod": 0.0,
        },
    )
    triage_rows = triage_applicable_risks(scope)
    sections = generate_risk_questionnaire(_high_priority_keys(triage_rows))
    finding = score_finding(
        risk_key="goal_instruction",
        finding_description=(
            "A forged bank statement PDF with adversarial text hidden in "
            "the document (e.g. white-on-white instructions targeting the "
            "LLM's document-reading step) can steer the agent into "
            "auto-approving a fast-track loan for an applicant with "
            "insufficient real income, with no human reviewer in that tier."
        ),
        cvss_base=3.1,
        factor_levels=scope.factor_hints,
        threat_multiplier=0.97,  # proof-of-concept, found via red-team test
        mitigation_factor=1.00,  # no adversarial-document validation yet
    )
    return assemble_audit_deliverable(
        scope=scope,
        triage_rows=triage_rows,
        questionnaire_sections=sections,
        scored_findings=[finding],
        output_id="audit_program",
    )


SCENARIOS = {
    "mobile_banking_investment_advisor": mobile_banking_investment_advisor,
    "fraud_detection_transaction_monitoring": fraud_detection_transaction_monitoring,
    "credit_scoring_underwriting": credit_scoring_underwriting,
}


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    for name, builder in SCENARIOS.items():
        deliverable = builder()
        markdown = render_deliverable_markdown(deliverable)
        path = OUTPUT_DIR / f"{name}.md"
        path.write_text(markdown, encoding="utf-8")
        high_risks = [r["name"] for r in deliverable.risks if r["applicability"] == "high"]
        print(f"wrote {path}")
        print(f"  high-priority risks: {', '.join(high_risks)}")
        for finding in deliverable.findings:
            print(
                f"  scored finding [{finding['risk_name']}]: "
                f"AIVSS {finding['aivss']} ({finding['severity']})"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
