import os
import sqlite3
from contextlib import closing

DB_PATH = os.getenv("BLOOD_DB_PATH", "blood.db")

# ========= Database Initialization =========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ตารางหลัก
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blood_group TEXT,
        product_type TEXT,
        units INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT DEFAULT (datetime('now','localtime')),
        blood_group TEXT,
        product_type TEXT,
        action TEXT,
        units INTEGER,
        note TEXT,
        actor TEXT
    );

    CREATE TABLE IF NOT EXISTS thresholds (
        blood_group TEXT PRIMARY KEY,
        critical_min INTEGER,
        low_min INTEGER
    );
    """)

    # ค่าเริ่มต้น thresholds
    default_thresholds = {
        "O": (30, 60),
        "A": (25, 50),
        "B": (25, 50),
        "AB": (15, 30),
    }
    for bg, (crit, low) in default_thresholds.items():
        cur.execute("""
            INSERT OR IGNORE INTO thresholds (blood_group, critical_min, low_min)
            VALUES (?, ?, ?)
        """, (bg, crit, low))

    conn.commit()
    conn.close()

# ========= Connection Helper =========
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ========= Queries =========
def get_all_status():
    conn = get_conn()
    rows = conn.execute("""
        SELECT blood_group AS blood_type, SUM(units) AS total
        FROM stock
        GROUP BY blood_group
    """).fetchall()
    conn.close()
    return rows

def get_stock_by_blood(blood_group):
    conn = get_conn()
    rows = conn.execute("""
        SELECT product_type, units
        FROM stock
        WHERE blood_group = ?
    """, (blood_group,)).fetchall()
    conn.close()
    return rows

# ========= Updates =========
def adjust_stock(blood_group, product_type, delta_units, actor="system", note=""):
    """เพิ่มหรือลดจำนวนหน่วย (delta_units อาจเป็น + หรือ -)"""
    conn = get_conn()
    with closing(conn.cursor()) as cur:
        cur.execute("""
            INSERT INTO stock (blood_group, product_type, units)
            SELECT ?, ?, 0
            WHERE NOT EXISTS (
                SELECT 1 FROM stock WHERE blood_group=? AND product_type=?
            )
        """, (blood_group, product_type, blood_group, product_type))
        cur.execute("""
            SELECT units FROM stock WHERE blood_group=? AND product_type=?
        """, (blood_group, product_type))
        cur_units = cur.fetchone()
        current = int(cur_units["units"] if cur_units else 0)
        new_units = max(0, current + int(delta_units))
        cur.execute("""
            UPDATE stock SET units=? WHERE blood_group=? AND product_type=?
        """, (new_units, blood_group, product_type))
        # Log การทำรายการ
        action = "import" if delta_units >= 0 else "export"
        cur.execute("""
            INSERT INTO transactions (ts, blood_group, product_type, action, units, note, actor)
            VALUES (datetime('now','localtime'), ?, ?, ?, ?, ?, ?)
        """, (blood_group, product_type, action, abs(delta_units), note, actor))
    conn.commit()
    conn.close()

def reset_stock():
    """ตั้งค่าทุก stock เป็น 0"""
    conn = get_conn()
    with closing(conn.cursor()) as cur:
        cur.execute("UPDATE stock SET units = 0")
        cur.execute("""
            INSERT INTO transactions (ts, blood_group, product_type, action, units, note, actor)
            VALUES (datetime('now','localtime'), 'ALL', 'ALL', 'reset', 0, 'reset all', 'admin')
        """)
    conn.commit()
    conn.close()
