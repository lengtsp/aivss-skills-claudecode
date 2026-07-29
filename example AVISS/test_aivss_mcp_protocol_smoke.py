#!/usr/bin/env python3
"""Real MCP-protocol smoke test for aivss_mcp_server.py.

Unlike `test_aivss_mcp_server.py` (which calls the `@mcp.tool()`-decorated
Python functions directly, in-process — fast, no subprocess), this spawns
the server as a real subprocess over stdio and drives it through the actual
MCP client protocol: `initialize` -> `list_tools` -> `call_tool` per tool.
This is what a real MCP client (Claude Code, another agent) actually does,
so it catches things direct function calls can't: JSON-RPC serialization,
tool schema validity, subprocess startup failures, stdout pollution
breaking the stdio framing.

**Not part of the fast "Verify before/after any change" command list** in
README.md — it's slower (spawns a subprocess, real asyncio round-trips) and
only needs to run when `aivss_mcp_server.py` itself changes, not on every
edit to the underlying skill modules (those are already covered by
`test_aivss_mcp_server.py`'s in-process calls). Requires `mcp` installed
(already present in the `base` conda env — see the `env-mcp-python-sdk-
available` note) and the server to actually launch cleanly with `python3`.

**Wire-format finding from authoring this (2026-07-28), documented in
README.md "Tested via the real MCP protocol":** a tool's `content` list and
`structuredContent` field are shaped differently depending on the Python
return type annotation:
- Plain `dict[str, Any]` return -> `structuredContent` IS the dict directly
  (not wrapped), `content` has exactly one TextContent block.
- `list[dict[str, Any]]` return -> `structuredContent` is `{"result": [...]}`,
  and `content` gets **one TextContent block per list item** — so reading
  only `content[0].text` silently truncates to the first item. This was
  caught live while writing this test: an early draft did exactly that and
  under-reported `aivss_search_spec`'s 3 hits as 1.
- `dict[str, Any] | None` (Optional/Union) return -> always wrapped as
  `{"result": ...}` (including `{"result": null}` for the None case, with
  zero `content` blocks). A caller must branch on this, not assume a flat
  dict.
The `_unwrap()` helper below normalizes all three shapes — always prefer
`structuredContent` over `content[].text` when consuming these tools.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PATH = str(Path(__file__).resolve().parent / "aivss_mcp_server.py")

_FACTOR_LEVELS = {
    "autonomy": 1.0, "tools": 1.0, "language": 1.0, "context": 1.0,
    "non_determinism": 0.5, "opacity": 1.0, "persistence": 0.5,
    "identity": 0.5, "multi_agent": 0.5, "self_mod": 0.0,
}

EXPECTED_TOOL_COUNT = 14


def _unwrap(structured: dict[str, Any] | None) -> Any:
    if structured is None:
        return None
    if list(structured.keys()) == ["result"]:
        return structured["result"]
    return structured


async def _run_checks(session: ClientSession) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    async def call(name: str, args: dict[str, Any], extractor: Callable[[Any], dict[str, Any]]) -> None:
        result = await session.call_tool(name, args)
        data = _unwrap(result.structuredContent)
        checks.append(
            {
                "tool": name,
                "passed": not result.isError,
                "content_blocks": len(result.content),
                **extractor(data),
            }
        )

    tools = await session.list_tools()
    tool_names = sorted(t.name for t in tools.tools)
    checks.append(
        {
            "tool": "list_tools",
            "passed": len(tool_names) == EXPECTED_TOOL_COUNT,
            "count": len(tool_names),
        }
    )

    await call(
        "aivss_intake_and_triage",
        {
            "role": "IT Internal Audit",
            "system_name": "Mobile Banking - AI Investment Advisory",
            "ai_capability_summary": "Chat-based robo-advisor; can call a fund-switch API.",
            "factor_hints": {"autonomy": 1.0, "tools": 1.0, "language": 1.0, "context": 1.0},
        },
        lambda d: {"ok": len(d["triage"]) == 10},
    )

    await call(
        "aivss_generate_questionnaire",
        {"risk_keys": ["goal_instruction", "tool_misuse"]},
        lambda d: {"ok": len(d["sections"]) == 2 and bool(d["markdown"])},
    )

    await call(
        "aivss_score_finding",
        {
            "risk_key": "goal_instruction",
            "finding_description": "prompt injection auto fund-switch",
            "cvss_base": 2.4,
            "factor_levels": _FACTOR_LEVELS,
        },
        lambda d: {"ok": d["aivss"] == 7.6 and d["severity"] == "High"},
    )

    await call(
        "aivss_assemble_audit_deliverable",
        {
            "role": "IT Internal Audit",
            "system_name": "Mobile Banking - AI Investment Advisory",
            "ai_capability_summary": "Chat-based robo-advisor; can call a fund-switch API.",
            "factor_hints": _FACTOR_LEVELS,
            "top_n": 3,
        },
        lambda d: {"ok": len(d["risks"]) == 10 and bool(d["markdown"])},
    )

    await call(
        "aivss_classify_banking_system",
        {"text": "unrelated text about the weather"},
        lambda d: {"ok": d is None},
    )
    await call(
        "aivss_classify_banking_system",
        {"text": "our robo-advisor investment advisory chatbot"},
        lambda d: {"ok": d is not None and d["archetype_key"] == "robo_advisor"},
    )

    await call(
        "aivss_search_spec",
        {"query": "prompt injection", "limit": 3},
        lambda d: {"ok": isinstance(d, list) and len(d) == 3},
    )
    await call(
        "aivss_cite_spec_reference",
        {"key_or_query": "goal_instruction", "limit": 2},
        lambda d: {"ok": isinstance(d, list) and len(d) >= 1},
    )

    await call(
        "aivss_design_review",
        {
            "role": "AI Security Lead",
            "system_name": "New Collections Agent (planned)",
            "ai_capability_summary": "Autonomous agent negotiating settlement offers via chat.",
            "factor_hints": {"autonomy": 1.0, "tools": 1.0, "persistence": 1.0},
            "top_n": 2,
        },
        lambda d: {"ok": len(d["sections"]) == 2},
    )

    await call(
        "aivss_triage_threat_alert",
        {"alert_text": "unrelated text about the weather"},
        lambda d: {"ok": d is None},
    )
    await call(
        "aivss_triage_threat_alert",
        {"alert_text": "new MCP tool poisoning combined with prompt injection disclosed"},
        lambda d: {"ok": d is not None and set(d["matched_risk_keys"]) >= {"tool_misuse", "goal_instruction"}},
    )

    await call(
        "aivss_draft_finding_rationale",
        {
            "risk_key": "goal_instruction",
            "finding_description": "prompt injection auto fund-switch",
            "cvss_base": 2.4,
            "factor_levels": _FACTOR_LEVELS,
            "org_controls": {"controls_in_place": ["server-side confirm gate (planned)"]},
        },
        lambda d: {"ok": d["evidence_gap"] is False},
    )

    await call(
        "aivss_spec_provenance_report",
        {},
        lambda d: {"ok": d["all_risks_verified"] and d["all_factors_verified"] and not d["page_count_drift"]},
    )

    await call(
        "aivss_related_risks",
        {"risk_key": "goal_instruction", "limit": 3},
        lambda d: {"ok": isinstance(d, list) and len(d) > 0 and "goal_instruction" not in [r["risk_key"] for r in d]},
    )

    await call(
        "aivss_find_blind_spot_risks",
        {"triaged_risk_keys": ["tool_misuse", "access_control"], "limit": 2},
        lambda d: {"ok": isinstance(d, list) and d and d[0]["risk_key"] == "supply_chain"},
    )

    await call(
        "aivss_graph_export",
        {"risk_keys": ["goal_instruction"]},
        lambda d: {"ok": bool(d["nodes"]) and bool(d["relations"])},
    )

    return checks


async def _main_async() -> dict[str, Any]:
    params = StdioServerParameters(command="python3", args=[SERVER_PATH])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            checks = await _run_checks(session)

    for check in checks:
        check["passed"] = bool(check.get("passed", True) and check.get("ok", True))

    return {
        "passed": all(c["passed"] for c in checks),
        "passed_count": sum(1 for c in checks if c["passed"]),
        "test_count": len(checks),
        "results": checks,
    }


def main() -> int:
    payload = asyncio.run(_main_async())
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
