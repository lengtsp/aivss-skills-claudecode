#!/usr/bin/env python3
"""Deterministic contract tests for aivss_threat_intel.py.

Same no-pytest, self-contained-runner convention as
test_aivss_assessment_skills.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aivss_kg import RISK_DEFINITIONS  # noqa: E402
from aivss_threat_intel import THREAT_ALERT_KEYWORDS, triage_threat_alert  # noqa: E402


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_keyword_coverage_matches_all_ten_risks() -> None:
    risk_keys = {r["key"] for r in RISK_DEFINITIONS}
    _assert(set(THREAT_ALERT_KEYWORDS.keys()) == risk_keys, THREAT_ALERT_KEYWORDS.keys())
    for key, keywords in THREAT_ALERT_KEYWORDS.items():
        _assert(len(keywords) >= 5, f"{key} has too few keywords ({len(keywords)})")


def test_triage_single_risk_medium_confidence() -> None:
    alert = "A new report describes prompt injection and jailbreak techniques against LLM agents."
    result = triage_threat_alert(alert)
    _assert(result is not None, "expected a match")
    _assert(result["matched_risk_keys"][0] == "goal_instruction", result["matched_risk_keys"])
    top = result["matches"][0]
    _assert(top["score"] == 2, top)
    _assert(top["confidence"] == "medium", top)
    _assert(set(top["matched_keywords"]) == {"prompt injection", "jailbreak"}, top)
    _assert(top["audit_topic_ids"], "expected at least one audit topic id")
    _assert(top["cobit_codes"], "expected at least one COBIT code")


def test_triage_high_confidence_needs_three_keyword_hits() -> None:
    alert = (
        "Attackers used prompt injection combined with indirect instruction injection and "
        "resource exhaustion via goal looping to disrupt the agent."
    )
    result = triage_threat_alert(alert)
    _assert(result is not None, "expected a match")
    top = result["matches"][0]
    _assert(top["risk_key"] == "goal_instruction", top)
    _assert(top["score"] >= 3, top)
    _assert(top["confidence"] == "high", top)


def test_triage_can_match_multiple_risks_ranked_by_score() -> None:
    alert = (
        "The advisory covers tool poisoning and MCP server abuse (tool misuse), plus "
        "prompt injection and jailbreak attempts to hijack agent goals (goal manipulation)."
    )
    result = triage_threat_alert(alert, limit=5)
    _assert(result is not None, "expected matches")
    _assert(set(result["matched_risk_keys"]) >= {"tool_misuse", "goal_instruction"}, result)
    scores = [m["score"] for m in result["matches"]]
    _assert(scores == sorted(scores, reverse=True), scores)


def test_triage_limit_truncates_results() -> None:
    alert = (
        "tool squatting mcp server; permission escalation role inheritance; "
        "cascading failure lateral movement; prompt injection jailbreak"
    )
    result = triage_threat_alert(alert, limit=2)
    _assert(result is not None, "expected matches")
    _assert(len(result["matches"]) <= 2, result["matches"])


def test_triage_fails_closed_on_no_match_blank_or_none() -> None:
    _assert(triage_threat_alert("the weather is nice today") is None, "unrelated prose")
    _assert(triage_threat_alert("") is None, "empty string")
    _assert(triage_threat_alert("   ") is None, "whitespace only")
    _assert(triage_threat_alert(None) is None, "None input")  # type: ignore[arg-type]


def test_semantic_fallback_catches_paraphrased_alert_keyword_tier_misses() -> None:
    # This exact alert scored 0 against THREAT_ALERT_KEYWORDS before the
    # semantic fallback was added (2026-07-28), discovered during a live
    # MCP test — same wording that motivated the fix, kept as a regression
    # test.
    alert = (
        "Researchers disclosed a log-injection technique that tricks autonomous "
        "SOAR/EDR response agents into auto-isolating legitimate hosts via crafted "
        "alert text, effectively a denial-of-service against IT operations."
    )
    result = triage_threat_alert(alert)
    _assert(result is not None, "expected the semantic fallback to find something")
    _assert(result["matches"] == [], "keyword tier must find nothing for this exact phrasing")
    _assert(result["matched_risk_keys"] == [], result["matched_risk_keys"])
    _assert(result["overall_confidence"] == "possible", result)
    _assert(result["semantic_candidates"], "expected semantic candidates")
    top = result["semantic_candidates"][0]
    _assert(top["risk_key"] == "goal_instruction", result["semantic_candidates"])
    _assert(top["confidence"] == "possible", top)
    _assert(top["spec_page"] == 41, top)
    _assert(top["audit_topic_ids"], "expected audit topic ids")
    _assert(top["cobit_codes"], "expected COBIT codes")


def test_semantic_fallback_never_duplicates_a_keyword_tier_risk() -> None:
    alert = "A new report describes prompt injection and jailbreak techniques against LLM agents."
    result = triage_threat_alert(alert)
    _assert(result is not None, "expected a match")
    _assert(result["matched_risk_keys"] == ["goal_instruction"], result["matched_risk_keys"])
    semantic_keys = {row["risk_key"] for row in result["semantic_candidates"]}
    _assert("goal_instruction" not in semantic_keys, "must not duplicate a risk already in matches")


def test_semantic_fallback_can_be_disabled() -> None:
    alert = (
        "Researchers disclosed a log-injection technique that tricks autonomous "
        "SOAR/EDR response agents into auto-isolating legitimate hosts."
    )
    result = triage_threat_alert(alert, include_semantic_fallback=False)
    _assert(result is None, "with the fallback disabled, this alert must fail closed like before")


def test_semantic_fallback_still_fails_closed_on_unrelated_prose() -> None:
    # Same unrelated-prose case as above, but explicitly re-verified with the
    # semantic tier active (it's on by default) — a low search_spec score
    # (max observed 2, see aivss_threat_intel.py's SEMANTIC_FALLBACK_MIN_SCORE
    # comment) must not clear the min_score=6 threshold.
    _assert(triage_threat_alert("the weather is nice today") is None, "unrelated prose")
    _assert(
        triage_threat_alert("my cat likes to sleep on the couch every afternoon") is None,
        "unrelated prose 2",
    )


def main() -> int:
    tests = (
        test_keyword_coverage_matches_all_ten_risks,
        test_triage_single_risk_medium_confidence,
        test_triage_high_confidence_needs_three_keyword_hits,
        test_triage_can_match_multiple_risks_ranked_by_score,
        test_triage_limit_truncates_results,
        test_triage_fails_closed_on_no_match_blank_or_none,
        test_semantic_fallback_catches_paraphrased_alert_keyword_tier_misses,
        test_semantic_fallback_never_duplicates_a_keyword_tier_risk,
        test_semantic_fallback_can_be_disabled,
        test_semantic_fallback_still_fails_closed_on_unrelated_prose,
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
