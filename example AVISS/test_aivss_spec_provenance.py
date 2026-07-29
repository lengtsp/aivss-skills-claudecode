#!/usr/bin/env python3
"""Deterministic contract tests for aivss_spec_provenance.py.

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

from aivss_kg import FACTOR_DEFINITIONS, RISK_DEFINITIONS  # noqa: E402
from aivss_spec_provenance import (  # noqa: E402
    SPEC_PINNED_PAGE_COUNT,
    SPEC_PUBLISHED_DATE,
    catalog_provenance_report,
    render_provenance_markdown,
)


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_report_shape_and_counts() -> None:
    report = catalog_provenance_report()
    _assert(len(report["risks"]) == len(RISK_DEFINITIONS) == 10, report["risks"])
    _assert(len(report["factors"]) == len(FACTOR_DEFINITIONS) == 10, report["factors"])
    # v0.8 is a released publication, not a draft — verified 2026-07-28 against
    # the official OWASP AIVSS site (see aivss_spec_provenance.py module docstring)
    _assert(report["spec_version"] == "v0.8", report["spec_version"])
    _assert(report["spec_published_date"] == SPEC_PUBLISHED_DATE, report["spec_published_date"])
    _assert(report["spec_source_url"].startswith("https://aivss.owasp.org/"), report["spec_source_url"])
    _assert(report["pinned_page_count"] == SPEC_PINNED_PAGE_COUNT, report)


def test_all_current_catalog_entries_are_verified() -> None:
    # The whole point of the report: with the source OCR text present and
    # unchanged, every risk/factor name in aivss_kg.py must resolve to a
    # real (non-TOC) spec page — this is the regression signal that would
    # catch drift after a re-OCR or a renamed catalog entry.
    report = catalog_provenance_report()
    _assert(report["all_risks_verified"] is True, report["unverified_risk_keys"])
    _assert(report["all_factors_verified"] is True, report["unverified_factor_keys"])
    _assert(report["unverified_risk_keys"] == [], report["unverified_risk_keys"])
    _assert(report["unverified_factor_keys"] == [], report["unverified_factor_keys"])


def test_risk_sections_resolve_to_their_actual_content_page() -> None:
    # citations_per_entry=2 default should surface both the overview page (5)
    # and the risk's own dedicated section page, not just the overview.
    report = catalog_provenance_report()
    by_key = {row["key"]: row for row in report["risks"]}
    expected_section_page = {
        "tool_misuse": 8,
        "access_control": 10,
        "cascading_failures": 14,
        "orchestration": 17,
        "identity_impersonation": 21,
        "memory_context": 24,
        "critical_systems": 28,
        "supply_chain": 32,
        "untraceability": 38,
        "goal_instruction": 41,
    }
    for key, page in expected_section_page.items():
        _assert(page in by_key[key]["pages"], (key, by_key[key]["pages"]))


def test_no_page_count_drift_against_pinned_value() -> None:
    report = catalog_provenance_report()
    _assert(report["page_count_drift"] is False, report)
    _assert(report["loaded_page_count"] == SPEC_PINNED_PAGE_COUNT, report)


def test_no_matrix_gaps() -> None:
    report = catalog_provenance_report()
    _assert(report["matrix_gaps"] == [], report["matrix_gaps"])


def test_render_markdown_contains_all_sections() -> None:
    report = catalog_provenance_report()
    markdown = render_provenance_markdown(report)
    _assert("AIVSS Catalog Provenance Report" in markdown, markdown[:200])
    _assert("v0.8" in markdown, markdown)
    _assert(SPEC_PUBLISHED_DATE in markdown, markdown)
    _assert("## Risks" in markdown, markdown)
    _assert("## Factors" in markdown, markdown)
    _assert("WARNING" not in markdown, "no drift expected in current state")


def main() -> int:
    tests = (
        test_report_shape_and_counts,
        test_all_current_catalog_entries_are_verified,
        test_risk_sections_resolve_to_their_actual_content_page,
        test_no_page_count_drift_against_pinned_value,
        test_no_matrix_gaps,
        test_render_markdown_contains_all_sections,
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
