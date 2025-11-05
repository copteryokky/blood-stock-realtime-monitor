# app.py
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

/* ปุ่มเมนูใน sidebar */
[data-testid="stSidebar"] .stButton>button{
  width:100%; background:#ffffff; color:#111827; border:1px solid #cbd5e1;
  border-radius:12px; font-weight:700; justify-content:flex-start;
}
[data-testid="stSidebar"] .stButton>button:hover{background:#f3f4f6}

/* ====== ฟอร์ม LOGIN ====== */
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

/* DataFrame font */
[data-testid="stDataFrame"] table {font-size:14px;}
[data-testid="stDataFrame"] th {font-size:14px; font-weight:700; color:#111827;}
</style>
""", unsafe_allow_html=True)

# ============ CONFIG ============
BAG_MAX       = 20          # max ถุงต่อกรุ๊ป
CRITICAL_MAX  = 4
YELLOW_MAX    = 15
CRYO_MAX      = 30          # เผื่อใช้ภายหลัง
AUTH_PASSWORD = "1234"
FLASH_SECONDS = 2.5

# ===== กลุ่ม-สินค้า และ mapping =====
RENAME_TO_UI    = {"Plasma": "FFP", "Platelets": "PC"}
UI_TO_DB        = {"LPRC":"LPRC","PRC":"PRC","FFP":"Plasma","PC":"Platelets"}  # Cryo ไม่มีใน DB
ALL_PRODUCTS_UI = ["LPRC","PRC","FFP","Cryo","PC"]                             # ลำดับคงที่บนกราฟ

# ===== สถานะสำหรับกรอกเลือด =====
STATUS_OPTIONS = ["ว่าง","จอง","จำหน่าย","Exp","หลุดจอง"]
STATUS_COLOR   = {
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
    st.session_state.setdefault("page", "หน้าหลัก")
    st.session_state.setdefault("selected_bt", None)
    st.session_state.setdefault("flash", None)

    # ตารางสำหรับหน้า “กรอกเลือด”
    cols = ["Exp date","Unit number","Group","Blood Components","Status","ค่าสถานะ","สถานะ(สี)","บันทึก"]
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
    """รวมหน่วยของกรุ๊ปเดียว (ไม่รวม Cryo)"""
    d = {name: 0 for name in ALL_PRODUCTS_UI}
    for r in rows:
        name = str(r.get("product_type","")).strip()
        ui = RENAME_TO_UI.get(name, name)
        if ui in d and ui != "Cryo":
            d[ui] += int(r.get("units",0))
    return d

def get_global_cryo():
    """Cryo = รวมหน่วยของทุกกรุ๊ป/ทุก component (LPRC,PRC,FFP,PC)"""
    total = 0
    for bt in ["A","B","O","AB"]:
        rows = get_stock_by_blood(bt)
        for r in rows:
            name = str(r.get("product_type","")).strip()
            ui = RENAME_TO_UI.get(name, name)
            if ui != "Cryo":
                total += int(r.get("units",0))
    return total

# ===== SVG ถุงเลือด (ไม่มีตัวเลข unit ใต้ถุง) =====
def bag_svg(blood_type: str, total: int, dist: dict) -> str:
    status, label, pct = compute_bag(total, BAG_MAX)
    fill = bag_color(status)
    letter_fill = {"A":"#facc15","B":"#f472b6","O":"#60a5fa","AB":"#ffffff"}.get(blood_type, "#ffffff")
    letter_stroke = "#111827" if blood_type != "AB" else "#6b7280"

    inner_h = 148.0; inner_y0 = 40.0
    water_h = inner_h * pct / 100.0
    water_y = inner_y0 + (inner_h - water_h)
    gid = f"g_{blood_type}"
    wave_amp = 5 + 6*(pct/100)
    wave_path = f"M24,{water_y:.1f} Q54,{water_y - wave_amp:.1f} 84,{water_y:.1f} " \
                f"Q114,{water_y + wave_amp:.1f} 144,{water_y:.1f} L144,198 24,198 Z"

    return f"""
<div>
  <style>
    .bag-wrap{{display:flex;flex-direction:column;align-items:center;gap:10px;
               font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial}}
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
          <stop offset="0%"  stop-color="{fill}" stop-opacity=".96"/>
          <stop offset="100%" stop-color="{fill}" stop-opacity=".86"/>
        </linearGradient>
        <linearGradient id="gloss-{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="rgba(255,255,255,.75)"/>
          <stop offset="100%" stop-color="rgba(255,255,255,0)"/>
        </linearGradient>
      </defs>

      <circle cx="84" cy="10" r="7.5" fill="#eef2ff" stroke="#dbe0ea" stroke-width="3"/>
      <rect x="77.5" y="14" width="13" height="8" rx="3" fill="#e5e7eb"/>

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
            fill="{letter_fill}">{blood_type}</text>
    </svg>
    <div style="font-size:12px">{label}</div>
  </div>
</div>
"""

# ============ INIT DB ============
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()

# ============ SIDEBAR ============
with st.sidebar:
    # การ์ดชื่อผู้ใช้
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

    # Login form
    if st.session_state["page"] == "เข้าสู่ระบบ" and not st.session_state["logged_in"]:
        st.markdown("### เข้าสู่ระบบ")
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input("Username", key="login_user",
                              placeholder="พิมพ์ชื่อผู้ใช้ได้เลย", label_visibility="visible")
            p = st.text_input("Password", key="login_pwd",
                              type="password", placeholder="ใส่รหัส = 1234", label_visibility="visible")
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

# Flash แจ้งเตือนมุมขวาบน
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
            st_html(bag_svg(bt, total, dist), height=260, scrolling=False)
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
        dist_sel["Cryo"] = get_global_cryo()  # Cryo = รวมทุกกรุ๊ป

        _L,_M,_R = st.columns([1,1,1])
        with _M:
            st_html(bag_svg(sel, int(total_sel), dist_sel), height=260, scrolling=False)

        # ตาราง + กราฟ (ลำดับคงที่ + ตัวเลขบนแท่ง)
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
            x=alt.X("product_type:N", title="ประเภทผลิตภัณฑ์ (LPRC, PRC, FFP, Cryo=รวมทุกกรุ๊ป, PC)",
                    axis=alt.Axis(labelAngle=0,labelFontSize=14,titleFontSize=14,
                                  labelColor="#111827",titleColor="#111827")),
            y=alt.Y("units:Q", title="จำนวนหน่วย (unit)",
                    scale=alt.Scale(domainMin=0, domainMax=ymax),
                    axis=alt.Axis(labelFontSize=14,titleFontSize=14,
                                  labelColor="#111827",titleColor="#111827")),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=["product_type","units"]
        )
        text = alt.Chart().mark_text(align="center", baseline="bottom", dy=-4, fontSize=14)\
                          .encode(x="product_type:N", y="units:Q", text="units:Q")
        chart = alt.layer(bars, text, data=df).properties(height=360).configure_view(strokeOpacity=0)

        st.altair_chart(chart, use_container_width=True)
        st.dataframe(df[["product_type","units"]], use_container_width=True, hide_index=True)

        # ปรับปรุงคลัง (ต้องล็อกอิน)
        if st.session_state["logged_in"]:
            st.markdown("#### ปรับปรุงคลัง (ต้องล็อกอิน)")
            c1,c2,c3 = st.columns([1,1,2])
            with c1:
                product_ui = st.selectbox("ประเภทผลิตภัณฑ์", ["LPRC","PRC","FFP","PC","Cryo"])
            with c2:
                qty = int(st.number_input("จำนวน (หน่วย)", min_value=1, max_value=1000, value=1, step=1))
            with c3:
                note = st.text_input("หมายเหตุ", placeholder="เหตุผลการทำรายการ เช่น นำเข้า/เบิก")

            current_by_product = int(dist_sel.get(product_ui, 0))
            b1,b2 = st.columns(2)

            # นำเข้า (ยกเว้น Cryo)
            with b1:
                if st.button("➕ นำเข้าเข้าคลัง", use_container_width=True, disabled=(product_ui=="Cryo")):
                    if product_ui == "Cryo":
                        st.warning("Cryo คำนวณจากยอดรวมทุกกรุ๊ป ไม่สามารถนำเข้าโดยตรงได้")
                    else:
                        product_db = UI_TO_DB[product_ui]
                        space = max(0, BAG_MAX - min(int(total_sel), BAG_MAX))
                        add = min(qty, space)
                        if add <= 0:
                            st.warning("เต็มคลังแล้ว (20/20)")
                        else:
                            adjust_stock(sel, product_db, add, actor=st.session_state["username"] or "admin", note=note or "inbound")
                            if add < qty: st.info(f"นำเข้าได้เพียง {add} หน่วย (จำกัดเต็มคลัง 20)")
                            st.session_state["flash"] = {"type":"success","text":"บันทึกการนำเข้าแล้ว ✅","until": time.time()+FLASH_SECONDS}
                            _safe_rerun()

            # เบิกออก
            with b2:
                if st.button("➖ เบิกออกจากคลัง", use_container_width=True):
                    if product_ui == "Cryo":
                        # กระจายหักทุกกรุ๊ปตามลำดับสำคัญ
                        priority = ["PRC","LPRC","FFP","PC"]
                        remain_all = qty
                        for bt in ["A","B","O","AB"]:
                            if remain_all <= 0: break
                            dist_bt = normalize_products(get_stock_by_blood(bt))
                            for p in priority:
                                have = int(dist_bt.get(p,0))
                                if have <= 0: 
                                    continue
                                take = min(remain_all, have)
                                if take > 0:
                                    adjust_stock(bt, UI_TO_DB[p], -take, actor=st.session_state["username"] or "admin",
                                                 note=note or "cryo-outbound")
                                    remain_all -= take
                                if remain_all == 0: break
                        st.session_state["flash"] = {"type":"success","text":"เบิก Cryo แล้ว (หักทุกกรุ๊ป) ✅","until": time.time()+FLASH_SECONDS}
                        _safe_rerun()
                    else:
                        product_db = UI_TO_DB[product_ui]
                        have = current_by_product
                        take = min(qty, have)
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
        # ===== ฟอร์มกรอก: layout ตามภาพ =====
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
            # เก็บ Exp date แบบ YYYY/MM/DD ให้เหมือนภาพ
            if isinstance(exp_date, date):
                exp_str = exp_date.strftime("%Y/%m/%d")
            else:
                exp_str = str(exp_date)

            k_status = status
            color_status = STATUS_COLOR.get(status, status)
            new_row = {
                "Exp date": exp_str,
                "Unit number": unit_number,
                "Group": group,
                "Blood Components": component,
                "Status": status,
                "ค่าสถานะ": k_status,
                "สถานะ(สี)": color_status,
                "บันทึก": note,
            }
            st.session_state["entries"] = pd.concat(
                [st.session_state["entries"], pd.DataFrame([new_row])], ignore_index=True
            )
            st.session_state["flash"] = {"type":"success","text":"บันทึกรายการแล้ว ✅","until": time.time()+FLASH_SECONDS}
            _safe_rerun()

        st.markdown("### ตารางสรุป (แก้ไขได้)")
        df_vis = st.session_state["entries"].copy()

        # ให้ Data Editor โชว์เป็น YYYY/MM/DD ตามภาพ
        # ถ้าแถวไหนว่าง/แปลงไม่ได้ จะคงค่าสตริงเดิมไว้
        def _to_date_for_editor(x):
            try:
                return pd.to_datetime(x, errors="coerce").date()
            except Exception:
                return pd.NaT
        _tmp = pd.to_datetime(df_vis["Exp date"], errors="coerce")
        df_vis["Exp date"] = _tmp.dt.date

        col_cfg = {
            "Exp date": st.column_config.DateColumn("Exp date", format="YYYY/MM/DD"),
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

        # ถ้ามีการแก้ไข แปลงกลับเป็น string YYYY/MM/DD แล้วเก็บคืน state
        if not edited.equals(df_vis):
            out = edited.copy()

            def _d2str(x):
                if pd.isna(x): return ""
                if isinstance(x, (datetime, pd.Timestamp)): return x.date().strftime("%Y/%m/%d")
                if isinstance(x, date): return x.strftime("%Y/%m/%d")
                # ถ้าเป็นสตริงอยู่แล้วให้พยายาม normalize รูปแบบ
                try:
                    return pd.to_datetime(x, errors="coerce").date().strftime("%Y/%m/%d")
                except Exception:
                    return str(x)

            out["Exp date"] = out["Exp date"].apply(_d2str)
            out["ค่าสถานะ"] = out["Status"].astype(str)
            out["สถานะ(สี)"] = out["Status"].map(lambda s: STATUS_COLOR.get(s, s))

            for c in ["Unit number","Group","Blood Components","Status","ค่าสถานะ","สถานะ(สี)","บันทึก"]:
                out[c] = out[c].astype(str).fillna("")

            cols = ["Exp date","Unit number","Group","Blood Components","Status","ค่าสถานะ","สถานะ(สี)","บันทึก"]
            out = out[cols]
            st.session_state["entries"] = out.reset_index(drop=True)
            st.session_state["flash"] = {"type":"success","text":"อัปเดตตารางแล้ว ✅","until": time.time()+FLASH_SECONDS}
            _safe_rerun()
