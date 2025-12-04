# app.py
import os
import time
from datetime import datetime, date, datetime as dt

import altair as alt
import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html

# ===== optional autorefresh (ถ้าไม่มี lib นี้ก็ไม่ error) =====
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # noqa
    def st_autorefresh(*args, **kwargs):
        return None

# ===== DB funcs =====
from db import init_db, get_all_status, get_stock_by_blood, adjust_stock, reset_all_stock


# -------------------------------------------------------------------
# CONFIG & GLOBAL CONSTANTS
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Blood Stock Real-time Monitor",
    page_icon="🩸",
    layout="wide",
)

st.markdown(
    """
<style>
/* --------------------------------------------------
   พื้นหลังหลัก + layout
-------------------------------------------------- */
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top left,#ffe4e6 0,#ffffff 40%,#ffffff 100%);
    font-family: system-ui,-apple-system,"Sarabun","Segoe UI",sans-serif;
}

.block-container {
    padding-top: 0.8rem;
    padding-bottom: 3rem;
    max-width: 1180px;
}

/* --------------------------------------------------
   Heading
-------------------------------------------------- */
h1, h2, h3 {
    letter-spacing: 0.2px;
}

/* --------------------------------------------------
   Sidebar
-------------------------------------------------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#020617,#020617 30%,#020617 100%);
    color: #e5e7eb;
}
[data-testid="stSidebar"] .sidebar-title {
    color:#e5e7eb;
    font-weight:800;
    font-size:1.06rem;
    margin: 6px 0 14px 4px;
}
[data-testid="stSidebar"] .stButton>button {
    width:100%;
    border-radius:999px;
    border:1px solid transparent;
    padding:0.55rem 0.9rem;
    font-weight:600;
    background:#020617;
    color:#e5e7eb;
    box-shadow:0 0 0 1px rgba(148,27,37,.45);
}
[data-testid="stSidebar"] .stButton>button:hover {
    background:#111827;
}
[data-testid="stSidebar"] .stButton>button:focus {
    outline:2px solid #fb7185;
}

/* --------------------------------------------------
   legend badge
-------------------------------------------------- */
.badge{
    display:inline-flex;
    align-items:center;
    gap:.4rem;
    padding:.25rem .55rem;
    border-radius:999px;
    background:#f3f4f6;
    font-size:0.83rem;
}
.legend-dot{
    width:.7rem;
    height:.7rem;
    border-radius:999px;
    display:inline-block;
}

/* --------------------------------------------------
   Flash message
-------------------------------------------------- */
.flash{
    position:fixed;
    top:86px;
    right:24px;
    z-index:9999;
    color:#fff;
    padding:.75rem 1rem;
    border-radius:12px;
    font-weight:800;
    box-shadow:0 10px 24px rgba(0,0,0,.18);
}
.flash.success{background:#16a34a;}
.flash.info{background:#0ea5e9;}
.flash.warning{background:#f97316;}
.flash.error{background:#ef4444;}

/* --------------------------------------------------
   Sticky expiry banner
-------------------------------------------------- */
#expiry-banner{
    position:sticky;
    top:0;
    z-index:1000;
    border-radius:14px;
    margin:6px 0 12px 0;
    padding:12px 14px;
    border:2px solid #991b1b;
    background:linear-gradient(180deg,#fee2e2,#ffffff);
    box-shadow:0 10px 24px rgba(153,27,27,.12);
}
#expiry-banner .title{
    font-weight:900;
    font-size:1.02rem;
    color:#7f1d1d;
}
#expiry-banner .chip{
    display:inline-flex;
    align-items:center;
    gap:.35rem;
    padding:.2rem .55rem;
    border-radius:999px;
    font-weight:800;
    background:#ef4444;
    color:#fff;
    margin-left:.5rem;
}
#expiry-banner .chip.warn{background:#f59e0b;}

/* --------------------------------------------------
   Landing hero (หน้าแรกแบบการ์ดใหญ่)
-------------------------------------------------- */
.landing-shell{
    margin-top:1.5rem;
}
.landing-card-main{
    background:linear-gradient(135deg,#fff1f2,#ffffff);
    border-radius:28px;
    box-shadow:0 24px 45px rgba(248,113,113,.22);
    padding:26px 30px 26px 30px;
    display:grid;
    grid-template-columns: minmax(0,3fr) minmax(0,2.6fr);
    gap:16px;
    border:1px solid #fecaca;
}
.landing-hero-tag{
    display:inline-flex;
    align-items:center;
    gap:.4rem;
    background:#fee2e2;
    color:#b91c1c;
    font-weight:700;
    font-size:.82rem;
    padding:.3rem .9rem;
    border-radius:999px;
}
.landing-hero-title{
    margin-top:.7rem;
    font-size:1.7rem;
    font-weight:800;
    color:#111827;
}
.landing-hero-sub{
    margin-top:.35rem;
    font-size:.95rem;
    color:#374151;
}
.landing-hero-list{
    margin-top:.4rem;
    font-size:.9rem;
    color:#374151;
}
.landing-hero-list li{
    margin:0.12rem 0;
}
.landing-hero-list li::marker{
    color:#fb7185;
}

/* ปุ่มในหน้า landing */
.landing-hero-buttons{
    margin-top:1rem;
    display:flex;
    flex-wrap:wrap;
    gap:.75rem;
}
.landing-btn-primary{
    border-radius:999px;
    background:#fb3748;
    color:#ffffff;
    border:none;
    padding:.55rem 1.6rem;
    font-weight:700;
    font-size:.9rem;
    box-shadow:0 14px 28px rgba(248,113,113,.55);
}
.landing-btn-ghost{
    border-radius:999px;
    background:#ffffff;
    color:#111827;
    border:1px solid #fecaca;
    padding:.55rem 1.4rem;
    font-weight:600;
    font-size:.9rem;
}

/* Illustration */
.landing-hero-illu-wrap{
    position:relative;
    display:flex;
    align-items:center;
    justify-content:center;
}
.landing-hero-illu{
    width:220px;
    height:170px;
    border-radius:26px;
    background:radial-gradient(circle at top,#fee2e2 0,#fecaca 40%,#f97373 90%);
    box-shadow:0 20px 40px rgba(248,113,113,.45);
    display:flex;
    align-items:center;
    justify-content:center;
}
.landing-hero-illu-inner{
    width:140px;
    height:90px;
    border-radius:18px;
    background:#ffffff;
    box-shadow:0 10px 25px rgba(15,23,42,.22);
    padding:12px;
}
.landing-hero-illu-graph{
    width:100%;
    height:40px;
    border-radius:999px;
    background:linear-gradient(90deg,#fee2e2,#fecaca);
    margin-bottom:10px;
}
.landing-hero-illu-bags{
    display:flex;
    justify-content:flex-end;
    gap:8px;
}
.landing-hero-illu-bag{
    width:28px;
    height:48px;
    border-radius:12px;
    background:#fb3748;
    box-shadow:0 8px 18px rgba(185,28,28,.5);
}

/* card ด้านล่าง 2 ใบ */
.landing-row{
    margin-top:1.8rem;
    display:grid;
    grid-template-columns: minmax(0,1fr) minmax(0,1fr);
    gap:18px;
}
.landing-card{
    background:#ffffff;
    border-radius:20px;
    border:1px solid #e5e7eb;
    box-shadow:0 14px 35px rgba(15,23,42,.04);
    padding:18px 20px 20px 20px;
    font-size:.9rem;
}
.landing-card h3{
    font-size:1rem;
    margin-bottom:.45rem;
}

/* การ์ด 'จัดการระบบ' */
.system-card{
    margin-top:1.8rem;
    background:#eff6ff;
    border-radius:18px;
    border:1px solid #bfdbfe;
    padding:14px 18px;
    font-size:.9rem;
}

/* --------------------------------------------------
   Login layout (โหมดเข้าสู่ระบบ)
-------------------------------------------------- */
.login-root {
    min-height: 92vh;
    display:flex;
    align-items:center;
    justify-content:center;
}
.login-card {
    width: 360px;
    max-width: 92vw;
    background:#ffffff;
    border-radius:26px;
    padding:26px 26px 24px 26px;
    box-shadow:0 24px 60px rgba(15,23,42,.55);
    border:1px solid rgba(148,27,37,.35);
}
.login-title{
    font-size:1.3rem;
    font-weight:800;
    margin-bottom:.15rem;
}
.login-sub{
    font-size:.85rem;
    color:#6b7280;
    margin-bottom:1.1rem;
}
.login-hint{
    font-size:.8rem;
    color:#6b7280;
    margin-top:.3rem;
}

/* ปุ่ม login */
.login-btn > button{
    width:100%;
    border-radius:999px !important;
    background:#fb3748 !important;
    color:#ffffff !important;
    border:none !important;
    font-weight:700 !important;
    box-shadow:0 16px 35px rgba(248,113,113,.6);
}
.login-btn > button:hover{
    filter:brightness(1.03);
}

/* DataFrame font */
[data-testid="stDataFrame"] table {font-size:14px;}
[data-testid="stDataFrame"] th {
    font-size:14px;
    font-weight:700;
    color:#111827;
}
</style>
""",
    unsafe_allow_html=True,
)

# --- business config ---
BAG_MAX = 20
CRITICAL_MAX = 4
YELLOW_MAX = 15
AUTH_PASSWORD = "1234"
FLASH_SECONDS = 2.5

RENAME_TO_UI = {"Plasma": "FFP", "Platelets": "PC"}
UI_TO_DB = {"LPRC": "LPRC", "PRC": "PRC", "FFP": "Plasma", "PC": "Platelets"}
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

# -------------------------------------------------------------------
# STATE
# -------------------------------------------------------------------
def _init_state():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    # หน้าเริ่มต้นให้มา Landing (หน้าหลัก)
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

# -------------------------------------------------------------------
# HELPER ฟังก์ชันทั่วไป
# -------------------------------------------------------------------
def _safe_rerun():
    try:
        st.rerun()
    except Exception:  # streamlit เก่าบาง version
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


# ===== SVG: ถุงเลือด =====
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

      <!-- ตัวอักษรกำกับกรุ๊ป -->
      <text x="84" y="126" text-anchor="middle" font-size="32" font-weight="900"
            style="paint-order: stroke fill"
            stroke="#111827" stroke-width="4"
            fill="{letter_fill}">{blood_type}</text>
    </svg>
  </div>
</div>
"""


# -------------------------------------------------------------------
# DB UTIL
# -------------------------------------------------------------------
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


# -------------------------------------------------------------------
# Expiry util
# -------------------------------------------------------------------
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


# -------------------------------------------------------------------
# หน้า Landing (สำหรับคนยังไม่ล็อกอิน)
# -------------------------------------------------------------------
def render_landing_public():
    st.markdown(
        f"""
<div class="landing-shell">
  <div class="landing-card-main">
    <div>
      <div class="landing-hero-tag">
        <span>🩸 Blood Stock Real-time Monitor</span>
        <span style="font-weight:500;">สำหรับธนาคารเลือด / ห้อง Lab</span>
      </div>
      <div class="landing-hero-title">
        แดชบอร์ดคลังเลือดแบบ Real-time
      </div>
      <div class="landing-hero-sub">
        ช่วยดูปริมาณสำรองและวันหมดอายุแบบอัปเดตทันที ใช้สำหรับทีมธนาคารเลือดและห้อง Lab ในโรงพยาบาล
      </div>
      <ul class="landing-hero-list">
        <li>ดูปริมาณคลังเลือดรวมและแยกตามกรุ๊ปและผลิตภัณฑ์ (LPRC, PRC, FFP, PC)</li>
        <li>รองรับนำเข้าไฟล์ Excel / CSV จาก LIS หรือระบบเดิมของคุณ</li>
        <li>แจ้งเตือน Critical / Warning ช่วยให้เห็นเคสเร่งด่วนก่อนหมดอายุ</li>
      </ul>
      <div class="landing-hero-buttons">
        <button class="landing-btn-primary">เข้าสู่ระบบแดชบอร์ด</button>
        <button class="landing-btn-ghost">สำหรับทีม Audit / QA</button>
      </div>
    </div>
    <div class="landing-hero-illu-wrap">
      <div class="landing-hero-illu">
        <div class="landing-hero-illu-inner">
          <div class="landing-hero-illu-graph"></div>
          <div class="landing-hero-illu-bags">
            <div class="landing-hero-illu-bag"></div>
            <div class="landing-hero-illu-bag"></div>
            <div class="landing-hero-illu-bag" style="opacity:.85;"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="landing-row">
    <div class="landing-card">
      <h3>ภาพรวมคลังเลือดในแต่ละหมู่</h3>
      <p style="font-size:.82rem;color:#6b7280;margin-bottom:.4rem;">
        แสดงภาพรวมสถานะคลังเลือด A / B / O / AB ในมุมมองเดียว
      </p>
      <ul style="list-style:none;padding-left:0;font-size:.85rem;">
        <li style="margin:.15rem 0;">✅ เพียงพอ – ปริมาณคลังเลือดยังอยู่ในช่วงปลอดภัย</li>
        <li style="margin:.15rem 0;">🟠 ใกล้หมด – ควรเตรียมสั่งเพิ่ม หรือวางแผนการใช้</li>
        <li style="margin:.15rem 0;">🔴 น้อยมาก – เสี่ยงขาดสต็อก ต้องเฝ้าระวังเป็นพิเศษ</li>
      </ul>
    </div>
    <div class="landing-card">
      <h3>ระดับแจ้งเตือนวันหมดอายุ</h3>
      <p style="font-size:.82rem;color:#6b7280;margin-bottom:.4rem;">
        ช่วยมองเห็นถุงเลือดที่กำลังจะหมดอายุล่วงหน้า ลดการทิ้งและบริหารแผนการใช้เลือด
      </p>
      <ul style="list-style:none;padding-left:0;font-size:.85rem;">
        <li style="margin:.18rem 0;">
          <span style="color:#dc2626;font-weight:700;">Critical</span>
          <span style="margin-left:.3rem;">เหลือวันหมดอายุน้อยมาก ควรใช้ให้หมดโดยด่วน</span>
        </li>
        <li style="margin:.18rem 0;">
          <span style="color:#f97316;font-weight:700;">Warning</span>
          <span style="margin-left:.3rem;">เหลือเวลาอีกไม่กี่วัน เหมาะสำหรับการใช้ก่อนล็อตใหม่</span>
        </li>
      </ul>
    </div>
  </div>

  <div class="system-card">
    <strong>⚙️ จัดการระบบ</strong> — ต้องเข้าสู่ระบบก่อนจึงจะเข้าหน้ากรอกเลือดและแดชบอร์ดจริงได้
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ปุ่ม Streamlit จริง ๆ สำหรับเปลี่ยนหน้าไป Login
    st.write("")  # spacing
    col1, col2, _ = st.columns([1, 1, 2])
    with col1:
        if st.button("🔐 เข้าสู่ระบบเพื่อใช้งานจริง", use_container_width=True):
            st.session_state["page"] = "เข้าสู่ระบบ"
            _safe_rerun()
    with col2:
        st.caption("Tip: ใช้รหัสผ่านทดลอง 1234 เพื่อทดลองระบบ")


# -------------------------------------------------------------------
# หน้า LOGIN (กล่องอยู่กลางจอ)
# -------------------------------------------------------------------
def render_login_page():
    st.markdown(
        """
<style>
/* override พื้นหลังให้มืดนิดหน่อย */
[data-testid="stAppViewContainer"]{
    background: radial-gradient(circle at top,#020617 0,#020617 25%,#020617 40%,#020617 100%);
}
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="login-root">', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown(
            """
<div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.4rem;">
  <div style="width:32px;height:32px;border-radius:999px;background:#fb3748;
              display:flex;align-items:center;justify-content:center;color:white;
              box-shadow:0 0 0 3px rgba(248,113,113,.35);">
    🩸
  </div>
  <div style="font-weight:700;font-size:.9rem;color:#6b7280;">Blood Stock Real-time Monitor</div>
</div>
<div class="login-title">เข้าสู่ระบบคลังเลือด</div>
<div class="login-sub">สำหรับเจ้าหน้าที่ธนาคารเลือด / ห้อง Lab ที่ต้องการบันทึกและติดตามคลังเลือดแบบ Real-time</div>
""",
            unsafe_allow_html=True,
        )

        with st.form("login_form_main"):
            username = st.text_input("ชื่อผู้ใช้ (Username)", value="", placeholder="เช่น bloodbank01 หรือชื่อของคุณ")
            password = st.text_input("รหัสผ่าน (Password)", value="", type="password", placeholder="ทดลองใช้: 1234")
            st.markdown(
                '<div class="login-hint">แนะนำให้ใช้รหัสผ่านที่ได้รับจากหน่วยงานเท่านั้น • เวอร์ชันทดลองให้ใช้รหัสผ่าน 1234 เพื่อเข้าสู่ระบบ</div>',
                unsafe_allow_html=True,
            )
            st.write("")
            submit = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True)

        st.markdown('<div class="login-btn"></div>', unsafe_allow_html=True)

        if submit:
            if password == AUTH_PASSWORD:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username.strip() or "staff"
                st.session_state["page"] = "หน้าหลัก"
                flash("เข้าสู่ระบบสำเร็จ ✅", "success")
                _safe_rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง — กรุณาลองใหม่ (สำหรับทดสอบใช้ 1234)")

        st.markdown(
            """
<div style="margin-top:1.1rem;font-size:.78rem;color:#9ca3af;text-align:center;">
หากใช้เครื่องสาธารณะ เมื่อใช้งานเสร็จแล้ว กรุณากดออกจากระบบเพื่อความปลอดภัยของข้อมูล
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# -------------------------------------------------------------------
# หน้า กรอกเลือด (เหมือนเดิม + แก้บัค)
# -------------------------------------------------------------------
def render_entry_page():
    if not st.session_state["logged_in"]:
        st.warning("ต้องเข้าสู่ระบบก่อนจึงจะใช้งานเมนูนี้ได้")
        if st.button("ไปยังหน้าล็อกอิน", type="primary"):
            st.session_state["page"] = "เข้าสู่ระบบ"
            _safe_rerun()
        return

    st.subheader("กรอกเลือดเข้าระบบ (บันทึกทีละรายการ)")

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

    # ----------------- นำเข้าไฟล์ -----------------
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
        if st.session_state.get("last_upload_token") == token:
            st.info("ไฟล์นี้ถูกนำเข้าแล้วในการรันรอบนี้")
        else:
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
                            "created_at": str(r["created_at"] or datetime.now().strftime("%Y/%m/%d")),
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
                    _safe_rerun()
            except Exception as e:
                st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")

    # ----------------- ตารางสรุปแก้ไขได้ -----------------
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
        "สถานะวันหมดอายุ": st.column_config.TextColumn("สถานะวันหมดอายุ", disabled=True),
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


# -------------------------------------------------------------------
# หน้า Dashboard หลัก (หลังล็อกอิน)
# -------------------------------------------------------------------
def render_dashboard_page():
    if not st.session_state["logged_in"]:
        render_landing_public()
        return

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


# -------------------------------------------------------------------
# INIT DB
# -------------------------------------------------------------------
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()
else:
    # เผื่อกรณี schema ยังไม่ครบ
    init_db()

# -------------------------------------------------------------------
# SIDEBAR เมนูหลัก
# -------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="sidebar-title">เมนู</div>', unsafe_allow_html=True)

    if st.button("หน้าหลัก", use_container_width=True):
        st.session_state["page"] = "หน้าหลัก"
        _safe_rerun()
    if st.button("กรอกเลือด", use_container_width=True):
        st.session_state["page"] = "กรอกเลือด"
        _safe_rerun()
    if st.session_state["logged_in"]:
        if st.button("ออกจากระบบ", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["page"] = "หน้าหลัก"
            flash("ออกจากระบบแล้ว", "info")
            _safe_rerun()
    else:
        if st.button("เข้าสู่ระบบ", use_container_width=True):
            st.session_state["page"] = "เข้าสู่ระบบ"
            _safe_rerun()

# -------------------------------------------------------------------
# HEADER + ROUTER
# -------------------------------------------------------------------
st.title("Blood Stock Real-time Monitor")
st.caption(f"อัปเดตล่าสุด: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
show_flash()

current_page = st.session_state.get("page", "หน้าหลัก")

if current_page == "หน้าหลัก":
    # ถ้าล็อกอินแล้ว -> Dashboard จริง / ถ้ายังไม่ล็อกอิน -> Landing สวย ๆ
    if st.session_state["logged_in"]:
        render_dashboard_page()
    else:
        render_landing_public()

elif current_page == "กรอกเลือด":
    render_entry_page()

elif current_page == "เข้าสู่ระบบ":
    render_login_page()

# -------------------------------------------------------------------
# ปุ่มรีเซ็ตสต็อก (แสดงทุกหน้า แต่ต้องล็อกอิน)
# -------------------------------------------------------------------
st.divider()
st.markdown("### ⚠️ จัดการระบบ")
if st.session_state.get("logged_in"):
    if st.button("🧹 รีเซ็ตเลือดทั้งหมดเป็นศูนย์", type="primary", use_container_width=True):
        reset_all_stock(st.session_state.get("username", "admin"))
        flash("รีเซ็ตจำนวนเลือดทั้งหมดแล้ว ✅", "warning")
        _safe_rerun()
else:
    st.info("ต้องเข้าสู่ระบบก่อนจึงจะใช้งานปุ่มรีเซ็ตได้")
