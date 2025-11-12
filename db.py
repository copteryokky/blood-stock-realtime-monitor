import sqlite3
import pandas as pd
import os
from datetime import datetime

DB_PATH = "blood_stock.db"

# =====================================
# 🧩 ฟังก์ชันเชื่อมต่อฐานข้อมูล
# =====================================
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# =====================================
# 🧱 ฟังก์ชันเริ่มต้นฐานข้อมูล
# =====================================
def init_db():
    """สร้างตาราง blood_stock หากยังไม่มี"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blood_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blood_type TEXT,
            amount INTEGER DEFAULT 0
        )
    """)
    conn.commit()

    # เพิ่มกลุ่มเลือดพื้นฐาน (ถ้ายังไม่มี)
    cur.execute("SELECT COUNT(*) FROM blood_stock")
    if cur.fetchone()[0] == 0:
        groups = ["A", "B", "AB", "O"]
        for g in groups:
            cur.execute("INSERT INTO blood_stock (blood_type, amount) VALUES (?, ?)", (g, 0))
        conn.commit()

    conn.close()


# =====================================
# 📊 ดึงข้อมูลทั้งหมด
# =====================================
def get_all_status():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM blood_stock", conn)
    conn.close()
    return df


# =====================================
# 🔍 ดึงสต็อกเลือดตามกรุ๊ป
# =====================================
def get_stock_by_blood(blood_type: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT amount FROM blood_stock WHERE blood_type = ?", (blood_type,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


# =====================================
# 🔄 ปรับจำนวนสต็อก (เพิ่ม/ลด)
# =====================================
def adjust_stock(blood_type: str, change: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT amount FROM blood_stock WHERE blood_type = ?", (blood_type,))
    row = cur.fetchone()

    if not row:
        cur.execute("INSERT INTO blood_stock (blood_type, amount) VALUES (?, ?)", (blood_type, max(change, 0)))
    else:
        new_amt = max(row[0] + change, 0)
        cur.execute("UPDATE blood_stock SET amount = ? WHERE blood_type = ?", (new_amt, blood_type))

    conn.commit()
    conn.close()


# =====================================
# 🧨 รีเซ็ตข้อมูลทั้งหมด (พร้อมบันทึก log)
# =====================================
def reset_stock(actor: str = None):
    """รีเซ็ตปริมาณเลือดทั้งหมดให้เป็นศูนย์ และบันทึก log ว่าใครเป็นคนรีเซ็ต"""
    conn = get_connection()
    cur = conn.cursor()

    # รีเซ็ตค่า
    cur.execute("UPDATE blood_stock SET amount = 0")
    conn.commit()

    # สร้างตาราง log ถ้ายังไม่มี
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reset_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT,
            reset_time TEXT
        )
    """)
    conn.commit()

    # เพิ่ม log
    cur.execute(
        "INSERT INTO reset_logs (actor, reset_time) VALUES (?, ?)",
        (actor or "unknown", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
