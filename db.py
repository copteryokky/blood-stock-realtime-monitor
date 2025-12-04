# db.py
import os
import sqlite3
from datetime import datetime

DB_PATH = os.environ.get("BLOOD_DB_PATH", "blood.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """สร้างตารางพื้นฐาน ถ้ายังไม่มี"""
    conn = _get_conn()
    cur = conn.cursor()

    # ตารางสต็อกเลือด (เก็บเป็นยอดรวมตามกรุ๊ป / product_type)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blood_type TEXT NOT NULL,
            product_type TEXT NOT NULL,
            units INTEGER NOT NULL DEFAULT 0,
            UNIQUE(blood_type, product_type)
        )
        """
    )

    # ตาราง log การเปลี่ยนแปลง (ไม่จำเป็นต่อหน้าจอ แต่เก็บไว้เป็น history)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            actor TEXT,
            blood_type TEXT,
            product_type TEXT,
            delta INTEGER,
            note TEXT
        )
        """
    )

    conn.commit()
    conn.close()


# ------------ Query helper ------------

def get_all_status():
    """
    คืนค่า list ของ dict:
    { "blood_type": "A", "total": 10 }
    รวมทุก product_type ต่อกรุ๊ป
    """
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT blood_type, COALESCE(SUM(units),0) AS total
        FROM stock
        GROUP BY blood_type
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_stock_by_blood(blood_type: str):
    """
    คืน list ของ dict:
    { "product_type": "LPRC", "units": 5 }
    """
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT product_type, units
        FROM stock
        WHERE blood_type = ?
        """,
        (blood_type,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def adjust_stock(blood_type: str, product_type: str, qty: int, actor: str = "", note: str = ""):
    """
    ปรับสต็อก + เพิ่ม log
    qty > 0 = รับเข้า, qty < 0 = จ่ายออก
    """
    if not qty:
        return

    conn = _get_conn()
    cur = conn.cursor()

    # ถ้าไม่มี row ให้สร้างก่อน
    cur.execute(
        """
        INSERT OR IGNORE INTO stock(blood_type, product_type, units)
        VALUES (?, ?, 0)
        """,
        (blood_type, product_type),
    )

    # อัปเดตจำนวน
    cur.execute(
        """
        UPDATE stock
        SET units = MAX(units + ?, 0)
        WHERE blood_type = ? AND product_type = ?
        """,
        (qty, blood_type, product_type),
    )

    # บันทึก log
    cur.execute(
        """
        INSERT INTO stock_log(ts, actor, blood_type, product_type, delta, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            actor or "",
            blood_type,
            product_type,
            int(qty),
            note or "",
        ),
    )

    conn.commit()
    conn.close()


def reset_all_stock(actor: str = "admin"):
    """รีเซ็ต stock ทุกตัวเป็นศูนย์ + log"""
    conn = _get_conn()
    cur = conn.cursor()

    # log ก่อนรีเซ็ต (เก็บค่าเดิม)
    cur.execute("SELECT blood_type, product_type, units FROM stock")
    rows = cur.fetchall()
    for r in rows:
        if r["units"]:
            cur.execute(
                """
                INSERT INTO stock_log(ts, actor, blood_type, product_type, delta, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    actor,
                    r["blood_type"],
                    r["product_type"],
                    -int(r["units"]),
                    "reset_all_stock",
                ),
            )

    # set = 0
    cur.execute("UPDATE stock SET units = 0")
    conn.commit()
    conn.close()
