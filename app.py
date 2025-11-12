import os
import io
import pandas as pd
import streamlit as st
from datetime import datetime
from db import (
    get_conn, get_thresholds, get_group_total, get_stock_by_group,
    get_products, adjust_stock, update_stock, reset_stock, latest_transactions
)

# -----------------------------
# ตั้งค่าแอป + ค่าคงที่
# -----------------------------
st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")
BAG_MAX = 20
ADMIN_PIN = os.getenv("BLOOD_ADMIN_KEY", "1234")

# -----------------------------
# Helper UI
# -----------------------------
def bag_color(units: int):
    if units <= 3:
        return "#ef4444"  # แดง
    if units <= 14:
        return "#f59e0b"  # เหลือง
    return "#22c55e"      # เขียว

def bag_svg(label: str, units: int):
    pct = max(0, min(100, int(round(units / BAG_MAX * 100))))
    fill_h = 160 * pct / 100
    color = bag_color(units)
    return f"""
    <svg width="160" height="200" viewBox="0 0 160 200">
      <rect x="20" y="10" rx="18" ry="18" width="120" height="180" fill="white" stroke="#7f1d1d" stroke-width="5"/>
      <rect x="25" y="{190-fill_h}" width="110" height="{fill_h}" fill="{color}" />
      <text x="80" y="105" text-anchor="middle" font-size="48" font-weight="700" fill="#111">{label}</text>
      <text x="120" y="25" text-anchor="middle" font-size="12" fill="#6b7280">{BAG_MAX} max</text>
    </svg>
    """

def status_badge(total: int, t: dict):
    if total < t["critical_min"]:
        return "🔴 ขาดแคลน"
    if total < t["low_min"]:
        return "🟠 เหลือน้อย"
    return "🟢 ปกติ"

# -----------------------------
# Session: ผู้ใช้งาน + โหมดแก้ไข
# -----------------------------
if "user" not in st.session_state:
    st.session_state["user"] = None
if "admin" not in st.session_state:
    st.session_state["admin"] = False

with st.sidebar:
    st.header("เมนู")
    # ล็อกอินชื่อผู้ใช้
    if not st.session_state["user"]:
        username = st.text_input("ชื่อผู้ใช้งาน")
        if st.button("เข้าสู่ระบบ", use_container_width=True):
            if username.strip():
                st.session_state["user"] = username.strip()
                st.success(f"เข้าสู่ระบบในชื่อ {st.session_state['user']}")
                st.experimental_rerun()
    else:
        st.info(f"👤 ผู้ใช้งาน: {st.session_state['user']}")
        if st.button("ออกจากระบบ", use_container_width=True):
            st.session_state["user"] = None
            st.session_state["admin"] = False
            st.experimental_rerun()

    # โหมดเจ้าหน้าที่ (PIN)
    st.divider()
    st.subheader("โหมดเจ้าหน้าที่")
    if not st.session_state["admin"]:
        pin = st.text_input("PIN", type="password")
        if st.button("เปิดโหมดเจ้าหน้าที่", use_container_width=True):
            if pin == ADMIN_PIN:
                st.session_state["admin"] = True
                st.success("เข้าสู่โหมดเจ้าหน้าที่แล้ว")
                st.experimental_rerun()
            else:
                st.error("PIN ไม่ถูกต้อง")
    else:
        st.success("อยู่ในโหมดเจ้าหน้าที่")
        if st.button("ปิดโหมดเจ้าหน้าที่", use_container_width=True):
            st.session_state["admin"] = False
            st.experimental_rerun()

    st.divider()
    refresh_ms = st.slider("รีเฟรชอัตโนมัติ (มิลลิวินาที)", 0, 30000, 5000, step=1000)
    if refresh_ms > 0:
        st.caption("หน้าเว็บจะรีเฟรชอัตโนมัติเพื่อให้เห็นการเปลี่ยนแปลงจากผู้ใช้อื่น")

# autorefresh (แบบง่ายโดยใช้ empty + rerun)
if refresh_ms > 0:
    st.experimental_singleton.clear()  # ป้องกัน cache เก่า
    st_autorefresh = st.empty()
    st_autorefresh.info(f"⟳ รีเฟรชทุก {refresh_ms/1000:.0f}s")
    st.experimental_rerun  # (Streamlit Cloud จะรีเฟรชเมื่อ state เปลี่ยน)

# -----------------------------
# เนื้อหาหลัก
# -----------------------------
st.title("🩸 Blood Stock Real-time Monitor")

conn = get_conn()
thresholds = get_thresholds(conn)
totals = get_group_total(conn)
groups = ["A", "B", "O", "AB"]
products = get_products(conn) or ["PRC", "Platelets", "Plasma", "Cryo"]

# แถบสถานะรวม
cols = st.columns(4)
for i, g in enumerate(groups):
    with cols[i]:
        total = totals.get(g, 0)
        st.markdown(f"### ถุงเลือดกรุ๊ป {g}")
        st.markdown(bag_svg(g, total if total <= BAG_MAX else BAG_MAX), unsafe_allow_html=True)
        st.caption(status_badge(total, thresholds.get(g, {"critical_min": 0, "low_min": 0})))
        if st.button(f"ดูรายละเอียดกรุ๊ป {g}", key=f"btn_{g}"):
            st.session_state["detail_group"] = g

st.divider()

# กล่องรายละเอียดกรุ๊ป
detail_group = st.session_state.get("detail_group", "O")
st.header(f"รายละเอียดกรุ๊ป {detail_group}")

# ตารางสต็อกแยกตาม product_type
rows = get_stock_by_group(conn, detail_group)
df_stock = pd.DataFrame([{"ประเภทผลิตภัณฑ์": r["product_type"], "หน่วย (unit)": int(r["units"])} for r in rows])
st.dataframe(df_stock, use_container_width=True)

# ความเคลื่อนไหวล่าสุด (โชว์ actor)
st.subheader("รายการความเคลื่อนไหวล่าสุด")
tx = latest_transactions(conn, blood_group=detail_group, limit=30)
df_tx = pd.DataFrame([{
    "เวลา": r["ts"],
    "กรุ๊ป": r["blood_group"],
    "ประเภท": r["product_type"],
    "การทำรายการ": r["action"],
    "จำนวน": int(r["units"]),
    "หมายเหตุ": r["note"],
    "โดย": r["actor"],
} for r in tx])
st.dataframe(df_tx, use_container_width=True)

# -----------------------------
# โหมดเจ้าหน้าที่: ทำรายการ + รีเซ็ต + อัปโหลด Excel
# -----------------------------
st.divider()
st.subheader("โหมดเจ้าหน้าที่")

if not st.session_state["admin"]:
    st.info("กรุณาเปิดโหมดเจ้าหน้าที่จากแถบด้านซ้ายเพื่อทำรายการ")
else:
    with st.form("form_adjust"):
        st.markdown("### ปรับสต็อก (นำเข้า/เบิกออก)")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            g = st.selectbox("กรุ๊ปเลือด", groups, index=groups.index(detail_group))
        with c2:
            p = st.selectbox("ประเภทผลิตภัณฑ์", products)
        with c3:
            action = st.selectbox("การทำรายการ", ["นำเข้า (+)", "เบิกออก (−)"])
        with c4:
            units = st.number_input("จำนวน", min_value=1, step=1, value=1)
        note = st.text_input("หมายเหตุ (ถ้ามี)")
        submitted = st.form_submit_button("บันทึกการทำรายการ")
        if submitted:
            sign = 1 if "นำเข้า" in action else -1
            actor = st.session_state.get("user", "unknown")
            new_units = adjust_stock(conn, g, p, sign * int(units), actor=actor, note=note)
            st.success(f"บันทึกแล้ว ({action} {units} หน่วย) คงเหลือ {new_units} หน่วย")
            st.experimental_rerun()

    st.markdown("### การจัดการคลัง")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🧹 รีเซ็ตสต็อกทั้งหมดเป็น 0"):
            reset_stock(conn)
            st.success("รีเซ็ตสต็อกทั้งหมดเรียบร้อย")
            st.experimental_rerun()

    with c2:
        uploaded = st.file_uploader("📦 อัปโหลดไฟล์ Excel เพื่ออัปเดตสต็อก (คอลัมน์: blood_group, product_type, units)", type=["xlsx"])
        if uploaded:
            try:
                df = pd.read_excel(uploaded)
                req = {"blood_group", "product_type", "units"}
                if not req.issubset(df.columns):
                    st.error(f"ไฟล์ต้องมีคอลัมน์ {req}")
                else:
                    # ทำความสะอาดข้อมูล
                    df = df[list(req)].copy()
                    df["blood_group"] = df["blood_group"].astype(str).str.upper().str.strip()
                    df["product_type"] = df["product_type"].astype(str).str.strip()
                    df["units"] = pd.to_numeric(df["units"], errors="coerce").fillna(0).astype(int)

                    # เขียนลงฐานข้อมูล (set แบบเต็มต่อรายการ)
                    actor = st.session_state.get("user", "importer")
                    updated = 0
                    for _, r in df.iterrows():
                        update_stock(get_conn(), r["blood_group"], r["product_type"], int(max(0, r["units"])), actor=actor, note="excel import")
                        updated += 1
                    st.success(f"อัปเดตสำเร็จ {updated} รายการ")
                    st.experimental_rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")
