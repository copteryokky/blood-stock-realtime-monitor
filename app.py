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
    def st_autorefresh(*args, **kwargs): return None

# ===== DB funcs =====
from db import init_db, get_all_status, get_stock_by_blood, adjust_stock, reset_all_stock

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
#expiry-banner .chip.green{background:#22c55e}

/* Flash */
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
UI_TO_DB = {"LPRC": "LPRC", "PRC": "PRC", "FFP": "Plasma", "PC": "Platelets"}
ALL_PRODUCTS_UI = ["LPRC", "PRC", "FFP", "Cryo", "PC"]

STATUS_OPTIONS = ["ว่าง", "จอง", "จำหน่าย", "Exp", "หลุดจอง"]
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

    cols = ["created_at", "Exp date", "Unit number", "Group",
            "Blood Components", "Status", "สถานะ(สี)", "บันทึก"]
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

# ---------- ฟังก์ชันสร้าง tooltip chart ใต้ถุงเลือด ----------
def _build_chart_tooltip(blood_type: str, dist: dict | None) -> str:
    if not dist:
        dist = {}

    total_units = sum(int(v) for v in dist.values() if v)
    if total_units <= 0:
        body = '<div class="bag-bars-empty">ไม่มีเลือดคงเหลือที่ยังไม่หมดอายุ</div>'
    else:
        max_v = max(int(v) for v in dist.values() if v)
        rows_html = []
        color_map = {
            "LPRC": "#22c55e",
            "PRC": "#0ea5e9",
            "FFP": "#a855f7",
            "Cryo": "#f97316",
            "PC": "#eab308",
        }
        for p in ALL_PRODUCTS_UI:
            v = int(dist.get(p, 0))
            if v <= 0:
                continue
            width_pct = max(12, int(100 * v / max_v))
            bar_color = color_map.get(p, "#22c55e")
            rows_html.append(
                f"""
                <div class="bag-bar-row">
                  <div class="bag-bar-label">{p}</div>
                  <div class="bag-bar-track">
                    <div class="bag-bar-fill" style="width:{width_pct}%;background:{bar_color};"></div>
                  </div>
                  <div class="bag-bar-value">{v}</div>
                </div>
                """
            )
        body = '<div class="bag-bars">' + "".join(rows_html) + "</div>"

    return f"""
    <div class="bag-tooltip">
      <div class="bag-tooltip-card">
        <div class="bag-tooltip-title">
          <span>สรุปผลิตภัณฑ์กรุ๊ป {blood_type}</span>
        </div>
        {body}
      </div>
    </div>
    """

# ===== SVG: ถุงเลือด + คลื่นน้ำสมจริง + tooltip chart =====
def bag_svg(blood_type: str, total: int, dist: dict | None = None, show_chart: bool = False) -> str:
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

    # ถ้าไม่มีเลือดเลย ไม่วาดน้ำ
    if pct <= 0:
        liquid_group = ""
    else:
        liquid_group = f"""
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
          <!-- น้ำด้านล่าง -->
          <rect y="{base_y+4:.1f}" width="220" height="220" fill="url(#liquid-{gid})"/>
        </g>
      </g>
        """

    chart_html = _build_chart_tooltip(blood_type, dist) if show_chart else ""

    return f"""
<div>
  <style>
    .bag-hover-wrap{{position:relative;display:flex;flex-direction:column;align-items:center;gap:6px;
                     font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial}}
    .bag-wrap{{display:flex;flex-direction:column;align-items:center;gap:10px;}}
    .bag{{transition:transform .18s ease, filter .18s ease}}
    .bag:hover{{transform:translateY(-2px);
                filter:drop-shadow(0 10px 22px rgba(0,0,0,.12));}}
    .wave-layer{{mix-blend-mode:screen;opacity:.92}}
    @keyframes wave-move-1{{0%{{transform:translateX(0);}}
                            100%{{transform:translateX(-80px);}}}}
    @keyframes wave-move-2{{0%{{transform:translateX(0);}}
                            100%{{transform:translateX(-60px);}}}}

    .bag-tooltip{{position:absolute;top:-6px;left:50%;
                  transform:translate(-50%,-100%) scale(.96);
                  opacity:0;pointer-events:none;
                  transition:opacity .18s ease, transform .18s ease;}}
    .bag-hover-wrap:hover .bag-tooltip{{opacity:1;transform:translate(-50%,-112%) scale(1);}}
    .bag-tooltip-card{{min-width:230px;max-width:260px;background:rgba(17,24,39,.97);
                       color:#e5e7eb;border-radius:14px;padding:.7rem .85rem;
                       box-shadow:0 14px 28px rgba(0,0,0,.35);font-size:11px;}}
    .bag-tooltip-title{{font-weight:700;font-size:12px;margin-bottom:.35rem;
                        display:flex;justify-content:space-between;align-items:center;}}
    .bag-bars{{display:flex;flex-direction:column;gap:.25rem;}}
    .bag-bars-empty{{font-size:11px;color:#e5e7eb;opacity:.85;}}
    .bag-bar-row{{display:flex;align-items:center;gap:.35rem;}}
    .bag-bar-label{{width:46px;font-weight:600;color:#e5e7eb;}}
    .bag-bar-track{{flex:1;height:7px;border-radius:999px;background:rgba(148,163,184,.45);overflow:hidden;}}
    .bag-bar-fill{{height:100%;border-radius:999px;}}
    .bag-bar-value{{width:32px;text-align:right;font-variant-numeric:tabular-nums;}}
  </style>
  <div class="bag-hover-wrap">
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
            <stop offset="100%" stop-color="{fill}" stop-opacity=".60"/>
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

        {liquid_group}

        <!-- ป้าย max -->
        <rect x="98" y="24" rx="10" ry="10" width="54" height="22"
              fill="#ffffff" stroke="#e5e7eb"/>
        <text x="125" y="40" text-anchor="middle"
              font-size="12" fill="#374151">{BAG_MAX} max</text>

        <!-- ตัวอักษรกรุ๊ปเลือด -->
        <text x="84" y="126" text-anchor="middle" font-size="32" font-weight="900"
              style="paint-order: stroke fill"
              stroke="#111827" stroke-width="4"
              fill="{letter_fill}">{blood_type}</text>
      </svg>
    </div>
    {chart_html}
  </div>
</div>
"""

# ============ INIT DB ============
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()

# ===== utils with stability =====
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

# ===== Expiry rules =====
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
    # แบ่งตามสี
    df_days = df["_exp_days"]
    red_mask = df_days <= 4  # รวมหมดอายุแล้วด้วย
    yellow_mask = (df_days >= 5) & (df_days <= 10)
    green_mask = df_days > 10

    n_red = int(red_mask.sum())
    n_yellow = int(yellow_mask.sum())
    n_green = int(green_mask.sum())

    if n_red + n_yellow + n_green == 0:
        return

    st.markdown(
        f"""
        <div id="expiry-banner">
          <div class="title">
            ⏰ สถานะวันหมดอายุ (ทุกหน่วยในตาราง)
            <span class="chip">แดง {n_red}</span>
            <span class="chip warn">เหลือง {n_yellow}</span>
            <span class="chip green">เขียว {n_green}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ===== คำนวณ distribution ตามกรุ๊ป ใช้เฉพาะที่ยังไม่หมดอายุ =====
def non_expired_distribution_by_group():
    df = st.session_state["entries"]
    result = {bt: {p: 0 for p in ALL_PRODUCTS_UI} for bt in ["A", "B", "O", "AB"]}
    if df.empty:
        return result

    work = df.copy()
    work["_exp_days"] = work["Exp date"].apply(left_days_safe)

    # เฉพาะที่มีวันหมดอายุ และยังไม่หมดอายุ
    mask = work["_exp_days"].notna() & (work["_exp_days"] >= 0)
    # ไม่เอาสถานะจำหน่าย / Exp ออกจากกราฟ
    mask &= ~work["Status"].isin(["จำหน่าย", "Exp"])
    work = work[mask]

    for _, r in work.iterrows():
        bt = str(r.get("Group", "")).strip()
        comp = str(r.get("Blood Components", "")).strip()
        if bt in result and comp in result[bt]:
            result[bt][comp] += 1

    return result

# ============ SIDEBAR ============
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
        st.session_state["page"] = "กรอกเลือด"
        _safe_rerun()

# ============ HEADER ============
st.title("Blood Stock Real-time Monitor")
st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
show_flash()

# ---------- หน้า: กรอกเลือด ----------
if st.session_state["page"] == "กรอกเลือด":
    if not st.session_state["logged_in"]:
        st.warning("ต้องล็อกอินก่อนจึงจะใช้งานเมนูนี้ได้")
    else:
        st.subheader("กรอกเลือด")

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
                elif status in ["จำหน่าย", "Exp"]:
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

        # ===== นำเข้า Excel / CSV =====
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
            try:
                if up.name.lower().endswith(".csv"):
                    df_file = pd.read_csv(up)
                else:
                    try:
                        df_file = pd.read_excel(up)
                    except Exception as e:
                        st.error("อ่าน Excel ไม่ได้ (อาจขาด openpyxl). แนะนำเพิ่ม openpyxl ใน requirements.txt หรืออัปโหลด CSV แทน")
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
                    df_file = df_file.rename(columns={c: col_map.get(str(c).strip(), c) for c in df_file.columns})

                    # map สถานะจากไฟล์ภาษาอังกฤษ -> สถานะไทยในระบบ
                    status_map_en2th = {
                        "Available": "ว่าง",
                        "AVAILABLE": "ว่าง",
                        "ReadyToIssue": "จอง",
                        "Ready to issue": "จอง",
                        "Released": "จำหน่าย",
                        "RELEASED": "จำหน่าย",
                        "Expired": "Exp",
                        "ReleasedExpired": "Exp",
                        "Out": "จำหน่าย",
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
                        ["created_at", "Exp date", "Unit number", "Group", "Blood Components", "Status", "บันทึก"]
                    ].copy()

                    df_file["สถานะ(สี)"] = df_file["Status"].map(lambda s: STATUS_COLOR.get(str(s), str(s)))

                    if mode_merge.startswith("แทนที่"):
                        st.session_state["entries"] = pd.DataFrame(
                            columns=[
                                "created_at",
                                "Exp date",
                                "Unit number",
                                "Group",
                                "Blood Components",
                                "Status",
                                "สถานะ(สี)",
                                "บันทึก",
                            ]
                        )

                    applied = failed = 0
                    for _, r in df_file.iterrows():
                        g = str(r["Group"]).strip() or "A"
                        comp = str(r["Blood Components"]).strip() or "LPRC"
                        stt = str(r["Status"]).strip() or "ว่าง"
                        nt = str(r["บันทึก"]).strip()

                        st.session_state["entries"] = pd.concat(
                            [
                                st.session_state["entries"],
                                pd.DataFrame(
                                    [
                                        {
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
                                    ]
                                ),
                            ],
                            ignore_index=True,
                        )

                        try:
                            if stt in ["ว่าง", "หลุดจอง"]:
                                apply_stock_change(
                                    g, comp, +1, nt or "import", st.session_state.get("username") or "admin"
                                )
                                add_activity("INBOUND", g, comp, +1, f"import: {nt}")
                            elif stt in ["จำหน่าย", "Exp"]:
                                apply_stock_change(
                                    g, comp, -1, nt or "import-out", st.session_state.get("username") or "admin"
                                )
                                add_activity("OUTBOUND", g, comp, -1, f"import: {nt}")
                            else:
                                add_activity("BOOK", g, comp, 0, f"import: {nt}")
                            applied += 1
                        except Exception:
                            failed += 1

                    flash(
                        f"นำเข้าเสร็จสิ้น ✅ สำเร็จ {applied} รายการ"
                        f"{' (ล้มเหลว '+str(failed)+')' if failed else ''}"
                    )
                    _safe_rerun()
            except Exception as e:
                st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")

        # ===== ตารางสรุป (แก้ไขได้) =====
        st.markdown("### ตารางสรุป (แก้ไขได้)")
        df_vis = st.session_state["entries"].copy(deep=True)

        parsed = pd.to_datetime(df_vis["Exp date"], errors="coerce")
        df_vis["Exp date"] = parsed.dt.date

        df_vis["_exp_days"] = df_vis["Exp date"].apply(left_days_safe)
        df_vis["วันหมดอายุนับถอยหลัง (วัน)"] = df_vis["_exp_days"]
        df_vis["สถานะวันหมดอายุ"] = df_vis["_exp_days"].apply(expiry_label)

        # แบนเนอร์สรุปจำนวน แดง/เหลือง/เขียว
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

        col_cfg = {
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
            keep = [
                "created_at",
                "Exp date",
                "Unit number",
                "Group",
                "Blood Components",
                "Status",
                "สถานะ(สี)",
                "บันทึก",
            ]
            st.session_state["entries"] = out[keep].reset_index(drop=True)
            flash("อัปเดตตารางแล้ว ✅")
            _safe_rerun()

# ---------- หน้า: หน้าหลัก ----------
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
    # distribution เฉพาะที่ยังไม่หมดอายุ (ใช้ใน tooltip + กราฟด้านล่าง)
    dist_all = non_expired_distribution_by_group()

    blood_types = ["A", "B", "O", "AB"]
    cols = st.columns(4)
    for i, bt in enumerate(blood_types):
        with cols[i]:
            st.markdown(f"### ถุงเลือดกรุ๊ป **{bt}**")
            st_html(
                bag_svg(bt, totals.get(bt, 0), dist=dist_all.get(bt), show_chart=True),
                height=270,
                scrolling=False,
            )
            if st.button(f"ดูรายละเอียดกรุ๊ป {bt}", key=f"btn_{bt}"):
                st.session_state["selected_bt"] = bt
                _safe_rerun()

    st.divider()
    sel = st.session_state.get("selected_bt") or "A"
    st.subheader(f"รายละเอียดกรุ๊ป {sel}")
    _L, _M, _R = st.columns([1, 1, 1])
    with _M:
        st_html(
            bag_svg(sel, totals.get(sel, 0), dist=dist_all.get(sel), show_chart=True),
            height=270,
            scrolling=False,
        )

    # ใช้ distribution เฉพาะที่ยังไม่หมดอายุสำหรับกราฟแท่ง
    dist_sel = dist_all.get(sel, {p: 0 for p in ALL_PRODUCTS_UI})
    # Cryo เป็น global ถ้าต้องการจะใส่เพิ่มจาก DB ก็ทำได้ แต่ตอนนี้ 0 ถ้าไม่มีข้อมูล
    # dist_sel["Cryo"] = get_global_cryo()

    df = pd.DataFrame([{"product_type": k, "units": int(v)} for k, v in dist_sel.items()])
    df["product_type"] = pd.Categorical(df["product_type"], categories=ALL_PRODUCTS_UI, ordered=True)

    def color_for(u):
        if u <= CRITICAL_MAX:
            return "#ef4444"
        if u <= YELLOW_MAX:
            return "#f59e0b"
        return "#22c55e"

    df["color"] = df["units"].apply(color_for)
    ymax = max(10, int(df["units"].max() * 1.25))

    bars = alt.Chart(df).mark_bar().encode(
        x=alt.X("product_type:N", sort=ALL_PRODUCTS_UI, title="ประเภทผลิตภัณฑ์"),
        y=alt.Y("units:Q", title="จำนวนหน่วย (unit)", scale=alt.Scale(domainMin=0, domainMax=ymax)),
        color=alt.Color("color:N", scale=None, legend=None),
        tooltip=["product_type", "units"],
    )
    text = alt.Chart(df).mark_text(
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

    # ตารางสรุป: เอาคอลัมน์ color ออก เหลือแค่ product_type + units
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

# ========== ปุ่มรีเซ็ตสต็อก ==========
st.divider()
st.markdown("### ⚠️ จัดการระบบ")
if st.session_state.get("logged_in"):
    if st.button("🧹 รีเซ็ตเลือดทั้งหมดเป็นศูนย์", type="primary", use_container_width=True):
        reset_all_stock(st.session_state.get("username", "admin"))
        flash("รีเซ็ตจำนวนเลือดทั้งหมดแล้ว ✅", "warning")
        _safe_rerun()
else:
    st.info("ต้องเข้าสู่ระบบก่อนจึงจะใช้งานปุ่มรีเซ็ตได้")
