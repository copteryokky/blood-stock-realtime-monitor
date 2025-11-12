# app.py
import os, time
from datetime import datetime, date
import pandas as pd
import altair as alt
import streamlit as st
from streamlit.components.v1 import html as st_html

# ========== Auto Refresh ==========
try:
    from streamlit_autorefresh import st_autorefresh
except:
    def st_autorefresh(*args, **kwargs): return None

# ========== Database ==========
from db import init_db, get_all_status, get_stock_by_blood, adjust_stock, reset_stock, get_transactions

# ========== CONFIG ==========
st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")
BAG_MAX, CRITICAL_MAX, YELLOW_MAX = 20, 4, 15
AUTH_PASSWORD = "1234"

RENAME_TO_UI = {"Plasma": "FFP", "Platelets": "PC"}
UI_TO_DB = {"LPRC": "LPRC", "PRC": "PRC", "FFP": "Plasma", "PC": "Platelets"}
ALL_PRODUCTS_UI = ["LPRC", "PRC", "FFP", "Cryo", "PC"]

# ========== STATE ==========
def _init_state():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("page", "หน้าหลัก")
_init_state()

# ========== Helper ==========
def flash(msg, typ="success"):
    color = {"success":"#16a34a","error":"#ef4444"}.get(typ,"#0ea5e9")
    st.markdown(f"<div style='position:fixed;top:110px;right:24px;"
                f"background:{color};padding:10px 16px;border-radius:10px;"
                f"color:#fff;font-weight:700;z-index:9999'>{msg}</div>",
                unsafe_allow_html=True)

def _safe_rerun():
    try: st.rerun()
    except Exception: st.experimental_rerun()

def bag_color(u):
    if u <= CRITICAL_MAX: return "#ef4444"
    if u <= YELLOW_MAX: return "#f59e0b"
    return "#22c55e"

def bag_svg(bt, total):
    pct = min(100, int(total/BAG_MAX*100))
    fill = bag_color(total)
    return f"""
    <svg width="170" height="230" viewBox="0 0 168 206">
      <rect x="16" y="18" rx="18" ry="18" width="136" height="188" fill="#fff" stroke="#800000" stroke-width="4"/>
      <rect x="24" y="{198-160*pct/100:.1f}" width="120" height="{160*pct/100:.1f}" fill="{fill}"/>
      <text x="84" y="126" text-anchor="middle" font-size="34" font-weight="900" stroke="#111" stroke-width="4" fill="#fff">{bt}</text>
      <text x="130" y="36" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text>
    </svg>"""

# ========== Init DB ==========
if not os.path.exists("blood.db"):
    init_db()

# ========== Sidebar ==========
with st.sidebar:
    st.markdown("## เมนู")
    if not st.session_state["logged_in"]:
        u = st.text_input("ชื่อผู้ใช้")
        p = st.text_input("รหัสผ่าน", type="password", placeholder="1234")
        if st.button("เข้าสู่ระบบ", use_container_width=True):
            if p == AUTH_PASSWORD:
                st.session_state["logged_in"] = True
                st.session_state["username"] = u or "staff"
                _safe_rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        st.success(f"👤 เข้าระบบในชื่อ {st.session_state['username']}")
        if st.button("ออกจากระบบ", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            _safe_rerun()
    st.divider()
    if st.button("หน้าหลัก", use_container_width=True): st.session_state["page"]="หน้าหลัก"; _safe_rerun()
    if st.button("กรอกเลือด", use_container_width=True): st.session_state["page"]="กรอกเลือด"; _safe_rerun()

# ========== Header ==========
st.title("🩸 Blood Stock Real-time Monitor")
st.caption(f"อัปเดต: {datetime.now():%d/%m/%Y %H:%M:%S}")

# ========== หน้าหลัก ==========
if st.session_state["page"] == "หน้าหลัก":
    totals = {r["blood_group"]: r["total"] for r in get_all_status()}
    cols = st.columns(4)
    for i, bt in enumerate(["A", "B", "O", "AB"]):
        with cols[i]:
            st.markdown(f"### ถุงเลือดกรุ๊ป {bt}")
            st_html(bag_svg(bt, totals.get(bt, 0)), height=240)
    st.divider()
    st.subheader("รายการเคลื่อนไหวล่าสุด")
    tx = get_transactions(30)
    if tx:
        df = pd.DataFrame(tx)
        df.rename(columns={"ts":"เวลา","actor":"ผู้ทำรายการ","blood_type":"กรุ๊ป","product_type":"ประเภท","qty_change":"จำนวน","note":"หมายเหตุ"}, inplace=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูลการเคลื่อนไหว")

    st.divider()
    if st.session_state["logged_in"]:
        st.subheader("⚙️ เครื่องมือเจ้าหน้าที่")
        if st.button("🧹 ล้างเลือดทั้งหมด (Reset Stock)", use_container_width=True):
            reset_stock(actor=st.session_state["username"])
            flash("รีเซ็ตสต็อกทั้งหมดเรียบร้อย ✅")
            _safe_rerun()

# ========== หน้ากรอกเลือด ==========
elif st.session_state["page"] == "กรอกเลือด":
    if not st.session_state["logged_in"]:
        st.warning("ต้องเข้าสู่ระบบก่อนใช้งาน")
    else:
        st.subheader("กรอกเลือดใหม่")
        with st.form("entry_form"):
            c1, c2 = st.columns(2)
            group = c1.selectbox("Group", ["A","B","O","AB"])
            comp = c2.selectbox("Component", ["LPRC","PRC","FFP","PC"])
            status = st.selectbox("Status", ["ว่าง","จำหน่าย","Exp"])
            note = st.text_input("หมายเหตุ")
            ok = st.form_submit_button("บันทึก")
        if ok:
            try:
                qty = 1 if status == "ว่าง" else -1
                adjust_stock(group, UI_TO_DB[comp], qty, actor=st.session_state["username"], note=note)
                flash("บันทึกเรียบร้อย ✅")
                _safe_rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

        st.divider()
        st.subheader("📥 อัปโหลด Excel/CSV")
        up = st.file_uploader("เลือกไฟล์ (.xlsx, .csv)", type=["xlsx","csv"])
        if up:
            try:
                if up.name.endswith(".csv"):
                    df = pd.read_csv(up)
                else:
                    df = pd.read_excel(up)
                if {"Group","Blood Components","Status"}.issubset(df.columns):
                    for _,r in df.iterrows():
                        g = r["Group"]
                        c = r["Blood Components"]
                        s = r["Status"]
                        note = str(r.get("หมายเหตุ",""))
                        qty = 1 if s == "ว่าง" else -1 if s in ["จำหน่าย","Exp"] else 0
                        if qty != 0:
                            adjust_stock(g, UI_TO_DB[c], qty, actor=st.session_state["username"], note=note)
                    flash("อัปโหลดสำเร็จ ✅")
                    _safe_rerun()
                else:
                    st.error("ไฟล์ต้องมีคอลัมน์: Group, Blood Components, Status")
            except Exception as e:
                st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")
