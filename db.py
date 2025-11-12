# app.py
import os, time
from datetime import datetime, date
import pandas as pd
import altair as alt
import streamlit as st
from streamlit.components.v1 import html as st_html

# ===== optional autorefresh =====
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    def st_autorefresh(*args, **kwargs): return None

# ===== DB funcs =====
from db import init_db, get_all_status, get_stock_by_blood, adjust_stock, reset_stock

# ============ PAGE / THEME ============
st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")
st.markdown("""
<style>
.block-container{padding-top:1.0rem;}
h1,h2,h3{letter-spacing:.2px}

/* badge legend */
.badge{display:inline-flex;align-items:center;gap:.4rem;padding:.25rem .5rem;border-radius:999px;background:#f3f4f6}
.legend-dot{width:.7rem;height:.7rem;border-radius:999px;display:inline-block}

/* Sidebar */
[data-testid="stSidebar"]{background:#2e343a;}
[data-testid="stSidebar"] .sidebar-title{color:#e5e7eb;font-weight:800;font-size:1.06rem;margin:6px 0 10px 4px}
[data-testid="stSidebar"] .stButton>button{width:100%;background:#ffffff;color:#111827;border:1px solid #cbd5e1;border-radius:12px;font-weight:700}
[data-testid="stSidebar"] .stButton>button:hover{background:#f3f4f6}

/* DataFrame */
[data-testid="stDataFrame"] table {font-size:14px;}
[data-testid="stDataFrame"] th {font-size:14px; font-weight:700; color:#111827;}

/* Flash */
.flash{position:fixed; top:110px; right:24px; z-index:9999; color:#fff; padding:.7rem 1rem; border-radius:12px; font-weight:800; box-shadow:0 10px 24px rgba(0,0,0,.18)}
.flash.success{background:#16a34a}
.flash.error{background:#ef4444}
</style>
""", unsafe_allow_html=True)

# ============ CONFIG ============
BAG_MAX       = 20
CRITICAL_MAX  = 4
YELLOW_MAX    = 15
AUTH_PASSWORD = "1234"
FLASH_SECONDS = 2.5

# mapping / order
RENAME_TO_UI    = {"Plasma": "FFP", "Platelets": "PC"}
UI_TO_DB        = {"LPRC":"LPRC","PRC":"PRC","FFP":"Plasma","PC":"Platelets"}
ALL_PRODUCTS_UI = ["LPRC","PRC","FFP","Cryo","PC"]

# ============ STATE ============
def _init_state():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("page", "หน้าหลัก")
_init_state()

# ============ HELPERS ============
def flash(text, typ="success"):
    color = {"success":"#16a34a","error":"#ef4444"}.get(typ,"#0ea5e9")
    st.markdown(f"<div class='flash {typ}'>{text}</div>", unsafe_allow_html=True)

def _safe_rerun():
    try: st.rerun()
    except Exception: st.experimental_rerun()

def bag_color(u):
    if u <= CRITICAL_MAX: return "#ef4444"
    if u <= YELLOW_MAX: return "#f59e0b"
    return "#22c55e"

def bag_svg(bt, total):
    pct = min(100, int(total / BAG_MAX * 100))
    fill = bag_color(total)
    return f"""
    <svg width="170" height="230" viewBox="0 0 168 206">
      <rect x="16" y="18" rx="18" ry="18" width="136" height="188" fill="#fff" stroke="#800000" stroke-width="4"/>
      <rect x="24" y="{198-160*pct/100:.1f}" width="120" height="{160*pct/100:.1f}" fill="{fill}"/>
      <text x="84" y="126" text-anchor="middle" font-size="34" font-weight="900" stroke="#111" stroke-width="4" fill="#fff">{bt}</text>
      <text x="130" y="36" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text>
    </svg>
    """

# ============ INIT DB (Reset Every Start) ============
db_path = os.environ.get("BLOOD_DB_PATH", "blood.db")
if not os.path.exists(db_path):
    init_db()
else:
    reset_stock(actor="auto")

# ============ SIDEBAR ============
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

# ============ HEADER ============
st.title("🩸 Blood Stock Real-time Monitor")
st.caption(f"อัปเดต: {datetime.now():%d/%m/%Y %H:%M:%S}")

# ============ PAGE: หน้าหลัก ============
if st.session_state["page"] == "หน้าหลัก":
    totals = {r["blood_group"]: r["total"] for r in get_all_status()}
    cols = st.columns(4)
    for i, bt in enumerate(["A", "B", "O", "AB"]):
        with cols[i]:
            st.markdown(f"### ถุงเลือดกรุ๊ป {bt}")
            st_html(bag_svg(bt, totals.get(bt, 0)), height=240)
    st.divider()
    st.subheader("รายละเอียดกรุ๊ป O")
    rows = get_stock_by_blood("O")
    dist = {k: 0 for k in ALL_PRODUCTS_UI}
    for r in rows:
        ui = RENAME_TO_UI.get(r["product_type"], r["product_type"])
        if ui in dist:
            dist[ui] += int(r["units"])
    df = pd.DataFrame([{"Product": k, "Units": v} for k, v in dist.items()])
    chart = alt.Chart(df).mark_bar().encode(x="Product", y="Units", tooltip=["Product", "Units"])
    st.altair_chart(chart, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)

# ============ PAGE: กรอกเลือด ============
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
