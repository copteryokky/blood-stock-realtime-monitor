# app.py

import os
import time
from datetime import datetime, date, datetime as dt

import altair as alt
import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html

# ===== optional autorefresh =====
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # ถ้าไม่ได้ติดตั้งก็ไม่เป็นไร
    def st_autorefresh(*args, **kwargs):
        return None

# ===== DB funcs =====
from db import init_db, get_all_status, get_stock_by_blood, adjust_stock, reset_all_stock

# -----------------------------------------------------------------------------
# PAGE CONFIG & GLOBAL CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Blood Stock Real-time Monitor",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_CSS = """
<style>
/* ปรับ container ให้หายอัดขอบบน */
.block-container {
    padding-top: 1.0rem;
    padding-bottom: 3rem;
}

/* ฟอนต์ + heading */
html, body, [class*="css"] {
    font-family: "Sarabun", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
h1,h2,h3,h4 {
    letter-spacing: .2px;
}

/* พื้นหลังแบบ gradient พาสเทล (ใช้ใน landing + dashboard + entry) */
.stApp {
    background: radial-gradient(circle at top left, #ffe2e6 0%, #fff7f7 35%, #ffffff 100%);
}

/* Sidebar สไตล์คล้ายของเดิม */
[data-testid="stSidebar"] {
    background: #020617;
}
[data-testid="stSidebar"] .sidebar-title {
    color: #e5e7eb;
    font-weight: 800;
    font-size: 1.06rem;
    margin: 6px 0 10px 4px;
}
[data-testid="stSidebar"] .stButton>button {
    width: 100%;
    border-radius: 999px;
    padding: 0.55rem 0.9rem;
    font-weight: 600;
    border: 1px solid #e11d48;
    color: #e5e7eb;
    background: transparent;
}
[data-testid="stSidebar"] .stButton>button:hover {
    background: #e11d48;
    color: #ffffff;
}
[data-testid="stSidebar"] .stButton>button[data-selected="true"] {
    background: #f97373;
    color: #111827;
}

/* ปุ่ม logout มุมขวาบน */
.topbar-logout {
    position: fixed;
    right: 2.5rem;
    top: 0.9rem;
    z-index: 50;
}
.topbar-logout button {
    border-radius: 999px;
    padding: 0.45rem 1.4rem;
    font-weight: 600;
}

/* badge legend (ใช้ใน dashboard) */
.badge {
    display:inline-flex;
    align-items:center;
    gap:.4rem;
    padding:.25rem .5rem;
    border-radius:999px;
    background:#f3f4f6;
}
.legend-dot {
    width:.7rem;
    height:.7rem;
    border-radius:999px;
    display:inline-block;
}

/* DataFrame */
[data-testid="stDataFrame"] table {
    font-size: 14px;
}
[data-testid="stDataFrame"] th {
    font-size: 14px;
    font-weight: 700;
    color: #111827;
}

/* Sticky minimal banner (expiry summary) */
#expiry-banner {
    position: sticky;
    top: 0;
    z-index: 7;
    border-radius: 14px;
    margin: 6px 0 12px 0;
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
    padding:.2rem .55rem;
    border-radius:999px;
    font-weight:800;
    background:#ef4444;
    color:#fff;
    margin-left:.5rem;
}
#expiry-banner .chip.warn {
    background:#f59e0b;
}

/* Flash message */
.flash {
    position: fixed;
    top: 96px;
    right: 24px;
    z-index: 9999;
    color: #fff;
    padding: .7rem 1rem;
    border-radius: 12px;
    font-weight: 800;
    box-shadow: 0 10px 24px rgba(0,0,0,.18);
}
.flash.success {background:#16a34a;}
.flash.info    {background:#0ea5e9;}
.flash.warning {background:#f59e0b;}
.flash.error   {background:#ef4444;}

/* ---------------- Landing page styles ---------------- */
.landing-header {
    margin-top: 0.5rem;
    margin-bottom: 1.2rem;
}
.landing-subtitle {
    font-size: 0.9rem;
    color: #6b7280;
}

.landing-hero {
    border-radius: 28px;
    padding: 1.8rem 2.2rem;
    background: radial-gradient(circle at top left, #ffe4e6 0%, #fff7f7 55%, #ffffff 100%);
    box-shadow: 0 18px 55px rgba(248,113,113,.35);
    border: 1px solid rgba(248,113,113,.25);
}
.landing-pill {
    display:inline-flex;
    align-items:center;
    gap:.4rem;
    padding:.2rem .7rem;
    font-size:.78rem;
    border-radius:999px;
    background:#fee2e2;
    color:#b91c1c;
    font-weight:700;
}
.landing-title {
    font-size: 1.55rem;
    font-weight: 800;
    margin-top: .75rem;
    margin-bottom: .25rem;
}
.landing-sub {
    font-size: .95rem;
    color:#4b5563;
    margin-bottom: .8rem;
}
.landing-list {
    font-size: .9rem;
    color:#374151;
}
.landing-list li {
    margin-bottom: .15rem;
}
.landing-btn-row {
    margin-top: 1.1rem;
    display:flex;
    flex-wrap:wrap;
    gap:.7rem;
}
.landing-btn-primary {
    border-radius: 999px;
    background: #ef4444;
    color: #ffffff;
    font-weight: 700;
    padding: .55rem 1.4rem;
    border: none;
    font-size: .9rem;
}
.landing-btn-secondary {
    border-radius: 999px;
    border: 1px dashed #9ca3af;
    background: #ffffff;
    color: #4b5563;
    font-weight: 600;
    padding: .55rem 1.4rem;
    font-size: .85rem;
}

/* info cards */
.landing-grid {
    margin-top: 1.6rem;
}
.landing-card {
    background:#ffffff;
    border-radius: 22px;
    padding:1.4rem 1.6rem;
    box-shadow: 0 18px 40px rgba(15,23,42,.06);
    border:1px solid #e5e7eb;
}
.landing-card h3 {
    font-size: 1.02rem;
    margin-bottom: .5rem;
}

/* ระบบจัดการระบบ card */
.landing-system {
    margin-top: 1.7rem;
    border-radius: 22px;
    padding:1rem 1.4rem;
    background:#eff6ff;
    border:1px solid #bfdbfe;
    color:#1e3a8a;
    font-size:.88rem;
}

/* login tip badge */
.login-tip {
    display:flex;
    align-items:center;
    gap:.4rem;
    font-size:.8rem;
    color:#6b7280;
}


/* ---------------- Login page styles ---------------- */
.login-bg .stApp {
    background:#020617 !important;
}
.login-main {
    min-height: 100vh;
    display:flex;
    align-items:center;
    justify-content:center;
}
.login-title {
    text-align:center;
    font-size:1.6rem;
    font-weight:800;
    margin-bottom:.15rem;
}
.login-subtitle {
    text-align:center;
    font-size:.9rem;
    color:#6b7280;
    margin-bottom:1.3rem;
}

/* แปลง st.form ให้กลายเป็น card กลางจอ */
.login-card [data-testid="stForm"] {
    background:#f9fafb;
    padding:1.8rem 2.3rem 2.0rem 2.3rem;
    border-radius:26px;
    box-shadow:0 24px 60px rgba(15,23,42,.9);
    border:1px solid rgba(148,163,184,.6);
}
.login-card label {
    font-weight:600;
    font-size:.9rem;
}
.login-card .stTextInput>div>div>input {
    border-radius:999px;
}
.login-card .stPassword>div>div>input {
    border-radius:999px;
}
.login-card .stButton>button {
    border-radius:999px;
    width:100%;
    font-weight:700;
}
.login-card .primary-login button {
    background:#ef4444;
    border-color:#ef4444;
}
.login-card .primary-login button:hover {
    background:#dc2626;
    border-color:#dc2626;
}
.login-card .back-home button {
    margin-top:.4rem;
    background:#ffffff;
    color:#374151;
    border-color:#e5e7eb;
}
.login-card .back-home button:hover {
    background:#f3f4f6;
}

/* icon วงกลมด้านบนในการ login (โชว์ง่าย ๆ) */
.login-icon {
    width:44px;
    height:44px;
    border-radius:999px;
    background:#ef4444;
    display:flex;
    align-items:center;
    justify-content:center;
    color:#fff;
    font-size:1.3rem;
    margin:0 auto 0.8rem auto;
    box-shadow:0 10px 25px rgba(248,113,113,.5);
}
</style>
"""
st.markdown(BASE_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CONFIG & CONSTANTS
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# STATE
# -----------------------------------------------------------------------------
def _init_state():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("page", "landing")  # เริ่มต้นหน้า landing
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

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS (flash, compute, svg, expiry, db util)
# -----------------------------------------------------------------------------
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

      <circle cx="84" cy="10" r="7.5"
              fill="#eef2ff" stroke="#dbe0ea" stroke-width="3"/>
      <rect x="77.5" y="14" width="13" height="8" rx="3" fill="#e5e7eb"/>

      <path d="M16,34 C16,18 32,8 52,8 L116,8 C136,8 152,18 152,34
               L152,176 C152,195 136,206 116,206 L52,206 C32,206 16,195 16,176 Z"
            fill="#ffffff" stroke="#800000" stroke-width="3"/>

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

      <rect x="98" y="24" rx="10" ry="10" width="54" height="22"
            fill="#ffffff" stroke="#e5e7eb"/>
      <text x="125" y="40" text-anchor="middle"
            font-size="12" fill="#374151">{BAG_MAX} max</text>

      <text x="84" y="126" text-anchor="middle" font-size="32" font-weight="900"
            style="paint-order: stroke fill"
            stroke="#111827" stroke-width="4"
            fill="{letter_fill}">{blood_type}</text>
    </svg>
  </div>
</div>
"""


# ===== DB util =====
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()


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


# ===== Expiry util =====
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

# -----------------------------------------------------------------------------
# PAGE RENDER FUNCTIONS
# -----------------------------------------------------------------------------
def render_landing_page():
    """หน้าแรก (Landing) แบบภาพตัวอย่าง"""
    st.markdown(
        f"""
        <div class="landing-header">
            <h1>Blood Stock Real-time Monitor</h1>
            <div class="landing-subtitle">
                อัปเดตล่าสุด: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_main = st.columns([1, 1])[0]

    with col_main:
        st.markdown(
            """
            <div class="landing-hero">
              <div class="landing-pill">
                <span>🩸 Blood Stock Real-time Monitor</span>
                <span style="color:#6b7280;">สำหรับธนาคารเลือด / ห้อง Lab</span>
              </div>
              <div class="landing-title">
                แดชบอร์ดคลังเลือดแบบ Real-time<br/>ช่วยดูปริมาณสำรองและวันหมดอายุได้ทันที
              </div>
              <div class="landing-sub">
                ระบบออกแบบมาสำหรับธนาคารเลือดของโรงพยาบาล ช่วยติดตามสถานะคลังเลือดและผลิตภัณฑ์เลือดแบบอัปเดตทันที
              </div>
              <ul class="landing-list">
                <li>✓ ดูปริมาณคลังเลือดและส่วนผสมแบบแยกชนิดแบบทันที (LPRC, PRC, FFP, PC)</li>
                <li>✓ รองรับนำเข้าไฟล์ Excel / CSV จาก LIS หรือระบบเดิมของคุณ</li>
                <li>✓ แสดงเตือน Critical / Warning ช่วยให้จัดการการใช้เลือดอย่างเหมาะสม</li>
              </ul>
              <div class="landing-btn-row">
                <button class="landing-btn-primary" disabled>
                  เข้าสู่ระบบแดชบอร์ด
                </button>
                <button class="landing-btn-secondary" disabled>
                  สำหรับทีม Audit / QA
                </button>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ปุ่มจริง (ใช้ streamlit) ให้อยู่ใต้ hero -> เปลี่ยน page = login
    st.write("")
    col1, col2, col3 = st.columns([1.2, 1, 1.2])
    with col2:
        if st.button("เข้าสู่ระบบแดชบอร์ด", use_container_width=True):
            st.session_state["page"] = "login"
            _safe_rerun()

    # การ์ดตัวอย่างด้านล่าง 2 ใบ
    st.markdown('<div class="landing-grid">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            """
            <div class="landing-card">
              <h3>ภาพรวมคลังเลือดในแต่ละหมู่</h3>
              <p style="font-size:.85rem;color:#6b7280;margin-bottom:.45rem;">
                ภาพรวมสถานะคลังเลือด A / B / O / AB ให้เห็นได้ในมุมมองเดียว
              </p>
              <ul style="list-style:none;padding-left:0;font-size:.85rem;">
                <li>🟢 <b>เพียงพอ</b> – ปริมาณเลือดอยู่ในช่วงปลอดภัย</li>
                <li>🟠 <b>ใกล้หมด</b> – ควรเตรียมสั่งเพิ่ม หรือวางแผนการใช้</li>
                <li>🔴 <b>น้อยมาก</b> – เสี่ยงขาดเลือด ต้องเฝ้าระวังเป็นพิเศษ</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
            <div class="landing-card">
              <h3>ระดับแจ้งเตือนวันหมดอายุ</h3>
              <p style="font-size:.85rem;color:#6b7280;margin-bottom:.45rem;">
                ช่วยมองเห็นถุงเลือดที่กำลังจะหมดอายุล่วงหน้า ลดการทิ้งและปรับแผนการใช้เลือดได้ง่าย
              </p>
              <ul style="list-style:none;padding-left:0;font-size:.85rem;">
                <li><span style="color:#dc2626;font-weight:700;">Critical</span> &nbsp;– เหลือวันหมดอายุน้อยมาก ควรใช้ให้หมดโดยด่วน</li>
                <li><span style="color:#f97316;font-weight:700;">Warning</span> – เหลือเวลามากกว่าเล็กน้อย เหมาะสำหรับหมุนเวียนเลือดใหม่</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # การ์ด "จัดการระบบ"
    st.markdown(
        """
        <div class="landing-system">
          <b>⚙️ จัดการระบบ</b><br/>
          ต้องเข้าสู่ระบบคลังเลือดจริงก่อน จึงจะสามารถบันทึกข้อมูลคลังเลือด นำเข้าไฟล์ หรือรีเซ็ตจำนวนหน่วยได้
        </div>
        """,
        unsafe_allow_html=True,
    )

    # tip เล็ก ๆ ด้านล่าง
    st.write("")
    st.markdown(
        """
        <div class="login-tip">
          <span>💡</span>
          <span>เวอร์ชันทดลองใช้รหัสผ่าน <b>1234</b> เพื่อเข้าสู่ระบบแดชบอร์ด</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login_page():
    """หน้า Login แบบเต็มจอ (พื้นหลังมืด กล่องขาวกลางจอ)"""

    # override background เป็นโหมด login
    st.markdown('<style>.stApp{background:#020617 !important;}</style>', unsafe_allow_html=True)

    show_flash()  # เผื่อมี flash error จากรอบก่อน

    st.markdown('<div class="login-main">', unsafe_allow_html=True)
    col_left, col_center, col_right = st.columns([1, 1.2, 1])

    with col_center:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)

        st.markdown('<div class="login-icon">+</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">เข้าสู่ระบบคลังเลือด</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="login-subtitle">สำหรับเจ้าหน้าที่ธนาคารเลือด / ห้อง Lab ที่ต้องการบันทึกและติดตามคลังเลือดแบบ Real-time</div>',
            unsafe_allow_html=True,
        )

        with st.form("login_form_main", clear_on_submit=False):
            username = st.text_input("ชื่อผู้ใช้ (Username)", placeholder="เช่น thalab01 หรือชื่อย่อของคุณ")
            password = st.text_input("รหัสผ่าน (Password)", type="password", placeholder="ทดลองใช้: 1234")
            st.caption("แนะนำให้ใช้รหัสผ่านที่ได้รับจากหน่วยงานเท่านั้น – เวอร์ชันทดลองใช้รหัสผ่าน 1234 เพื่อเข้าสู่ระบบ")
            submitted = st.form_submit_button("เข้าสู่ระบบ")

        col_btn1, col_btn2 = st.columns([1.1, 1])
        with col_btn1:
            primary_clicked = st.button("เข้าสู่ระบบ", key="login_btn_dup", help="กดปุ่มนี้เพื่อเข้าสู่แดชบอร์ดจริง")
        with col_btn2:
            back_clicked = st.button("⬅ กลับไปหน้าแรก", key="login_back_btn")

        # logic กดปุ่ม (ทั้ง submit form หรือปุ่มซ้ำด้านล่าง)
        do_login = submitted or primary_clicked

        if do_login:
            if password == AUTH_PASSWORD:
                st.session_state["logged_in"] = True
                st.session_state["username"] = (username or "").strip() or "staff"
                st.session_state["page"] = "dashboard"
                flash("เข้าสู่ระบบสำเร็จ ✅", "success")
                _safe_rerun()
            else:
                flash("รหัสผ่านไม่ถูกต้อง (password = 1234)", "error")
                _safe_rerun()

        if back_clicked:
            st.session_state["page"] = "landing"
            _safe_rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_entry_page():
    """หน้า กรอกเลือด (ต้องล็อกอินก่อน)"""

    st.title("กรอกข้อมูลคลังเลือด (Entry)")
    st.caption("บันทึกและนำเข้าข้อมูลถุงเลือด อัปเดตเข้าฐานข้อมูลแบบ Real-time")

    show_flash()

    if not st.session_state["logged_in"]:
        st.warning("ต้องเข้าสู่ระบบก่อนจึงจะใช้งานเมนูนี้ได้")
        return

    st.subheader("กรอกเลือดทีละรายการ")

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

    # นำเข้าไฟล์ Excel / CSV
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

                    for c in ["created_at", "Exp date", "Unit number", "Group",
                              "Blood Components", "Status", "บันทึก"]:
                        if c not in df_file.columns:
                            df_file[c] = ""
                    df_file = df_file[
                        ["created_at", "Exp date", "Unit number", "Group",
                         "Blood Components", "Status", "บันทึก"]
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
                    _safe_rerun()
            except Exception as e:
                st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")

    # ตารางสรุป (แก้ไขได้)
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


def render_dashboard_page():
    """หน้าแดชบอร์ด (แสดงถุงเลือด, กราฟ, activity log)"""

    auto_update_booking_to_release()

    st.title("แดชบอร์ดคลังเลือด")
    st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    show_flash()

    if not st.session_state["logged_in"]:
        st.warning("ต้องเข้าสู่ระบบก่อนจึงจะใช้งานแดชบอร์ดนี้ได้")
        return

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


def render_reset_section():
    """ส่วนจัดการระบบด้านล่าง (รีเซ็ตสต็อก)"""
    st.divider()
    st.markdown("### ⚠️ จัดการระบบ")
    if st.session_state.get("logged_in"):
        if st.button("🧹 รีเซ็ตเลือดทั้งหมดเป็นศูนย์", type="primary", use_container_width=True):
            reset_all_stock(st.session_state.get("username", "admin"))
            flash("รีเซ็ตจำนวนเลือดทั้งหมดแล้ว ✅", "warning")
            _safe_rerun()
    else:
        st.info("ต้องเข้าสู่ระบบก่อนจึงจะใช้งานปุ่มรีเซ็ตได้")

# -----------------------------------------------------------------------------
# SIDEBAR NAV
# -----------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="sidebar-title">เมนู</div>', unsafe_allow_html=True)

        def nav_button(label, target_page):
            selected = st.session_state.get("page") == target_page
            if st.button(label, key=f"nav_{target_page}", use_container_width=True):
                st.session_state["page"] = target_page
                _safe_rerun()
            # mark selected ใน DOM
            st.markdown(
                f"""<script>
                const btns = window.parent.document.querySelectorAll('button[kind="secondary"]');
                btns.forEach(b => {{
                    if (b.innerText.trim() === "{label}") {{
                        b.dataset.selected = "{str(selected).lower()}";
                    }}
                }});
                </script>""",
                unsafe_allow_html=True,
            )

        nav_button("หน้าแรก", "landing")
        nav_button("แดชบอร์ดคลังเลือด", "dashboard")
        nav_button("กรอกเลือด", "entry")

        st.write("")
        if st.session_state.get("logged_in"):
            if st.button("ออกจากระบบ", key="nav_logout", use_container_width=True):
                st.session_state["logged_in"] = False
                st.session_state["username"] = ""
                st.session_state["page"] = "landing"
                flash("ออกจากระบบเรียบร้อยแล้ว ✅", "info")
                _safe_rerun()
        else:
            if st.button("เข้าสู่ระบบ", key="nav_login", use_container_width=True):
                st.session_state["page"] = "login"
                _safe_rerun()

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
def main():
    render_sidebar()

    # ปุ่ม logout มุมขวาบน (เฉพาะเมื่อ login อยู่) บนหน้า landing / dashboard / entry
    if st.session_state.get("logged_in") and st.session_state.get("page") != "login":
        with st.container():
            st.markdown(
                '<div class="topbar-logout">',
                unsafe_allow_html=True,
            )
            if st.button("ออกจากระบบแล้ว", key="top_logout"):
                st.session_state["logged_in"] = False
                st.session_state["username"] = ""
                st.session_state["page"] = "landing"
                flash("ออกจากระบบเรียบร้อยแล้ว ✅", "info")
                _safe_rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    page = st.session_state.get("page", "landing")

    if page == "landing":
        render_landing_page()
    elif page == "login":
        render_login_page()
    elif page == "entry":
        render_entry_page()
        render_reset_section()
    elif page == "dashboard":
        render_dashboard_page()
        render_reset_section()
    else:
        st.session_state["page"] = "landing"
        _safe_rerun()


if __name__ == "__main__":
    main()
