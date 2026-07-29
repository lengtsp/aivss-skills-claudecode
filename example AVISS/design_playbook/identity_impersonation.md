# วิธีคิด (Reasoning) — AI Voice-Banking Authentication & Support Agent

วิธีคิด: identity_impersonation ถูกขยายด้วย identity + opacity + language — agent ตัดสินใจ 'ใครคือใคร' ผ่านเสียง/บทสนทนาล้วน (language=1) โดยไม่สามารถตรวจสอบย้อนกลับได้ ว่าทำไมถึงเชื่อว่าเป็นลูกค้าจริง (opacity=1) แล้วกระทำการในนามลูกค้าคนนั้นต่อ (identity=1) — ช่องทางนี้เสี่ยงต่อ voice deepfake และ human impersonation โดยตรง

---

# AIVSS Design Review — AI Voice-Banking Authentication & Support Agent
role: AI Security Lead | schema: rag.aivss-design-review-skills.v1

**Objective:** ทบทวนการออกแบบ 'AI Voice-Banking Authentication & Support Agent' เทียบกับ AIVSS core risks ก่อน/ระหว่างพัฒนา ในมุมมองของ AI Security Lead (proactive design-time review)
**Scope:** ยืนยันตัวตนลูกค้าด้วย voice biometric ผสมกับบทสนทนาภาษาธรรมชาติ แล้วดำเนินการเปลี่ยนแปลง บัญชี (เปลี่ยนเบอร์โทร, ปลดล็อกบัญชี) ในนามลูกค้าที่ 'ยืนยันแล้ว' โดยไม่ผ่านเจ้าหน้าที่
**Regulatory context:** BOT KYC/CDD guideline, PDPA

## Risk-by-risk design recommendations
### Agent Identity Impersonation (identity_impersonation) — high
agent แอบอ้าง/สวมรอยเป็นบุคคลหรือระบบที่ได้รับอนุญาตจริง (หรือถูกปลอมตัว โดยผู้โจมตี) จนก่อให้เกิดผลเสียหาย

Design targets for amplifying factors:
- Dynamic Identity: The ability to assume different user roles or permissions at runtime.
- Opacity & Reflexivity: The lack of internal visibility or the ability to audit decision logic.
- Natural Language Interface: The reliance on unstructured natural language for goal formulation and instruction.

Recommended design mitigations:
- ให้แต่ละ agent มี cryptographic identity เฉพาะตัว ห้ามใช้ shared service account/API key ร่วมกัน
- ตรวจสอบและยืนยัน agent card/capability declaration ก่อนเชื่อถือ ป้องกัน misleading agent card
- ควบคุม provenance/consent สำหรับการ clone เสียง/หน้า/ลายมือ (voice, face, writing style) ป้องกัน unauthorized cloning
- เสริม human-verification channel (เช่น callback ผ่านช่องทางที่ยืนยันแล้ว) เพื่อลดผลจาก deepfake-based human impersonation

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.21 (medium): <page_number>21</page_number> 5. Agent Identity Impersonation DESCRIPTION This risk class includes instances of agentic AI systems intentional...
- p.22 (medium): ...Traceability & Attribution Gaps: In the absence of DID/VC-based identity proofs, it becomes impossible to tie agent actions or outputs back to legitimate owners, undermining accountability and forensics. - Agent In The M...

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

### Agent Cascading Failures (cascading_failures) — medium
ช่องโหว่ใน agent หนึ่งตัวลุกลามส่งผลกระทบต่อระบบ/บริการอื่นที่เชื่อมต่อกัน ขยายผลกระทบเกินจุดที่ถูกโจมตีครั้งแรก

Design targets for amplifying factors:
- Execution Autonomy: The ability to execute actions without human verification.
- Multi-Agent Interactions: Coordination or dependencies on other autonomous agents.
- Behavioral Non-Determinism: The variance in output or action for identical inputs.
- Opacity & Reflexivity: The lack of internal visibility or the ability to audit decision logic.

Recommended design mitigations:
- ใส่ circuit breaker / blast-radius containment ระหว่าง agent แต่ละตัว ไม่ให้ compromise หนึ่งจุดลามทั้งเครือข่าย
- ตรวจสอบความน่าเชื่อถือของข้อมูลที่ agent อื่นรายงานก่อนนำไปตัดสินใจ (cross-validation) ป้องกัน data poisoning ที่ทำให้เกิด cascading decision ผิดพลาด
- จำกัด implicit trust ระหว่างระบบที่เชื่อมต่อกัน (SaaS-to-SaaS, cross-system) ด้วย explicit authorization ทุกจุดเชื่อมต่อ
- ตรวจสอบความสอดคล้อง (consistency check) ก่อนส่งต่อผลลัพธ์ agent หนึ่งเป็น input ให้ agent อื่น ป้องกัน hallucination propagation

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.15 (medium): ...lid instructions, interact in unexpected ways, resulting in a collectively damaging or destructive outcome. - Cross-System Exploitation: Happens when attackers use one compromised agent to gain access to multiple connect...
- p.16 (medium): ...opagates across connected systems) branches down via arrows into 3 boxes: "Trust & Pivoting" (left, pink): - Cross-system exploitation - Lateral movement via trusted channels - SaaS-to-SaaS pivoting "Amplification & Co...

### Agent Goal and Instruction Manipulation (goal_instruction) — medium
การชักจูง/บิดเบือน goal หรือ instruction ของ agent ให้เบี่ยงไปจากวัตถุประสงค์ที่ตั้งใจ เช่น prompt injection ผ่านอินพุตหรือบริบทแวดล้อม

Design targets for amplifying factors:
- Natural Language Interface: The reliance on unstructured natural language for goal formulation and instruction.
- Execution Autonomy: The ability to execute actions without human verification.
- Behavioral Non-Determinism: The variance in output or action for identical inputs.
- Contextual Awareness: The utilization of environmental sensors or broad data context to drive decisions.

Recommended design mitigations:
- กรอง input/output เพื่อจับ instruction ที่ฝังมาใน content ภายนอก (indirect injection) ก่อนถึง agent
- แยก instruction source: content ที่ดึงมาจากภายนอก (RAG, email, website) ต้องไม่ถูกตีความเป็น คำสั่งระดับเดียวกับ system/developer instruction
- บังคับ human-confirmation gate สำหรับ action ที่มีผลกระทบสูง (fund transfer, account reset) แม้ agent จะ "เชื่อ" ว่าถูกสั่งให้ทำ
- จำกัด loop/recursion depth และ resource quota ต่อ task ป้องกัน resource exhaustion via goal looping

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.41 (medium): ...e, machine-executable commands. Attackers exploit this gap by crafting deceptive inputs—a technique known as prompt injection—to manipulate the agent's understanding of its assigned goals. By embedding hidden instructio...
- p.42 (medium): ...titled "Agent Goal and Instruction Manipulation — Key Risks". Top box "Goal Subversion via Deceptive Inputs" (prompt injection and instruction chaining redirect autonomous tool use) branches down via crossing arrows into...

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

## Proof boundary
การประเมินนี้เป็นข้อเสนอแนะเชิงออกแบบ (Codex-curated design guidance) อ้างอิงจากรูปแบบการโจมตี (KEY RISKS) ที่มีการบันทึกไว้ใน AIVSS v0.8 เท่านั้น ไม่ใช่ control ที่ผ่านการตรวจสอบ ทดสอบ หรือยืนยันประสิทธิผลแล้ว — ทีมออกแบบต้อง implement, test, และ threat-model แต่ละมาตรการเองก่อนถือว่าความเสี่ยงลดลงจริง และห้ามใช้ผลลัพธ์นี้แทนการตรวจสอบโดย AI Security Lead / Internal Audit

---

## LLM synthesis prompt (ready to hand to a narrating LLM)

```
You are answering a design/security consultation question. Use ONLY the verified, deterministic AIVSS (OWASP Agentic AI Core Security Risks) findings below as your factual grounding — do not invent additional risks, mitigations, or spec citations beyond what is listed. You MAY: connect the listed mitigations to the specific regulatory/domain terms named in the scope or regulatory context below (e.g. named laws, standards, or protocols), add general security-engineering judgment on top, and organize/prioritize/phrase the final answer freely for a business/design audience evaluating a system that is being designed or changed. Preserve the proof-boundary caveat at the end of your answer, in substance if not verbatim — do not present this as a certified/validated assessment. IMPORTANT: each 'Spec grounding' page citation supports the risk/finding *description* above it, not any individual mitigation, control question, or organization-context item listed nearby — do not claim a specific mitigation is spec-sourced or cite a page number next to a mitigation unless that exact page's snippet demonstrates it.

Original question from the user:
ควรออกแบบระบบนี้อย่างไรให้ปลอดภัยจากความเสี่ยงด้าน AI agentic?

--- Grounded AIVSS data (do not exceed this factual scope) ---
# AIVSS Design Review — AI Voice-Banking Authentication & Support Agent
role: AI Security Lead | schema: rag.aivss-design-review-skills.v1

**Objective:** ทบทวนการออกแบบ 'AI Voice-Banking Authentication & Support Agent' เทียบกับ AIVSS core risks ก่อน/ระหว่างพัฒนา ในมุมมองของ AI Security Lead (proactive design-time review)
**Scope:** ยืนยันตัวตนลูกค้าด้วย voice biometric ผสมกับบทสนทนาภาษาธรรมชาติ แล้วดำเนินการเปลี่ยนแปลง บัญชี (เปลี่ยนเบอร์โทร, ปลดล็อกบัญชี) ในนามลูกค้าที่ 'ยืนยันแล้ว' โดยไม่ผ่านเจ้าหน้าที่
**Regulatory context:** BOT KYC/CDD guideline, PDPA

## Risk-by-risk design recommendations
### Agent Identity Impersonation (identity_impersonation) — high
agent แอบอ้าง/สวมรอยเป็นบุคคลหรือระบบที่ได้รับอนุญาตจริง (หรือถูกปลอมตัว โดยผู้โจมตี) จนก่อให้เกิดผลเสียหาย

Design targets for amplifying factors:
- Dynamic Identity: The ability to assume different user roles or permissions at runtime.
- Opacity & Reflexivity: The lack of internal visibility or the ability to audit decision logic.
- Natural Language Interface: The reliance on unstructured natural language for goal formulation and instruction.

Recommended design mitigations:
- ให้แต่ละ agent มี cryptographic identity เฉพาะตัว ห้ามใช้ shared service account/API key ร่วมกัน
- ตรวจสอบและยืนยัน agent card/capability declaration ก่อนเชื่อถือ ป้องกัน misleading agent card
- ควบคุม provenance/consent สำหรับการ clone เสียง/หน้า/ลายมือ (voice, face, writing style) ป้องกัน unauthorized cloning
- เสริม human-verification channel (เช่น callback ผ่านช่องทางที่ยืนยันแล้ว) เพื่อลดผลจาก deepfake-based human impersonation

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.21 (medium): <page_number>21</page_number> 5. Agent Identity Impersonation DESCRIPTION This risk class includes instances of agentic AI systems intentional...
- p.22 (medium): ...Traceability & Attribution Gaps: In the absence of DID/VC-based identity proofs, it becomes impossible to tie agent actions or outputs back to legitimate owners, undermining accountability and forensics. - Agent In The M...

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

### Agent Cascading Failures (cascading_failures) — medium
ช่องโหว่ใน agent หนึ่งตัวลุกลามส่งผลกระทบต่อระบบ/บริการอื่นที่เชื่อมต่อกัน ขยายผลกระทบเกินจุดที่ถูกโจมตีครั้งแรก

Design targets for amplifying factors:
- Execution Autonomy: The ability to execute actions without human verification.
- Multi-Agent Interactions: Coordination or dependencies on other autonomous agents.
- Behavioral Non-Determinism: The variance in output or action for identical inputs.
- Opacity & Reflexivity: The lack of internal visibility or the ability to audit decision logic.

Recommended design mitigations:
- ใส่ circuit breaker / blast-radius containment ระหว่าง agent แต่ละตัว ไม่ให้ compromise หนึ่งจุดลามทั้งเครือข่าย
- ตรวจสอบความน่าเชื่อถือของข้อมูลที่ agent อื่นรายงานก่อนนำไปตัดสินใจ (cross-validation) ป้องกัน data poisoning ที่ทำให้เกิด cascading decision ผิดพลาด
- จำกัด implicit trust ระหว่างระบบที่เชื่อมต่อกัน (SaaS-to-SaaS, cross-system) ด้วย explicit authorization ทุกจุดเชื่อมต่อ
- ตรวจสอบความสอดคล้อง (consistency check) ก่อนส่งต่อผลลัพธ์ agent หนึ่งเป็น input ให้ agent อื่น ป้องกัน hallucination propagation

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.15 (medium): ...lid instructions, interact in unexpected ways, resulting in a collectively damaging or destructive outcome. - Cross-System Exploitation: Happens when attackers use one compromised agent to gain access to multiple connect...
- p.16 (medium): ...opagates across connected systems) branches down via arrows into 3 boxes: "Trust & Pivoting" (left, pink): - Cross-system exploitation - Lateral movement via trusted channels - SaaS-to-SaaS pivoting "Amplification & Co...

### Agent Goal and Instruction Manipulation (goal_instruction) — medium
การชักจูง/บิดเบือน goal หรือ instruction ของ agent ให้เบี่ยงไปจากวัตถุประสงค์ที่ตั้งใจ เช่น prompt injection ผ่านอินพุตหรือบริบทแวดล้อม

Design targets for amplifying factors:
- Natural Language Interface: The reliance on unstructured natural language for goal formulation and instruction.
- Execution Autonomy: The ability to execute actions without human verification.
- Behavioral Non-Determinism: The variance in output or action for identical inputs.
- Contextual Awareness: The utilization of environmental sensors or broad data context to drive decisions.

Recommended design mitigations:
- กรอง input/output เพื่อจับ instruction ที่ฝังมาใน content ภายนอก (indirect injection) ก่อนถึง agent
- แยก instruction source: content ที่ดึงมาจากภายนอก (RAG, email, website) ต้องไม่ถูกตีความเป็น คำสั่งระดับเดียวกับ system/developer instruction
- บังคับ human-confirmation gate สำหรับ action ที่มีผลกระทบสูง (fund transfer, account reset) แม้ agent จะ "เชื่อ" ว่าถูกสั่งให้ทำ
- จำกัด loop/recursion depth และ resource quota ต่อ task ป้องกัน resource exhaustion via goal looping

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.41 (medium): ...e, machine-executable commands. Attackers exploit this gap by crafting deceptive inputs—a technique known as prompt injection—to manipulate the agent's understanding of its assigned goals. By embedding hidden instructio...
- p.42 (medium): ...titled "Agent Goal and Instruction Manipulation — Key Risks". Top box "Goal Subversion via Deceptive Inputs" (prompt injection and instruction chaining redirect autonomous tool use) branches down via crossing arrows into...

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

## Proof boundary
การประเมินนี้เป็นข้อเสนอแนะเชิงออกแบบ (Codex-curated design guidance) อ้างอิงจากรูปแบบการโจมตี (KEY RISKS) ที่มีการบันทึกไว้ใน AIVSS v0.8 เท่านั้น ไม่ใช่ control ที่ผ่านการตรวจสอบ ทดสอบ หรือยืนยันประสิทธิผลแล้ว — ทีมออกแบบต้อง implement, test, และ threat-model แต่ละมาตรการเองก่อนถือว่าความเสี่ยงลดลงจริง และห้ามใช้ผลลัพธ์นี้แทนการตรวจสอบโดย AI Security Lead / Internal Audit
--- End grounded data ---

Now write the final answer in Thai, as a security consultant would give directly to the person who asked.
```