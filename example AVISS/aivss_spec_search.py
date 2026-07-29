"""Deterministic full-text search over the manually-OCR'd AIVSS v0.8 source
pages, per `SKILLS_ROADMAP.md` idea #1 ("อ้างอิงเนื้อหาต้นฉบับ").

No LLM call, no fuzzy/embedding search — a keyword/substring scorer over the
98 plain-text pages already produced by the manual Claude-vision OCR pass
documented in `README.md` (`AIVSS Scoring System For OWASP Agentic AI Core
Security Risks v0.8 (1)_pages/text/page-NN.txt`). This exists so any other
skill in this folder (or an MCP caller — see `aivss_mcp_server.py`) can cite
an actual spec page + quote instead of asserting a fact about the source with
no traceable anchor, matching the "never guess" convention set by
`aivss_assessment_skills.py`.

Fails closed: `search_spec()` / `cite_spec_reference()` return an empty list
when nothing meets `min_score` — never a low-confidence guess presented as a
citation. Confidence is reported per hit, not filtered out, so a caller can
decide its own bar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

SPEC_SEARCH_SCHEMA = "rag.aivss-spec-search.v1"

_SPEC_TEXT_DIR = (
    Path(__file__).resolve().parent
    / "AIVSS Scoring System For OWASP Agentic AI Core Security Risks v0.8 (1)_pages"
    / "text"
)

_DOT_LEADER_RE = re.compile(r"\.{4,}")
_TOC_DOT_LEADER_MIN = 4  # table-of-contents pages repeat "....... N" per entry

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_\-]{1,}")
_STOPWORDS = frozenset(
    {
        "the", "and", "for", "with", "that", "this", "from", "into", "via",
        "are", "was", "were", "can", "may", "its", "their", "not", "any",
        "all", "when", "how", "what", "who", "which", "such", "than",
    }
)


@dataclass(frozen=True)
class SpecPage:
    page_number: int
    text: str


@lru_cache(maxsize=1)
def _load_pages() -> tuple[SpecPage, ...]:
    """Load every text/page-NN.txt once, sorted by page number.

    Cached for process lifetime — the OCR output is static reference
    material (see README.md "Process"), never rewritten at runtime.
    """

    if not _SPEC_TEXT_DIR.is_dir():
        return ()
    pages: list[SpecPage] = []
    for path in _SPEC_TEXT_DIR.glob("page-*.txt"):
        match = re.search(r"page-(\d+)\.txt$", path.name)
        if not match:
            continue
        pages.append(
            SpecPage(
                page_number=int(match.group(1)),
                text=path.read_text(encoding="utf-8"),
            )
        )
    pages.sort(key=lambda page: page.page_number)
    return tuple(pages)


def spec_pages_available() -> int:
    """Number of OCR'd source pages currently loadable — 0 if the reference
    material is missing (e.g. this module copied without the _pages dir)."""

    return len(_load_pages())


def _is_toc_like(text: str) -> bool:
    """Table-of-contents / list-of-figures pages repeat every entry as
    'Title ....... N' (dot leaders). They match on risk/factor names just as
    strongly as the real section, but citing one as spec evidence would point
    a reader at a page number, not the actual described content — so search
    excludes them by default (see `include_toc` on search_spec)."""

    return len(_DOT_LEADER_RE.findall(text)) >= _TOC_DOT_LEADER_MIN


def _tokenize(query: str) -> list[str]:
    tokens = [
        token.casefold()
        for token in _TOKEN_RE.findall(query)
        if len(token) >= 3 and token.casefold() not in _STOPWORDS
    ]
    # de-dupe, keep first-seen order
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique


def _snippet_around(text: str, needle_positions: list[int], *, width: int = 220) -> str:
    if not needle_positions:
        stripped = re.sub(r"\s+", " ", text).strip()
        return stripped[:width]
    center = needle_positions[0]
    start = max(0, center - width // 2)
    end = min(len(text), center + width // 2)
    snippet = re.sub(r"\s+", " ", text[start:end]).strip()
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{snippet}{suffix}"


def _confidence(*, exact_phrase_hit: bool, matched_tokens: int, total_tokens: int) -> str:
    if exact_phrase_hit:
        return "high"
    if total_tokens <= 0:
        return "low"
    ratio = matched_tokens / total_tokens
    if ratio >= 0.75:
        return "medium"
    return "low"


def search_spec(
    query: str,
    *,
    limit: int = 5,
    min_score: int = 1,
    include_toc: bool = False,
) -> list[dict[str, Any]]:
    """Deterministic keyword search over the 98 OCR'd AIVSS v0.8 pages.

    Score per page = count of distinct query tokens present (casefold
    substring match) + a fixed bonus if the full query also appears as a
    verbatim phrase on that page. Returns page/snippet/score/confidence,
    sorted by score desc then page number asc (stable, reproducible order).
    Returns [] for a blank query, no loaded pages, or no page reaching
    `min_score` — this never returns a low-confidence guess dressed as a hit.

    Table-of-contents / list-of-figures pages are excluded by default (see
    `_is_toc_like`) — they name-match everything without describing it, which
    makes them a misleading citation target. Set `include_toc=True` to search
    them anyway (e.g. to look up a section's page number).
    """

    text = str(query or "").strip()
    pages = _load_pages()
    if not text or not pages:
        return []

    tokens = _tokenize(text)
    if not tokens:
        return []
    phrase = text.casefold()

    scored: list[tuple[int, bool, int, SpecPage]] = []
    for page in pages:
        if not include_toc and _is_toc_like(page.text):
            continue
        haystack = page.text.casefold()
        matched = [token for token in tokens if token in haystack]
        exact_phrase_hit = len(phrase) >= 6 and phrase in haystack
        score = len(matched) + (2 if exact_phrase_hit else 0)
        if score >= max(1, int(min_score)):
            scored.append((score, exact_phrase_hit, len(matched), page))

    scored.sort(key=lambda row: (-row[0], row[3].page_number))

    results: list[dict[str, Any]] = []
    for score, exact_phrase_hit, matched_count, page in scored[: max(1, int(limit))]:
        haystack = page.text.casefold()
        first_hit = haystack.find(phrase) if exact_phrase_hit else -1
        if first_hit < 0:
            for token in tokens:
                pos = haystack.find(token)
                if pos >= 0:
                    first_hit = pos
                    break
        results.append(
            {
                "page": page.page_number,
                "score": score,
                "confidence": _confidence(
                    exact_phrase_hit=exact_phrase_hit,
                    matched_tokens=matched_count,
                    total_tokens=len(tokens),
                ),
                "matched_tokens": matched_count,
                "total_tokens": len(tokens),
                "snippet": _snippet_around(
                    page.text, [first_hit] if first_hit >= 0 else []
                ),
            }
        )
    return results


def _resolve_named_query(key_or_query: str) -> str:
    """If key_or_query is a known AIVSS risk/factor key, expand it to that
    catalog's human-readable name (better search recall than the raw key,
    e.g. 'goal_instruction' -> 'Agent Goal and Instruction Manipulation').
    Falls back to the raw text unchanged for freeform search queries."""

    normalized = str(key_or_query or "").strip().casefold().replace("-", "_").replace(" ", "_")
    if not normalized:
        return str(key_or_query or "")

    try:
        from aivss_kg import FACTOR_DEFINITIONS, RISK_DEFINITIONS
    except ImportError:
        return str(key_or_query or "")

    for row in RISK_DEFINITIONS:
        if row["key"] == normalized:
            return str(row["name"])
    for row in FACTOR_DEFINITIONS:
        if row["key"] == normalized:
            return str(row["name"])
    return str(key_or_query or "")


def cite_spec_reference(
    key_or_query: str,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Convenience wrapper over search_spec for the common case: cite spec
    pages backing an AIVSS risk key, factor key, or freeform topic.

    A known risk/factor key is expanded to its catalog name first (see
    `_resolve_named_query`) so the search targets the term the spec actually
    uses, rather than the internal snake_case key. Anything else is searched
    as-is. Returns [] (never a guessed citation) if nothing is found.
    """

    query = _resolve_named_query(key_or_query)
    return search_spec(query, limit=limit)


__all__ = [
    "SPEC_SEARCH_SCHEMA",
    "SpecPage",
    "spec_pages_available",
    "search_spec",
    "cite_spec_reference",
]
