# AIVSS Skills Roadmap — Multi-Provider Plugin Design (draft, 2026-07-27)

Design analysis for future work sessions to pick from, scoped to
`example AVISS/` per the folder rule in `README.md`'s "Status & Handoff"
section. **Update 2026-07-27:** idea #3 (banking-system taxonomy) below is
now implemented in basic form — see `aivss_banking_taxonomy.py` — along with
`render_questionnaire_markdown()` in `aivss_assessment_skills.py`, which
closes the render-function asymmetry noted under idea #3 (skill 5 had
`render_deliverable_markdown`; skill 3 had no equivalent).

**Update 2026-07-28:** ideas #1 (spec citation), #4 (threat-intel triage),
and #5 (MCP server) below are now implemented — see
`aivss_spec_search.py`, `aivss_threat_intel.py`, `aivss_mcp_server.py`, and
README.md's "Design/analyze/evaluate expansion" section for full detail and
the honesty caveat on idea #2-adjacent mitigation content (v0.8 has no
per-risk mitigations subsection yet — see that section). A new,
previously-undiscussed direction was also implemented alongside them:
`aivss_design_review.py`, a proactive design-time review chain (1st/2nd-line
role) as a counterpart to the existing retrospective audit chain.

**Update 2026-07-28 (same day, continued):** ideas #2 (organization-context
reasoning) and #6 (spec-version tracking) are now also implemented — see
`aivss_finding_rationale.py` and `aivss_spec_provenance.py`. That closes out
every idea originally listed in this document except #7, which was
addressed inline rather than as its own module (see note below "Suggested
phasing"). `aivss_mcp_server.py` now wraps all 6 modules as 11 tools.

**Update 2026-07-28 (same day, continued further):** two more
previously-undiscussed directions were added: `aivss_synthesis_prompt.py`
(closes a real gap found via a live quality test comparing tool output
against general-knowledge LLM answers — see README.md "Live quality test")
and `aivss_knowledge_graph.py` (an in-memory graph layer over this folder's
existing taxonomy data, enabling "which other risks are structurally
entangled with this one" queries a flat per-risk lookup can't answer — see
README.md "Knowledge-graph layer"). `aivss_mcp_server.py` now wraps 8
modules as 14 tools, registered locally with Claude Code and verified over
the real MCP protocol (17/17 checks).

## Design principle: keep skills provider-agnostic by keeping them LLM-free

`aivss_assessment_skills.py`'s existing 5-skill chain and 2 chat-text parsers
(`parse_finding_score_request`, `parse_scope_triage_request`) never call an
LLM themselves — they parse/compute/retrieve deterministically and return
JSON-safe data. That is *why* they are provider-agnostic: whichever LLM is
driving the calling agent (Claude, GPT, Qwen via llama-server, Gemini, ...)
does the actual reasoning/narration on top of grounding context the skill
supplies. Every new skill idea below should keep this shape — retrieval and
computation in the skill, reasoning left to the caller — rather than each
skill picking its own LLM provider internally.

**Existing precedent in this project:** `excel-mcp-server` (negokaz), noted
in the root `CLAUDE.md`, is exactly this pattern already in production use —
an MCP server exposing deterministic tools (`excel_read_sheet`,
`excel_write_to_sheet`, ...) that any MCP-compatible agent can call, opt-in
via `mcpServers` in `.claude/settings.json`. Extending the same strategy to
AIVSS (an `aivss-mcp-server` wrapping `aivss_assessment_skills.py`) is not a
novel architecture decision for this codebase — it's applying a pattern that
already works here.

## Candidate skills — expanded from the 4 seed ideas

### 1. Spec-grounded scoring rationale (`อ้างอิงเนื้อหาต้นฉบับ`) — ✅ implemented (2026-07-28)

`cite_spec_reference(factor_or_risk_key: str, query: str) -> list[{page, quote}]`

The source spec is already OCR'd page-by-page in
`AIVSS Scoring System For OWASP Agentic AI Core Security Risks v0.8 (1)_pages/text/page-NN.txt`.
A deterministic keyword/full-text search over those 98 pages lets `score_finding`
callers cite the actual spec page + quote justifying a 0/0.5/1 factor level,
instead of the caller (human or LLM) asserting a level with no traceable
source. No LLM needed — pure text search.

Implemented as `aivss_spec_search.py`: `search_spec(query)` (general keyword
search with confidence bands, TOC-page filtering) and
`cite_spec_reference(key_or_query)` (risk/factor-key-aware wrapper). Not yet
wired *into* `score_finding` itself (that would mean auto-attaching a
citation to every scored factor level) — currently consumed by
`aivss_design_review.py`'s `generate_design_recommendations()` to ground each
risk's design mitigations. Wiring citations directly into
`aivss_assessment_skills.score_finding`'s output is a reasonable next step if
this proves useful.

### 2. Organization-context reasoning (`เหตุผลประกอบการประเมินในหน่วยงาน`) — ✅ implemented (2026-07-28)

`draft_finding_rationale_context(finding: dict, org_controls: dict) -> str`

Not a skill that *writes* the rationale (that requires an LLM and belongs to
the calling agent) — a skill that *assembles* the grounding an agent needs to
write one defensibly: the deterministic `score_finding()` result + matching
`control_questions`/`evidence_requests` from skill 3 + a spec citation from
idea #1. Keeps the "never let the LLM guess a number" convention — the LLM
only narrates over already-computed facts.

Implemented as `aivss_finding_rationale.py`. Returns a dict (JSON-safe, same
convention as skills 1+2/4's parsers), not a string — `str` was the original
sketch's return type but every other skill in this folder returns structured
data plus a separate `render_*_markdown()` for the string form, so this
matches that pattern instead (`render_finding_rationale_markdown()`).
`org_controls` is optional; when omitted the result carries `evidence_gap:
true` rather than failing, since "no evidence gathered yet" is a legitimate
state for an in-progress assessment, not an error.

### 3. Banking system classification (`การจำแนกระบบงานธนาคาร`) — ✅ implemented (basic version)

`aivss_banking_taxonomy.py`, same shape as `aivss_internal_audit.py`'s
`AUDIT_TOPICS`/`OUTPUT_OPTIONS`: 5 curated banking AI-system archetypes
(`robo_advisor`, `fraud_transaction_monitoring`, `credit_scoring_underwriting`,
`kyc_onboarding_chatbot`, `collections_recovery_agent`) — the first 3 formalize
what `aivss_worked_examples.py`'s existing regression-tested scenarios already
established; the last 2 are new. Each archetype carries default
`factor_hints` (only the 3-4 factors true by definition of the archetype
itself, not a fully-scoped engagement) + `regulatory_context` (BOT, SEC,
PDPA, AMLO where relevant).

`classify_banking_system(text: str) -> str | None` — deterministic
keyword-count classifier (no LLM, fails closed on no match), tested against
the real worked-example scenarios' `system_name + capability` text, not just
synthetic examples. Output is meant to feed `intake_assessment_scope` as a
pre-filled starting scope. **Not yet wired to anything automatically** — a
caller (agent or future script) still has to explicitly call
`classify_banking_system()` → `get_archetype()` → `intake_assessment_scope()`.

Also added as part of this: `render_questionnaire_markdown()` in
`aivss_assessment_skills.py` — the skill-3 counterpart to
`render_deliverable_markdown()` (skill 5), closing the asymmetry noted
below.

### 4. Threat-intel / news triage vs AIVSS (`ประเมินข่าว/สารแจ้งเตือนภัยคุกคาม AI`) — ✅ implemented (2026-07-28)

`triage_threat_alert(alert_text: str) -> {matched_risk_keys, audit_topic_ids, cobit_codes}`

Deterministic keyword/heuristic classifier (same family as the `_TYPE_KEYWORDS`
fallback classifier already used in the main app's `knowledge_graph.py`),
reusing `RISK_SUMMARIES` and `_topics_for_risk()` already in
`aivss_assessment_skills.py` to map an incoming news/advisory text to the 10
AIVSS core risks + relevant audit topics/COBIT codes. Does not itself fetch
news — the main app already has a Tavily web-search fallback skill in
`rag_skills.py` (out of scope here); this skill is the "map fetched text to
AIVSS" layer, decoupled from how the text was sourced.

Implemented as `aivss_threat_intel.py`. Differs slightly from the original
sketch: matches multiple risks per alert (ranked, each with its own
confidence band) rather than one `matched_risk_keys` list at a single
confidence, and `THREAT_ALERT_KEYWORDS` is a dedicated attack-pattern
vocabulary per risk (grounded in the spec's KEY RISKS bullets) rather than
reusing `AUDIT_TOPICS`' governance-domain keywords, which don't cover attack
techniques like "prompt injection" or "tool squatting".

## Additional ideas

### 5. Tool manifest / MCP exposure layer — ✅ implemented (2026-07-28)

`aivss_skill_manifest.json` (or equivalent MCP tool schema) enumerating every
skill function — the 5-skill chain, both existing parsers, and all skills
above — with input/output JSON schema as a single source of truth. Wrapping
this as an MCP server (mirroring `excel-mcp-server`) is the most direct
answer to "support multiple AI providers": any MCP-capable client can call
these tools directly, without going through `routes_chat.py`'s regex-parsing
chat injectors at all.

Implemented as `aivss_mcp_server.py` using the `mcp` Python SDK's `FastMCP`
(already installed, `mcp==1.26.0`) instead of a hand-written JSON manifest
file — `FastMCP` derives each tool's JSON schema from its Python type hints
automatically, so a separate manifest would just be a duplicate,
drift-prone source of truth. 11 tools registered, one per skill/capability
(see README.md for the full list — grew from 9 to 11 on 2026-07-28 when
ideas #2 and #6 were implemented and wrapped in too). Not registered in any
`.claude/settings.json` — that's a deliberate separate step for the user,
not assumed as part of authoring the server.

### 6. Spec-version tracking & audit traceability — ✅ implemented (2026-07-28)

Source spec is v0.8. `ASSESSMENT_SCHEMA = "rag.aivss-assessment-skills.v1"`
already exists as a pin point — extend with an explicit spec-version field and
a page-range map per data source (`RISK_DEFINITIONS`, `FACTOR_DEFINITIONS`,
`RISK_FACTOR_MATRIX`) so that when the spec updates (v0.9/v1.0), it's clear
which entries need re-verification against the new source.

Implemented as `aivss_spec_provenance.py`, with one deliberate deviation from
the original sketch: no hand-typed page-range table. `catalog_provenance_report()`
calls `aivss_spec_search.cite_spec_reference()` for every risk/factor key at
report-generation time instead — a hand-typed table would itself go stale
the moment the OCR text is regenerated, which is exactly the drift problem
this idea exists to catch. `SPEC_VERSION = "v0.8"`, `SPEC_PUBLISHED_DATE =
"2026-04-10"`, and `SPEC_PINNED_PAGE_COUNT = 98` are the only hand-set pins;
everything else is computed and re-verified on every call. **Correction
(2026-07-28, same day):** this module originally pinned `SPEC_VERSION =
"0.8-draft"` — an unverified assumption. Directly checked against the
official OWASP AIVSS site while testing the live calculators (see README.md
"Version and date verification" and "Live calculator comparison"): the
document never calls itself a draft anywhere in its 98 pages, and the site
headlines it "AIVSS v0.8 Released." Corrected to `"v0.8"` with a real
published date sourced from the site's own HTTP `Last-Modified` header on
the PDF asset, cross-checked byte-for-byte against the local copy in this
folder.

### 7. Confidence/uncertainty flagging

Any skill with a classification step that isn't 100% deterministic (idea #3
and #4 above) should return an explicit confidence/flag distinguishing "exact
keyword match" from "ambiguous — agent should confirm" — preserves audit
defensibility instead of silently guessing.

## Suggested phasing (original plan, superseded 2026-07-28)

1. Idea #1 (spec citation search) — lowest risk, no new taxonomy/judgment calls, immediately useful to every existing skill.
2. Idea #3 (banking taxonomy) — reuses the existing worked-examples pattern, deterministic.
3. Idea #6 (spec-version tracking) — small, prevents drift as more skills are added.
4. Idea #5 (MCP manifest) — bigger, cross-cutting; best done once there are enough skills to be worth exposing as a set.
5. Idea #2 and #4 — depend on #1 and #3 respectively for grounding data.

User picked all of #1, #4, #5 (plus the new design-review idea) in one pass
on 2026-07-28, then #2 and #6 in a follow-up pass the same day, rather than
this staged order — see both 2026-07-28 update notes at the top of this
file. Every idea originally listed here is now implemented except #7, which
was addressed inline instead of as its own module: both
`aivss_threat_intel.triage_threat_alert` and
`aivss_spec_search.search_spec`/`cite_spec_reference` return a per-match
`confidence` field.

## Open questions for the user

- Banking taxonomy (idea #3): any specific archetypes beyond the current 5
  that matter most to your use case?
- `aivss_mcp_server.py` is authored but not registered in
  `.claude/settings.json` — register it now, or keep it documentation-only
  until there's a concrete MCP client to point at it?
- Every idea originally in this document is now implemented (except #7,
  addressed inline) — is there a new direction to add, or should this
  roadmap be considered closed for now?
