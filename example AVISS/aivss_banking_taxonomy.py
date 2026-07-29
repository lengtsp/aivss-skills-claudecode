"""Banking-system archetype taxonomy — a reference/knowledge asset for
`aivss_assessment_skills.intake_assessment_scope` (skill 1), per
`SKILLS_ROADMAP.md` idea #3 ("การจำแนกระบบงานธนาคาร").

Not a duplicate data source: `default_factor_hints` for the three shared
archetypes (`robo_advisor`, `fraud_transaction_monitoring`,
`credit_scoring_underwriting`) are pulled directly from
`aivss_worked_examples.py`'s existing regression-tested scenarios, so this
taxonomy formalizes what's already validated by
`test_aivss_assessment_skills.py`, rather than inventing new characteristics.

Unlike a worked example (fully scoped, all 10 AIVSS factors, for one
specific engagement), each archetype here only carries the 3-4 factors that
are true *by definition of the system type itself* (e.g. a robo-advisor is
inherently language-driven). The rest is deliberately left unscoped — a
partial `factor_hints` dict is valid input to `intake_assessment_scope`, and
drives `needs_scoping` rows in `triage_applicable_risks`. This module gives
an auditor a realistic starting point, not a completed scope.

`classify_banking_system()` is a deterministic keyword-count classifier —
no LLM call, fails closed (returns None on no match) — consistent with the
rest of this folder's "never guess" convention.
"""

from __future__ import annotations

from dataclasses import dataclass

from aivss_kg import FACTOR_DEFINITIONS

_VALID_FACTOR_KEYS = frozenset(row["key"] for row in FACTOR_DEFINITIONS)


@dataclass(frozen=True)
class BankingSystemArchetype:
    key: str
    label: str
    description: str
    keywords: tuple[str, ...]
    default_factor_hints: dict[str, float]
    default_regulatory_context: tuple[str, ...]

    def __post_init__(self) -> None:
        unknown = set(self.default_factor_hints) - _VALID_FACTOR_KEYS
        if unknown:
            raise ValueError(f"{self.key}: unknown factor keys {sorted(unknown)}")
        for value in self.default_factor_hints.values():
            if value not in (0.0, 0.5, 1.0):
                raise ValueError(f"{self.key}: factor levels must be 0/0.5/1, got {value!r}")


BANKING_SYSTEM_ARCHETYPES: tuple[BankingSystemArchetype, ...] = (
    BankingSystemArchetype(
        key="robo_advisor",
        label="Chat-based Robo-Advisor / Investment Advisory",
        description=(
            "Chat-based investment advisory agent embedded in a banking app; "
            "reads customer KYC/suitability profile and can call a "
            "fund-switch/rebalance API, typically with a low-friction "
            "one-tap confirm."
        ),
        keywords=(
            "robo-advisor", "robo advisor", "roboadvisor", "investment advisory",
            "investment advisor", "portfolio advisory", "fund-switch", "fund switch",
            "rebalance", "ที่ปรึกษาการลงทุน", "หุ่นยนต์ที่ปรึกษา",
        ),
        default_factor_hints={"language": 1.0, "tools": 1.0, "autonomy": 1.0},
        default_regulatory_context=(
            "SEC Thailand robo-advisor guideline",
            "BOT IT risk / third-party risk management",
            "PDPA",
        ),
    ),
    BankingSystemArchetype(
        key="fraud_transaction_monitoring",
        label="Real-Time Fraud / Transaction Monitoring Agent",
        description=(
            "Behavioral-analytics + ML scoring agent watching transaction "
            "streams; can auto-freeze accounts, auto-block transactions, or "
            "force step-up authentication for high-confidence scores without "
            "waiting for analyst review; retains a rolling behavioral "
            "baseline per customer."
        ),
        keywords=(
            "fraud", "transaction monitoring", "auto-freeze", "auto freeze",
            "auto-block", "auto block", "behavioral-analytics", "behavioral analytics",
            "step-up authentication", "ตรวจจับการทุจริต", "ทุจริต",
        ),
        default_factor_hints={"language": 0.0, "tools": 1.0, "autonomy": 1.0, "persistence": 1.0},
        default_regulatory_context=(
            "BOT IT risk / fraud-management guideline",
            "PDPA (behavioral profiling)",
        ),
    ),
    BankingSystemArchetype(
        key="credit_scoring_underwriting",
        label="AI Credit Scoring / Underwriting Agent",
        description=(
            "Document-reading agent (OCR + LLM) extracts income evidence from "
            "bank statements/payslips, combines it with a numeric scorecard "
            "and an external credit-bureau lookup; may auto-approve below a "
            "small-loan threshold; retains applicant profile/documents across "
            "re-application attempts."
        ),
        keywords=(
            "credit scoring", "underwriting", "loan approval", "lending",
            "bank statement", "payslip", "credit bureau", "credit-bureau",
            "สินเชื่อ", "การพิจารณาสินเชื่อ",
        ),
        default_factor_hints={"language": 1.0, "tools": 0.5, "persistence": 1.0},
        default_regulatory_context=(
            "BOT lending / responsible-lending guideline",
            "Fair-lending / adverse-action disclosure expectations",
            "PDPA",
        ),
    ),
    BankingSystemArchetype(
        key="kyc_onboarding_chatbot",
        label="KYC / Customer Onboarding Chatbot",
        description=(
            "Chat-based onboarding agent that collects identity documents, "
            "runs identity verification / liveness checks, and performs "
            "customer due diligence before account opening."
        ),
        keywords=(
            "kyc", "onboarding", "customer due diligence", "cdd",
            "identity verification", "liveness", "account opening",
            "เปิดบัญชี", "ยืนยันตัวตน", "รู้จักลูกค้า",
        ),
        default_factor_hints={"language": 1.0, "tools": 0.5, "persistence": 0.5},
        default_regulatory_context=(
            "BOT KYC/CDD guideline",
            "AMLO customer due diligence",
            "PDPA",
        ),
    ),
    BankingSystemArchetype(
        key="collections_recovery_agent",
        label="Collections / Debt Recovery Agent",
        description=(
            "Agent that contacts delinquent customers, negotiates payment "
            "plans or settlements, and tracks promises-to-pay and contact "
            "history across a recovery case."
        ),
        keywords=(
            "collections", "debt recovery", "settlement", "payment plan",
            "delinquent", "ทวงหนี้", "เร่งรัดหนี้สิน", "หนี้ค้างชำระ",
        ),
        default_factor_hints={"language": 1.0, "autonomy": 0.5, "persistence": 1.0},
        default_regulatory_context=(
            "BOT debt collection / fair-treatment-of-customers guideline",
            "PDPA",
        ),
    ),
)

_ARCHETYPE_BY_KEY: dict[str, BankingSystemArchetype] = {
    archetype.key: archetype for archetype in BANKING_SYSTEM_ARCHETYPES
}


def get_archetype(key: str) -> BankingSystemArchetype | None:
    return _ARCHETYPE_BY_KEY.get(str(key).strip())


def classify_banking_system(text: str) -> str | None:
    """Deterministic keyword-count classifier — no LLM call.

    Returns the archetype key with the most case-insensitive keyword
    substring matches in `text`, ties broken by declaration order in
    BANKING_SYSTEM_ARCHETYPES. Returns None if no archetype has any match —
    fails closed, never guesses.
    """

    source = str(text or "").casefold()
    if not source.strip():
        return None

    best_key: str | None = None
    best_score = 0
    for archetype in BANKING_SYSTEM_ARCHETYPES:
        score = sum(1 for keyword in archetype.keywords if keyword.casefold() in source)
        if score > best_score:
            best_score = score
            best_key = archetype.key
    return best_key


__all__ = [
    "BankingSystemArchetype",
    "BANKING_SYSTEM_ARCHETYPES",
    "get_archetype",
    "classify_banking_system",
]
