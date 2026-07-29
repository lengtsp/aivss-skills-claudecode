# วิธีคิด (Reasoning) — AI Compliance Monitoring Agent Across Core Banking + Digital Channels

วิธีคิด: untraceability ถูกขยายด้วย opacity + identity + non_determinism — agent สวมบทบาทต่างกันในแต่ละระบบ (identity=1, dynamic identity), ให้คะแนนที่ไม่ deterministic เปลี่ยนไปตาม model version (non_determinism=1), และมองไม่เห็นเหตุผลภายในการให้คะแนน (opacity=1) — รวมกันแล้วตรวจสอบย้อนกลับไม่ได้ว่าทำไมธุรกรรมหนึ่งถูกปล่อยผ่านหรือถูกบล็อก

---

# AIVSS Design Review — AI Compliance Monitoring Agent Across Core Banking + Digital Channels
role: AI Security Lead | schema: rag.aivss-design-review-skills.v1

**Objective:** ทบทวนการออกแบบ 'AI Compliance Monitoring Agent Across Core Banking + Digital Channels' เทียบกับ AIVSS core risks ก่อน/ระหว่างพัฒนา ในมุมมองของ AI Security Lead (proactive design-time review)
**Scope:** สแกนธุรกรรมข้าม core banking, mobile banking, และ internet banking หาความผิดปกติ โดยสวมบทบาท (role) ต่างกันเพื่อ query แต่ละระบบ และให้คะแนนความเสี่ยงด้วย ML model ที่ผลลัพธ์เปลี่ยนไปตามเวอร์ชันโมเดล
**Regulatory context:** BOT AML/CFT monitoring guideline, AMLO, PDPA

## Risk-by-risk design recommendations
### Agent Untraceability (untraceability) — high
ไม่สามารถระบุลำดับเหตุการณ์ ตัวตน และการอนุญาตที่นำไปสู่การกระทำของ agent ได้ครบถ้วน (ช่องว่างด้าน visibility/audit trail)

Design targets for amplifying factors:
- Opacity & Reflexivity: The lack of internal visibility or the ability to audit decision logic.
- Dynamic Identity: The ability to assume different user roles or permissions at runtime.
- Behavioral Non-Determinism: The variance in output or action for identical inputs.

Recommended design mitigations:
- ใช้ centralized, tamper-evident logging พร้อม correlation ID ตลอด transaction เดียว ข้าม cloud/on-prem/SaaS
- ผูกทุก action กลับไปยัง accountable identity ต้นทาง (human หรือ agent) ป้องกัน loss of chain-of-action
- ป้องกัน log tampering/poisoning ด้วย write-once storage หรือ external SIEM ที่ agent เข้าถึงไม่ได้
- ตรวจสอบ integrity ของ explainability artifact (SHAP/LIME) แยกจาก inference pipeline หลัก

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.38 (medium): ...users or systems that trigger them. This creates a convoluted and transient trail of activity where a single logical operation can span multiple identities and system logs, if logs are even captured consistently. The no...
- p.39 (medium): ...ins) - Distributed audit events with no correlation IDs - Broken chain of custody across cloud/on-prem/SaaS "Log Tampering or Absence" (top-right, green): - Log tampering or absence (erase or avoid traces) - Agents inte...

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

## Proof boundary
การประเมินนี้เป็นข้อเสนอแนะเชิงออกแบบ (Codex-curated design guidance) อ้างอิงจากรูปแบบการโจมตี (KEY RISKS) ที่มีการบันทึกไว้ใน AIVSS v0.8 เท่านั้น ไม่ใช่ control ที่ผ่านการตรวจสอบ ทดสอบ หรือยืนยันประสิทธิผลแล้ว — ทีมออกแบบต้อง implement, test, และ threat-model แต่ละมาตรการเองก่อนถือว่าความเสี่ยงลดลงจริง และห้ามใช้ผลลัพธ์นี้แทนการตรวจสอบโดย AI Security Lead / Internal Audit

---

## LLM synthesis prompt (ready to hand to a narrating LLM)

```
You are answering a design/security consultation question. Use ONLY the verified, deterministic AIVSS (OWASP Agentic AI Core Security Risks) findings below as your factual grounding — do not invent additional risks, mitigations, or spec citations beyond what is listed. You MAY: connect the listed mitigations to the specific regulatory/domain terms named in the scope or regulatory context below (e.g. named laws, standards, or protocols), add general security-engineering judgment on top, and organize/prioritize/phrase the final answer freely for a business/design audience evaluating a system that is being designed or changed. Preserve the proof-boundary caveat at the end of your answer, in substance if not verbatim — do not present this as a certified/validated assessment. IMPORTANT: each 'Spec grounding' page citation supports the risk/finding *description* above it, not any individual mitigation, control question, or organization-context item listed nearby — do not claim a specific mitigation is spec-sourced or cite a page number next to a mitigation unless that exact page's snippet demonstrates it.

Original question from the user:
ควรออกแบบระบบนี้อย่างไรให้ปลอดภัยจากความเสี่ยงด้าน AI agentic?

--- Grounded AIVSS data (do not exceed this factual scope) ---
# AIVSS Design Review — AI Compliance Monitoring Agent Across Core Banking + Digital Channels
role: AI Security Lead | schema: rag.aivss-design-review-skills.v1

**Objective:** ทบทวนการออกแบบ 'AI Compliance Monitoring Agent Across Core Banking + Digital Channels' เทียบกับ AIVSS core risks ก่อน/ระหว่างพัฒนา ในมุมมองของ AI Security Lead (proactive design-time review)
**Scope:** สแกนธุรกรรมข้าม core banking, mobile banking, และ internet banking หาความผิดปกติ โดยสวมบทบาท (role) ต่างกันเพื่อ query แต่ละระบบ และให้คะแนนความเสี่ยงด้วย ML model ที่ผลลัพธ์เปลี่ยนไปตามเวอร์ชันโมเดล
**Regulatory context:** BOT AML/CFT monitoring guideline, AMLO, PDPA

## Risk-by-risk design recommendations
### Agent Untraceability (untraceability) — high
ไม่สามารถระบุลำดับเหตุการณ์ ตัวตน และการอนุญาตที่นำไปสู่การกระทำของ agent ได้ครบถ้วน (ช่องว่างด้าน visibility/audit trail)

Design targets for amplifying factors:
- Opacity & Reflexivity: The lack of internal visibility or the ability to audit decision logic.
- Dynamic Identity: The ability to assume different user roles or permissions at runtime.
- Behavioral Non-Determinism: The variance in output or action for identical inputs.

Recommended design mitigations:
- ใช้ centralized, tamper-evident logging พร้อม correlation ID ตลอด transaction เดียว ข้าม cloud/on-prem/SaaS
- ผูกทุก action กลับไปยัง accountable identity ต้นทาง (human หรือ agent) ป้องกัน loss of chain-of-action
- ป้องกัน log tampering/poisoning ด้วย write-once storage หรือ external SIEM ที่ agent เข้าถึงไม่ได้
- ตรวจสอบ integrity ของ explainability artifact (SHAP/LIME) แยกจาก inference pipeline หลัก

Spec grounding for this risk's description above (AIVSS v0.8, page + snippet) — describes the attack pattern, NOT a per-mitigation citation; do not attribute an individual mitigation to a specific page unless the snippet itself demonstrates it:
- p.38 (medium): ...users or systems that trigger them. This creates a convoluted and transient trail of activity where a single logical operation can span multiple identities and system logs, if logs are even captured consistently. The no...
- p.39 (medium): ...ins) - Distributed audit events with no correlation IDs - Broken chain of custody across cloud/on-prem/SaaS "Log Tampering or Absence" (top-right, green): - Log tampering or absence (erase or avoid traces) - Agents inte...

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

## Proof boundary
การประเมินนี้เป็นข้อเสนอแนะเชิงออกแบบ (Codex-curated design guidance) อ้างอิงจากรูปแบบการโจมตี (KEY RISKS) ที่มีการบันทึกไว้ใน AIVSS v0.8 เท่านั้น ไม่ใช่ control ที่ผ่านการตรวจสอบ ทดสอบ หรือยืนยันประสิทธิผลแล้ว — ทีมออกแบบต้อง implement, test, และ threat-model แต่ละมาตรการเองก่อนถือว่าความเสี่ยงลดลงจริง และห้ามใช้ผลลัพธ์นี้แทนการตรวจสอบโดย AI Security Lead / Internal Audit
--- End grounded data ---

Now write the final answer in Thai, as a security consultant would give directly to the person who asked.
```