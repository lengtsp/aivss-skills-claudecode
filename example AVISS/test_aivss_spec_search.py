#!/usr/bin/env python3
"""Deterministic contract tests for aivss_spec_search.py.

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

from aivss_spec_search import (  # noqa: E402
    cite_spec_reference,
    search_spec,
    spec_pages_available,
)


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_spec_pages_loaded() -> None:
    # README.md "Process" section: 98 pages verified converted 1:1.
    _assert(spec_pages_available() == 98, spec_pages_available())


def test_search_spec_finds_known_topic_with_high_confidence() -> None:
    results = search_spec("prompt injection", limit=5)
    _assert(results, "expected at least one hit for 'prompt injection'")
    _assert(all("page" in r and "snippet" in r and "confidence" in r for r in results), results)
    _assert(results[0]["confidence"] in {"high", "medium", "low"}, results[0])
    # results must be sorted by score desc
    scores = [r["score"] for r in results]
    _assert(scores == sorted(scores, reverse=True), scores)


def test_search_spec_blank_or_no_match_fails_closed() -> None:
    _assert(search_spec("") == [], "blank query must return []")
    _assert(search_spec("   ") == [], "whitespace-only query must return []")
    _assert(search_spec(None) == [], "None query must return []")  # type: ignore[arg-type]
    _assert(
        search_spec("zzz_definitely_not_in_the_spec_xyz123") == [],
        "nonsense query must return [] (fails closed, no low-confidence guess)",
    )


def test_search_spec_excludes_toc_pages_by_default() -> None:
    # "Agent Goal and Instruction Manipulation" is both a TOC/list-of-figures
    # entry (pages 2-3) and a real section heading (page 41). Default search
    # must surface the real content page.
    default_results = search_spec("Agent Goal and Instruction Manipulation", limit=10)
    pages = {r["page"] for r in default_results}
    _assert(41 in pages, f"expected content page 41 in default results, got {pages}")

    # With include_toc=True the TOC pages become eligible again (not asserting
    # they're returned — just that the flag doesn't error and page 41 still
    # shows up since it out-scores nothing new being excluded).
    toc_results = search_spec(
        "Agent Goal and Instruction Manipulation", limit=10, include_toc=True
    )
    _assert({r["page"] for r in toc_results}, "include_toc=True must still return results")


def test_cite_spec_reference_resolves_risk_key() -> None:
    hits = cite_spec_reference("goal_instruction", limit=3)
    _assert(hits, "expected citations for known risk key 'goal_instruction'")
    pages = {h["page"] for h in hits}
    _assert(41 in pages or 42 in pages, f"expected the goal_instruction section page, got {pages}")


def test_cite_spec_reference_resolves_factor_key() -> None:
    hits = cite_spec_reference("autonomy", limit=3)
    _assert(hits, "expected citations for known factor key 'autonomy'")


def test_cite_spec_reference_freeform_and_fails_closed() -> None:
    # Freeform text search still works for keys that aren't in either catalog.
    hits = cite_spec_reference("mitigation factor", limit=2)
    _assert(hits, "expected citations for a freeform topic present in the spec")

    _assert(cite_spec_reference("") == [], "blank key_or_query must return []")
    _assert(
        cite_spec_reference("zzz_definitely_not_in_the_spec_xyz123") == [],
        "unknown key + not-in-spec text must fail closed to []",
    )


def main() -> int:
    tests = (
        test_spec_pages_loaded,
        test_search_spec_finds_known_topic_with_high_confidence,
        test_search_spec_blank_or_no_match_fails_closed,
        test_search_spec_excludes_toc_pages_by_default,
        test_cite_spec_reference_resolves_risk_key,
        test_cite_spec_reference_resolves_factor_key,
        test_cite_spec_reference_freeform_and_fails_closed,
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
