"""Knowledge-graph-style reasoning over the AIVSS taxonomy.

Everything in this folder up to now models AIVSS relationships as flat,
independent lookups: `RISK_FACTOR_MATRIX` (`aivss_kg.py`) is
`risk_key -> tuple of factor_keys`; `AUDIT_TOPICS` (`aivss_internal_audit.py`)
is `topic -> risk_keys + cobit_codes`; `BANKING_SYSTEM_ARCHETYPES`
(`aivss_banking_taxonomy.py`) is `archetype -> factor_hints`. These are
already graph-shaped data — nodes with typed edges between them — that
nothing in this folder has ever explicitly modeled or queried as a graph.
This module adds that layer: an in-memory node/edge graph built from the
existing, already-verified data (no new facts authored, nothing invented),
with deterministic traversal functions for multi-hop reasoning a flat
per-risk lookup cannot answer — e.g. "which other risks are strongly
connected to this one, and why" (`related_risks`), or "given the risks I
already triaged as high, what connected risks might be a blind spot"
(`find_blind_spot_risks`).

**Not the main app's real Knowledge Graph.** `knowledge_graph.py` /
`neo4j_sync.py` / `routes_kg.py` / the `kg_nodes` / `kg_relations` DB tables
are a separate, LLM-driven entity/relation extraction system over uploaded
documents, live in the main app, and are out of this folder's scope per
README.md's hard scope rule. `export_kg_shape()` below produces data in a
*compatible shape* (`entity_name`/`entity_type`/`description`,
`source_entity`/`target_entity`/`relation_type`) so a future explicit
integration step could import this taxonomy into that real system — but
this module never touches the database, Neo4j, or any file outside
`example AVISS/`.

Graph size is small by construction (10 risks + 10 factors + 10 audit
topics + ~22 COBIT codes + 5 banking archetypes ≈ 57 nodes, ~41+ edges) —
traversal functions use plain BFS/dict lookups, no graph library dependency.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from aivss_kg import FACTOR_DEFINITIONS, RISK_DEFINITIONS, RISK_FACTOR_MATRIX
from aivss_internal_audit import AUDIT_TOPICS
from aivss_banking_taxonomy import BANKING_SYSTEM_ARCHETYPES
from aivss_assessment_skills import RISK_SUMMARIES

KNOWLEDGE_GRAPH_SCHEMA = "rag.aivss-knowledge-graph.v1"

NODE_TYPES = ("risk", "factor", "audit_topic", "cobit_code", "banking_archetype")
RELATION_TYPES = (
    "amplifies",           # factor -> risk
    "maps_to_topic",       # risk -> audit_topic
    "maps_to_control",     # audit_topic -> cobit_code
    "typical_for",         # banking_archetype -> factor
    "shares_factor_with",  # risk <-> risk (derived)
    "shares_topic_with",   # risk <-> risk (derived)
)


@dataclass(frozen=True)
class GraphNode:
    id: str
    type: str
    label: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    relation: str
    weight: float = 1.0
    detail: str = ""


@dataclass(frozen=True)
class AivssKnowledgeGraph:
    nodes: dict[str, GraphNode]
    edges: tuple[GraphEdge, ...]


def _risk_id(key: str) -> str:
    return f"risk:{key}"


def _factor_id(key: str) -> str:
    return f"factor:{key}"


def _topic_id(topic_id: str) -> str:
    return f"audit_topic:{topic_id}"


def _cobit_id(code: str) -> str:
    return f"cobit:{code}"


def _archetype_id(key: str) -> str:
    return f"archetype:{key}"


@lru_cache(maxsize=1)
def build_graph() -> AivssKnowledgeGraph:
    """Build the AIVSS taxonomy graph once (cached for process lifetime —
    every source is static reference data, same convention as
    `aivss_spec_search._load_pages`)."""

    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    for row in RISK_DEFINITIONS:
        key = row["key"]
        nodes[_risk_id(key)] = GraphNode(
            id=_risk_id(key),
            type="risk",
            label=row["name"],
            description=RISK_SUMMARIES.get(key, ""),
            metadata={
                "start_page": row.get("start_page"),
                "end_page": row.get("end_page"),
                "aliases": list(row.get("aliases") or ()),
            },
        )

    for row in FACTOR_DEFINITIONS:
        key = row["key"]
        nodes[_factor_id(key)] = GraphNode(
            id=_factor_id(key),
            type="factor",
            label=row["name"],
            description=row.get("description", ""),
            metadata={"short": row.get("short", "")},
        )

    for topic in AUDIT_TOPICS:
        nodes[_topic_id(topic["id"])] = GraphNode(
            id=_topic_id(topic["id"]),
            type="audit_topic",
            label=topic["label"],
            description=topic.get("audit_focus", ""),
        )

    for archetype in BANKING_SYSTEM_ARCHETYPES:
        nodes[_archetype_id(archetype.key)] = GraphNode(
            id=_archetype_id(archetype.key),
            type="banking_archetype",
            label=archetype.label,
            description=archetype.description,
        )

    seen_cobit: set[str] = set()
    for topic in AUDIT_TOPICS:
        for code in topic["cobit_codes"]:
            if code not in seen_cobit:
                seen_cobit.add(code)
                nodes[_cobit_id(code)] = GraphNode(
                    id=_cobit_id(code), type="cobit_code", label=code
                )

    # factor -[amplifies]-> risk
    for risk_key, factor_keys in RISK_FACTOR_MATRIX.items():
        for factor_key in factor_keys:
            edges.append(
                GraphEdge(
                    source=_factor_id(factor_key),
                    target=_risk_id(risk_key),
                    relation="amplifies",
                )
            )

    # risk -[maps_to_topic]-> audit_topic ; audit_topic -[maps_to_control]-> cobit_code
    for topic in AUDIT_TOPICS:
        for risk_key in topic["risk_keys"]:
            edges.append(
                GraphEdge(
                    source=_risk_id(risk_key),
                    target=_topic_id(topic["id"]),
                    relation="maps_to_topic",
                )
            )
        for code in topic["cobit_codes"]:
            edges.append(
                GraphEdge(
                    source=_topic_id(topic["id"]),
                    target=_cobit_id(code),
                    relation="maps_to_control",
                )
            )

    # banking_archetype -[typical_for]-> factor (only factors true by default
    # for that archetype, weighted by the archetype's own 0/0.5/1 level)
    for archetype in BANKING_SYSTEM_ARCHETYPES:
        for factor_key, level in archetype.default_factor_hints.items():
            if level > 0:
                edges.append(
                    GraphEdge(
                        source=_archetype_id(archetype.key),
                        target=_factor_id(factor_key),
                        relation="typical_for",
                        weight=level,
                    )
                )

    # Derived risk<->risk edges: shared amplifying factors / shared audit topics.
    risk_keys = [row["key"] for row in RISK_DEFINITIONS]
    factor_sets = {key: set(RISK_FACTOR_MATRIX.get(key, ())) for key in risk_keys}
    topic_sets: dict[str, set[str]] = {key: set() for key in risk_keys}
    for topic in AUDIT_TOPICS:
        for risk_key in topic["risk_keys"]:
            topic_sets[risk_key].add(topic["id"])

    for i, a in enumerate(risk_keys):
        for b in risk_keys[i + 1 :]:
            shared_factors = factor_sets[a] & factor_sets[b]
            if shared_factors:
                edges.append(
                    GraphEdge(
                        source=_risk_id(a),
                        target=_risk_id(b),
                        relation="shares_factor_with",
                        weight=float(len(shared_factors)),
                        detail=", ".join(sorted(shared_factors)),
                    )
                )
            shared_topics = topic_sets[a] & topic_sets[b]
            if shared_topics:
                edges.append(
                    GraphEdge(
                        source=_risk_id(a),
                        target=_risk_id(b),
                        relation="shares_topic_with",
                        weight=float(len(shared_topics)),
                        detail=", ".join(sorted(shared_topics)),
                    )
                )

    return AivssKnowledgeGraph(nodes=nodes, edges=tuple(edges))


def neighbors(
    node_id: str,
    *,
    relations: tuple[str, ...] | None = None,
    graph: AivssKnowledgeGraph | None = None,
) -> list[GraphEdge]:
    """Every edge touching `node_id` (either direction), optionally filtered
    to specific relation types. Returns [] for an unknown node id — fails
    closed, never guesses a connection."""

    g = graph or build_graph()
    if node_id not in g.nodes:
        return []
    allowed = set(relations) if relations else None
    return [
        edge
        for edge in g.edges
        if (edge.source == node_id or edge.target == node_id)
        and (allowed is None or edge.relation in allowed)
    ]


def related_risks(
    risk_key: str,
    *,
    via: tuple[str, ...] = ("shares_factor_with", "shares_topic_with"),
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Other AIVSS risks connected to `risk_key` via shared amplifying
    factors and/or shared audit topics, ranked by total connection weight.

    This is the core "graph thinking" query this module exists for: a flat
    per-risk lookup (e.g. `aivss_assessment_skills.triage_applicable_risks`)
    can tell you THIS risk's own applicability, but not which OTHER risks
    are structurally entangled with it — two risks sharing 3 amplifying
    factors will very plausibly co-occur in a real system, which a
    risk-by-risk assessment can silently miss. Returns [] for an unknown
    risk key.
    """

    g = build_graph()
    node_id = _risk_id(risk_key)
    if node_id not in g.nodes:
        return []

    scores: dict[str, dict[str, Any]] = {}
    for edge in neighbors(node_id, relations=via, graph=g):
        other = edge.target if edge.source == node_id else edge.source
        if not other.startswith("risk:"):
            continue
        other_key = other.split(":", 1)[1]
        row = scores.setdefault(
            other_key,
            {"risk_key": other_key, "name": g.nodes[other].label, "weight": 0.0, "via": []},
        )
        row["weight"] += edge.weight
        row["via"].append({"relation": edge.relation, "weight": edge.weight, "detail": edge.detail})

    ranked = sorted(scores.values(), key=lambda row: (-row["weight"], row["risk_key"]))
    return ranked[: max(1, int(limit))]


def find_blind_spot_risks(
    triaged_risk_keys: list[str],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Given a set of risk keys already surfaced by a triage/design review
    (e.g. the top-N from `triage_applicable_risks` or
    `generate_design_recommendations`), find OTHER risks (not already in the
    set) that are strongly connected to the given set via shared amplifying
    factors/audit topics — candidates worth a second look even though they
    didn't score into the top-N on their own.

    Aggregate connection weight = sum of `related_risks()` weight to every
    risk already in `triaged_risk_keys` (a candidate connected to 3 of the
    given risks outranks one connected to only 1, even at equal per-edge
    weight). Returns [] if `triaged_risk_keys` is empty or covers every risk
    already (nothing left to flag).
    """

    given = {key for key in triaged_risk_keys if key}
    if not given:
        return []

    totals: dict[str, dict[str, Any]] = {}
    for key in given:
        for row in related_risks(key, limit=len(RISK_DEFINITIONS)):
            candidate = row["risk_key"]
            if candidate in given:
                continue
            entry = totals.setdefault(
                candidate,
                {"risk_key": candidate, "name": row["name"], "weight": 0.0, "connected_to": []},
            )
            entry["weight"] += row["weight"]
            entry["connected_to"].append({"risk_key": key, "weight": row["weight"]})

    ranked = sorted(totals.values(), key=lambda row: (-row["weight"], row["risk_key"]))
    return ranked[: max(1, int(limit))]


def shortest_path(source_id: str, target_id: str) -> list[str] | None:
    """Plain BFS shortest path (edges treated as undirected, unweighted) —
    the graph is small enough (~57 nodes) that this needs no graph library.
    Returns None if either id is unknown or no path exists (never guesses)."""

    g = build_graph()
    if source_id not in g.nodes or target_id not in g.nodes:
        return None
    if source_id == target_id:
        return [source_id]

    adjacency: dict[str, set[str]] = {node_id: set() for node_id in g.nodes}
    for edge in g.edges:
        adjacency[edge.source].add(edge.target)
        adjacency[edge.target].add(edge.source)

    visited = {source_id}
    queue: deque[list[str]] = deque([[source_id]])
    while queue:
        path = queue.popleft()
        for neighbor_id in adjacency[path[-1]]:
            if neighbor_id == target_id:
                return path + [neighbor_id]
            if neighbor_id not in visited:
                visited.add(neighbor_id)
                queue.append(path + [neighbor_id])
    return None


def subgraph_for_scope(risk_keys: list[str]) -> dict[str, Any]:
    """Extract the slice of the graph reachable from the given risk keys in
    one hop (their amplifying factors, mapped audit topics/COBIT codes, and
    any other risks they share a factor/topic with) — a bounded view for
    rendering/export instead of the full ~57-node graph. Unknown risk keys
    are skipped defensively."""

    g = build_graph()
    keep_nodes: set[str] = set()
    keep_edges: list[GraphEdge] = []
    for key in risk_keys:
        node_id = _risk_id(key)
        if node_id not in g.nodes:
            continue
        keep_nodes.add(node_id)
        for edge in neighbors(node_id, graph=g):
            keep_nodes.add(edge.source)
            keep_nodes.add(edge.target)
            keep_edges.append(edge)

    return {
        "nodes": [g.nodes[node_id] for node_id in sorted(keep_nodes)],
        "edges": keep_edges,
    }


def to_mermaid(risk_keys: list[str] | None = None, *, max_edges: int = 60) -> str:
    """Render the graph (or a scope-limited subgraph) as a Mermaid
    flowchart. Deterministic string building only — no LLM, no rendering
    engine required to produce the diagram source itself."""

    if risk_keys:
        scoped = subgraph_for_scope(risk_keys)
        nodes = {node.id: node for node in scoped["nodes"]}
        edges = scoped["edges"]
    else:
        g = build_graph()
        nodes = g.nodes
        edges = list(g.edges)

    def sanitize(node_id: str) -> str:
        return node_id.replace(":", "_").replace(".", "_").replace("-", "_")

    lines = ["flowchart LR"]
    for node in nodes.values():
        shape = "([{}])" if node.type == "risk" else "[{}]"
        label = node.label.replace('"', "'")
        lines.append(f'    {sanitize(node.id)}{shape.format(label)}')
    for edge in edges[:max_edges]:
        if edge.source not in nodes or edge.target not in nodes:
            continue
        lines.append(
            f"    {sanitize(edge.source)} -- {edge.relation} --> {sanitize(edge.target)}"
        )
    return "\n".join(lines)


def export_kg_shape(risk_keys: list[str] | None = None) -> dict[str, Any]:
    """Export nodes/relations in a shape compatible with the main app's real
    Knowledge Graph tables (`kg_nodes`: entity_name/entity_type/description;
    `kg_relations`: source/target/relation_type/description) — for a future,
    explicit, out-of-this-folder integration step. Does not write to any
    database or call `neo4j_sync.py`/`routes_kg.py`."""

    if risk_keys:
        scoped = subgraph_for_scope(risk_keys)
        nodes = scoped["nodes"]
        edges = scoped["edges"]
    else:
        g = build_graph()
        nodes = list(g.nodes.values())
        edges = list(g.edges)

    return {
        "schema": KNOWLEDGE_GRAPH_SCHEMA,
        "nodes": [
            {
                "entity_name": node.id,
                "entity_type": node.type,
                "label": node.label,
                "description": node.description,
            }
            for node in nodes
        ],
        "relations": [
            {
                "source_entity": edge.source,
                "target_entity": edge.target,
                "relation_type": edge.relation,
                "weight": edge.weight,
                "description": edge.detail,
            }
            for edge in edges
        ],
    }


__all__ = [
    "KNOWLEDGE_GRAPH_SCHEMA",
    "NODE_TYPES",
    "RELATION_TYPES",
    "GraphNode",
    "GraphEdge",
    "AivssKnowledgeGraph",
    "build_graph",
    "neighbors",
    "related_risks",
    "find_blind_spot_risks",
    "shortest_path",
    "subgraph_for_scope",
    "to_mermaid",
    "export_kg_shape",
]
