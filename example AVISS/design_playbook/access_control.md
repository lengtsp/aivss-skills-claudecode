# วิธีคิด (Reasoning) — AI Case-Management Agent for KYC/AML Investigation

วิธีคิด: access_control ถูกขยายด้วย tools + identity + persistence ระบบนี้ถือ credential เดียวเข้าหลายระบบพร้อมกัน (tools=1, external tool control surface กว้าง) ใช้ identity เดิมต่อเนื่องยาวนานหลาย session ของเคสเดียว (persistence=1) และมีการสวม บทบาทตามเคสที่ได้รับมอบหมายบางส่วน (identity=0.5) — โครงสร้างนี้เข้าเงื่อนไข temporal permission drift และ confused-deputy pattern ได้ง่ายถ้าไม่มี re-authorization ต่อระบบ

---

# AIVSS Design Review — AI Case-Management Agent for KYC/AML Investigation
role: AI Security Lead | schema: rag.aivss-design-review-skills.v1

**Objective:** ทบทวนการออกแบบ 'AI Case-Management Agent for KYC/AML Investigation' เทียบกับ AIVSS core risks ก่อน/ระหว่างพัฒนา ในมุมมองของ AI Security Lead (proactive design-time review)
**Scope:** สืบสวนเคส AML/KYC ที่น่าสงสัยโดยใช้ identity ของผู้สืบสวนคนเดียวกันข้าม case-management, core banking, และ watchlist screening system ตลอดระยะเวลาสืบสวนหลายสัปดาห์ต่อเนื่อง
**Regulatory context:** AMLO customer due diligence, BOT IT risk, PDPA

## Risk-by-risk design recommendations
### Agent Access Control Violation (access_control) — high
agent เข้าถึงหรือกระทำการเกินสิทธิ์ที่ควรได้รับ รวมถึงการยกระดับสิทธิ์ (privilege escalation) หรือข้ามขอบเขตการอนุญาตที่กำหนดไว้

Design targets for amplifying factors:
- External Tool Control Surface: The breadth and privilege of external APIs/tools the agent can access.
- Dynamic Identity: The ability to assume different user roles or permissions at runtime.
- Persistent State Retention: The ability to retain memory or state across sessions.

Recommended design mitigations:
- ออกแบบ least-privilege + time-boxed role ต่องาน ป้องกัน temporal permission drift และ orphaned account persistence
- ใช้ cryptographic role attestation (signed token) แทนการให้ agent อ้างสิทธิ์ด้วยคำสั่งข้อความ ป้องกัน forged role assertion
- ตรวจสิทธิ์ซ้ำ (re-authorize) ทุกครั้งที่ agent หนึ่งขอให้อีก agent กระทำการแทน ป้องกัน confused-deputy / multi-agent permission mismatch
- แยก credential/token store ต่อ agent พร้อม rotation ป้องกัน credential/token mismanagement
- ปิด session/role อัตโนมัติเมื่อ task จบ ป้องกัน cross-context privilege bleed ระหว่าง environment

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.11 (medium): ...1</page_number> Agent Access Control Violation occurs when an attacker manipulates or exploits an AI agent's permission system, causing the agent to operate beyond its intended authorization boundaries. This can occur t...
- p.12 (medium): ...acker to gain unauthorized access by simply instructing the agent to assume a privileged identity. - Temporal Permission Drift: An agent's permissions or roles persist longer than necessary for a task, creating an exploi...

### Agent Supply Chain and Dependency Risk (supply_chain) — medium
ความเสี่ยงที่ความมั่นคง/integrity ของ agent ถูกโจมตีผ่านช่องโหว่ใน component พื้นฐานหรือ dependency ที่ agent พึ่งพา (model, library, vendor, plugin)

Design targets for amplifying factors:
- Execution Autonomy: The ability to execute actions without human verification.
- External Tool Control Surface: The breadth and privilege of external APIs/tools the agent can access.
- Natural Language Interface: The reliance on unstructured natural language for goal formulation and instruction.
- Contextual Awareness: The utilization of environmental sensors or broad data context to drive decisions.
- Behavioral Non-Determinism: The variance in output or action for identical inputs.
- Opacity & Reflexivity: The lack of internal visibility or the ability to audit decision logic.
- Persistent State Retention: The ability to retain memory or state across sessions.
- Dynamic Identity: The ability to assume different user roles or permissions at runtime.
- Multi-Agent Interactions: Coordination or dependencies on other autonomous agents.
- Self-Modification: The ability to alter its own code, prompts, or tool configurations.

Recommended design mitigations:
- เก็บ signed provenance/SBOM ของ model และ dependency ทุกตัว ป้องกัน model/registry tampering
- ปิด write access ที่ไม่จำเป็นบน model registry/artifact store ป้องกัน unauthorized model swap
- ตรวจสอบ (vet) MCP server/marketplace app ของบุคคลที่สามก่อนติดตั้ง ป้องกัน malicious dependency
- pin เวอร์ชัน dependency ที่ผ่านการ review แล้ว ไม่ auto-update โดยไม่มี change control

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.33 (medium): ...ndors' security practices, often without the means to independently verify them. KEY RISKS (See Figure 8) - Development Chain Attack: Introduces malicious code or components during the agent development process, potent...
- p.35 (medium): ...h models, data, code, tools, and services) branches down via crossing arrows into 4 quadrant boxes: "Build & Development Chain" (top-left, pink): - Development chain attack - Deployment systems attack - Naive prompt reu...

### Insecure Agent Critical Systems Interaction (critical_systems) — medium
agent เชื่อมต่อ/สั่งการกับ environment ระบบ หรืออุปกรณ์ที่สำคัญ (critical infra, IaaS/SaaS, IoT) โดยไม่มีการควบคุมที่เพียงพอ

Design targets for amplifying factors:
- Execution Autonomy: The ability to execute actions without human verification.
- External Tool Control Surface: The breadth and privilege of external APIs/tools the agent can access.
- Contextual Awareness: The utilization of environmental sensors or broad data context to drive decisions.
- Self-Modification: The ability to alter its own code, prompts, or tool configurations.

Recommended design mitigations:
- บังคับ human-in-the-loop gate สำหรับ action ที่ irreversible หรือกระทบ critical system
- แบ่ง network segmentation ระหว่าง agent กับ critical infrastructure ป้องกัน SSRF/direct access
- จำกัดสิทธิ์ deployment-bot ใน CI/CD pipeline เฉพาะ scope ที่จำเป็น ป้องกัน pipeline tampering
- ต้องมี validation + rollback path ก่อน apply การเปลี่ยนแปลงบน production จริง

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.28 (medium): ...tal institutions being manipulated in unintended ways that can cause catastrophic consequences. This includes physical consequences, operational disruptions, and safety incidents. The autonomous nature of AI agents combi...
- p.30 (medium): ...Critical Systems Interaction — Key Risks". Top box "Autonomous Actions on Mission-Critical Assets" (digital + physical impact when guardrails and validation are weak) branches down via crossing arrows into 4 quadrant box...

### Agent Orchestration and Multi-Agent Exploitation (orchestration) — medium
การโจมตีที่มุ่งเป้าไปที่การประสานงาน/สื่อสารระหว่าง agent หลายตัว เช่น การปลอมแปลง message หรือแทรกแซงการมอบหมายงานระหว่าง agent

Design targets for amplifying factors:
- Execution Autonomy: The ability to execute actions without human verification.
- Dynamic Identity: The ability to assume different user roles or permissions at runtime.
- Multi-Agent Interactions: Coordination or dependencies on other autonomous agents.
- Contextual Awareness: The utilization of environmental sensors or broad data context to drive decisions.

Recommended design mitigations:
- เข้ารหัส + ยืนยันตัวตนทุก inter-agent channel พร้อม message-integrity check ป้องกัน communication interception/injection
- ควบคุม integrity ของ shared memory/RAG/knowledge base ที่หลาย agent ใช้ร่วมกัน ป้องกัน shared knowledge poisoning
- ผูก session/message กับ nonce หรือ timestamp ที่ตรวจ replay ได้ ป้องกัน session fixation/replay
- ตรวจสอบ capability/schema ของ agent ใหม่ก่อนขึ้นทะเบียนใน orchestrator registry ป้องกัน capability drift / rogue autonomy

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.18 (medium): <page_number>18</page_number> KEY RISKS (See Figure 4) - Inter-Agent Communication Exploitation: Occurs when adversaries intercept, manipulate, or inject messages exch...
- p.19 (medium): ...down via arrows (crossing pattern) into 4 quadrant boxes: "Messaging & Session Attacks" (top-left, pink): - Inter-agent communication exploitation - Session fixation & replay attacks "Shared Context & Registries" (top...

### Agent Memory and Context Manipulation (memory_context) — medium
การโจมตีที่มุ่งเป้าไปที่วิธีที่ agent จัดเก็บ/คงไว้/ใช้ข้อมูลบริบทและความจำ ทั้งในและข้าม session

Design targets for amplifying factors:
- Persistent State Retention: The ability to retain memory or state across sessions.
- Contextual Awareness: The utilization of environmental sensors or broad data context to drive decisions.
- Opacity & Reflexivity: The lack of internal visibility or the ability to audit decision logic.

Recommended design mitigations:
- แยก memory store ต่อ tenant/ต่อ user อย่างเข้มงวด ป้องกัน cross-session/cross-user memory contamination
- กำหนด retention/deletion policy ที่ purge residual memory หลังหมดอายุการใช้งาน ป้องกัน residual memory exploitation
- ตรวจสอบ integrity ของ context/memory ก่อนใช้งาน (checksum/signature) ป้องกัน context poisoning
- ติดตาม drift ของพฤติกรรม agent เทียบ baseline เพื่อจับ context drift exploit แต่เนิ่น ๆ

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.25 (medium): ...context resets. This can cause an agent to forget critical security constraints or operational parameters. - Cross-Session Data Leakage: Happens when attackers exploit how agents maintain state across different sessions...
- p.26 (medium): ...memory exploitation - (long-lived / unencrypted zones) "Leakage & Susceptibility" (bottom-right, purple): - Cross-session data leakage (state persists across sessions) - Cognitive resilience variance Diagonal crossed...

## Proof boundary
การประเมินนี้เป็นข้อเสนอแนะเชิงออกแบบ (Codex-curated design guidance) อ้างอิงจากรูปแบบการโจมตี (KEY RISKS) ที่มีการบันทึกไว้ใน AIVSS v0.8 เท่านั้น ไม่ใช่ control ที่ผ่านการตรวจสอบ ทดสอบ หรือยืนยันประสิทธิผลแล้ว — ทีมออกแบบต้อง implement, test, และ threat-model แต่ละมาตรการเองก่อนถือว่าความเสี่ยงลดลงจริง และห้ามใช้ผลลัพธ์นี้แทนการตรวจสอบโดย AI Security Lead / Internal Audit

---

## LLM synthesis prompt (ready to hand to a narrating LLM)

```
You are answering a design/security consultation question. Use ONLY the verified, deterministic AIVSS (OWASP Agentic AI Core Security Risks) findings below as your factual grounding — do not invent additional risks, mitigations, or spec citations beyond what is listed. You MAY: connect the listed mitigations to the specific regulatory/domain terms named in the scope or regulatory context below (e.g. named laws, standards, or protocols), add general security-engineering judgment on top, and organize/prioritize/phrase the final answer freely for a business/design audience evaluating a system that is being designed or changed. Preserve the proof-boundary caveat at the end of your answer, in substance if not verbatim — do not present this as a certified/validated assessment. IMPORTANT: each 'Spec grounding' page citation supports the risk/finding *description* above it, not any individual mitigation, control question, or organization-context item listed nearby — do not claim a specific mitigation is spec-sourced or cite a page number next to a mitigation unless that exact page's snippet demonstrates it.

Original question from the user:
ควรออกแบบระบบนี้อย่างไรให้ปลอดภัยจากความเสี่ยงด้าน AI agentic?

--- Grounded AIVSS data (do not exceed this factual scope) ---
# AIVSS Design Review — AI Case-Management Agent for KYC/AML Investigation
role: AI Security Lead | schema: rag.aivss-design-review-skills.v1

**Objective:** ทบทวนการออกแบบ 'AI Case-Management Agent for KYC/AML Investigation' เทียบกับ AIVSS core risks ก่อน/ระหว่างพัฒนา ในมุมมองของ AI Security Lead (proactive design-time review)
**Scope:** สืบสวนเคส AML/KYC ที่น่าสงสัยโดยใช้ identity ของผู้สืบสวนคนเดียวกันข้าม case-management, core banking, และ watchlist screening system ตลอดระยะเวลาสืบสวนหลายสัปดาห์ต่อเนื่อง
**Regulatory context:** AMLO customer due diligence, BOT IT risk, PDPA

## Risk-by-risk design recommendations
### Agent Access Control Violation (access_control) — high
agent เข้าถึงหรือกระทำการเกินสิทธิ์ที่ควรได้รับ รวมถึงการยกระดับสิทธิ์ (privilege escalation) หรือข้ามขอบเขตการอนุญาตที่กำหนดไว้

Design targets for amplifying factors:
- External Tool Control Surface: The breadth and privilege of external APIs/tools the agent can access.
- Dynamic Identity: The ability to assume different user roles or permissions at runtime.
- Persistent State Retention: The ability to retain memory or state across sessions.

Recommended design mitigations:
- ออกแบบ least-privilege + time-boxed role ต่องาน ป้องกัน temporal permission drift และ orphaned account persistence
- ใช้ cryptographic role attestation (signed token) แทนการให้ agent อ้างสิทธิ์ด้วยคำสั่งข้อความ ป้องกัน forged role assertion
- ตรวจสิทธิ์ซ้ำ (re-authorize) ทุกครั้งที่ agent หนึ่งขอให้อีก agent กระทำการแทน ป้องกัน confused-deputy / multi-agent permission mismatch
- แยก credential/token store ต่อ agent พร้อม rotation ป้องกัน credential/token mismanagement
- ปิด session/role อัตโนมัติเมื่อ task จบ ป้องกัน cross-context privilege bleed ระหว่าง environment

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.11 (medium): ...1</page_number> Agent Access Control Violation occurs when an attacker manipulates or exploits an AI agent's permission system, causing the agent to operate beyond its intended authorization boundaries. This can occur t...
- p.12 (medium): ...acker to gain unauthorized access by simply instructing the agent to assume a privileged identity. - Temporal Permission Drift: An agent's permissions or roles persist longer than necessary for a task, creating an exploi...

### Agent Supply Chain and Dependency Risk (supply_chain) — medium
ความเสี่ยงที่ความมั่นคง/integrity ของ agent ถูกโจมตีผ่านช่องโหว่ใน component พื้นฐานหรือ dependency ที่ agent พึ่งพา (model, library, vendor, plugin)

Design targets for amplifying factors:
- Execution Autonomy: The ability to execute actions without human verification.
- External Tool Control Surface: The breadth and privilege of external APIs/tools the agent can access.
- Natural Language Interface: The reliance on unstructured natural language for goal formulation and instruction.
- Contextual Awareness: The utilization of environmental sensors or broad data context to drive decisions.
- Behavioral Non-Determinism: The variance in output or action for identical inputs.
- Opacity & Reflexivity: The lack of internal visibility or the ability to audit decision logic.
- Persistent State Retention: The ability to retain memory or state across sessions.
- Dynamic Identity: The ability to assume different user roles or permissions at runtime.
- Multi-Agent Interactions: Coordination or dependencies on other autonomous agents.
- Self-Modification: The ability to alter its own code, prompts, or tool configurations.

Recommended design mitigations:
- เก็บ signed provenance/SBOM ของ model และ dependency ทุกตัว ป้องกัน model/registry tampering
- ปิด write access ที่ไม่จำเป็นบน model registry/artifact store ป้องกัน unauthorized model swap
- ตรวจสอบ (vet) MCP server/marketplace app ของบุคคลที่สามก่อนติดตั้ง ป้องกัน malicious dependency
- pin เวอร์ชัน dependency ที่ผ่านการ review แล้ว ไม่ auto-update โดยไม่มี change control

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.33 (medium): ...ndors' security practices, often without the means to independently verify them. KEY RISKS (See Figure 8) - Development Chain Attack: Introduces malicious code or components during the agent development process, potent...
- p.35 (medium): ...h models, data, code, tools, and services) branches down via crossing arrows into 4 quadrant boxes: "Build & Development Chain" (top-left, pink): - Development chain attack - Deployment systems attack - Naive prompt reu...

### Insecure Agent Critical Systems Interaction (critical_systems) — medium
agent เชื่อมต่อ/สั่งการกับ environment ระบบ หรืออุปกรณ์ที่สำคัญ (critical infra, IaaS/SaaS, IoT) โดยไม่มีการควบคุมที่เพียงพอ

Design targets for amplifying factors:
- Execution Autonomy: The ability to execute actions without human verification.
- External Tool Control Surface: The breadth and privilege of external APIs/tools the agent can access.
- Contextual Awareness: The utilization of environmental sensors or broad data context to drive decisions.
- Self-Modification: The ability to alter its own code, prompts, or tool configurations.

Recommended design mitigations:
- บังคับ human-in-the-loop gate สำหรับ action ที่ irreversible หรือกระทบ critical system
- แบ่ง network segmentation ระหว่าง agent กับ critical infrastructure ป้องกัน SSRF/direct access
- จำกัดสิทธิ์ deployment-bot ใน CI/CD pipeline เฉพาะ scope ที่จำเป็น ป้องกัน pipeline tampering
- ต้องมี validation + rollback path ก่อน apply การเปลี่ยนแปลงบน production จริง

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.28 (medium): ...tal institutions being manipulated in unintended ways that can cause catastrophic consequences. This includes physical consequences, operational disruptions, and safety incidents. The autonomous nature of AI agents combi...
- p.30 (medium): ...Critical Systems Interaction — Key Risks". Top box "Autonomous Actions on Mission-Critical Assets" (digital + physical impact when guardrails and validation are weak) branches down via crossing arrows into 4 quadrant box...

### Agent Orchestration and Multi-Agent Exploitation (orchestration) — medium
การโจมตีที่มุ่งเป้าไปที่การประสานงาน/สื่อสารระหว่าง agent หลายตัว เช่น การปลอมแปลง message หรือแทรกแซงการมอบหมายงานระหว่าง agent

Design targets for amplifying factors:
- Execution Autonomy: The ability to execute actions without human verification.
- Dynamic Identity: The ability to assume different user roles or permissions at runtime.
- Multi-Agent Interactions: Coordination or dependencies on other autonomous agents.
- Contextual Awareness: The utilization of environmental sensors or broad data context to drive decisions.

Recommended design mitigations:
- เข้ารหัส + ยืนยันตัวตนทุก inter-agent channel พร้อม message-integrity check ป้องกัน communication interception/injection
- ควบคุม integrity ของ shared memory/RAG/knowledge base ที่หลาย agent ใช้ร่วมกัน ป้องกัน shared knowledge poisoning
- ผูก session/message กับ nonce หรือ timestamp ที่ตรวจ replay ได้ ป้องกัน session fixation/replay
- ตรวจสอบ capability/schema ของ agent ใหม่ก่อนขึ้นทะเบียนใน orchestrator registry ป้องกัน capability drift / rogue autonomy

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.18 (medium): <page_number>18</page_number> KEY RISKS (See Figure 4) - Inter-Agent Communication Exploitation: Occurs when adversaries intercept, manipulate, or inject messages exch...
- p.19 (medium): ...down via arrows (crossing pattern) into 4 quadrant boxes: "Messaging & Session Attacks" (top-left, pink): - Inter-agent communication exploitation - Session fixation & replay attacks "Shared Context & Registries" (top...

### Agent Memory and Context Manipulation (memory_context) — medium
การโจมตีที่มุ่งเป้าไปที่วิธีที่ agent จัดเก็บ/คงไว้/ใช้ข้อมูลบริบทและความจำ ทั้งในและข้าม session

Design targets for amplifying factors:
- Persistent State Retention: The ability to retain memory or state across sessions.
- Contextual Awareness: The utilization of environmental sensors or broad data context to drive decisions.
- Opacity & Reflexivity: The lack of internal visibility or the ability to audit decision logic.

Recommended design mitigations:
- แยก memory store ต่อ tenant/ต่อ user อย่างเข้มงวด ป้องกัน cross-session/cross-user memory contamination
- กำหนด retention/deletion policy ที่ purge residual memory หลังหมดอายุการใช้งาน ป้องกัน residual memory exploitation
- ตรวจสอบ integrity ของ context/memory ก่อนใช้งาน (checksum/signature) ป้องกัน context poisoning
- ติดตาม drift ของพฤติกรรม agent เทียบ baseline เพื่อจับ context drift exploit แต่เนิ่น ๆ

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.25 (medium): ...context resets. This can cause an agent to forget critical security constraints or operational parameters. - Cross-Session Data Leakage: Happens when attackers exploit how agents maintain state across different sessions...
- p.26 (medium): ...memory exploitation - (long-lived / unencrypted zones) "Leakage & Susceptibility" (bottom-right, purple): - Cross-session data leakage (state persists across sessions) - Cognitive resilience variance Diagonal crossed...

## Proof boundary
การประเมินนี้เป็นข้อเสนอแนะเชิงออกแบบ (Codex-curated design guidance) อ้างอิงจากรูปแบบการโจมตี (KEY RISKS) ที่มีการบันทึกไว้ใน AIVSS v0.8 เท่านั้น ไม่ใช่ control ที่ผ่านการตรวจสอบ ทดสอบ หรือยืนยันประสิทธิผลแล้ว — ทีมออกแบบต้อง implement, test, และ threat-model แต่ละมาตรการเองก่อนถือว่าความเสี่ยงลดลงจริง และห้ามใช้ผลลัพธ์นี้แทนการตรวจสอบโดย AI Security Lead / Internal Audit
--- End grounded data ---

Now write the final answer in Thai, as a security consultant would give directly to the person who asked.
```