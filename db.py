# db.py
import os
import sqlite3
from contextlib import closing

DB_PATH = os.getenv("BLOOD_DB_PATH", "blood.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """สร้างตารางตาม schema.sql และ seed ค่าเริ่มต้น"""
    if not os.path.exists("schema.sql"):
        raise FileNotFoundError("ไม่พบไฟล์ schema.sql")
    with open("schema.sql", "r", encoding="utf-8") as f:
        schema = f.read()
    with closing(get_conn()) as conn:
        conn.executescript(schema)
        conn.commit()

# =============================
# ดึงข้อมูลสรุป / สถานะ
# =============================
def get_all_status():
    """ดึงยอดรวมเลือดทุกกรุ๊ป"""
    with closing(get_conn()) as conn:
        cur = conn.execute("""
            SELECT blood_type AS blood_group, SUM(units) AS total
            FROM stock
            GROUP BY blood_type
        """)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def get_stock_by_blood(blood_group):
    """ดึงข้อมูลตามกรุ๊ปเลือด"""
    with closing(get_conn()) as conn:
        cur = conn.execute("""
            SELECT product_type, units
            FROM stock
            WHERE blood_type = ?
            ORDER BY product_type
        """, (blood_group,))
        return [dict(r) for r in cur.fetchall()]

def get_transactions(limit=50, blood_type=None):
    """ดึง log รายการเคลื่อนไหว"""
    with closing(get_conn()) as conn:
        if blood_type:
            cur = conn.execute("""
                SELECT ts, actor, blood_type, product_type, qty_change, note
                FROM transactions
                WHERE blood_type = ?
                ORDER BY id DESC
                LIMIT ?
            """, (blood_type, limit))
        else:
            cur = conn.execute("""
                SELECT ts, actor, blood_type, product_type, qty_change, note
                FROM transactions
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
        return [dict(r) for r in cur.fetchall()]

# =============================
# ปรับปรุง / อัปเดตสต็อก
# =============================
def _ensure_stock_row(conn, blood_type, product_type):
    conn.execute("""
        INSERT INTO stock (blood_type, product_type, units)
        SELECT ?, ?, 0
        WHERE NOT EXISTS (
            SELECT 1 FROM stock WHERE blood_type=? AND product_type=?
        )
    """, (blood_type, product_type, blood_type, product_type))

def adjust_stock(blood_type, product_type, qty_change, actor="system", note=""):
    """เพิ่มหรือลดสต็อก และบันทึกลงตาราง transactions"""
    with closing(get_conn()) as conn:
        _ensure_stock_row(conn, blood_type, product_type)
        cur = conn.execute("""
            SELECT units FROM stock WHERE blood_type=? AND product_type=?
        """, (blood_type, product_type))
        old_units = int((cur.fetchone() or {"units": 0})["units"])
        new_units = max(0, old_units + int(qty_change))
        conn.execute("""
            UPDATE stock SET units=? WHERE blood_type=? AND product_type=?
        """, (new_units, blood_type, product_type))
        conn.execute("""
            INSERT INTO transactions (ts, actor, blood_type, product_type, qty_change, note)
            VALUES (datetime('now','localtime'), ?, ?, ?, ?, ?)
        """, (actor, blood_type, product_type, qty_change, note))
        conn.commit()
        return new_units

def reset_stock(actor="admin"):
    """รีเซ็ตสต็อกทั้งหมดให้เป็น 0"""
    with closing(get_conn()) as conn:
        conn.execute("UPDATE stock SET units=0")
        conn.execute("""
            INSERT INTO transactions (ts, actor, blood_type, product_type, qty_change, note)
            VALUES (datetime('now','localtime'), ?, 'ALL', 'ALL', 0, 'reset all stock')
        """, (actor,))
        conn.commit()
