import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = "logs/audit.db"

def init_db():
    Path("logs").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            verdict TEXT NOT NULL,
            intent_type TEXT,
            policy_id TEXT,
            policy_name TEXT,
            severity TEXT,
            reason TEXT,
            proposed_action TEXT,
            parameters TEXT,
            agent_id TEXT,
            agent_mode TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_decision(result, proposed_action: str, agent_id: str = "main_agent"):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO audit_log
        (timestamp, verdict, intent_type, policy_id, policy_name,
         severity, reason, proposed_action, parameters, agent_id, agent_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result.timestamp,
        result.verdict,
        result.intent,
        result.policy_id or "NONE",
        result.policy_name or "ALL_PASSED",
        result.severity or "INFO",
        result.reason,
        proposed_action,
        json.dumps(result.parameters or {}),
        agent_id,
        result.parameters.get("mode") if result.parameters else None
    ))
    conn.commit()
    conn.close()

def get_recent_logs(limit: int = 50) -> list:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
    )
    cols = [d[0] for d in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_log_stats() -> dict:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    blocked = conn.execute("SELECT COUNT(*) FROM audit_log WHERE verdict='BLOCK'").fetchone()[0]
    allowed = conn.execute("SELECT COUNT(*) FROM audit_log WHERE verdict='ALLOW'").fetchone()[0]
    conn.close()
    return {"total": total, "blocked": blocked, "allowed": allowed,
            "block_rate": round(blocked / total * 100, 1) if total > 0 else 0}