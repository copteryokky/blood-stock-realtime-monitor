# app.py — Blood Stock Real-time Monitor (classic blood bag UI)

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
    def st_autorefresh(*args, **kwargs):  # no-op on local/dev without package
        return None

# ===== DB funcs (ของคุณ) =====
from db import init_db, get_all_status, get_stock_by_blood, adjust_stock  #, get_transactions


# ===== PAGE CONFIG & BASE THEME =====
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
BAG_MAX      = 20    # เต็มคลังต่อกรุ๊ป (จำกัดตอนนำเข้า)
CRITICAL_MAX = 4     # 0–4 = แดง
YELLOW_MAX   = 15    # 5–15 = เหลือง  |  >=16 = เขียว


# ===== Helpers =====
def compute_status(total: int):
    t = max(0, int(total))
    if t <= CRITICAL_MAX:
        status, label = "red", "วิกฤตใกล้หมด"
    elif t <= YELLOW_MAX:
        status, label = "yellow", "เพียงพอ"
    else:
        status, label = "green", "ปกติ"
    pct = max(0, min(100, int(round(100 * min(t, BAG_MAX) / BAG_MAX))))
    return status, label, pct


def traffic_color(status: str) -> str:
    return {"green":"#22c55e", "yellow":"#f59e0b", "red":"#ef4444"}[status]


def norm_pin(s: str) -> str:
    trans = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
    return (s or "").translate(trans).strip()


def blood_letter_color(bt: str) -> str:
    """สีตัวอักษรบนถุง: A=เหลือง, B=ชมพู, O=ฟ้า, AB=ขาวมีสโตรกเข้ม"""
    bt = bt.upper()
    if bt == "A":
        return "#facc15"
    if bt == "B":
        return "#f472b6"
    if bt == "O":
        return "#60a5fa"
    return "#ffffff"  # AB


# ===== Classic Blood Bag (ไม่มีกราฟซ่อน) =====
def bag_svg_classic(blood_type: str, total_units: int) -> str:
    """
    ถุงเลือดสไตล์เดิม:
    - ไม่มีแผนภูมิในถุง
    - เส้นขอบถุงสีโทนแดงให้ดูเป็นถุงเลือด
    - ตัวอักษรกรุ๊ป: A=เหลือง, B=ชมพู, O=ฟ้า, AB=ขาว (มี stroke เข้มให้ชัด)
    """
    status, _label, pct = compute_status(total_units)
    liquid = traffic_color(status)
    textc = blood_letter_color(blood_type)
    stroke_for_ab = 'stroke="#1f2937" stroke-width="2.2"' if blood_type.upper() == "AB" else ''

    # ของเหลวในถุง
    water_h = 162 * pct / 100.0
    water_y = 182 - water_h
    gid = f"g_{blood_type}"

    return f"""
<div style="display:flex;flex-direction:column;align-items:center;gap:8px;font-family:ui-sans-serif,system-ui,'Segoe UI',Roboto,Arial">
  <svg width="160" height="210" viewBox="0 0 140 190" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <filter id="shadow_{gid}" x="-20%" y="-20%" width="160%" height="160%">
        <feDropShadow dx="0" dy="6" stdDeviation="7" flood-opacity="0.18"/>
      </filter>
      <clipPath id="clip_{gid}">
        <path d="M30,22 C30,12 40,6 50,6 L90,6 C100,6 110,12 110,22 L110,155
                 C110,170 100,180 85,182 L45,182 C30,180 30,170 30,155 Z" />
      </clipPath>
      <linearGradient id="liquid_{gid}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%"  stop-color="{liquid}" stop-opacity=".96"/>
        <stop offset="100%" stop-color="{liquid}" stop-opacity=".86"/>
      </linearGradient>
    </defs>

    <!-- หูหิ้ว -->
    <path d="M55,8 L55,0 M85,8 L85,0" stroke="#9ca3af" stroke-width="6" stroke-linecap="round"/>

    <!-- ตัวถุง -->
    <g filter="url(#shadow_{gid})">
      <path d="M30,22 C30,12 40,6 50,6 L90,6 C100,6 110,12 110,22 L110,155
               C110,170 100,180 85,182 L45,182 C30,180 30,170 30,155 Z"
            fill="#ffffff" stroke="#ef4444" stroke-opacity=".9" stroke-width="3.2" />

      <!-- ของเหลว -->
      <rect x="31" y="{water_y:.1f}" width="78" height="{water_h:.1f}"
            fill="url(#liquid_{gid})" clip-path="url(#clip_{gid})"/>

      <!-- เส้นผิวน้ำ -->
      <path d="M31,155 Q70,170 109,155" fill="none" stroke="rgba(0,0,0,0.10)"/>
    </g>

    <!-- ป้าย max -->
    <g>
      <rect x="76" y="15" rx="10" ry="10" width="50" height="22" fill="#ffffff" stroke="#e5e7eb"/>
      <text x="101" y="30" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text>
    </g>

    <!-- กรุ๊ปเลือด -->
    <text x="70" y="120" text-anchor="middle" font-weight="900" font-size="32" fill="{textc}" {stroke_for_ab}>{blood_type}</text>
  </svg>

  <div style="text-align:center;line-height:1.2">
    <div style="font-weight:800">{int(total_units)} unit</div>
  </div>
</div>
"""


# ===== Init DB & Admin key =====
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()

ADMIN_KEY = os.environ.get("BLOOD_ADMIN_KEY", "1234")


# ===== Sidebar =====
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


# ===== Header & Legend =====
left, right = st.columns([3,1])
with left:
    st.title("Blood Stock Real-time Monitor")
    st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
with right:
    try:
        st.image("assets/header.jpg", use_container_width=True)
    except Exception:
        pass

c1, c2, c3 = st.columns(3)
c1.markdown('<span class="badge"><span class="legend-dot" style="background:#ef4444"></span> วิกฤตใกล้หมด 0–4</span>', unsafe_allow_html=True)
c2.markdown('<span class="badge"><span class="legend-dot" style="background:#f59e0b"></span> เพียงพอ 5–15</span>', unsafe_allow_html=True)
c3.markdown('<span class="badge"><span class="legend-dot" style="background:#22c55e"></span> ปกติ ≥16</span>', unsafe_allow_html=True)


# ===== Overview (A, B, O, AB) =====
overview = get_all_status()          # [{blood_type, total}]
blood_types = ["A", "B", "O", "AB"]  # เรียงตามที่ต้องการ

cols = st.columns(4)
selected = st.session_state.get("selected_bt")

for i, bt in enumerate(blood_types):
    info = next(d for d in overview if d["blood_type"] == bt)
    total = int(info.get("total", 0))

    with cols[i]:
        st.markdown(f"### ถุงเลือดกรุ๊ป **{bt}**")
        st_html(bag_svg_classic(bt, total), height=260, scrolling=False)
        if st.button(f"ดูรายละเอียดกรุ๊ป {bt}", key=f"btn_{bt}"):
            st.session_state["selected_bt"] = bt
            selected = bt

st.divider()


# ===== Detail page (กราฟปกติด้านล่าง, ไม่มีกราฟซ่อนในถุง) =====
if not selected:
    st.info("กดเลือกรายละเอียดที่กรุ๊ปโลหิตด้านบน เพื่อดูและปรับปรุงคลัง")
else:
    st.subheader(f"รายละเอียดกรุ๊ป {selected}")

    # สรุปรวม + ถุงย่อ
    total_selected = next(d for d in overview if d["blood_type"] == selected)["total"]
    st_html(bag_svg_classic(selected, int(total_selected)), height=260, scrolling=False)

    # โหลดคงคลังตามชนิดผลิตภัณฑ์
    # ต้องการเรียง: LPRC, PRC, FFP (แทน Plasma), Cryo(รวม), PC(แทน Platelets)
    raw_list = get_stock_by_blood(selected)  # [{product_type, units}]
    # map เดิม → ใหม่
    mapping = {
        "LPRC": "LPRC",
        "PRC": "PRC",
        "Plasma": "FFP",
        "Cryo": "Cryo",
        "Platelets": "PC",
    }

    # รวมยอด และคำนวณ Cryo = ผลรวมทั้งหมดของกรุ๊ปนั้น
    temp = {}
    group_sum = 0
    for r in raw_list:
        name = mapping.get(r["product_type"], r["product_type"])
        u = int(r["units"])
        group_sum += u
        temp[name] = temp.get(name, 0) + u

    temp["Cryo"] = group_sum  # ตามที่ขอ: Cryo = รวมทั้งหมด

    order = ["LPRC", "PRC", "FFP", "Cryo", "PC"]
    df = pd.DataFrame([{"product_type": k, "units": int(temp.get(k, 0))} for k in order])

    if df["units"].sum() == 0:
        st.warning("ยังไม่มีข้อมูลคงคลังสำหรับกรุ๊ปนี้")
    else:
        # สีกราฟตามไฟจราจร โดยเทียบค่า units: <=4 แดง, <=15 เหลือง, >15 เขียว
        def color_for_units(v: int) -> str:
            if v <= CRITICAL_MAX: return "#ef4444"
            if v <= YELLOW_MAX:   return "#f59e0b"
            return "#22c55e"

        df["bar_color"] = df["units"].apply(color_for_units)

        chart = (
            alt.Chart(df)
              .mark_bar()
              .encode(
                  x=alt.X('product_type:N', title='ประเภทผลิตภัณฑ์ (LPRC, PRC, FFP, Cryo=รวม, PC)'),
                  y=alt.Y('units:Q', title='จำนวนหน่วย (unit)', scale=alt.Scale(domainMin=0)),
                  color=alt.Color('bar_color:N', scale=None, legend=None),
                  tooltip=['product_type:N','units:Q']
              )
              .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)

        st.dataframe(df.drop(columns=["bar_color"]), use_container_width=True, hide_index=True)

    # ===== Update Mode =====
    if admin_mode and pin_ok:
        st.markdown("#### ปรับปรุงคลัง")
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            product = st.selectbox("ประเภทผลิตภัณฑ์", ["LPRC", "PRC", "FFP", "Cryo", "PC"])
        with c2:
            qty = int(st.number_input("จำนวน (หน่วย)", min_value=1, max_value=1000, value=1, step=1))
        with c3:
            note = st.text_input("หมายเหตุ", placeholder="เหตุผลการทำรายการ เช่น นำเข้า/เบิกให้ผู้ป่วย/ทดแทนการหมดอายุ")

        # แปลงชื่อกลับเป็นฐาน (ตาม db.py เดิม)
        reverse_map = {"LPRC":"LPRC", "PRC":"PRC", "FFP":"Plasma", "Cryo":"Cryo", "PC":"Platelets"}

        # ปัจจุบัน
        current_total = int(total_selected)
        current_by_product = int(temp.get(product, 0))

        b1, b2 = st.columns(2)
        with b1:
            if st.button("➕ นำเข้าเข้าคลัง", use_container_width=True):
                # จำกัดรวมไม่เกิน 20 ต่อกรุ๊ป (ตาม requirement เดิม)
                space = max(0, BAG_MAX - min(current_total, BAG_MAX))
                add = min(qty, space)
                if add <= 0:
                    st.warning("เต็มคลังแล้ว (20/20) – ไม่สามารถนำเข้าเพิ่มได้")
                else:
                    adjust_stock(selected, reverse_map[product], add, actor="admin", note=note or "inbound")
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
                    adjust_stock(selected, reverse_map[product], -take, actor="admin", note=note or "outbound")
                    if take < qty:
                        st.info(f"ทำการเบิกได้เพียง {take} หน่วย (ตามยอดคงเหลือ)")
                    st.toast("บันทึกการเบิกออกแล้ว", icon="✅")
                    st.rerun()
