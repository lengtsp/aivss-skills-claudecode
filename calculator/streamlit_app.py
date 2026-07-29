"""AIVSS Calculator (Streamlit) -- calls this repo's real aivss_kg.calculate_aivss()
directly. No formula is reimplemented here; if aivss_kg.py changes, this app's
output changes with it automatically, unlike index.html's JavaScript copy.

Run from this folder:
    streamlit run streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aivss_kg import calculate_aivss  # noqa: E402

FACTORS = [
    ("autonomy", "Autonomy", "Can the agent act without human approval?"),
    ("tools", "Tools", "Can the agent invoke external tools/APIs?"),
    ("language", "Language", "Does the agent take natural-language instructions?"),
    ("context", "Context", "How much environmental/document context feeds the decision?"),
    ("non_determinism", "Non-Determinism", "Does output vary for identical input?"),
    ("opacity", "Opacity", "Is the agent's reasoning a black box?"),
    ("persistence", "Persistence", "Does state/memory persist across sessions?"),
    ("identity", "Identity", "Does the agent hold or assume identity/credentials?"),
    ("multi_agent", "Multi-Agent", "Does it orchestrate or get orchestrated by other agents?"),
    ("self_mod", "Self-Modification", "Can the agent modify its own config/tools/goals?"),
]

# Same 10 official v0.8 worked examples as index.html and
# test_aivss_owasp_calculator_cross_validation.py.
SCENARIOS = {
    "1. Agentic AI Tool Misuse": (9.4, {"autonomy": 1, "tools": 1, "language": 1, "context": 1,
        "non_determinism": 1, "opacity": 1, "persistence": 0.5, "identity": 1, "multi_agent": 1, "self_mod": 0.5}),
    "2. Agent Access Control Violation": (8.7, {"autonomy": 1, "tools": 1, "language": 1, "context": 1,
        "non_determinism": 0.5, "opacity": 1, "persistence": 1, "identity": 1, "multi_agent": 0.5, "self_mod": 0}),
    "3. Agent Cascading Failures": (7.1, {"autonomy": 1, "tools": 0.5, "language": 1, "context": 1,
        "non_determinism": 1, "opacity": 1, "persistence": 0.5, "identity": 0.5, "multi_agent": 1, "self_mod": 0.5}),
    "4. Agent Orchestration and Multi-Agent Exploitation": (9.4, {"autonomy": 1, "tools": 1, "language": 1,
        "context": 1, "non_determinism": 1, "opacity": 1, "persistence": 1, "identity": 1, "multi_agent": 1, "self_mod": 0.5}),
    "5. Agent Identity Impersonation": (7.4, {"autonomy": 1, "tools": 1, "language": 1, "context": 1,
        "non_determinism": 1, "opacity": 1, "persistence": 0, "identity": 1, "multi_agent": 0.5, "self_mod": 0}),
    "6. Agent Memory and Context Manipulation": (5.8, {"autonomy": 1, "tools": 0.5, "language": 1, "context": 1,
        "non_determinism": 0.5, "opacity": 1, "persistence": 1, "identity": 0, "multi_agent": 0.5, "self_mod": 1}),
    "7. Insecure Agent Critical Systems Interaction": (6.9, {"autonomy": 1, "tools": 1, "language": 0.5,
        "context": 1, "non_determinism": 0.5, "opacity": 1, "persistence": 0.5, "identity": 0, "multi_agent": 1, "self_mod": 1}),
    "8. Agent Supply Chain and Dependency Risk": (9.3, {"autonomy": 1, "tools": 1, "language": 0, "context": 0,
        "non_determinism": 1, "opacity": 1, "persistence": 0.5, "identity": 1, "multi_agent": 1, "self_mod": 0}),
    "9. Agent Untraceability": (5.3, {"autonomy": 1, "tools": 1, "language": 0, "context": 0,
        "non_determinism": 1, "opacity": 1, "persistence": 0.5, "identity": 0.5, "multi_agent": 1, "self_mod": 0.5}),
    "10. Agent Goal and Instruction Manipulation": (2.1, {"autonomy": 0.5, "tools": 0, "language": 1, "context": 1,
        "non_determinism": 1, "opacity": 1, "persistence": 1, "identity": 0, "multi_agent": 0, "self_mod": 1}),
}

st.set_page_config(page_title="AIVSS Calculator (Streamlit)", layout="wide")
st.title("AIVSS Calculator (Streamlit)")
st.caption(
    "Calls `aivss_kg.calculate_aivss()` from this repo directly -- not a reimplementation. "
    "Educational/study artifact, not an official OWASP tool."
)

scenario_key = st.selectbox("Load a scenario", ["-- custom input --"] + list(SCENARIOS.keys()))
if scenario_key != "-- custom input --":
    default_cvss, default_factors = SCENARIOS[scenario_key]
else:
    default_cvss, default_factors = 5.0, {k: 0.0 for k, _, _ in FACTORS}

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. CVSS Base Score")
    cvss_base = st.number_input("CVSS v4.0 Base Score", min_value=0.0, max_value=10.0,
                                 value=float(default_cvss), step=0.1, key=f"cvss_{scenario_key}")

    st.subheader("3. Threat Multiplier (ThM)")
    thm_label = st.selectbox(
        "ThM", ["Attacked (1.00)", "Proof-of-Concept (0.97, default)", "Unreported (0.50)"],
        index=1, key=f"thm_{scenario_key}",
    )
    thm = {"Attacked (1.00)": 1.00, "Proof-of-Concept (0.97, default)": 0.97, "Unreported (0.50)": 0.50}[thm_label]

    st.subheader("4. Mitigation Factor")
    mit_label = st.selectbox(
        "Mitigation", ["No / Weak (1.00, default)", "Partial (0.83)", "Strong (0.67)"],
        index=0, key=f"mit_{scenario_key}",
    )
    mitigation = {"No / Weak (1.00, default)": 1.00, "Partial (0.83)": 0.83, "Strong (0.67)": 0.67}[mit_label]

with col2:
    st.subheader("2. Agentic Risk Amplification Factors")
    factors: dict[str, float] = {}
    fcols = st.columns(2)
    for i, (key, label, desc) in enumerate(FACTORS):
        with fcols[i % 2]:
            factors[key] = st.select_slider(
                f"{label} — {desc}", options=[0.0, 0.5, 1.0],
                value=float(default_factors[key]), key=f"f_{key}_{scenario_key}",
            )

result = calculate_aivss(
    cvss_base=cvss_base,
    factors=factors,
    threat_multiplier=thm,
    mitigation_factor=mitigation,
)

st.divider()
st.subheader("Result (from aivss_kg.calculate_aivss())")

m1, m2, m3 = st.columns(3)
m1.metric("AIVSS Score", f"{result['aivss']:.1f}", result["severity"])
m2.metric("Factor Sum", f"{result['factor_sum']:.1f} / 10.0")
m3.metric("AARS (Agentic Uplift)", f"{result['aars']:.4f}")

st.json(result, expanded=False)

st.divider()
st.caption(
    f"Formula: {result['authoritative_formulas']['aivss']} | "
    f"{result['authoritative_formulas']['aars']} | rounding: {result['rounding']}"
)
