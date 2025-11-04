import os
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html  # ใช้ component html สำหรับ SVG

# ===== Auto refresh helper =====
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    def st_autorefresh(*args, **kwargs):
        return None

from db import (
    init_db,
    get_all_status,
    get_stock_by_blood,
    adjust_stock,
    get_transactions,
)

# ===== PAGE CONFIG & THEME =====
st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")
st.markdown(
    """
<style>
.block-container{padding-top:1.2rem;}
h1,h2,h3{letter-spacing:.2px}
.badge{display:inline-flex;align-items:center;gap:.4rem;padding:.25rem .5rem;border-radius:999px;background:#f3f4f6}
.legend-dot{width:.7rem;height:.7rem;border-radius:999px;display:inline-block}
.stButton>button{border-radius:12px;padding:.55rem 1rem;font-weight:600}
</style>
""",
    unsafe_allow_html=True,
)

# ===== CONFIG =====
BAG_MAX = 20        # เต็มคลังต่อกรุ๊ป
CRITICAL_MAX = 4    # 0–4 แดง
YELLOW_MAX = 15     # 5–15 เหลือง (≥16 เขียว)

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
    return {"green": "#22c55e", "yellow": "#f59e0b", "red": "#ef4444"}[status]


def norm_pin(s: str) -> str:
    trans = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
    return (s or "").translate(trans).strip()


# ===== SVG Blood Bag (สมจริง + กราฟภายในโชว์ตอน hover + ชื่อชนิดเลือด) =====
def bag_svg_with_distribution(blood_type: str, total: int, dist: dict) -> str:
    status, label, pct = compute_bag(total)
    fill = bag_color(status)

    # พื้นที่ด้านในของถุง (สำหรับน้ำ/กราฟ)
    INNER_LEFT, INNER_RIGHT = 36.0, 114.0
    INNER_TOP, INNER_BOTTOM = 30.0, 186.0
    INNER_W = INNER_RIGHT - INNER_LEFT          # 78
    INNER_H = INNER_BOTTOM - INNER_TOP          # 156

    # ระดับผิวน้ำ (อิง 0..20) -> 0..INNER_H
    water_h = INNER_H * max(0, min(BAG_MAX, min(total, BAG_MAX))) / BAG_MAX
    water_y = INNER_BOTTOM - water_h

    # กราฟย่อยในถุง
    ORDER = ["PRC", "Platelets", "Plasma", "Cryo"]
    COLORS = {
        "PRC": "#1f77b4",       # ฟ้า
        "Platelets": "#ff7f0e", # ส้ม
        "Plasma": "#2ca02c",    # เขียว
        "Cryo": "#d62728",      # แดง
    }
    vals = [max(0, int(dist.get(k, 0))) for k in ORDER]
    bar_heights = [(min(v, BAG_MAX) / BAG_MAX) * water_h for v in vals]

    gap = 6.0
    bar_w = (INNER_W - gap * 3) / 4.0
    bars, labels = [], []
    for i, (k, h) in enumerate(zip(ORDER, bar_heights)):
        x = INNER_LEFT + i * (bar_w + gap)
        y = water_y + (water_h - h)  # ดันจากก้นน้ำขึ้นมา
        color = COLORS[k]
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="4" fill="{color}"></rect>'
        )
        # ป้ายชื่อชนิดเลือดบนแท่ง (อ่านง่ายเวลา hover)
        ty = max(y + 12, water_y + 12)
        labels.append(
            f'<text x="{x + bar_w/2:.1f}" y="{ty:.1f}" text-anchor="middle" '
            f'font-size="9" font-weight="600" fill="white">{k}</text>'
        )

    gid = f"g_{blood_type}"

    return f"""
<div>
  <style>
    .bag-wrap{{display:flex;flex-direction:column;align-items:center;gap:8px;
               font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial}}
    .bag{{transition:transform .18s ease, filter .18s ease}}
    .bag:hover{{transform:translateY(-2px); filter:drop-shadow(0 8px 24px rgba(0,0,0,.12));}}
    .dist-group{{opacity:0; transition:opacity .2s ease;}}
    .bag:hover .dist-group{{opacity:1;}}
    .bag-caption{{text-align:center; line-height:1.2}}
    .bag-caption .total{{font-weight:700}}
    .bag-caption .tip{{font-size:10px;color:#6b7280}}
  </style>

  <div class="bag-wrap">
    <svg class="bag" width="170" height="220" viewBox="0 0 150 200" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="shadow_{gid}" x="-20%" y="-20%" width="160%" height="160%">
          <feDropShadow dx="0" dy="6" stdDeviation="7" flood-opacity="0.18"/>
        </filter>
        <clipPath id="clip_{gid}">
          <!-- โครงด้านในของถุง (พื้นที่น้ำ/กราฟ) -->
          <path d="M35,25 C35,13 45,7 57,7 L93,7 C105,7 115,13 115,25 L115,160
                   C115,176 104,186 88,188 L62,188 C46,186 35,176 35,160 Z"/>
        </clipPath>
        <linearGradient id="liquid_{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"  stop-color="{fill}" stop-opacity=".96"/>
          <stop offset="100%" stop-color="{fill}" stop-opacity=".86"/>
        </linearGradient>
        <linearGradient id="gloss_{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="rgba(255,255,255,.65)"/>
          <stop offset="100%" stop-color="rgba(255,255,255,0)"/>
        </linearGradient>
      </defs>

      <!-- หูถุง/คอท่อ -->
      <rect x="70" y="0" width="10" height="10" rx="5" fill="#9ca3af"/>
      <rect x="68" y="10" width="14" height="6" rx="3" fill="#cbd5e1"/>
      <path d="M75,16 C75,22 75,22 75,22" stroke="#cbd5e1" stroke-width="4" stroke-linecap="round"/>

      <!-- สเกลด้านซ้ายให้สมจริง -->
      <g opacity=".35">
        <line x1="28" x2="28" y1="28" y2="184" stroke="#9ca3af" stroke-width="1"/>
        {"".join([f'<line x1="26" x2="30" y1="{y}" y2="{y}" stroke="#9ca3af" stroke-width="{2 if i%5==0 else 1}"/>'
                 for i,y in enumerate(range(184, 27, -8))])}
      </g>

      <!-- ตัวถุง -->
      <g filter="url(#shadow_{gid})">
        <path d="M35,25 C35,13 45,7 57,7 L93,7 C105,7 115,13 115,25 L115,160
                 C115,176 104,186 88,188 L62,188 C46,186 35,176 35,160 Z"
              fill="#ffffff" stroke="#e5e7eb" stroke-width="3"/>

        <!-- ของเหลวในถุง -->
        <rect x="{INNER_LEFT:.1f}" y="{water_y:.1f}" width="{INNER_W:.1f}" height="{water_h:.1f}"
              fill="url(#liquid_{gid})" clip-path="url(#clip_{gid})"/>

        <!-- กราฟย่อย + ป้ายชื่อ (แสดงเฉพาะตอน hover) -->
        <g class="dist-group" clip-path="url(#clip_{gid})">
          {"".join(bars)}
          {"".join(labels)}
        </g>

        <!-- ผิวน้ำโค้ง + ไฮไลต์ -->
        <path d="M{INNER_LEFT:.1f},160 Q75,174 {INNER_RIGHT:.1f},160" fill="none" stroke="rgba(0,0,0,0.10)"/>
        <rect x="{INNER_LEFT+5:.1f}" y="21" width="9" height="165" fill="url(#gloss_{gid})" opacity=".55" clip-path="url(#clip_{gid})"/>
      </g>

      <!-- ป้าย 20 max -->
      <g>
        <rect x="82" y="17" rx="10" ry="10" width="52" height="22" fill="#ffffff" stroke="#e5e7eb"/>
        <text x="108" y="32" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text>
      </g>

      <!-- ตัวอักษรกรุ๊ป -->
      <text x="75" y="125" text-anchor="middle" font-weight="bold" font-size="28" fill="#ffffff">{blood_type}</text>
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
left, right = st.columns([3, 1])
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

    # distribution เพื่อวาดในถุง
    dist_list = get_stock_by_blood(bt)  # [{product_type, units}]
    dist = {d["product_type"]: int(d["units"]) for d in dist_list}

    with cols[i]:
        st.markdown(f"### ถุงเลือดกรุ๊ป **{bt}**")
        # ใช้ st_html เพื่อ render SVG แยก scope ป้องกัน error React
        st_html(bag_svg_with_distribution(bt, total, dist), height=270, scrolling=False)
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
    dist_selected = {d["product_type"]: int(d["units"]) for d in dist_selected_list}

    st_html(bag_svg_with_distribution(selected, int(total_selected), dist_selected), height=270, scrolling=False)

    df = pd.DataFrame(dist_selected_list)
    if df.empty:
        st.warning("ยังไม่มีข้อมูลในคลังสำหรับกรุ๊ปนี้")
    else:
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X("product_type:N", title="ประเภทผลิตภัณฑ์"),
                y=alt.Y("units:Q", title="จำนวนหน่วย (unit)", scale=alt.Scale(domainMin=0, domainMax=BAG_MAX)),
                tooltip=["product_type", "units"],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ===== Update Mode =====
    if admin_mode and pin_ok:
        st.markdown("#### ปรับปรุงคลัง")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            product = st.selectbox("ประเภทผลิตภัณฑ์", ["PRC", "Platelets", "Plasma", "Cryo"])
        with c2:
            qty = int(st.number_input("จำนวน (หน่วย)", min_value=1, max_value=1000, value=1, step=1))
        with c3:
            note = st.text_input("หมายเหตุ", placeholder="เหตุผลการทำรายการ เช่น นำเข้า/เบิกให้ผู้ป่วย/ทดแทนการหมดอายุ")

        current_total = int(total_selected)
        current_by_product = int(dist_selected.get(product, 0))

        b1, b2 = st.columns(2)
        with b1:
            if st.button("➕ นำเข้าเข้าคลัง", use_container_width=True):
                # จำกัดรวมไม่เกิน 20
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
                take = min(qty, current_by_product)  # ไม่ให้ชนิดนั้นติดลบ
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
