import os
from datetime import datetime
import pandas as pd
import altair as alt
import streamlit as st
from streamlit.components.v1 import html as st_html  # ใช้ component html สำหรับ SVG

# ===== Auto refresh helper =====
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    def st_autorefresh(*args, **kwargs): return None

from db import init_db, get_all_status, get_stock_by_blood, adjust_stock, get_transactions

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
BAG_MAX      = 20    # เต็มคลังต่อกรุ๊ป
CRITICAL_MAX = 4     # 0–4 แดง
YELLOW_MAX   = 15    # 5–15 เหลือง, >=16 เขียว

# ===== Helpers =====
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

# ===== SVG Blood Bag (ทรงเหมือนไอคอน + ผิวน้ำโค้ง + กราฟในถุง (hover)) =====
def bag_svg_with_distribution(blood_type: str, total: int, dist: dict) -> str:
    status, label, pct = compute_bag(total)
    fill = bag_color(status)

    # โซนภายในถุง (ไว้คำนวณผิวน้ำ)
    inner_h = 148.0
    inner_y0 = 40.0
    water_h = inner_h * pct / 100.0
    water_y = inner_y0 + (inner_h - water_h)

    # กราฟย่อย 4 ชนิด
    ORDER  = ["PRC", "Platelets", "Plasma", "Cryo"]
    COLORS = {"PRC":"#1f77b4", "Platelets":"#ff7f0e", "Plasma":"#2ca02c", "Cryo":"#d62728"}
    vals   = [max(0, int(dist.get(k, 0))) for k in ORDER]
    bar_hs = [(min(v, BAG_MAX)/BAG_MAX) * water_h for v in vals]

    gap = 6
    inner_w = 84.0
    bar_w = (inner_w - gap*3)/4.0
    x0 = 33.0
    bars, labels_svg = [], []
    for i, (k, h) in enumerate(zip(ORDER, bar_hs)):
        x = x0 + i*(bar_w + gap)
        y = water_y + (water_h - h)
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="4" fill="{COLORS[k]}" />'
        )
        labels_svg.append(
            f'<text x="{x + bar_w/2:.1f}" y="{max(y+12, water_y+12):.1f}" '
            f'text-anchor="middle" font-size="9" font-weight="700" fill="#fff">{k}</text>'
        )

    gid = f"g_{blood_type}"

    # ผิวน้ำแบบคลื่นให้อารมณ์ของเหลวจริง
    wave_amp = 5 + 6*(pct/100)  # 5–11
    wave_path = (
        f"M28,{water_y:.1f} "
        f"Q55,{water_y - wave_amp:.1f} 82,{water_y:.1f} "
        f"Q109,{water_y + wave_amp:.1f} 136,{water_y:.1f} "
        f"L136,188 28,188 Z"
    )

    return f"""
<div>
  <style>
    .bag-wrap{{display:flex;flex-direction:column;align-items:center;gap:8px;font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial}}
    .bag{{transition:transform .18s ease, filter .18s ease}}
    .bag:hover{{transform:translateY(-2px); filter:drop-shadow(0 10px 22px rgba(0,0,0,.12));}}
    .dist-group{{opacity:0; transition:opacity .2s ease;}}
    .bag:hover .dist-group{{opacity:1;}}
    .bag-caption{{text-align:center; line-height:1.2}}
    .bag-caption .total{{font-weight:700}}
    .bag-caption .tip{{font-size:10px;color:#6b7280}}
  </style>

  <div class="bag-wrap">
    <svg class="bag" width="170" height="230" viewBox="0 0 164 200" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <!-- พื้นที่ภายในถุงสำหรับ clip -->
        <clipPath id="clip-{gid}">
          <path d="M28,40
                   C28,25 40,16 56,16
                   L108,16
                   C124,16 136,25 136,40
                   L136,166
                   C136,182 123,192 106,194
                   L58,194
                   C41,192 28,182 28,166 Z"/>
        </clipPath>
        <linearGradient id="liquid-{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"  stop-color="{fill}" stop-opacity=".96"/>
          <stop offset="100%" stop-color="{fill}" stop-opacity=".86"/>
        </linearGradient>
        <linearGradient id="gloss-{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="rgba(255,255,255,.75)"/>
          <stop offset="100%" stop-color="rgba(255,255,255,0)"/>
        </linearGradient>
        <filter id="shadow-{gid}" x="-20%" y="-20%" width="160%" height="160%">
          <feDropShadow dx="0" dy="6" stdDeviation="6" flood-opacity=".2"/>
        </filter>
      </defs>

      <!-- หูหิ้วกลม -->
      <circle cx="82" cy="8" r="7.5" fill="#eef2ff" stroke="#dbe0ea" stroke-width="3"/>
      <rect x="75.5" y="12" width="13" height="8" rx="3" fill="#e5e7eb"/>

      <!-- ตัวถุง (ทรงมน) -->
      <g filter="url(#shadow-{gid})">
        <path d="
          M20,34
          C20,18 34,8 54,8
          L110,8
          C130,8 144,18 144,34
          L144,168
          C144,187 128,198 108,200
          L56,200
          C36,198 20,187 20,168 Z"
          fill="#ffffff" stroke="#e5e7eb" stroke-width="3"/>

        <!-- ไฮไลต์เงาวาว -->
        <rect x="36" y="20" width="10" height="170" fill="url(#gloss-{gid})" opacity=".7" clip-path="url(#clip-{gid})"/>

        <!-- ของเหลว + ผิวน้ำ -->
        <g clip-path="url(#clip-{gid})">
          <path d="{wave_path}" fill="url(#liquid-{gid})"/>
          <!-- กราฟย่อย แสดงเมื่อ hover -->
          <g class="dist-group">
            {"".join(bars)}
            {"".join(labels_svg)}
          </g>
        </g>
      </g>

      <!-- ป้าย max -->
      <g>
        <rect x="94" y="22" rx="10" ry="10" width="54" height="22" fill="#ffffff" stroke="#e5e7eb"/>
        <text x="121" y="38" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text>
      </g>

      <!-- ชื่อกรุ๊ปเลือด (ขาวมีเส้นขอบอ่อน) -->
      <text x="82" y="120" text-anchor="middle" font-size="32" font-weight="800"
            fill="#ffffff" stroke="#e5e7eb" stroke-width="3">{blood_type}</text>
    </svg>

    <div class="bag-caption">
      <div class="total">{min(total, BAG_MAX)} / {BAG_MAX} unit</div>
      <div style="font-size:12px">{label}</div>
      <div class="tip">เอาเมาส์วางบนถุงเพื่อดูสัดส่วน PRC / Platelets / Plasma / Cryo</div>
    </div>
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
    total = int(info.get("total", 0))
    dist_list = get_stock_by_blood(bt)  # [{product_type, units}]
    dist = { d["product_type"]: int(d["units"]) for d in dist_list }

    with cols[i]:
        st.markdown(f"### ถุงเลือดกรุ๊ป **{bt}**")
        st_html(bag_svg_with_distribution(bt, total, dist), height=260, scrolling=False)
        if st.button(f"ดูรายละเอียดกรุ๊ป {bt}", key=f"btn_{bt}"):
            st.session_state["selected_bt"] = bt
            selected = bt

st.divider()

# ===== DETAIL =====
if not selected:
    st.info("กดเลือกรายละเอียดที่กรุ๊ปโลหิตด้านบน เพื่อดูสต็อกตามประเภทผลิตภัณฑ์และทำรายการเบิก/นำเข้า")
else:
    st.subheader(f"รายละเอียดกรุ๊ป {selected}")

    total_selected = next(d for d in overview if d["blood_type"] == selected)["total"]
    dist_selected_list = get_stock_by_blood(selected)
    dist_selected = { d["product_type"]: int(d["units"]) for d in dist_selected_list }

    st_html(bag_svg_with_distribution(selected, int(total_selected), dist_selected), height=260, scrolling=False)

    df = pd.DataFrame(dist_selected_list)
    if df.empty:
        st.warning("ยังไม่มีข้อมูลในคลังสำหรับกรุ๊ปนี้")
    else:
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X('product_type:N', title='ประเภทผลิตภัณฑ์'),
            y=alt.Y('units:Q', title='จำนวนหน่วย (unit)', scale=alt.Scale(domainMin=0, domainMax=BAG_MAX)),
            tooltip=['product_type','units']
        ).properties(height=320)
        st.altair_chart(chart, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ===== Update Mode =====
    if admin_mode and pin_ok:
        st.markdown("#### ปรับปรุงคลัง")
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            product = st.selectbox("ประเภทผลิตภัณฑ์", ["PRC","Platelets","Plasma","Cryo"])
        with c2:
            qty = int(st.number_input("จำนวน (หน่วย)", min_value=1, max_value=1000, value=1, step=1))
        with c3:
            note = st.text_input("หมายเหตุ", placeholder="เหตุผลการทำรายการ เช่น นำเข้า/เบิกให้ผู้ป่วย/ทดแทนการหมดอายุ")

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

    st.markdown("#### รายการความเคลื่อนไหวล่าสุด")
    tx = get_transactions(50, blood_type=selected)
    if tx:
        st.dataframe(pd.DataFrame(tx), use_container_width=True, hide_index=True)
    else:
        st.write("— ไม่มีรายการ —")
