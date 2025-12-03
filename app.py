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

st.markdown(
    """
<style>
.block-container{
    padding-top:1.0rem;
    max-width:1180px;
}
body{
    background:#fefefe;
}
h1,h2,h3{letter-spacing:.2px}

/* badge legend */
.badge{
    display:inline-flex;
    align-items:center;
    gap:.4rem;
    padding:.25rem .5rem;
    border-radius:999px;
    background:#f3f4f6
}
.legend-dot{
    width:.7rem;
    height:.7rem;
    border-radius:999px;
    display:inline-block
}

/* Sidebar */
[data-testid="stSidebar"]{
    background:#111827;
}
[data-testid="stSidebar"] .sidebar-title{
    color:#e5e7eb;
    font-weight:800;
    font-size:1.06rem;
    margin:6px 0 10px 4px
}
[data-testid="stSidebar"] .user-card{
    display:flex;
    align-items:center;
    gap:.8rem;
    background:linear-gradient(135deg,#1f2937,#111827);
    border:1px solid #4b5563;
    border-radius:14px;
    padding:.75rem .9rem;
    margin:.5rem .2rem 1rem .2rem;
    box-shadow:0 8px 22px rgba(0,0,0,.25)
}
[data-testid="stSidebar"] .user-avatar{
    width:40px;
    height:40px;
    border-radius:999px;
    background:#ef4444;
    color:#fff;
    font-weight:900;
    display:flex;
    align-items:center;
    justify-content:center;
    letter-spacing:.5px;
    box-shadow:0 0 0 3px rgba(239,68,68,.25)
}
[data-testid="stSidebar"] .user-meta{
    display:flex;
    flex-direction:column;
    line-height:1.1
}
[data-testid="stSidebar"] .user-meta .label{
    font-size:.75rem;
    color:#cbd5e1
}
[data-testid="stSidebar"] .user-meta .name{
    font-size:1rem;
    color:#fff;
    font-weight:800
}
[data-testid="stSidebar"] .stButton>button{
    width:100%;
    background:#ffffff;
    color:#111827;
    border:1px solid #cbd5e1;
    border-radius:12px;
    font-weight:700;
    justify-content:flex-start
}
[data-testid="stSidebar"] .stButton>button:hover{
    background:#f3f4f6
}

/* DataFrame */
[data-testid="stDataFrame"] table {font-size:14px;}
[data-testid="stDataFrame"] th {
    font-size:14px;
    font-weight:700;
    color:#111827;
}

/* Sticky minimal banner */
#expiry-banner{
    position:sticky;
    top:0;
    z-index:1000;
    border-radius:14px;
    margin:6px 0 12px 0;
    padding:12px 14px;
    border:2px solid #991b1b;
    background:linear-gradient(180deg,#fee2e2,#ffffff);
    box-shadow:0 10px 24px rgba(153,27,27,.12)
}
#expiry-banner .title{
    font-weight:900;
    font-size:1.02rem;
    color:#7f1d1d
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
    margin-left:.5rem
}
#expiry-banner .chip.warn{background:#f59e0b}

/* Flash */
.flash{
    position:fixed;
    top:110px;
    right:24px;
    z-index:9999;
    color:#fff;
    padding:.7rem 1rem;
    border-radius:12px;
    font-weight:800;
    box-shadow:0 10px 24px rgba(0,0,0,.18)
}
.flash.success{background:#16a34a}
.flash.info{background:#0ea5e9}
.flash.warning{background:#f59e0b}
.flash.error{background:#ef4444}

/* ===========================
   Landing page (ก่อนล็อกอิน)
   =========================== */
.landing-card-outer{
    background:#ffffff;
    border-radius:18px;
    padding:1.2rem 1.6rem 1.4rem;
    margin-top:.6rem;
    box-shadow:0 22px 45px rgba(15,23,42,.06);
    border:1px solid #f3f4f6;
}
.landing-header-left{
    display:flex;
    align-items:center;
    gap:.6rem;
}
.landing-header-icon{
    width:30px;
    height:30px;
    border-radius:999px;
    background:#fee2e2;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:16px;
}
.landing-header-title{
    font-size:1.05rem;
    font-weight:700;
    color:#111827;
}
.landing-header-updated{
    text-align:right;
    font-size:.86rem;
    color:#6b7280;
    margin-top:.3rem;
}
.landing-hero-inner{
    display:flex;
    gap:2.0rem;
    align-items:stretch;
    margin-top:1.0rem;
    padding:1.3rem 1.4rem 1.5rem;
    border-radius:16px;
    background:linear-gradient(90deg,#fff1f2,#fff7ed);
    position:relative;
    overflow:hidden;
}
.hero-left-block{
    flex:1.6;
    z-index:1;
}
.hero-main-title{
    font-size:1.6rem;
    font-weight:800;
    color:#111827;
    margin:0 0 .3rem;
}
.hero-main-sub{
    font-size:1rem;
    font-weight:500;
    color:#374151;
    margin-bottom:.9rem;
}
.hero-bullets{
    list-style:none;
    padding:0;
    margin:0;
    font-size:.9rem;
    color:#4b5563;
}
.hero-bullets li{
    display:flex;
    gap:.45rem;
    margin-bottom:.25rem;
}
.hero-bullets li span.icon{
    font-size:.85rem;
    margin-top:.1rem;
}
.hero-cta-row{
    margin-top:1.2rem;
}
.hero-cta-row .hero-btn-primary [data-testid="stButton"]>button{
    border-radius:999px;
    padding:.7rem 1.6rem;
    font-weight:700;
    font-size:.95rem;
    background:#ef4444;
    border:1px solid #ef4444;
    color:#ffffff;
    box-shadow:0 14px 30px rgba(248,113,113,.55);
}
.hero-cta-row .hero-btn-primary [data-testid="stButton"]>button:hover{
    background:#dc2626;
    border-color:#dc2626;
    transform:translateY(-1px);
}
.hero-cta-row .hero-btn-secondary [data-testid="stButton"]>button{
    border-radius:999px;
    padding:.7rem 1.6rem;
    font-weight:600;
    font-size:.95rem;
    background:#ffffff;
    border:1px solid #e5e7eb;
    color:#111827;
    box-shadow:0 10px 24px rgba(148,163,184,.18);
}
.hero-cta-row .hero-btn-secondary [data-testid="stButton"]>button:hover{
    border-color:#fecaca;
    transform:translateY(-1px);
}
.landing-hero-footer{
    text-align:right;
    font-size:.8rem;
    color:#9ca3af;
    margin-top:.5rem;
}

/* Illustration ขวามือ */
.hero-right-block{
    flex:1;
    display:flex;
    align-items:center;
    justify-content:center;
}
.hero-illust{
    position:relative;
    width:230px;
    height:180px;
    border-radius:28px;
    background:linear-gradient(145deg,#fee2e2,#fecaca);
    box-shadow:0 20px 45px rgba(248,113,113,.55);
    display:flex;
    align-items:center;
    justify-content:center;
}
.hero-illust-inner{
    width:78%;
    height:72%;
    border-radius:20px;
    background:#ffffff;
    box-shadow:0 10px 26px rgba(148,163,184,.55);
    position:relative;
    padding:.8rem .9rem;
}
.hero-chart-line{
    position:absolute;
    left:14px;
    right:14px;
    top:52%;
    height:2px;
    background:linear-gradient(90deg,#fecaca,#fb7185);
}
.hero-chart-line::before{
    content:"";
    position:absolute;
    left:8%;
    top:-14px;
    width:40%;
    height:2px;
    border-top:3px solid #fb7185;
    border-radius:999px;
}
.hero-chart-line::after{
    content:"";
    position:absolute;
    left:48%;
    top:-5px;
    width:35%;
    height:2px;
    border-top:3px solid #b91c1c;
    border-radius:999px;
}
.hero-bag{
    position:absolute;
    width:44px;
    height:72px;
    border-radius:18px;
    background:#ef4444;
    box-shadow:0 12px 24px rgba(185,28,28,.7);
}
.hero-bag::before{
    content:"";
    position:absolute;
    inset:4px;
    border-radius:15px;
    background:#fee2e2;
}
.hero-bag::after{
    content:"";
    position:absolute;
    left:50%;
    transform:translateX(-50%);
    bottom:10px;
    width:14px;
    height:20px;
    border-radius:999px;
    background:#ef4444;
}
.hero-bag-left{
    right:82px;
    bottom:-18px;
}
.hero-bag-right{
    right:26px;
    bottom:4px;
}

/* bottom cards */
.landing-bottom-grid{
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:1.1rem;
    margin-top:1.6rem;
}
.landing-bottom-card{
    background:#ffffff;
    border-radius:18px;
    border:1px solid #f3f4f6;
    box-shadow:0 14px 32px rgba(148,163,184,.12);
    padding:1.0rem 1.3rem 1.1rem;
}
.landing-bottom-title{
    font-size:1.05rem;
    font-weight:700;
    color:#111827;
    margin-bottom:.55rem;
}
.landing-bottom-sub{
    font-size:.9rem;
    color:#4b5563;
    margin-bottom:.6rem;
}
.blood-overview-line{
    font-size:.92rem;
    font-weight:600;
    margin-bottom:.3rem;
}
.blood-overview-tags .tag{
    display:flex;
    align-items:center;
    gap:.35rem;
    font-size:.86rem;
    color:#4b5563;
    margin-bottom:.15rem;
}
.tag-dot{
    width:9px;
    height:9px;
    border-radius:999px;
    display:inline-block;
}
.tag-dot.green{background:#22c55e;}
.tag-dot.amber{background:#f59e0b;}
.tag-dot.red{background:#ef4444;}

.landing-alert-row{
    display:flex;
    gap:.5rem;
    align-items:flex-start;
    font-size:.88rem;
    margin-bottom:.3rem;
}
.alert-label{
    min-width:70px;
    font-weight:700;
}
.alert-label.critical{color:#dc2626;}
.alert-label.warning{color:#f97316;}
.alert-text{color:#4b5563;}

/* การ์ดจัดการระบบ */
.system-manage-card{
    margin-top:1.8rem;
    background:#eff6ff;
    border-radius:16px;
    border:1px solid #dbeafe;
    padding:1rem 1.2rem 1.2rem;
}
.system-manage-title{
    font-weight:700;
    margin-bottom:.4rem;
    font-size:1.02rem;
}
.system-manage-card [data-testid="stButton"]>button{
    border-radius:999px;
    font-weight:700;
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
    # ให้หน้าแรกเป็น "หน้าหลัก" = landing page
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

    # ถ้า total = 0 ให้น้ำอยู่ต่ำสุด (แทบมองไม่เห็น)
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
# LANDING PAGE (ก่อนล็อกอิน)
# --------------------------------
def render_public_landing():
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # การ์ดใหญ่ด้านบนเหมือนภาพตัวอย่าง
    st.markdown('<div class="landing-card-outer">', unsafe_allow_html=True)

    h_left, h_right = st.columns([4, 2])
    with h_left:
        st.markdown(
            """
            <div class="landing-header-left">
              <div class="landing-header-icon">🩸</div>
              <div class="landing-header-title">Blood Stock Real-time Monitor</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with h_right:
        st.markdown(
            f'<div class="landing-header-updated">อัปเดตล่าสุด: <strong>{now_str}</strong></div>',
            unsafe_allow_html=True,
        )

    # hero ภายใน
    st.markdown('<div class="landing-hero-inner">', unsafe_allow_html=True)
    left, right = st.columns([1.9, 1.4])

    with left:
        st.markdown(
            """
            <div class="hero-left-block">
              <div class="hero-main-title">Blood Stock Real-time Monitor</div>
              <div class="hero-main-sub">แดชบอร์ดคลังเลือดแบบ Real-time ของโรงพยาบาล</div>
              <ul class="hero-bullets">
                <li><span class="icon">✓</span><span>ดูปริมาณคลังเลือดและส่วนผสมแบบอัปเดตทันที</span></li>
                <li><span class="icon">✓</span><span>รองรับ LPRC, PRC, FFP, PC และ Cryo</span></li>
                <li><span class="icon">✓</span><span>แจ้งเตือน Critical / Warning ช่วยบริหารการใช้เลือด</span></li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="hero-cta-row">', unsafe_allow_html=True)
        cta1, cta2 = st.columns([1, 1])
        with cta1:
            st.markdown('<div class="hero-btn-primary">', unsafe_allow_html=True)
            if st.button("เข้าสู่ระบบแดชบอร์ด", key="hero_login", use_container_width=True):
                st.session_state["page"] = "เข้าสู่ระบบ"
                _safe_rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with cta2:
            st.markdown('<div class="hero-btn-secondary">', unsafe_allow_html=True)
            st.button("ดูตัวอย่างหน้าจอ Lab", key="hero_preview", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown(
            """
            <div class="hero-right-block">
              <div class="hero-illust">
                <div class="hero-illust-inner">
                  <div class="hero-chart-line"></div>
                </div>
                <div class="hero-bag hero-bag-left"></div>
                <div class="hero-bag hero-bag-right"></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)  # ปิด landing-hero-inner
    st.markdown(
        '<div class="landing-hero-footer">สำหรับทีมธนาคารเลือด ห้อง Lab และฝ่ายประกันคุณภาพโรงพยาบาล</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)  # ปิด landing-card-outer

    # การ์ด 2 ใบด้านล่าง
    st.markdown(
        """
        <div class="landing-bottom-grid">
          <div class="landing-bottom-card">
            <div class="landing-bottom-title">ภาพรวมคลังเลือดในแต่ละหมู่</div>
            <div class="landing-bottom-sub">ภาพรวมสถานะคลังเลือด A / B / O / AB ในมุมมองเดียว</div>
            <div class="blood-overview-line">A / B / O / AB</div>
            <div class="blood-overview-tags">
              <div class="tag"><span class="tag-dot green"></span>เพียงพอ – ปริมาณเลือดอยู่ในช่วงปลอดภัย</div>
              <div class="tag"><span class="tag-dot amber"></span>ใกล้หมด – ควรเตรียมสั่งเพิ่ม หรือวางแผนการใช้</div>
              <div class="tag"><span class="tag-dot red"></span>น้อยมาก – เสี่ยงขาดสต็อก ต้องเฝ้าระวังเป็นพิเศษ</div>
            </div>
          </div>

          <div class="landing-bottom-card">
            <div class="landing-bottom-title">ระดับแจ้งเตือนวันหมดอายุ</div>
            <div class="landing-bottom-sub">ช่วยมองเห็นเลือดที่ใกล้หมดอายุและวางแผนการใช้ล่วงหน้า</div>

            <div class="landing-alert-row">
              <div class="alert-label critical">Critical</div>
              <div class="alert-text">เลือดใกล้หมดอายุมาก ควรเร่งใช้หรือตรวจสอบแนวทางจัดการ</div>
            </div>
            <div class="landing-alert-row">
              <div class="alert-label warning">Warning</div>
              <div class="alert-text">เตือนล่วงหน้าให้ทีมงานวางแผนใช้เลือดให้เหมาะสมภายในไม่กี่วัน</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
        st.session_state["page"] = "เข้าสู่ระบบ" if not st.session_state["logged_in"] else "ออกจากระบบ"
        _safe_rerun()

    if st.session_state["page"] == "เข้าสู่ระบบ" and not st.session_state["logged_in"]:
        st.markdown("### เข้าสู่ระบบ")
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input("Username", key="login_user", placeholder="พิมพ์ชื่อผู้ใช้ได้เลย")
            p = st.text_input("Password", key="login_pwd", type="password", placeholder="ใส่รหัส = 1234")
            sub = st.form_submit_button("Login", type="primary", use_container_width=True)
        if sub:
            if p == AUTH_PASSWORD:
                st.session_state["logged_in"] = True
                st.session_state["username"] = (u or "").strip() or "staff"
                st.session_state["page"] = "กรอกเลือด"
                _safe_rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง (password = 1234)")

    if st.session_state["page"] == "ออกจากระบบ" and st.session_state["logged_in"]:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["page"] = "หน้าหลัก"
        _safe_rerun()

# --------------------------------
# FLASH (ใช้ได้ทุกหน้า)
# --------------------------------
show_flash()

# --------------------------------
# PAGE: กรอกเลือด
# --------------------------------
if st.session_state["page"] == "กรอกเลือด":
    st.title("Blood Stock Real-time Monitor")
    st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    if not st.session_state["logged_in"]:
        st.warning("ต้องล็อกอินก่อนจึงจะใช้งานเมนูนี้ได้")
    else:
        st.subheader("กรอกเลือด")

        # ---- แบบฟอร์มกรอกทีละรายการ ----
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
            # token ไฟล์เพื่อกันนำเข้าซ้ำทุกครั้งที่มี rerun
            token = (up.name, up.size)
            if st.session_state.get("last_upload_token") != token:
                st.session_state["last_upload_token"] = token

                # อ่านไฟล์
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
                        # mapping header ให้มาตรงกับคอลัมน์หลัก
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

                        # แปลงสถานะจากอังกฤษ -> ไทย
                        status_map_en2th = {
                            "Available": "ว่าง",  # พร้อมใช้
                            "ReadyToIssue": "จอง",  # จอง
                            "Released": "จ่ายแล้ว",  # จ่ายแล้ว
                            "Expired": "Exp",
                            "ReleasedExpired": "Exp",
                            "Out": "จ่ายแล้ว",
                        }
                        if "Status" in df_file.columns:
                            df_file["Status"] = df_file["Status"].map(
                                lambda s: status_map_en2th.get(str(s).strip(), str(s).strip())
                            )

                        # เติมคอลัมน์ที่จำเป็น
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

                        # คอลัมน์สถานะ(สี)
                        df_file["สถานะ(สี)"] = df_file["Status"].map(
                            lambda s: STATUS_COLOR.get(str(s), str(s))
                        )

                        # ถ้าเลือก "แทนที่ทั้งหมด" ให้ล้าง entries + reset stock ก่อน
                        replace_mode = mode_merge.startswith("แทนที่")
                        if replace_mode:
                            st.session_state["entries"] = pd.DataFrame(columns=ENTRY_COLS)
                            st.session_state["activity"] = []
                            # reset stock ใน db ให้เป็นศูนย์แล้วค่อย build ใหม่
                            reset_all_stock(st.session_state.get("username", "admin"))

                        # เตรียม list สำหรับสร้าง DataFrame ใหม่
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

                            # อัปเดตคลัง: สำหรับไฟล์ snapshot เรานับเฉพาะ "ว่าง" และ "หลุดจอง"
                            try:
                                if stt in ["ว่าง", "หลุดจอง"]:
                                    apply_stock_change(
                                        g, comp, +1, nt or "import", st.session_state.get("username") or "admin"
                                    )
                                    add_activity("INBOUND", g, comp, +1, f"import: {nt}")
                                elif stt in ["จ่ายแล้ว"]:
                                    # เป็นสถานะที่ออกไปแล้ว ไม่เพิ่มสต็อก
                                    add_activity("OUTBOUND", g, comp, 0, f"import: {nt}")
                                else:
                                    # Exp / จอง ฯลฯ ที่ไม่อยากให้ไปเพิ่มสต็อก
                                    add_activity("INFO", g, comp, 0, f"import: {nt}")
                                applied += 1
                            except Exception:
                                failed += 1

                        new_df = pd.DataFrame(new_rows, columns=ENTRY_COLS)

                        if replace_mode:
                            # ต้องการให้จำนวนแถวตรงกับไฟล์เป๊ะ ๆ
                            st.session_state["entries"] = new_df
                        else:
                            # โหมด merge: รวมกับของเดิม แล้วลบแถวซ้ำออกตาม Unit+Group+Component
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

        # เพิ่มคอลัมน์ลำดับ (index ที่มองเห็น)
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

        # ถ้ามีการแก้ไขตาราง -> sync กลับไปที่ session_state["entries"]
        if not edited.equals(df_vis):
            out = edited.copy()
            # ตัดคอลัมน์ "ลำดับ" ทิ้งก่อนเก็บจริง
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
            keep = ENTRY_COLS
            st.session_state["entries"] = out[keep].reset_index(drop=True)
            flash("อัปเดตตารางแล้ว ✅")
            _safe_rerun()

# --------------------------------
# PAGE: หน้าหลัก
# --------------------------------
elif st.session_state["page"] == "หน้าหลัก":
    if not st.session_state.get("logged_in"):
        # Landing page (ก่อนล็อกอิน) ตามดีไซน์ภาพ
        render_public_landing()
    else:
        # Dashboard หลังล็อกอิน (ใช้โค้ดเดิม)
        auto_update_booking_to_release()

        st.title("Blood Stock Real-time Monitor")
        st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

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
                y=alt.Y(
                    "units:Q",
                    title="จำนวนหน่วย (unit)",
                    scale=alt.Scale(domainMin=0, domainMax=ymax),
                ),
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

        # ตารางสรุปหน่วยตาม product type
        st.dataframe(
            df.sort_values(by="product_type")[["product_type", "units"]],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### รายการบันทึกความเคลื่อนไหว (Activity Log)")
        if st.session_state["activity"]:
            st.dataframe(
                pd.DataFrame(st.session_state["activity"]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("ยังไม่มีรายการความเคลื่อนไหว")

# --------------------------------
# การ์ด ⚙️ จัดการระบบ  (แสดงทุกหน้า)
# --------------------------------
st.markdown(
    '<div class="system-manage-card"><div class="system-manage-title">⚙️ การจัดการระบบ</div>',
    unsafe_allow_html=True,
)

if st.session_state.get("logged_in"):
    st.write(
        "รีเซ็ตจำนวนหน่วยเลือดทั้งหมดในฐานข้อมูลให้เป็นศูนย์ "
        "เหมาะสำหรับเริ่มต้นระบบใหม่หรือทดสอบการทำงาน (ควรใช้ด้วยความระมัดระวัง)"
    )
    if st.button("🧹 รีเซ็ตเลือดทั้งหมดเป็นศูนย์", type="primary", use_container_width=True):
        reset_all_stock(st.session_state.get("username", "admin"))
        flash("รีเซ็ตจำนวนเลือดทั้งหมดแล้ว ✅", "warning")
        _safe_rerun()
else:
    st.write("ต้องเข้าสู่ระบบก่อนจึงจะใช้งานฟังก์ชันรีเซ็ตระบบได้")

st.markdown("</div>", unsafe_allow_html=True)
