"""Threat-intel / news triage against the 10 AIVSS core risks, per
`SKILLS_ROADMAP.md` idea #4 ("ประเมินข่าว/สารแจ้งเตือนภัยคุกคาม AI").

Deterministic keyword classifier — no LLM call, same family as the
`_TYPE_KEYWORDS` fallback classifier already used in the main app's
`knowledge_graph.py` and this folder's own `aivss_banking_taxonomy.py`. Does
not fetch news itself (the main app already has a Tavily web-search fallback
skill in `rag_skills.py`, out of scope here) — this is the "map already-
fetched alert/advisory text to AIVSS" layer, decoupled from how the text was
sourced.

THREAT_ALERT_KEYWORDS below is a Codex-curated attack-pattern vocabulary per
risk, grounded against the actual "KEY RISKS" manifestation bullets read from
the OCR'd spec pages during authoring (2026-07-28) — e.g. "tool squatting",
"MCP" for tool_misuse (pages 8-9); "confused deputy", "role inheritance" for
access_control (pages 11-12); "prompt injection", "indirect instruction
injection" for goal_instruction (pages 41-43). It is not exhaustive and will
drift as new attack techniques are published — see SKILLS_ROADMAP.md idea #6
(spec-version tracking) for the general problem of catalog drift.

**Semantic fallback (2026-07-28), added after a live test found a real gap:**
a genuine, on-topic alert paraphrased in different words than the curated
list ("a log-injection technique that tricks autonomous SOAR/EDR response
agents into auto-isolating legitimate hosts...") scored 0 against
`THREAT_ALERT_KEYWORDS` and returned `None`, even though the same text
scored strongly (8) against page 41 of the OCR'd spec via
`aivss_spec_search.search_spec()` — page 41 is exactly the first page of the
`goal_instruction` risk's own section (verified: `RISK_DEFINITIONS[...]
["start_page"/"end_page"]` in `aivss_kg.py` gives each risk's authoritative
page range). `_semantic_risk_candidates()` below reuses that same full-text
search — already built, already tested — as a second, explicitly weaker tier:
when the curated keyword list finds nothing (or as extra risks alongside it),
map each matching spec page back to the risk whose section contains it, and
surface that as a `semantic_candidates` list with confidence `"possible"` —
never blended into the keyword tier's `matches`/`score` numbers, since the
two scoring scales aren't comparable (keyword score = distinct phrase count,
1-5ish; spec-search score = token-overlap count, can run higher) and forcing
them into one ranked list would produce a false sense of precision.
"""

from __future__ import annotations

from typing import Any

from aivss_internal_audit import AUDIT_TOPICS
from aivss_kg import RISK_DEFINITIONS
from aivss_spec_search import search_spec

THREAT_INTEL_SCHEMA = "rag.aivss-threat-intel-triage.v1"

THREAT_ALERT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "tool_misuse": (
        "tool squatting", "tool poisoning", "mcp server", "model context protocol",
        "malicious code execution", "kill switch", "tool metadata", "semantic tool hijacking",
        "compromised tool", "rogue trading agent", "tool discovery",
    ),
    "access_control": (
        "permission escalation", "privilege escalation", "role inheritance",
        "confused deputy", "credential mismanagement", "control-flow hijacking",
        "shadow identity bridging", "orphaned account", "forged role", "token mismanagement",
    ),
    "cascading_failures": (
        "cascading failure", "harmful collaboration", "cross-system exploitation",
        "lateral movement", "saas-to-saas", "data poisoning", "hallucination propagation",
        "blast radius", "impact amplification",
    ),
    "orchestration": (
        "inter-agent communication", "shared knowledge poisoning", "trust relationship abuse",
        "coordination protocol", "session fixation", "replay attack", "capability drift",
        "rogue autonomy", "agent-to-agent", "a2a protocol",
    ),
    "identity_impersonation": (
        "agent impersonation", "human impersonation", "misleading agent card",
        "shared identity pool", "deepfake", "unauthorized cloning", "identity spoofing",
        "voice clone", "agent card",
    ),
    "memory_context": (
        "context manipulation", "memory manipulation", "context amnesia",
        "cross-session data leakage", "cross-user memory contamination",
        "residual memory", "context drift", "memory poisoning",
    ),
    "critical_systems": (
        "physical system manipulation", "iot device compromise", "server-side request forgery",
        "ssrf", "ci/cd pipeline tampering", "critical infrastructure", "direct critical system access",
        "operational override",
    ),
    "supply_chain": (
        "model registry", "development chain attack", "deployment systems attack",
        "dependency exploitation", "malicious mcp server dependency", "saas marketplace hijack",
        "trust chain propagation", "supply chain", "sbom", "typosquat",
    ),
    "untraceability": (
        "log tampering", "log poisoning", "chain-of-action", "repudiation",
        "forensic evasion", "explainability artifact poisoning", "audit trail gap",
        "correlation id",
    ),
    "goal_instruction": (
        "prompt injection", "jailbreak", "semantic ambiguity", "goal hijacking",
        "instruction injection", "indirect instruction injection", "dynamic goal steering",
        "goal looping", "resource exhaustion", "model poisoning",
    ),
}

_RISK_KEY_LABEL: dict[str, str] = {
    "tool_misuse": "Agentic AI Tool Misuse",
    "access_control": "Agent Access Control Violation",
    "cascading_failures": "Agent Cascading Failures",
    "orchestration": "Agent Orchestration and Multi-Agent Exploitation",
    "identity_impersonation": "Agent Identity Impersonation",
    "memory_context": "Agent Memory and Context Manipulation",
    "critical_systems": "Insecure Agent Critical Systems Interaction",
    "supply_chain": "Agent Supply Chain and Dependency Risk",
    "untraceability": "Agent Untraceability",
    "goal_instruction": "Agent Goal and Instruction Manipulation",
}


def _topics_for_risk(risk_key: str) -> tuple[dict[str, Any], ...]:
    return tuple(topic for topic in AUDIT_TOPICS if risk_key in topic["risk_keys"])


def _confidence_for_score(score: int) -> str:
    if score >= 3:
        return "high"
    if score == 2:
        return "medium"
    return "low"


# Half-open [start_page, end_page) ranges — authoritative, from aivss_kg.py's
# own RISK_DEFINITIONS, not re-derived or guessed here.
_PAGE_RISK_RANGES: tuple[tuple[int, int, str], ...] = tuple(
    (row["start_page"], row["end_page"], row["key"])
    for row in RISK_DEFINITIONS
    if row.get("start_page") is not None and row.get("end_page") is not None
)

SEMANTIC_FALLBACK_MIN_SCORE = 6  # search_spec score; verified during authoring
# against unrelated prose (max observed score 2) vs a genuine paraphrased
# threat matching the wrong-risk's own spec section (score 8) — see module
# docstring "Semantic fallback".


def _page_to_risk_key(page: int) -> str | None:
    for start, end, key in _PAGE_RISK_RANGES:
        if start <= page < end:
            return key
    return None


def _semantic_risk_candidates(
    alert_text: str, *, search_limit: int = 8, min_score: int = SEMANTIC_FALLBACK_MIN_SCORE
) -> dict[str, dict[str, Any]]:
    """Full-text search the alert against the OCR'd spec pages (reusing
    aivss_spec_search.search_spec, not a new search engine), then map each
    matching page back to the risk whose section it belongs to. Keeps only
    each risk's single best-scoring page. Returns {} below min_score — same
    fail-closed discipline as everything else in this folder."""

    candidates: dict[str, dict[str, Any]] = {}
    for hit in search_spec(alert_text, limit=search_limit):
        if hit["score"] < min_score:
            continue
        risk_key = _page_to_risk_key(hit["page"])
        if risk_key is None:
            continue
        existing = candidates.get(risk_key)
        if existing is None or hit["score"] > existing["spec_score"]:
            candidates[risk_key] = {
                "risk_key": risk_key,
                "spec_page": hit["page"],
                "spec_score": hit["score"],
                "snippet": hit["snippet"],
            }
    return candidates


def triage_threat_alert(
    alert_text: str,
    *,
    limit: int = 3,
    include_semantic_fallback: bool = True,
    semantic_min_score: int = SEMANTIC_FALLBACK_MIN_SCORE,
) -> dict[str, Any] | None:
    """Map an already-fetched threat/news/advisory text to the AIVSS risks it
    most plausibly concerns.

    Score per risk = count of distinct THREAT_ALERT_KEYWORDS matched
    (case-insensitive substring). An alert can plausibly touch more than one
    risk (unlike aivss_banking_taxonomy.classify_banking_system's single best
    match), so this returns every risk with score > 0, ranked, capped at
    `limit`. Each match carries its own confidence band (see
    _confidence_for_score) rather than one aggregate label, since a multi-risk
    alert can be sure about one risk and marginal about another. This
    keyword tier's shape/behavior is unchanged from before the semantic
    fallback was added — same scores, same ranking, same confidence bands.

    `include_semantic_fallback` (default True) adds a second, explicitly
    weaker signal: `_semantic_risk_candidates()` full-text searches the alert
    against the OCR'd spec and maps matching pages back to risks, for risks
    the keyword tier didn't already find. These appear in the separate
    `semantic_candidates` key, confidence `"possible"` — never merged into
    `matches`/`matched_risk_keys`/`score`, since the two tiers' scores aren't
    on the same scale (see module docstring "Semantic fallback").

    Fails closed: returns None for blank text, or when NEITHER tier finds
    anything — never a guessed risk mapping.
    """

    raw_text = str(alert_text or "").strip()
    if not raw_text:
        return None
    text = raw_text.casefold()

    scored: list[tuple[int, str, tuple[str, ...]]] = []
    for risk_key, keywords in THREAT_ALERT_KEYWORDS.items():
        matched = tuple(kw for kw in keywords if kw in text)
        if matched:
            scored.append((len(matched), risk_key, matched))
    scored.sort(key=lambda row: (-row[0], row[1]))
    top = scored[: max(1, int(limit))]

    matches: list[dict[str, Any]] = []
    for score, risk_key, matched_keywords in top:
        topics = _topics_for_risk(risk_key)
        matches.append(
            {
                "risk_key": risk_key,
                "risk_name": _RISK_KEY_LABEL.get(risk_key, risk_key),
                "score": score,
                "confidence": _confidence_for_score(score),
                "matched_keywords": list(matched_keywords),
                "audit_topic_ids": [t["id"] for t in topics],
                "cobit_codes": sorted({code for t in topics for code in t["cobit_codes"]}),
            }
        )

    semantic_candidates: list[dict[str, Any]] = []
    if include_semantic_fallback:
        keyword_risk_keys = {row[1] for row in scored}
        candidates = _semantic_risk_candidates(raw_text, min_score=semantic_min_score)
        for risk_key, hit in candidates.items():
            if risk_key in keyword_risk_keys:
                continue
            topics = _topics_for_risk(risk_key)
            semantic_candidates.append(
                {
                    "risk_key": risk_key,
                    "risk_name": _RISK_KEY_LABEL.get(risk_key, risk_key),
                    "confidence": "possible",
                    "spec_page": hit["spec_page"],
                    "spec_score": hit["spec_score"],
                    "snippet": hit["snippet"],
                    "audit_topic_ids": [t["id"] for t in topics],
                    "cobit_codes": sorted({code for t in topics for code in t["cobit_codes"]}),
                }
            )
        semantic_candidates.sort(key=lambda row: (-row["spec_score"], row["risk_key"]))
        semantic_candidates = semantic_candidates[: max(1, int(limit))]

    if not matches and not semantic_candidates:
        return None

    return {
        "schema": THREAT_INTEL_SCHEMA,
        "matched_risk_keys": [m["risk_key"] for m in matches],
        "overall_confidence": matches[0]["confidence"] if matches else "possible",
        "matches": matches,
        "semantic_candidates": semantic_candidates,
    }


__all__ = [
    "THREAT_INTEL_SCHEMA",
    "THREAT_ALERT_KEYWORDS",
    "triage_threat_alert",
]
