# AIVSS Calculator (web page) — this repo's formula, tested against the originals

A single self-contained static HTML page (`index.html`, no build step, no
dependencies — open it in any browser or serve it with any static file
server) implementing the **exact same formula** this repo's
`aivss_kg.calculate_aivss()` uses, so it can be checked visually and tested
directly against the two official reference tools, per request.

**Educational/study artifact** — not an official OWASP tool, not affiliated
with or endorsed by OWASP or the reference sites below.

## What it implements

The v0.8 PDF's Section 3.4 **Primary AIVSS Scoring Equation** (the same one
`aivss_kg.py` and every skill in `example AIVSS/` uses):

```
AIVSS = (CVSS_Base + AARS) × Mitigation_Factor
AARS  = (10 − CVSS_Base) × (Factor_Sum / 10) × ThM
```

- **CVSS_Base** — CVSS v4.0 base score (0.0–10.0), entered directly.
- **Factor_Sum** — sum of the 10 Agentic Risk Amplification Factors
  (Autonomy, Tools, Language, Context, Non-Determinism, Opacity,
  Persistence, Identity, Multi-Agent, Self-Modification), each scored
  0 / 0.5 / 1.0.
- **ThM (Threat Multiplier)** — Attacked (1.00) / Proof-of-Concept (0.97,
  default) / Unreported (0.50).
- **Mitigation_Factor** — No/Weak (1.00, default) / Partial (0.83) / Strong
  (0.67).
- Final score rounded to the nearest tenth (round-half-up), banded None
  (0) / Low (0.1–3.9) / Medium (4.0–6.9) / High (7.0–8.9) / Critical
  (9.0–10.0).

A **"Load a scenario"** dropdown pre-fills all 10 of the v0.8 PDF's own
official worked examples (Sections 3.6.1–3.6.10) — the same 10 scenarios
`test_aivss_owasp_calculator_cross_validation.py` uses — so every input can
be reproduced with one click instead of typed by hand.

## Running it

```bash
cd calculator
python3 -m http.server 8000
# open http://127.0.0.1:8000/
```

(Opening `index.html` directly via `file://` also works in most browsers;
some sandboxed environments, including the one used to test this, block
`file://` navigation, hence the http.server instruction.)

## Tested — automated, and against both reference tools live

**1. All 10 official scenarios, automated (Playwright), against this
repo's own `calculate_aivss()` output:**

| # | Scenario | CVSS Base | Expected AIVSS | Got | Match |
|---|---|---|---|---|---|
| 1 | Agentic AI Tool Misuse | 9.4 | 9.9 | 9.9 | ✅ |
| 2 | Agent Access Control Violation | 8.7 | 9.7 | 9.7 | ✅ |
| 3 | Agent Cascading Failures | 7.1 | 9.4 | 9.4 | ✅ |
| 4 | Agent Orchestration and Multi-Agent Exploitation | 9.4 | 10.0 | 10.0 | ✅ |
| 5 | Agent Identity Impersonation | 7.4 | 9.3 | 9.3 | ✅ |
| 6 | Agent Memory and Context Manipulation | 5.8 | 8.9 | 8.9 | ✅ |
| 7 | Insecure Agent Critical Systems Interaction | 6.9 | 9.2 | 9.2 | ✅ |
| 8 | Agent Supply Chain and Dependency Risk | 9.3 | 9.7 | 9.7 | ✅ |
| 9 | Agent Untraceability | 5.3 | 8.3 | 8.3 | ✅ |
| 10 | Agent Goal and Instruction Manipulation | 2.1 | 7.1 | 7.1 | ✅ |

**10/10 match exactly.** These are the same expected values already pinned
in `example AIVSS/test_aivss_owasp_calculator_cross_validation.py`
(re-confirmed passing, 3/3, before writing this page).

**2. Live, real-time spot check against
[aivss.parthsohaney.online](https://aivss.parthsohaney.online/)** — the
community AIVSS calculator linked from the official OWASP homepage, which
states it "Reproduces the v0.8 report exactly." Its own "Formula
Visualization" panel reads, verbatim: *"AIVSS = (CVSS Base + AARS Uplift) ×
Mitigation Factor"* / *"AARS Uplift = (10 − CVSS Base) × (Factor Sum / 10)
× Threat Multiplier"* — character-for-character the same formula. Loaded its
"Load OWASP Scenario" dropdown live (Playwright, this session) for two
scenarios:

| Scenario | This page | aivss.parthsohaney.online (live) | Match |
|---|---|---|---|
| 1. Agentic AI Tool Misuse | 9.9 | 9.9 | ✅ |
| 10. Agent Goal and Instruction Manipulation | 7.1 | 7.1 | ✅ |

Screenshots: [`test_screenshots/02_calculator_scenario1_result.png`](test_screenshots/02_calculator_scenario1_result.png)
vs. [`test_screenshots/04_reference_site_scenario1.png`](test_screenshots/04_reference_site_scenario1.png);
[`test_screenshots/03_calculator_scenario10_result.png`](test_screenshots/03_calculator_scenario10_result.png)
vs. [`test_screenshots/05_reference_site_scenario10.png`](test_screenshots/05_reference_site_scenario10.png).

**3. Reviewed [aivss.owasp.org/ssvc.html](https://aivss.owasp.org/ssvc.html)
live** — the **AIVSS-SSVC Calculator**. Confirmed it is genuinely a
different tool, not a second implementation of the same formula, matching
what this repo already documented from the v0.8 PDF (page 51: *"a parallel
but complementary effort... designed to be used together rather than as
alternatives"*):

- **Different inputs:** P(Threat) exploitation state, P(Vulnerability)
  posture, systemic Impact, and 10 differently-named capability factors
  (Execution Autonomy, Tool Authority Level, Code Execution Rights,
  Critical System Access, Persistent Memory, Dynamic Identity &
  Permissions, Multi-Agent Coordination, Self-Modification Capability,
  Non-Determinism Level, Deceptiveness Potential) scored 1–5 and grouped
  into Category A/B/C averages.
- **Different formula:** `Risk Score = Likelihood × Exposure × Impact`
  (e.g. `0.25 × 8 × 10 = 20` in the default example shown), not
  `(CVSS + AARS) × Mitigation`.
- **Different output type:** a categorical **Remediation Outcome** —
  Defer / Scheduled / Out-of-Cycle / **Immediate** — with a timeline (e.g.
  "0–7 days"), not a 0–10 severity number.

Screenshot: [`test_screenshots/06_ssvc_reference_page.png`](test_screenshots/06_ssvc_reference_page.png).
**No numeric comparison was attempted against SSVC** — doing so would be
comparing two things that were never meant to produce the same kind of
output, exactly as this repo's existing cross-validation writeup already
concluded (see the root README's "Verified correctness" and
`example AIVSS/README.md`'s "Live calculator comparison").

## Files

```
calculator/
├── index.html              # the calculator itself, self-contained
└── test_screenshots/
    ├── 01_calculator_blank.png
    ├── 02_calculator_scenario1_result.png
    ├── 03_calculator_scenario10_result.png
    ├── 04_reference_site_scenario1.png       # aivss.parthsohaney.online, live
    ├── 05_reference_site_scenario10.png      # aivss.parthsohaney.online, live
    └── 06_ssvc_reference_page.png            # aivss.owasp.org/ssvc.html, live
```
