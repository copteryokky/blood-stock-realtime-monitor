import os, time
from datetime import datetime, date, datetime as dt
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
from db import init_db, get_all_status, get_stock_by_blood, adjust_stock, reset_stock   # ✅ เพิ่ม reset_stock

# ============ PAGE / THEME ============
st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")
st.markdown("""
<style>
.block-container{padding-top:1.0rem;}
h1,h2,h3{letter-spacing:.2px}
.badge{display:inline-flex;align-items:center;gap:.4rem;padding:.25rem .5rem;border-radius:999px;background:#f3f4f6}
.legend-dot{width:.7rem;height:.7rem;border-radius:999px;display:inline-block}
[data-testid="stSidebar"]{background:#2e343a;}
[data-testid="stSidebar"] .sidebar-title{color:#e5e7eb;font-weight:800;font-size:1.06rem;margin:6px 0 10px 4px}
[data-testid="stSidebar"] .user-card{display:flex;align-items:center;gap:.8rem;background:linear-gradient(135deg,#39424a,#2f343a);border:1px solid #475569;border-radius:14px;padding:.75rem .9rem;margin:.5rem .2rem 1rem .2rem;box-shadow:0 8px 22px rgba(0,0,0,.25)}
[data-testid="stSidebar"] .user-avatar{width:40px;height:40px;border-radius:999px;background:#ef4444;color:#fff;font-weight:900;display:flex;align-items:center;justify-content:center;letter-spacing:.5px;box-shadow:0 0 0 3px rgba(239,68,68,.25)}
[data-testid="stSidebar"] .user-meta{display:flex;flex-direction:column;line-height:1.1}
[data-testid="stSidebar"] .user-meta .label{font-size:.75rem;color:#cbd5e1}
[data-testid="stSidebar"] .user-meta .name{font-size:1rem;color:#fff;font-weight:800}
[data-testid="stSidebar"] .stButton>button{width:100%;background:#ffffff;color:#111827;border:1px solid #cbd5e1;border-radius:12px;font-weight:700;justify-content:flex-start}
[data-testid="stSidebar"] .stButton>button:hover{background:#f3f4f6}
[data-testid="stDataFrame"] table {font-size:14px;}
[data-testid="stDataFrame"] th {font-size:14px; font-weight:700; color:#111827;}
#expiry-banner{position:sticky;top:0;z-index:1000;border-radius:14px;margin:6px 0 12px 0;padding:12px 14px;border:2px solid #991b1b;background:linear-gradient(180deg,#fee2e2,#ffffff);box-shadow:0 10px 24px rgba(153,27,27,.12)}
#expiry-banner .title{font-weight:900;font-size:1.02rem;color:#7f1d1d}
#expiry-banner .chip{display:inline-flex;align-items:center;gap:.35rem;padding:.2rem .55rem;border-radius:999px;font-weight:800;background:#ef4444;color:#fff;margin-left:.5rem}
#expiry-banner .chip.warn{background:#f59e0b}
.flash{position:fixed; top:110px; right:24px; z-index:9999; color:#fff; padding:.7rem 1rem; border-radius:12px; font-weight:800; box-shadow:0 10px 24px rgba(0,0,0,.18)}
.flash.success{background:#16a34a}
.flash.info{background:#0ea5e9}
.flash.warning{background:#f59e0b}
.flash.error{background:#ef4444}
</style>
""", unsafe_allow_html=True)

# ============ CONFIG ============
BAG_MAX = 20
CRITICAL_MAX = 4
YELLOW_MAX = 15
AUTH_PASSWORD = "1234"
FLASH_SECONDS = 2.5
RENAME_TO_UI = {"Plasma": "FFP", "Platelets": "PC"}
UI_TO_DB = {"LPRC":"LPRC","PRC":"PRC","FFP":"Plasma","PC":"Platelets"}
ALL_PRODUCTS_UI = ["LPRC","PRC","FFP","Cryo","PC"]
STATUS_OPTIONS = ["ว่าง","จอง","จำหน่าย","Exp","หลุดจอง"]
STATUS_COLOR = {
    "ว่าง": "🟢 ว่าง",
    "จอง": "🟠 จอง",
    "จำหน่าย": "⚫ จำหน่าย",
    "Exp": "🔴 Exp",
    "หลุดจอง": "🔵 หลุดจอง",
}

# ============ STATE ============
def _init_state():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("page", "กรอกเลือด")
    st.session_state.setdefault("selected_bt", None)
    st.session_state.setdefault("flash", None)
    cols = ["created_at","Exp date","Unit number","Group","Blood Components","Status","สถานะ(สี)","บันทึก"]
    if "entries" not in st.session_state:
        st.session_state["entries"] = pd.DataFrame(columns=cols)
    else:
        for c in cols:
            if c not in st.session_state["entries"].columns:
                st.session_state["entries"][c] = ""
        st.session_state["entries"] = st.session_state["entries"][cols].copy()
    if "activity" not in st.session_state:
        st.session_state["activity"] = []
_init_state()

# ============ HELPERS ============
def _safe_rerun():
    try: st.rerun()
    except Exception: st.experimental_rerun()

def flash(text, typ="success"):
    st.session_state["flash"] = {"type": typ, "text": text, "until": time.time()+FLASH_SECONDS}

def show_flash():
    data = st.session_state.get("flash")
    if not data: return
    if time.time() > data.get("until", 0):
        st.session_state["flash"] = None
        return
    st.markdown(f'<div class="flash {data.get("type","success")}">{data.get("text","")}</div>', unsafe_allow_html=True)

def compute_bag(total: int, max_cap=BAG_MAX):
    t = max(0, int(total))
    if t <= CRITICAL_MAX: status, label = "red", "วิกฤตใกล้หมด"
    elif t <= YELLOW_MAX: status, label = "yellow", "เพียงพอ"
    else: status, label = "green", "ปกติ"
    pct = max(0, min(100, int(round(100 * min(t, max_cap) / max_cap))))
    return status, label, pct

def bag_color(status: str) -> str:
    return {"green":"#22c55e", "yellow":"#f59e0b", "red":"#ef4444"}[status]

# ============ INIT DB ============
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()

# ===== utils with stability =====
def totals_overview():
    ov = get_all_status()
    return {d["blood_type"]: int(d.get("total",0)) for d in ov}

# ============ SIDEBAR ============
with st.sidebar:
    st.markdown('<div class="sidebar-title">เมนู</div>', unsafe_allow_html=True)
    if st.button("หน้าหลัก", use_container_width=True):
        st.session_state["page"] = "หน้าหลัก"; _safe_rerun()
    if st.button("กรอกเลือด", use_container_width=True):
        st.session_state["page"] = "กรอกเลือด"; _safe_rerun()

# ============ HEADER ============
st.title("Blood Stock Real-time Monitor")
st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
show_flash()

# ============ MAIN ============
if st.session_state["page"] == "กรอกเลือด":
    st.subheader("กรอกเลือด")
    if st.button("รีเซ็ตข้อมูลคลังเลือดทั้งหมด 🧹", type="primary"):   # ✅ ปุ่มใหม่
        reset_stock()
        flash("รีเซ็ตคลังเลือดเรียบร้อยแล้ว ✅", "info")
        _safe_rerun()
