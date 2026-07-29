#!/usr/bin/env python3
"""Deterministic contract tests for aivss_knowledge_graph.py.

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

from aivss_kg import FACTOR_DEFINITIONS, RISK_DEFINITIONS, RISK_FACTOR_MATRIX  # noqa: E402
from aivss_internal_audit import AUDIT_TOPICS  # noqa: E402
from aivss_banking_taxonomy import BANKING_SYSTEM_ARCHETYPES  # noqa: E402
from aivss_knowledge_graph import (  # noqa: E402
    NODE_TYPES,
    RELATION_TYPES,
    build_graph,
    export_kg_shape,
    find_blind_spot_risks,
    neighbors,
    related_risks,
    shortest_path,
    subgraph_for_scope,
    to_mermaid,
)


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_graph_node_counts_match_source_catalogs() -> None:
    g = build_graph()
    by_type: dict[str, int] = {}
    for node in g.nodes.values():
        by_type[node.type] = by_type.get(node.type, 0) + 1
        _assert(node.type in NODE_TYPES, node.type)

    _assert(by_type["risk"] == len(RISK_DEFINITIONS) == 10, by_type)
    _assert(by_type["factor"] == len(FACTOR_DEFINITIONS) == 10, by_type)
    _assert(by_type["audit_topic"] == len(AUDIT_TOPICS) == 10, by_type)
    _assert(by_type["banking_archetype"] == len(BANKING_SYSTEM_ARCHETYPES) == 5, by_type)
    expected_cobit = len({code for t in AUDIT_TOPICS for code in t["cobit_codes"]})
    _assert(by_type["cobit_code"] == expected_cobit, (by_type, expected_cobit))


def test_amplifies_edge_count_matches_risk_factor_matrix() -> None:
    g = build_graph()
    amplifies = [e for e in g.edges if e.relation == "amplifies"]
    expected = sum(len(factors) for factors in RISK_FACTOR_MATRIX.values())
    _assert(len(amplifies) == expected, (len(amplifies), expected))
    for edge in amplifies:
        _assert(edge.relation in RELATION_TYPES, edge.relation)
        _assert(edge.source.startswith("factor:"), edge.source)
        _assert(edge.target.startswith("risk:"), edge.target)


def test_neighbors_fails_closed_on_unknown_node() -> None:
    _assert(neighbors("risk:not_a_real_risk") == [], "unknown node must return []")
    # goal_instruction is the TARGET of its amplifying factors' edges
    # (factor -[amplifies]-> risk), so neighbors() must find them via the
    # target-side match, not just source-side.
    hits = neighbors("risk:goal_instruction", relations=("amplifies",))
    expected = set(RISK_FACTOR_MATRIX["goal_instruction"])
    found = {edge.source.split(":", 1)[1] for edge in hits}
    _assert(found == expected, (found, expected))


def test_related_risks_ranks_by_shared_connectivity() -> None:
    rows = related_risks("goal_instruction", limit=10)
    _assert(rows, "expected at least one related risk")
    keys = [row["risk_key"] for row in rows]
    _assert("goal_instruction" not in keys, "a risk must not be related to itself")
    weights = [row["weight"] for row in rows]
    _assert(weights == sorted(weights, reverse=True), weights)
    for row in rows:
        _assert(row["via"], row)
        _assert(all(v["relation"] in ("shares_factor_with", "shares_topic_with") for v in row["via"]), row)

    _assert(related_risks("not_a_real_risk") == [], "unknown risk key must fail closed to []")


def test_find_blind_spot_risks_aggregates_across_given_set() -> None:
    rows = find_blind_spot_risks(["tool_misuse", "access_control"], limit=5)
    _assert(rows, "expected at least one blind-spot candidate")
    keys = [row["risk_key"] for row in rows]
    _assert("tool_misuse" not in keys and "access_control" not in keys, keys)
    # supply_chain shares factors with both tool_misuse and access_control
    # (verified via aivss_knowledge_graph smoke test during authoring) -> must
    # rank first with connections to both.
    top = rows[0]
    _assert(top["risk_key"] == "supply_chain", rows)
    connected_keys = {c["risk_key"] for c in top["connected_to"]}
    _assert(connected_keys == {"tool_misuse", "access_control"}, top)

    _assert(find_blind_spot_risks([]) == [], "empty input must fail closed to []")
    _assert(find_blind_spot_risks(["", None]) == [], "blank/None entries must fail closed to []")  # type: ignore[list-item]


def test_shortest_path_finds_real_path_and_fails_closed() -> None:
    path = shortest_path("risk:goal_instruction", "cobit:EDM03.01")
    _assert(path is not None and path[0] == "risk:goal_instruction" and path[-1] == "cobit:EDM03.01", path)
    _assert(len(path) >= 2, path)

    _assert(shortest_path("risk:goal_instruction", "risk:goal_instruction") == ["risk:goal_instruction"], "same node")
    _assert(shortest_path("risk:goal_instruction", "not:a_real_node") is None, "unknown target must fail closed")
    _assert(shortest_path("not:a_real_node", "risk:goal_instruction") is None, "unknown source must fail closed")


def test_subgraph_for_scope_includes_one_hop_neighbors() -> None:
    sub = subgraph_for_scope(["goal_instruction"])
    node_ids = {node.id for node in sub["nodes"]}
    _assert("risk:goal_instruction" in node_ids, node_ids)
    for factor_key in RISK_FACTOR_MATRIX["goal_instruction"]:
        _assert(f"factor:{factor_key}" in node_ids, (factor_key, node_ids))

    _assert(subgraph_for_scope(["not_a_real_risk"])["nodes"] == [], "unknown risk key skipped defensively")
    _assert(subgraph_for_scope([])["nodes"] == [], "empty scope -> empty subgraph")


def test_to_mermaid_produces_flowchart_syntax() -> None:
    full = to_mermaid()
    _assert(full.startswith("flowchart LR"), full[:50])
    _assert("-->" in full, full[:200])

    scoped = to_mermaid(["goal_instruction"])
    _assert(scoped.startswith("flowchart LR"), scoped[:50])
    _assert(len(scoped) < len(full), "scoped diagram must be smaller than the full graph")


def test_export_kg_shape_matches_compatible_field_names() -> None:
    full = export_kg_shape()
    _assert(full["nodes"], "expected nodes")
    _assert(full["relations"], "expected relations")
    for node in full["nodes"][:5]:
        _assert(set(node.keys()) == {"entity_name", "entity_type", "label", "description"}, node)
    for relation in full["relations"][:5]:
        _assert(
            set(relation.keys())
            == {"source_entity", "target_entity", "relation_type", "weight", "description"},
            relation,
        )

    scoped = export_kg_shape(["goal_instruction"])
    _assert(len(scoped["nodes"]) < len(full["nodes"]), "scoped export must be smaller than full export")
    # round-trip through JSON to catch any non-serializable field
    json.dumps(scoped, ensure_ascii=False)


def main() -> int:
    tests = (
        test_graph_node_counts_match_source_catalogs,
        test_amplifies_edge_count_matches_risk_factor_matrix,
        test_neighbors_fails_closed_on_unknown_node,
        test_related_risks_ranks_by_shared_connectivity,
        test_find_blind_spot_risks_aggregates_across_given_set,
        test_shortest_path_finds_real_path_and_fails_closed,
        test_subgraph_for_scope_includes_one_hop_neighbors,
        test_to_mermaid_produces_flowchart_syntax,
        test_export_kg_shape_matches_compatible_field_names,
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
