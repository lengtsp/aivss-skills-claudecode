# example AVISS — Manual PDF OCR via Claude Vision (Sonnet)

This folder contains a manual PDF→text conversion done directly in a Claude Code session — **not** part of the app's `/process_batch` OCR Worker pipeline (which calls llama-server vision). No tesseract, llama-server, or ollama was used; Claude (Sonnet 5) read each page image directly.

## Status & Handoff (read this first)

**Hard scope rule:** all work under this thread of work is confined to this
folder, `example AVISS/`. Do not create, edit, or delete files outside this
folder (e.g. `routes_chat.py`, `app.py`, or anything else at the project
root) even when the natural next step would touch them (like wiring a new
parser into `/chat`). This is an explicit user instruction given on
2026-07-27, after a `/chat` wiring change was made to `routes_chat.py` and
had to be reverted. If a task genuinely seems to require touching the main
app, stop and ask first — never assume it's in scope.

**What's implemented (as of 2026-07-27):**
- `AIVSS Scoring System For OWASP Agentic AI Core Security Risks v0.8 (1)_pages/`
  — 98-page source PDF manually OCR'd via Claude vision into `jpg/` + `text/`
  (read-only reference material; see "Source"/"Process" below).
- `aivss_assessment_skills.py` — deterministic 5-skill chain
  (`intake_assessment_scope` → `triage_applicable_risks` →
  `generate_risk_questionnaire` → `score_finding` → `assemble_audit_deliverable`)
  plus 2 chat-text parsers (`parse_finding_score_request` for skill 4,
  `parse_scope_triage_request` for skills 1+2) and 2 markdown renderers
  (`render_deliverable_markdown` for skill 5, `render_questionnaire_markdown`
  for skill 3). Imports `aivss_kg.py` / `aivss_internal_audit.py` from the
  project root as a read-only dependency — don't edit those without asking
  either, they're outside this folder.
- `aivss_banking_taxonomy.py` — banking-system archetype taxonomy (5
  archetypes) + `classify_banking_system()` deterministic keyword classifier,
  a reference/knowledge asset that pairs with skill 1
  (`intake_assessment_scope`) by supplying realistic default
  `factor_hints`/`regulatory_context` per system type. 3 archetypes'
  defaults are sourced directly from `aivss_worked_examples.py`'s
  regression-tested scenarios; 2 are new (`kyc_onboarding_chatbot`,
  `collections_recovery_agent`).
- `test_aivss_assessment_skills.py` — self-contained test runner (no
  pytest), currently 13/13 passing.
- `aivss_worked_examples.py` — 3 fully scoped worked scenarios, writes
  rendered deliverables to `deliverables/`.
- `deliverables/*.md` — rendered `audit_program` outputs for the 3 worked
  scenarios.
- `aivss_spec_search.py` (2026-07-28, `SKILLS_ROADMAP.md` idea #1) —
  deterministic full-text search over the 98 OCR'd spec pages:
  `search_spec()` / `cite_spec_reference()`, TOC-page filtering, confidence
  bands, fails closed to `[]`.
- `aivss_design_review.py` (2026-07-28, new — not one of the original 4 seed
  ideas) — a proactive, design-time counterpart to the audit chain: reuses
  `intake_assessment_scope`/`triage_applicable_risks`, then
  `generate_design_recommendations()` attaches Codex-authored
  `DESIGN_MITIGATIONS` (grounded in the spec's documented KEY RISKS
  manifestations, not a verbatim mitigations section — see module docstring
  for why) plus live spec citations via `aivss_spec_search`.
  `parse_design_review_request()` chat-text parser included but **not
  wired**, same as skills 1+2's parser.
- `aivss_threat_intel.py` (2026-07-28, `SKILLS_ROADMAP.md` idea #4) —
  `triage_threat_alert()` maps already-fetched threat/news text to the 10
  AIVSS risks + audit topics/COBIT codes via a Codex-curated keyword catalog,
  multi-risk-aware, confidence-banded, fails closed to `None`. **Semantic
  fallback added (2026-07-28, same day)** after a live MCP test found a real
  recall gap: a genuine, on-topic alert paraphrased differently than the
  curated keywords scored 0 and returned `None`. Now, when the keyword tier
  finds nothing for a risk, `_semantic_risk_candidates()` full-text searches
  the alert against the OCR'd spec (reusing `aivss_spec_search.search_spec`)
  and maps matching pages back to the risk whose section contains them (via
  `aivss_kg.RISK_DEFINITIONS`' own `start_page`/`end_page`), surfaced
  separately as `semantic_candidates` with confidence `"possible"` — never
  blended into the keyword tier's `matches`, since the two scoring scales
  aren't comparable. See "Live quality test — threat-intel recall gap"
  below for the exact test case and threshold-tuning evidence.
- `aivss_finding_rationale.py` (2026-07-28, `SKILLS_ROADMAP.md` idea #2) —
  `draft_finding_rationale_context()` assembles (never writes) grounding for
  a scored finding: score_finding() result + skill-3 questionnaire + spec
  citation + caller-supplied `org_controls`, with an `evidence_gap` flag.
- `aivss_spec_provenance.py` (2026-07-28, `SKILLS_ROADMAP.md` idea #6) —
  `catalog_provenance_report()` dynamically verifies every
  RISK_DEFINITIONS/FACTOR_DEFINITIONS/RISK_FACTOR_MATRIX entry against the
  loaded OCR'd spec pages; pins `SPEC_VERSION`/page count, flags drift.
- `aivss_knowledge_graph.py` (2026-07-28) — an in-memory node/edge graph
  built over this folder's *already-verified* taxonomy data
  (`RISK_FACTOR_MATRIX`, `AUDIT_TOPICS`, `BANKING_SYSTEM_ARCHETYPES`) — no
  new facts authored. 57 nodes (10 risks, 10 factors, 10 audit topics, 22
  COBIT codes, 5 banking archetypes), 167 edges across 6 relation types
  (`amplifies`, `maps_to_topic`, `maps_to_control`, `typical_for`, plus
  derived `shares_factor_with`/`shares_topic_with` between risks). Core
  query: `related_risks()` / `find_blind_spot_risks()` — risks structurally
  entangled via shared amplifying factors/audit topics that a flat
  risk-by-risk triage can miss (e.g. `find_blind_spot_risks(["tool_misuse",
  "access_control"])` surfaces `supply_chain` as the top overlooked risk
  connected to both). Also `shortest_path()`, `subgraph_for_scope()`,
  `to_mermaid()`, and `export_kg_shape()` (compatible-shaped export for a
  *future* explicit integration into the main app's real Knowledge Graph —
  does not touch the DB/Neo4j/`routes_kg.py` itself). See "Knowledge-graph
  layer" below for the full design rationale.
- `aivss_mcp_server.py` (2026-07-28, `SKILLS_ROADMAP.md` idea #5) — FastMCP
  server (`mcp==1.26.0`, already present in the `base` conda env) exposing
  14 tools wrapping the full skill set above (all 7 modules listed above).
  **Registered with Claude Code (2026-07-28)** via
  `claude mcp add aivss-assessment-skills -s local -- python3 "example AVISS/aivss_mcp_server.py"`
  (local scope — private to this user/project, not committed to git; run
  `claude mcp list` / `claude mcp get aivss-assessment-skills` to inspect,
  `claude mcp remove aivss-assessment-skills -s local` to undo). Verified
  end-to-end over the real MCP protocol (not just direct Python calls) —
  see "Tested via the real MCP protocol" below.
- `aivss_synthesis_prompt.py` (2026-07-28) — shared `build_synthesis_prompt()`
  scaffold that wraps any of this folder's `render_*_markdown()` output with
  instructions for a caller LLM to narrate over it, instead of handing back
  raw markdown. Added after a live quality test found the raw output reads
  as a reference/checklist, not a consultant's answer — see "Live quality
  test" below. Consumed by `build_design_review_synthesis_prompt()`
  (`aivss_design_review.py`), `build_audit_deliverable_synthesis_prompt()`
  (`aivss_assessment_skills.py`), and
  `build_finding_rationale_synthesis_prompt()` (`aivss_finding_rationale.py`);
  all three are also wired into the matching MCP tools as a `narrative_prompt`
  field (plus new optional `original_question`/`answer_language` params).
- `aivss_ten_risk_design_playbook.py` (2026-07-28) — 10 worked design-review
  use cases, one dedicated banking/fintech scenario per AIVSS core risk
  (vs. `aivss_worked_examples.py`'s 3, audit-chain only). Each
  `RiskUseCase.factor_hints` is grounded in that risk's own
  `RISK_FACTOR_MATRIX` amplifying factors, with a `reasoning_th` field (the
  "วิธีคิด" the user asked for) explaining *why* those factors apply before
  any skill is run. Runs the design-review chain (not the audit chain —
  chosen because the user's request emphasized "ออกแบบ") and renders each
  to `design_playbook/<risk_key>.md`. 9 of 10 use cases' target risk
  triages as `high` by design; `supply_chain` triages `medium` — a genuine,
  documented structural finding (it's the only risk keyed on all 10
  amplifying factors, so a realistic non-maxed-out profile can't clear the
  0.7 average needed for `high`), not a bug. See "Ten-risk design playbook"
  below for full detail.

**Design ideas for future work** (not implemented, analysis only): see
`SKILLS_ROADMAP.md` in this folder — candidate new skills (spec-citation
search, threat-intel triage vs AIVSS, org-context reasoning grounding) plus
a recommendation to expose the skill set as an MCP server (multi-provider,
mirroring the existing `excel-mcp-server` pattern in this project) instead
of only wiring into `routes_chat.py`. Idea #3 (banking-system taxonomy) is
now implemented in basic form — see `aivss_banking_taxonomy.py` above.

**What's NOT implemented:**
- Nothing in this folder is wired into the live `/chat` endpoint.
  `routes_chat.py` already has *pre-existing* AIVSS integration (KG context,
  questionnaire, and finding-score injectors) from before this folder's
  scope rule was set — extending or modifying that from here is out of
  scope; see "Wired into `/chat`" below for what already exists there.
- Skill 5 (`assemble_audit_deliverable`) has no chat-text parser yet — it's
  only exercised by `aivss_worked_examples.py`.
- `aivss_design_review.py`'s `parse_design_review_request()` (2026-07-28) is
  drafted and tested but, like `parse_scope_triage_request`, not wired into
  `routes_chat.py` — same hard scope rule.
- `aivss_mcp_server.py` **is now registered** with Claude Code (2026-07-28,
  `claude mcp add ... -s local`, see "Design/analyze/evaluate expansion" #4
  below) — this is no longer a "not implemented" item, listed here only as a
  pointer. Because MCP servers wire in at session start, a session running
  before the registration (this one) can't use the tools directly — verified
  instead via `test_aivss_mcp_protocol_smoke.py`'s real-protocol client, not
  by calling the tools through this session's own tool-calling.
- No session/multi-turn state anywhere in this folder — every parser here is
  stateless, single-message, fail-closed (never guesses missing input).

**Verify before/after any change** (from the project root):
```bash
python -c "import py_compile; py_compile.compile('example AVISS/aivss_assessment_skills.py', doraise=True); print('OK')"
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
All eleven must succeed — each test runner prints a JSON summary with
`"passed": true` and its current pass count (as of 2026-07-28:
`test_aivss_assessment_skills.py` 14/14, `test_aivss_spec_search.py` 7/7,
`test_aivss_design_review.py` 7/7, `test_aivss_threat_intel.py` 10/10,
`test_aivss_finding_rationale.py` 7/7, `test_aivss_spec_provenance.py` 6/6,
`test_aivss_synthesis_prompt.py` 5/5, `test_aivss_knowledge_graph.py` 9/9,
`test_aivss_mcp_server.py` 14/14,
`test_aivss_owasp_calculator_cross_validation.py` 3/3,
`test_aivss_ten_risk_design_playbook.py` 6/6 — 88 tests total).
The last one needs no network access to *run* — the 10 official scenarios'
inputs/outputs are baked in as constants, verified once against the live
calculator during authoring (see "Live calculator comparison" below); it
only needs live browser access again if the reference calculator's own
scenario data changes and the baked-in values need re-verifying.

Optional, slower, only needed when `aivss_mcp_server.py` itself changes
(spawns a real subprocess over the actual MCP protocol — see "Tested via the
real MCP protocol" below):
```bash
python3 "example AVISS/test_aivss_mcp_protocol_smoke.py"
```
17/17 checks as of 2026-07-28 (14 tools × representative call(s), including
the 3 knowledge-graph tools added alongside `aivss_knowledge_graph.py`).

## Source

- `AIVSS Scoring System For OWASP Agentic AI Core Security Risks v0.8 (1).pdf` — 98 pages

## Process

1. Extract each PDF page to JPG:
   ```
   pdftoppm -jpeg -r 200 -jpegopt quality=90 "<file>.pdf" "<outdir>/jpg/page"
   ```
   → produces `page-01.jpg`, `page-02.jpg`, ... `page-98.jpg`

2. For each page, Claude read the JPG directly (vision) and transcribed it to `text/page-NN.txt`, preserving:
   - Heading/section structure
   - Tables as Markdown tables
   - Figures/diagrams described as `[Graph / Diagram Details: ...]` blocks
   - Footnote/reference lists
   - Code/JSON blocks in fenced blocks
   - `<page_number>N</page_number>` tag (physical PDF page index) at the top of each file, and the original printed page-footer number preserved at the bottom

3. Output layout:
   ```
   AIVSS Scoring System For OWASP Agentic AI Core Security Risks v0.8 (1)_pages/
     jpg/page-01.jpg ... page-98.jpg
     text/page-01.txt ... page-98.txt
   ```

No DB writes, no `Document`/`Page` rows — this is a standalone filesystem export.

Verified 2026-07-26 — all 98 pages converted 1:1 to `jpg/` + `text/`.

## AIVSS assessment-authoring skills (2026-07-27)

`aivss_assessment_skills.py` and `test_aivss_assessment_skills.py` live in this
folder at the user's request, kept alongside the source PDF/OCR pages they are
about. They are otherwise ordinary project Python modules (not OCR output):
a deterministic 5-skill chain — `intake_assessment_scope` →
`triage_applicable_risks` → `generate_risk_questionnaire` → `score_finding` →
`assemble_audit_deliverable` — that turns a role + a named AI-embedded system
into an actual AIVSS/AIVSS questionnaire and scored audit deliverable. It
reuses (does not duplicate) `aivss_kg.py` (`calculate_aivss`,
`RISK_FACTOR_MATRIX`) and `aivss_internal_audit.py` (`AUDIT_TOPICS`,
`OUTPUT_OPTIONS`) at the project root — both must remain importable, i.e. the
project root must stay on `sys.path` when this module runs (already handled
in `test_aivss_assessment_skills.py` via `parents[1]`).

Run the self-test from this folder:
```bash
python3 "example AVISS/test_aivss_assessment_skills.py"
```

`aivss_worked_examples.py` (2026-07-27) applies the same chain to three fully
scoped scenarios and writes rendered `audit_program` deliverables to
`deliverables/`: `mobile_banking_investment_advisor` (robo-advisor; top risk
Goal & Instruction Manipulation, AIVSS 7.6 High),
`fraud_detection_transaction_monitoring` (auto-freeze/auto-block agent; top
risk Memory & Context Manipulation, AIVSS 4.5 Medium after partial
mitigation), and `credit_scoring_underwriting` (document-reading loan
approval agent; top risk Goal & Instruction Manipulation via a forged-document
attack, AIVSS 7.1 High). Each scenario's expected high-priority risk set and
scored AIVSS value is locked in as a regression test in
`test_aivss_assessment_skills.py` (see "Status & Handoff" above for the
current pass count). Run it directly to regenerate the deliverables:
```bash
python3 "example AVISS/aivss_worked_examples.py"
```

## Wired into `/chat` (2026-07-27)

`aivss_assessment_skills.py` stays under this folder (deliberately, per the
placement decision above) even though `routes_chat.py` — real production
code — now imports it directly. `app.py` registers this folder on `sys.path`
once at process startup (`_EXAMPLE_AVISS_DIR`, right after the top imports)
so that deferred `from aivss_assessment_skills import ...` calls inside
`routes_chat.py` resolve exactly like any other top-level project module.

Two new gated context-injection functions in `routes_chat.py` (both no-op
unless the `agents_aviss` chat profile is active — checked via the existing
`_aivss_profile_id_active()`), called right after the existing
`_apply_aivss_kg_context()`:

- `_apply_aivss_assessment_questionnaire_context()` — when the question also
  matches a questionnaire-intent phrase (`แบบสอบถาม`, `questionnaire`,
  `scoping question`, `checklist`, `ออกแบบการประเมิน`, ...), reuses the topic
  ranking `_apply_aivss_kg_context` already produced
  (`chat_params["aivss_internal_audit_topics"]`) to pick risk keys, calls
  `generate_risk_questionnaire()`, and injects only the per-factor
  `scoping_questions` (the genuinely new content — control focus/PBC/tests/
  COBIT codes are already injected by the existing lens).
- `_apply_aivss_finding_score_context()` — parses a full
  `risk=... cvss=... <10 factors>=... thm=... mitigation=...` message via the
  new `aivss_assessment_skills.parse_finding_score_request()` (chat-text-only
  scoring, mirroring the existing aggregate-Factor_Sum calculator convention
  in `aivss_kg.parse_aivss_calculation_request`, but for the 10 named factor
  levels `score_finding()` needs) and injects the precomputed AIVSS score so
  the LLM only relays/explains it instead of computing it.

Both fail closed silently (recorded as `*_error` keys in `chat_params`, no
crash) if the module can't be imported or a message is incomplete/ambiguous —
never a guessed or partial score reaches the model.

## Skills 1+2 chat-text parser — scope intake + risk triage (2026-07-27)

`aivss_assessment_skills.parse_scope_triage_request()` is a new chat-text
parser for skills 1 and 2 (`intake_assessment_scope` -> `triage_applicable_risks`),
which were previously only reachable from the offline `aivss_worked_examples.py`
script. It parses a message like `role="..." system="..." capability="..."
regulatory="..." autonomy=1 tools=1 ...`, calls `intake_assessment_scope()`
then `triage_applicable_risks()`, and returns a JSON-safe dict (never a
dataclass) — same shape/return convention as `score_finding()`. Unlike
`parse_finding_score_request`, factor levels here are optional (0 to 10 of
the 10 factor keys) — a partial or empty `factor_hints` set is valid input;
risks with any unscoped amplifying factor surface as `needs_scoping`, per
the deterministic ranking rule in `triage_applicable_risks`. Fails closed
(returns `None`) if role, system, or capability is missing from the message
— never a guessed scope. Covered by
`test_parse_scope_triage_request_full_and_partial` in
`test_aivss_assessment_skills.py` (11/11 tests passing).

**Not wired into `/chat`.** By explicit instruction, work in this repo is
scoped to the `example AVISS/` folder only — `routes_chat.py` (main app,
outside this folder) is not to be modified here. An `_apply_aivss_scope_triage_context()`
chat injector mirroring `_apply_aivss_finding_score_context`'s shape was
drafted and verified, then reverted; wiring this parser into production chat
routing is a separate, explicitly out-of-scope follow-up.

## Design/analyze/evaluate expansion — spec citation, design review, threat intel, MCP server (2026-07-28)

Four new modules, all under this folder only, requested to deepen AIVSS
skills for "ออกแบบ วิเคราะห์ ประเมินระบบงาน AI อย่างละเอียด" (design,
analyze, evaluate AI systems in detail). Picked from `SKILLS_ROADMAP.md`'s
open menu plus one new direction, per explicit user selection (all four):

1. **`aivss_spec_search.py`** — deterministic full-text search over the 98
   OCR'd spec pages (`SKILLS_ROADMAP.md` idea #1). `search_spec(query)` scores
   pages by matched keyword count + an exact-phrase bonus, returns
   page/snippet/score/confidence, sorted, capped by `limit`.
   `cite_spec_reference(key_or_query)` expands a known AIVSS risk/factor key
   to its catalog name first (better recall than the snake_case key) then
   delegates to `search_spec`. Table-of-contents / list-of-figures pages are
   excluded by default (`_is_toc_like`, detects dot-leader density) since
   they name-match everything without describing it — a real quality bug
   caught while authoring: `cite_spec_reference("goal_instruction")`
   initially returned TOC pages 2-3 instead of the actual section (page 41)
   before this filter was added. Fails closed to `[]`.

2. **`aivss_design_review.py`** — a new proactive, design-time skill chain,
   distinct in purpose from `aivss_assessment_skills.py`'s retrospective
   3rd-line audit chain: it answers "what should we build" for a System
   Owner / AI Security Lead / Agent Developer (1st/2nd line), not "what IS
   already built" for an auditor. Reuses `intake_assessment_scope` and
   `triage_applicable_risks` unchanged (scope/triage don't depend on the
   caller's purpose). `generate_design_recommendations()` then builds, per
   triaged risk: `factor_design_guidance` (restates each amplifying factor's
   own `aivss_kg.FACTOR_DEFINITIONS` description as a design target),
   `mitigations` from the `DESIGN_MITIGATIONS` catalog, and `spec_citations`
   via live `aivss_spec_search.cite_spec_reference()` calls (dynamic search,
   not hand-pinned quotes). **Important honesty note carried in the module
   docstring and `DESIGN_REVIEW_PROOF_BOUNDARY_NOTE`:** the AIVSS v0.8 spec's
   per-risk sections (verified by reading pages 8-44 of the OCR'd text while
   authoring this) contain DESCRIPTION + KEY RISKS (attack-surface
   manifestations) + diagram + EXAMPLE ATTACK SCENARIOS — there is **no**
   dedicated "Prevention and Mitigation Strategies" subsection per risk in
   this version (Section 3.4.1's "Mitigation Factor" is a *scoring* input, not
   a controls catalog). So `DESIGN_MITIGATIONS` is Codex-authored guidance
   that responds directly to each risk's real, spec-documented KEY RISKS
   bullets (same "paraphrase, not verbatim" convention as `RISK_SUMMARIES`),
   not a transcription of mitigation text that doesn't exist yet in v0.8 —
   treat it as a starting checklist, not an authoritative catalog.
   `assemble_design_review()` + `render_design_review_markdown()` follow the
   same shape as skill 5's audit renderer. `parse_design_review_request()`
   chat-text parser is included (same regex convention as
   `parse_scope_triage_request`) but **not wired** into `routes_chat.py` —
   same hard scope rule as the existing skills 1+2 parser.

3. **`aivss_threat_intel.py`** (`SKILLS_ROADMAP.md` idea #4) —
   `triage_threat_alert(alert_text)` maps an already-fetched threat/news/
   advisory text to the AIVSS risks it plausibly concerns, via
   `THREAT_ALERT_KEYWORDS` — a Codex-curated attack-pattern vocabulary per
   risk, grounded against the real "KEY RISKS" bullets read from the OCR'd
   spec pages while authoring (e.g. "tool squatting"/"MCP server" for
   `tool_misuse`; "confused deputy"/"role inheritance" for `access_control`;
   "prompt injection"/"indirect instruction injection" for
   `goal_instruction`). Unlike `aivss_banking_taxonomy.classify_banking_system`
   (single best match), an alert can score against multiple risks at once —
   results are ranked, each with its own confidence band (`high` at 3+
   keyword hits, `medium` at 2, `low` at 1) and matching `audit_topic_ids`/
   `cobit_codes` reused from `aivss_internal_audit.AUDIT_TOPICS`. Does not
   fetch news itself — the main app's Tavily fallback skill in
   `rag_skills.py` is a separate, out-of-scope concern; this is only the
   "map already-fetched text to AIVSS" layer. Fails closed to `None`.
   **Semantic fallback tier added (2026-07-28)** — see "Live quality test —
   threat-intel recall gap" below.

4. **`aivss_mcp_server.py`** (`SKILLS_ROADMAP.md` idea #5) — a FastMCP
   server (`mcp==1.26.0`, already installed in the `base` conda env; verified
   during authoring that `@mcp.tool()`-decorated functions stay directly
   callable, so tests call them without a client/transport) exposing tools
   that wrap — not reimplement — everything above:
   `aivss_intake_and_triage`, `aivss_generate_questionnaire`,
   `aivss_score_finding`, `aivss_assemble_audit_deliverable`,
   `aivss_classify_banking_system`, `aivss_search_spec`,
   `aivss_cite_spec_reference`, `aivss_design_review`,
   `aivss_triage_threat_alert`, `aivss_draft_finding_rationale`,
   `aivss_spec_provenance_report` (11 tools total — the last two added
   2026-07-28 alongside items 5/6 below). Every tool is stateless (a caller
   re-supplies scope/triage as plain JSON on every call, same convention as
   the rest of this folder) and JSON-safe in/out.

   **Registered with Claude Code (2026-07-28)** using the CLI (not a
   hand-edited JSON file — `claude mcp add` is the documented, correct way
   to register a server and manages the underlying config file for you):
   ```bash
   claude mcp add aivss-assessment-skills -s local -- python3 "example AVISS/aivss_mcp_server.py"
   ```
   `-s local` = private to this user in this project, stored in the user's
   global `~/.claude.json` under this project's entry — **not** committed to
   git (unlike `-s project`, which would write a shared `.mcp.json`). No
   `cwd` flag needed: the server resolves its own paths from `__file__`
   (`_PROJECT_ROOT`/`_THIS_DIR` in `aivss_mcp_server.py`,
   `_SPEC_TEXT_DIR` in `aivss_spec_search.py`), so it works regardless of
   the caller's working directory. Verify / undo:
   ```bash
   claude mcp list                                    # health-checks all registered servers
   claude mcp get aivss-assessment-skills              # shows scope, command, status
   claude mcp remove aivss-assessment-skills -s local  # undo
   ```
   Because MCP servers are wired into an agent's tool set at session start,
   a server registered mid-session (as this one was) is not usable by that
   *same* session — it needs a new session to pick it up. See "Tested via
   the real MCP protocol" below for how this was verified without waiting
   for that.

5. **`aivss_finding_rationale.py`** (`SKILLS_ROADMAP.md` idea #2) —
   `draft_finding_rationale_context(scored_finding, org_controls=None, ...)`
   assembles (never writes) the grounding an agent needs to defensibly
   narrate why a scored finding's AIVSS value is what it is: the already-
   computed `score_finding()` result, the matching risk's
   `control_questions`/`evidence_requests`/`suggested_tests` reused from
   skill 3 (`generate_risk_questionnaire`, auto-fetched if not supplied), and
   a live `aivss_spec_search.cite_spec_reference()` citation. `org_controls`
   is caller-supplied and passed through verbatim — this module never
   infers or matches it against the evidence catalog. The one thing it does
   compute is `evidence_gap`: `True` whenever no organization controls or
   evidence were supplied at all, so a downstream narrator can't accidentally
   claim a control exists just because skill 3's questionnaire mentions one.
   `render_finding_rationale_markdown()` included.

6. **`aivss_spec_provenance.py`** (`SKILLS_ROADMAP.md` idea #6) —
   `catalog_provenance_report()` verifies every entry in
   `aivss_kg.RISK_DEFINITIONS` / `FACTOR_DEFINITIONS` / `RISK_FACTOR_MATRIX`
   against the currently-loaded OCR'd spec pages, **dynamically** via
   `aivss_spec_search.cite_spec_reference()` rather than a hand-typed
   page-range table (a hand-typed table would itself drift the moment the
   OCR text is regenerated — exactly the problem this idea exists to catch).
   Pins `SPEC_VERSION = "v0.8"`, `SPEC_PUBLISHED_DATE = "2026-04-10"`,
   `SPEC_SOURCE_URL` (the official OWASP AIVSS site), and
   `SPEC_PINNED_PAGE_COUNT = 98` — the version/date pins were corrected
   2026-07-28 (see "Version and date verification" below: v0.8 is a released
   publication, not a draft, and the date is the official site's own
   `Last-Modified` header, confirmed against a byte-identical local copy of
   the PDF). Reports `page_count_drift` if the loaded OCR text no longer
   matches, plus per-entry `verified`/`pages`/`confidence` and any
   `RISK_FACTOR_MATRIX` entries referencing an unknown factor key. Re-run
   after any re-OCR or spec version bump (v0.9, v1.0, ...) — that re-run *is*
   the traceability idea #6 asked for, not a document to maintain by hand.
   `render_provenance_markdown()` included; a genuinely useful detail found
   while tuning it: `citations_per_entry=1` mostly lands on the page-5
   overview list (every risk name appears there), while
   `citations_per_entry=2` (the chosen default) reliably surfaces each
   risk's actual dedicated section page as the second hit.

Each module has its own self-contained test runner: `test_aivss_spec_search.py`
7/7, `test_aivss_design_review.py` 7/7, `test_aivss_threat_intel.py` 10/10,
`test_aivss_finding_rationale.py` 7/7, `test_aivss_spec_provenance.py` 6/6,
`test_aivss_synthesis_prompt.py` 5/5, `test_aivss_knowledge_graph.py` 9/9,
`test_aivss_mcp_server.py` 14/14,
`test_aivss_owasp_calculator_cross_validation.py` 3/3,
`test_aivss_ten_risk_design_playbook.py` 6/6 — see "Verify before/after any
change" above for the full command list. (Counts for
`test_aivss_design_review.py`/`test_aivss_finding_rationale.py` include
one new test each for `build_*_synthesis_prompt()` — see "Live quality test"
below.)

## Tested via the real MCP protocol (2026-07-28)

`test_aivss_mcp_server.py` (11/11) calls the `@mcp.tool()`-decorated Python
functions directly, in-process — fast, but it never actually exercises the
MCP JSON-RPC wire format, so it can't catch a whole class of integration
bugs (bad tool schema, broken stdio framing from stray stdout output,
subprocess startup failure). To close that gap, `test_aivss_mcp_protocol_smoke.py`
spawns `aivss_mcp_server.py` as a real subprocess and drives it through the
actual MCP client protocol (`initialize` -> `list_tools` -> `call_tool`,
using the `mcp` SDK's `ClientSession`/`stdio_client` — the same primitives a
real MCP client uses) against all 11 tools, including both branches of every
nullable-return tool. Currently 14/14 checks pass.

**A real integration finding came out of writing this test**, not just a
"nothing broke" confirmation: a tool's `content` list and `structuredContent`
field are shaped differently depending on the Python return type annotation,
and an early draft of the test naively read only `content[0].text`, which
silently truncated `aivss_search_spec`'s 3 hits down to 1:

- Plain `dict[str, Any]` return (e.g. `aivss_score_finding`) ->
  `structuredContent` **is** the dict directly (not wrapped), `content` has
  exactly one `TextContent` block.
- `list[dict[str, Any]]` return (e.g. `aivss_search_spec`,
  `aivss_cite_spec_reference`) -> `structuredContent` is `{"result": [...]}`,
  and `content` gets **one `TextContent` block per list item** — reading
  only `content[0].text` silently truncates to the first item.
- `dict[str, Any] | None` (Optional/Union) return (e.g.
  `aivss_classify_banking_system`, `aivss_triage_threat_alert`) -> always
  wrapped as `{"result": ...}`, including `{"result": null}` for the `None`
  case with **zero** `content` blocks.

This isn't a bug in `aivss_mcp_server.py` — it's correct, spec-compliant
FastMCP behavior — but it's a real gotcha for any caller, including a future
session of this same server. Documented here plus in
`test_aivss_mcp_protocol_smoke.py`'s own docstring (`_unwrap()` helper) so
neither has to be rediscovered. The improvement made as a direct result:
any future consumer of these tools (this document, an agent's own
tool-calling code) should read `structuredContent`, never
`content[0].text`, for list- or Optional-returning tools.

## Live quality test — answer quality with vs. without the AIVSS tools (2026-07-28)

User asked to test whether the registered MCP server actually improves
design-question answer quality when used through Claude Code sub agents, on
a fresh scenario (Trade Finance L/C document-verification + auto-
disbursement agent — not reused from any existing test fixture in this
folder).

**Blocker found first:** a fresh sub agent launched via the `Agent` tool,
even after the MCP server was registered, still could not see any `aivss_*`
tools (`ToolSearch` found nothing). This confirms — the hard way — the
limitation already noted under "AIVSS MCP server" above: a server
registered with `claude mcp add` mid-session needs a genuinely new Claude
Code **process**, not just a new sub agent within the same running process.
Two general-knowledge baseline agents were run instead (one that was
supposed to have tools and reported none found, one explicitly told not to
use any), and the real `aivss_design_review` skill was called directly via
Python on the identical scenario to get genuine tool output for comparison.

**First comparison result (before this section's fix):** the AIVSS output
was **more traceable** (real AIVSS v0.8 page citations, e.g. p.41 for
prompt injection) and **more consistent** (deterministic risk ranking,
same input always produces the same 10-risk ranking) than either LLM
baseline — but as **raw markdown alone**, it read as a reference/checklist,
not a consultant's answer, and it never connected its generic mitigations
to the scenario's own regulatory terms (`UCP 600` was in the input's
`regulatory_context` but never appeared in the output, because
`DESIGN_MITIGATIONS` is a fixed catalog keyed by risk type, not
scenario-aware — and deliberately so, per the "skills stay LLM-free"
design principle). Both LLM baselines, despite having zero real citations,
produced more fluent, directly-useful-looking answers than the raw AIVSS
markdown.

**Fix:** `aivss_synthesis_prompt.py` / `build_*_synthesis_prompt()`
functions (see "Status & Handoff" above) — wrap the grounded markdown with
explicit instructions for a caller LLM to narrate over it, including
permission to connect the listed mitigations to the scenario's own named
regulatory/domain terms while forbidding invented facts.

**Verified the fix actually closes the gap**, not just that the prompt
text looks right: ran the exact generated prompt for the L/C scenario
through a fresh agent with no other context. Result — the agent's answer
stayed within the 5 grounded risks and their listed mitigations (verified
by its own self-report and spot-checked), explicitly wove in `UCP 600`,
`SWIFT`, `BOT`, `AMLO/FATF`, and `PDPA` while **explicitly flagging that
connection as its own reasoning layered on top, not part of the verified
AIVSS data** (e.g. "แม้กรอบ AIVSS จะไม่ได้ระบุ mapping ไปยังกฎหมาย/มาตรฐาน
เหล่านี้โดยตรง..."), and preserved the proof-boundary caveat in full. That
last point — the model *itself* keeping fact-boundary discipline instead of
blending inferred connections into the verified findings — is exactly the
epistemic behavior `PROOF_BOUNDARY_NOTE`/`DESIGN_REVIEW_PROOF_BOUNDARY_NOTE`
across this folder are trying to induce in a downstream narrator, and this
is the first time it was checked against a real model run rather than only
asserted in a docstring.

**Net assessment, stated plainly:** the AIVSS tools' raw output alone does
**not** out-answer a good general-knowledge LLM response to an open design
question — it's a source of grounding, not a finished consultant's answer.
The `narrative_prompt` field closes that gap by giving the caller a
ready-made "have an LLM narrate over these verified facts" step, which
combines the AIVSS output's traceability/consistency with the baseline
LLM's domain fluency. This was validated with one scenario and one model
run, not a large-scale benchmark — treat the improvement as demonstrated,
not proven at scale.

**Follow-up fix from the validation run's own self-report (2026-07-28,
same day):** the validating agent said it deliberately avoided citing a
specific page number next to any individual mitigation, because the
grounded markdown lists a risk's `spec_citations` and its `mitigations` as
two separate blocks with no explicit statement of what the citations
actually ground — the model had to *infer* that citations support the risk
description, not each mitigation, and got it right, but that inference
shouldn't be left to chance on every future run. Fixed by making it
explicit rather than implicit: `render_design_review_markdown()` and
`render_finding_rationale_markdown()` now label the citation block itself
("...describes the attack pattern, NOT a per-mitigation citation..."), and
`aivss_synthesis_prompt.build_synthesis_prompt()`'s instructions now state
the same rule directly ("do not claim a specific mitigation is spec-sourced
... unless that exact page's snippet demonstrates it"). Covered by new
assertions in `test_aivss_design_review.py`, `test_aivss_finding_rationale.py`,
and `test_aivss_synthesis_prompt.py` (see current pass counts under "Verify
before/after any change" above).

## Knowledge-graph layer (2026-07-28)

User asked to make the skill assets "support knowledge-graph-style
thinking" too. Everything built in this folder up to this point models
AIVSS relationships as flat, independent per-risk lookups —
`triage_applicable_risks()` scores one risk at a time against its own
amplifying factors, `generate_risk_questionnaire()` builds one section per
risk key, etc. That flat shape can't answer a genuinely different class of
question: *which other risks are structurally entangled with this one, and
why* — two risks sharing several amplifying factors will very plausibly
co-occur in a real system, and a risk-by-risk assessment has no way to
surface that on its own.

The underlying data to answer that question was already sitting in this
folder's existing, already-verified sources — `RISK_FACTOR_MATRIX`
(`aivss_kg.py`, risk → amplifying factors), `AUDIT_TOPICS`
(`aivss_internal_audit.py`, risk → audit topic → COBIT code), and
`BANKING_SYSTEM_ARCHETYPES` (`aivss_banking_taxonomy.py`, archetype →
typical factors) — it just had never been modeled or queried as a graph.
`aivss_knowledge_graph.py` adds that layer: nodes (`risk`, `factor`,
`audit_topic`, `cobit_code`, `banking_archetype` — 57 total) and typed
edges (`amplifies`, `maps_to_topic`, `maps_to_control`, `typical_for`, plus
two *derived* risk↔risk edges — `shares_factor_with` and
`shares_topic_with`, computed by intersecting each pair of risks'
amplifying-factor/audit-topic sets — 167 edges total). No new facts were
authored to build this; it's purely a different lens on data that was
already verified elsewhere in this folder.

**The concrete payoff — blind-spot detection.** `find_blind_spot_risks()`
takes the risk keys a triage/design review already surfaced (e.g. the
top-N from `triage_applicable_risks` or `generate_design_recommendations`)
and finds *other* risks strongly connected to that set via shared factors/
topics, ranked by aggregate connection weight. Verified during authoring:
`find_blind_spot_risks(["tool_misuse", "access_control"])` correctly
surfaces `supply_chain` as the top candidate (weight 7.0 — connected to
*both* given risks, via 4 shared factors with `tool_misuse` and 3 with
`access_control`), ahead of `critical_systems` (weight 4.0, connected to
both but more weakly) and `goal_instruction` (weight 4.0, connected to only
one). This is a genuinely different signal than triage applicability alone
— a risk can be a blind spot precisely because it's entangled with risks
the assessor already flagged, independent of its own standalone score.

Other queries: `related_risks(risk_key)` (the single-risk version of the
same idea), `shortest_path(a, b)` (plain BFS — the graph is small enough
that no graph library is needed), `subgraph_for_scope(risk_keys)` (bounded
one-hop extract for rendering instead of the full ~57-node graph),
`to_mermaid(risk_keys=None)` (deterministic Mermaid flowchart source, no
rendering engine required to produce the diagram text itself), and
`export_kg_shape(risk_keys=None)`.

**On `export_kg_shape()` and the main app's real Knowledge Graph:** the
main app already has a separate, LLM-driven entity/relation extraction
system (`knowledge_graph.py`, `neo4j_sync.py`, `routes_kg.py`, the
`kg_nodes`/`kg_relations` DB tables) — a different thing from this
in-memory taxonomy graph, and out of this folder's scope per the hard scope
rule. `export_kg_shape()` produces output in a *compatible* shape
(`entity_name`/`entity_type`/`description` for nodes,
`source_entity`/`target_entity`/`relation_type` for relations) so a future,
explicit, separately-authorized integration step could import this
taxonomy into that real system — this module does not call
`neo4j_sync.py`, does not touch `kg_nodes`/`kg_relations`, and does not
open a database connection anywhere.

**Wired into `aivss_mcp_server.py`** as 3 new tools —
`aivss_related_risks`, `aivss_find_blind_spot_risks`, `aivss_graph_export`
— bringing the server to 14 tools total. Verified over the real MCP
protocol too (`test_aivss_mcp_protocol_smoke.py`, now 17/17 checks).
`test_aivss_knowledge_graph.py` (9/9) covers node/edge counts against the
source catalogs, ranking order, fail-closed behavior on unknown risk keys,
BFS correctness, and that `export_kg_shape()` output round-trips through
`json.dumps` cleanly.

## Live test through Claude Code itself, and a real fix it found (2026-07-28)

A later Claude Code session (a genuinely new process, started after the MCP
server registration above) picked up all 14 `aivss_*` tools automatically —
confirming the earlier hypothesis that a server registered mid-session needs
a new process, not just a new sub agent, to become usable. This let every
tool be exercised for the first time through the *actual* tool-calling path
a real user session uses, not a subprocess-client workaround
(`test_aivss_mcp_protocol_smoke.py`) or direct Python calls.

**Test scenario:** an Autonomous IT Incident Response Agent (isolates
hosts / revokes credentials from SIEM/EDR alerts with no human approval) —
deliberately a fresh, non-banking scenario not reused from any existing
test fixture, to check the taxonomy generalizes. All 14 tools were called
live, covering the full chain (intake → triage → design review → audit
deliverable → finding scoring → rationale) plus the graph tools together on
the same triaged risk set.

**Confirmed working correctly, live:**
- Full pipeline correctness matched what the unit tests already asserted —
  triage ranking, spec page citations (e.g. p.28/30 for `critical_systems`,
  matching values already verified during authoring), AIVSS score
  computation (7.1 High, formula-correct).
- **Fail-closed discipline holds under real MCP error handling, not just
  direct Python exceptions:** calling `aivss_score_finding` with only 4 of
  the 10 required `factor_levels` was rejected outright
  (`"factor keys mismatch; missing=[...]"`) instead of silently scoring
  with a guessed/partial factor set.
- `aivss_find_blind_spot_risks(["critical_systems", "memory_context",
  "supply_chain"])` surfaced `goal_instruction` and `orchestration` (tied,
  weight 9) as the top blind spots — a genuinely plausible finding for this
  scenario (the least-considered risk for an auto-isolating incident
  responder is exactly "an attacker crafts the alert/log content itself to
  steer *which* host gets isolated" — a goal_instruction-shaped attack) that
  the graph surfaced from pure structural connectivity, without anyone
  having to think of it by hand.

**A real gap, found and fixed the same session:** `aivss_triage_threat_alert`
returned `None` for a genuinely on-topic, plausible alert —
*"Researchers disclosed a log-injection technique that tricks autonomous
SOAR/EDR response agents into auto-isolating legitimate hosts via crafted
alert text..."* — because it didn't contain any `THREAT_ALERT_KEYWORDS`
phrase verbatim (only matched once reworded to say "indirect instruction
injection" literally). This is exactly the known, already-documented
precision/recall tradeoff of a fixed keyword list — now demonstrated
concretely instead of just theorized.

**Fix:** a second, explicitly weaker tier in `aivss_threat_intel.py`.
`_semantic_risk_candidates()` reuses `aivss_spec_search.search_spec()`
(already built, already tested — no new search engine) to full-text search
the alert against the 98 OCR'd spec pages, then maps each matching page
back to the risk whose section contains it, using `aivss_kg.RISK_DEFINITIONS`'
own authoritative `start_page`/`end_page` fields (discovered during this
work — a cleaner, more authoritative page-range source than the dynamic
citation search `aivss_spec_provenance.py` uses). Threshold-tuned against
real data: `SEMANTIC_FALLBACK_MIN_SCORE = 6` — unrelated prose ("the weather
is nice today", "my cat likes to sleep on the couch...") topped out at
`search_spec` score 1-2 in testing, while the failing alert scored 8 against
page 41 (`goal_instruction`'s own section, which discusses prompt injection
at length) — a clear separation.

**Kept deliberately separate, not merged, from the keyword tier:** the new
results appear under a distinct `semantic_candidates` key with confidence
`"possible"` (a new, explicitly weaker tier — not `"low"`), never blended
into `matches`/`matched_risk_keys`/`score`. The two scores aren't on
comparable scales (keyword score = distinct-phrase count, typically 1-5;
`search_spec` score = token-overlap count, can run higher), so merging them
into one ranked list would have produced a false sense of precision — the
same "don't blend distinct evidence types into one number" principle
already applied to the citation-attribution fix earlier in this document.
The keyword tier's own behavior, scores, and confidence bands are
byte-for-byte unchanged; all 6 pre-existing tests still pass without
modification. 4 new tests added
(`test_aivss_threat_intel.py`, now 10/10) — including a direct regression
test using the exact alert text that triggered this fix, and confirmation
that unrelated prose still fails closed to `None` with the new tier active.

## Version and date verification (2026-07-28)

User asked to pin down the spec's actual version and publication date, and
to cross-check the AIVSS skill set's output against two live calculators the
user linked: `https://aivss.parthsohaney.online/` and
`https://aivss.owasp.org/ssvc.html`. Both done via real browser automation
(Playwright), not guessed.

**"0.8-draft" was wrong — corrected to `"v0.8"`.** This folder's
`aivss_spec_provenance.py` had pinned `SPEC_VERSION = "0.8-draft"` since it
was first written — an assumption, never actually checked against the
source. Verifying it properly this time:
- Searched every occurrence of the word "draft" across all 98 OCR'd pages —
  none refer to this document's own status (one is inside an attack-scenario
  example, "draft a promotional blog post"; one is a `json-schema draft-07`
  reference; one refers to the *separate* SSVC methodology's own draft
  status, not AIVSS itself — see "Live calculator comparison" below).
- The official project homepage (`https://aivss.owasp.org/`, fetched live)
  headlines: **"📄 New Publication: AIVSS v0.8 Released."**
- The PDF actually served from that site
  (`assets/publications/AIVSS Scoring System For OWASP Agentic AI Core
  Security Risks v0.8.pdf`) is **byte-identical** to the local copy in this
  folder — `4,596,969` bytes both ways, confirmed via `stat` locally and
  `curl -I` against the live URL — so this folder's OCR source and the
  currently-published official document are the same file.
- That same `curl -I` gave the file's `Last-Modified` HTTP header:
  **`Fri, 10 Apr 2026 21:08:51 GMT`** — the closest thing to an official
  publication date available (the PDF itself, exported from Google Docs,
  carries no internal creation-date metadata — checked via `pdfinfo`).

`aivss_spec_provenance.py` now pins `SPEC_VERSION = "v0.8"`,
`SPEC_PUBLISHED_DATE = "2026-04-10"`, and `SPEC_SOURCE_URL` pointing at the
official PDF, all surfaced in `catalog_provenance_report()`'s output and
`render_provenance_markdown()`. Every other "v0.8 draft" reference across
`aivss_design_review.py`, `aivss_finding_rationale.py`, this README, and
`SKILLS_ROADMAP.md` was found (`grep`) and corrected to match — tests
updated accordingly, `test_aivss_spec_provenance.py` still 6/6.

## Live calculator comparison (2026-07-28)

**Two officially-linked calculators are genuinely different tools, not two
implementations of one formula** — this was the first thing to establish,
before any score comparison would even make sense:

- `https://aivss.owasp.org/ssvc.html` — "AIVSS-SSVC Calculator." A
  Stakeholder-Specific Vulnerability Categorization (SSVC) decision-tree
  tool: different inputs (P(Threat) exploitation state, P(Vulnerability)
  posture, systemic Impact, 10 differently-named 1–5-scored capability
  factors grouped into categories A/B/C), a completely different formula
  (`Likelihood × Exposure multiplier × Impact` → a decision-matrix lookup),
  and a categorical output (`Defer` / `Scheduled` / `Out-of-Cycle` /
  `Immediate` remediation timeline) — not a 0–10 severity number at all.
  Confirmed this is intentional, not a competing/inconsistent
  implementation: page 51 of the OCR'd spec text says SSVC is "a parallel
  but complementary effort... designed to be used together rather than as
  alternatives," and community contribution to *that* methodology's draft
  is what page 51's one legitimate "draft" reference is about.
- `https://aivss.parthsohaney.online/calculator` — "AIVSS Calculator,"
  linked from the official homepage as "🚀 Try the AIVSS Calculator Demo."
  This one implements the *same* formula as the v0.8 PDF and this folder's
  `aivss_kg.calculate_aivss()`: the site's own "Formula Visualization"
  panel reads `AIVSS = (CVSS Base + AARS Uplift) × Mitigation Factor` /
  `AARS Uplift = (10 − CVSS Base) × (Factor Sum / 10) × Threat Multiplier`
  — character-for-character the same structure this folder has implemented
  since `aivss_assessment_skills.py`'s `score_finding()` was first authored.
  Its own copy states it "Reproduces the v0.8 report exactly."

**Numeric cross-validation, done properly (not assumed), across all 10
official scenarios:** the calculator ships all 10 official OWASP
worked-example scenarios (Sections 3.6.1–3.6.10 of the v0.8 PDF,
"Agentic AI Risk Scoring for OWASP Agentic AI Core") in a "Load OWASP
Scenario" dropdown — one per core risk. First tested scenario 10 alone,
reading the resulting inputs off the live page via a full-page screenshot
(not scraped CSS classes alone — the screenshot cross-checked an initial
CSS-class-based read before trusting it, since getting that wrong would
have produced a false "mismatch" finding). Once that method was confirmed
reliable, cycled through the remaining 9 scenarios the same way (dropdown
select → read `CVSS Base` / all 10 agent-factor levels via the same
CSS-class check / `AIVSS Score` / `Agentic Uplift` off the live page).
`Threat Multiplier` (0.97, Proof-of-Concept) and `Mitigation Factor` (1.00,
No/Weak) stayed at default for every one of the 10 — confirmed, not
assumed, on each read.

| # | Risk | CVSS Base | Factor Sum | Site AIVSS | Mine | Match |
|---|------|-----------|------------|------------|------|-------|
| 1 | Agentic AI Tool Misuse | 9.4 | 9.0 | 9.9 | 9.9 | ✅ |
| 2 | Agent Access Control Violation | 8.7 | 8.0 | 9.7 | 9.7 | ✅ |
| 3 | Agent Cascading Failures | 7.1 | 8.0 | 9.4 | 9.4 | ✅ |
| 4 | Agent Orchestration and Multi-Agent Exploitation | 9.4 | 9.5 | 10.0 | 10.0 | ✅ |
| 5 | Agent Identity Impersonation | 7.4 | 7.5 | 9.3 | 9.3 | ✅ |
| 6 | Agent Memory and Context Manipulation | 5.8 | 7.5 | 8.9 | 8.9 | ✅ |
| 7 | Insecure Agent Critical Systems Interaction | 6.9 | 7.5 | 9.2 | 9.2 | ✅ |
| 8 | Agent Supply Chain and Dependency Risk | 9.3 | 6.5 | 9.7 | 9.7 | ✅ |
| 9 | Agent Untraceability | 5.3 | 6.5 | 8.3 | 8.3 | ✅ |
| 10 | Agent Goal and Instruction Manipulation | 2.1 | 6.5 | 7.1 | 7.1 | ✅ |

**All 10 of 10 match exactly.** (Full factor-level inputs for every
scenario, and the exact `aars`/`aivss_raw` intermediate values, are in
`test_aivss_owasp_calculator_cross_validation.py` — this table is a
summary, that file is the actual regression test, now baked permanently
into this folder's test suite rather than left as a one-off finding here.
An initial hand-calculation while checking scenario 10 summed its 10 factor
values wrong — miscounted six `1.0`s as five — and briefly looked like a
7.5-vs-6.5 discrepancy; re-verified against the code's own actual
arithmetic, which was correct all along. Worth recording since it's a good
illustration of why "the code disagrees with my mental math" should always
be checked against the code, not assumed to be a code bug.)

**Net result:** this folder's `calculate_aivss()` / `score_finding()`
formula implementation is independently verified correct against a
community-built reference implementation of the same v0.8 formula, across
*every one* of the spec's own 10 official worked examples (one per core
risk) — not just self-consistent with this folder's own test suite, and not
just one spot-check. The SSVC calculator was not a candidate for this kind
of numeric comparison (different methodology by design), but is now
correctly understood and documented as a complementary tool rather than a
second, conflicting "official" AIVSS calculator.

## Ten-risk design playbook (2026-07-28)

User asked to "design use cases matching these 10 scenarios, with the
thinking method [วิธีคิด]" — following directly from the 10-scenario
calculator cross-validation above. `aivss_ten_risk_design_playbook.py`
answers that: one dedicated banking/fintech use case per AIVSS core risk
(10 total), run through the *design-review* chain
(`generate_design_recommendations` / `assemble_design_review`) rather than
the audit chain, since the request specifically emphasized "ออกแบบ"
(design) — a 1st/2nd-line "what should we build" perspective, distinct from
`aivss_worked_examples.py`'s existing 3 audit-chain scenarios.

**The 10 use cases:**

| Risk | System |
|------|--------|
| Agentic AI Tool Misuse | AI Treasury Dealing Assistant |
| Agent Access Control Violation | AI Case-Management Agent for KYC/AML Investigation |
| Agent Cascading Failures | Multi-Branch AI Teller Orchestration Network |
| Agent Orchestration and Multi-Agent Exploitation | Multi-Agent Loan Origination Pipeline |
| Agent Identity Impersonation | AI Voice-Banking Authentication & Support Agent |
| Agent Memory and Context Manipulation | AI Relationship Manager with Long-Term Customer Memory |
| Insecure Agent Critical Systems Interaction | AI Core Banking Configuration Agent |
| Agent Supply Chain and Dependency Risk | Bank's AI Agent Platform (Foundation Model + Plugin Marketplace) |
| Agent Untraceability | AI Compliance Monitoring Agent Across Core Banking + Digital Channels |
| Agent Goal and Instruction Manipulation | AI Customer Complaint & Goodwill Compensation Agent |

**วิธีคิด (the thinking method), concretely:** each `RiskUseCase` carries a
`reasoning_th` field — a short Thai paragraph written *before* running any
skill, connecting the system's actual described capabilities to that
specific risk's own `RISK_FACTOR_MATRIX` amplifying factors, then stating
in one sentence why the resulting attack surface matches the risk's
definition. E.g. for `tool_misuse` (amplified by `autonomy` + `tools` +
`language`): the Treasury Dealing Assistant fires trade orders itself
(`autonomy=1`), can call multiple trading/market-data tools including MCP
servers (`tools=1`), and takes all instructions as natural language from a
trader (`language=1`) — three factors, three concrete capabilities, one
clear line to why tool-squatting / metadata-injection is the risk to design
against. All 10 reasoning notes follow this same shape: factor → concrete
capability → why it matters.

**Verified, not just asserted:** `target_risk_applicability()` runs each
use case's `factor_hints` through the real `triage_applicable_risks()` and
checks the *intended* risk actually comes out on top — 9 of 10 land on
`high`. The 10th, `supply_chain`, is a genuine, documented finding rather
than a tuning failure: it's the only core risk keyed on *all 10* amplifying
factors (`RISK_FACTOR_MATRIX["supply_chain"]` — every other risk uses only
3-4), so the triage heuristic's `>=0.7 average` bar for `high` is
structurally harder to clear with a realistic, non-maxed-out factor profile
(this use case averages 0.55). Deliberately did **not** "fix" this by
maxing every factor to 1.0 to force a `high` label — that would have turned
a plausible varied system into an artificial worst-case just to pass a
threshold, which is exactly the kind of dishonesty this folder's proof-
boundary discipline exists to prevent. The `medium` result, and the reason
for it, is recorded directly in the `supply_chain` use case's own
`reasoning_th` and enforced as the expected value in
`test_aivss_ten_risk_design_playbook.py`.

**Output:** `main()` renders all 10 to `design_playbook/<risk_key>.md` —
each file has the วิธีคิด reasoning, the full design-review markdown
(risk-by-risk mitigations + real spec citations, same as
`aivss_design_review.py` produces anywhere else), and the ready-to-use
`narrative_prompt` (from `build_design_review_synthesis_prompt()`) so the
files double as live examples of every prior fix in this document (the
citation-attribution disclaimer, the synthesis-prompt gap closure) applied
to 10 genuinely different scenarios at once. `test_aivss_ten_risk_design_playbook.py`
(6/6) covers full risk coverage, required-field validation on every use
case, the applicability check above, that each use case's own target risk
appears in its own top-3 design sections (except `supply_chain`, documented
exception), and that the rendered markdown actually contains the วิธีคิด
text and a working synthesis prompt.
