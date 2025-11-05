# app.py
import os
from datetime import datetime
import pandas as pd
import altair as alt
import streamlit as st
from streamlit.components.v1 import html as st_html  # สำหรับเรนเดอร์ SVG

# ===== Auto refresh helper =====
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    def st_autorefresh(*args, **kwargs): return None

# ---- เชื่อมฟังก์ชัน DB เดิมของคุณ ----
from db import init_db, get_all_status, get_stock_by_blood, adjust_stock

# ====== PAGE CONFIG & THEME ======
st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")
st.markdown("""
<style>
.block-container{padding-top:.8rem;}
h1,h2,h3{letter-spacing:.2px}
.badge{display:inline-flex;align-items:center;gap:.4rem;padding:.25rem .5rem;border-radius:999px;background:#f3f4f6}
.legend-dot{width:.7rem;height:.7rem;border-radius:999px;display:inline-block}
.stButton>button{border-radius:12px;padding:.55rem 1rem;font-weight:600}

/* sidebar nav */
.sidebar-title{ font-weight:800;color:#111827;font-size:14px;margin:8px 0 4px 2px; }
.nav-item{ padding:8px 10px; border-radius:10px; cursor:pointer; display:flex; gap:.6rem; align-items:center; }
.nav-item:hover{ background:#f3f4f6; }
.nav-item.active{ background:#e6f0ff; border:1px solid #dbeafe; }
.nav-icon{ width:18px; text-align:center; }
.nav-label{ font-weight:700 }

/* data font */
[data-testid="stDataFrame"] table {font-size:14px;}
[data-testid="stDataFrame"] th {font-size:14px;font-weight:700;color:#111827;}

/* status chip */
.chip { display:inline-flex; align-items:center; gap:.4rem; padding:.2rem .55rem; border-radius:999px; font-weight:700; font-size:12px; }
.chip.green { background:#ecfdf5; color:#065f46; }
.chip.yellow{ background:#fffbeb; color:#92400e; }
.chip.gray  { background:#f3f4f6; color:#374151; }
.chip.red   { background:#fef2f2; color:#991b1b; }
</style>
""", unsafe_allow_html=True)

# ===== CONFIG (เหมือนเดิม) =====
BAG_MAX      = 20
CRITICAL_MAX = 4
YELLOW_MAX   = 15

# ===== Helpers (เหมือนเดิม) =====
def compute_bag(total: int):
    t = max(0, int(total))
    if t <= CRITICAL_MAX:
        status, label = "red", "วิกฤตใกล้หมด"
    elif t <= YELLOW_MAX:
        status, label = "yellow", "เพียงพอ"
    else:
        status, label = "green", "ปกติ"
    pct = max(0, min(100, int(round(100 * min(t, BAG_MAX) / BAG_MAX))))
    return status, label, pct

def bag_color(status: str) -> str:
    return {"green":"#22c55e", "yellow":"#f59e0b", "red":"#ef4444"}[status]

def norm_pin(s:str)->str:
    trans = str.maketrans("๐๑๒๓๔๕๖๗๘๙","0123456789")
    return (s or "").translate(trans).strip()

# ชื่อผลิตภัณฑ์ใน UI
RENAME_TO_UI = {"Plasma": "FFP", "Platelets": "PC"}
UI_TO_DB     = {"LPRC": "LPRC", "PRC": "PRC", "FFP": "Plasma", "PC": "Platelets"}
ALL_PRODUCTS_UI = ["LPRC", "PRC", "FFP", "Cryo", "PC"]

def normalize_products(rows):
    d = {name: 0 for name in ALL_PRODUCTS_UI}
    for r in rows:
        name = str(r.get("product_type","")).strip()
        ui = RENAME_TO_UI.get(name, name)
        if ui in d and ui != "Cryo":
            d[ui] += int(r.get("units",0))
    d["Cryo"] = d["LPRC"] + d["PRC"] + d["FFP"] + d["PC"]
    return d

# ===== SVG ถุงเลือด (เหมือนเดิม – ไม่มีกราฟในถุง) =====
def bag_svg_with_distribution(blood_type: str, total: int, dist: dict) -> str:
    status, label, pct = compute_bag(total)
    fill = bag_color(status)
    letter_fill = {"A": "#facc15", "B": "#f472b6", "O": "#60a5fa", "AB": "#ffffff"}.get(blood_type, "#ffffff")
    letter_stroke = "#111827" if blood_type != "AB" else "#6b7280"
    cryo_total = int(dist.get("Cryo", total))

    inner_h = 148.0
    inner_y0 = 40.0
    water_h = inner_h * pct / 100.0
    water_y = inner_y0 + (inner_h - water_h)

    gid = f"g_{blood_type}"
    wave_amp = 5 + 6*(pct/100)
    wave_path = (
        f"M24,{water_y:.1f} Q54,{water_y - wave_amp:.1f} 84,{water_y:.1f} "
        f"Q114,{water_y + wave_amp:.1f} 144,{water_y:.1f} L144,198 24,198 Z"
    )

    return f"""
<div>
  <div class="bag-wrap" style="display:flex;flex-direction:column;align-items:center;gap:10px;font-family:ui-sans-serif,system-ui,Segoe UI,Roboto,Arial">
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
        <filter id="rough-{gid}"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="1" seed="8"/></filter>
        <filter id="blood-smear-{gid}" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.2"/></filter>
        <filter id="textshadow-{gid}"><feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-color="#111827" flood-opacity="0.65"/></filter>
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

      <g>
        <rect x="98" y="24" rx="10" ry="10" width="54" height="22" fill="#ffffff" stroke="#e5e7eb"/>
        <text x="125" y="40" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text>
      </g>

      <text x="84" y="126" text-anchor="middle" font-size="32" font-weight="900"
            style="paint-order: stroke fill" stroke="{letter_stroke}" stroke-width="4"
            fill="{letter_fill}" filter="url(#textshadow-{gid})">{blood_type}</text>
    </svg>

    <div class="bag-caption" style="text-align:center;line-height:1.3;margin-top:2px">
      <div class="total" style="font-weight:800;font-size:16px">{cryo_total} unit</div>
      <div style="font-size:12px">{label}</div>
    </div>
  </div>
</div>
"""

# ===== Init DB =====
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()
ADMIN_KEY = os.environ.get("BLOOD_ADMIN_KEY", "1234")

# ===== Sidebar (เพิ่มเฉพาะเมนู แต่ฟังก์ชันเดิม) =====
if "page" not in st.session_state:
    st.session_state.page = "dashboard"  # แบบเดิม

st.sidebar.markdown('<div class="sidebar-title">เมนู</div>', unsafe_allow_html=True)
def nav_btn(label, key, icon=""):
    active = st.session_state.page == key
    style = "nav-item active" if active else "nav-item"
    placeholder = st.sidebar.container()
    if placeholder.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
        st.session_state.page = key
        st.rerun()

# Auto-refresh & Controls (แบบเดิม)
st_autorefresh_ms = st.sidebar.number_input("Auto-refresh (ms)", 1000, 60000, 5000, step=500)
st_autorefresh(interval=st_autorefresh_ms, key="auto_refresh")

with st.sidebar:
    st.header("Controls")
    admin_mode = st.toggle("Update Mode (สำหรับเจ้าหน้าที่)", value=False)
    pin_ok = False
    if admin_mode:
        pin = st.text_input("ใส่รหัส PIN", type="password")
        if norm_pin(pin) == norm_pin(ADMIN_KEY):
            st.success("✔ เข้าสู่โหมดปรับปรุงคลังแล้ว")
            pin_ok = True
        elif pin:
            st.error("รหัสไม่ถูกต้อง")

nav_btn("แดชบอร์ด", "dashboard", "🏠")
nav_btn("กรอกเลือด", "entry", "✏️")
nav_btn("รายงาน", "report", "📄")

# ===== HEADER =====
left, right = st.columns([3,1])
with left:
    st.title("Blood Stock Real-time Monitor")
    st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
with right:
    try:
        st.image("assets/header.jpg", use_container_width=True)
    except Exception:
        pass

# ===== LEGEND (คงเดิม) =====
c1, c2, c3 = st.columns(3)
c1.markdown('<span class="badge"><span class="legend-dot" style="background:#ef4444"></span> วิกฤตใกล้หมด 0–4</span>', unsafe_allow_html=True)
c2.markdown('<span class="badge"><span class="legend-dot" style="background:#f59e0b"></span> เพียงพอ 5–15</span>', unsafe_allow_html=True)
c3.markdown('<span class="badge"><span class="legend-dot" style="background:#22c55e"></span> ปกติ ≥16</span>', unsafe_allow_html=True)

# ================== PAGE: DASHBOARD (แบบเดิม) ==================
if st.session_state.page == "dashboard":
    overview = get_all_status()
    blood_types = ["A", "B", "O", "AB"]

    cols = st.columns(4)
    selected = st.session_state.get("selected_bt")

    for i, bt in enumerate(blood_types):
        info = next(d for d in overview if d["blood_type"] == bt)
        total = int(info.get("total", 0))
        dist  = normalize_products(get_stock_by_blood(bt))

        with cols[i]:
            st.markdown(f"### ถุงเลือดกรุ๊ป **{bt}**")
            st_html(bag_svg_with_distribution(bt, total, dist), height=270, scrolling=False)
            if st.button(f"ดูรายละเอียดกรุ๊ป {bt}", key=f"btn_{bt}"):
                st.session_state["selected_bt"] = bt
                selected = bt

    st.divider()

    # ===== DETAIL (คงเดิม) =====
    if not selected:
        st.info("กดเลือกรายละเอียดที่กรุ๊ปโลหิตด้านบน เพื่อดูสต๊อกตามประเภทผลิตภัณฑ์และทำรายการเบิก/นำเข้า")
    else:
        st.subheader(f"รายละเอียดกรุ๊ป {selected}")
        total_selected = next(d for d in overview if d["blood_type"] == selected)["total"]
        dist_selected   = normalize_products(get_stock_by_blood(selected))

        # วางถุงตรงกลาง
        _spL, _mid, _spR = st.columns([1,1,1])
        with _mid:
            st_html(bag_svg_with_distribution(selected, int(total_selected), dist_selected), height=270, scrolling=False)

        # ตาราง + กราฟ (สีตามไฟจราจร)
        df = pd.DataFrame([{"product_type":k, "units":v} for k,v in dist_selected.items()])
        df = df.set_index("product_type").loc[ALL_PRODUCTS_UI].reset_index()

        def color_for(u):
            if u <= CRITICAL_MAX: return "#ef4444"
            if u <= YELLOW_MAX:   return "#f59e0b"
            return "#22c55e"
        df["color"] = df["units"].apply(color_for)
        ymax = max(10, int(df["units"].max() * 1.25))

        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("product_type:N", title="ประเภทผลิตภัณฑ์ (LPRC, PRC, FFP, Cryo=รวม, PC)",
                    axis=alt.Axis(labelAngle=0,labelFontSize=14,titleFontSize=14,labelColor="#111827",titleColor="#111827")),
            y=alt.Y("units:Q", title="จำนวนหน่วย (unit)", scale=alt.Scale(domainMin=0, domainMax=ymax),
                    axis=alt.Axis(labelFontSize=14,titleFontSize=14,labelColor="#111827",titleColor="#111827")),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=["product_type","units"]
        ).properties(height=360).configure_view(strokeOpacity=0)
        st.altair_chart(chart, use_container_width=True)
        st.dataframe(df.drop(columns=["color"]), use_container_width=True, hide_index=True)

        # ปรับปรุงคลัง (คงเดิม)
        if admin_mode and pin_ok:
            st.markdown("#### ปรับปรุงคลัง")
            c1, c2, c3 = st.columns([1,1,2])
            with c1:
                product_ui = st.selectbox("ประเภทผลิตภัณฑ์", ["LPRC","PRC","FFP","PC"])
            with c2:
                qty = int(st.number_input("จำนวน (หน่วย)", min_value=1, max_value=1000, value=1, step=1))
            with c3:
                note = st.text_input("หมายเหตุ", placeholder="เหตุผลการทำรายการ เช่น นำเข้า/เบิกให้ผู้ป่วย/ทดแทนการหมดอายุ")

            product_db = UI_TO_DB[product_ui]
            current_total = int(total_selected)
            current_by_product = int(dist_selected.get(product_ui, 0))

            b1, b2 = st.columns(2)
            with b1:
                if st.button("➕ นำเข้าเข้าคลัง", use_container_width=True):
                    space = max(0, BAG_MAX - min(current_total, BAG_MAX))
                    add = min(qty, space)
                    if add <= 0:
                        st.warning("เต็มคลังแล้ว (20/20) – ไม่สามารถนำเข้าเพิ่มได้")
                    else:
                        adjust_stock(selected, product_db, add, actor="admin", note=note or "inbound")
                        if add < qty:
                            st.info(f"นำเข้าได้เพียง {add} หน่วย (จำกัดเต็มคลัง 20)")
                        st.toast("บันทึกการนำเข้าแล้ว", icon="✅"); st.rerun()

            with b2:
                if st.button("➖ เบิกออกจากคลัง", use_container_width=True):
                    take = min(qty, current_by_product)
                    if take <= 0:
                        st.warning(f"ไม่มี {product_ui} ในกรุ๊ป {selected} เพียงพอสำหรับการเบิก")
                    else:
                        adjust_stock(selected, product_db, -take, actor="admin", note=note or "outbound")
                        if take < qty:
                            st.info(f"ทำการเบิกได้เพียง {take} หน่วย (ตามยอดคงเหลือ)")
                        st.toast("บันทึกการเบิกออกแล้ว", icon="✅"); st.rerun()

# ================== PAGE: กรอกเลือด (ตาราง) ==================
elif st.session_state.page == "entry":
    st.header("กรอกเลือด")
    if not (admin_mode and pin_ok):
        st.warning("ต้องเปิด Update Mode และใส่ PIN จึงจะใช้หน้านี้ได้")
        st.stop()

    # เตรียมตารางใน session
    TABLE_COLUMNS = ["ID","หมู่เลือด","รหัส","ว่าง","จอง","จำหน่าย","หมดอายุ","ค่าสถานะ"]
    if "entries" not in st.session_state:
        st.session_state.entries = pd.DataFrame(columns=TABLE_COLUMNS)

    def derive_status_row(row: dict) -> str:
        def asint(v): 
            try: return int(v)
            except: return 0
        w, r, s, e = asint(row.get("ว่าง")), asint(row.get("จอง")), asint(row.get("จำหน่าย")), asint(row.get("หมดอายุ"))
        if e>0: return '<span class="chip red">หมดอายุ</span>'
        if s>0: return '<span class="chip gray">จำหน่าย</span>'
        if r>0: return '<span class="chip yellow">จอง</span>'
        if w>0: return '<span class="chip green">ว่าง</span>'
        return '<span class="chip gray">-</span>'

    bp = ["A","B","O","AB"]
    edited = st.data_editor(
        st.session_state.entries,
        key="blood_entry_editor",
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "ID": st.column_config.TextColumn("ID"),
            "หมู่เลือด": st.column_config.SelectboxColumn("หมู่เลือด", options=bp, required=False),
            "รหัส": st.column_config.TextColumn("รหัส"),
            "ว่าง": st.column_config.TextColumn("ว่าง"),
            "จอง": st.column_config.TextColumn("จอง"),
            "จำหน่าย": st.column_config.TextColumn("จำหน่าย"),
            "หมดอายุ": st.column_config.TextColumn("หมดอายุ"),
            "ค่าสถานะ": st.column_config.Column("ค่าสถานะ", disabled=True),
        }
    )
    # คำนวณค่าสถานะ
    if not edited.empty:
        edited["ค่าสถานะ"] = edited.apply(lambda r: derive_status_row(r.to_dict()), axis=1)
    st.session_state.entries = edited.copy()

    st.markdown("##### ตารางสรุป")
    st.write(edited.to_html(escape=False, index=False), unsafe_allow_html=True)

# ================== PAGE: รายงาน (สรุปเลข) ==================
elif st.session_state.page == "report":
    st.header("รายงาน")
    # สรุปจาก entries (ถ้าใช้)
    if "entries" in st.session_state and not st.session_state.entries.empty:
        df = st.session_state.entries.copy()
        for col in ["ว่าง","จอง","จำหน่าย","หมดอายุ"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        agg = df.groupby("หมู่เลือด", dropna=False)[["ว่าง","จอง","จำหน่าย","หมดอายุ"]].sum().reset_index()
        st.dataframe(agg, use_container_width=True, hide_index=True)
        total = agg[["ว่าง","จอง","จำหน่าย","หมดอายุ"]].sum()
        st.success(f"รวมทั้งหมด — ว่าง: {int(total['ว่าง'])} | จอง: {int(total['จอง'])} | จำหน่าย: {int(total['จำหน่าย'])} | หมดอายุ: {int(total['หมดอายุ'])}")
    else:
        st.info("ยังไม่มีข้อมูลในตารางกรอกเลือด")
