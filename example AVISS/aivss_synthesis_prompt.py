"""Shared narrative-synthesis prompt scaffold — closes a real quality gap
found during a live test on 2026-07-28 (see README.md "Live quality test").

Test setup: the same trade-finance (Letter of Credit auto-disbursement
agent) design question was answered three ways — two general-knowledge LLM
baselines, and `aivss_design_review`'s real structured+spec-cited output
called directly. Finding: the AIVSS skill's raw markdown is *more*
traceable (real AIVSS v0.8 page citations) and *more* consistent
(deterministic risk ranking) than a free-form LLM answer, but *less* useful
as a standalone answer to an open design question — it reads as a
reference/checklist, not a consultant's response, and doesn't weave in the
scenario's own regulatory/domain context (e.g. it never mentions "UCP 600"
even when that string was supplied in `regulatory_context`, because
`DESIGN_MITIGATIONS` is a fixed per-risk-type catalog, not scenario-aware).

This is the missing "narrate over already-computed facts" step from
`SKILLS_ROADMAP.md`'s core design principle, made explicit instead of left
for each caller to improvise differently. It does NOT call an LLM itself
(that would violate the "skills stay LLM-free / provider-agnostic"
convention) — it only formats a prompt for whichever LLM the caller is
already using to fill in.
"""

from __future__ import annotations


def build_synthesis_prompt(
    *,
    grounded_markdown: str,
    original_question: str = "",
    answer_language: str = "Thai",
    audience_hint: str = "a business/design audience",
) -> str:
    """Wrap already-rendered, grounded markdown (from any render_*_markdown()
    in this folder) with instructions for a caller LLM to narrate over it.

    Deliberately permissive about phrasing/organization/added judgment, but
    strict about not inventing facts: the LLM may connect listed mitigations
    to the scenario's own regulatory/domain terms (this is exactly the
    "UCP 600 never gets mentioned" gap the live test found — the model
    reading this prompt is expected to make that connection, since the
    deterministic skill correctly does not attempt free-form domain
    reasoning itself), but must not add risks, mitigations, or citations
    beyond what's in `grounded_markdown`.
    """

    question_block = f"\nOriginal question from the user:\n{original_question}\n" if original_question else ""
    return (
        "You are answering a design/security consultation question. Use ONLY "
        "the verified, deterministic AIVSS (OWASP Agentic AI Core Security "
        "Risks) findings below as your factual grounding — do not invent "
        "additional risks, mitigations, or spec citations beyond what is "
        "listed. You MAY: connect the listed mitigations to the specific "
        "regulatory/domain terms named in the scope or regulatory context "
        "below (e.g. named laws, standards, or protocols), add general "
        "security-engineering judgment on top, and organize/prioritize/phrase "
        "the final answer freely for " + audience_hint + ". Preserve the "
        "proof-boundary caveat at the end of your answer, in substance if not "
        "verbatim — do not present this as a certified/validated assessment. "
        "IMPORTANT: each 'Spec grounding' page citation supports the risk/"
        "finding *description* above it, not any individual mitigation, "
        "control question, or organization-context item listed nearby — do "
        "not claim a specific mitigation is spec-sourced or cite a page "
        "number next to a mitigation unless that exact page's snippet "
        "demonstrates it.\n"
        f"{question_block}\n"
        "--- Grounded AIVSS data (do not exceed this factual scope) ---\n"
        f"{grounded_markdown}\n"
        "--- End grounded data ---\n\n"
        f"Now write the final answer in {answer_language}, as a security "
        "consultant would give directly to the person who asked."
    )


__all__ = ["build_synthesis_prompt"]
