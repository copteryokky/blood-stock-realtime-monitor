import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

DB_PATH = os.environ.get("BLOOD_DB_PATH", "blood.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with closing(get_conn()) as conn, open("schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())
        conn.commit()

def get_status_for_blood(blood_type: str):
    with closing(get_conn()) as conn:
        cur = conn.execute("""
            SELECT t.blood_type,
                   COALESCE(SUM(s.units),0) AS total,
                   t.critical_min, t.low_min
              FROM thresholds t
              LEFT JOIN stock s ON s.blood_type = t.blood_type
             WHERE t.blood_type = ?
          GROUP BY t.blood_type
        """, (blood_type,))
        row = cur.fetchone()
        if not row:
            return {"blood_type": blood_type, "total": 0, "status": "unknown"}
        total = row["total"]
        if total < row["critical_min"]:
            status = "critical"
        elif total < row["low_min"]:
            status = "low"
        else:
            status = "ok"
        return {
            "blood_type": blood_type,
            "total": total,
            "status": status,
            "critical_min": row["critical_min"],
            "low_min": row["low_min"]
        }

def get_all_status():
    return [get_status_for_blood(bt) for bt in ["O", "A", "B", "AB"]]

def get_stock_by_blood(blood_type: str):
    with closing(get_conn()) as conn:
        cur = conn.execute("""
            SELECT product_type, units
              FROM stock
             WHERE blood_type = ?
             ORDER BY product_type
        """, (blood_type,))
        return [dict(row) for row in cur.fetchall()]

def adjust_stock(blood_type: str, product_type: str, qty_change: int,
                 actor: str = "system", note: str = ""):
    with closing(get_conn()) as conn:
        conn.execute("""
        INSERT INTO stock (blood_type, product_type, units)
        VALUES (?, ?, 0)
        ON CONFLICT(blood_type, product_type) DO NOTHING
        """, (blood_type, product_type))
        conn.execute("""
        UPDATE stock SET units = MAX(0, units + ?)
         WHERE blood_type = ? AND product_type = ?
        """, (qty_change, blood_type, product_type))
        conn.execute("""
        INSERT INTO transactions (ts, actor, blood_type, product_type, qty_change, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.now(timezone.utc).isoformat(),
              actor, blood_type, product_type, qty_change, note))
        conn.commit()

def get_transactions(limit: int = 50, blood_type: str | None = None):
    with closing(get_conn()) as conn:
        if blood_type:
            cur = conn.execute("""
            SELECT * FROM transactions
             WHERE blood_type = ?
             ORDER BY id DESC LIMIT ?
            """, (blood_type, limit))
        else:
            cur = conn.execute("""
            SELECT * FROM transactions
             ORDER BY id DESC LIMIT ?
            """, (limit,))
        return [dict(r) for r in cur.fetchall()]

# ===============================
# 🩸 เพิ่มฟังก์ชันรีเซ็ตสต็อกทั้งหมด
# ===============================
def reset_all_stock(actor: str = "admin"):
    """รีเซ็ตจำนวนเลือดทั้งหมดให้เป็นศูนย์"""
    with closing(get_conn()) as conn:
        conn.execute("UPDATE stock SET units = 0")
        conn.execute("""
        INSERT INTO transactions (ts, actor, blood_type, product_type, qty_change, note)
        VALUES (?, ?, 'ALL', 'ALL', 0, 'RESET STOCK ALL TO ZERO')
        """, (datetime.now(timezone.utc).isoformat(), actor))
        conn.commit()
