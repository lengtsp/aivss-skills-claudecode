# AIVSS Assessment — Digital Lending - AI Credit Scoring / Underwriting Agent
role: IT Internal Audit | output: audit_program | schema: rag.aivss-assessment-skills.v1

**Objective:** ประเมินความเสี่ยง AIVSS-amplified ของ 'Digital Lending - AI Credit Scoring / Underwriting Agent' ในมุมมองของ IT Internal Audit (independent re-assessment)
**Scope:** Document-reading agent (OCR + LLM) extracts income evidence from bank statements/payslips and combines it with a numeric scorecard and an external credit-bureau lookup; below a small-loan threshold it auto-approves without human review, above it the recommendation goes to a human underwriter; retains applicant profile/documents across re-application attempts.
**Regulatory context:** BOT lending / responsible-lending guideline, Fair-lending / adverse-action disclosure expectations, PDPA

## Risks
### Agent Goal and Instruction Manipulation (goal_instruction) — high
- COBIT: APO12.03, APO13.01, BAI06.01, BAI07.05, BAI07.08, DSS06.05, EDM03.01, MEA01.03
- Control focus: governance ownership, risk appetite, AI risk profile, ISMS scope, and oversight
- Control focus: authorized changes, acceptance criteria, adversarial testing, release evidence, rollback, and PIR
- Control focus: attributable and time-consistent audit trails across user, agent, model, memory, and tool boundaries
- PBC/Evidence: AI governance charter and accountable-owner/RACI
- PBC/Evidence: approved risk appetite, AI risk register, and treatment decisions
- PBC/Evidence: board or risk-committee oversight and ISMS scope records
- PBC/Evidence: versioned prompts/models/tools and approved change tickets
- PBC/Evidence: acceptance, security, and adversarial test evidence
- PBC/Evidence: release/rollback records and post-implementation review
- PBC/Evidence: logging standard, event schema, retention, and time-synchronization evidence
- PBC/Evidence: SIEM/source coverage and protected log-access records
- PBC/Evidence: end-to-end transaction reconstruction with correlation identifiers
- Test: trace selected AIVSS risks into the approved enterprise risk profile
- Test: inspect design approval and sample operating oversight evidence
- Test: sample normal and emergency AI changes from approval through deployment
- Test: reconcile production versions to approved baselines and PIR actions
- Test: reconstruct samples from user intent through agent decision and tool outcome
- Test: test log completeness, tamper protection, clock alignment, and exception follow-up

### Agent Identity Impersonation (identity_impersonation) — high
- COBIT: DSS05.04, DSS06.03
- Control focus: least privilege, machine identity lifecycle, segregation of duties, and tool-call authorization
- PBC/Evidence: agent/service-account and privileged-tool inventory
- PBC/Evidence: authorization matrix, access reviews, and SoD exception register
- PBC/Evidence: approved tool-call logs and revoked-access samples
- Test: sample joiner/mover/leaver and privilege-escalation events
- Test: reperform denied and approved privileged tool calls against policy

### Agent Memory and Context Manipulation (memory_context) — high
- COBIT: APO14.08, DSS06.02
- Control focus: memory provenance, tenant segregation, retention, deletion, processing integrity, and replay risk
- PBC/Evidence: memory-store schema, lineage, tenant-boundary, and encryption configuration
- PBC/Evidence: retention/deletion standard with executed deletion samples
- PBC/Evidence: memory poisoning, replay, and integrity-monitoring test results
- Test: trace one memory item from creation through use, retention, and deletion
- Test: test cross-session and cross-tenant isolation with authorized synthetic data

### Agent Supply Chain and Dependency Risk (supply_chain) — medium
- COBIT: APO10.04, APO10.05, APO12.03, APO13.01, EDM03.01

### Agent Cascading Failures (cascading_failures) — medium
- COBIT: BAI04.04, DSS02.02, DSS02.04, DSS04.04, MEA01.03

### Insecure Agent Critical Systems Interaction (critical_systems) — medium
- COBIT: APO12.03, APO13.01, BAI03.02, BAI04.04, DSS02.02, DSS02.04, DSS04.04, DSS05.02, EDM03.01, MEA01.03

### Agent Orchestration and Multi-Agent Exploitation (orchestration) — medium
- COBIT: BAI03.02, BAI04.04, BAI06.01, BAI07.05, BAI07.08, DSS04.04, DSS05.02

### Agent Access Control Violation (access_control) — medium
- COBIT: BAI03.02, DSS05.02, DSS05.04, DSS06.03, MEA04.06, MEA04.07

### Agentic AI Tool Misuse (tool_misuse) — medium
- COBIT: APO10.04, APO10.05, BAI06.01, BAI07.05, BAI07.08, DSS05.04, DSS06.03, DSS06.05, MEA01.03, MEA04.06, MEA04.07

### Agent Untraceability (untraceability) — medium
- COBIT: APO14.08, DSS02.02, DSS02.04, DSS06.02, DSS06.05, MEA01.03, MEA04.06, MEA04.07

## Scored findings
- [Agent Goal and Instruction Manipulation] A forged bank statement PDF with adversarial text hidden in the document (e.g. white-on-white instructions targeting the LLM's document-reading step) can steer the agent into auto-approving a fast-track loan for an applicant with insufficient real income, with no human reviewer in that tier. -> AIVSS 7.1 (High), CVSS_Base 3.1, Factor_Sum 6.0

## Proof boundary
AIVSS graph/score และ audit-lens นี้เป็นเครื่องมือวางแผนตรวจสอบเชิงวิเคราะห์ (Codex-curated) ไม่ใช่หลักฐานว่า control ถูกออกแบบหรือปฏิบัติงานอย่างมีประสิทธิผล และไม่ใช่ข้อสรุป finding/compliance ด้วยตัวเอง ต้องมี condition evidence ของระบบจริงก่อนสรุปผลเสมอ