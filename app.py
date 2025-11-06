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
from db import init_db, get_all_status, get_stock_by_blood, adjust_stock

# ============ PAGE / THEME ============
st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")
st.markdown("""
<style>
.block-container{padding-top:1.0rem;}
h1,h2,h3{letter-spacing:.2px}

/* badge legend */
.badge{display:inline-flex;align-items:center;gap:.4rem;padding:.25rem .5rem;border-radius:999px;background:#f3f4f6}
.legend-dot{width:.7rem;height:.7rem;border-radius:999px;display:inline-block}

/* ===== Sidebar ===== */
[data-testid="stSidebar"]{background:#2e343a;}
[data-testid="stSidebar"] .sidebar-title{color:#e5e7eb;font-weight:800;font-size:1.06rem;margin:6px 0 10px 4px}

/* --- User card --- */
[data-testid="stSidebar"] .user-card{
  display:flex; align-items:center; gap:.8rem;
  background:linear-gradient(135deg,#39424a,#2f343a);
  border:1px solid #475569; border-radius:14px; padding:.75rem .9rem; margin:.5rem .2rem 1rem .2rem;
  box-shadow:0 8px 22px rgba(0,0,0,.25);
}
[data-testid="stSidebar"] .user-avatar{
  width:40px; height:40px; border-radius:999px; background:#ef4444; color:#fff; font-weight:900;
  display:flex; align-items:center; justify-content:center; letter-spacing:.5px;
  box-shadow:0 0 0 3px rgba(239,68,68,.25);
}
[data-testid="stSidebar"] .user-meta{display:flex; flex-direction:column; line-height:1.1}
[data-testid="stSidebar"] .user-meta .label{font-size:.75rem; color:#cbd5e1}
[data-testid="stSidebar"] .user-meta .name{font-size:1rem; color:#fff; font-weight:800}

/* ปุ่มเมนู */
[data-testid="stSidebar"] .stButton>button{
  width:100%; background:#ffffff; color:#111827; border:1px solid #cbd5e1;
  border-radius:12px; font-weight:700; justify-content:flex-start;
}
[data-testid="stSidebar"] .stButton>button:hover{background:#f3f4f6}

/* ฟอร์ม LOGIN */
[data-testid="stSidebar"] label{ color:#f3f4f6 !important; font-weight:700; }
[data-testid="stSidebar"] input[type="text"],
[data-testid="stSidebar"] input[type="password"]{
  background:#ffffff !important; color:#111827 !important;
  border:2px solid #e5e7eb !important; border-radius:10px !important; font-weight:600 !important;
  caret-color:#111827 !important;
}
[data-testid="stSidebar"] input::placeholder{ color:#6b7280 !important; opacity:1 !important; }
[data-testid="stSidebar"] input:focus{
  outline:none !important; border-color:#ef4444 !important;
  box-shadow:0 0 0 3px rgba(239,68,68,.25) !important;
}
[data-testid="stSidebar"] button[kind="primary"]{
  width:100%; background:#ef4444 !important; color:#ffffff !important;
  border:none !important; border-radius:10px !important; font-weight:800;
}
[data-testid="stSidebar"] button[kind="primary"]:hover{ filter:brightness(.95); }

/* DataFrame */
[data-testid="stDataFrame"] table {font-size:14px;}
[data-testid="stDataFrame"] th {font-size:14px; font-weight:700; color:#111827;}
</style>
""", unsafe_allow_html=True)

# ============ CONFIG ============
BAG_MAX       = 20
CRITICAL_MAX  = 4
YELLOW_MAX    = 15
AUTH_PASSWORD = "1234"
FLASH_SECONDS = 2.5

# ===== Mapping / Orders =====
RENAME_TO_UI    = {"Plasma": "FFP", "Platelets": "PC"}
UI_TO_DB        = {"LPRC":"LPRC","PRC":"PRC","FFP":"Plasma","PC":"Platelets"}
ALL_PRODUCTS_UI = ["LPRC","PRC","FFP","Cryo","PC"]

STATUS_OPTIONS = ["ว่าง","จอง","จำหน่าย","Exp","หลุดจอง"]
STATUS_COLOR   = {
    "ว่าง": "🟢 ว่าง", "จอง": "🟠 จอง", "จำหน่าย": "⚫ จำหน่าย", "Exp": "🔴 Exp", "หลุดจอง": "🔵 หลุดจอง",
}

# ============ STATE ============
def _init_state():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("page", "หน้าหลัก")
    st.session_state.setdefault("selected_bt", None)
    st.session_state.setdefault("flash", None)

    # เพิ่มคอลัมน์ 'เหลือ(วัน)' ถัดจาก Exp date
    cols = ["Exp date","เหลือ(วัน)","Unit number","Group","Blood Components","Status","ค่าสถานะ","สถานะ(สี)","บันทึก"]
    if "entries" not in st.session_state:
        st.session_state["entries"] = pd.DataFrame(columns=cols)
    else:
        for c in cols:
            if c not in st.session_state["entries"].columns:
                st.session_state["entries"][c] = ""
        st.session_state["entries"] = st.session_state["entries"][cols]
_init_state()

# ============ HELPERS ============
def _safe_rerun():
    try: st.rerun()
    except Exception: st.experimental_rerun()

def compute_bag(total: int, max_cap=BAG_MAX):
    t = max(0, int(total))
    if t <= CRITICAL_MAX: status, label = "red", "วิกฤตใกล้หมด"
    elif t <= YELLOW_MAX: status, label = "yellow", "เพียงพอ"
    else: status, label = "green", "ปกติ"
    pct = max(0, min(100, int(round(100 * min(t, max_cap) / max_cap))))
    return status, label, pct

def bag_color(status: str) -> str:
    return {"green":"#22c55e", "yellow":"#f59e0b", "red":"#ef4444"}[status]

def normalize_products(rows):
    d = {name: 0 for name in ALL_PRODUCTS_UI}
    for r in rows:
        name = str(r.get("product_type","")).strip()
        ui = RENAME_TO_UI.get(name, name)
        if ui in d and ui != "Cryo":
            d[ui] += int(r.get("units",0))
    return d

def get_global_cryo():
    total = 0
    for bt in ["A","B","O","AB"]:
        rows = get_stock_by_blood(bt)
        for r in rows:
            name = str(r.get("product_type","")).strip()
            ui = RENAME_TO_UI.get(name, name)
            if ui != "Cryo":
                total += int(r.get("units",0))
    return total

# ===== SVG bag (ไม่มี unit ใต้ถุง) =====
def bag_svg(blood_type: str, total: int) -> str:
    status, _label, pct = compute_bag(total, BAG_MAX)
    fill = bag_color(status)
    letter_fill   = {"A":"#facc15","B":"#f472b6","O":"#60a5fa","AB":"#ffffff"}.get(blood_type, "#ffffff")
    letter_stroke = "#111827" if blood_type != "AB" else "#6b7280"
    inner_h, inner_y0 = 148.0, 40.0
    water_h = inner_h * pct / 100.0
    water_y = inner_y0 + (inner_h - water_h)
    gid = f"g_{blood_type}"
    wave_amp = 5 + 6*(pct/100)
    wave_path = f"M24,{water_y:.1f} Q54,{water_y-wave_amp:.1f} 84,{water_y:.1f} Q114,{water_y+wave_amp:.1f} 144,{water_y:.1f} L144,198 24,198 Z"
    edge = "#dc2626"
    return f"""
<div>
  <style>
    .bag-wrap{{display:flex;flex-direction:column;align-items:center;gap:10px;font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial}}
    .bag{{transition:transform .18s ease, filter .18s ease}}
    .bag:hover{{transform:translateY(-2px); filter:drop-shadow(0 10px 22px rgba(0,0,0,.12));}}
  </style>
  <div class="bag-wrap">
    <svg class="bag" width="170" height="230" viewBox="0 0 168 206" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <clipPath id="clip-{gid}">
          <path d="M24,40 C24,24 38,14 58,14 L110,14 C130,14 144,24 144,40
                   L144,172 C144,191 128,202 108,204 L56,204 C36,202 24,191 24,172 Z"/>
        </clipPath>
        <linearGradient id="liquid-{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="{fill}" stop-opacity=".96"/>
          <stop offset="100%" stop-color="{fill}" stop-opacity=".86"/>
        </linearGradient>
        <linearGradient id="gloss-{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="rgba(255,255,255,.75)"/>
          <stop offset="100%" stop-color="rgba(255,255,255,0)"/>
        </linearGradient>
      </defs>
      <circle cx="84" cy="10" r="7.5" fill="#eef2ff" stroke="#dbe0ea" stroke-width="3"/>
      <rect x="77.5" y="14" width="13" height="8" rx="3" fill="#e5e7eb"/>
      <g>
        <path d="M16,34 C16,18 32,8 52,8 L116,8 C136,8 152,18 152,34 L152,176 C152,195 136,206 116,206 L52,206 C32,206 16,195 16,176 Z"
              fill="#ffffff" stroke="{edge}" stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round"/>
        <path d="M16,34 C16,18 32,8 52,8 L116,8 C136,8 152,18 152,34 L152,176 C152,195 136,206 116,206 L52,206 C32,206 16,195 16,176 Z"
              fill="none" stroke="#7f1d1d" stroke-opacity=".18" stroke-width="6"/>
      </g>
      <g clip-path="url(#clip-{gid})"><path d="{wave_path}" fill="url(#liquid-{gid})"/></g>
      <rect x="38" y="22" width="10" height="176" fill="url(#gloss-{gid})" opacity=".7" clip-path="url(#clip-{gid})"/>
      <g><rect x="98" y="24" rx="10" ry="10" width="54" height="22" fill="#fff" stroke="#e5e7eb"/>
         <text x="125" y="40" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text></g>
      <text x="84" y="126" text-anchor="middle" font-size="32" font-weight="900"
            style="paint-order:stroke fill" stroke="{letter_stroke}" stroke-width="4" fill="{letter_fill}">{blood_type}</text>
    </svg>
  </div>
</div>
"""

# ============ INIT DB ============
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()

# ============ SIDEBAR ============
with st.sidebar:
    if st.session_state.get("logged_in"):
        name = (st.session_state.get("username") or "staff").strip()
        initials = (name[:2] or "ST").upper()
        st.markdown(f"""
        <div class="user-card">
          <div class="user-avatar">{initials}</div>
          <div class="user-meta">
            <span class="label">เข้าสู่ระบบสำเร็จ</span>
            <span class="name">{name}</span>
          </div>
        </div>""", unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">เมนู</div>', unsafe_allow_html=True)
    if st.button("หน้าหลัก", key="nav_home", use_container_width=True):
        st.session_state["page"] = "หน้าหลัก"; _safe_rerun()
    if st.button("กรอกเลือด", key="nav_entry", use_container_width=True):
        st.session_state["page"] = "กรอกเลือด"; _safe_rerun()
    if st.button("เข้าสู่ระบบ" if not st.session_state["logged_in"] else "ออกจากระบบ",
                 key="nav_auth", use_container_width=True):
        st.session_state["page"] = "เข้าสู่ระบบ" if not st.session_state["logged_in"] else "ออกจากระบบ"; _safe_rerun()

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
                st.session_state["page"] = "หน้าหลัก"
                st.session_state["flash"] = {"type":"success","text":f"เข้าสู่ระบบสำเร็จ: {st.session_state['username']}",
                                             "until": time.time()+FLASH_SECONDS}
                _safe_rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง (password = 1234)")

    if st.session_state["page"] == "ออกจากระบบ" and st.session_state["logged_in"]:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["page"] = "หน้าหลัก"
        st.session_state["flash"] = {"type":"info","text":"ออกจากระบบแล้ว","until": time.time()+FLASH_SECONDS}
        _safe_rerun()

# ============ HEADER ============
st.title("Blood Stock Real-time Monitor")
st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# Flash
if st.session_state.get("flash"):
    now = time.time()
    data = st.session_state["flash"]
    if now < data.get("until", 0):
        color = {"success":"#16a34a","info":"#0ea5e9","warning":"#f59e0b","error":"#ef4444"}.get(data.get("type","success"),"#16a34a")
        st.markdown(f"""<div style="position:fixed; top:110px; right:24px; z-index:9999;
                    background:{color}; color:#fff; padding:.7rem 1rem; border-radius:12px;
                    font-weight:800; box-shadow:0 10px 24px rgba(0,0,0,.18)">{data.get("text","")}</div>""",
                    unsafe_allow_html=True)
    else:
        st.session_state["flash"] = None

# ============ PAGES ============
page = st.session_state["page"]

# ---------- หน้า: หน้าหลัก ----------
if page == "หน้าหลัก":
    c1, c2, c3 = st.columns(3)
    c1.markdown('<span class="badge"><span class="legend-dot" style="background:#ef4444"></span> วิกฤตใกล้หมด 0–4</span>', unsafe_allow_html=True)
    c2.markdown('<span class="badge"><span class="legend-dot" style="background:#f59e0b"></span> เพียงพอ 5–15</span>', unsafe_allow_html=True)
    c3.markdown('<span class="badge"><span class="legend-dot" style="background:#22c55e"></span> ปกติ ≥16</span>', unsafe_allow_html=True)

    overview = get_all_status()
    blood_types = ["A","B","O","AB"]
    cols = st.columns(4)
    for i, bt in enumerate(blood_types):
        info = next(d for d in overview if d["blood_type"] == bt)
        total = int(info.get("total", 0))
        with cols[i]:
            st.markdown(f"### ถุงเลือดกรุ๊ป **{bt}**")
            st_html(bag_svg(bt, total), height=270, scrolling=False)
            if st.button(f"ดูรายละเอียดกรุ๊ป {bt}", key=f"btn_{bt}"):
                st.session_state["selected_bt"] = bt; _safe_rerun()

    st.divider()
    sel = st.session_state.get("selected_bt")
    if not sel:
        st.info("กดเลือกรายละเอียดที่กรุ๊ปโลหิตด้านบน เพื่อดูสต๊อกและทำรายการนำเข้า/เบิก")
    else:
        st.subheader(f"รายละเอียดกรุ๊ป {sel}")
        total_sel = next(d for d in overview if d["blood_type"] == sel)["total"]

        _L,_M,_R = st.columns([1,1,1])
        with _M:
            st_html(bag_svg(sel, int(total_sel)), height=270, scrolling=False)

        # สรุปจำนวนต่อชนิด + Cryo รวมทุกกรุ๊ป
        def _normalize(blood):
            rows = get_stock_by_blood(blood)
            d = {name: 0 for name in ALL_PRODUCTS_UI}
            for r in rows:
                name = str(r.get("product_type","")).strip()
                ui = RENAME_TO_UI.get(name, name)
                if ui in d and ui != "Cryo":
                    d[ui] += int(r.get("units",0))
            return d
        dist_sel  = _normalize(sel)
        dist_sel["Cryo"] = get_global_cryo()

        df = pd.DataFrame([{"product_type":k, "units":int(v)} for k,v in dist_sel.items()])
        order_dtype = pd.CategoricalDtype(ALL_PRODUCTS_UI, ordered=True)
        df["product_type"] = df["product_type"].astype(order_dtype)

        def color_for(u):
            if u <= CRITICAL_MAX: return "#ef4444"
            if u <= YELLOW_MAX:   return "#f59e0b"
            return "#22c55e"
        df["color"] = df["units"].apply(color_for)
        ymax = max(10, int(df["units"].max() * 1.25))

        bars = alt.Chart(df).mark_bar().encode(
            x=alt.X("product_type:N",
                    sort=ALL_PRODUCTS_UI,
                    title="ประเภทผลิตภัณฑ์ (ลำดับ: LPRC, PRC, FFP, Cryo, PC)",
                    axis=alt.Axis(labelAngle=0, labelFontSize=15, titleFontSize=15,
                                  labelColor="#111827", titleColor="#111827")),
            y=alt.Y("units:Q", title="จำนวนหน่วย (unit)",
                    scale=alt.Scale(domainMin=0, domainMax=ymax),
                    axis=alt.Axis(labelFontSize=15, titleFontSize=15,
                                  labelColor="#111827", titleColor="#111827")),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=[alt.Tooltip("product_type:N", title="ประเภท"),
                     alt.Tooltip("units:Q", title="จำนวน")]
        )
        text = alt.Chart(df).mark_text(align="center", baseline="middle", dy=0,
                                       fontSize=16, fill="#111827").encode(
            x=alt.X("product_type:N", sort=ALL_PRODUCTS_UI),
            y="units:Q", text="units:Q"
        )
        chart = (bars + text).properties(height=420).configure_view(strokeOpacity=0)
        st.altair_chart(chart, use_container_width=True)

        st.dataframe(df[["product_type","units"]], use_container_width=True, hide_index=True)

# ---------- หน้า: กรอกเลือด ----------
elif page == "กรอกเลือด":
    st.subheader("กรอกเลือด")
    if not st.session_state["logged_in"]:
        st.warning("ต้องล็อกอินก่อนจึงจะใช้งานเมนูนี้ได้")
    else:
        with st.form("blood_entry_form", clear_on_submit=True):
            c1,c2 = st.columns(2)
            with c1:
                unit_number = st.text_input("Unit number")
            with c2:
                exp_date = st.date_input("Exp date", value=date.today())
            c3,c4 = st.columns(2)
            with c3:
                group = st.selectbox("Group", ["A","B","O","AB"])
            with c4:
                status = st.selectbox("Status", STATUS_OPTIONS, index=0)
            c5,c6 = st.columns(2)
            with c5:
                component = st.selectbox("Blood Components", ["LPRC","PRC","FFP","Cryo","PC"])
            with c6:
                note = st.text_input("บันทึก")
            submitted = st.form_submit_button("บันทึกรายการ", use_container_width=True)

        if submitted:
            exp_str = exp_date.strftime("%Y/%m/%d")
            # คำนวณวันคงเหลือทันทีตอนบันทึก
            days_left = (exp_date - date.today()).days
            new_row = {
                "Exp date": exp_str,
                "เหลือ(วัน)": str(days_left),
                "Unit number": unit_number,
                "Group": group,
                "Blood Components": component,
                "Status": status,
                "ค่าสถานะ": status,
                "สถานะ(สี)": STATUS_COLOR.get(status, status),
                "บันทึก": note,
            }
            st.session_state["entries"] = pd.concat(
                [st.session_state["entries"], pd.DataFrame([new_row])], ignore_index=True
            )
            st.session_state["flash"] = {"type":"success","text":"บันทึกรายการแล้ว ✅","until": time.time()+FLASH_SECONDS}
            _safe_rerun()

        st.markdown("### ตารางสรุป (แก้ไขได้)")
        df_vis = st.session_state["entries"].copy()

        # แปลงวันที่ + คำนวณ 'เหลือ(วัน)' ทุกครั้งที่รีเฟรช เพื่อให้ตรงกับวันที่ปัจจุบัน
        _exp = pd.to_datetime(df_vis["Exp date"], errors="coerce")
        df_vis["Exp date"] = _exp.dt.date
        today = date.today()
        df_vis["เหลือ(วัน)"] = _exp.dt.date.apply(
            lambda d: "" if pd.isna(pd.to_datetime(d, errors="coerce")) else str((d - today).days)
        )

        col_cfg = {
            "Exp date": st.column_config.DateColumn("Exp date", format="YYYY/MM/DD"),
            "เหลือ(วัน)": st.column_config.TextColumn("วันหมดอายุนับถอยหลัง (วัน)", disabled=True),
            "Unit number": st.column_config.TextColumn("Unit number"),
            "Group": st.column_config.SelectboxColumn("Group", options=["A","B","O","AB"]),
            "Blood Components": st.column_config.SelectboxColumn("Blood Components", options=ALL_PRODUCTS_UI),
            "Status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS),
            "ค่าสถานะ": st.column_config.TextColumn("ค่าสถานะ", disabled=True),
            "สถานะ(สี)": st.column_config.TextColumn("สถานะ(สี)", disabled=True),
            "บันทึก": st.column_config.TextColumn("บันทึก"),
        }

        edited = st.data_editor(
            df_vis, num_rows="dynamic", use_container_width=True, hide_index=True, column_config=col_cfg
        )

        # เซฟกลับ + คำนวณ 'เหลือ(วัน)' จาก Exp date เสมอ
        if not edited.equals(df_vis):
            out = edited.copy()

            def _d2str(x):
                if pd.isna(x): return ""
                if isinstance(x, (datetime, pd.Timestamp)): return x.date().strftime("%Y/%m/%d")
                if isinstance(x, date): return x.strftime("%Y/%m/%d")
                try:
                    return pd.to_datetime(x, errors="coerce").date().strftime("%Y/%m/%d")
                except Exception:
                    return str(x)

            out["Exp date"] = out["Exp date"].apply(_d2str)

            # คำนวณวันคงเหลือตาม Exp date ที่แก้ไข
            _exp2 = pd.to_datetime(out["Exp date"], errors="coerce").dt.date
            out["เหลือ(วัน)"] = _exp2.apply(lambda d: "" if pd.isna(pd.to_datetime(d, errors="coerce")) else str((d - date.today()).days))

            out["ค่าสถานะ"] = out["Status"].astype(str)
            out["สถานะ(สี)"] = out["Status"].map(lambda s: STATUS_COLOR.get(s, s))
            for c in ["Unit number","Group","Blood Components","Status","ค่าสถานะ","สถานะ(สี)","บันทึก","เหลือ(วัน)"]:
                out[c] = out[c].astype(str).fillna("")

            cols = ["Exp date","เหลือ(วัน)","Unit number","Group","Blood Components","Status","ค่าสถานะ","สถานะ(สี)","บันทึก"]
            st.session_state["entries"] = out[cols].reset_index(drop=True)
            st.session_state["flash"] = {"type":"success","text":"อัปเดตตารางแล้ว ✅","until": time.time()+FLASH_SECONDS}
            _safe_rerun()
