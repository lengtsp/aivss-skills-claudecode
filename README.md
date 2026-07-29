# AIVSS Assessment Skills — MCP Server for Claude Code

Deterministic, LLM-free tooling for **AIVSS v0.8** (OWASP's Agentic AI
Vulnerability Scoring System) — intake & scope an AI-embedded system, triage
it against the 10 AIVSS core risks, generate audit questionnaires, score
findings, run proactive design reviews, triage threat-intel alerts, and query
a knowledge-graph layer over the risk taxonomy — all exposed as **14 MCP
tools** any MCP-capable agent (Claude Code, GPT, Qwen via llama-server, ...)
can call directly.

Built around one design principle: **the skills never call an LLM
themselves.** Every tool parses/computes/retrieves deterministically from the
OWASP AIVSS v0.8 spec (OCR'd once into `example AVISS/.../text/page-NN.txt`,
shipped in this repo) and returns JSON-safe data plus a ready-to-use
`narrative_prompt` field. The calling agent supplies the reasoning and
narration on top of grounded, cited facts — the tools supply the facts.

## Why this exists

A generic LLM answering "what should I design against AI agent risk in this
system?" is fluent but has zero traceability — no page citation, no
guaranteed-consistent scoring, and it will happily blend invented mitigations
into an otherwise real spec. This project's live testing (see
[`example AVISS/README.md`](example%20AVISS/README.md) — "Live quality test")
found the reverse problem too: raw deterministic output alone reads like a
checklist, not a consultant's answer. The `narrative_prompt` field on every
tool closes that gap — it hands the calling LLM the verified facts *and*
explicit instructions for how to narrate over them without inventing new
ones.

## What's inside

| Module | Purpose |
|---|---|
| `aivss_assessment_skills.py` | 5-skill audit chain: intake → triage → questionnaire → score → assemble deliverable |
| `aivss_banking_taxonomy.py` | 5 banking/fintech AI-system archetypes with default factor hints + regulatory context |
| `aivss_spec_search.py` | Deterministic full-text search + citation over the 98-page OCR'd spec |
| `aivss_design_review.py` | Proactive, design-time risk review (1st/2nd-line "what should we build") |
| `aivss_threat_intel.py` | Maps threat/news alert text to the 10 AIVSS risks (keyword tier + semantic fallback) |
| `aivss_finding_rationale.py` | Assembles defensible grounding for narrating a scored finding |
| `aivss_spec_provenance.py` | Verifies the risk/factor catalog against the OCR'd spec, flags drift |
| `aivss_knowledge_graph.py` | In-memory graph over risks/factors/audit topics/archetypes — blind-spot detection |
| `aivss_synthesis_prompt.py` | Shared scaffold that wraps any rendered markdown with LLM narration instructions |
| `aivss_mcp_server.py` | FastMCP server wrapping all of the above as 14 stateless MCP tools |
| `aivss_kg.py`, `aivss_internal_audit.py` (repo root) | Core AIVSS scoring formula + IT-audit/COBIT lens — required dependencies of everything above |

Full authoring history, design rationale, and every live-quality-test finding
is in [`example AVISS/README.md`](example%20AVISS/README.md) (kept in place —
it's referenced by several module docstrings).

## Requirements

- Python 3.11+ (tested on 3.13)
- `mcp>=1.26.0` (`pip install -r requirements.txt`)
- No network access needed at runtime — all data (spec text, taxonomy) ships
  in the repo and every skill is pure Python

## Quick start

```bash
git clone https://github.com/lengtsp/aivss-skills-claudecode.git
cd aivss-skills-claudecode
pip install -r requirements.txt
```

### Use it with Claude Code

This repo ships a project-scoped [`.mcp.json`](.mcp.json), so opening Claude
Code in this directory auto-detects the server (you'll be prompted to
approve it on first use):

```json
{
  "mcpServers": {
    "aivss-assessment-skills": {
      "type": "stdio",
      "command": "python3",
      "args": ["example AVISS/aivss_mcp_server.py"],
      "env": {}
    }
  }
}
```

Or register it yourself (user-scoped, not committed to git):

```bash
claude mcp add aivss-assessment-skills -s local -- python3 "example AVISS/aivss_mcp_server.py"
claude mcp list                                    # health-check
claude mcp get aivss-assessment-skills              # inspect
claude mcp remove aivss-assessment-skills -s local  # undo
```

MCP servers wire into an agent's tool set at session start — register, then
start a **new** Claude Code session (or a fresh sub-agent process) to see the
`aivss_*` tools.

### Use it with any other MCP client

`aivss_mcp_server.py` is a standard stdio MCP server (FastMCP) — point any
MCP-compatible client (Claude Desktop, other agent frameworks) at:

```bash
python3 "example AVISS/aivss_mcp_server.py"
```

## The 14 MCP tools

| Tool | What it does |
|---|---|
| `aivss_intake_and_triage` | Scope a system + triage all 10 AIVSS risks against it |
| `aivss_generate_questionnaire` | Fillable scoping/control questionnaire for given risk keys |
| `aivss_score_finding` | Score one confirmed finding (CVSS + 10 AIVSS factors → AIVSS value) |
| `aivss_assemble_audit_deliverable` | Full intake→triage→questionnaire→score→deliverable chain, rendered + narration prompt |
| `aivss_classify_banking_system` | Classify free text against 5 banking/fintech AI archetypes |
| `aivss_search_spec` | Keyword search over the 98 OCR'd spec pages |
| `aivss_cite_spec_reference` | Cite spec pages for a risk key, factor key, or freeform topic |
| `aivss_design_review` | Design-time risk-by-risk mitigations + spec citations + narration prompt |
| `aivss_triage_threat_alert` | Map a threat/news alert to the AIVSS risks it plausibly concerns |
| `aivss_draft_finding_rationale` | Score + assemble organization-context rationale grounding |
| `aivss_spec_provenance_report` | Verify the risk/factor catalog against the spec, flag drift |
| `aivss_related_risks` | Other risks structurally connected to a given risk |
| `aivss_find_blind_spot_risks` | Given already-triaged risks, find structurally-connected risks that may be a blind spot |
| `aivss_graph_export` | Export the taxonomy graph in a Neo4j/knowledge-graph-compatible shape |

Every tool is **stateless** — callers re-supply scope/triage as plain JSON on
every call — and **fails closed**: incomplete input returns `null`/`[]`/a
validation error, never a guessed score.

## Example prompts (once registered with Claude Code)

```
Use aivss_intake_and_triage to triage an autonomous SOAR/EDR incident
response agent that isolates hosts and revokes credentials without human
approval.

Run aivss_design_review for a KYC onboarding chatbot, then call
aivss_find_blind_spot_risks on the top 3 triaged risks.

Score a finding: risk=tool_misuse, cvss_base=8.5, with these 10 factor
levels ... then draft the rationale for it.
```

## Verified correctness

- **88/88 unit tests** across 11 self-contained test runners (no pytest,
  each prints a JSON pass/fail summary):
  ```bash
  python3 "example AVISS/test_aivss_assessment_skills.py"
  python3 "example AVISS/test_aivss_spec_search.py"
  python3 "example AVISS/test_aivss_design_review.py"
  python3 "example AVISS/test_aivss_threat_intel.py"
  python3 "example AVISS/test_aivss_finding_rationale.py"
  python3 "example AVISS/test_aivss_spec_provenance.py"
  python3 "example AVISS/test_aivss_synthesis_prompt.py"
  python3 "example AVISS/test_aivss_knowledge_graph.py"
  python3 "example AVISS/test_aivss_mcp_server.py"
  python3 "example AVISS/test_aivss_owasp_calculator_cross_validation.py"
  python3 "example AVISS/test_aivss_ten_risk_design_playbook.py"
  ```
- **17/17 checks** driving the real MCP JSON-RPC protocol over a subprocess
  (`test_aivss_mcp_protocol_smoke.py`) — catches wire-format/schema bugs the
  in-process tests can't.
- **10/10 official OWASP worked scenarios match exactly** against the
  live reference calculator (`test_aivss_owasp_calculator_cross_validation.py`)
  — the scoring formula is independently verified, not just self-consistent.
- All of the above re-verified standalone from a clean checkout of this
  exact repo layout before publishing.
- **Live, end-to-end screenshots** of all 14 MCP tools called from
  brand-new, non-interactive Claude Code sessions against a fresh
  `git clone` (real commands, real model output, not staged) — see
  [`example AVISS/mcp_test_screenshots/README.md`](example%20AVISS/mcp_test_screenshots/README.md)
  for the full gallery with captions, organized by category. Surfaced one
  real limitation along the way: `aivss_classify_banking_system` is
  English-keyword-only and fails closed to `null` on Thai-language input.

## Scope & honesty notes

- **AIVSS v0.8 has no dedicated "mitigations" section per risk** — the spec's
  per-risk content is DESCRIPTION + KEY RISKS + EXAMPLE ATTACK SCENARIOS
  only. `DESIGN_MITIGATIONS` in `aivss_design_review.py` is authored guidance
  grounded in each risk's real KEY RISKS bullets, not a transcription — treat
  it as a starting checklist, not an authoritative catalog. This is stated
  directly in every rendered design review's `proof_boundary` field.
- **Citations ground the risk description, not individual mitigations** —
  rendered output and `narrative_prompt` text both say this explicitly, so a
  narrating LLM doesn't imply a specific mitigation is spec-sourced when it
  isn't.
- **Threat-intel triage has a documented precision/recall tradeoff** — a
  fixed keyword tier plus a weaker, separately-labeled semantic fallback tier
  (`confidence: "possible"`), never blended into the keyword tier's scores.
- No PII, credentials, or proprietary source-code from the parent project
  are in this repo — only the AIVSS skill modules, the OCR'd spec text
  derived from the public OWASP AIVSS v0.8 PDF, and this documentation.
- **The source PDF and page scans (`.jpg`) are intentionally not included.**
  No tool in this repo opens the PDF or any `.jpg` at runtime — every skill
  reads the OCR'd `text/page-NN.txt` corpus only (see `aivss_spec_search.py`).
  The PDF is only referenced elsewhere as a filename/URL string for
  provenance display (`aivss_spec_provenance.py`'s `SPEC_SOURCE_URL`, which
  points at the official OWASP-hosted copy) — never read as a file. Get the
  original from `https://aivss.owasp.org/` if you need it; both are
  `.gitignore`d here to keep the repo lean.

## Repository layout

```
aivss-assessment-skills/
├── aivss_kg.py                 # core AIVSS scoring formula + risk/factor definitions
├── aivss_internal_audit.py     # IT-audit/COBIT lens (audit topics, output options)
├── requirements.txt
├── .mcp.json                   # Claude Code project-scoped MCP registration
└── example AVISS/              # skill modules, tests, docs (folder name is load-bearing —
    ├── aivss_*.py               # see aivss_kg.py's DEFAULT_SOURCE_DIR — do not rename)
    ├── test_aivss_*.py
    ├── README.md                # full authoring history / design rationale / live test log
    ├── SKILLS_ROADMAP.md        # design analysis this skill set was built from
    ├── deliverables/            # rendered worked-example audit deliverables
    ├── design_playbook/         # 10 rendered design-review use cases (one per core risk)
    └── AIVSS Scoring System For OWASP Agentic AI Core Security Risks v0.8 (1)_pages/
        └── text/                # 98-page OCR'd spec text (the search corpus every tool reads —
                                  # the source PDF and jpg/ page scans are not shipped, see above)
```

`example AVISS/` keeps its original name and nesting deliberately — several
modules resolve paths relative to it (`Path(__file__).resolve().parents[1]`),
and renaming it would require coordinated edits across every module and test.

## License

No license file is included — treat this as "all rights reserved" unless
the repository owner adds one. Ask before redistributing outside your
organization.
