# Agent: Audit Logger

## Role
Maintain a complete, structured audit trail of all decisions.

---

## Input

{
  "intent": {...},
  "decision": "...",
  "violations": [...],
  "execution_status": "..."
}

---

## Responsibilities

- Log every step deterministically
- Ensure traceability for:
  - compliance
  - debugging
  - auditing

---

## Output Schema

{
  "audit_log": {
    "intent": {...},
    "decision": "approved | blocked",
    "violations": [...],
    "execution_status": "...",
    "timestamp": "ISO-8601",
    "system_tag": "intent-enforcement-v1"
  }
}