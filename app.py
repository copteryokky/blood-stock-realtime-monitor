# app.py

import os
import time
from datetime import datetime, date, datetime as dt

import altair as alt
import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html

# ------- (optional) auto refresh -------
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    def st_autorefresh(*args, **kwargs):
        return None

# ------- DB functions (ใช้ db.py เดิม) -------
from db import init_db, get_all_status, get_stock_by_blood, adjust_stock, reset_all_stock


# ==========================================
# CONFIG & GLOBAL STYLE
# ==========================================
st.set_page_config(
    page_title="Blood Stock Real-time Monitor",
    page_icon="🩸",
    layout="wide",
)

st.markdown(
    """
<style>
/* พื้นหลังหลัก */
body {
    background: radial-gradient(circle at 0% 0%, #ffe4e6 0, #fff1f2 28%, #fdf2f8 52%, #ffffff 100%);
    font-family: system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
.block-container {
    padding-top: 1.7rem;
    padding-bottom: 2.5rem;
    max-width: 1240px;
}

/* หัวเรื่อง */
h1, h2, h3 {
    letter-spacing: .03em;
}

/* ปุ่ม Streamlit ทั่วไป */
.stButton>button {
    border-radius: 999px;
    font-weight: 600;
    border: 1px solid #e5e7eb;
    padding-top: .4rem;
    padding-bottom: .4rem;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: #020617;
}
[data-testid="stSidebar"] > div {
    padding-top: 1.2rem;
}
[data-testid="stSidebar"] .sidebar-title {
    color: #e5e7eb;
    font-weight: 800;
    font-size: 1.02rem;
    margin: 0 0 0.7rem 0.2rem;
}
[data-testid="stSidebar"] .stButton>button {
    width: 100%;
    justify-content: center;
    border-radius: 999px;
    border: 1px solid rgba(248,113,113,0.25);
    background: transparent;
    color: #e5e7eb;
    font-weight: 600;
}
[data-testid="stSidebar"] .stButton>button:hover {
    border-color: rgba(248,113,113,0.8);
    background: rgba(248, 113, 113, 0.08);
}

/* ---------- Badge ---------- */
.badge {
    display: inline-flex;
    align-items: center;
    gap: .4rem;
    padding: .25rem .6rem;
    border-radius: 999px;
    background: #f3f4f6;
    font-size: .82rem;
    color: #374151;
}
.legend-dot {
    width: .7rem;
    height: .7rem;
    border-radius: 999px;
    display: inline-block;
}

/* ---------- Flash message ---------- */
.flash {
    position: fixed;
    top: 90px;
    right: 24px;
    z-index: 9999;
    color: #fff;
    padding: .7rem 1rem;
    border-radius: 12px;
    font-weight: 700;
    box-shadow: 0 14px 30px rgba(0,0,0,.2);
    font-size: .9rem;
}
.flash.success { background:#16a34a; }
.flash.info    { background:#0ea5e9; }
.flash.warning { background:#f59e0b; }
.flash.error   { background:#ef4444; }

/* ---------- แบนเนอร์วันหมดอายุ ---------- */
#expiry-banner {
    border-radius: 14px;
    margin: 10px 0 12px 0;
    padding: 12px 14px;
    border: 2px solid #991b1b;
    background: linear-gradient(180deg,#fee2e2,#ffffff);
    box-shadow: 0 10px 24px rgba(153,27,27,.12);
}
#expiry-banner .title {
    font-weight: 900;
    font-size: 1.02rem;
    color: #7f1d1d;
}
#expiry-banner .chip {
    display:inline-flex;
    align-items:center;
    gap:.35rem;
    padding:.18rem .55rem;
    border-radius:999px;
    font-weight:800;
    background:#ef4444;
    color:#fff;
    margin-left:.45rem;
    font-size:.82rem;
}
#expiry-banner .chip.warn { background:#f59e0b; }

/* ---------- Landing hero ---------- */
.landing-shell { margin-top: 1.0rem; }
.landing-hero-card {
    position: relative;
    border-radius: 26px;
    padding: 24px 28px;
    background: radial-gradient(circle at 0% 0%, #fee2e2 0, #ffe4e6 36%, #fef2f2 100%);
    box-shadow: 0 26px 60px rgba(248,113,113,0.25);
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(0, .9fr);
    gap: 24px;
}
.landing-hero-pill {
    display:inline-flex;
    align-items:center;
    gap:.45rem;
    font-size:.80rem;
    padding:.25rem .8rem;
    border-radius:999px;
    background:#fee2e2;
    color:#b91c1c;
    font-weight:700;
    margin-bottom:.4rem;
}
.landing-hero-title {
    font-size: 1.7rem;
    font-weight: 900;
    color: #111827;
    margin-bottom: .3rem;
}
.landing-hero-sub {
    font-size: .96rem;
    color: #374151;
    margin-bottom: .7rem;
}
.landing-hero-list {
    padding-left: 1.15rem;
    margin-bottom: .9rem;
}
.landing-hero-list li {
    margin-bottom: .25rem;
    font-size: .9rem;
    color: #374151;
}
.landing-btn-row {
    display:flex;
    flex-wrap:wrap;
    gap:.65rem;
}
.landing-btn-primary,
.landing-btn-ghost {
    display:inline-flex;
    align-items:center;
    justify-content:center;
    border-radius:999px;
    padding:.55rem 1.4rem;
    font-size:.92rem;
    font-weight:700;
    text-decoration:none;
    border: 1px solid transparent;
    box-shadow: 0 14px 34px rgba(248,113,113,0.45);
}
.landing-btn-primary {
    background: linear-gradient(135deg,#fb7185,#f97316);
    color:#fff;
}
.landing-btn-primary:hover { filter: brightness(1.05); }
.landing-btn-ghost {
    background:#fff;
    color:#111827;
    box-shadow:none;
    border-color:#fed7d7;
}
.landing-hero-illu-wrap {
    display:flex;
    align-items:center;
    justify-content:center;
}
.landing-hero-illu {
    width: 260px;
    max-width: 100%;
    border-radius: 26px;
    background: radial-gradient(circle at 30% 0%, #fecaca 0, #f97373 40%, #b91c1c 100%);
    box-shadow: 0 32px 70px rgba(248,113,113,0.85);
    padding: 32px 26px;
}
.landing-hero-illu-inner {
    background:#fef2f2;
    border-radius: 20px;
    padding: 22px 18px;
    box-shadow: 0 16px 32px rgba(220,38,38,0.65);
}
.landing-hero-illu-chart {
    height: 78px;
    border-radius: 14px;
    background: linear-gradient(135deg,#fee2e2,#fecaca);
    margin-bottom: 18px;
    position: relative;
    overflow:hidden;
}
.landing-hero-illu-bag-row {
    display:flex;
    justify-content:flex-end;
    gap: 10px;
}
.landing-hero-illu-bag {
    width: 34px;
    height: 60px;
    border-radius: 16px;
    background:#ef4444;
    position:relative;
    box-shadow: 0 8px 18px rgba(127,29,29,0.55);
}
.landing-hero-illu-bag::before {
    content:"";
    position:absolute;
    top:-8px; left:8px; right:8px;
    height:8px;
    border-radius:999px;
    background:#fecaca;
}
.landing-hero-illu-bag::after {
    content:"";
    position:absolute;
    inset: 18px 4px 6px 4px;
    border-radius: 10px;
    background: linear-gradient(180deg,#fee2e2,#f97373);
}

/* กล่องข้อมูลด้านล่างหน้าแรก */
.landing-info-row {
    margin-top: 1.4rem;
    display: grid;
    grid-template-columns: minmax(0,1fr) minmax(0,1fr);
    gap: 16px;
}
.landing-card {
    border-radius: 20px;
    background:#ffffff;
    box-shadow: 0 18px 40px rgba(15,23,42,0.10);
    padding: 18px 20px 16px;
    border: 1px solid #fee2e2;
}
.landing-card h3 { font-size: 1.02rem; margin-bottom: .4rem; }
.landing-card small {
    display:block;
    color:#6b7280;
    font-size:.8rem;
    margin-bottom:.7rem;
}

/* ---------- Login Page ---------- */
/* กล่อง login ขาวกลางจอแบบ MEM System */
.login-card {
    max-width: 480px;
    margin: 80px auto 40px auto;
    padding: 32px 32px 26px;
    border-radius: 30px;
    background: #f9fafb;
    box-shadow: 0 32px 90px rgba(15,23,42,.9);
    border: 1px solid rgba(148,163,184,.45);
}
.login-title {
    text-align:center;
    font-size: 1.8rem;
    font-weight: 900;
    color: #111827;
    margin-bottom: .2rem;
}
.login-subtitle {
    text-align:center;
    font-size: .9rem;
    color: #6b7280;
    margin-bottom: 1.3rem;
}
.login-icon {
    width: 52px;
    height: 52px;
    border-radius: 18px;
    background: linear-gradient(135deg,#fb7185,#f97316);
    display:flex;
    align-items:center;
    justify-content:center;
    color:#fff;
    font-size:1.8rem;
    margin: 0 auto 10px auto;
    box-shadow: 0 18px 40px rgba(248,113,113,.55);
}

/* ฟอร์มใน login card */
.login-card .stTextInput>div>div>input {
    background: #ffffff;
    border-radius: 999px;
    border: 1px solid #d1d5db;
    color: #111827;
    padding: .55rem 1rem;
}
.login-card .stTextInput>div>div>input::placeholder { color: #9ca3af; }
.login-card .stTextInput>label>div>p {
    color: #111827;
    font-weight: 600;
    font-size: .86rem;
}
.login-note {
    font-size: .78rem;
    color: #6b7280;
    margin: .35rem 0 1.1rem 0;
}

/* ปุ่มใน login card */
.login-btn-primary button,
.login-btn-ghost button {
    border-radius: 999px !important;
    font-weight: 700 !important;
    padding-top: .45rem !important;
    padding-bottom: .45rem !important;
}
.login-btn-primary button {
    background: linear-gradient(135deg,#fb7185,#f97316);
    border: none;
    color: #fff;
    box-shadow: 0 18px 42px rgba(248,113,113,.7);
}
.login-btn-primary button:hover { filter: brightness(1.05); }
.login-btn-ghost button {
    background: #f9fafb;
    border:1px solid #cbd5f5;
    color:#111827;
}
.login-btn-ghost button:hover { background:#e5e7eb; }

/* ตาราง */
[data-testid="stDataFrame"] table { font-size: 13px; }
[data-testid="stDataFrame"] th {
    font-size: 13px;
    font-weight: 700;
    color: #111827;
}
</style>
""",
    unsafe_allow_html=True,
)


# ==========================================
# CONSTANTS
# ==========================================
BAG_MAX = 20
CRITICAL_MAX = 4
YELLOW_MAX = 15
AUTH_PASSWORD = "1234"
FLASH_SECONDS = 2.5

REN_TO_UI = {"Plasma": "FFP", "Platelets": "PC"}
UI_TO_DB = {
    "LPRC": "LPRC",
    "PRC": "PRC",
    "FFP": "Plasma",
    "PC": "Platelets",
}
ALL_PRODUCTS_UI = ["LPRC", "PRC", "FFP", "Cryo", "PC"]

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

STATUS_OPTIONS = ["ว่าง", "จอง", "จ่ายแล้ว", "Exp", "หลุดจอง"]
STATUS_COLOR = {
    "ว่าง": "🟢 ว่าง",
    "จอง": "🟠 จอง",
    "จ่ายแล้ว": "⚫ จ่ายแล้ว",
    "Exp": "🔴 Exp",
    "หลุดจอง": "🔵 หลุดจอง",
}

# ==========================================
# QUERY PARAMS ใช้จำสถานะล็อกอินหลัง F5
# ==========================================
try:
    _raw_qp = st.query_params
except Exception:
    _raw_qp = st.experimental_get_query_params()

if isinstance(_raw_qp, dict):
    _auth = _raw_qp.get("auth")
    if isinstance(_auth, list):
        _auth = _auth[0] if _auth else None
    URL_LOGGED = str(_auth) == "1"

    _go = _raw_qp.get("go")
    if isinstance(_go, list):
        _go = _go[0]
    URL_GO = _go
else:
    URL_LOGGED = False
    URL_GO = None


def set_auth_query(logged: bool):
    """อัปเดต query 'auth' สำหรับจำล็อกอินข้าม F5"""
    try:
        if logged:
            st.query_params = {"auth": "1"}
        else:
            st.query_params = {}
    except Exception:
        if logged:
            st.experimental_set_query_params(auth="1")
        else:
            st.experimental_set_query_params()


# ==========================================
# STATE INITIALIZATION
# ==========================================
def _init_state():
    ss = st.session_state
    ss.setdefault("logged_in", URL_LOGGED)
    ss.setdefault("username", "")
    default_page = "แดชบอร์ดคลังเลือด" if ss["logged_in"] else "หน้าแรก"
    ss.setdefault("page", default_page)
    ss.setdefault("selected_bt", None)
    ss.setdefault("flash", None)
    ss.setdefault("last_upload_token", None)

    if "entries" not in ss:
        ss["entries"] = pd.DataFrame(columns=ENTRY_COLS)
    else:
        for c in ENTRY_COLS:
            if c not in ss["entries"].columns:
                ss["entries"][c] = ""
        ss["entries"] = ss["entries"][ENTRY_COLS].copy()

    if "activity" not in ss:
        ss["activity"] = []


_init_state()

# ใช้ปุ่ม ?go=login / ?go=dashboard จากหน้าแรก
if URL_GO == "login":
    st.session_state["page"] = "เข้าสู่ระบบ"
elif URL_GO == "dashboard":
    st.session_state["page"] = "แดชบอร์ดคลังเลือด"


# ==========================================
# HELPER FUNCTIONS
# ==========================================
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
    d = {name: 0 for name in ALL_PRODUCTS_UI}
    for r in rows:
        name = str(r.get("product_type", "")).strip()
        ui = REN_TO_UI.get(name, name)
        if ui in d and ui != "Cryo":
            d[ui] += int(r.get("units", 0))
    return d


def get_global_cryo():
    total = 0
    for bt in ["A", "B", "O", "AB"]:
        rows = get_stock_by_blood(bt)
        for r in rows:
            name = str(r.get("product_type", "")).strip()
            ui = REN_TO_UI.get(name, name)
            if ui != "Cryo":
                total += int(r.get("units", 0))
    return total


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
          <g class="wave-layer" style="animation:wave-move-1 {wave_speed1}s linear infinite;">
            <use href="#wave1-{gid}" fill="url(#liquid-{gid})" x="0"/>
            <use href="#wave1-{gid}" fill="url(#liquid-{gid})" x="80"/>
            <use href="#wave1-{gid}" fill="url(#liquid-{gid})" x="160"/>
          </g>
          <g class="wave-layer" style="animation:wave-move-2 {wave_speed2}s linear infinite;">
            <use href="#wave2-{gid}" fill="url(#liquid-soft-{gid})" x="0"/>
            <use href="#wave2-{gid}" fill="url(#liquid-soft-{gid})" x="80"/>
            <use href="#wave2-{gid}" fill="url(#liquid-soft-{gid})" x="160"/>
          </g>
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
    n_warn = int(((df["_exp_days"].notna()) & (df["_exp_days"] <= 10) & (df["_exp_days"] >= 5)).sum())
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


# ==========================================
# INIT DB
# ==========================================
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()


# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown('<div class="sidebar-title">เมนู</div>', unsafe_allow_html=True)
    if st.button("หน้าแรก", key="nav_home"):
        st.session_state["page"] = "หน้าแรก"
        _safe_rerun()
    if st.button("แดชบอร์ดคลังเลือด", key="nav_dash"):
        st.session_state["page"] = "แดชบอร์ดคลังเลือด"
        _safe_rerun()
    if st.button("กรอกเลือด", key="nav_entry"):
        st.session_state["page"] = "กรอกเลือด"
        _safe_rerun()

    if not st.session_state["logged_in"]:
        if st.button("เข้าสู่ระบบ", key="nav_login"):
            st.session_state["page"] = "เข้าสู่ระบบ"
            _safe_rerun()
    else:
        if st.button("ออกจากระบบ", key="nav_logout"):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["page"] = "หน้าแรก"
            set_auth_query(False)
            flash("ออกจากระบบแล้ว", "info")
            _safe_rerun()


# ==========================================
# HEADER
# ==========================================
st.title("Blood Stock Real-time Monitor")
st.caption(f"อัปเดตล่าสุด: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
show_flash()


# ==========================================
# หน้าแรก
# ==========================================
if st.session_state["page"] == "หน้าแรก":
    st.markdown('<div class="landing-shell">', unsafe_allow_html=True)
    st.markdown(
        """
<div class="landing-hero-card">
  <div>
      <div class="landing-hero-pill">
        <span>🩸</span>
        <span>Blood Stock Real-time Monitor – สำหรับธนาคารเลือด / ห้อง Lab</span>
      </div>
      <div class="landing-hero-title">
        แดชบอร์ดคลังเลือดแบบ Real-time<br>ช่วยดูปริมาณสำรองและวันหมดอายุได้ทันที
      </div>
      <div class="landing-hero-sub">
        ระบบออกแบบมาสำหรับธนาคารเลือด ห้อง Lab และหน่วยงานควบคุมคุณภาพของโรงพยาบาล
        ใช้ติดตามสถานะถุงเลือดแต่ละกรุ๊ปและผลิตภัณฑ์แบบอัปเดตทันที พร้อมแจ้งเตือนวันหมดอายุเชิงรุก
      </div>
      <ul class="landing-hero-list">
        <li>ดูปริมาณคลังเลือดแยกตามกรุ๊ปและชนิดผลิตภัณฑ์ (LPRC, PRC, FFP, PC)</li>
        <li>รองรับนำเข้าไฟล์ Excel / CSV จาก LIS หรือระบบเดิมของคุณ</li>
        <li>แจ้งเตือน Critical / Warning ช่วยให้ทีมเตรียมเลือดทราบล่วงหน้า</li>
      </ul>
      <div class="landing-btn-row">
        <a href="?go=login" class="landing-btn-primary">เข้าสู่ระบบแดชบอร์ด</a>
        <a href="#examples" class="landing-btn-ghost">สำหรับทีม Audit / QA</a>
      </div>
  </div>
  <div class="landing-hero-illu-wrap">
    <div class="landing-hero-illu">
      <div class="landing-hero-illu-inner">
        <div class="landing-hero-illu-chart"></div>
        <div class="landing-hero-illu-bag-row">
          <div class="landing-hero-illu-bag"></div>
          <div class="landing-hero-illu-bag"></div>
          <div class="landing-hero-illu-bag"></div>
        </div>
      </div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
<div id="examples" class="landing-info-row">
  <div class="landing-card">
    <h3>ภาพรวมคลังเลือดในแต่ละหมู่</h3>
    <small>สถานะภาพรวมคลังเลือดกรุ๊ป A / B / O / AB ให้เห็นในมุมมองเดียว</small>
    <ul style="list-style:none;margin:0;padding-left:0;font-size:.9rem;">
      <li>🟢 <strong>เพียงพอ</strong> – ปริมาณเลือดยังอยู่ในช่วงปลอดภัย</li>
      <li>🟠 <strong>ใกล้หมด</strong> – ควรเตรียมสั่งเพิ่ม หรือวางแผนการใช้</li>
      <li>🔴 <strong>น้อยมาก</strong> – เสี่ยงขาดสต็อก ต้องเฝ้าระวังเป็นพิเศษ</li>
    </ul>
  </div>
  <div class="landing-card">
    <h3>ระดับแจ้งเตือนวันหมดอายุ</h3>
    <small>ช่วยมองเห็นถุงเลือดที่กำลังจะหมดอายุล่วงหน้า ลดการทิ้งและปรับแผนการใช้เลือด</small>
    <ul style="list-style:none;margin:0;padding-left:0;font-size:.9rem;">
      <li>
        <span style="color:#dc2626;font-weight:700;">Critical</span>
        <span style="margin-left:.35rem;">– เหลือวันหมดอายุน้อยมาก ควรใช้ให้หมดโดยด่วน</span>
      </li>
      <li style="margin-top:.15rem;">
        <span style="color:#f97316;font-weight:700;">Warning</span>
        <span style="margin-left:.35rem;">– เหลือวันหมดอายุไม่กี่วัน เหมาะสำหรับทดแทนหน่วยเลือดใหม่</span>
      </li>
    </ul>
  </div>
</div>
<div style="margin-top:1.4rem;border-radius:20px;background:#eff6ff;
            padding:10px 18px;border:1px solid #bfdbfe;font-size:.88rem;">
  ⚙️ <strong>การจัดการระบบ</strong> – เมื่อล็อกอินด้วยรหัสสำหรับเจ้าหน้าที่ธนาคารเลือด / ห้อง Lab
  จะสามารถบันทึกข้อมูลจริงในคลังเลือดและปรับสต็อกได้
</div>
</div>
""",
        unsafe_allow_html=True,
    )


# ==========================================
# LOGIN PAGE
# ==========================================
elif st.session_state["page"] == "เข้าสู่ระบบ":
    # ทำพื้นหลังทั้งหน้ามืด (เข้ม) แบบ MEM
    st.markdown(
        """
<style>
[data-testid="stAppViewContainer"]{
    background: radial-gradient(circle at 50% 0%, #111827 0, #020617 55%, #020617 100%) !important;
}
[data-testid="stHeader"]{background:transparent;}
.block-container{
    max-width: 1100px;
    padding-top: 2.5rem;
}
</style>
""",
        unsafe_allow_html=True,
    )

    col_l, col_c, col_r = st.columns([1, 1.1, 1])
    with col_c:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)

        st.markdown('<div class="login-icon">+</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">เข้าสู่ระบบคลังเลือด</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="login-subtitle">สำหรับเจ้าหน้าที่ธนาคารเลือด / ห้อง Lab ที่ต้องการบันทึกและติดตามคลังเลือดแบบ Real-time</div>',
            unsafe_allow_html=True,
        )

        username = st.text_input("ชื่อผู้ใช้ (Username)", key="login_username")
        password = st.text_input("รหัสผ่าน (Password)", type="password", key="login_password")

        st.markdown(
            '<div class="login-note">ทดลองใช้รหัสผ่าน <strong>1234</strong> เพื่อเข้าสู่ระบบ หรือเปลี่ยนเป็นรหัสจริงของหน่วยงานได้ภายหลัง</div>',
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        with c1:
            with st.container():
                login_clicked = st.button("เข้าสู่ระบบ", use_container_width=True, key="login_btn")
        with c2:
            with st.container():
                back_clicked = st.button("⬅️ กลับไปหน้าแรก", use_container_width=True, key="back_btn")

        st.markdown("</div>", unsafe_allow_html=True)

        # ใส่ class ให้ปุ่ม 2 อันสำหรับสไตล์กลม ๆ
        st.markdown(
            """
<script>
const root = window.parent.document;
const btns = root.querySelectorAll('button[kind="secondary"]');
if (btns.length >= 2) {
  btns[btns.length-2].parentElement.classList.add("login-btn-primary");
  btns[btns.length-1].parentElement.classList.add("login-btn-ghost");
}
</script>
""",
            unsafe_allow_html=True,
        )

        if login_clicked:
            if password == AUTH_PASSWORD:
                st.session_state["logged_in"] = True
                st.session_state["username"] = (username or "").strip() or "staff"
                st.session_state["page"] = "แดชบอร์ดคลังเลือด"
                set_auth_query(True)  # ใส่ auth=1 → F5 แล้วไม่เด้งออก
                flash("เข้าสู่ระบบสำเร็จ ✅", "success")
                _safe_rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง (ตัวอย่าง: 1234)")

        if back_clicked:
            st.session_state["page"] = "หน้าแรก"
            _safe_rerun()


# ==========================================
# PAGE: กรอกเลือด
# ==========================================
elif st.session_state["page"] == "กรอกเลือด":
    if not st.session_state["logged_in"]:
        st.warning("ต้องเข้าสู่ระบบก่อนจึงจะใช้งานเมนูนี้ได้")
    else:
        # *** เหมือนเวอร์ชันเดิมของคุณด้านล่าง ***
        # (ตัดมาจากโค้ดของคุณ แบบเดิมทุกอย่าง)
        ...
        # เพื่อไม่ให้ข้อความยาวเกินไป ตรงนี้ให้คุณวางส่วน "กรอกเลือด" จากไฟล์เดิมต่อได้เลย


# ==========================================
# PAGE: แดชบอร์ดคลังเลือด
# ==========================================
elif st.session_state["page"] == "แดชบอร์ดคลังเลือด":
    auto_update_booking_to_release()
    # ... ส่วนแดชบอร์ดใช้ตามโค้ดเดิมของคุณ ...


# ==========================================
# ปุ่มรีเซ็ต
# ==========================================
st.divider()
st.markdown("### ⚠️ การจัดการระบบ")
if st.session_state.get("logged_in"):
    if st.button("🧹 รีเซ็ตเลือดทั้งหมดเป็นศูนย์", type="primary", use_container_width=True):
        reset_all_stock(st.session_state.get("username", "admin"))
        flash("รีเซ็ตจำนวนเลือดทั้งหมดแล้ว ✅", "warning")
        _safe_rerun()
else:
    st.info("ต้องเข้าสู่ระบบก่อนจึงจะใช้งานปุ่มรีเซ็ตได้")
