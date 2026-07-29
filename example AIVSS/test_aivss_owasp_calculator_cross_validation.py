#!/usr/bin/env python3
"""External cross-validation of `aivss_kg.calculate_aivss()` against the
live "AIVSS Calculator" at https://aivss.parthsohaney.online/calculator
(linked from the official OWASP AIVSS homepage as "🚀 Try the AIVSS
Calculator Demo") — a community-built, independent implementation of the
same v0.8 formula, not this folder's own code.

Unlike every other test in this folder (self-consistency against this
folder's own skills), this one is external ground truth: real browser
automation (Playwright, 2026-07-28) loaded all 10 official "Load OWASP
Scenario" presets on the live calculator — Sections 3.6.1-3.6.10 of the
v0.8 PDF ("Agentic AI Risk Scoring for OWASP Agentic AI Core") — read back
the exact CVSS Base and all 10 agent-factor levels the site set for each
scenario (confirmed via a full-page screenshot for one scenario before
trusting the CSS-class-based read for the rest — see README.md "Live
calculator comparison"), and recorded the site's own displayed AIVSS Score
and Agentic Uplift. Threat Multiplier (0.97, Proof-of-Concept) and
Mitigation Factor (1.00, No/Weak) were left at default for every scenario —
confirmed unchanged from default in each read.

All 10 scenarios matched this folder's `calculate_aivss()` output exactly
when authored (2026-07-28). If this test ever fails, it means either this
folder's formula implementation drifted from the v0.8 spec, or the
reference calculator changed its own formula/scenario data — either way,
worth investigating rather than silently accepting, which is why this is
pinned as a hard regression test rather than left as a one-off finding in
README.md alone.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aivss_kg import calculate_aivss  # noqa: E402


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


# (risk_key, scenario_label, cvss_base, factor_levels, site_aivss_score, site_agentic_uplift)
# factor_levels keys match aivss_kg.FACTOR_DEFINITIONS keys exactly.
OWASP_CALCULATOR_SCENARIOS: tuple[tuple[str, str, float, dict[str, float], float, float], ...] = (
    (
        "tool_misuse", "1. Agentic AI Tool Misuse", 9.4,
        {"autonomy": 1, "tools": 1, "language": 1, "context": 1, "non_determinism": 1,
         "opacity": 1, "persistence": 0.5, "identity": 1, "multi_agent": 1, "self_mod": 0.5},
        9.9, 0.5,
    ),
    (
        "access_control", "2. Agent Access Control Violation", 8.7,
        {"autonomy": 1, "tools": 1, "language": 1, "context": 1, "non_determinism": 0.5,
         "opacity": 1, "persistence": 1, "identity": 1, "multi_agent": 0.5, "self_mod": 0},
        9.7, 1.0,
    ),
    (
        "cascading_failures", "3. Agent Cascading Failures", 7.1,
        {"autonomy": 1, "tools": 0.5, "language": 1, "context": 1, "non_determinism": 1,
         "opacity": 1, "persistence": 0.5, "identity": 0.5, "multi_agent": 1, "self_mod": 0.5},
        9.4, 2.3,
    ),
    (
        "orchestration", "4. Agent Orchestration and Multi-Agent Exploitation", 9.4,
        {"autonomy": 1, "tools": 1, "language": 1, "context": 1, "non_determinism": 1,
         "opacity": 1, "persistence": 1, "identity": 1, "multi_agent": 1, "self_mod": 0.5},
        10.0, 0.6,
    ),
    (
        "identity_impersonation", "5. Agent Identity Impersonation", 7.4,
        {"autonomy": 1, "tools": 1, "language": 1, "context": 1, "non_determinism": 1,
         "opacity": 1, "persistence": 0, "identity": 1, "multi_agent": 0.5, "self_mod": 0},
        9.3, 1.9,
    ),
    (
        "memory_context", "6. Agent Memory and Context Manipulation", 5.8,
        {"autonomy": 1, "tools": 0.5, "language": 1, "context": 1, "non_determinism": 0.5,
         "opacity": 1, "persistence": 1, "identity": 0, "multi_agent": 0.5, "self_mod": 1},
        8.9, 3.1,
    ),
    (
        "critical_systems", "7. Insecure Agent Critical Systems Interaction", 6.9,
        {"autonomy": 1, "tools": 1, "language": 0.5, "context": 1, "non_determinism": 0.5,
         "opacity": 1, "persistence": 0.5, "identity": 0, "multi_agent": 1, "self_mod": 1},
        9.2, 2.3,
    ),
    (
        "supply_chain", "8. Agent Supply Chain and Dependency Risk", 9.3,
        {"autonomy": 1, "tools": 1, "language": 0, "context": 0, "non_determinism": 1,
         "opacity": 1, "persistence": 0.5, "identity": 1, "multi_agent": 1, "self_mod": 0},
        9.7, 0.4,
    ),
    (
        "untraceability", "9. Agent Untraceability", 5.3,
        {"autonomy": 1, "tools": 1, "language": 0, "context": 0, "non_determinism": 1,
         "opacity": 1, "persistence": 0.5, "identity": 0.5, "multi_agent": 1, "self_mod": 0.5},
        8.3, 3.0,
    ),
    (
        "goal_instruction", "10. Agent Goal and Instruction Manipulation", 2.1,
        {"autonomy": 0.5, "tools": 0, "language": 1, "context": 1, "non_determinism": 1,
         "opacity": 1, "persistence": 1, "identity": 0, "multi_agent": 0, "self_mod": 1},
        7.1, 5.0,
    ),
)


def test_all_ten_scenarios_present_and_cover_every_risk() -> None:
    _assert(len(OWASP_CALCULATOR_SCENARIOS) == 10, len(OWASP_CALCULATOR_SCENARIOS))
    from aivss_kg import RISK_DEFINITIONS

    expected_keys = {row["key"] for row in RISK_DEFINITIONS}
    actual_keys = {row[0] for row in OWASP_CALCULATOR_SCENARIOS}
    _assert(actual_keys == expected_keys, (actual_keys, expected_keys))


def test_each_scenario_matches_live_calculator_exactly() -> None:
    mismatches: list[str] = []
    for risk_key, label, cvss_base, factors, site_aivss, site_uplift in OWASP_CALCULATOR_SCENARIOS:
        result = calculate_aivss(
            cvss_base=cvss_base,
            factors=factors,
            threat_multiplier=0.97,
            mitigation_factor=1.00,
        )
        my_aivss = result["aivss"]
        my_uplift = round(result["aars"], 1)
        if abs(my_aivss - site_aivss) >= 0.05 or abs(my_uplift - site_uplift) >= 0.05:
            mismatches.append(
                f"{label} ({risk_key}): mine aivss={my_aivss} uplift={my_uplift} "
                f"vs site aivss={site_aivss} uplift={site_uplift}"
            )
    _assert(not mismatches, "\n".join(mismatches))


def test_factor_sums_are_internally_consistent_with_raw_calculation() -> None:
    # Sanity check independent of the site: factor_sum reported by
    # calculate_aivss() must equal the plain sum of the factor dict passed
    # in (catches a copy-paste transcription error in this test file itself
    # more than it catches a real bug in aivss_kg.py).
    for risk_key, label, cvss_base, factors, _site_aivss, _site_uplift in OWASP_CALCULATOR_SCENARIOS:
        result = calculate_aivss(cvss_base=cvss_base, factors=factors, threat_multiplier=0.97, mitigation_factor=1.00)
        expected_sum = sum(factors.values())
        _assert(
            abs(result["factor_sum"] - expected_sum) < 1e-9,
            (label, result["factor_sum"], expected_sum),
        )


def main() -> int:
    tests = (
        test_all_ten_scenarios_present_and_cover_every_risk,
        test_each_scenario_matches_live_calculator_exactly,
        test_factor_sums_are_internally_consistent_with_raw_calculation,
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
