import os
from datetime import datetime
import pandas as pd
import altair as alt
import streamlit as st
from streamlit.components.v1 import html as st_html

# ===== Auto refresh helper =====
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    def st_autorefresh(*args, **kwargs): return None

from db import init_db, get_all_status, get_stock_by_blood, adjust_stock

# ===== PAGE CONFIG & THEME =====
st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")
st.markdown("""
<style>
.block-container{padding-top:1.2rem;}
h1,h2,h3{letter-spacing:.2px}
.badge{display:inline-flex;align-items:center;gap:.4rem;padding:.25rem .5rem;border-radius:999px;background:#f3f4f6}
.legend-dot{width:.7rem;height:.7rem;border-radius:999px;display:inline-block}
.stButton>button{border-radius:12px;padding:.55rem 1rem;font-weight:600}
</style>
""", unsafe_allow_html=True)

# ===== CONFIG =====
BAG_MAX      = 20    # ความจุสูงสุดในถุง (ใช้คุมระดับของเหลวเท่านั้น)
CRITICAL_MAX = 4     # 0–4 แดง
YELLOW_MAX   = 15    # 5–15 เหลือง, >=16 เขียว

# ลำดับ/ชื่อผลิตภัณฑ์ที่เราต้องการให้โชว์
ALL_PRODUCTS_UI = ["LPRC", "PRC", "FFP", "Cryo", "PC"]  # Cryo = รวมทั้งหมด

# ===== Helpers =====
def compute_bag(total: int):
    """คำนวณสถานะ + เปอร์เซ็นต์ความสูงของของเหลว (อิง BAG_MAX)"""
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

def normalize_products(rows):
    """
    รับรายการ [{product_type, units}] จาก DB
    - เปลี่ยน Plasma -> FFP
    - mapping Platelets -> PC
    - เติม 0 ให้ชนิดที่ไม่มี
    - คำนวณ Cryo = รวมทั้งหมดของกรุ๊ปนั้น
    """
    m = {"PRC":0, "LPRC":0, "FFP":0, "PC":0}
    for r in rows:
        p = (r.get("product_type") or "").strip()
        u = int(r.get("units") or 0)
        if p.lower() == "plasma":     # เปลี่ยนชื่อเป็น FFP
            m["FFP"] += u
        elif p.lower() == "platelets": # mapping -> PC
            m["PC"] += u
        elif p.upper() in m:
            m[p.upper()] += u
    total = sum(m.values())          # รวมทุกชนิด
    m["Cryo"] = total                # Cryo = รวมทั้งหมด
    # คืน dict ตามลำดับที่เราต้องการ
    ordered = {k: m.get(k, 0) for k in ALL_PRODUCTS_UI}
    return ordered

def blood_type_text_color(bt: str) -> str:
    """
    สีตัวอักษรบนถุง:
    A=เหลือง, B=ชมพู, O=ฟ้า, AB=ขาวพร้อมสโตรกเทาเข้ม
    """
    bt = bt.upper()
    if bt == "A":   return "#facc15"   # yellow-400
    if bt == "B":   return "#f472b6"   # pink-400
    if bt == "O":   return "#60a5fa"   # blue-400
    return "#ffffff"                   # AB = white (จะวาด stroke เพิ่มใน SVG)

def bag_svg(blood_type: str, total: int) -> str:
    """
    วาดถุงเลือดแบบสมจริง: ขอบแดงเลอะๆ, ของเหลวไล่เฉด, ไม่มีกราฟซ่อนในถุง
    แสดงจำนวนหน่วยเป็น "{total} unit" (ไม่แสดง /20)
    """
    status, label, pct = compute_bag(total)
    fill = bag_color(status)
    # ระดับของเหลว
    water_h = 162 * pct / 100.0
    water_y = 182 - water_h
    # สีตัวอักษรกรุ๊ป
    text_color = blood_type_text_color(blood_type)
    stroke_for_ab = 'stroke="#1f2937" stroke-width="2"' if blood_type.upper()=="AB" else ''

    # เลอะเลือด: ใช้กราดิเอนต์ขอบแดง + feTurbulence เล็กน้อย
    gid = f"g_{blood_type}"

    return f"""
<div style="display:flex;flex-direction:column;align-items:center;gap:8px;font-family:ui-sans-serif,system-ui,'Segoe UI',Roboto,Arial">
  <svg width="170" height="220" viewBox="0 0 150 200" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <filter id="shadow_{gid}" x="-20%" y="-20%" width="160%" height="160%">
        <feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#991b1b" flood-opacity="0.18"/>
      </filter>
      <clipPath id="clip_{gid}">
        <path d="M35,25 C35,13 45,7 57,7 L93,7 C105,7 115,13 115,25 L115,160
                 C115,176 104,186 88,188 L62,188 C46,186 35,176 35,160 Z"/>
      </clipPath>
      <linearGradient id="liquid_{gid}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%"  stop-color="{fill}" stop-opacity=".96"/>
        <stop offset="100%" stop-color="{fill}" stop-opacity=".86"/>
      </linearGradient>
      <linearGradient id="edge_{gid}" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%"  stop-color="#fecaca"/>
        <stop offset="60%" stop-color="#fca5a5"/>
        <stop offset="100%" stop-color="#ef4444"/>
      </linearGradient>
      <filter id="smear_{gid}">
        <feTurbulence baseFrequency="0.6" numOctaves="2" seed="3" type="fractalNoise" result="noise"/>
        <feColorMatrix in="noise" type="saturate" values="0"/>
        <feBlend mode="multiply" in2="SourceGraphic"/>
      </filter>
    </defs>

    <!-- คอถุง -->
    <rect x="70" y="0" width="10" height="10" rx="5" fill="#9ca3af"/>
    <rect x="68" y="10" width="14" height="6" rx="3" fill="#cbd5e1"/>
    <path d="M75,16 C75,22 75,22 75,22" stroke="#cbd5e1" stroke-width="4" stroke-linecap="round"/>

    <!-- สเกลด้านซ้าย -->
    <g opacity=".35">
      <line x1="28" x2="28" y1="28" y2="184" stroke="#9ca3af" stroke-width="1"/>
      {"".join([f'<line x1="26" x2="30" y1="{y}" y2="{y}" stroke="#9ca3af" stroke-width="{2 if i%5==0 else 1}"/>'
               for i,y in enumerate(range(184, 27, -8))])}
    </g>

    <!-- ตัวถุง + ขอบแดงเลอะ -->
    <g filter="url(#shadow_{gid})">
      <path d="M35,25 C35,13 45,7 57,7 L93,7 C105,7 115,13 115,25 L115,160
               C115,176 104,186 88,188 L62,188 C46,186 35,176 35,160 Z"
            fill="#ffffff" stroke="url(#edge_{gid})" stroke-width="3" filter="url(#smear_{gid})"/>

      <!-- ของเหลว -->
      <rect x="36" y="{water_y:.1f}" width="78" height="{water_h:.1f}"
            fill="url(#liquid_{gid})" clip-path="url(#clip_{gid})"/>

      <!-- เส้นผิวน้ำ + ไฮไลต์ -->
      <path d="M36,160 Q75,174 114,160" fill="none" stroke="rgba(0,0,0,0.10)"/>
      <rect x="41" y="21" width="9" height="165" fill="#ffffff" opacity=".35" clip-path="url(#clip_{gid})"/>
    </g>

    <!-- ป้าย max (ยังแสดง 20 max ไว้ที่มุม) -->
    <g>
      <rect x="82" y="17" rx="10" ry="10" width="52" height="22" fill="#ffffff" stroke="#e5e7eb"/>
      <text x="108" y="32" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text>
    </g>

    <!-- ตัวอักษรกรุ๊ป -->
    <text x="75" y="125" text-anchor="middle" font-weight="900" font-size="32" fill="{text_color}" {stroke_for_ab}>{blood_type}</text>
  </svg>

  <div style="text-align:center;line-height:1.2">
    <div style="font-weight:800;font-size:14px">{int(total)} unit</div>
  </div>
</div>
"""

# ===== Init DB =====
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()

ADMIN_KEY = os.environ.get("BLOOD_ADMIN_KEY", "1234")

# ===== SIDEBAR =====
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

# ===== LEGEND =====
c1, c2, c3 = st.columns(3)
c1.markdown('<span class="badge"><span class="legend-dot" style="background:#ef4444"></span> วิกฤตใกล้หมด 0–4</span>', unsafe_allow_html=True)
c2.markdown('<span class="badge"><span class="legend-dot" style="background:#f59e0b"></span> เพียงพอ 5–15</span>', unsafe_allow_html=True)
c3.markdown('<span class="badge"><span class="legend-dot" style="background:#22c55e"></span> ปกติ ≥16</span>', unsafe_allow_html=True)

# ===== OVERVIEW =====
overview = get_all_status()
blood_types = ["A", "B", "O", "AB"]  # เรียง A→B→O→AB
cols = st.columns(4)
selected = st.session_state.get("selected_bt")

for i, bt in enumerate(blood_types):
    info = next(d for d in overview if d["blood_type"] == bt)
    # ดึงสต็อก + ทำ normalize
    dist_map = normalize_products(get_stock_by_blood(bt))
    total = int(dist_map.get("Cryo", 0))  # ใช้รวมทั้งหมดเป็นตัวเลขใต้ถุง

    with cols[i]:
        st.markdown(f"### ถุงเลือดกรุ๊ป **{bt}**")
        st_html(bag_svg(bt, total), height=270, scrolling=False)
        if st.button(f"ดูรายละเอียดกรุ๊ป {bt}", key=f"btn_{bt}"):
            st.session_state["selected_bt"] = bt
            selected = bt

st.divider()

# ===== DETAIL =====
if not selected:
    st.info("กดเลือกรายละเอียดที่กรุ๊ปโลหิตด้านบน เพื่อดูสต็อกตามประเภทผลิตภัณฑ์และทำรายการเบิก/นำเข้า")
else:
    st.subheader(f"รายละเอียดกรุ๊ป {selected}")

    # ข้อมูลกรุ๊ปที่เลือก
    dist_selected = normalize_products(get_stock_by_blood(selected))
    total_selected = int(dist_selected.get("Cryo", 0))  # รวมทั้งหมด

    # ถุงสรุป (เอากราฟในถุงออกแล้ว)
    st_html(bag_svg(selected, total_selected), height=270, scrolling=False)

    # ตาราง + กราฟ (แก้ปัญหา alt.condition โดยใช้คอลัมน์สีแทน)
    df = pd.DataFrame([{"product_type": k, "units": v} for k, v in dist_selected.items()])
    df = df.set_index("product_type").loc[ALL_PRODUCTS_UI].reset_index()

    # สีไฟจราจร
    def traffic(u: int) -> str:
        if u <= CRITICAL_MAX: return "#ef4444"
        if u <= YELLOW_MAX:   return "#f59e0b"
        return "#22c55e"

    df["color"] = df["units"].apply(traffic)

    # ทำให้กราฟนิ่ง: domain Y อิงค่าจริงอย่างน้อย = BAG_MAX
    y_max = max(int(df["units"].max()), BAG_MAX)

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("product_type:N", title="ประเภทผลิตภัณฑ์ (LPRC, PRC, FFP, Cryo=รวม, PC)"),
            y=alt.Y("units:Q", title="จำนวนหน่วย (unit)", scale=alt.Scale(domainMin=0, domainMax=y_max)),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=["product_type", "units"]
        )
        .properties(height=340)
    )
    st.altair_chart(chart, use_container_width=True)
    st.dataframe(df.drop(columns=["color"]), use_container_width=True, hide_index=True)

    # ===== Update Mode (ไม่ให้แก้ Cryo เพราะเป็น 'รวม') =====
    if admin_mode and pin_ok:
        st.markdown("#### ปรับปรุงคลัง")
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            product = st.selectbox("ประเภทผลิตภัณฑ์", ["LPRC", "PRC", "FFP", "PC"])
        with c2:
            qty = int(st.number_input("จำนวน (หน่วย)", min_value=1, max_value=1000, value=1, step=1))
        with c3:
            note = st.text_input("หมายเหตุ", placeholder="เหตุผลการทำรายการ เช่น นำเข้า/เบิกให้ผู้ป่วย/ทดแทนการหมดอายุ")

        # จำกัดรวมสูงสุด = 20 โดยคิดจากผลรวมจริง (total_selected)
        current_total = int(total_selected)
        current_by_product = int(dist_selected.get(product, 0))

        b1, b2 = st.columns(2)
        with b1:
            if st.button("➕ นำเข้าเข้าคลัง", use_container_width=True):
                space = max(0, BAG_MAX - min(current_total, BAG_MAX))
                add = min(qty, space)
                if add <= 0:
                    st.warning("เต็มคลังแล้ว (20/20) – ไม่สามารถนำเข้าเพิ่มได้")
                else:
                    adjust_stock(selected, product, add, actor="admin", note=note or "inbound")
                    if add < qty:
                        st.info(f"นำเข้าได้เพียง {add} หน่วย (จำกัดเต็มคลัง 20)")
                    st.toast("บันทึกการนำเข้าแล้ว", icon="✅")
                    st.rerun()

        with b2:
            if st.button("➖ เบิกออกจากคลัง", use_container_width=True):
                take = min(qty, current_by_product)
                if take <= 0:
                    st.warning(f"ไม่มี {product} ในกรุ๊ป {selected} เพียงพอสำหรับการเบิก")
                else:
                    adjust_stock(selected, product, -take, actor="admin", note=note or "outbound")
                    if take < qty:
                        st.info(f"ทำการเบิกได้เพียง {take} หน่วย (ตามยอดคงเหลือ)")
                    st.toast("บันทึกการเบิกออกแล้ว", icon="✅")
                    st.rerun()
