"""Spec-version tracking & catalog traceability, per `SKILLS_ROADMAP.md`
idea #6.

The source spec is **AIVSS v0.8** — a genuine release, not a draft. This was
verified directly (2026-07-28), not assumed: the document text itself never
labels itself "draft" (checked every occurrence of the word "draft" across
all 98 OCR'd pages — none refer to this document's own status), and the
official project homepage (https://aivss.owasp.org/) headlines it
"📄 New Publication: AIVSS v0.8 Released." The local PDF in this folder is
byte-identical (4,596,969 bytes, confirmed via `stat`/`curl -I`) to the copy
currently served from the official site, whose `Last-Modified` HTTP header
gives the publication date: **2026-04-10**. (An earlier version of this
module incorrectly called it "0.8-draft" — a guess never verified against
the actual source; corrected here.) `aivss_kg.RISK_DEFINITIONS`,
`aivss_kg.FACTOR_DEFINITIONS`, and `aivss_kg.RISK_FACTOR_MATRIX` are pinned
against it, and this folder's OCR'd text (`AIVSS Scoring System For OWASP
Agentic AI Core Security Risks v0.8 (1)_pages/text/`) is the traceable source
of truth for every risk/factor name and description elsewhere in this
folder. When the spec updates (v0.9, v1.0, ...) every one of those catalog
entries needs re-verification against the new source — this module is that
verification, run on demand rather than a hand-maintained page-range table.

Deliberately dynamic, not hand-pinned: `catalog_provenance_report()` calls
`aivss_spec_search.cite_spec_reference()` for every risk/factor key at call
time instead of hard-coding page numbers. A hand-typed page-range table
would itself drift the moment the OCR text is regenerated (different
pagination, a corrected transcription, ...) — exactly the problem idea #6
is meant to catch, so this module can't be the thing that reintroduces it.
Re-run this after any re-OCR or spec version bump to see what changed.
"""

from __future__ import annotations

from typing import Any

from aivss_kg import FACTOR_DEFINITIONS, RISK_DEFINITIONS, RISK_FACTOR_MATRIX
from aivss_spec_search import cite_spec_reference, spec_pages_available

PROVENANCE_SCHEMA = "rag.aivss-spec-provenance.v1"

# Pinned at authoring time (2026-07-28) against the source PDF named in
# README.md "Source", and re-verified the same day against the copy served
# from the official OWASP AIVSS site. Bump all four together when the spec
# is re-OCR'd from a newer version.
SPEC_VERSION = "v0.8"
SPEC_PUBLISHED_DATE = "2026-04-10"  # official site's Last-Modified header on the PDF asset
SPEC_SOURCE_FILENAME = (
    "AIVSS Scoring System For OWASP Agentic AI Core Security Risks v0.8 (1).pdf"
)
SPEC_SOURCE_URL = (
    "https://aivss.owasp.org/assets/publications/"
    "AIVSS%20Scoring%20System%20For%20OWASP%20Agentic%20AI%20Core%20Security%20Risks%20v0.8.pdf"
)
SPEC_PINNED_PAGE_COUNT = 98

_VALID_FACTOR_KEYS = frozenset(row["key"] for row in FACTOR_DEFINITIONS)


def _entry_provenance(key: str, name: str, *, citations_per_entry: int) -> dict[str, Any]:
    hits = cite_spec_reference(key, limit=citations_per_entry)
    return {
        "key": key,
        "name": name,
        "verified": bool(hits),
        "pages": [hit["page"] for hit in hits],
        "confidence": hits[0]["confidence"] if hits else None,
    }


def catalog_provenance_report(*, citations_per_entry: int = 2) -> dict[str, Any]:
    """Verify every RISK_DEFINITIONS / FACTOR_DEFINITIONS / RISK_FACTOR_MATRIX
    entry against the currently-loaded OCR'd spec pages.

    `verified` is True when `aivss_spec_search.cite_spec_reference()` finds
    at least one non-TOC page for that key's catalog name (dynamic search,
    same "fails closed" discipline as the rest of this folder — an
    unverified entry is reported, not silently assumed correct).
    `matrix_gaps` catches a structural drift case idea #6 also covers:
    RISK_FACTOR_MATRIX referencing a factor key that no longer exists in
    FACTOR_DEFINITIONS. `page_count_drift` flags if the currently-loaded OCR
    text no longer matches the page count this module was pinned against —
    the first signal that a re-OCR happened and this report should be
    re-read carefully.
    """

    risks = [
        _entry_provenance(row["key"], row["name"], citations_per_entry=citations_per_entry)
        for row in RISK_DEFINITIONS
    ]
    factors = [
        _entry_provenance(row["key"], row["name"], citations_per_entry=citations_per_entry)
        for row in FACTOR_DEFINITIONS
    ]

    matrix_gaps = [
        {"risk_key": risk_key, "unknown_factor_key": factor_key}
        for risk_key, factor_keys in RISK_FACTOR_MATRIX.items()
        for factor_key in factor_keys
        if factor_key not in _VALID_FACTOR_KEYS
    ]

    loaded_page_count = spec_pages_available()

    return {
        "schema": PROVENANCE_SCHEMA,
        "spec_version": SPEC_VERSION,
        "spec_published_date": SPEC_PUBLISHED_DATE,
        "spec_source_filename": SPEC_SOURCE_FILENAME,
        "spec_source_url": SPEC_SOURCE_URL,
        "pinned_page_count": SPEC_PINNED_PAGE_COUNT,
        "loaded_page_count": loaded_page_count,
        "page_count_drift": loaded_page_count != SPEC_PINNED_PAGE_COUNT,
        "risks": risks,
        "factors": factors,
        "matrix_gaps": matrix_gaps,
        "all_risks_verified": all(row["verified"] for row in risks),
        "all_factors_verified": all(row["verified"] for row in factors),
        "unverified_risk_keys": [row["key"] for row in risks if not row["verified"]],
        "unverified_factor_keys": [row["key"] for row in factors if not row["verified"]],
    }


def render_provenance_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [
        "# AIVSS Catalog Provenance Report",
        f"spec_version: {report['spec_version']} (published {report['spec_published_date']}) "
        f"| source: {report['spec_source_filename']}",
        f"official source: {report['spec_source_url']}",
        f"pinned_page_count: {report['pinned_page_count']} | loaded_page_count: "
        f"{report['loaded_page_count']}",
    ]
    if report["page_count_drift"]:
        lines.append(
            "**WARNING: page_count_drift — the loaded OCR text no longer matches the "
            "pinned page count. Re-verify SPEC_VERSION/SPEC_PINNED_PAGE_COUNT.**"
        )
    lines.append("")

    lines.append("## Risks")
    for row in report["risks"]:
        mark = "✅" if row["verified"] else "❌ UNVERIFIED"
        pages = ", ".join(f"p.{p}" for p in row["pages"]) or "—"
        lines.append(f"- {mark} {row['name']} ({row['key']}) — {pages}")

    lines.append("")
    lines.append("## Factors")
    for row in report["factors"]:
        mark = "✅" if row["verified"] else "❌ UNVERIFIED"
        pages = ", ".join(f"p.{p}" for p in row["pages"]) or "—"
        lines.append(f"- {mark} {row['name']} ({row['key']}) — {pages}")

    if report["matrix_gaps"]:
        lines.append("")
        lines.append("## RISK_FACTOR_MATRIX gaps")
        for gap in report["matrix_gaps"]:
            lines.append(f"- {gap['risk_key']} references unknown factor {gap['unknown_factor_key']}")

    return "\n".join(lines)


__all__ = [
    "PROVENANCE_SCHEMA",
    "SPEC_VERSION",
    "SPEC_PUBLISHED_DATE",
    "SPEC_SOURCE_FILENAME",
    "SPEC_SOURCE_URL",
    "SPEC_PINNED_PAGE_COUNT",
    "catalog_provenance_report",
    "render_provenance_markdown",
]
