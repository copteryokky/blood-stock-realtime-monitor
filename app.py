import os
from datetime import datetime
import pandas as pd
import altair as alt
import streamlit as st

# auto refresh helper
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    def st_autorefresh(*args, **kwargs): return None

from db import init_db, get_all_status, get_stock_by_blood, adjust_stock, get_transactions

st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")

# ===== CONFIG =====
BAG_MAX = 20     # เต็มถุงที่ 20
GREEN_MIN = 15   # >=15 เขียว
YELLOW_MIN = 4   # 4–14 เหลือง; 0–3 แดง

# ---------- helpers ----------
def compute_bag(total: int):
    if total >= GREEN_MIN:
        status, label = "green", "ปกติ"
    elif total >= YELLOW_MIN:
        status, label = "yellow", "เพียงพอ"
    else:
        status, label = "red", "วิกฤตใกล้หมด"
    pct = max(0, min(100, int(round(100 * min(total, BAG_MAX) / BAG_MAX))))
    return status, label, pct

def bag_color(status: str) -> str:
    return {"green":"#22c55e", "yellow":"#f59e0b", "red":"#ef4444"}[status]

def blood_bag_svg(blood_type: str, total: int) -> str:
    """สวยขึ้น: ใช้ SVG + gradient + shadow"""
    status, label, pct = compute_bag(total)
    fill = bag_color(status)
    # เติมจากล่างขึ้นบนตาม pct
    fill_height = pct
    # SVG 140x190 สัดส่วนพอดี
    return f"""
    <div style="display:flex;flex-direction:column;align-items:center;gap:8px">
    <svg width="140" height="190" viewBox="0 0 140 190" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="4" stdDeviation="6" flood-opacity="0.15"/>
        </filter>
        <clipPath id="bag-clip">
          <path d="M30,20 C30,10 40,5 50,5 L90,5 C100,5 110,10 110,20 L110,155
                   C110,170 100,180 85,182 L45,182 C30,180 30,170 30,155 Z" />
        </clipPath>
      </defs>

      <!-- หูหิ้ว -->
      <path d="M55,6 L55,0 M85,6 L85,0" stroke="#9ca3af" stroke-width="6" stroke-linecap="round"/>

      <!-- ถุง -->
      <g filter="url(#shadow)">
        <path d="M30,20 C30,10 40,5 50,5 L90,5 C100,5 110,10 110,20 L110,155
                 C110,170 100,180 85,182 L45,182 C30,180 30,170 30,155 Z"
              fill="white" stroke="#e5e7eb" stroke-width="3"/>
        <!-- ของเหลว -->
        <rect x="31" y="{182 - 162*fill_height/100:.1f}" width="78" height="{162*fill_height/100:.1f}"
              fill="{fill}" clip-path="url(#bag-clip)"/>
        <!-- เส้นขอบโค้งด้านใน -->
        <path d="M31,155 Q70,170 109,155" fill="none" stroke="rgba(0,0,0,0.08)"/>
      </g>

      <!-- ป้าย max -->
      <g>
        <rect x="78" y="16" rx="10" ry="10" width="48" height="22" fill="#ffffff" stroke="#e5e7eb"/>
        <text x="102" y="31" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text>
      </g>

      <!-- label กรุ๊ป -->
      <text x="70" y="120" text-anchor="middle" font-weight="bold" font-size="28" fill="#ffffff">{blood_type}</text>
    </svg>

    <div style="text-align:center;line-height:1.2">
      <div style="font-weight:700">{total} / {BAG_MAX} unit</div>
      <div style="font-size:12px">{label}</div>
    </div>
    </div>
    """

def norm_pin(s:str)->str:
    trans = str.maketrans("๐๑๒๓๔๕๖๗๘๙","0123456789")
    return (s or "").translate(trans).strip()

# ---------- init DB ----------
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()

ADMIN_KEY = os.environ.get("BLOOD_ADMIN_KEY", "1234")

# ---------- sidebar ----------
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

# ---------- header ----------
left, right = st.columns([3,1])
with left:
    st.title("Blood Stock Real-time Monitor")
    st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
with right:
    try:
        st.image("assets/header.jpg", use_container_width=True)
    except Exception:
        pass

# ---------- legend ----------
c1, c2, c3 = st.columns(3)
c1.markdown("🟥 **วิกฤตใกล้หมด** 0–3")
c2.markdown("🟨 **เพียงพอ** 4–14")
c3.markdown(f"🟩 **ปกติ** ≥ {GREEN_MIN}")

# ---------- overview ----------
overview = get_all_status()  # fresh ทุกครั้งเพราะไม่มี cache

cols = st.columns(4)
blood_types = ["O","A","B","AB"]
selected = st.session_state.get("selected_bt")

for i, bt in enumerate(blood_types):
    info = next(d for d in overview if d["blood_type"] == bt)
    total = int(info.get("total", 0))
    with cols[i]:
        st.markdown(f"### ถุงเลือดกรุ๊ป **{bt}**")
        st.markdown(blood_bag_svg(bt, total), unsafe_allow_html=True)
        if st.button(f"ดูรายละเอียดกรุ๊ป {bt}", key=f"btn_{bt}"):
            st.session_state["selected_bt"] = bt
            selected = bt

st.divider()

# ---------- detail ----------
if not selected:
    st.info("กดเลือกรายละเอียดที่กรุ๊ปโลหิตด้านบน เพื่อดูสต็อกตามประเภทผลิตภัณฑ์และทำรายการเบิก/นำเข้า")
else:
    st.subheader(f"รายละเอียดกรุ๊ป {selected}")

    # show mini bag for this group
    total_selected = next(d for d in overview if d["blood_type"] == selected)["total"]
    st.markdown(blood_bag_svg(selected, int(total_selected)), unsafe_allow_html=True)

    stock = get_stock_by_blood(selected)
    df = pd.DataFrame(stock)

    if df.empty:
        st.warning("ยังไม่มีข้อมูลในคลังสำหรับกรุ๊ปนี้")
    else:
        # y ให้เริ่มที่ 0 และแสดง label ชัดขึ้น
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X('product_type:N', title='ประเภทผลิตภัณฑ์'),
            y=alt.Y('units:Q', title='จำนวนหน่วย (unit)', scale=alt.Scale(domainMin=0)),
            tooltip=['product_type','units']
        ).properties(height=320)
        st.altair_chart(chart, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

    if admin_mode and pin_ok:
        st.markdown("#### ปรับปรุงคลัง")
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            product = st.selectbox("ประเภทผลิตภัณฑ์", ["PRC","Platelets","Plasma","Cryo"])
        with c2:
            qty = st.number_input("จำนวน (หน่วย)", min_value=1, max_value=1000, value=1, step=1)
        with c3:
            note = st.text_input("หมายเหตุ", placeholder="เหตุผลการทำรายการ เช่น นำเข้า/เบิกให้ผู้ป่วย/ทดแทนการหมดอายุ")

        b1, b2 = st.columns(2)
        with b1:
            if st.button("➕ นำเข้าเข้าคลัง", use_container_width=True):
                adjust_stock(selected, product, int(qty), actor="admin", note=note or "inbound")
                st.toast("บันทึกการนำเข้าแล้ว", icon="✅")
                st.rerun()   # ← อัปเดตทันทีทั้งถุงและกราฟ
        with b2:
            if st.button("➖ เบิกออกจากคลัง", use_container_width=True):
                adjust_stock(selected, product, -int(qty), actor="admin", note=note or "outbound")
                st.toast("บันทึกการเบิกออกแล้ว", icon="✅")
                st.rerun()   # ← อัปเดตทันทีทั้งถุงและกราฟ

    st.markdown("#### รายการความเคลื่อนไหวล่าสุด")
    tx = get_transactions(50, blood_type=selected)
    if tx:
        st.dataframe(pd.DataFrame(tx), use_container_width=True, hide_index=True)
    else:
        st.write("— ไม่มีรายการ —")
