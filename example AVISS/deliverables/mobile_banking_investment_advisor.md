# AIVSS Assessment — Mobile Banking - AI Investment Advisory
role: IT Internal Audit | output: audit_program | schema: rag.aivss-assessment-skills.v1

**Objective:** ประเมินความเสี่ยง AIVSS-amplified ของ 'Mobile Banking - AI Investment Advisory' ในมุมมองของ IT Internal Audit (independent re-assessment)
**Scope:** Chat-based robo-advisor embedded in the mobile banking app; reads customer KYC/suitability profile and portfolio data; can call a fund-switch/rebalance API with a one-tap confirm; backed by a third-party LLM.
**Regulatory context:** SEC Thailand robo-advisor guideline, BOT IT risk / third-party risk management, PDPA

## Risks
### Agent Supply Chain and Dependency Risk (supply_chain) — high
- COBIT: APO10.04, APO10.05, APO12.03, APO13.01, EDM03.01
- Control focus: governance ownership, risk appetite, AI risk profile, ISMS scope, and oversight
- Control focus: AI component inventory, due diligence, contractual controls, monitoring, concentration risk, and exit
- PBC/Evidence: AI governance charter and accountable-owner/RACI
- PBC/Evidence: approved risk appetite, AI risk register, and treatment decisions
- PBC/Evidence: board or risk-committee oversight and ISMS scope records
- PBC/Evidence: AI component/SBOM and critical-supplier inventory
- PBC/Evidence: supplier risk assessments, contracts, right-to-audit, and incident clauses
- PBC/Evidence: performance/compliance monitoring, change notices, and tested exit plan
- Test: trace selected AIVSS risks into the approved enterprise risk profile
- Test: inspect design approval and sample operating oversight evidence
- Test: sample critical suppliers from onboarding through monitoring and renewal
- Test: inspect one material model/tool change and one exit or substitution exercise

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

### Agent Orchestration and Multi-Agent Exploitation (orchestration) — high
- COBIT: BAI03.02, BAI04.04, BAI06.01, BAI07.05, BAI07.08, DSS04.04, DSS05.02
- Control focus: agent topology, inter-agent authentication, message integrity, delegated authority, and blast radius
- Control focus: authorized changes, acceptance criteria, adversarial testing, release evidence, rollback, and PIR
- Control focus: critical dependencies, capacity thresholds, graceful degradation, continuity exercises, and recoverability
- PBC/Evidence: agent topology, data-flow, and trust-boundary diagrams
- PBC/Evidence: inter-agent authentication/authorization and delegated-scope configuration
- PBC/Evidence: message integrity, replay protection, and orchestration test results
- PBC/Evidence: versioned prompts/models/tools and approved change tickets
- PBC/Evidence: acceptance, security, and adversarial test evidence
- PBC/Evidence: release/rollback records and post-implementation review
- PBC/Evidence: BIA, service dependency map, RTO/RPO, and failure-mode analysis
- PBC/Evidence: capacity/circuit-breaker/failover configuration and alerts
- PBC/Evidence: BCP/DR exercise results, recovery evidence, and tracked remediation
- Test: trace delegated authority across a complete multi-agent transaction
- Test: test replay, identity substitution, and boundary failure controls
- Test: sample normal and emergency AI changes from approval through deployment
- Test: reconcile production versions to approved baselines and PIR actions
- Test: inspect one dependency-failure exercise against approved RTO/RPO
- Test: verify remediation from the latest continuity test through closure

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

### Agentic AI Tool Misuse (tool_misuse) — high
- COBIT: APO10.04, APO10.05, BAI06.01, BAI07.05, BAI07.08, DSS05.04, DSS06.03, DSS06.05, MEA01.03, MEA04.06, MEA04.07
- Control focus: least privilege, machine identity lifecycle, segregation of duties, and tool-call authorization
- Control focus: AI component inventory, due diligence, contractual controls, monitoring, concentration risk, and exit
- Control focus: authorized changes, acceptance criteria, adversarial testing, release evidence, rollback, and PIR
- Control focus: attributable and time-consistent audit trails across user, agent, model, memory, and tool boundaries
- Control focus: criteria, population, sample, design adequacy, operating evidence, exceptions, cause, impact, and follow-up
- PBC/Evidence: agent/service-account and privileged-tool inventory
- PBC/Evidence: authorization matrix, access reviews, and SoD exception register
- PBC/Evidence: approved tool-call logs and revoked-access samples
- PBC/Evidence: AI component/SBOM and critical-supplier inventory
- PBC/Evidence: supplier risk assessments, contracts, right-to-audit, and incident clauses
- PBC/Evidence: performance/compliance monitoring, change notices, and tested exit plan
- PBC/Evidence: versioned prompts/models/tools and approved change tickets
- PBC/Evidence: acceptance, security, and adversarial test evidence
- PBC/Evidence: release/rollback records and post-implementation review
- PBC/Evidence: logging standard, event schema, retention, and time-synchronization evidence
- PBC/Evidence: SIEM/source coverage and protected log-access records
- PBC/Evidence: end-to-end transaction reconstruction with correlation identifiers
- PBC/Evidence: approved control design, owner, frequency, population, and evidence standard
- PBC/Evidence: complete population plus reproducible sample and operating evidence
- PBC/Evidence: exceptions, root cause, impact assessment, action owner, and due date
- Test: sample joiner/mover/leaver and privilege-escalation events
- Test: reperform denied and approved privileged tool calls against policy
- Test: sample critical suppliers from onboarding through monitoring and renewal
- Test: inspect one material model/tool change and one exit or substitution exercise
- Test: sample normal and emergency AI changes from approval through deployment
- Test: reconcile production versions to approved baselines and PIR actions
- Test: reconstruct samples from user intent through agent decision and tool outcome
- Test: test log completeness, tamper protection, clock alignment, and exception follow-up
- Test: separate test of design from test of operating effectiveness
- Test: form a finding only from verified condition evidence against approved criteria

### Agent Access Control Violation (access_control) — medium
- COBIT: BAI03.02, DSS05.02, DSS05.04, DSS06.03, MEA04.06, MEA04.07

### Agent Untraceability (untraceability) — medium
- COBIT: APO14.08, DSS02.02, DSS02.04, DSS06.02, DSS06.05, MEA01.03, MEA04.06, MEA04.07

## Scored findings
- [Agent Goal and Instruction Manipulation] Prompt injection can steer the advisor into auto-submitting a portfolio shift to a higher-risk fund than the customer's suitability profile allows, with no human-confirmation gate. -> AIVSS 7.6 (High), CVSS_Base 2.4, Factor_Sum 7.0

## Proof boundary
AIVSS graph/score และ audit-lens นี้เป็นเครื่องมือวางแผนตรวจสอบเชิงวิเคราะห์ (Codex-curated) ไม่ใช่หลักฐานว่า control ถูกออกแบบหรือปฏิบัติงานอย่างมีประสิทธิผล และไม่ใช่ข้อสรุป finding/compliance ด้วยตัวเอง ต้องมี condition evidence ของระบบจริงก่อนสรุปผลเสมอ