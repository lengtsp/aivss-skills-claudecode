# AIVSS Assessment — Digital Channel - Real-Time Fraud/Transaction Monitoring Agent
role: IT Internal Audit | output: audit_program | schema: rag.aivss-assessment-skills.v1

**Objective:** ประเมินความเสี่ยง AIVSS-amplified ของ 'Digital Channel - Real-Time Fraud/Transaction Monitoring Agent' ในมุมมองของ IT Internal Audit (independent re-assessment)
**Scope:** Behavioral-analytics + ML scoring agent watching transaction streams; for high-confidence scores it can auto-freeze an account, auto-block a transaction, or force step-up authentication without waiting for analyst review; coordinates with a case-management/notification agent; retains a rolling behavioral baseline per customer.
**Regulatory context:** BOT IT risk / fraud-management guideline, PDPA (behavioral profiling)

## Risks
### Agent Cascading Failures (cascading_failures) — high
- COBIT: BAI04.04, DSS02.02, DSS02.04, DSS04.04, MEA01.03
- Control focus: AI incident taxonomy, severity, ownership, investigation, escalation, evidence preservation, and lessons learned
- Control focus: critical dependencies, capacity thresholds, graceful degradation, continuity exercises, and recoverability
- PBC/Evidence: AI incident taxonomy, severity matrix, playbooks, and escalation tree
- PBC/Evidence: incident tickets, investigation records, preserved logs, and communications
- PBC/Evidence: metrics, root-cause, remediation, and repeat-event monitoring
- PBC/Evidence: BIA, service dependency map, RTO/RPO, and failure-mode analysis
- PBC/Evidence: capacity/circuit-breaker/failover configuration and alerts
- PBC/Evidence: BCP/DR exercise results, recovery evidence, and tracked remediation
- Test: sample incidents for classification, response time, escalation, and closure evidence
- Test: trace high-impact events into risk, problem, change, and governance reporting
- Test: inspect one dependency-failure exercise against approved RTO/RPO
- Test: verify remediation from the latest continuity test through closure

### Insecure Agent Critical Systems Interaction (critical_systems) — high
- COBIT: APO12.03, APO13.01, BAI03.02, BAI04.04, DSS02.02, DSS02.04, DSS04.04, DSS05.02, EDM03.01, MEA01.03
- Control focus: governance ownership, risk appetite, AI risk profile, ISMS scope, and oversight
- Control focus: agent topology, inter-agent authentication, message integrity, delegated authority, and blast radius
- Control focus: AI incident taxonomy, severity, ownership, investigation, escalation, evidence preservation, and lessons learned
- Control focus: critical dependencies, capacity thresholds, graceful degradation, continuity exercises, and recoverability
- PBC/Evidence: AI governance charter and accountable-owner/RACI
- PBC/Evidence: approved risk appetite, AI risk register, and treatment decisions
- PBC/Evidence: board or risk-committee oversight and ISMS scope records
- PBC/Evidence: agent topology, data-flow, and trust-boundary diagrams
- PBC/Evidence: inter-agent authentication/authorization and delegated-scope configuration
- PBC/Evidence: message integrity, replay protection, and orchestration test results
- PBC/Evidence: AI incident taxonomy, severity matrix, playbooks, and escalation tree
- PBC/Evidence: incident tickets, investigation records, preserved logs, and communications
- PBC/Evidence: metrics, root-cause, remediation, and repeat-event monitoring
- PBC/Evidence: BIA, service dependency map, RTO/RPO, and failure-mode analysis
- PBC/Evidence: capacity/circuit-breaker/failover configuration and alerts
- PBC/Evidence: BCP/DR exercise results, recovery evidence, and tracked remediation
- Test: trace selected AIVSS risks into the approved enterprise risk profile
- Test: inspect design approval and sample operating oversight evidence
- Test: trace delegated authority across a complete multi-agent transaction
- Test: test replay, identity substitution, and boundary failure controls
- Test: sample incidents for classification, response time, escalation, and closure evidence
- Test: trace high-impact events into risk, problem, change, and governance reporting
- Test: inspect one dependency-failure exercise against approved RTO/RPO
- Test: verify remediation from the latest continuity test through closure

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

### Agent Goal and Instruction Manipulation (goal_instruction) — medium
- COBIT: APO12.03, APO13.01, BAI06.01, BAI07.05, BAI07.08, DSS06.05, EDM03.01, MEA01.03

### Agent Orchestration and Multi-Agent Exploitation (orchestration) — medium
- COBIT: BAI03.02, BAI04.04, BAI06.01, BAI07.05, BAI07.08, DSS04.04, DSS05.02

### Agent Access Control Violation (access_control) — medium
- COBIT: BAI03.02, DSS05.02, DSS05.04, DSS06.03, MEA04.06, MEA04.07

### Agentic AI Tool Misuse (tool_misuse) — medium
- COBIT: APO10.04, APO10.05, BAI06.01, BAI07.05, BAI07.08, DSS05.04, DSS06.03, DSS06.05, MEA01.03, MEA04.06, MEA04.07

### Agent Untraceability (untraceability) — medium
- COBIT: APO14.08, DSS02.02, DSS02.04, DSS06.02, DSS06.05, MEA01.03, MEA04.06, MEA04.07

### Agent Identity Impersonation (identity_impersonation) — low
- COBIT: DSS05.04, DSS06.03

## Scored findings
- [Agent Memory and Context Manipulation] An adversary can deliberately shape a customer's transaction pattern over weeks to drift the behavioral baseline (memory/context poisoning), so a later genuinely fraudulent transaction scores as normal; the inverse — injected lookalike-noise across many accounts — can trigger a mass false-positive auto-freeze event against real customers. -> AIVSS 4.5 (Medium), CVSS_Base 3.5, Factor_Sum 6.0

## Proof boundary
AIVSS graph/score และ audit-lens นี้เป็นเครื่องมือวางแผนตรวจสอบเชิงวิเคราะห์ (Codex-curated) ไม่ใช่หลักฐานว่า control ถูกออกแบบหรือปฏิบัติงานอย่างมีประสิทธิผล และไม่ใช่ข้อสรุป finding/compliance ด้วยตัวเอง ต้องมี condition evidence ของระบบจริงก่อนสรุปผลเสมอ