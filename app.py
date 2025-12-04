# app.py

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
    def st_autorefresh(*args, **kwargs):
        return None

# ===== DB funcs =====
from db import init_db, get_all_status, get_stock_by_blood, adjust_stock, reset_all_stock

# --------------------------------
# CONFIG & CONSTANTS
# --------------------------------
st.set_page_config(
    page_title="Blood Stock Real-time Monitor",
    page_icon="🩸",
    layout="wide",
)

# ---------- GLOBAL STYLE ----------
st.markdown(
    """
<style>
/* พื้นหลัง + layout ทั่วไป */
html, body, [data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top left, #ffe4e6 0, #ffffff 40%, #f9fafb 100%) !important;
}
.block-container {
    padding-top: 1.2rem;
    max-width: 1200px;
}

/* heading */
h1, h2, h3 {
    letter-spacing: .2px;
    font-weight: 800;
}

/* badge legend */
.badge {
    display: inline-flex;
    align-items: center;
    gap: .4rem;
    padding: .25rem .5rem;
    border-radius: 999px;
    background: #f3f4f6;
}
.legend-dot {
    width: .7rem;
    height: .7rem;
    border-radius: 999px;
    display: inline-block;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #020617;
    border-right: 1px solid #0f172a;
}
[data-testid="stSidebar"] .sidebar-title{
    color:#e5e7eb;
    font-weight:800;
    font-size:1.06rem;
    margin:6px 0 10px 4px;
}
[data-testid="stSidebar"] .user-card{
    display:flex;
    align-items:center;
    gap:.8rem;
    background:radial-gradient(circle at top left,#f97373,#b91c1c);
    border-radius:18px;
    padding:.85rem 1rem;
    margin:.5rem .2rem 1.3rem .2rem;
    box-shadow:0 18px 45px rgba(0,0,0,.55);
}
[data-testid="stSidebar"] .user-avatar{
    width:40px;height:40px;border-radius:999px;
    background:#fee2e2;color:#b91c1c;font-weight:900;
    display:flex;align-items:center;justify-content:center;
    letter-spacing:.5px;
}
[data-testid="stSidebar"] .user-meta{
    display:flex;flex-direction:column;line-height:1.15;
}
[data-testid="stSidebar"] .user-meta .label{
    font-size:.75rem;color:#fecaca;
}
[data-testid="stSidebar"] .user-meta .name{
    font-size:1rem;color:#ffffff;font-weight:800;
}
[data-testid="stSidebar"] .stButton>button{
    width:100%;
    background:#0f172a;
    color:#e5e7eb;
    border-radius:999px;
    border:1px solid #1f2937;
    font-weight:600;
    padding:.5rem .9rem;
}
[data-testid="stSidebar"] .stButton>button:hover{
    background:#111827;
    border-color:#f97373;
    color:#fef2f2;
}
[data-testid="stSidebar"] .stButton>button:focus-visible{
    outline:2px solid #f97373;
}

/* DataFrame */
[data-testid="stDataFrame"] table {font-size:14px;}
[data-testid="stDataFrame"] th {font-size:14px;font-weight:700;color:#111827;}

/* Sticky minimal banner */
#expiry-banner{
    position:sticky;top:0;z-index:1000;
    border-radius:14px;margin:6px 0 12px 0;
    padding:12px 14px;
    border:2px solid #991b1b;
    background:linear-gradient(180deg,#fee2e2,#ffffff);
    box-shadow:0 10px 24px rgba(153,27,27,.12);
}
#expiry-banner .title{
    font-weight:900;font-size:1.02rem;color:#7f1d1d;
}
#expiry-banner .chip{
    display:inline-flex;align-items:center;gap:.35rem;
    padding:.2rem .55rem;border-radius:999px;
    font-weight:800;background:#ef4444;color:#fff;
    margin-left:.5rem;font-size:.8rem;
}
#expiry-banner .chip.warn{background:#f97316;}

/* Flash */
.flash{
    position:fixed; top:110px; right:24px;
    z-index:9999; color:#fff;
    padding:.7rem 1rem;
    border-radius:12px;
    font-weight:800;
    box-shadow:0 10px 24px rgba(0,0,0,.18);
    backdrop-filter:blur(14px);
}
.flash.success{background:linear-gradient(135deg,#16a34a,#22c55e);}
.flash.info{background:linear-gradient(135deg,#0ea5e9,#22d3ee);}
.flash.warning{background:linear-gradient(135deg,#f97316,#facc15);}
.flash.error{background:linear-gradient(135deg,#ef4444,#b91c1c);}

/* ---------- LANDING PAGE ---------- */
.landing-wrap{
    margin-top:0.4rem;
    margin-bottom:1.6rem;
}
.landing-hero{
    background:radial-gradient(circle at top left,#ffe4e6 0,#fef2f2 40%,#ffffff 100%);
    border-radius:30px;
    padding:1.9rem 2.4rem;
    box-shadow:0 20px 60px rgba(248,113,113,.25);
    border:1px solid #fecaca;
}
.landing-hero-top{
    display:flex;
    justify-content:space-between;
    font-size:.8rem;
    color:#9ca3af;
    margin-bottom:.2rem;
}
.landing-hero-pill{
    display:inline-flex;
    align-items:center;
    gap:.45rem;
    padding:.25rem .6rem;
    border-radius:999px;
    background:#fee2e2;
    color:#b91c1c;
    font-weight:600;
    font-size:.78rem;
}
.landing-hero-pill span.dot{
    width:.38rem;height:.38rem;border-radius:999px;
    background:#ef4444;
}
.landing-hero-grid{
    display:grid;
    grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);
    gap:2.2rem;
    align-items:center;
}
.landing-hero-title{
    font-size:1.5rem;
    font-weight:800;
    margin-bottom:.15rem;
}
.landing-hero-sub{
    font-size:.95rem;
    color:#4b5563;
    margin-bottom:.8rem;
}
.landing-hero-list{
    font-size:.9rem;
    color:#374151;
    margin-bottom:1.1rem;
}
.landing-hero-list li{
    margin-bottom:.11rem;
}
.landing-hero-list li::marker{
    color:#ef4444;
}
.landing-hero-buttons{
    display:flex;
    flex-wrap:wrap;
    gap:.7rem;
}
.landing-btn-primary,
.landing-btn-ghost{
    padding:.55rem 1.35rem;
    border-radius:999px;
    font-size:.9rem;
    font-weight:700;
    border:none;
    cursor:default;
}
.landing-btn-primary{
    background:#ef4444;
    color:#ffffff;
    box-shadow:0 16px 40px rgba(248,113,113,.7);
}
.landing-btn-ghost{
    background:#ffffff;
    color:#111827;
    border:1px solid #e5e7eb;
}
.landing-hero-illu{
    position:relative;
    height:200px;
    display:flex;
    align-items:center;
    justify-content:center;
}
.landing-hero-illu-main{
    width:180px;height:140px;border-radius:26px;
    background:linear-gradient(135deg,#fee2e2,#fecaca);
    box-shadow:0 26px 70px rgba(239,68,68,.75);
    display:flex;
    align-items:center;
    justify-content:center;
    position:relative;
}
.landing-hero-illu-main::before{
    content:"";
    position:absolute;
    inset:18px 18px;
    border-radius:18px;
    border:2px solid rgba(248,250,252,.85);
}
.landing-hero-illu-chart{
    width:70%;
    height:40%;
    border-radius:14px;
    background:rgba(248,250,252,.96);
    box-shadow:0 10px 25px rgba(148,27,30,.45) inset;
    position:relative;
    overflow:hidden;
}
.landing-hero-illu-chart::before{
    content:"";
    position:absolute;
    left:10%;
    right:10%;
    top:55%;
    height:3px;
    background:linear-gradient(90deg,#fecaca,#ef4444,#b91c1c);
}
.landing-hero-illu-chart::after{
    content:"";
    position:absolute;
    width:70%;
    height:55%;
    left:16%;
    top:20%;
    background:conic-gradient(from 210deg,#f97373,#fecaca,#fee2e2,#fee2e2);
    border-radius:999px;
    opacity:.95;
}
.landing-hero-bag{
    position:absolute;
    bottom:-12px;
    right:-22px;
    width:66px;height:86px;
    border-radius:18px;
    background:#ef4444;
    box-shadow:0 16px 46px rgba(127,29,29,.85);
    border:3px solid #fee2e2;
}
.landing-hero-bag::before{
    content:"";
    position:absolute;
    inset:10px 10px 22px 10px;
    border-radius:14px;
    background:linear-gradient(180deg,#fecaca,#ef4444);
}
.landing-hero-bag::after{
    content:"";
    position:absolute;
    width:32px;height:10px;
    left:50%;transform:translateX(-50%);
    top:-12px;border-radius:999px;
    background:#fee2e2;
    box-shadow:0 3px 6px rgba(15,23,42,.15);
}

/* landing cards */
.landing-cards{
    margin-top:1.4rem;
    display:grid;
    grid-template-columns:minmax(0,1fr) minmax(0,1fr);
    gap:1.1rem;
}
.landing-card{
    background:#ffffff;
    border-radius:22px;
    padding:1.2rem 1.5rem 1.35rem;
    box-shadow:0 14px 38px rgba(148,163,184,.22);
    border:1px solid #e5e7eb;
    font-size:.9rem;
}
.landing-card h3{
    font-size:1.02rem;
    margin-bottom:.45rem;
}
.landing-card small{
    color:#6b7280;
    font-size:.8rem;
}
.landing-blood-dot{
    display:inline-block;
    width:.5rem;height:.5rem;border-radius:999px;
    margin-right:.35rem;
}
.landing-blood-dot.green{background:#22c55e;}
.landing-blood-dot.orange{background:#fb923c;}
.landing-blood-dot.red{background:#ef4444;}
.landing-card ul{
    list-style:none;
    padding-left:0;
    margin-top:.6rem;
}
.landing-card ul li{
    display:flex;
    align-items:flex-start;
    gap:.45rem;
    margin-bottom:.25rem;
}
.landing-card ul li span.label{
    font-weight:700;
}
.landing-alert-label{
    font-weight:700;
    min-width:62px;
}
.landing-alert-label.critical{color:#dc2626;}
.landing-alert-label.warning{color:#f97316;}

/* การจัดการระบบ card (หน้า landing) */
.landing-manage{
    margin-top:1.6rem;
    background:#eff6ff;
    border-radius:20px;
    padding:1rem 1.4rem;
    border:1px dashed #93c5fd;
    font-size:.88rem;
}

/* ---------- LOGIN PAGE ---------- */
.login-bg{
    min-height:calc(100vh - 3rem);
    display:flex;
    align-items:center;
    justify-content:center;
}
.login-bg::before{
    content:"";
    position:fixed;
    inset:0;
    background:
      radial-gradient(circle at top,#fecaca 0,#0f172a 45%);
    opacity:.96;
    z-index:-1;
}
.login-bg [data-testid="stForm"]{
    background:#f9fafb;
    border-radius:28px;
    padding:2.4rem 2.7rem 2.2rem;
    box-shadow:0 28px 80px rgba(15,23,42,.88);
    max-width:420px;
    width:420px;
    border:1px solid rgba(148,163,184,.5);
}
.login-header-icon{
    width:40px;height:40px;border-radius:14px;
    display:flex;align-items:center;justify-content:center;
    background:#ef4444;color:#fef2f2;
    font-size:1.2rem;margin-bottom:.5rem;
}
.login-title{
    font-size:1.3rem;font-weight:800;margin-bottom:.15rem;
}
.login-sub{
    font-size:.86rem;color:#cbd5f5;margin-bottom:1.1rem;
}
.login-bg label{
    font-size:.88rem;font-weight:600;color:#0f172a;
}
.login-bg .stTextInput>div>div>input{
    border-radius:999px !important;
    border:1px solid #cbd5e1 !important;
    background:#ffffff !important;
    padding:.5rem .9rem !important;
}
.login-bg .stTextInput>div>div>input:focus{
    border-color:#ef4444 !important;
    box-shadow:0 0 0 1.5px rgba(248,113,113,.6) !important;
}
.login-hint{
    font-size:.78rem;
    color:#6b7280;
    margin-top:.35rem;
    margin-bottom:1.1rem;
}
.login-bg .stButton>button{
    width:100%;
    border-radius:999px;
    background:#ef4444;
    color:#fef2f2;
    font-weight:700;
    padding:.55rem 1rem;
    border:none;
    box-shadow:0 18px 40px rgba(248,113,113,.75);
}
.login-bg .stButton>button:hover{
    background:#dc2626;
}
.login-footer{
    margin-top:.7rem;
    font-size:.78rem;
    color:#9ca3af;
    text-align:center;
}

/* ปุ่มที่เหลือใน main (เช่นในฟอร์มกรอกเลือด) */
main .stButton>button{
    border-radius:999px;
}

/* altair chart borders clear */
.vega-embed .chart-wrapper{
    border-radius:18px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ===== CONFIG =====
BAG_MAX = 20
CRITICAL_MAX = 4
YELLOW_MAX = 15
AUTH_PASSWORD = "1234"
FLASH_SECONDS = 2.5

RENAME_TO_UI = {"Plasma": "FFP", "Platelets": "PC"}
UI_TO_DB = {
    "LPRC": "LPRC",
    "PRC": "PRC",
    "FFP": "Plasma",
    "PC": "Platelets",
}
ALL_PRODUCTS_UI = ["LPRC", "PRC", "FFP", "Cryo", "PC"]

# คอลัมน์หลักที่ใช้เก็บใน session_state["entries"]
ENTRY_COLS = [
    "created_at",
    "Exp date",
    "Unit number",
    "Group",
    "Blood Components",
    "Status",
    "สถานะ(สี)",
    "บันทึก",
]

# สถานะหลัก (แก้จาก "จำหน่าย" เป็น "จ่ายแล้ว")
STATUS_OPTIONS = ["ว่าง", "จอง", "จ่ายแล้ว", "Exp", "หลุดจอง"]
STATUS_COLOR = {
    "ว่าง": "🟢 ว่าง",
    "จอง": "🟠 จอง",
    "จ่ายแล้ว": "⚫ จ่ายแล้ว",
    "Exp": "🔴 Exp",
    "หลุดจอง": "🔵 หลุดจอง",
}

# --------------------------------
# STATE
# --------------------------------
def _init_state():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("page", "หน้าหลัก")
    st.session_state.setdefault("selected_bt", None)
    st.session_state.setdefault("flash", None)
    st.session_state.setdefault("last_upload_token", None)

    if "entries" not in st.session_state:
        st.session_state["entries"] = pd.DataFrame(columns=ENTRY_COLS)
    else:
        for c in ENTRY_COLS:
            if c not in st.session_state["entries"].columns:
                st.session_state["entries"][c] = ""
        st.session_state["entries"] = st.session_state["entries"][ENTRY_COLS].copy()

    if "activity" not in st.session_state:
        st.session_state["activity"] = []


_init_state()

# --------------------------------
# HELPER FUNCTIONS
# --------------------------------
def _safe_rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


def flash(text, typ="success"):
    st.session_state["flash"] = {
        "type": typ,
        "text": text,
        "until": time.time() + FLASH_SECONDS,
    }


def show_flash():
    data = st.session_state.get("flash")
    if not data:
        return
    if time.time() > data.get("until", 0):
        st.session_state["flash"] = None
        return
    st.markdown(
        f'<div class="flash {data.get("type","success")}">{data.get("text","")}</div>',
        unsafe_allow_html=True,
    )


def compute_bag(total: int, max_cap=BAG_MAX):
    t = max(0, int(total))
    if t <= CRITICAL_MAX:
        status, label = "red", "วิกฤตใกล้หมด"
    elif t <= YELLOW_MAX:
        status, label = "yellow", "เพียงพอ"
    else:
        status, label = "green", "ปกติ"
    pct = max(0, min(100, int(round(100 * min(t, max_cap) / max_cap))))
    return status, label, pct


def bag_color(status: str) -> str:
    return {"green": "#22c55e", "yellow": "#f59e0b", "red": "#ef4444"}[status]


def normalize_products(rows):
    """สรุปจำนวนหน่วยตาม product_type จากข้อมูลใน db.get_stock_by_blood()"""
    d = {name: 0 for name in ALL_PRODUCTS_UI}
    for r in rows:
        name = str(r.get("product_type", "")).strip()
        ui = RENAME_TO_UI.get(name, name)
        if ui in d and ui != "Cryo":
            d[ui] += int(r.get("units", 0))
    return d


def get_global_cryo():
    total = 0
    for bt in ["A", "B", "O", "AB"]:
        rows = get_stock_by_blood(bt)
        for r in rows:
            name = str(r.get("product_type", "")).strip()
            ui = RENAME_TO_UI.get(name, name)
            if ui != "Cryo":
                total += int(r.get("units", 0))
    return total


# ===== SVG: ถุงเลือด + คลื่นน้ำ 2 ชั้น =====
def bag_svg(blood_type: str, total: int) -> str:
    status, _label, pct = compute_bag(total, BAG_MAX)
    fill = bag_color(status)
    letter_fill = {
        "A": "#facc15",
        "B": "#f472b6",
        "O": "#60a5fa",
        "AB": "#ffffff",
    }.get(blood_type, "#ffffff")

    inner_h = 148.0
    inner_y0 = 40.0
    water_h = inner_h * pct / 100.0
    water_y = inner_y0 + (inner_h - water_h)
    gid = f"g_{blood_type}"

    base_y = 20.0
    amp1 = 5 + 6 * (pct / 100.0)
    amp2 = amp1 * 0.6

    wave1_d = (
        f"M0 {base_y:.1f} "
        f"Q20 {base_y-amp1:.1f} 40 {base_y:.1f} "
        f"T80 {base_y:.1f} T120 {base_y:.1f} T160 {base_y:.1f} "
        "V40 H0 Z"
    )
    wave2_d = (
        f"M0 {base_y+2:.1f} "
        f"Q20 {base_y+2-amp2:.1f} 40 {base_y+2:.1f} "
        f"T80 {base_y+2:.1f} T120 {base_y+2:.1f} T160 {base_y+2:.1f} "
        "V42 H0 Z"
    )

    wave_speed1 = 5.0
    wave_speed2 = 7.5

    # ถ้า total = 0 ให้น้ำอยู่ต่ำสุด
    if total <= 0:
        water_y = inner_y0 + inner_h - 1

    return f"""
<div>
  <style>
    .bag-wrap{{display:flex;flex-direction:column;align-items:center;gap:10px;
               font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial}}
    .bag{{transition:transform .18s ease, filter .18s ease}}
    .bag:hover{{transform:translateY(-2px);
                filter:drop-shadow(0 10px 22px rgba(0,0,0,.12));}}
    .wave-layer{{mix-blend-mode:screen;opacity:.92}}
    @keyframes wave-move-1{{0%{{transform:translateX(0);}}
                            100%{{transform:translateX(-80px);}}}}
    @keyframes wave-move-2{{0%{{transform:translateX(0);}}
                            100%{{transform:translateX(-60px);}}}}
  </style>
  <div class="bag-wrap">
    <svg class="bag" width="170" height="230" viewBox="0 0 168 206"
         xmlns="http://www.w3.org/2000/svg">
      <defs>
        <clipPath id="clip-{gid}">
          <path d="M24,40 C24,24 38,14 58,14 L110,14 C130,14 144,24 144,40
                   L144,172 C144,191 128,202 108,204 L56,204 C36,202 24,191 24,172 Z"/>
        </clipPath>
        <linearGradient id="liquid-{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"  stop-color="{fill}" stop-opacity=".98"/>
          <stop offset="55%" stop-color="{fill}" stop-opacity=".94"/>
          <stop offset="100%" stop-color="{fill}" stop-opacity=".88"/>
        </linearGradient>
        <linearGradient id="liquid-soft-{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"  stop-color="{fill}" stop-opacity=".75"/>
          <stop offset="100%" stop-color="{fill}" stop-opacity=".6"/>
        </linearGradient>
        <path id="wave1-{gid}" d="{wave1_d}" />
        <path id="wave2-{gid}" d="{wave2_d}" />
      </defs>

      <!-- หูถุง -->
      <circle cx="84" cy="10" r="7.5"
              fill="#eef2ff" stroke="#dbe0ea" stroke-width="3"/>
      <rect x="77.5" y="14" width="13" height="8" rx="3" fill="#e5e7eb"/>

      <!-- ตัวถุง -->
      <path d="M16,34 C16,18 32,8 52,8 L116,8 C136,8 152,18 152,34
               L152,176 C152,195 136,206 116,206 L52,206 C32,206 16,195 16,176 Z"
            fill="#ffffff" stroke="#800000" stroke-width="3"/>

      <!-- ของเหลว + คลื่น -->
      <g clip-path="url(#clip-{gid})">
        <g transform="translate(24,{water_y:.1f})">
          <!-- ชั้นคลื่นหลัก -->
          <g class="wave-layer" style="animation:wave-move-1 {wave_speed1}s linear infinite;">
            <use href="#wave1-{gid}" fill="url(#liquid-{gid})" x="0"/>
            <use href="#wave1-{gid}" fill="url(#liquid-{gid})" x="80"/>
            <use href="#wave1-{gid}" fill="url(#liquid-{gid})" x="160"/>
          </g>
          <!-- ชั้นคลื่นรอง -->
          <g class="wave-layer" style="animation:wave-move-2 {wave_speed2}s linear infinite;">
            <use href="#wave2-{gid}" fill="url(#liquid-soft-{gid})" x="0"/>
            <use href="#wave2-{gid}" fill="url(#liquid-soft-{gid})" x="80"/>
            <use href="#wave2-{gid}" fill="url(#liquid-soft-{gid})" x="160"/>
          </g>
          <!-- น้ำส่วนล่าง -->
          <rect y="{base_y+4:.1f}" width="220" height="220" fill="url(#liquid-{gid})"/>
        </g>
      </g>

      <!-- ป้าย max -->
      <rect x="98" y="24" rx="10" ry="10" width="54" height="22"
            fill="#ffffff" stroke="#e5e7eb"/>
      <text x="125" y="40" text-anchor="middle"
            font-size="12" fill="#374151">{BAG_MAX} max</text>

      <!-- ตัวอักษรกำกับกรุ๊ปเลือด -->
      <text x="84" y="126" text-anchor="middle" font-size="32" font-weight="900"
            style="paint-order: stroke fill"
            stroke="#111827" stroke-width="4"
            fill="{letter_fill}">{blood_type}</text>
    </svg>
  </div>
</div>
"""


# --------------------------------
# INIT DB
# --------------------------------
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()


# --------------------------------
# DB UTIL
# --------------------------------
def totals_overview():
    ov = get_all_status()
    return {d["blood_type"]: int(d.get("total", 0)) for d in ov}


def products_of(bt):
    return normalize_products(get_stock_by_blood(bt))


def apply_stock_change(group, component_ui, qty, note, actor):
    if component_ui == "Cryo":
        raise ValueError("Cryo cannot be directly adjusted.")
    adjust_stock(group, UI_TO_DB[component_ui], qty, actor=actor, note=note)


def add_activity(action, bt, product_ui, qty, note):
    st.session_state["activity"].insert(
        0,
        {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "blood_type": bt,
            "product": product_ui,
            "qty": int(qty),
            "by": (st.session_state.get("username") or "staff"),
            "note": note or "",
        },
    )


def auto_update_booking_to_release():
    df = st.session_state["entries"]
    if df.empty:
        return
    today = date.today()
    updated_any = False
    for i, row in df.iterrows():
        try:
            if str(row.get("Status", "")) == "จอง":
                d = pd.to_datetime(row.get("created_at", ""), errors="coerce")
                if pd.isna(d):
                    continue
                if (today - d.date()).days >= 3:
                    df.at[i, "Status"] = "หลุดจอง"
                    df.at[i, "สถานะ(สี)"] = STATUS_COLOR["หลุดจอง"]
                    updated_any = True
        except Exception:
            pass
    if updated_any:
        st.session_state["entries"] = df


# --------------------------------
# EXPIRY UTIL
# --------------------------------
def left_days_safe(d):
    try:
        if pd.isna(d):
            return None
    except Exception:
        pass
    if isinstance(d, str):
        d2 = pd.to_datetime(d, errors="coerce")
        if pd.isna(d2):
            return None
        d = d2.date()
    elif isinstance(d, (datetime, pd.Timestamp)):
        d = d.date()
    elif not isinstance(d, date):
        return None
    return (d - date.today()).days


def expiry_label(days: int | None) -> str:
    if days is None:
        return ""
    if days < 0:
        return "🔴 หมดอายุแล้ว"
    if days <= 3:
        return f"🔴 เร่งด่วน (เหลือ {days} วัน)"
    if days == 4:
        return "🔴 ใกล้ครบกำหนด (4 วัน)"
    if 5 <= days <= 10:
        return f"🟠 เตือนล่วงหน้า (เหลือ {days} วัน)"
    if days > 8:
        return "🟢 ปกติ"
    return f"🟠 เตือนล่วงหน้า (เหลือ {days} วัน)"


def render_minimal_banner(df):
    if df.empty:
        return
    n_warn = int(
        ((df["_exp_days"].notna()) & (df["_exp_days"] <= 10) & (df["_exp_days"] >= 5)).sum()
    )
    n_red = int(((df["_exp_days"].notna()) & (df["_exp_days"] <= 4) & (df["_exp_days"] >= 0)).sum())
    n_exp = int(((df["_exp_days"].notna()) & (df["_exp_days"] < 0)).sum())
    if (n_warn + n_red + n_exp) == 0:
        return
    st.markdown(
        f"""<div id="expiry-banner"><div class="title">
        ⏰ สถานะวันหมดอายุ — 
        <span class="chip warn">เตือน {n_warn}</span>
        <span class="chip">วิกฤต {n_red+n_exp}</span></div></div>""",
        unsafe_allow_html=True,
    )


# --------------------------------
# VIEW: LANDING (ก่อนล็อกอิน)
# --------------------------------
def render_public_landing():
    last_update = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    st.markdown(
        f"""
<div class="landing-wrap">
  <div class="landing-hero">
    <div class="landing-hero-top">
      <div class="landing-hero-pill">
        <span class="dot"></span>
        Blood Stock Real-time Monitor – สำหรับธนาคารเลือด / ห้อง Lab
      </div>
      <div>อัปเดตล่าสุด: {last_update}</div>
    </div>

    <div class="landing-hero-grid">
      <div>
        <div class="landing-hero-title">Blood Stock Real-time Monitor</div>
        <div class="landing-hero-sub">
          แดชบอร์ดคลังเลือดแบบ Real-time ช่วยดูปริมาณสำรองและวันหมดอายุได้ทันที
        </div>
        <ul class="landing-hero-list">
          <li>ดูปริมาณคงเหลือแยกตามกรุ๊ปและผลิตภัณฑ์ (LPRC, PRC, FFP, PC, Cryo)</li>
          <li>รองรับการนำเข้าไฟล์ Excel / CSV จากระบบเดิมที่มีอยู่ได้ทันที</li>
          <li>แจ้งเตือน Critical / Warning จากวันหมดอายุ ช่วยลดความเสี่ยงของเลือดหมดอายุ</li>
        </ul>
        <div class="landing-hero-buttons">
          <button class="landing-btn-primary">เข้าสู่ระบบแดชบอร์ด</button>
          <button class="landing-btn-ghost">ดูตัวอย่างหน้าใช้งาน Lab</button>
        </div>
      </div>

      <div class="landing-hero-illu">
        <div class="landing-hero-illu-main">
          <div class="landing-hero-illu-chart"></div>
          <div class="landing-hero-bag"></div>
        </div>
      </div>
    </div>
  </div>

  <div class="landing-cards">
    <div class="landing-card">
      <h3>ภาพรวมคลังเลือดในแต่ละหมู่</h3>
      <small>ช่วยมองภาพรวมสถานะเลือดของกรุ๊ป A / B / O / AB ในมุมมองเดียว</small>
      <ul>
        <li><span class="landing-blood-dot green"></span>เพียงพอ – ปริมาณเลือดอยู่ในช่วงปลอดภัย</li>
        <li><span class="landing-blood-dot orange"></span>ใกล้หมด – ควรเตรียมสั่งเพิ่ม หรือวางแผนการใช้</li>
        <li><span class="landing-blood-dot red"></span>น้อยมาก – เสี่ยงขาดสต็อก ต้องเฝ้าระวังเป็นพิเศษ</li>
      </ul>
    </div>

    <div class="landing-card">
      <h3>ระดับแจ้งเตือนวันหมดอายุ</h3>
      <small>ช่วยมองล่วงหน้าว่ามีเลือดกำลังจะหมดอายุ และต้องจัดการหน่วยไหนก่อน</small>
      <ul>
        <li>
          <span class="landing-alert-label critical">Critical</span>
          <span>เลือดใกล้หมดอายุมาก ควรรีบใช้หรือพิจารณาปรับแผนให้ใช้หมดก่อน</span>
        </li>
        <li>
          <span class="landing-alert-label warning">Warning</span>
          <span>เลือดจะหมดอายุในไม่กี่วันข้างหน้า ควรนำไปใช้ก่อนหน่วยอื่น</span>
        </li>
      </ul>
    </div>
  </div>

  <div class="landing-manage">
    <strong>⚙️ การจัดการระบบ</strong><br/>
    ต้องเข้าสู่ระบบก่อนจึงจะใช้งานฟังก์ชันกรอกเลือด / แก้ไขตาราง และรีเซ็ตจำนวนสต็อกได้
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


# --------------------------------
# VIEW: DASHBOARD หลังล็อกอิน
# --------------------------------
def render_dashboard_home():
    auto_update_booking_to_release()

    c1, c2, _ = st.columns(3)
    c1.markdown(
        '<span class="badge"><span class="legend-dot" style="background:#ef4444"></span> วิกฤตใกล้หมด 0–4</span>',
        unsafe_allow_html=True,
    )
    c2.markdown(
        '<span class="badge"><span class="legend-dot" style="background:#f59e0b"></span> เพียงพอ 5–15</span>',
        unsafe_allow_html=True,
    )

    totals = totals_overview()
    blood_types = ["A", "B", "O", "AB"]
    cols = st.columns(4)
    for i, bt in enumerate(blood_types):
        with cols[i]:
            st.markdown(f"### ถุงเลือดกรุ๊ป **{bt}**")
            st_html(bag_svg(bt, totals.get(bt, 0)), height=270, scrolling=False)
            if st.button(f"ดูรายละเอียดกรุ๊ป {bt}", key=f"btn_{bt}"):
                st.session_state["selected_bt"] = bt
                _safe_rerun()

    st.divider()
    sel = st.session_state.get("selected_bt") or "A"
    st.subheader(f"รายละเอียดกรุ๊ป {sel}")
    _L, _M, _R = st.columns([1, 1, 1])
    with _M:
        st_html(bag_svg(sel, totals.get(sel, 0)), height=270, scrolling=False)

    dist_sel = products_of(sel)
    dist_sel["Cryo"] = get_global_cryo()

    df = pd.DataFrame([{"product_type": k, "units": int(v)} for k, v in dist_sel.items()])
    df["product_type"] = pd.Categorical(df["product_type"], categories=ALL_PRODUCTS_UI, ordered=True)

    def color_for(u):
        if u <= CRITICAL_MAX:
            return "#ef4444"
        if u <= YELLOW_MAX:
            return "#f59e0b"
        return "#22c55e"

    df["color"] = df["units"].apply(color_for)

    # สำหรับกราฟ: แสดงเฉพาะที่มีหน่วย > 0
    df_chart = df[df["units"] > 0].copy()
    ymax = max(10, int(df_chart["units"].max() * 1.25)) if not df_chart.empty else 10

    if df_chart.empty:
        st.info("ยังไม่มีหน่วยเลือดที่ใช้งานได้สำหรับกรุ๊ปนี้")
    else:
        bars = alt.Chart(df_chart).mark_bar().encode(
            x=alt.X("product_type:N", sort=ALL_PRODUCTS_UI, title="ประเภทผลิตภัณฑ์"),
            y=alt.Y("units:Q", title="จำนวนหน่วย (unit)", scale=alt.Scale(domainMin=0, domainMax=ymax)),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=["product_type", "units"],
        )
        text = alt.Chart(df_chart).mark_text(
            align="center",
            baseline="bottom",
            dy=-4,
            fontSize=13,
        ).encode(
            x=alt.X("product_type:N", sort=ALL_PRODUCTS_UI),
            y="units:Q",
            text="units:Q",
        )
        chart = alt.layer(bars, text).properties(height=340).configure_view(strokeOpacity=0)
        st.altair_chart(chart, use_container_width=True)

    st.dataframe(
        df.sort_values(by="product_type")[["product_type", "units"]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### รายการบันทึกความเคลื่อนไหว (Activity Log)")
    if st.session_state["activity"]:
        st.dataframe(pd.DataFrame(st.session_state["activity"]), use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีรายการความเคลื่อนไหว")


# --------------------------------
# VIEW: LOGIN PAGE
# --------------------------------
def render_login_page():
    st.markdown('<div class="login-bg">', unsafe_allow_html=True)

    with st.form("login_form_main", clear_on_submit=False):
        st.markdown(
            """
        <div class="login-header-icon">🩸</div>
        <div class="login-title">เข้าสู่ระบบคลังเลือด</div>
        <div class="login-sub">
            สำหรับเจ้าหน้าที่ธนาคารเลือด / ห้อง Lab ที่ต้องบันทึกและติดตามคลังเลือดแบบ Real-time
        </div>
        """,
            unsafe_allow_html=True,
        )
        u = st.text_input(
            "ชื่อผู้ใช้ (Username)",
            key="login_user_main",
            placeholder="เช่น bloodbank01 หรือชื่อของคุณ",
        )
        p = st.text_input(
            "รหัสผ่าน (Password)",
            key="login_pwd_main",
            type="password",
            placeholder="ทดลองใช้: 1234",
        )
        st.markdown(
            '<div class="login-hint">• แนะนำให้ใช้รหัสผ่านที่ไม่ซ้ำระบบอื่น และเก็บรักษาข้อมูลของคุณให้ปลอดภัย</div>',
            unsafe_allow_html=True,
        )
        submitted = st.form_submit_button("เข้าสู่ระบบ")

    st.markdown(
        '<div class="login-footer">หากลืมรหัสผ่าน กรุณาติดต่อผู้ดูแลระบบของหน่วยงานคุณ</div>',
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if p == AUTH_PASSWORD:
            st.session_state["logged_in"] = True
            st.session_state["username"] = (u or "").strip() or "staff"
            st.session_state["page"] = "กรอกเลือด"
            flash("เข้าสู่ระบบสำเร็จ ✅", "success")
            _safe_rerun()
        else:
            st.error("รหัสผ่านไม่ถูกต้อง (password = 1234)")


# --------------------------------
# SIDEBAR
# --------------------------------
with st.sidebar:
    if st.session_state.get("logged_in"):
        name = (st.session_state.get("username") or "staff").strip()
        initials = (name[:2] or "ST").upper()
        st.markdown(
            f"""
            <div class="user-card">
              <div class="user-avatar">{initials}</div>
              <div class="user-meta">
                <span class="label">เข้าสู่ระบบสำเร็จ</span>
                <span class="name">{name}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sidebar-title">เมนู</div>', unsafe_allow_html=True)
    if st.button("หน้าหลัก", key="nav_home", use_container_width=True):
        st.session_state["page"] = "หน้าหลัก"
        _safe_rerun()
    if st.button("กรอกเลือด", key="nav_entry", use_container_width=True):
        st.session_state["page"] = "กรอกเลือด"
        _safe_rerun()
    if st.button(
        "เข้าสู่ระบบ" if not st.session_state["logged_in"] else "ออกจากระบบ",
        key="nav_auth",
        use_container_width=True,
    ):
        if st.session_state["logged_in"]:
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["page"] = "หน้าหลัก"
            flash("ออกจากระบบแล้ว", "info")
        else:
            st.session_state["page"] = "เข้าสู่ระบบ"
        _safe_rerun()


# --------------------------------
# HEADER (ยกเว้นหน้า login)
# --------------------------------
if st.session_state["page"] != "เข้าสู่ระบบ":
    st.title("Blood Stock Real-time Monitor")
    st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

show_flash()

# --------------------------------
# PAGE: กรอกเลือด
# --------------------------------
if st.session_state["page"] == "กรอกเลือด":
    if not st.session_state["logged_in"]:
        st.warning("ต้องล็อกอินก่อนจึงจะใช้งานเมนูนี้ได้")
    else:
        st.subheader("กรอกเลือด")

        # ---- ฟอร์มกรอกทีละรายการ ----
        with st.form("blood_entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                unit_number = st.text_input("Unit number")
            with c2:
                exp_date = st.date_input("Exp date", value=date.today())
            c3, c4 = st.columns(2)
            with c3:
                group = st.selectbox("Group", ["A", "B", "O", "AB"])
            with c4:
                status = st.selectbox("Status", STATUS_OPTIONS, index=0)
            c5, c6 = st.columns(2)
            with c5:
                component = st.selectbox("Blood Components", ["LPRC", "PRC", "FFP", "PC"])
            with c6:
                note = st.text_input("บันทึก")
            submitted = st.form_submit_button("บันทึกรายการ", use_container_width=True)

        if submitted:
            new_row = {
                "created_at": datetime.now().strftime("%Y/%m/%d"),
                "Exp date": exp_date.strftime("%Y/%m/%d"),
                "Unit number": unit_number,
                "Group": group,
                "Blood Components": component,
                "Status": status,
                "สถานะ(สี)": STATUS_COLOR.get(status, status),
                "บันทึก": note,
            }
            st.session_state["entries"] = pd.concat(
                [st.session_state["entries"], pd.DataFrame([new_row])],
                ignore_index=True,
            )
            try:
                if status in ["ว่าง", "หลุดจอง"]:
                    apply_stock_change(
                        group, component, +1, note or "inbound", st.session_state.get("username") or "admin"
                    )
                    add_activity("INBOUND", group, component, +1, note)
                elif status in ["จ่ายแล้ว", "Exp"]:
                    apply_stock_change(
                        group, component, -1, note or status, st.session_state.get("username") or "admin"
                    )
                    add_activity("OUTBOUND", group, component, -1, note or status)
                else:
                    add_activity("BOOK", group, component, 0, "จอง (ไม่กระทบคลัง)")
                flash("บันทึกรายการและอัปเดตคลังแล้ว ✅")
            except Exception as e:
                st.error(f"ปรับคลังไม่สำเร็จ: {e}")
            _safe_rerun()

        # ---- นำเข้า Excel / CSV ----
        st.markdown("### 📁 นำเข้าจาก Excel/CSV (อัปโหลดแล้วลงตารางอัตโนมัติ)")
        up = st.file_uploader("เลือกไฟล์ (.xlsx, .xls, .csv)", type=["xlsx", "xls", "csv"], key="uploader_file")
        mode_merge = st.radio(
            "โหมดนำเข้า",
            ["รวมกับตาราง (merge/update)", "แทนที่ทั้งหมด (replace)"],
            horizontal=True,
            index=0,
            key="uploader_mode",
        )

        if up is not None:
            token = (up.name, up.size)
            if st.session_state.get("last_upload_token") != token:
                st.session_state["last_upload_token"] = token

                try:
                    if up.name.lower().endswith(".csv"):
                        df_file = pd.read_csv(up)
                    else:
                        try:
                            df_file = pd.read_excel(up)
                        except Exception as e:
                            st.error(
                                "อ่าน Excel ไม่ได้ (อาจขาด openpyxl). "
                                "แนะนำเพิ่ม openpyxl ใน requirements.txt หรืออัปโหลด CSV แทน"
                            )
                            st.info(str(e))
                            df_file = pd.DataFrame()

                    if not df_file.empty:
                        col_map = {
                            "created_at": "created_at",
                            "Created": "created_at",
                            "Created at": "created_at",
                            "Exp date": "Exp date",
                            "Exp": "Exp date",
                            "exp_date": "Exp date",
                            "Unit": "Unit number",
                            "Unit number": "Unit number",
                            "Group": "Group",
                            "Blood Components": "Blood Components",
                            "Components": "Blood Components",
                            "Status": "Status",
                            "Note": "บันทึก",
                            "Remarks": "บันทึก",
                            "บันทึก": "บันทึก",
                        }
                        df_file = df_file.rename(
                            columns={c: col_map.get(str(c).strip(), c) for c in df_file.columns}
                        )

                        status_map_en2th = {
                            "Available": "ว่าง",
                            "ReadyToIssue": "จอง",
                            "Released": "จ่ายแล้ว",
                            "Expired": "Exp",
                            "ReleasedExpired": "Exp",
                            "Out": "จ่ายแล้ว",
                        }
                        if "Status" in df_file.columns:
                            df_file["Status"] = df_file["Status"].map(
                                lambda s: status_map_en2th.get(str(s).strip(), str(s).strip())
                            )

                        for c in [
                            "created_at",
                            "Exp date",
                            "Unit number",
                            "Group",
                            "Blood Components",
                            "Status",
                            "บันทึก",
                        ]:
                            if c not in df_file.columns:
                                df_file[c] = ""
                        df_file = df_file[
                            [
                                "created_at",
                                "Exp date",
                                "Unit number",
                                "Group",
                                "Blood Components",
                                "Status",
                                "บันทึก",
                            ]
                        ].copy()

                        df_file["สถานะ(สี)"] = df_file["Status"].map(
                            lambda s: STATUS_COLOR.get(str(s), str(s))
                        )

                        replace_mode = mode_merge.startswith("แทนที่")
                        if replace_mode:
                            st.session_state["entries"] = pd.DataFrame(columns=ENTRY_COLS)
                            st.session_state["activity"] = []
                            reset_all_stock(st.session_state.get("username", "admin"))

                        new_rows = []
                        applied = failed = 0

                        for _, r in df_file.iterrows():
                            g = str(r["Group"]).strip() or "A"
                            comp = str(r["Blood Components"]).strip() or "LPRC"
                            stt = str(r["Status"]).strip() or "ว่าง"
                            nt = str(r["บันทึก"]).strip()

                            row_dict = {
                                "created_at": str(
                                    r["created_at"] or datetime.now().strftime("%Y/%m/%d")
                                ),
                                "Exp date": str(r["Exp date"] or ""),
                                "Unit number": str(r["Unit number"] or ""),
                                "Group": g,
                                "Blood Components": comp,
                                "Status": stt,
                                "สถานะ(สี)": STATUS_COLOR.get(stt, stt),
                                "บันทึก": nt,
                            }
                            new_rows.append(row_dict)

                            try:
                                if stt in ["ว่าง", "หลุดจอง"]:
                                    apply_stock_change(
                                        g, comp, +1, nt or "import", st.session_state.get("username") or "admin"
                                    )
                                    add_activity("INBOUND", g, comp, +1, f"import: {nt}")
                                elif stt in ["จ่ายแล้ว"]:
                                    add_activity("OUTBOUND", g, comp, 0, f"import: {nt}")
                                else:
                                    add_activity("INFO", g, comp, 0, f"import: {nt}")
                                applied += 1
                            except Exception:
                                failed += 1

                        new_df = pd.DataFrame(new_rows, columns=ENTRY_COLS)

                        if replace_mode:
                            st.session_state["entries"] = new_df
                        else:
                            combined = pd.concat(
                                [st.session_state["entries"], new_df],
                                ignore_index=True,
                            )
                            combined = combined.drop_duplicates(
                                subset=["Unit number", "Group", "Blood Components"],
                                keep="last",
                            )
                            st.session_state["entries"] = combined

                        flash(
                            f"นำเข้าเสร็จสิ้น ✅ สำเร็จ {applied} รายการ"
                            f"{' (ล้มเหลว '+str(failed)+')' if failed else ''}"
                        )

                except Exception as e:
                    st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")

        # ---- ตารางสรุป (แก้ไขได้) + ลำดับ ----
        st.markdown("### ตารางสรุป (แก้ไขได้)")
        df_vis = st.session_state["entries"].copy(deep=True)

        parsed = pd.to_datetime(df_vis["Exp date"], errors="coerce")
        df_vis["Exp date"] = parsed.dt.date

        df_vis["_exp_days"] = df_vis["Exp date"].apply(left_days_safe)
        df_vis["วันหมดอายุนับถอยหลัง (วัน)"] = df_vis["_exp_days"]
        df_vis["สถานะวันหมดอายุ"] = df_vis["_exp_days"].apply(expiry_label)

        render_minimal_banner(df_vis)

        cols_show = [
            "created_at",
            "Exp date",
            "วันหมดอายุนับถอยหลัง (วัน)",
            "สถานะวันหมดอายุ",
            "Unit number",
            "Group",
            "Blood Components",
            "Status",
            "สถานะ(สี)",
            "บันทึก",
        ]
        df_vis = df_vis.reindex(columns=cols_show)

        df_vis.insert(0, "ลำดับ", range(1, len(df_vis) + 1))

        col_cfg = {
            "ลำดับ": st.column_config.NumberColumn("ลำดับ", disabled=True),
            "created_at": st.column_config.TextColumn("Created at (YYYY/MM/DD)"),
            "Exp date": st.column_config.DateColumn("Exp date", format="YYYY/MM/DD"),
            "วันหมดอายุนับถอยหลัง (วัน)": st.column_config.NumberColumn(
                "วันหมดอายุนับถอยหลัง (วัน)", disabled=True
            ),
            "สถานะวันหมดอายุ": st.column_config.TextColumn("ค่าสถานะ (สี)", disabled=True),
            "Unit number": st.column_config.TextColumn("Unit number"),
            "Group": st.column_config.SelectboxColumn("Group", options=["A", "B", "O", "AB"]),
            "Blood Components": st.column_config.SelectboxColumn(
                "Blood Components", options=["LPRC", "PRC", "FFP", "PC"]
            ),
            "Status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS),
            "สถานะ(สี)": st.column_config.TextColumn("สถานะ(สี)", disabled=True),
            "บันทึก": st.column_config.TextColumn("บันทึก"),
        }

        edited = st.data_editor(
            df_vis,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg,
            key="entries_editor",
        )

        if not edited.equals(df_vis):
            out = edited.copy()
            if "ลำดับ" in out.columns:
                out = out.drop(columns=["ลำดับ"])

            def _d2str(x):
                try:
                    if pd.isna(x):
                        return ""
                except Exception:
                    pass
                if isinstance(x, (datetime, pd.Timestamp)):
                    return x.date().strftime("%Y/%m/%d")
                if isinstance(x, date):
                    return x.strftime("%Y/%m/%d")
                try:
                    return pd.to_datetime(x, errors="coerce").date().strftime("%Y/%m/%d")
                except Exception:
                    return str(x)

            out["Exp date"] = out["Exp date"].apply(_d2str)
            st.session_state["entries"] = out[ENTRY_COLS].reset_index(drop=True)
            flash("อัปเดตตารางแล้ว ✅")
            _safe_rerun()

# --------------------------------
# PAGE: หน้าหลัก
# --------------------------------
elif st.session_state["page"] == "หน้าหลัก":
    if not st.session_state["logged_in"]:
        render_public_landing()
    else:
        render_dashboard_home()

# --------------------------------
# PAGE: LOGIN
# --------------------------------
elif st.session_state["page"] == "เข้าสู่ระบบ":
    render_login_page()

# --------------------------------
# ปุ่มรีเซ็ตสต็อกทั้งหมด (เฉพาะหน้า dashboard / กรอกเลือด / landing)
# --------------------------------
if st.session_state["page"] != "เข้าสู่ระบบ":
    st.divider()
    st.markdown("### ⚠️ จัดการระบบ")
    if st.session_state.get("logged_in"):
        if st.button("🧹 รีเซ็ตเลือดทั้งหมดเป็นศูนย์", type="primary", use_container_width=True):
            reset_all_stock(st.session_state.get("username", "admin"))
            flash("รีเซ็ตจำนวนเลือดทั้งหมดแล้ว ✅", "warning")
            _safe_rerun()
    else:
        st.info("ต้องเข้าสู่ระบบก่อนจึงจะใช้งานปุ่มรีเซ็ตได้")
