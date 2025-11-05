import os, time
from datetime import datetime
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

/* ปุ่มเมนูใน sidebar */
[data-testid="stSidebar"] .stButton>button{
  width:100%; background:#ffffff; color:#111827; border:1px solid #cbd5e1;
  border-radius:12px; font-weight:700; justify-content:flex-start;
}
[data-testid="stSidebar"] .stButton>button:hover{background:#f3f4f6}

/* ฟอร์ม LOGIN ให้เห็นชัด */
[data-testid="stSidebar"] label{ color:#f3f4f6 !important; font-weight:700; }
[data-testid="stSidebar"] input[type="text"],[data-testid="stSidebar"] input[type="password"]{
  background:#ffffff !important; color:#111827 !important;
  border:2px solid #e5e7eb !important; border-radius:10px !important; font-weight:600 !important; caret-color:#111827 !important;
}
[data-testid="stSidebar"] input::placeholder{ color:#6b7280 !important; opacity:1 !important; }
[data-testid="stSidebar"] input:focus{
  outline:none !important; border-color:#ef4444 !important; box-shadow:0 0 0 3px rgba(239,68,68,.25) !important;
}

/* ปุ่ม Login สีแดง */
[data-testid="stSidebar"] button[kind="primary"]{
  width:100%; background:#ef4444 !important; color:#ffffff !important;
  border:none !important; border-radius:10px !important; font-weight:800;
}
[data-testid="stSidebar"] button[kind="primary"]:hover{ filter:brightness(.95); }

/* DataFrame ฟอนต์ชัด */
[data-testid="stDataFrame"] table {font-size:14px;}
[data-testid="stDataFrame"] th {font-size:14px; font-weight:700; color:#111827;}
</style>
""", unsafe_allow_html=True)

# ============ CONFIG ============
BAG_MAX      = 20
CRITICAL_MAX = 4
YELLOW_MAX   = 15
AUTH_PASSWORD = "1234"
FLASH_SECONDS = 2.5

# ============ STATE ============
def _init_state():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("page", "หน้าหลัก")
    st.session_state.setdefault("selected_bt", None)
    st.session_state.setdefault("flash", None)   # {"type","text","until"}
    if "entries" not in st.session_state:
        st.session_state["entries"] = pd.DataFrame(
            columns=["ID","หมู่เลือด","รหัส","ว่าง","จอง","จำหน่าย","หมดอายุ","ค่าสถานะ"]
        )
_init_state()

# ============ HELPERS ============
def _safe_rerun():
    try: st.rerun()
    except Exception: st.experimental_rerun()

def compute_bag(total: int):
    t = max(0, int(total))
    if t <= CRITICAL_MAX: status, label = "red", "วิกฤตใกล้หมด"
    elif t <= YELLOW_MAX: status, label = "yellow", "เพียงพอ"
    else: status, label = "green", "ปกติ"
    pct = max(0, min(100, int(round(100 * min(t, BAG_MAX) / BAG_MAX))))
    return status, label, pct

def bag_color(status: str) -> str:
    return {"green":"#22c55e", "yellow":"#f59e0b", "red":"#ef4444"}[status]

RENAME_TO_UI = {"Plasma": "FFP", "Platelets": "PC"}
UI_TO_DB     = {"LPRC":"LPRC","PRC":"PRC","FFP":"Plasma","PC":"Platelets"}
ALL_PRODUCTS_UI = ["LPRC","PRC","FFP","Cryo","PC"]

def normalize_products(rows):
    d = {name: 0 for name in ALL_PRODUCTS_UI}
    for r in rows:
        name = str(r.get("product_type","")).strip()
        ui = RENAME_TO_UI.get(name, name)
        if ui in d and ui != "Cryo":
            d[ui] += int(r.get("units",0))
    d["Cryo"] = d["LPRC"] + d["PRC"] + d["FFP"] + d["PC"]
    return d

def derive_status(row: dict) -> str:
    """หมดอายุ > จำหน่าย > จอง > ว่าง"""
    try:
        if str(row.get("หมดอายุ") or "").strip() not in ["", "0"]: return "หมดอายุ"
        if str(row.get("จำหน่าย") or "").strip() not in ["", "0"]: return "จำหน่าย"
        if str(row.get("จอง") or "").strip() not in ["", "0"]: return "จอง"
        if str(row.get("ว่าง") or "").strip() not in ["", "0"]: return "ว่าง"
    except Exception:
        pass
    return "ว่าง"

def color_status(val: str) -> str:
    m = {
        "ว่าง": "background-color:#22c55e; color:white; font-weight:700",
        "จอง": "background-color:#f59e0b; color:white; font-weight:700",
        "จำหน่าย": "background-color:#6b7280; color:white; font-weight:700",
        "หมดอายุ": "background-color:#ef4444; color:white; font-weight:700",
    }
    return m.get(str(val).strip(), "")

def bag_svg(blood_type: str, total: int, dist: dict) -> str:
    status, label, pct = compute_bag(total)
    fill = bag_color(status)
    letter_fill = {"A":"#facc15","B":"#f472b6","O":"#60a5fa","AB":"#ffffff"}.get(blood_type, "#ffffff")
    letter_stroke = "#111827" if blood_type != "AB" else "#6b7280"
    cryo_total = int(dist.get("Cryo", total))
    inner_h = 148.0; inner_y0 = 40.0
    water_h = inner_h * pct / 100.0
    water_y = inner_y0 + (inner_h - water_h)
    gid = f"g_{blood_type}"
    wave_amp = 5 + 6*(pct/100)
    wave_path = f"M24,{water_y:.1f} Q54,{water_y - wave_amp:.1f} 84,{water_y:.1f} Q114,{water_y + wave_amp:.1f} 144,{water_y:.1f} L144,198 24,198 Z"
    return f"""
<div>
  <style>
    .bag-wrap{{display:flex;flex-direction:column;align-items:center;gap:10px;font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial}}
    .bag{{transition:transform .18s ease, filter .18s ease}}
    .bag:hover{{transform:translateY(-2px); filter:drop-shadow(0 10px 22px rgba(0,0,0,.12));}}
    .bag-caption{{text-align:center; line-height:1.3; margin-top:2px}}
    .bag-caption .total{{font-weight:800; font-size:16px}}
  </style>
  <div class="bag-wrap">
    <svg class="bag" width="170" height="230" viewBox="0 0 168 206" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <clipPath id="clip-{gid}">
          <path d="M24,40 C24,24 38,14 58,14 L110,14 C130,14 144,24 144,40
                   L144,172 C144,191 128,202 108,204 L56,204 C36,202 24,191 24,172 Z"/>
        </clipPath>
        <linearGradient id="liquid-{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"  stop-color="{fill}" stop-opacity=".96"/>
          <stop offset="100%" stop-color="{fill}" stop-opacity=".86"/>
        </linearGradient>
        <linearGradient id="gloss-{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="rgba(255,255,255,.75)"/>
          <stop offset="100%" stop-color="rgba(255,255,255,0)"/>
        </linearGradient>
        <filter id="rough-{gid}">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="1" seed="8" result="noise"/>
          <feColorMatrix type="saturate" values="0.2" in="SourceGraphic"/>
        </filter>
        <filter id="blood-smear-{gid}" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="2.2"/>
        </filter>
        <filter id="textshadow-{gid}">
          <feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-color="#111827" flood-opacity="0.65"/>
        </filter>
      </defs>
      <circle cx="84" cy="10" r="7.5" fill="#eef2ff" stroke="#dbe0ea" stroke-width="3"/>
      <rect x="77.5" y="14" width="13" height="8" rx="3" fill="#e5e7eb"/>
      <g>
        <path d="M16,34 C16,18 32,8 52,8 L116,8 C136,8 152,18 152,34
                 L152,176 C152,195 136,206 116,206 L52,206 C32,206 16,195 16,176 Z"
              fill="#ffffff" stroke="#7f1d1d" stroke-width="6" opacity=".15" filter="url(#blood-smear-{gid})"/>
        <path d="M16,34 C16,18 32,8 52,8 L116,8 C136,8 152,18 152,34
                 L152,176 C152,195 136,206 116,206 L52,206 C32,206 16,195 16,176 Z"
              fill="#ffffff" stroke="#dc2626" stroke-width="3" filter="url(#rough-{gid})"/>
      </g>
      <g clip-path="url(#clip-{gid})">
        <path d="{wave_path}" fill="url(#liquid-{gid})"/>
      </g>
      <rect x="38" y="22" width="10" height="176" fill="url(#gloss-{gid})" opacity=".7" clip-path="url(#clip-{gid})"/>
      <g>
        <rect x="98" y="24" rx="10" ry="10" width="54" height="22" fill="#ffffff" stroke="#e5e7eb"/>
        <text x="125" y="40" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text>
      </g>
      <text x="84" y="126" text-anchor="middle" font-size="32" font-weight="900"
            style="paint-order: stroke fill" stroke="{letter_stroke}" stroke-width="4"
            fill="{letter_fill}" filter="url(#textshadow-{gid})">{blood_type}</text>
    </svg>
    <div class="bag-caption">
      <div class="total">{cryo_total} unit</div>
      <div style="font-size:12px">{label}</div>
    </div>
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
            unsafe_allow_html=True
        )

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

# ============ HEADER ============
st.title("Blood Stock Real-time Monitor")
st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# แถบแจ้งสถานะมุมขวา (fixed)
if st.session_state.get("flash"):
    now = time.time()
    data = st.session_state["flash"]
    if now < data.get("until", 0):
        color = {
            "success": "#16a34a",
            "info":    "#0ea5e9",
            "warning": "#f59e0b",
            "error":   "#ef4444",
        }.get(data.get("type","success"), "#16a34a")
        st.markdown(
            f"""
            <div style="
                position:fixed; top:90px; right:24px; z-index:9999;
                background:{color}; color:#fff; padding:.70rem 1.0rem;
                border-radius:12px; font-weight:800; box-shadow:0 10px 24px rgba(0,0,0,.18);
                letter-spacing:.2px;">
                {data.get("text","")}
            </div>
            """,
            unsafe_allow_html=True
        )
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
        dist  = normalize_products(get_stock_by_blood(bt))
        with cols[i]:
            st.markdown(f"### ถุงเลือดกรุ๊ป **{bt}**")
            st_html(bag_svg(bt, total, dist), height=270, scrolling=False)
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
        dist_sel  = normalize_products(get_stock_by_blood(sel))
        _L,_M,_R = st.columns([1,1,1])
        with _M:
            st_html(bag_svg(sel, int(total_sel), dist_sel), height=270, scrolling=False)

        df = pd.DataFrame([{"product_type":k, "units":v} for k,v in dist_sel.items()])
        df = df.set_index("product_type").loc[ALL_PRODUCTS_UI].reset_index()
        def color_for(u):
            if u <= CRITICAL_MAX: return "#ef4444"
            if u <= YELLOW_MAX:   return "#f59e0b"
            return "#22c55e"
        df["color"] = df["units"].apply(color_for)
        ymax = max(10, int(df["units"].max() * 1.25))
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("product_type:N", title="ประเภทผลิตภัณฑ์ (LPRC, PRC, FFP, Cryo=รวม, PC)",
                    axis=alt.Axis(labelAngle=0,labelFontSize=14,titleFontSize=14,
                                  labelColor="#111827",titleColor="#111827")),
            y=alt.Y("units:Q", title="จำนวนหน่วย (unit)",
                    scale=alt.Scale(domainMin=0, domainMax=ymax),
                    axis=alt.Axis(labelFontSize=14,titleFontSize=14,
                                  labelColor="#111827",titleColor="#111827")),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=["product_type","units"]
        ).properties(height=360).configure_view(strokeOpacity=0)
        st.altair_chart(chart, use_container_width=True)
        st.dataframe(df.drop(columns=["color"]), use_container_width=True, hide_index=True)

        if st.session_state["logged_in"]:
            st.markdown("#### ปรับปรุงคลัง (ต้องล็อกอิน)")
            c1,c2,c3 = st.columns([1,1,2])
            with c1:
                product_ui = st.selectbox("ประเภทผลิตภัณฑ์", ["LPRC","PRC","FFP","PC"])
            with c2:
                qty = int(st.number_input("จำนวน (หน่วย)", min_value=1, max_value=1000, value=1, step=1))
            with c3:
                note = st.text_input("หมายเหตุ", placeholder="เหตุผลการทำรายการ เช่น นำเข้า/เบิกให้ผู้ป่วย/ทดแทนการหมดอายุ")
            product_db = UI_TO_DB[product_ui]
            current_total = int(total_sel)
            current_by_product = int(dist_sel.get(product_ui, 0))
            b1,b2 = st.columns(2)
            with b1:
                if st.button("➕ นำเข้าเข้าคลัง", use_container_width=True):
                    space = max(0, BAG_MAX - min(current_total, BAG_MAX))
                    add = min(qty, space)
                    if add <= 0:
                        st.warning("เต็มคลังแล้ว (20/20)")
                    else:
                        adjust_stock(sel, product_db, add, actor=st.session_state["username"] or "admin", note=note or "inbound")
                        if add < qty: st.info(f"นำเข้าได้เพียง {add} หน่วย (จำกัดเต็มคลัง 20)")
                        st.session_state["flash"] = {"type":"success","text":"บันทึกการนำเข้าแล้ว ✅","until": time.time()+FLASH_SECONDS}
                        _safe_rerun()
            with b2:
                if st.button("➖ เบิกออกจากคลัง", use_container_width=True):
                    take = min(qty, current_by_product)
                    if take <= 0:
                        st.warning(f"ไม่มี {product_ui} เพียงพอสำหรับการเบิก")
                    else:
                        adjust_stock(sel, product_db, -take, actor=st.session_state["username"] or "admin", note=note or "outbound")
                        if take < qty: st.info(f"ทำการเบิกได้เพียง {take} หน่วย")
                        st.session_state["flash"] = {"type":"success","text":"บันทึกการเบิกแล้ว ✅","until": time.time()+FLASH_SECONDS}
                        _safe_rerun()

# ---------- หน้า: กรอกเลือด ----------
elif page == "กรอกเลือด":
    st.subheader("กรอกเลือด")
    if not st.session_state["logged_in"]:
        st.warning("ต้องล็อกอินก่อนจึงจะใช้งานเมนูนี้ได้")
    else:
        with st.form("blood_entry_form", clear_on_submit=True):
            c1,c2,c3 = st.columns([1,1,1])
            with c1:
                _id = st.text_input("ID")
                blood = st.selectbox("หมู่เลือด", ["A","B","O","AB"])
            with c2:
                code = st.text_input("รหัส")
                free = st.text_input("ว่าง", value="")
            with c3:
                book = st.text_input("จอง", value="")
                sold = st.text_input("จำหน่าย", value="")
            exp = st.text_input("หมดอายุ", value="")
            submit = st.form_submit_button("บันทึก", use_container_width=True)
        if submit:
            new_row = {"ID":_id,"หมู่เลือด":blood,"รหัส":code,"ว่าง":free,"จอง":book,"จำหน่าย":sold,"หมดอายุ":exp}
            new_row["ค่าสถานะ"] = derive_status(new_row)
            st.session_state["entries"] = pd.concat(
                [st.session_state["entries"], pd.DataFrame([new_row])], ignore_index=True
            )
            st.session_state["flash"] = {"type":"success","text":"บันทึกรายการแล้ว ✅","until": time.time()+FLASH_SECONDS}
            _safe_rerun()

        st.markdown("### ตารางสรุป (แก้ไขได้)")

        # Data Editor แก้ไขได้
        df = st.session_state["entries"].copy()
        for col in ["ID","หมู่เลือด","รหัส","ว่าง","จอง","จำหน่าย","หมดอายุ","ค่าสถานะ"]:
            if col not in df.columns:
                df[col] = ""

        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "หมู่เลือด": st.column_config.SelectboxColumn("หมู่เลือด", options=["A","B","O","AB"], required=True),
                "ค่าสถานะ": st.column_config.TextColumn("ค่าสถานะ", help="ระบบคำนวณให้อัตโนมัติ", disabled=True),
            },
            key="entries_editor"
        )

        # คำนวณค่าสถานะใหม่หลังแก้ไข
        if not edited_df.empty:
            edited_df["ค่าสถานะ"] = [
                derive_status(row._asdict() if hasattr(row, "_asdict") else row)
                for _, row in edited_df.iterrows()
            ]

        c_left, c_right = st.columns([1,1])
        with c_left:
            if st.button("บันทึกการแก้ไข", type="primary"):
                st.session_state["entries"] = edited_df.reset_index(drop=True)
                st.session_state["flash"] = {"type":"success","text":"บันทึกการแก้ไขในตารางเรียบร้อย ✅","until": time.time()+FLASH_SECONDS}
                _safe_rerun()
        with c_right:
            if st.button("ล้างตาราง (รีเซ็ต)"):
                st.session_state["entries"] = pd.DataFrame(
                    columns=["ID","หมู่เลือด","รหัส","ว่าง","จอง","จำหน่าย","หมดอายุ","ค่าสถานะ"]
                )
                st.session_state["flash"] = {"type":"warning","text":"ล้างตารางแล้ว","until": time.time()+FLASH_SECONDS}
                _safe_rerun()

        # ตารางอ่านอย่างเดียว พร้อม "สีค่าสถานะ"
        st.markdown("### ตารางสรุป (แสดงสีสถานะ)")
        if st.session_state["entries"].empty:
            st.info("ยังไม่มีรายการ")
        else:
            show_df = st.session_state["entries"].copy()
            # ให้แน่ใจว่ามีคอลัมน์ครบและสถานะอัปเดต
            for col in ["ID","หมู่เลือด","รหัส","ว่าง","จอง","จำหน่าย","หมดอายุ","ค่าสถานะ"]:
                if col not in show_df.columns:
                    show_df[col] = ""
            if not show_df.empty:
                show_df["ค่าสถานะ"] = [
                    derive_status(row._asdict() if hasattr(row, "_asdict") else row)
                    for _, row in show_df.iterrows()
                ]
            st.dataframe(
                show_df.style.applymap(color_status, subset=["ค่าสถานะ"]),
                use_container_width=True, hide_index=True
            )
