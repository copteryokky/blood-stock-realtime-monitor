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
    layout="wide"
)

# ---------- Global CSS (รวม Landing + Login + Sidebar + Table) ----------
st.markdown(
    """
<style>
.block-container{padding-top:1.0rem;}
h1,h2,h3{letter-spacing:.2px}

/* badge legend */
.badge{display:inline-flex;align-items:center;gap:.4rem;padding:.25rem .5rem;border-radius:999px;background:#f3f4f6}
.legend-dot{width:.7rem;height:.7rem;border-radius:999px;display:inline-block}

/* Sidebar */
[data-testid="stSidebar"]{background:#2e343a;}
[data-testid="stSidebar"] .sidebar-title{color:#e5e7eb;font-weight:800;font-size:1.06rem;margin:6px 0 10px 4px}
[data-testid="stSidebar"] .user-card{display:flex;align-items:center;gap:.8rem;background:linear-gradient(135deg,#39424a,#2f343a);border:1px solid #475569;border-radius:14px;padding:.75rem .9rem;margin:.5rem .2rem 1rem .2rem;box-shadow:0 8px 22px rgba(0,0,0,.25)}
[data-testid="stSidebar"] .user-avatar{width:40px;height:40px;border-radius:999px;background:#ef4444;color:#fff;font-weight:900;display:flex;align-items:center;justify-content:center;letter-spacing:.5px;box-shadow:0 0 0 3px rgba(239,68,68,.25)}
[data-testid="stSidebar"] .user-meta{display:flex;flex-direction:column;line-height:1.1}
[data-testid="stSidebar"] .user-meta .label{font-size:.75rem;color:#cbd5e1}
[data-testid="stSidebar"] .user-meta .name{font-size:1rem;color:#fff;font-weight:800}
[data-testid="stSidebar"] .stButton>button{width:100%;background:#ffffff;color:#111827;border:1px solid #cbd5e1;border-radius:12px;font-weight:700;justify-content:flex-start}
[data-testid="stSidebar"] .stButton>button:hover{background:#f3f4f6}

/* DataFrame */
[data-testid="stDataFrame"] table {font-size:14px;}
[data-testid="stDataFrame"] th {font-size:14px; font-weight:700; color:#111827;}

/* Sticky minimal banner */
#expiry-banner{position:sticky;top:0;z-index:1000;border-radius:14px;margin:6px 0 12px 0;padding:12px 14px;border:2px solid #991b1b;background:linear-gradient(180deg,#fee2e2,#ffffff);box-shadow:0 10px 24px rgba(153,27,27,.12)}
#expiry-banner .title{font-weight:900;font-size:1.02rem;color:#7f1d1d}
#expiry-banner .chip{display:inline-flex;align-items:center;gap:.35rem;padding:.2rem .55rem;border-radius:999px;font-weight:800;background:#ef4444;color:#fff;margin-left:.5rem}
#expiry-banner .chip.warn{background:#f59e0b}

/* Flash */
.flash{position:fixed; top:110px; right:24px; z-index:9999; color:#fff; padding:.7rem 1rem; border-radius:12px; font-weight:800; box-shadow:0 10px 24px rgba(0,0,0,.18)}
.flash.success{background:#16a34a}
.flash.info{background:#0ea5e9}
.flash.warning{background:#f59e0b}
.flash.error{background:#ef4444}

/* SVG ถุงเลือด (ใช้ร่วมกันทุกหน้า) */
.bag-wrap{display:flex;flex-direction:column;align-items:center;gap:10px;
          font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial;}
.bag{transition:transform .18s ease, filter .18s ease;}
.bag:hover{transform:translateY(-2px);
           filter:drop-shadow(0 10px 22px rgba(0,0,0,.12));}
.wave-layer{mix-blend-mode:screen;opacity:.92;}
@keyframes wave-move-1{0%{transform:translateX(0);}100%{transform:translateX(-80px);}}
@keyframes wave-move-2{0%{transform:translateX(0);}100%{transform:translateX(-60px);}}

/* Landing Page */
.landing-hero{min-height:80vh;display:flex;flex-direction:column;justify-content:center;align-items:center;background:radial-gradient(circle at top,#fee2e2 0,#ffffff 55%,#e0f2fe 100%);padding:2.5rem 1.5rem;}
.landing-inner{max-width:980px;margin:0 auto;display:grid;grid-template-columns:minmax(0,6fr) minmax(0,5fr);gap:2.5rem;align-items:center;}
.landing-badge{display:inline-flex;align-items:center;gap:.4rem;padding:.25rem .7rem;border-radius:999px;background:rgba(248,250,252,.9);font-size:.9rem;color:#b91c1c;font-weight:700;border:1px solid rgba(248,113,113,.4);}
.landing-title{font-size:2.1rem;font-weight:900;color:#111827;margin-top:.9rem;margin-bottom:.6rem;}
.landing-subtitle{font-size:1rem;color:#4b5563;margin-bottom:1.2rem;}
.landing-list{list-style:none;padding-left:0;margin:0 0 1.4rem 0;color:#111827;}
.landing-list li{display:flex;align-items:flex-start;gap:.55rem;margin-bottom:.35rem;font-size:.96rem;}
.landing-list li span.icon{margin-top:.1rem;}
.landing-cta{display:flex;flex-wrap:wrap;gap:.9rem;align-items:center;margin-top:.4rem;}
.landing-cta small{color:#4b5563;font-size:.86rem;}
.landing-pill{display:inline-flex;align-items:center;gap:.35rem;padding:.3rem .7rem;border-radius:999px;background:rgba(15,23,42,.85);color:#e5e7eb;font-size:.78rem;margin-top:.45rem;}
.landing-pill strong{color:#f97316;}
.landing-card{position:relative;background:rgba(255,255,255,.96);border-radius:1.4rem;padding:1.4rem 1.6rem;box-shadow:0 18px 45px rgba(15,23,42,.22);border:1px solid rgba(148,163,184,.5);}
.landing-card h3{font-size:1.05rem;margin:0 0 .3rem 0;color:#0f172a;font-weight:800;}
.landing-metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem;margin-top:.7rem;}
.landing-metric{background:#f9fafb;border-radius:.9rem;padding:.65rem .7rem;display:flex;flex-direction:column;gap:.1rem;}
.landing-metric-label{font-size:.8rem;color:#6b7280;}
.landing-metric-value{font-weight:800;font-size:1.1rem;color:#0f172a;}
.landing-metric-tag{font-size:.78rem;color:#16a34a;}
.landing-tag-muted{color:#f97316;}
.landing-mini-badges{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.7rem;}
.landing-mini-badges span{font-size:.75rem;border-radius:999px;padding:.18rem .55rem;background:#eff6ff;color:#1d4ed8;}
.landing-note{margin-top:.9rem;font-size:.76rem;color:#64748b;}

/* Login Page */
.login-wrap{min-height:90vh;display:flex;align-items:center;justify-content:center;background:radial-gradient(circle at top,#fee2e2 0,#ffffff 55%,#e0f2fe 100%);padding:1.5rem .75rem;}
.login-card{max-width:920px;width:100%;background:rgba(255,255,255,.98);border-radius:1.5rem;box-shadow:0 24px 60px rgba(15,23,42,.35);display:grid;grid-template-columns:minmax(0,5fr) minmax(0,4.5fr);overflow:hidden;border:1px solid rgba(148,163,184,.55);}
.login-left{background:radial-gradient(circle at top,#b91c1c,#7f1d1d);color:#fee2e2;padding:1.8rem 1.7rem;display:flex;flex-direction:column;justify-content:space-between;}
.login-logo{display:inline-flex;align-items:center;gap:.55rem;font-size:.95rem;font-weight:700;background:rgba(248,250,252,.12);padding:.35rem .7rem;border-radius:999px;}
.login-logo span.icon{font-size:1.1rem;}
.login-left h2{font-size:1.5rem;margin:.9rem 0 .5rem 0;font-weight:900;}
.login-left p{font-size:.92rem;opacity:.95;margin-bottom:1.1rem;}
.login-bullets{list-style:none;padding-left:0;margin:0;}
.login-bullets li{display:flex;gap:.45rem;font-size:.83rem;margin-bottom:.35rem;opacity:.96;}
.login-bullets span.icon{margin-top:.08rem;}
.login-stat-pill{margin-top:1.1rem;display:inline-flex;align-items:center;gap:.4rem;font-size:.8rem;background:rgba(15,23,42,.35);padding:.3rem .7rem;border-radius:999px;}
.login-right{padding:1.8rem 1.8rem 1.6rem 1.8rem;display:flex;flex-direction:column;justify-content:center;}
.login-title{font-size:1.5rem;font-weight:900;color:#111827;margin-bottom:.25rem;}
.login-subtitle{font-size:.95rem;color:#4b5563;margin-bottom:1.1rem;}
.login-form label{font-size:.9rem;font-weight:600;color:#374151;margin-bottom:.2rem;display:block;}
.login-form .hint{font-size:.8rem;color:#6b7280;margin-top:.45rem;}
.login-footer-note{margin-top:1.1rem;font-size:.8rem;color:#6b7280;}

@media (max-width:900px){
  .landing-inner{grid-template-columns:minmax(0,1fr);gap:1.8rem;text-align:center;}
  .landing-card{order:-1;}
  .landing-cta{justify-content:center;}
  .login-card{grid-template-columns:minmax(0,1fr);}
  .login-left{display:none;}
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
    st.session_state.setdefault("page", "หน้าหลัก")   # หน้าแรกหลังล็อกอิน
    st.session_state.setdefault("selected_bt", None)
    st.session_state.setdefault("flash", None)
    st.session_state.setdefault("last_upload_token", None)
    st.session_state.setdefault("view", "landing")     # landing / login / app

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
          <!-- คลื่นหลัก -->
          <g class="wave-layer" style="animation:wave-move-1 {wave_speed1}s linear infinite;">
            <use href="#wave1-{gid}" fill="url(#liquid-{gid})" x="0"/>
            <use href="#wave1-{gid}" fill="url(#liquid-{gid})" x="80"/>
            <use href="#wave1-{gid}" fill="url(#liquid-{gid})" x="160"/>
          </g>
          <!-- คลื่นรอง -->
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

# --------------------------------
# LANDING PAGE
# --------------------------------
def render_landing():
    st.markdown(
        """
<div class="landing-hero">
  <div class="landing-inner">
    <div>
      <div class="landing-badge">
        <span>🩸 Blood Stock Real-time Monitor</span>
        <span>สำหรับทีมธนาคารเลือดและห้อง Lab</span>
      </div>
      <h1 class="landing-title">
        แดชบอร์ดคลังเลือดแบบ Real-time<br>ช่วยดูปริมาณสำรองและวันหมดอายุได้ทันที
      </h1>
      <p class="landing-subtitle">
        ระบบนี้ออกแบบมาเพื่อทีมธนาคารเลือด ห้อง Lab และงานระบบคุณภาพของโรงพยาบาล
        ใช้ติดตามปริมาณเลือดแต่ละกรุ๊ปและผลิตภัณฑ์ พร้อมแจ้งเตือนวันหมดอายุแบบอัตโนมัติ
      </p>
      <ul class="landing-list">
        <li><span class="icon">✅</span><span>ดูปริมาณสำรองเลือดแยกตามกรุ๊ปและชนิดผลิตภัณฑ์ (LPRC, PRC, FFP, PC, Cryo)</span></li>
        <li><span class="icon">✅</span><span>ระบบเตือนวันหมดอายุด้วยสีแดง/เหลือง ช่วยจัดลำดับการใช้เลือด</span></li>
        <li><span class="icon">✅</span><span>รองรับการอัปโหลดไฟล์ Excel/CSV จากระบบ LIS หรือคลังเลือดเดิม</span></li>
      </ul>
      <div class="landing-cta">
        """,
        unsafe_allow_html=True,
    )
    c1, c2, _ = st.columns([1.2, 1, 2])
    with c1:
        if st.button("เข้าสู่ระบบเพื่อเริ่มใช้งานระบบ", type="primary", use_container_width=True):
            st.session_state["view"] = "login"
            _safe_rerun()
    with c2:
        st.write("")
        st.markdown(
            "<small>สำหรับเจ้าหน้าที่ธนาคารเลือด / ห้อง Lab / Admin ระบบคุณภาพภายในโรงพยาบาล</small>",
            unsafe_allow_html=True,
        )

    st.markdown(
        """
      </div>
      <div class="landing-pill">
        <span>🔐 ต้องล็อกอินก่อนจึงจะเข้าถึงข้อมูลได้</span>
        <span>|</span>
        <strong>ข้อมูลภายในองค์กรเท่านั้น</strong>
      </div>
    </div>
    <div>
      <div class="landing-card">
        <h3>ตัวอย่างภาพรวมระบบ</h3>
        <div class="landing-metrics">
          <div class="landing-metric">
            <span class="landing-metric-label">สถานะสำรองเลือดรวม</span>
            <span class="landing-metric-value">A / B / O / AB</span>
            <span class="landing-metric-tag">แสดงระดับเป็นสีเขียว-เหลือง-แดง</span>
          </div>
          <div class="landing-metric">
            <span class="landing-metric-label">การแจ้งเตือนวันหมดอายุ</span>
            <span class="landing-metric-value">Critical + Warning</span>
            <span class="landing-metric-tag landing-tag-muted">ลดความเสี่ยงเลือดหมดอายุในคลัง</span>
          </div>
        </div>
        <div class="landing-mini-badges">
          <span>Real-time Stock</span>
          <span>Expiry Monitor</span>
          <span>Excel / CSV Import</span>
          <span>Activity Log</span>
        </div>
        <p class="landing-note">
          * หน้าจอนี้เป็นหน้าแนะนำระบบก่อนเข้าสู่แดชบอร์ดจริง —
          กดปุ่ม “เข้าสู่ระบบเพื่อเริ่มใช้งานระบบ” เพื่อไปยังหน้าล็อกอิน
        </p>
      </div>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

# --------------------------------
# LOGIN PAGE
# --------------------------------
def render_login():
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    with st.container():
        st.markdown(
            """
<div class="login-card">
  <div class="login-left">
    <div>
      <div class="login-logo">
        <span class="icon">🩸</span>
        <span>Blood Stock Monitor</span>
      </div>
      <h2>ระบบบริหารคลังเลือดโรงพยาบาล</h2>
      <p>
        ดูปริมาณเลือดคงเหลือแยกตามกรุ๊ปและชนิดผลิตภัณฑ์ พร้อมระบบแจ้งเตือนวันหมดอายุ
        ช่วยให้ทีมธนาคารเลือดและห้อง Lab ตัดสินใจได้อย่างรวดเร็วและปลอดภัย
      </p>
      <ul class="login-bullets">
        <li><span class="icon">✅</span><span>แดชบอร์ด Real-time แสดงถุงเลือดพร้อมระดับคลื่นน้ำ</span></li>
        <li><span class="icon">✅</span><span>นำเข้าไฟล์ Excel/CSV จากระบบเดิมได้ทันที</span></li>
        <li><span class="icon">✅</span><span>แสดงสถานะวันหมดอายุเป็นสีแดง/เหลืองอย่างชัดเจน</span></li>
      </ul>
    </div>
    <div>
      <div class="login-stat-pill">
        <span>🔒 ข้อมูลเฉพาะภายในองค์กร</span>
        <span>•</span>
        <span>รองรับการ Audit & ระบบคุณภาพ</span>
      </div>
    </div>
  </div>
  <div class="login-right">
    <div class="login-title">เข้าสู่ระบบคลังเลือด</div>
    <div class="login-subtitle">Blood Stock Real-time Monitor สำหรับทีมธนาคารเลือดและห้อง Lab</div>
    """,
            unsafe_allow_html=True,
        )

        # ฟอร์มล็อกอินหลัก
        with st.form("login_form_main", clear_on_submit=False):
            st.markdown('<div class="login-form">', unsafe_allow_html=True)
            username = st.text_input("ชื่อผู้ใช้ (Username)", placeholder="เช่น bloodbank01 หรือชื่อย่อของคุณ")
            password = st.text_input("รหัสผ่าน (Password)", type="password", placeholder="ทดลองใช้: 1234")
            st.markdown(
                '<div class="hint">* เวอร์ชันทดลองใช้ ใช้รหัสผ่าน <strong>1234</strong> สำหรับเข้าใช้งาน</div>',
                unsafe_allow_html=True,
            )
            submitted = st.form_submit_button("เข้าสู่ระบบ", type="primary", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            if password == AUTH_PASSWORD:
                st.session_state["logged_in"] = True
                st.session_state["username"] = (username or "").strip() or "staff"
                st.session_state["view"] = "app"
                st.session_state["page"] = "หน้าหลัก"
                flash("เข้าสู่ระบบสำเร็จ ✅", "success")
                _safe_rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง (ทดลองใช้ password = 1234)")

        st.markdown(
            """
    <div class="login-footer-note">
      หากคุณไม่ใช่เจ้าหน้าที่ที่ได้รับอนุญาต กรุณาออกจากหน้านี้ทันที
      ข้อมูลทั้งหมดเป็นข้อมูลภายในของโรงพยาบาล
    </div>
  </div>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------
# MAIN ROUTER: landing / login / app
# --------------------------------
view = st.session_state.get("view", "landing")

if view == "landing":
    render_landing()
elif view == "login":
    render_login()
else:
    # ====== APP VIEW (ต้องล็อกอินแล้ว) ======
    if not st.session_state.get("logged_in"):
        st.session_state["view"] = "login"
        _safe_rerun()

    # ---------- SIDEBAR ----------
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

        st.write("")
        if st.button("ออกจากระบบ", key="nav_logout", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["view"] = "landing"
            flash("ออกจากระบบเรียบร้อยแล้ว", "info")
            _safe_rerun()

    # ---------- HEADER ----------
    st.title("Blood Stock Real-time Monitor")
    st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    show_flash()

    # ---------- PAGE: กรอกเลือด ----------
    if st.session_state["page"] == "กรอกเลือด":

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
                            "Available": "ว่าง",        # พร้อมใช้
                            "ReadyToIssue": "จอง",      # จอง
                            "Released": "จ่ายแล้ว",     # จ่ายแล้ว
                            "Expired": "Exp",
                            "ReleasedExpired": "Exp",
                            "Out": "จ่ายแล้ว",
                        }
                        if "Status" in df_file.columns:
                            df_file["Status"] = df_file["Status"].map(
                                lambda s: status_map_en2th.get(str(s).strip(), str(s).strip())
                            )

                        # เติมคอลัมน์ที่จำเป็น
                        for c in ["created_at", "Exp date", "Unit number", "Group",
                                  "Blood Components", "Status", "บันทึก"]:
                            if c not in df_file.columns:
                                df_file[c] = ""
                        df_file = df_file[
                            ["created_at", "Exp date", "Unit number", "Group",
                             "Blood Components", "Status", "บันทึก"]
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
                                    # Exp / จอง ฯลฯ
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

        # เพิ่มคอลัมน์ลำดับ
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

    # ---------- PAGE: หน้าหลัก ----------
    elif st.session_state["page"] == "หน้าหลัก":
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

        # เฉพาะ product ที่มีหน่วยมากกว่า 0
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

        # ตารางสรุป: product_type + units
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

    # ---------- ปุ่มรีเซ็ตสต็อก ----------
    st.divider()
    st.markdown("### ⚠️ จัดการระบบ")
    if st.session_state.get("logged_in"):
        if st.button("🧹 รีเซ็ตเลือดทั้งหมดเป็นศูนย์", type="primary", use_container_width=True):
            reset_all_stock(st.session_state.get("username", "admin"))
            flash("รีเซ็ตจำนวนเลือดทั้งหมดแล้ว ✅", "warning")
            _safe_rerun()
