#!/usr/bin/env python3
"""Page-anchored AIVSS v0.8 knowledge graph and deterministic scorer.

The source is the 98-page AIVSS PDF and its one-text-file-per-page manual OCR
export under ``example AIVSS``.  Codex owns the semantic compilation into
nodes and relations; every generated semantic item retains a physical PDF page
and exact source evidence.  The source files remain read-only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_DIR = REPO_ROOT / "example AIVSS"
DEFAULT_ARTIFACT_DIR = (
    REPO_ROOT / "config" / "knowledge_graphs" / "aivss_agentic_v08"
)
DEFAULT_GRAPH_PATH = DEFAULT_ARTIFACT_DIR / "graph.json"
SOURCE_PDF_NAME = (
    "AIVSS Scoring System For OWASP Agentic AI Core Security Risks v0.8 (1).pdf"
)
SOURCE_PAGES_DIR_NAME = SOURCE_PDF_NAME.removesuffix(".pdf") + "_pages"
GRAPH_SCHEMA = "rag.aivss-agentic-kg.v1"
MANIFEST_SCHEMA = "rag.aivss-source-manifest.v1"
EXPECTED_PAGE_COUNT = 98

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.+&/-]{1,}|[ก-๙]{2,}")
PAGE_TAG_RE = re.compile(r"^\s*<page_number>(\d+)</page_number>\s*$")
NUMBERED_HEADING_RE = re.compile(
    r"^(?:Part\s+\d+\s*:|Appendix\s+[A-D]\s*:|"
    r"\d+(?:\.\d+){0,3}\s+[A-Z].+)$"
)
UPPER_HEADING_RE = re.compile(
    r"^(?:DESCRIPTION|KEY RISKS(?:\s+\(.+\))?|EXAMPLE ATTACK SCENARIOS|"
    r"Executive Summary|Acknowledgement)$",
    re.IGNORECASE,
)
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
CALC_CVSS_RE = re.compile(
    r"\b(?:cvss(?:_base|\s+base)?|คะแนน\s*cvss)\s*(?:=|:|คือ)?\s*"
    r"(?P<value>10(?:\.0+)?|[0-9](?:\.[0-9]+)?)\b",
    re.IGNORECASE,
)
CALC_FACTOR_SUM_RE = re.compile(
    r"\b(?:factor[_\s-]*sum|ผลรวม(?:ของ)?ปัจจัย|คะแนนรวมปัจจัย)\s*"
    r"(?:=|:|คือ)?\s*(?P<value>10(?:\.0+)?|[0-9](?:\.[0-9]+)?)\b",
    re.IGNORECASE,
)
CALC_THM_RE = re.compile(
    r"\b(?:thm|threat[_\s-]*multiplier)\s*(?:=|:|คือ)?\s*"
    r"(?P<value>0\.50|0\.5|0\.97|1(?:\.0+)?)\b",
    re.IGNORECASE,
)
CALC_MITIGATION_RE = re.compile(
    r"\b(?:mitigation[_\s-]*factor|mitigation)\s*(?:=|:|คือ)?\s*"
    r"(?P<value>0\.67|0\.83|1(?:\.0+)?)\b",
    re.IGNORECASE,
)

STOPWORDS = {
    "the", "and", "or", "of", "to", "in", "for", "is", "are", "a", "an",
    "with", "this", "that", "from", "by", "on", "as", "what", "how", "why",
    "when", "which", "does", "ตาม", "จาก", "ของ", "และ", "หรือ", "ที่", "ใน",
    "ให้", "เป็น", "อะไร", "อย่างไร", "เกี่ยวกับ", "การ", "คะแนน", "ระบบ",
}

RISK_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "tool_misuse",
        "name": "Agentic AI Tool Misuse",
        "aliases": ["Tool Misuse", "ASI02", "การใช้เครื่องมือผิดวัตถุประสงค์"],
        "start_page": 5,
        "end_page": 10,
    },
    {
        "key": "access_control",
        "name": "Agent Access Control Violation",
        "aliases": ["Access Control Violation", "ASI03", "การละเมิดสิทธิ์"],
        "start_page": 10,
        "end_page": 14,
    },
    {
        "key": "cascading_failures",
        "name": "Agent Cascading Failures",
        "aliases": ["Cascading Failures", "ASI08", "ความล้มเหลวแบบลูกโซ่"],
        "start_page": 14,
        "end_page": 17,
    },
    {
        "key": "orchestration",
        "name": "Agent Orchestration and Multi-Agent Exploitation",
        "aliases": [
            "Agent Orchestration Exploitation",
            "Insecure Inter-Agent Communication",
            "ASI07",
            "การโจมตี multi-agent",
        ],
        "start_page": 17,
        "end_page": 21,
    },
    {
        "key": "identity_impersonation",
        "name": "Agent Identity Impersonation",
        "aliases": ["Identity Impersonation", "ASI09", "การปลอมตัวตน agent"],
        "start_page": 21,
        "end_page": 24,
    },
    {
        "key": "memory_context",
        "name": "Agent Memory and Context Manipulation",
        "aliases": [
            "Agent Memory & Context Manipulation",
            "Memory and Context Poisoning",
            "ASI06",
            "การวางยาความจำ",
        ],
        "start_page": 24,
        "end_page": 28,
    },
    {
        "key": "critical_systems",
        "name": "Insecure Agent Critical Systems Interaction",
        "aliases": [
            "Critical Systems Interaction",
            "Unexpected Code Execution",
            "ASI05",
            "ระบบสำคัญ",
        ],
        "start_page": 28,
        "end_page": 32,
    },
    {
        "key": "supply_chain",
        "name": "Agent Supply Chain and Dependency Risk",
        "aliases": [
            "Agent Supply Chain & Dependency Risk",
            "Agentic Supply Chain Vulnerabilities",
            "ASI04",
            "ห่วงโซ่อุปทาน",
        ],
        "start_page": 32,
        "end_page": 38,
    },
    {
        "key": "untraceability",
        "name": "Agent Untraceability",
        "aliases": ["Untraceability", "Rogue Agents", "ASI10", "ตรวจสอบย้อนหลังไม่ได้"],
        "start_page": 38,
        "end_page": 41,
    },
    {
        "key": "goal_instruction",
        "name": "Agent Goal and Instruction Manipulation",
        "aliases": [
            "Agent Goal & Instruction Manipulation",
            "Agent Goal Hijack",
            "Goal Manipulation",
            "ASI01",
            "การบิดเบือนเป้าหมายและคำสั่ง",
        ],
        "start_page": 41,
        "end_page": 44,
    },
)

FACTOR_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "autonomy",
        "name": "Execution Autonomy",
        "short": "Autonomy",
        "description": "The ability to execute actions without human verification.",
    },
    {
        "key": "tools",
        "name": "External Tool Control Surface",
        "short": "Tools",
        "description": "The breadth and privilege of external APIs/tools the agent can access.",
    },
    {
        "key": "language",
        "name": "Natural Language Interface",
        "short": "Language",
        "description": "The reliance on unstructured natural language for goal formulation and instruction.",
    },
    {
        "key": "context",
        "name": "Contextual Awareness",
        "short": "Context",
        "description": "The utilization of environmental sensors or broad data context to drive decisions.",
    },
    {
        "key": "non_determinism",
        "name": "Behavioral Non-Determinism",
        "short": "Non-Determinism",
        "description": "The variance in output or action for identical inputs.",
    },
    {
        "key": "opacity",
        "name": "Opacity & Reflexivity",
        "short": "Opacity",
        "description": "The lack of internal visibility or the ability to audit decision logic.",
    },
    {
        "key": "persistence",
        "name": "Persistent State Retention",
        "short": "Persistence",
        "description": "The ability to retain memory or state across sessions.",
    },
    {
        "key": "identity",
        "name": "Dynamic Identity",
        "short": "Identity",
        "description": "The ability to assume different user roles or permissions at runtime.",
    },
    {
        "key": "multi_agent",
        "name": "Multi-Agent Interactions",
        "short": "Multi-Agent",
        "description": "Coordination or dependencies on other autonomous agents.",
    },
    {
        "key": "self_mod",
        "name": "Self-Modification",
        "short": "Self-Mod",
        "description": "The ability to alter its own code, prompts, or tool configurations.",
    },
)

RISK_FACTOR_MATRIX: dict[str, tuple[str, ...]] = {
    "tool_misuse": ("autonomy", "tools", "language"),
    "access_control": ("tools", "identity", "persistence"),
    "cascading_failures": ("autonomy", "multi_agent", "non_determinism", "opacity"),
    "orchestration": ("autonomy", "identity", "multi_agent", "context"),
    "identity_impersonation": ("identity", "opacity", "language"),
    "memory_context": ("persistence", "context", "opacity"),
    "critical_systems": ("autonomy", "tools", "context", "self_mod"),
    "supply_chain": tuple(row["key"] for row in FACTOR_DEFINITIONS),
    "untraceability": ("opacity", "identity", "non_determinism"),
    "goal_instruction": ("language", "autonomy", "non_determinism", "context"),
}

EXAMPLE_SCORES: dict[str, dict[str, Any]] = {
    "tool_misuse": {"page": 56, "cvss_base": 9.4, "factor_sum": 9.0, "aars": 0.5, "aivss": 9.9, "severity": "Critical"},
    "access_control": {"page": 57, "cvss_base": 8.7, "factor_sum": 8.0, "aars": 1.0, "aivss": 9.7, "severity": "Critical"},
    "cascading_failures": {"page": 58, "cvss_base": 7.1, "factor_sum": 8.0, "aars": 2.3, "aivss": 9.4, "severity": "Critical"},
    "orchestration": {"page": 59, "cvss_base": 9.4, "factor_sum": 9.5, "aars": 0.6, "aivss": 10.0, "severity": "Critical"},
    "identity_impersonation": {"page": 60, "cvss_base": 7.4, "factor_sum": 7.5, "aars": 1.9, "aivss": 9.3, "severity": "Critical"},
    "memory_context": {"page": 61, "cvss_base": 5.8, "factor_sum": 7.5, "aars": 3.1, "aivss": 8.9, "severity": "High"},
    "critical_systems": {"page": 62, "cvss_base": 6.9, "factor_sum": 7.5, "aars": 2.3, "aivss": 9.2, "severity": "Critical"},
    "supply_chain": {"page": 63, "cvss_base": 9.3, "factor_sum": 6.5, "aars": 0.4, "aivss": 9.7, "severity": "Critical"},
    "untraceability": {"page": 64, "cvss_base": 5.3, "factor_sum": 6.5, "aars": 3.0, "aivss": 8.3, "severity": "High"},
    "goal_instruction": {"page": 65, "cvss_base": 2.1, "factor_sum": 6.5, "aars": 5.0, "aivss": 7.1, "severity": "High"},
}

ASI_MAPPINGS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("ASI01", "Agent Goal Hijack", "goal_instruction", ("memory_context", "critical_systems")),
    ("ASI02", "Tool Misuse & Exploitation", "tool_misuse", ("orchestration", "critical_systems")),
    ("ASI03", "Identity & Privilege Abuse", "access_control", ("identity_impersonation", "untraceability")),
    ("ASI04", "Agentic Supply Chain Vulnerabilities", "supply_chain", ("tool_misuse", "orchestration")),
    ("ASI05", "Unexpected Code Execution (RCE)", "tool_misuse", ("access_control", "critical_systems")),
    ("ASI06", "Memory & Context Poisoning", "memory_context", ("goal_instruction", "cascading_failures")),
    ("ASI07", "Insecure Inter-Agent Communication", "orchestration", ("access_control", "identity_impersonation")),
    ("ASI08", "Cascading Failures", "cascading_failures", ("orchestration", "memory_context")),
    ("ASI09", "Human–Agent Trust Exploitation", "identity_impersonation", ("goal_instruction", "access_control")),
    ("ASI10", "Rogue Agents", "access_control", ("untraceability", "goal_instruction")),
)

MAESTRO_MAPPINGS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Layer 1: Foundation Models", "Base models and fine-tuned variants used by agents", ("goal_instruction", "untraceability")),
    ("Layer 2: Data Operations", "Training data, RAG pipelines, vector stores, memory inputs", ("memory_context", "supply_chain")),
    ("Layer 3: Agent Frameworks", "Agent logic, planners, tool orchestration frameworks", ("orchestration", "cascading_failures")),
    ("Layer 4: Deployment and Infrastructure", "Cloud, on-prem, runtime environments, execution substrates", ("critical_systems", "access_control")),
    ("Layer 5: Evaluation and Observability", "Monitoring, logging, evaluation, runtime visibility", ("untraceability", "cascading_failures")),
    ("Layer 6: Security and Compliance (Vertical)", "Cross-cutting security, identity, policy, and compliance controls", ("identity_impersonation", "access_control")),
    ("Layer 7: Agent Ecosystem", "External tools, plugins, MCP servers, agent marketplaces, SaaS integrations", ("tool_misuse", "supply_chain")),
)

ROLE_DEFINITIONS: tuple[tuple[str, int], ...] = (
    ("AI Security Lead/Assessor", 67),
    ("Agent Developers/Engineers & Data Scientists", 67),
    ("Security Operations (SecOps) Team", 68),
    ("Governance, Risk, and Compliance (GRC) Team", 68),
    ("Risk Management/Compliance Officer", 68),
    ("System Owners/Business Stakeholders", 68),
    ("Chief Security Officer (CISO/CSO/equivalent)", 68),
    ("AI Reliability & Policy Engineer (AI RPE)", 68),
    ("AI Governance Board", 69),
    ("AI Risk Classification Committee", 69),
)

FRAMEWORK_DEFINITIONS: tuple[tuple[str, int], ...] = (
    ("NIST Cybersecurity Framework (CSF)", 71),
    ("NIST AI Risk Management Framework (AI RMF)", 71),
    ("ISO/IEC 27001/27002", 71),
    ("ISO/IEC 23894:2023", 71),
    ("MITRE ATLAS", 73),
    ("CSA MAESTRO", 73),
    ("Digital Identity Rights Framework (DIRF)", 72),
    ("OWASP Agentic AI Top 10 for 2026", 75),
)

QUERY_EXPANSIONS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("สูตร", "คำนวณ", "calculate", "aivss score", "aars"),
        ("risk_gap", "factor_sum", "threat multiplier", "mitigation factor", "roundhalfup", "primary aivss scoring equation"),
    ),
    (
        ("ปัจจัย", "factor", "amplification"),
        ("autonomy", "tools", "language", "context", "non-determinism", "opacity", "persistence", "identity", "multi-agent", "self-mod"),
    ),
    (
        ("ระดับความรุนแรง", "severity", "critical", "high", "medium", "low"),
        ("severity band definitions", "9.0", "7.0", "4.0", "0.1"),
    ),
    (
        ("เฉลี่ย", "average", "ordinal", "interval"),
        ("do not average scores", "ordinal", "interval scales", "severity band"),
    ),
    (
        ("สิทธิ์", "permission", "access control", "privilege"),
        ("agent access control violation", "identity", "role inheritance", "credential"),
    ),
    (
        ("ความจำ", "memory", "rag", "context poisoning"),
        ("agent memory and context manipulation", "persistence", "context", "opacity", "asi06"),
    ),
    (
        ("เครื่องมือ", "tool", "mcp", "api"),
        ("agentic ai tool misuse", "external tool control surface", "asi02"),
    ),
    (
        ("บทบาท", "role", "ใครรับผิดชอบ", "responsible"),
        ("ai security lead", "system owners", "secops", "grc", "governance board", "classification committee"),
    ),
    (
        ("release gate", "อนุมัติ", "approval", "ก่อน production"),
        ("release gates and approval mechanisms", "ai governance board", "ai risk classification committee"),
    ),
    (
        ("asi", "top 10 2026"),
        ("owasp genai llm agentic ai top 10", "primary aivss core risk", "secondary overlapping"),
    ),
    (
        ("maestro", "layer", "สถาปัตยกรรม"),
        ("foundation models", "data operations", "agent frameworks", "deployment infrastructure", "evaluation observability", "security compliance", "agent ecosystem"),
    ),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_sha(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _clean_inline(value: object, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _normalize_name(value: object) -> str:
    return re.sub(r"[^a-z0-9ก-๙]+", " ", str(value or "").casefold()).strip()


def _source_paths(source_dir: Path | str) -> tuple[Path, Path, list[Path]]:
    source_root = Path(source_dir).resolve()
    pdf_path = source_root / SOURCE_PDF_NAME
    text_dir = source_root / SOURCE_PAGES_DIR_NAME / "text"
    text_paths = sorted(text_dir.glob("page-*.txt"))
    if not pdf_path.is_file():
        raise FileNotFoundError(f"AIVSS source PDF not found: {pdf_path}")
    if len(text_paths) != EXPECTED_PAGE_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_PAGE_COUNT} AIVSS text pages, found {len(text_paths)}"
        )
    return source_root, pdf_path, text_paths


def build_source_manifest(source_dir: Path | str = DEFAULT_SOURCE_DIR) -> dict[str, Any]:
    source_root, pdf_path, text_paths = _source_paths(source_dir)
    files: list[dict[str, Any]] = []
    observed_pages: list[int] = []
    for path in text_paths:
        text = path.read_text(encoding="utf-8")
        first_line = text.splitlines()[0] if text.splitlines() else ""
        match = PAGE_TAG_RE.match(first_line)
        page = int(match.group(1)) if match else 0
        observed_pages.append(page)
        files.append(
            {
                "kind": "page_text",
                "physical_page": page,
                "source_file": path.relative_to(source_root).as_posix(),
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
                "chars": len(text),
                "line_count": len(text.splitlines()),
            }
        )
    expected_pages = list(range(1, EXPECTED_PAGE_COUNT + 1))
    if observed_pages != expected_pages:
        raise ValueError(
            "AIVSS page tags are not a complete ordered 1..98 sequence: "
            f"{observed_pages[:5]}...{observed_pages[-5:]}"
        )
    pdf = {
        "kind": "source_pdf",
        "source_file": pdf_path.relative_to(source_root).as_posix(),
        "sha256": _sha256_file(pdf_path),
        "bytes": pdf_path.stat().st_size,
        "physical_pages": EXPECTED_PAGE_COUNT,
    }
    fingerprint_rows = [
        {"source_file": pdf["source_file"], "sha256": pdf["sha256"]},
        *[
            {
                "source_file": row["source_file"],
                "sha256": row["sha256"],
                "physical_page": row["physical_page"],
            }
            for row in files
        ],
    ]
    return {
        "schema": MANIFEST_SCHEMA,
        "built_at": _utc_now(),
        "source_name": "AIVSS Scoring System for OWASP Agentic AI Core Security Risks v0.8",
        "source_root": str(source_root),
        "source_pdf": pdf,
        "page_count": EXPECTED_PAGE_COUNT,
        "page_text_files": files,
        "source_fingerprint": _json_sha(fingerprint_rows),
        "provenance": {
            "ocr_method": "manual page-image transcription",
            "ocr_creator": "Claude Vision (Sonnet 5)",
            "knowledge_graph_creator": "Codex",
            "database_mutated": False,
            "source_text_rewritten": False,
        },
    }


def _page_texts(source_dir: Path | str) -> dict[int, str]:
    _, _, text_paths = _source_paths(source_dir)
    pages: dict[int, str] = {}
    for path in text_paths:
        raw = path.read_text(encoding="utf-8")
        lines = raw.splitlines()
        match = PAGE_TAG_RE.match(lines[0] if lines else "")
        if not match:
            raise ValueError(f"Missing physical page tag: {path}")
        page = int(match.group(1))
        body_lines = lines[1:]
        while body_lines and not body_lines[-1].strip():
            body_lines.pop()
        if body_lines and re.fullmatch(r"\s*\d+\s*", body_lines[-1]):
            body_lines.pop()
        pages[page] = "\n".join(body_lines).strip()
    return pages


def _split_long_block(block: str, max_chars: int = 1800) -> list[str]:
    value = str(block or "").strip()
    if not value:
        return []
    if len(value) <= max_chars:
        return [value]
    parts: list[str] = []
    current = ""
    for line in value.splitlines():
        candidate = f"{current}\n{line}".strip() if current else line
        if current and len(candidate) > max_chars:
            parts.append(current.strip())
            current = line
        else:
            current = candidate
    if current:
        parts.append(current.strip())
    final: list[str] = []
    for part in parts:
        if len(part) <= max_chars:
            final.append(part)
            continue
        for start in range(0, len(part), max_chars):
            final.append(part[start : start + max_chars].strip())
    return [part for part in final if part]


def _page_blocks(page_text: str) -> list[str]:
    blocks: list[str] = []
    for raw in re.split(r"\n\s*\n", str(page_text or "")):
        blocks.extend(_split_long_block(raw))
    return blocks


def _find_evidence(
    pages: dict[int, str],
    page: int,
    terms: Iterable[str],
    *,
    fallback_chars: int = 900,
) -> str:
    wanted = [str(term or "").casefold() for term in terms if str(term or "").strip()]
    blocks = _page_blocks(pages.get(page, ""))
    for block in blocks:
        hay = block.casefold()
        if all(term in hay for term in wanted):
            return block
    for block in blocks:
        hay = block.casefold()
        if any(term in hay for term in wanted):
            return block
    return str(pages.get(page, ""))[:fallback_chars].strip()


def _anchor(
    manifest: dict[str, Any],
    page: int,
    *,
    evidence_id: str = "",
) -> dict[str, Any]:
    rows = manifest.get("page_text_files") or []
    page_row = next(
        (row for row in rows if int(row.get("physical_page") or 0) == int(page)),
        {},
    )
    return {
        "source_document": manifest.get("source_name"),
        "source_pdf": (manifest.get("source_pdf") or {}).get("source_file"),
        "source_pdf_sha256": (manifest.get("source_pdf") or {}).get("sha256"),
        "source_text_file": page_row.get("source_file"),
        "source_text_sha256": page_row.get("sha256"),
        "physical_page": int(page),
        "printed_page": max(0, int(page) - 1),
        "evidence_id": evidence_id,
    }


def _semantic_description_for_risk(
    pages: dict[int, str],
    risk: dict[str, Any],
) -> str:
    page = int(risk["start_page"])
    blocks = _page_blocks(pages.get(page, ""))
    heading_seen = False
    for block in blocks:
        if risk["name"].casefold() in block.casefold():
            heading_seen = True
            remainder = block.split(risk["name"], 1)[-1].strip()
            if len(remainder) >= 80:
                return _clean_inline(remainder, 900)
            continue
        if heading_seen and len(block) >= 80:
            return _clean_inline(block, 900)
    return _clean_inline(
        _find_evidence(pages, page, [risk["name"]]),
        900,
    )


def _topic_candidates(pages: dict[int, str]) -> list[tuple[str, int, str]]:
    topics: list[tuple[str, int, str]] = []
    seen: set[tuple[int, str]] = set()
    for page, text in pages.items():
        for raw in text.splitlines():
            line = raw.strip()
            if (
                not line
                or len(line) > 150
                or "..." in line
                or line.startswith("|")
                or line.startswith("-")
            ):
                continue
            if not (NUMBERED_HEADING_RE.match(line) or UPPER_HEADING_RE.match(line)):
                continue
            normalized = _normalize_name(line)
            key = (page, normalized)
            if not normalized or key in seen:
                continue
            seen.add(key)
            topics.append((f"topic_p{page}_{len(topics) + 1}", page, line))
    return topics


def _add_node(
    nodes: list[dict[str, Any]],
    *,
    node_id: str,
    entity_type: str,
    name: str,
    description: str,
    aliases: Iterable[str],
    anchor: dict[str, Any],
    evidence_span: str,
    properties: dict[str, Any] | None = None,
    codex_generated: bool = True,
) -> dict[str, Any]:
    node = {
        "id": node_id,
        "entity_type": entity_type,
        "name": name,
        "canonical_name": name,
        "description": description,
        "aliases": [str(value) for value in aliases if str(value).strip()],
        "source_anchor": anchor,
        "evidence_span": evidence_span,
        "confidence": 1.0,
        "source_grounded": True,
        "created_by": "Codex" if codex_generated else "source",
        "codex_generated": bool(codex_generated),
        "properties": dict(properties or {}),
    }
    nodes.append(node)
    return node


def _add_relation(
    relations: list[dict[str, Any]],
    *,
    source: str,
    predicate: str,
    target: str,
    anchor: dict[str, Any],
    evidence_span: str,
    confidence: float = 1.0,
) -> None:
    relations.append(
        {
            "id": f"rel_{len(relations) + 1:05d}",
            "source": source,
            "predicate": predicate,
            "target": target,
            "source_anchor": anchor,
            "evidence_span": evidence_span,
            "confidence": float(confidence),
            "source_grounded": True,
            "created_by": "Codex",
            "codex_generated": True,
        }
    )


def _extract_table_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in str(text or "").splitlines():
        match = TABLE_ROW_RE.match(line.strip())
        if not match:
            continue
        cells = [cell.strip() for cell in match.group(1).split("|")]
        if not cells or all(re.fullmatch(r":?-+:?", cell or "") for cell in cells):
            continue
        rows.append(cells)
    return rows


def build_aivss_graph(
    source_dir: Path | str = DEFAULT_SOURCE_DIR,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = build_source_manifest(source_dir)
    pages = _page_texts(source_dir)
    nodes: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    node_by_id: dict[str, dict[str, Any]] = {}

    def node(**kwargs: Any) -> dict[str, Any]:
        row = _add_node(nodes, **kwargs)
        node_by_id[str(row["id"])] = row
        return row

    doc_evidence = _find_evidence(pages, 1, ["AIVSS", "v0.8"])
    doc_anchor = _anchor(manifest, 1)
    node(
        node_id="doc_aivss_v08",
        entity_type="Document",
        name="AIVSS Scoring System for OWASP Agentic AI Core Security Risks v0.8",
        description=(
            "The selected 98-page source document compiled into a "
            "page-anchored knowledge graph by Codex."
        ),
        aliases=["AIVSS v0.8", "AIVSS", "AIVSS-Agentic"],
        anchor=doc_anchor,
        evidence_span=doc_evidence,
        properties={"physical_pages": EXPECTED_PAGE_COUNT, "version": "0.8"},
    )

    evidence_ids_by_page: dict[int, list[str]] = {}
    for page in range(1, EXPECTED_PAGE_COUNT + 1):
        page_text = pages[page]
        page_anchor = _anchor(manifest, page)
        page_node = node(
            node_id=f"page_{page:03d}",
            entity_type="PageIndex",
            name=f"AIVSS physical page {page}",
            description=_clean_inline(page_text, 320),
            aliases=[f"page {page}", f"หน้า {page}", f"printed page {max(0, page - 1)}"],
            anchor=page_anchor,
            evidence_span=_clean_inline(page_text, 900),
            properties={
                "physical_page": page,
                "printed_page": max(0, page - 1),
                "chars": len(page_text),
            },
            codex_generated=False,
        )
        _add_relation(
            relations,
            source="doc_aivss_v08",
            predicate="contains_page",
            target=page_node["id"],
            anchor=page_anchor,
            evidence_span=_clean_inline(page_text, 400),
        )
        evidence_ids_by_page[page] = []
        for block_index, block in enumerate(_page_blocks(page_text), start=1):
            evidence_id = f"evidence_p{page:03d}_{block_index:02d}"
            evidence_anchor = _anchor(
                manifest,
                page,
                evidence_id=evidence_id,
            )
            evidence_node = node(
                node_id=evidence_id,
                entity_type="EvidenceSpan",
                name=f"AIVSS p.{page} evidence {block_index}",
                description=_clean_inline(block, 500),
                aliases=[],
                anchor=evidence_anchor,
                evidence_span=block,
                properties={
                    "physical_page": page,
                    "block_index": block_index,
                    "source_text": block,
                },
                codex_generated=False,
            )
            evidence_ids_by_page[page].append(evidence_id)
            _add_relation(
                relations,
                source=page_node["id"],
                predicate="has_evidence",
                target=evidence_node["id"],
                anchor=evidence_anchor,
                evidence_span=block,
            )

    for topic_id, page, title in _topic_candidates(pages):
        evidence = _find_evidence(pages, page, [title])
        anchor = _anchor(manifest, page)
        topic = node(
            node_id=topic_id,
            entity_type="Topic",
            name=title,
            description=_clean_inline(evidence, 700),
            aliases=[],
            anchor=anchor,
            evidence_span=evidence,
            properties={"physical_page": page},
        )
        _add_relation(
            relations,
            source="doc_aivss_v08",
            predicate="contains_section",
            target=topic["id"],
            anchor=anchor,
            evidence_span=evidence,
        )
        _add_relation(
            relations,
            source=topic["id"],
            predicate="source_page",
            target=f"page_{page:03d}",
            anchor=anchor,
            evidence_span=evidence,
        )

    risk_node_ids: dict[str, str] = {}
    for risk in RISK_DEFINITIONS:
        page = int(risk["start_page"])
        evidence = _find_evidence(pages, page, [risk["name"]])
        anchor = _anchor(manifest, page)
        risk_id = f"risk_{risk['key']}"
        risk_node_ids[risk["key"]] = risk_id
        risk_node = node(
            node_id=risk_id,
            entity_type="Risk",
            name=risk["name"],
            description=_semantic_description_for_risk(pages, risk),
            aliases=risk["aliases"],
            anchor=anchor,
            evidence_span=evidence,
            properties={
                "risk_order": len(risk_node_ids),
                "start_physical_page": page,
                "end_physical_page": int(risk["end_page"]),
            },
        )
        _add_relation(
            relations,
            source="doc_aivss_v08",
            predicate="defines",
            target=risk_node["id"],
            anchor=anchor,
            evidence_span=evidence,
        )
        for source_page in range(page, int(risk["end_page"]) + 1):
            _add_relation(
                relations,
                source=risk_node["id"],
                predicate="source_page",
                target=f"page_{source_page:03d}",
                anchor=_anchor(manifest, source_page),
                evidence_span=_clean_inline(pages[source_page], 450),
            )

    factor_node_ids: dict[str, str] = {}
    rubric_rows = _extract_table_rows(pages[46] + "\n" + pages[47])
    for index, factor in enumerate(FACTOR_DEFINITIONS, start=1):
        factor_id = f"factor_{factor['key']}"
        factor_node_ids[factor["key"]] = factor_id
        factor_terms = [factor["name"], factor["short"]]
        evidence = _find_evidence(pages, 46, factor_terms)
        rubric = next(
            (
                row
                for row in rubric_rows
                if row and re.match(rf"^{index}\.\s*", row[0])
            ),
            [],
        )
        factor_node = node(
            node_id=factor_id,
            entity_type="RiskFactor",
            name=factor["name"],
            description=factor["description"],
            aliases=[factor["short"], factor["key"], factor["key"].replace("_", "-")],
            anchor=_anchor(manifest, 46),
            evidence_span=evidence,
            properties={
                "factor_order": index,
                "short_name": factor["short"],
                "allowed_scores": [0.0, 0.5, 1.0],
                "rubric": rubric,
                "rubric_pages": [46, 47],
            },
        )
        _add_relation(
            relations,
            source="doc_aivss_v08",
            predicate="defines",
            target=factor_node["id"],
            anchor=_anchor(manifest, 46),
            evidence_span=evidence,
        )

    matrix_evidence = _find_evidence(pages, 49, ["Risk Amplification Matrix"])
    for risk_key, factor_keys in RISK_FACTOR_MATRIX.items():
        for factor_key in factor_keys:
            _add_relation(
                relations,
                source=risk_node_ids[risk_key],
                predicate="amplified_by",
                target=factor_node_ids[factor_key],
                anchor=_anchor(manifest, 49),
                evidence_span=matrix_evidence,
            )

    metric_definitions = (
        ("cvss_base", "CVSS Base", 50, "CVSS v4.0 Baseline Requirements"),
        ("risk_gap", "Agentic Risk Gap", 52, "10 - CVSS_Base"),
        ("factor_sum", "Factor Sum", 51, "Factor_Sum ="),
        ("thm", "Threat Multiplier (ThM)", 52, "Threat Multiplier"),
        ("aars", "Agentic AI Risk Score (AARS)", 51, "AARS ="),
        ("mitigation_factor", "Mitigation Factor", 53, "Mitigation_Factor"),
        ("aivss_raw", "AIVSS Raw Score", 53, "AIVSS_raw"),
        ("aivss", "Final AIVSS Score", 54, "AIVSS is reported"),
        ("severity_band", "AIVSS Severity Band", 54, "Severity Band Definitions"),
    )
    metric_node_ids: dict[str, str] = {}
    for key, name, page, evidence_term in metric_definitions:
        evidence = _find_evidence(pages, page, [evidence_term])
        metric_id = f"metric_{key}"
        metric_node_ids[key] = metric_id
        metric = node(
            node_id=metric_id,
            entity_type="ScoringMetric",
            name=name,
            description=_clean_inline(evidence, 700),
            aliases=[key, name.replace(" ", "_")],
            anchor=_anchor(manifest, page),
            evidence_span=evidence,
            properties={"physical_page": page},
        )
        _add_relation(
            relations,
            source="doc_aivss_v08",
            predicate="defines",
            target=metric["id"],
            anchor=_anchor(manifest, page),
            evidence_span=evidence,
        )

    formula_aars_evidence = _find_evidence(pages, 51, ["AARS =", "Factor_Sum"])
    formula_aars = node(
        node_id="formula_aars",
        entity_type="Formula",
        name="AARS = (10 - CVSS_Base) × (Factor_Sum / 10) × ThM",
        description="Calculates the agentic uplift within the remaining risk gap.",
        aliases=["AARS formula", "สูตร AARS", "Agentic Uplift"],
        anchor=_anchor(manifest, 51),
        evidence_span=formula_aars_evidence,
        properties={
            "expression": "(10 - CVSS_Base) * (Factor_Sum / 10) * ThM"
        },
    )
    formula_aivss_evidence = _find_evidence(
        pages,
        53,
        ["AIVSS = (CVSS_Base + AARS) * Mitigation_Factor"],
    )
    formula_aivss = node(
        node_id="formula_aivss",
        entity_type="Formula",
        name="AIVSS = (CVSS_Base + AARS) × Mitigation_Factor",
        description=(
            "Combines the technical baseline and agentic uplift, applies "
            "mitigation scaling, and rounds half up to one decimal place."
        ),
        aliases=["Primary AIVSS Scoring Equation", "สูตร AIVSS"],
        anchor=_anchor(manifest, 53),
        evidence_span=formula_aivss_evidence,
        properties={
            "expression": "(CVSS_Base + AARS) * Mitigation_Factor",
            "rounding": "RoundHalfUp(AIVSS_raw, 1)",
        },
    )
    for input_metric in ("cvss_base", "factor_sum", "thm"):
        _add_relation(
            relations,
            source=formula_aars["id"],
            predicate="requires",
            target=metric_node_ids[input_metric],
            anchor=_anchor(manifest, 51 if input_metric != "thm" else 52),
            evidence_span=formula_aars_evidence,
        )
    _add_relation(
        relations,
        source=formula_aars["id"],
        predicate="calculates",
        target=metric_node_ids["aars"],
        anchor=_anchor(manifest, 51),
        evidence_span=formula_aars_evidence,
    )
    for input_metric in ("cvss_base", "aars", "mitigation_factor"):
        _add_relation(
            relations,
            source=formula_aivss["id"],
            predicate="requires",
            target=metric_node_ids[input_metric],
            anchor=_anchor(manifest, 53),
            evidence_span=formula_aivss_evidence,
        )
    _add_relation(
        relations,
        source=formula_aivss["id"],
        predicate="calculates",
        target=metric_node_ids["aivss"],
        anchor=_anchor(manifest, 53),
        evidence_span=formula_aivss_evidence,
    )

    scale_definitions = (
        ("factor_none", "None / Not Present", "FactorScoreLevel", 45, 0.0),
        ("factor_partial", "Partial / Limited", "FactorScoreLevel", 45, 0.5),
        ("factor_full", "Full / Unconstrained", "FactorScoreLevel", 45, 1.0),
        ("thm_unreported", "Unreported exploit maturity", "ThreatMaturity", 52, 0.50),
        ("thm_poc", "Proof-of-Concept exploit maturity", "ThreatMaturity", 52, 0.97),
        ("thm_attacked", "Attacked exploit maturity", "ThreatMaturity", 52, 1.00),
        ("mitigation_strong", "Strong Mitigation", "MitigationStrength", 53, 0.67),
        ("mitigation_partial", "Partial Mitigation", "MitigationStrength", 53, 0.83),
        ("mitigation_weak", "No/Weak Mitigation", "MitigationStrength", 53, 1.00),
        ("severity_low", "Low severity (0.1–3.9)", "SeverityBand", 54, "Low"),
        ("severity_medium", "Medium severity (4.0–6.9)", "SeverityBand", 54, "Medium"),
        ("severity_high", "High severity (7.0–8.9)", "SeverityBand", 54, "High"),
        ("severity_critical", "Critical severity (9.0–10.0)", "SeverityBand", 54, "Critical"),
    )
    for key, name, entity_type, page, value in scale_definitions:
        evidence = _find_evidence(pages, page, [name.split(" (", 1)[0]])
        scale_node = node(
            node_id=key,
            entity_type=entity_type,
            name=name,
            description=_clean_inline(evidence, 600),
            aliases=[str(value)],
            anchor=_anchor(manifest, page),
            evidence_span=evidence,
            properties={"value": value},
        )
        target_metric = (
            "factor_sum"
            if entity_type == "FactorScoreLevel"
            else "thm"
            if entity_type == "ThreatMaturity"
            else "mitigation_factor"
            if entity_type == "MitigationStrength"
            else "severity_band"
        )
        _add_relation(
            relations,
            source=scale_node["id"],
            predicate="defines_value_for",
            target=metric_node_ids[target_metric],
            anchor=_anchor(manifest, page),
            evidence_span=evidence,
        )

    for risk_key, score in EXAMPLE_SCORES.items():
        risk_name = node_by_id[risk_node_ids[risk_key]]["name"]
        page = int(score["page"])
        evidence = _find_evidence(
            pages,
            page,
            ["Final AIVSS Score"],
        )
        example_node = node(
            node_id=f"example_score_{risk_key}",
            entity_type="ScoringExample",
            name=f"AIVSS example: {risk_name}",
            description=(
                f"Illustrative source example with CVSS {score['cvss_base']} "
                f"and final AIVSS {score['aivss']} ({score['severity']})."
            ),
            aliases=[f"{risk_name} score", f"3.6 {risk_name}"],
            anchor=_anchor(manifest, page),
            evidence_span=evidence,
            properties=score,
        )
        _add_relation(
            relations,
            source=risk_node_ids[risk_key],
            predicate="illustrated_by",
            target=example_node["id"],
            anchor=_anchor(manifest, page),
            evidence_span=evidence,
        )

    for role_name, page in ROLE_DEFINITIONS:
        evidence = _find_evidence(pages, page, [role_name.split(" (", 1)[0]])
        role_id = "role_" + re.sub(r"[^a-z0-9]+", "_", role_name.casefold()).strip("_")
        role = node(
            node_id=role_id,
            entity_type="Role",
            name=role_name,
            description=_clean_inline(evidence, 700),
            aliases=[],
            anchor=_anchor(manifest, page),
            evidence_span=evidence,
            properties={},
        )
        _add_relation(
            relations,
            source=role["id"],
            predicate="responsible_for",
            target="metric_aivss",
            anchor=_anchor(manifest, page),
            evidence_span=evidence,
        )

    for framework_name, page in FRAMEWORK_DEFINITIONS:
        evidence = _find_evidence(
            pages,
            page,
            [framework_name.split(" (", 1)[0]],
        )
        framework_id = "framework_" + re.sub(
            r"[^a-z0-9]+",
            "_",
            framework_name.casefold(),
        ).strip("_")
        framework = node(
            node_id=framework_id,
            entity_type="Framework",
            name=framework_name,
            description=_clean_inline(evidence, 700),
            aliases=[],
            anchor=_anchor(manifest, page),
            evidence_span=evidence,
            properties={},
        )
        _add_relation(
            relations,
            source="doc_aivss_v08",
            predicate="maps_to",
            target=framework["id"],
            anchor=_anchor(manifest, page),
            evidence_span=evidence,
        )

    for index, (asi_id, name, primary, secondary) in enumerate(ASI_MAPPINGS):
        page = 94 if index < 3 else 95
        evidence = _find_evidence(pages, page, [asi_id])
        asi_node = node(
            node_id=f"asi_{asi_id.casefold()}",
            entity_type="ThreatCategory",
            name=f"{asi_id} {name}",
            description=_clean_inline(evidence, 650),
            aliases=[asi_id, name],
            anchor=_anchor(manifest, page),
            evidence_span=evidence,
            properties={"asi_id": asi_id},
        )
        _add_relation(
            relations,
            source=asi_node["id"],
            predicate="primary_maps_to",
            target=risk_node_ids[primary],
            anchor=_anchor(manifest, page),
            evidence_span=evidence,
        )
        for risk_key in secondary:
            _add_relation(
                relations,
                source=asi_node["id"],
                predicate="overlaps_with",
                target=risk_node_ids[risk_key],
                anchor=_anchor(manifest, page),
                evidence_span=evidence,
            )

    maestro_evidence = _find_evidence(pages, 96, ["MAESTRO Layer"])
    for index, (layer, description, risks) in enumerate(MAESTRO_MAPPINGS, start=1):
        layer_node = node(
            node_id=f"maestro_layer_{index}",
            entity_type="ArchitectureLayer",
            name=layer,
            description=description,
            aliases=[f"MAESTRO {index}", f"Layer {index}"],
            anchor=_anchor(manifest, 96),
            evidence_span=maestro_evidence,
            properties={"layer_number": index},
        )
        for risk_key in risks:
            _add_relation(
                relations,
                source=layer_node["id"],
                predicate="maps_to",
                target=risk_node_ids[risk_key],
                anchor=_anchor(manifest, 96),
                evidence_span=maestro_evidence,
            )

    node_ids = {str(row["id"]) for row in nodes}
    related_ids = {
        str(row["source"]) for row in relations
    } | {
        str(row["target"]) for row in relations
    }
    anchored_nodes = sum(
        1
        for row in nodes
        if int((row.get("source_anchor") or {}).get("physical_page") or 0) > 0
    )
    anchored_relations = sum(
        1
        for row in relations
        if int((row.get("source_anchor") or {}).get("physical_page") or 0) > 0
    )
    normalized_names = [
        _normalize_name(row.get("name"))
        for row in nodes
        if _normalize_name(row.get("name"))
    ]
    duplicate_ratio = (
        0.0
        if not normalized_names
        else 1.0 - (len(set(normalized_names)) / len(normalized_names))
    )
    orphan_ratio = (
        0.0
        if not nodes
        else 1.0 - (len(node_ids & related_ids) / len(node_ids))
    )
    entity_counts = Counter(str(row.get("entity_type") or "") for row in nodes)
    predicate_counts = Counter(str(row.get("predicate") or "") for row in relations)
    metrics = {
        "documents": entity_counts["Document"],
        "pages": entity_counts["PageIndex"],
        "evidence_spans": entity_counts["EvidenceSpan"],
        "risks": entity_counts["Risk"],
        "risk_factors": entity_counts["RiskFactor"],
        "scoring_metrics": entity_counts["ScoringMetric"],
        "roles": entity_counts["Role"],
        "frameworks": entity_counts["Framework"],
        "asi_threat_categories": entity_counts["ThreatCategory"],
        "maestro_layers": entity_counts["ArchitectureLayer"],
        "nodes": len(nodes),
        "relations": len(relations),
        "source_anchor_node_ratio": round(anchored_nodes / max(len(nodes), 1), 4),
        "source_anchor_relation_ratio": round(
            anchored_relations / max(len(relations), 1),
            4,
        ),
        "duplicate_entity_ratio": round(duplicate_ratio, 4),
        "orphan_entity_ratio": round(orphan_ratio, 4),
        "entity_type_counts": dict(sorted(entity_counts.items())),
        "predicate_counts": dict(sorted(predicate_counts.items())),
    }
    quality_gates = {
        "physical_page_coverage": {
            "target": EXPECTED_PAGE_COUNT,
            "value": entity_counts["PageIndex"],
            "passed": entity_counts["PageIndex"] == EXPECTED_PAGE_COUNT,
        },
        "risk_coverage": {
            "target": 10,
            "value": entity_counts["Risk"],
            "passed": entity_counts["Risk"] == 10,
        },
        "risk_factor_coverage": {
            "target": 10,
            "value": entity_counts["RiskFactor"],
            "passed": entity_counts["RiskFactor"] == 10,
        },
        "page_anchor_node_ratio": {
            "target": 0.70,
            "value": metrics["source_anchor_node_ratio"],
            "passed": metrics["source_anchor_node_ratio"] >= 0.70,
        },
        "page_anchor_relation_ratio": {
            "target": 0.85,
            "value": metrics["source_anchor_relation_ratio"],
            "passed": metrics["source_anchor_relation_ratio"] >= 0.85,
        },
        "duplicate_entity_ratio": {
            "target_max": 0.10,
            "value": metrics["duplicate_entity_ratio"],
            "passed": metrics["duplicate_entity_ratio"] <= 0.10,
        },
        "orphan_entity_ratio": {
            "target_max": 0.20,
            "value": metrics["orphan_entity_ratio"],
            "passed": metrics["orphan_entity_ratio"] <= 0.20,
        },
    }
    graph = {
        "schema": GRAPH_SCHEMA,
        "built_at": _utc_now(),
        "name": "AIVSS-Agentic v0.8 — Page-Anchored Knowledge Graph",
        "description": (
            "Codex-created semantic graph over the complete 98-page AIVSS v0.8 "
            "source for evidence-grounded Q&A and deterministic score support."
        ),
        "source_manifest": {
            "source_name": manifest["source_name"],
            "source_pdf": manifest["source_pdf"],
            "page_count": manifest["page_count"],
            "source_fingerprint": manifest["source_fingerprint"],
        },
        "generation_contract": {
            "data_creator": "Codex",
            "semantic_nodes_and_relations_are_codex_generated": True,
            "source_evidence_is_verbatim_page_text": True,
            "source_text_rewritten": False,
            "database_mutated": False,
        },
        "proof_boundary": {
            "graph_supports": [
                "source-grounded AIVSS definitions",
                "risk and factor mapping",
                "scoring-method explanation",
                "deterministic arithmetic when inputs are supplied",
            ],
            "graph_does_not_prove": [
                "that a target system was assessed",
                "that a vulnerability exists",
                "that a mitigation is implemented or effective",
                "that an AIVSS score certifies a product",
            ],
        },
        "ontology": {
            "entity_types": sorted(entity_counts),
            "predicates": sorted(predicate_counts),
        },
        "nodes": nodes,
        "relations": relations,
        "links": relations,
        "metrics": metrics,
        "quality_gates": quality_gates,
    }
    return graph, manifest


def _decimal(value: float | int | str) -> Decimal:
    return Decimal(str(value))


def _validate_number(name: str, value: float, allowed: set[float]) -> float:
    number = float(value)
    if number not in allowed:
        allowed_label = ", ".join(str(item) for item in sorted(allowed))
        raise ValueError(f"{name} must be one of: {allowed_label}")
    return number


def calculate_aivss_from_sum(
    *,
    cvss_base: float,
    factor_sum: float,
    threat_multiplier: float = 0.97,
    mitigation_factor: float = 1.0,
) -> dict[str, Any]:
    cvss = float(cvss_base)
    total = float(factor_sum)
    if not 0.0 <= cvss <= 10.0:
        raise ValueError("cvss_base must be between 0.0 and 10.0")
    if not 0.0 <= total <= 10.0:
        raise ValueError("factor_sum must be between 0.0 and 10.0")
    thm = _validate_number(
        "threat_multiplier",
        threat_multiplier,
        {0.50, 0.97, 1.00},
    )
    mitigation = _validate_number(
        "mitigation_factor",
        mitigation_factor,
        {0.67, 0.83, 1.00},
    )
    risk_gap = _decimal(10) - _decimal(cvss)
    aars = risk_gap * (_decimal(total) / _decimal(10)) * _decimal(thm)
    raw = (_decimal(cvss) + aars) * _decimal(mitigation)
    final = raw.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    final_float = float(final)
    severity = (
        "Critical"
        if final_float >= 9.0
        else "High"
        if final_float >= 7.0
        else "Medium"
        if final_float >= 4.0
        else "Low"
        if final_float >= 0.1
        else "None"
    )
    return {
        "cvss_base": cvss,
        "risk_gap": float(risk_gap),
        "factor_sum": total,
        "threat_multiplier": thm,
        "aars": float(aars),
        "mitigation_factor": mitigation,
        "aivss_raw": float(raw),
        "aivss": final_float,
        "severity": severity,
        "authoritative_formulas": {
            "aars": "AARS = (10 - CVSS_Base) × (Factor_Sum / 10) × ThM",
            "aivss": (
                "AIVSS = (CVSS_Base + AARS) × Mitigation_Factor"
            ),
        },
        "rounding": "ROUND_HALF_UP to one decimal place",
        "source_pages": {
            "aars_formula": 51,
            "threat_multiplier": 52,
            "aivss_formula_and_mitigation": 53,
            "rounding_and_severity": 54,
        },
    }


def calculate_aivss(
    *,
    cvss_base: float,
    factors: dict[str, float],
    threat_multiplier: float = 0.97,
    mitigation_factor: float = 1.0,
) -> dict[str, Any]:
    required = {row["key"] for row in FACTOR_DEFINITIONS}
    provided = {str(key or "").strip().casefold().replace("-", "_") for key in factors}
    missing = sorted(required - provided)
    extra = sorted(provided - required)
    if missing or extra:
        raise ValueError(f"factor keys mismatch; missing={missing}, extra={extra}")
    normalized: dict[str, float] = {}
    for key, value in factors.items():
        normalized_key = str(key).strip().casefold().replace("-", "_")
        normalized[normalized_key] = _validate_number(
            normalized_key,
            float(value),
            {0.0, 0.5, 1.0},
        )
    result = calculate_aivss_from_sum(
        cvss_base=cvss_base,
        factor_sum=sum(normalized.values()),
        threat_multiplier=threat_multiplier,
        mitigation_factor=mitigation_factor,
    )
    result["factors"] = normalized
    return result


def parse_aivss_calculation_request(query: str) -> dict[str, Any] | None:
    text = str(query or "")
    cvss_match = CALC_CVSS_RE.search(text)
    factor_sum_match = CALC_FACTOR_SUM_RE.search(text)
    if not cvss_match or not factor_sum_match:
        return None
    thm_match = CALC_THM_RE.search(text)
    mitigation_match = CALC_MITIGATION_RE.search(text)
    lower = text.casefold()
    threat_multiplier = (
        float(thm_match.group("value"))
        if thm_match
        else 1.0
        if re.search(r"\battacked\b|โจมตีจริง|active(?:ly)? exploited", lower)
        else 0.5
        if re.search(r"\bunreported\b|ยังไม่มี exploit|theoretical", lower)
        else 0.97
    )
    mitigation_factor = (
        float(mitigation_match.group("value"))
        if mitigation_match
        else 0.67
        if re.search(r"strong mitigation|มาตรการเข้มแข็ง", lower)
        else 0.83
        if re.search(r"partial mitigation|มาตรการบางส่วน", lower)
        else 1.0
    )
    result = calculate_aivss_from_sum(
        cvss_base=float(cvss_match.group("value")),
        factor_sum=float(factor_sum_match.group("value")),
        threat_multiplier=threat_multiplier,
        mitigation_factor=mitigation_factor,
    )
    result["defaults_applied"] = {
        "threat_multiplier": not bool(thm_match),
        "mitigation_factor": not bool(mitigation_match),
    }
    return result


def _tokens(value: object) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in TOKEN_RE.findall(str(value or "").casefold()):
        token = raw.strip(" .,:;()[]{}'\"")
        if len(token) < 2 or token in STOPWORDS or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out[:96]


def _query_terms(query: str) -> list[str]:
    values = [str(query or "").casefold(), *_tokens(query)]
    lower = str(query or "").casefold()
    for triggers, expansions in QUERY_EXPANSIONS:
        if any(trigger.casefold() in lower for trigger in triggers):
            values.extend(expansions)
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        for value in (str(raw).strip().casefold(), *_tokens(raw)):
            if len(value) < 2 or value in STOPWORDS or value in seen:
                continue
            seen.add(value)
            out.append(value)
    return out[:128]


def _node_score(
    node: dict[str, Any],
    terms: list[str],
    query: str,
) -> tuple[float, list[str]]:
    fields = [
        node.get("name"),
        node.get("description"),
        " ".join(node.get("aliases") or []),
        node.get("evidence_span"),
        json.dumps(node.get("properties") or {}, ensure_ascii=False),
    ]
    hay = " ".join(str(value or "") for value in fields).casefold()
    if not hay:
        return 0.0, []
    hits: list[str] = []
    score = 0.0
    for term in terms:
        if term and term in hay:
            hits.append(term)
            score += 3.0 if " " in term else 1.6 if len(term) >= 7 else 1.0
    normalized_query = _normalize_name(query)
    normalized_name = _normalize_name(node.get("name"))
    if normalized_query and normalized_name:
        if normalized_query == normalized_name:
            score += 20.0
        elif normalized_name in normalized_query or normalized_query in normalized_name:
            score += 7.0
    query_lower = str(query or "").casefold()
    entity_type = str(node.get("entity_type") or "")
    if entity_type == "Risk" and (
        "ความเสี่ยงหลัก" in query_lower
        or "core security risk" in query_lower
        or (
            "10" in query_lower
            and any(term in query_lower for term in ("risk", "ความเสี่ยง"))
            and not any(term in query_lower for term in ("factor", "ปัจจัย"))
        )
    ):
        score += 18.0
    if entity_type == "MitigationStrength" and any(
        term in query_lower
        for term in ("mitigation", "มาตรการลด", "การบรรเทา")
    ):
        score += 18.0
    if entity_type == "SeverityBand" and any(
        term in query_lower
        for term in ("severity", "ระดับความรุนแรง", "critical", "medium", "low")
    ):
        score += 18.0
    type_boost = {
        "Formula": 2.5,
        "Risk": 2.2,
        "RiskFactor": 2.2,
        "ScoringMetric": 2.0,
        "ScoringExample": 1.8,
        "MitigationStrength": 2.2,
        "SeverityBand": 2.2,
        "ThreatMaturity": 2.0,
        "FactorScoreLevel": 1.8,
        "ThreatCategory": 1.7,
        "ArchitectureLayer": 1.7,
        "Role": 1.5,
        "Framework": 1.4,
        "Topic": 0.8,
        "EvidenceSpan": 0.25,
        "PageIndex": 0.1,
        "Document": 0.5,
    }.get(entity_type, 1.0)
    return round(score * type_boost, 5), hits[:20]


def _source_state(source_dir: Path | str) -> tuple[int, int]:
    _, pdf_path, text_paths = _source_paths(source_dir)
    paths = [pdf_path, *text_paths]
    return (
        max(int(path.stat().st_mtime_ns) for path in paths),
        sum(int(path.stat().st_size) for path in paths),
    )


@lru_cache(maxsize=8)
def _load_graph_cached(
    graph_path_text: str,
    graph_modified_ns: int,
    source_dir_text: str,
    source_modified_ns: int,
    source_total_bytes: int,
) -> dict[str, Any]:
    del graph_modified_ns, source_modified_ns, source_total_bytes
    graph_path = Path(graph_path_text)
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    if not isinstance(graph, dict) or graph.get("schema") != GRAPH_SCHEMA:
        raise ValueError(f"Unsupported AIVSS graph artifact: {graph_path}")
    manifest_path = graph_path.with_name("source_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    current = build_source_manifest(source_dir_text)
    expected_fingerprint = str(current.get("source_fingerprint") or "")
    if (
        str(manifest.get("source_fingerprint") or "") != expected_fingerprint
        or str((graph.get("source_manifest") or {}).get("source_fingerprint") or "")
        != expected_fingerprint
    ):
        raise ValueError("AIVSS source changed; rebuild the graph before serving it")
    failed = [
        key
        for key, gate in (graph.get("quality_gates") or {}).items()
        if isinstance(gate, dict) and not bool(gate.get("passed"))
    ]
    if failed:
        raise ValueError(f"AIVSS graph quality gates failed: {failed}")
    return graph


def load_aivss_graph(
    graph_path: Path | str = DEFAULT_GRAPH_PATH,
    *,
    source_dir: Path | str = DEFAULT_SOURCE_DIR,
) -> dict[str, Any]:
    path = Path(graph_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"AIVSS graph artifact not found: {path}; "
            "run python scripts/build_aivss_kg.py"
        )
    source_root = Path(source_dir).resolve()
    source_mtime, source_bytes = _source_state(source_root)
    return _load_graph_cached(
        str(path),
        int(path.stat().st_mtime_ns),
        str(source_root),
        source_mtime,
        source_bytes,
    )


def search_aivss_graph(
    query: str,
    *,
    graph_path: Path | str = DEFAULT_GRAPH_PATH,
    source_dir: Path | str = DEFAULT_SOURCE_DIR,
    limit: int = 10,
    relation_limit: int = 18,
    max_chars: int = 14000,
) -> dict[str, Any]:
    try:
        graph = load_aivss_graph(graph_path, source_dir=source_dir)
    except Exception as exc:
        return {
            "status": "not_ready",
            "query": str(query or ""),
            "results": [],
            "relations": [],
            "context": "",
            "error": f"{type(exc).__name__}: {exc}",
            "meta": {"result_count": 0, "relation_count": 0},
        }
    terms = _query_terms(str(query or ""))
    scored: list[tuple[float, list[str], dict[str, Any]]] = []
    for node in graph.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        score, hits = _node_score(node, terms, str(query or ""))
        if score > 0:
            scored.append((score, hits, node))
    scored.sort(
        key=lambda item: (
            -item[0],
            1 if item[2].get("entity_type") in {"EvidenceSpan", "PageIndex"} else 0,
            str(item[2].get("name") or "").casefold(),
        )
    )
    capped_limit = max(2, min(int(limit or 10), 20))
    semantic_candidates = [
        item
        for item in scored
        if item[2].get("entity_type") not in {"EvidenceSpan", "PageIndex"}
    ]
    query_lower = str(query or "").casefold()
    preferred_type = ""
    preferred_count = 0
    if (
        "ความเสี่ยงหลัก" in query_lower
        or "core security risk" in query_lower
        or (
            "10" in query_lower
            and any(term in query_lower for term in ("risk", "ความเสี่ยง"))
            and not any(term in query_lower for term in ("factor", "ปัจจัย"))
        )
    ):
        preferred_type = "Risk"
        preferred_count = 10
    elif (
        any(term in query_lower for term in ("factor", "ปัจจัย"))
        and any(term in query_lower for term in ("10", "catalog", "มีอะไรบ้าง"))
    ):
        preferred_type = "RiskFactor"
        preferred_count = 10
    if preferred_type:
        preferred = [
            item
            for item in semantic_candidates
            if item[2].get("entity_type") == preferred_type
        ][: min(preferred_count, capped_limit)]
        preferred_ids = {str(item[2].get("id") or "") for item in preferred}
        semantic = preferred + [
            item
            for item in semantic_candidates
            if str(item[2].get("id") or "") not in preferred_ids
        ][: max(0, capped_limit - len(preferred))]
    else:
        semantic = semantic_candidates[: max(2, capped_limit // 2)]
    evidence = [
        item
        for item in scored
        if item[2].get("entity_type") == "EvidenceSpan"
    ][: max(3, capped_limit - len(semantic))]
    selected = semantic + evidence
    selected.sort(key=lambda item: -item[0])
    selected = selected[:capped_limit]
    selected_ids = {str(item[2].get("id") or "") for item in selected}
    node_by_id = {
        str(node.get("id") or ""): node
        for node in graph.get("nodes") or []
        if isinstance(node, dict)
    }
    relation_candidates: list[tuple[int, float, dict[str, Any]]] = []
    neighbors: set[str] = set()
    for relation in graph.get("relations") or []:
        source = str(relation.get("source") or "")
        target = str(relation.get("target") or "")
        match_count = int(source in selected_ids) + int(target in selected_ids)
        if not match_count:
            continue
        candidate = dict(relation)
        candidate["_hop"] = 1
        relation_candidates.append(
            (match_count, float(relation.get("confidence") or 0), candidate)
        )
        neighbors.update((source, target))
    one_hop_ids = {str(row[2].get("id") or "") for row in relation_candidates}
    allowed_second_hop = {
        "amplified_by", "requires", "calculates", "maps_to", "primary_maps_to",
        "overlaps_with", "illustrated_by", "responsible_for", "defines_value_for",
    }
    for relation in graph.get("relations") or []:
        if (
            str(relation.get("id") or "") in one_hop_ids
            or str(relation.get("predicate") or "") not in allowed_second_hop
        ):
            continue
        source = str(relation.get("source") or "")
        target = str(relation.get("target") or "")
        if source not in neighbors and target not in neighbors:
            continue
        candidate = dict(relation)
        candidate["_hop"] = 2
        relation_candidates.append(
            (0, float(relation.get("confidence") or 0), candidate)
        )
    predicate_rank = {
        "calculates": 0,
        "requires": 1,
        "amplified_by": 2,
        "primary_maps_to": 3,
        "maps_to": 4,
        "overlaps_with": 5,
        "illustrated_by": 6,
        "responsible_for": 7,
        "defines_value_for": 8,
        "defines": 9,
        "source_page": 10,
        "has_evidence": 11,
        "contains_page": 12,
    }
    relation_candidates.sort(
        key=lambda item: (
            predicate_rank.get(str(item[2].get("predicate") or ""), 99),
            int(item[2].get("_hop") or 1),
            -item[0],
            -item[1],
        )
    )
    selected_relations: list[dict[str, Any]] = []
    relation_keys: set[tuple[str, str, str]] = set()
    for _, _, relation in relation_candidates:
        key = (
            str(relation.get("source") or ""),
            str(relation.get("predicate") or ""),
            str(relation.get("target") or ""),
        )
        if key in relation_keys:
            continue
        relation_keys.add(key)
        selected_relations.append(relation)
        if len(selected_relations) >= max(2, min(int(relation_limit or 18), 30)):
            break

    results: list[dict[str, Any]] = []
    for score, hits, node in selected:
        results.append(
            {
                "id": node.get("id"),
                "name": node.get("name"),
                "entity_type": node.get("entity_type"),
                "description": node.get("description"),
                "evidence_span": node.get("evidence_span"),
                "source_anchor": node.get("source_anchor"),
                "properties": node.get("properties") or {},
                "score": score,
                "matched_terms": hits,
            }
        )
    relation_results: list[dict[str, Any]] = []
    for relation in selected_relations:
        source = node_by_id.get(str(relation.get("source") or ""), {})
        target = node_by_id.get(str(relation.get("target") or ""), {})
        relation_results.append(
            {
                "source": source.get("name") or relation.get("source"),
                "predicate": relation.get("predicate"),
                "target": target.get("name") or relation.get("target"),
                "source_anchor": relation.get("source_anchor"),
                "evidence_span": relation.get("evidence_span"),
                "confidence": relation.get("confidence"),
                "hop": int(relation.get("_hop") or 1),
            }
        )
    calculation = None
    try:
        calculation = parse_aivss_calculation_request(str(query or ""))
    except ValueError as exc:
        calculation = {"error": str(exc)}

    lines = [
        "[AIVSS-Agentic v0.8 Knowledge Graph]",
        "authority: selected local AIVSS v0.8 PDF, compiled into page-anchored graph data by Codex.",
        (
            "citation_contract: use physical PDF page numbers shown below; "
            "printed footer numbers are one lower."
        ),
        (
            "proof_boundary: graph evidence explains the framework and its "
            "scoring method; it does not prove a system was assessed, a "
            "vulnerability exists, or a mitigation is effective."
        ),
        f"source_pdf_sha256: {(graph.get('source_manifest') or {}).get('source_pdf', {}).get('sha256')}",
        f"query: {str(query or '').strip()}",
    ]
    if preferred_type == "Risk":
        lines.extend(
            [
                "",
                (
                    "authoritative_catalog_contract: the source defines exactly "
                    "the following 10 AIVSS core risks. Reproduce these names; "
                    "do not substitute, infer, reorder by severity, or invent "
                    "another catalog entry."
                ),
                *[
                    (
                        f"{index}. {risk['name']} "
                        f"[physical pp.{risk['start_page']}–{risk['end_page']}]"
                    )
                    for index, risk in enumerate(RISK_DEFINITIONS, start=1)
                ],
            ]
        )
    elif preferred_type == "RiskFactor":
        lines.extend(
            [
                "",
                (
                    "authoritative_catalog_contract: the source defines exactly "
                    "the following 10 amplification factors. Reproduce these "
                    "names; do not substitute or invent another factor."
                ),
                *[
                    f"{index}. {factor['name']} ({factor['short']}) [physical pp.46–47]"
                    for index, factor in enumerate(FACTOR_DEFINITIONS, start=1)
                ],
            ]
        )
    if calculation:
        lines.extend(
            [
                "",
                "Deterministic AIVSS calculation:",
                json.dumps(calculation, ensure_ascii=False, sort_keys=True),
                (
                    "authoritative_formula_contract: reproduce both formulas "
                    "exactly as written in the calculation packet. Parentheses "
                    "are material: multiply Mitigation_Factor by the complete "
                    "(CVSS_Base + AARS) sum. Never render or calculate "
                    "CVSS_Base + (AARS × Mitigation_Factor)."
                ),
                (
                    "calculation_source: physical pp.51–54 "
                    "(AARS, ThM, AIVSS equation, mitigation, rounding, severity)."
                ),
            ]
        )
    lines.extend(["", "Selected page-anchored nodes and evidence:"])
    for index, row in enumerate(results, start=1):
        anchor = row.get("source_anchor") or {}
        evidence_text = _clean_inline(
            row.get("evidence_span") or row.get("description"),
            760,
        )
        lines.extend(
            [
                f"{index}. [{row.get('entity_type')}] {row.get('name')}",
                f"   evidence: {evidence_text}",
                (
                    f"   source: {anchor.get('source_pdf')} physical p."
                    f"{anchor.get('physical_page')} "
                    f"(printed p.{anchor.get('printed_page')})"
                ),
                f"   source_text: {anchor.get('source_text_file')}",
            ]
        )
    if relation_results:
        lines.extend(["", "Relevant graph relations (maximum two hops):"])
        for row in relation_results:
            anchor = row.get("source_anchor") or {}
            lines.append(
                "- "
                f"{row.get('source')} -> {row.get('predicate')} -> "
                f"{row.get('target')} [hop {row.get('hop')}; "
                f"physical p.{anchor.get('physical_page')}]"
            )
    context = "\n".join(lines).strip()
    if len(context) > max_chars:
        kept: list[str] = []
        current = 0
        for line in lines:
            additional = len(line) + (1 if kept else 0)
            if current + additional > max_chars - 60:
                break
            kept.append(line)
            current += additional
        kept.append("[bounded at AIVSS KG context limit]")
        context = "\n".join(kept)
    return {
        "status": "ready" if results else "no_match",
        "query": str(query or ""),
        "query_terms": terms,
        "results": results,
        "relations": relation_results,
        "calculation": calculation,
        "context": context if results or calculation else "",
        "meta": {
            "result_count": len(results),
            "relation_count": len(relation_results),
            "context_chars": len(context) if results or calculation else 0,
            "graph_nodes": int((graph.get("metrics") or {}).get("nodes") or 0),
            "graph_relations": int(
                (graph.get("metrics") or {}).get("relations") or 0
            ),
            "source_fingerprint": (
                graph.get("source_manifest") or {}
            ).get("source_fingerprint"),
            "source_pdf_sha256": (
                graph.get("source_manifest") or {}
            ).get("source_pdf", {}).get("sha256"),
            "source_anchor_node_ratio": (
                graph.get("metrics") or {}
            ).get("source_anchor_node_ratio"),
            "source_anchor_relation_ratio": (
                graph.get("metrics") or {}
            ).get("source_anchor_relation_ratio"),
            "proof_boundary": graph.get("proof_boundary") or {},
        },
    }


EVALUATION_CASES: tuple[dict[str, Any], ...] = (
    {"id": "risk_catalog", "question": "AIVSS มีความเสี่ยงหลัก 10 ข้ออะไรบ้าง", "expected_types": {"Risk"}, "pages": {5}},
    {"id": "tool_misuse", "question": "Agentic AI Tool Misuse คืออะไรและมีความเสี่ยงด้าน MCP อย่างไร", "expected_names": {"Agentic AI Tool Misuse"}, "pages": set(range(5, 11))},
    {"id": "factor_catalog", "question": "ปัจจัยขยายความเสี่ยง AIVSS 10 factors มีอะไรบ้าง", "expected_types": {"RiskFactor"}, "pages": {45, 46, 47}},
    {"id": "formula", "question": "สูตรคำนวณ AARS และ AIVSS ใช้ CVSS Factor_Sum ThM อย่างไร", "expected_types": {"Formula", "ScoringMetric"}, "pages": {51, 52, 53}},
    {"id": "mitigation", "question": "Mitigation Factor strong partial weak มีค่าเท่าไร", "expected_types": {"MitigationStrength"}, "pages": {53, 54}},
    {"id": "severity", "question": "ระดับความรุนแรง Critical High Medium Low ของ AIVSS", "expected_types": {"SeverityBand"}, "pages": {54}},
    {"id": "ordinal", "question": "ทำไมจึงไม่ควรเฉลี่ยคะแนน AIVSS และต้องอ่าน severity band", "pages": {50, 51}},
    {"id": "roles", "question": "ใครมีบทบาทรับผิดชอบการประเมิน AIVSS", "expected_types": {"Role"}, "pages": {67, 68, 69, 70}},
    {"id": "release_gate", "question": "AIVSS release gate ก่อนขึ้น production และคณะกรรมการอนุมัติ", "expected_names": {"AI Governance Board", "AI Risk Classification Committee"}, "pages": {69, 70}},
    {"id": "frameworks", "question": "AIVSS เชื่อม NIST AI RMF ISO 27001 และ risk register อย่างไร", "expected_types": {"Framework"}, "pages": {71, 72, 73, 74}},
    {"id": "asi_mapping", "question": "ASI06 Memory Context Poisoning map ไป AIVSS risk ใด", "expected_names": {"ASI06 Memory & Context Poisoning"}, "pages": {94, 95}},
    {"id": "maestro", "question": "CSA MAESTRO Layer 7 Agent Ecosystem map กับ AIVSS อย่างไร", "expected_types": {"ArchitectureLayer"}, "pages": {96}},
)


def evaluate_aivss_graph(
    graph_path: Path | str = DEFAULT_GRAPH_PATH,
    *,
    source_dir: Path | str = DEFAULT_SOURCE_DIR,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case in EVALUATION_CASES:
        result = search_aivss_graph(
            str(case["question"]),
            graph_path=graph_path,
            source_dir=source_dir,
            limit=12,
            relation_limit=20,
            max_chars=10000,
        )
        results = result.get("results") or []
        result_types = {str(row.get("entity_type") or "") for row in results}
        result_names = {str(row.get("name") or "") for row in results}
        result_pages = {
            int((row.get("source_anchor") or {}).get("physical_page") or 0)
            for row in results
        }
        anchored = bool(results) and all(
            int((row.get("source_anchor") or {}).get("physical_page") or 0) > 0
            and (row.get("source_anchor") or {}).get("source_pdf_sha256")
            for row in results
        )
        type_ok = not case.get("expected_types") or bool(
            set(case["expected_types"]).intersection(result_types)
        )
        name_ok = not case.get("expected_names") or bool(
            set(case["expected_names"]).intersection(result_names)
        )
        page_ok = bool(set(case.get("pages") or set()).intersection(result_pages))
        passed = (
            result.get("status") == "ready"
            and anchored
            and type_ok
            and name_ok
            and page_ok
        )
        rows.append(
            {
                "id": case["id"],
                "question": case["question"],
                "result_count": len(results),
                "result_types": sorted(result_types),
                "result_pages": sorted(result_pages),
                "anchored": anchored,
                "type_ok": type_ok,
                "name_ok": name_ok,
                "page_ok": page_ok,
                "passed": passed,
            }
        )
    passed_count = sum(1 for row in rows if row["passed"])
    return {
        "schema": "rag.aivss-kg-evaluation.v1",
        "evaluated_at": _utc_now(),
        "case_count": len(rows),
        "passed_count": passed_count,
        "route_evidence_coverage": round(passed_count / max(len(rows), 1), 4),
        "passed": passed_count == len(rows),
        "results": rows,
    }


def _render_report(
    graph: dict[str, Any],
    manifest: dict[str, Any],
    evaluation: dict[str, Any],
) -> str:
    metrics = graph.get("metrics") or {}
    lines = [
        "# AIVSS-Agentic v0.8 Knowledge Graph",
        "",
        f"- Built at: `{graph.get('built_at')}`",
        f"- Source PDF: `{(manifest.get('source_pdf') or {}).get('source_file')}`",
        f"- Source PDF SHA-256: `{(manifest.get('source_pdf') or {}).get('sha256')}`",
        f"- Source fingerprint: `{manifest.get('source_fingerprint')}`",
        "- Graph/data creator: `Codex`",
        "- Source mutation: `none`",
        "- Citation unit: physical PDF page; printed footer page is retained separately.",
        "",
        "## Graph metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key in (
        "documents", "pages", "evidence_spans", "risks", "risk_factors",
        "scoring_metrics", "roles", "frameworks", "asi_threat_categories",
        "maestro_layers", "nodes", "relations", "source_anchor_node_ratio",
        "source_anchor_relation_ratio", "duplicate_entity_ratio",
        "orphan_entity_ratio",
    ):
        lines.append(f"| {key} | {metrics.get(key)} |")
    lines.extend(
        [
            "",
            "## Quality gates",
            "",
            "| Gate | Value | Target | Pass |",
            "|---|---:|---:|:---:|",
        ]
    )
    for name, gate in (graph.get("quality_gates") or {}).items():
        lines.append(
            f"| {name} | {gate.get('value')} | "
            f"{gate.get('target', gate.get('target_max'))} | "
            f"{'yes' if gate.get('passed') else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Isolated retrieval evaluation",
            "",
            "| Case | Pages | Anchored | Pass |",
            "|---|---|:---:|:---:|",
        ]
    )
    for row in evaluation.get("results") or []:
        lines.append(
            f"| {row.get('id')} | "
            f"{', '.join(str(page) for page in row.get('result_pages') or [])} | "
            f"{'yes' if row.get('anchored') else 'no'} | "
            f"{'yes' if row.get('passed') else 'no'} |"
        )
    lines.extend(
        [
            "",
            f"Route-evidence coverage: `{evaluation.get('route_evidence_coverage')}`",
            "",
            "## Usage",
            "",
            "```bash",
            "python scripts/build_aivss_kg.py",
            "python scripts/build_aivss_kg.py --check",
            "python scripts/test_aivss_kg.py",
            "```",
            "",
            "Select `Agents AIVSS` in Chat or mention `agents_AIVSS`; the old `agents_AVISS` form is a compatibility alias.",
            "",
            "## Proof boundary",
            "",
            "The graph explains AIVSS v0.8 and can calculate a score from supplied inputs. "
            "It is not evidence that a target was tested, that a vulnerability exists, "
            "that a mitigation is effective, or that a product is certified.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temp_path, path)


def write_aivss_artifacts(
    source_dir: Path | str = DEFAULT_SOURCE_DIR,
    output_dir: Path | str = DEFAULT_ARTIFACT_DIR,
) -> dict[str, Any]:
    graph, manifest = build_aivss_graph(source_dir)
    output = Path(output_dir).resolve()
    _write_json(output / "graph.json", graph)
    _write_json(output / "source_manifest.json", manifest)
    _load_graph_cached.cache_clear()
    evaluation = evaluate_aivss_graph(
        output / "graph.json",
        source_dir=source_dir,
    )
    _write_json(output / "evaluation.json", evaluation)
    (output / "report.md").write_text(
        _render_report(graph, manifest, evaluation),
        encoding="utf-8",
    )
    quality_passed = all(
        bool(gate.get("passed"))
        for gate in (graph.get("quality_gates") or {}).values()
        if isinstance(gate, dict)
    )
    return {
        "output_dir": str(output),
        "graph_path": str(output / "graph.json"),
        "manifest_path": str(output / "source_manifest.json"),
        "evaluation_path": str(output / "evaluation.json"),
        "report_path": str(output / "report.md"),
        "metrics": graph["metrics"],
        "quality_gates": graph["quality_gates"],
        "route_evidence_coverage": evaluation["route_evidence_coverage"],
        "evaluation_passed": evaluation["passed"],
        "source_fingerprint": manifest["source_fingerprint"],
        "passed": bool(quality_passed and evaluation["passed"]),
    }


def check_aivss_artifacts(
    source_dir: Path | str = DEFAULT_SOURCE_DIR,
    output_dir: Path | str = DEFAULT_ARTIFACT_DIR,
) -> dict[str, Any]:
    output = Path(output_dir).resolve()
    graph_path = output / "graph.json"
    manifest_path = output / "source_manifest.json"
    if not graph_path.is_file() or not manifest_path.is_file():
        return {
            "passed": False,
            "error": "AIVSS artifacts are missing; run the build command",
            "output_dir": str(output),
        }
    try:
        graph = load_aivss_graph(graph_path, source_dir=source_dir)
        evaluation = evaluate_aivss_graph(
            graph_path,
            source_dir=source_dir,
        )
        current_manifest = build_source_manifest(source_dir)
        stored_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        fingerprint_matches = (
            stored_manifest.get("source_fingerprint")
            == current_manifest.get("source_fingerprint")
        )
        quality_passed = all(
            bool(gate.get("passed"))
            for gate in (graph.get("quality_gates") or {}).values()
            if isinstance(gate, dict)
        )
        return {
            "passed": bool(
                fingerprint_matches
                and quality_passed
                and evaluation.get("passed")
            ),
            "fingerprint_matches": fingerprint_matches,
            "quality_passed": quality_passed,
            "evaluation_passed": bool(evaluation.get("passed")),
            "route_evidence_coverage": evaluation.get(
                "route_evidence_coverage"
            ),
            "metrics": graph.get("metrics") or {},
            "source_fingerprint": current_manifest.get("source_fingerprint"),
            "output_dir": str(output),
        }
    except Exception as exc:
        return {
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
            "output_dir": str(output),
        }


__all__ = [
    "DEFAULT_ARTIFACT_DIR",
    "DEFAULT_GRAPH_PATH",
    "DEFAULT_SOURCE_DIR",
    "FACTOR_DEFINITIONS",
    "GRAPH_SCHEMA",
    "RISK_DEFINITIONS",
    "build_aivss_graph",
    "build_source_manifest",
    "calculate_aivss",
    "calculate_aivss_from_sum",
    "check_aivss_artifacts",
    "evaluate_aivss_graph",
    "load_aivss_graph",
    "parse_aivss_calculation_request",
    "search_aivss_graph",
    "write_aivss_artifacts",
]
