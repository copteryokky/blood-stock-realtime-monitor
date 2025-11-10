# app.py (fixed types for Data Editor)
import os, time
from datetime import datetime, date, datetime as dt
import pandas as pd
import altair as alt
import streamlit as st
from streamlit.components.v1 import html as st_html

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    def st_autorefresh(*args, **kwargs): return None

from db import init_db, get_all_status, get_stock_by_blood, adjust_stock

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
[data-testid="stSidebar"] label{color:#f3f4f6 !important;font-weight:700;}
[data-testid="stSidebar"] input[type="text"],[data-testid="stSidebar"] input[type="password"]{background:#ffffff !important;color:#111827 !important;border:2px solid #e5e7eb !important;border-radius:10px !important;font-weight:600 !important}
[data-testid="stSidebar"] input:focus{outline:none !important;border-color:#ef4444 !important;box-shadow:0 0 0 3px rgba(239,68,68,.25) !important}
[data-testid="stSidebar"] button[kind="primary"]{width:100%;background:#ef4444 !important;color:#ffffff !important;border:none !important;border-radius:10px !important;font-weight:800}
[data-testid="stSidebar"] button[kind="primary"]:hover{filter:brightness(.95)}
[data-testid="stDataFrame"] table {font-size:14px;}
[data-testid="stDataFrame"] th {font-size:14px;font-weight:700;color:#111827;}
.badge-pill{display:inline-flex;align-items:center;gap:.4rem;padding:.15rem .5rem;border-radius:999px;font-weight:700;font-size:12px}
.badge-green{background:#e8f9ee;color:#047857;border:1px solid #a7f3d0}
.badge-amber{background:#fff7ed;color:#b45309;border:1px solid #fed7aa}
.badge-red{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca}
.badge-gray{background:#f3f4f6;color:#374151;border:1px solid #e5e7eb}
</style>
""", unsafe_allow_html=True)

BAG_MAX = 20
CRITICAL_MAX, YELLOW_MAX = 4, 15
AUTH_PASSWORD = "1234"
FLASH_SECONDS = 2.5

RENAME_TO_UI    = {"Plasma": "FFP", "Platelets": "PC"}
UI_TO_DB        = {"LPRC":"LPRC","PRC":"PRC","FFP":"Plasma","PC":"Platelets"}
ALL_PRODUCTS_UI = ["LPRC","PRC","FFP","Cryo","PC"]
STATUS_OPTIONS  = ["ว่าง","จอง","จำหน่าย","Exp","หลุดจอง"]

def _init_state():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("page", "หน้าหลัก")
    st.session_state.setdefault("selected_bt", None)
    st.session_state.setdefault("flash", None)
    cols = ["Created at (YYYY/MM/DD)","Exp date","วันหมดอายุคงเหลือ (วัน)","Unit number",
            "Group","Blood Components","Status","สถานะวันหมดอายุ","บันทึก"]
    if "entries" not in st.session_state:
        st.session_state["entries"] = pd.DataFrame(columns=cols)
    else:
        for c in cols:
            if c not in st.session_state["entries"].columns:
                st.session_state["entries"][c] = ""
        st.session_state["entries"] = st.session_state["entries"][cols]
_init_state()

def _safe_rerun():
    try: st.rerun()
    except Exception: st.experimental_rerun()

def compute_bag(total: int, max_cap=BAG_MAX):
    t = max(0, int(total))
    if t <= CRITICAL_MAX: status="red"
    elif t <= YELLOW_MAX: status="yellow"
    else: status="green"
    pct = max(0, min(100, int(round(100 * min(t, max_cap) / max_cap))))
    return status, pct

def bag_color(status: str) -> str:
    return {"green":"#22c55e","yellow":"#f59e0b","red":"#ef4444"}[status]

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

def days_left_badge(exp_val):
    if exp_val in (None, "", "None"):
        return "", '<span class="badge-pill badge-gray">-</span>'
    if isinstance(exp_val, str):
        d = pd.to_datetime(exp_val, errors="coerce")
        if pd.isna(d): return "", '<span class="badge-pill badge-gray">-</span>'
        exp_d = d.date()
    elif isinstance(exp_val, (dt, pd.Timestamp)):
        exp_d = exp_val.date()
    elif isinstance(exp_val, date):
        exp_d = exp_val
    else:
        return "", '<span class="badge-pill badge-gray">-</span>'
    days = (exp_d - date.today()).days
    if days <= 0: return days, f'<span class="badge-pill badge-red">หมดอายุ ({days} วัน)</span>'
    if days <= 3: return days, f'<span class="badge-pill badge-red">เร่งด่วน (เหลือ {days} วัน)</span>'
    if days <= 8: return days, f'<span class="badge-pill badge-amber">ใกล้ครบกำหนด (เหลือ {days} วัน)</span>'
    return days, f'<span class="badge-pill badge-green">ปกติ (เหลือ {days} วัน)</span>'

def bag_svg(blood_type: str, total: int) -> str:
    status, pct = compute_bag(total, BAG_MAX)
    fill = bag_color(status)
    letter_fill = {"A":"#facc15","B":"#f472b6","O":"#60a5fa","AB":"#ffffff"}.get(blood_type, "#ffffff")
    inner_h = 148.0; inner_y0 = 40.0
    water_h = inner_h * pct / 100.0
    water_y = inner_y0 + (inner_h - water_h)
    gid = f"g_{blood_type}"
    wave_amp = 5 + 6*(pct/100)
    wave_path = (f"M24,{water_y:.1f} Q54,{water_y - wave_amp:.1f} 84,{water_y:.1f} "
                 f"Q114,{water_y + wave_amp:.1f} 144,{water_y:.1f} L144,198 24,198 Z")
    return f"""
<div><div class="bag-wrap" style='display:flex;flex-direction:column;align-items:center;gap:10px;font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial'>
<svg width="170" height="230" viewBox="0 0 168 206" xmlns="http://www.w3.org/2000/svg" style="transition:transform .18s ease, filter .18s ease">
  <defs>
    <clipPath id="clip-{gid}">
      <path d="M24,40 C24,24 38,14 58,14 L110,14 C130,14 144,24 144,40 L144,172 C144,191 128,202 108,204 L56,204 C36,202 24,191 24,172 Z"/>
    </clipPath>
    <linearGradient id="liquid-{gid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="{fill}" stop-opacity=".96"/>
      <stop offset="100%" stop-color="{fill}" stop-opacity=".86"/>
    </linearGradient>
  </defs>
  <circle cx="84" cy="10" r="7.5" fill="#eef2ff" stroke="#dbe0ea" stroke-width="3"/>
  <rect x="77.5" y="14" width="13" height="8" rx="3" fill="#e5e7eb"/>
  <g>
    <path d="M16,34  C16,18 32,8 52,8 L116,8 C136,8 152,18 152,34  L152,176 C152,195 136,206 116,206 L52,206 C32,206 16,195 16,176 Z"
          fill="#ffffff" stroke="#5a0f16" stroke-width="7" opacity=".22"/>
    <path d="M16,34  C16,18 32,8 52,8 L116,8 C136,8 152,18 152,34  L152,176 C152,195 136,206 116,206 L52,206 C32,206 16,195 16,176 Z"
          fill="#ffffff" stroke="#800000" stroke-width="3"/>
  </g>
  <g clip-path="url(#clip-{gid})">
    <path d="{wave_path}" fill="url(#liquid-{gid})"/>
  </g>
  <g><rect x="98" y="24" rx="10" ry="10" width="54" height="22" fill="#ffffff" stroke="#e5e7eb"/>
     <text x="125" y="40" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text></g>
  <text x="84" y="126" text-anchor="middle" font-size="32" font-weight="900" style="paint-order: stroke fill" stroke="#111827" stroke-width="4" fill="{letter_fill}">{blood_type}</text>
</svg>
</div></div>
"""

if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()

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

st.title("Blood Stock Real-time Monitor")
st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

if st.session_state.get("flash"):
    now = time.time()
    data = st.session_state["flash"]
    if now < data.get("until", 0):
        color = {"success":"#16a34a","info":"#0ea5e9","warning":"#f59e0b","error":"#ef4444"}.get(data.get("type","success"),"#16a34a")
        st.markdown(f"""
        <div style="position:fixed; top:110px; right:24px; z-index:9999;
                    background:{color}; color:#fff; padding:.7rem 1rem; border-radius:12px;
                    font-weight:800; box-shadow:0 10px 24px rgba(0,0,0,.18)">
            {data.get("text","")}
        </div>""", unsafe_allow_html=True)
    else:
        st.session_state["flash"] = None

def parse_dates_safe(s):
    if pd.isna(s) or s in ("", None): return ""
    try:
        d = pd.to_datetime(s, errors="coerce")
        if pd.isna(d): return ""
        return d.date().strftime("%Y/%m/%d")
    except Exception:
        return ""

def read_uploaded_file(file) -> pd.DataFrame:
    name = (file.name or "").lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file)
    elif name.endswith(".xlsx"):
        df = pd.read_excel(file, engine="openpyxl")
    elif name.endswith(".xls"):
        df = pd.read_excel(file, engine="xlrd")
    else:
        raise RuntimeError("รองรับเฉพาะไฟล์ .xlsx, .xls, .csv")

    rename_map = {
        "created_at":"Created at (YYYY/MM/DD)","created at":"Created at (YYYY/MM/DD)",
        "exp":"Exp date","exp_date":"Exp date","unit":"Unit number","unit number":"Unit number",
        "group":"Group","blood components":"Blood Components","components":"Blood Components",
        "status":"Status","note":"บันทึก"
    }
    df = df.rename(columns={c: rename_map.get(str(c).strip().lower(), c) for c in df.columns})
    for col in ["Exp date","Unit number","Group","Blood Components","Status","บันทึก"]:
        if col not in df.columns: df[col] = ""
    if "Created at (YYYY/MM/DD)" not in df.columns:
        df["Created at (YYYY/MM/DD)"] = date.today().strftime("%Y/%m/%d")

    df["Created at (YYYY/MM/DD)"] = df["Created at (YYYY/MM/DD)"].apply(parse_dates_safe)
    df["Exp date"] = df["Exp date"].apply(parse_dates_safe)

    days, badges = [], []
    for _, row in df.iterrows():
        d, b = days_left_badge(row.get("Exp date",""))
        days.append(d if d != "" else "")
        badges.append(b)
    df.insert(df.columns.get_loc("Exp date")+1, "วันหมดอายุคงเหลือ (วัน)", days)
    df.insert(df.columns.get_loc("Status")+1, "สถานะวันหมดอายุ", badges)

    final_cols = ["Created at (YYYY/MM/DD)","Exp date","วันหมดอายุคงเหลือ (วัน)",
                  "Unit number","Group","Blood Components","Status","สถานะวันหมดอายุ","บันทึก"]
    return df.reindex(columns=final_cols, fill_value="")

def recalc_badges_inplace(df: pd.DataFrame):
    if df.empty or "Exp date" not in df.columns: return df
    new_days, new_badges = [], []
    for _, row in df.iterrows():
        d, badge = days_left_badge(row.get("Exp date",""))
        new_days.append(d if d != "" else "")
        new_badges.append(badge)
    df["วันหมดอายุคงเหลือ (วัน)"] = new_days
    df["สถานะวันหมดอายุ"] = new_badges
    return df

page = st.session_state["page"]

# ---------- หน้าหลัก ----------
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
                st.session_state["selected_bt"] = bt
                _safe_rerun()

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
        order = pd.CategoricalDtype(ALL_PRODUCTS_UI, ordered=True)
        df["product_type"] = df["product_type"].astype(order)
        df = df.sort_values("product_type").reset_index(drop=True)

        def color_for(u):
            if u <= CRITICAL_MAX: return "#ef4444"
            if u <= YELLOW_MAX:   return "#f59e0b"
            return "#22c55e"
        df["color"] = df["units"].apply(color_for)
        ymax = max(10, int(df["units"].max() * 1.25))

        bars = alt.Chart().mark_bar().encode(
            x=alt.X("product_type:N", title="ประเภทผลิตภัณฑ์ (ลำดับ: LPRC, PRC, FFP, Cryo, PC)",
                    axis=alt.Axis(labelAngle=0,labelFontSize=14,titleFontSize=14,labelColor="#111827",titleColor="#111827")),
            y=alt.Y("units:Q", title="จำนวนหน่วย (unit)",
                    scale=alt.Scale(domainMin=0, domainMax=ymax),
                    axis=alt.Axis(labelFontSize=14,titleFontSize=14,labelColor="#111827",titleColor="#111827")),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=["product_type","units"]
        )
        text = alt.Chart().mark_text(align="center", baseline="bottom", dy=-4, fontSize=14)\
                          .encode(x="product_type:N", y="units:Q", text="units:Q")
        chart = alt.layer(bars, text, data=df).properties(height=360).configure_view(strokeOpacity=0)
        st.altair_chart(chart, use_container_width=True)

# ---------- กรอกเลือด (รวมอัปโหลดไฟล์) ----------
elif page == "กรอกเลือด":
    st.subheader("กรอกเลือด")
    if not st.session_state["logged_in"]:
        st.warning("ต้องล็อกอินก่อนจึงจะใช้งานเมนูนี้ได้")
    else:
        with st.form("blood_entry_form", clear_on_submit=True):
            c1,c2 = st.columns(2)
            with c1: unit_number = st.text_input("Unit number")
            with c2: exp_date = st.date_input("Exp date", value=date.today())
            c3,c4 = st.columns(2)
            with c3: group = st.selectbox("Group", ["A","B","O","AB"])
            with c4: status = st.selectbox("Status", STATUS_OPTIONS, index=0)
            c5,c6 = st.columns(2)
            with c5: component = st.selectbox("Blood Components", ["LPRC","PRC","FFP","Cryo","PC"])
            with c6: note = st.text_input("บันทึก")
            submitted = st.form_submit_button("บันทึกรายการ", use_container_width=True)

        if submitted:
            created_str = date.today().strftime("%Y/%m/%d")
            exp_str = exp_date.strftime("%Y/%m/%d")
            dleft, badge = days_left_badge(exp_str)
            new_row = {
                "Created at (YYYY/MM/DD)": created_str,
                "Exp date": exp_str,
                "วันหมดอายุคงเหลือ (วัน)": dleft if dleft != "" else "",
                "Unit number": unit_number, "Group": group,
                "Blood Components": component, "Status": status,
                "สถานะวันหมดอายุ": badge, "บันทึก": note,
            }
            st.session_state["entries"] = pd.concat(
                [st.session_state["entries"], pd.DataFrame([new_row])], ignore_index=True
            )
            st.session_state["flash"] = {"type":"success","text":"บันทึกรายการแล้ว ✅","until": time.time()+FLASH_SECONDS}
            _safe_rerun()

        st.markdown("### นำเข้าจาก Excel/CSV (อัปโหลดแล้วลงตารางอัตโนมัติ)")
        up = st.file_uploader("เลือดไฟล์ (.xlsx, .xls, .csv)", type=["xlsx","xls","csv"])
        mode = st.radio("โหมดนำเข้า", ["รวมกับตาราง (merge/update)","แทนที่ทั้งหมด (replace)"],
                        horizontal=True, index=0)
        if up is not None:
            try:
                df_new = read_uploaded_file(up)
                if mode.startswith("แทนที่"):
                    st.session_state["entries"] = df_new.copy()
                else:
                    st.session_state["entries"] = pd.concat([st.session_state["entries"], df_new],
                                                            ignore_index=True)
                st.success(f"นำเข้า {len(df_new)} แถวสำเร็จ ✅")
            except Exception as e:
                st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")

        st.markdown("### ตารางสรุป (แก้ไขได้)")
        df_vis = recalc_badges_inplace(st.session_state["entries"].copy())

        # >>> บังคับชนิดข้อมูลให้ตรง column_config <<<
        df_vis["Created at (YYYY/MM/DD)"] = pd.to_datetime(df_vis["Created at (YYYY/MM/DD)"], errors="coerce")
        df_vis["Exp date"] = pd.to_datetime(df_vis["Exp date"], errors="coerce")
        df_vis["วันหมดอายุคงเหลือ (วัน)"] = pd.to_numeric(df_vis["วันหมดอายุคงเหลือ (วัน)"], errors="coerce")

        col_cfg = {
            "Created at (YYYY/MM/DD)": st.column_config.DateColumn("Created at (YYYY/MM/DD)", format="YYYY/MM/DD"),
            "Exp date": st.column_config.DateColumn("Exp date", format="YYYY/MM/DD"),
            "วันหมดอายุคงเหลือ (วัน)": st.column_config.NumberColumn("วันหมดอายุคงเหลือ (วัน)", step=1),
            "สถานะวันหมดอายุ": st.column_config.TextColumn("สถานะวันหมดอายุ", disabled=True),
            "Unit number": st.column_config.TextColumn("Unit number"),
            "Group": st.column_config.SelectboxColumn("Group", options=["A","B","O","AB"]),
            "Blood Components": st.column_config.SelectboxColumn("Blood Components", options=ALL_PRODUCTS_UI),
            "Status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS),
            "บันทึก": st.column_config.TextColumn("บันทึก"),
        }

        edited = st.data_editor(
            df_vis, num_rows="dynamic", use_container_width=True, hide_index=True, column_config=col_cfg
        )

        if not edited.equals(df_vis):
            out = edited.copy()

            def _to_datestr(x):
                if pd.isna(x): return ""
                if isinstance(x, (pd.Timestamp, datetime)): return x.date().strftime("%Y/%m/%d")
                if isinstance(x, date): return x.strftime("%Y/%m/%d")
                try:
                    d = pd.to_datetime(x, errors="coerce")
                    return "" if pd.isna(d) else d.date().strftime("%Y/%m/%d")
                except Exception:
                    return ""

            out["Created at (YYYY/MM/DD)"] = out["Created at (YYYY/MM/DD)"].apply(_to_datestr)
            out["Exp date"] = out["Exp date"].apply(_to_datestr)
            out = recalc_badges_inplace(out)
            cols = ["Created at (YYYY/MM/DD)","Exp date","วันหมดอายุคงเหลือ (วัน)",
                    "Unit number","Group","Blood Components","Status","สถานะวันหมดอายุ","บันทึก"]
            st.session_state["entries"] = out[cols].reset_index(drop=True)
            st.session_state["flash"] = {"type":"success","text":"อัปเดตตารางแล้ว ✅","until": time.time()+FLASH_SECONDS}
            _safe_rerun()
