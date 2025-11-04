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

# ----- product name normalization (DB -> UI) -----
RENAME_TO_UI = {
    "Plasma": "FFP",      # เปลี่ยนชื่อ Plasma -> FFP
    "Platelets": "PC",    # Platelets -> PC
}
ALL_PRODUCTS_UI = ["LPRC", "PRC", "FFP", "Cryo", "PC"]  # ลำดับกราฟที่ต้องการ

def normalize_products(rows):
    """
    rows: [{'product_type':..., 'units':...}]
    -> dict ที่แปลงชื่อเป็น UI และเติม 0 ให้ครบทุกชนิด
       โดย 'Cryo' = ผลรวม LPRC+PRC+FFP+PC
    """
    d = {name: 0 for name in ALL_PRODUCTS_UI}
    for r in rows:
        name = str(r.get("product_type","")).strip()
        ui = RENAME_TO_UI.get(name, name)
        if ui in d and ui != "Cryo":
            d[ui] += int(r.get("units",0))
    d["Cryo"] = d["LPRC"] + d["PRC"] + d["FFP"] + d["PC"]  # Cryo = รวมทั้งหมด
    return d

# ===== SVG Blood Bag (ขอบแดงเลอะ ๆ + ตัวอักษรเด่น + กราฟในถุงโชว์ตอน hover) =====
def bag_svg_with_distribution(blood_type: str, total: int, dist: dict) -> str:
    status, label, pct = compute_bag(total)
    fill = bag_color(status)

    # สีตัวอักษรตามกรุ๊ป (ให้ชัดขึ้น)
    letter_fill = {
        "A":  "#facc15",   # เหลือง
        "B":  "#f472b6",   # ชมพู
        "O":  "#60a5fa",   # ฟ้า
        "AB": "#ffffff",   # ขาว
    }.get(blood_type, "#ffffff")
    letter_stroke = "#111827" if blood_type != "AB" else "#6b7280"  # ขอบเข้มให้คอนทราสต์

    # ความสูงของของเหลว (พื้นที่ภายใน)
    inner_h = 148.0
    inner_y0 = 40.0
    water_h = inner_h * pct / 100.0
    water_y = inner_y0 + (inner_h - water_h)

    # ลำดับแท่ง + สี (มี LPRC และ Cryo=รวม)
    ORDER  = ALL_PRODUCTS_UI                   # ["LPRC","PRC","FFP","Cryo","PC"]
    COLORS = {"LPRC": "#8b5cf6", "PRC":"#1f77b4", "FFP":"#22c55e", "Cryo":"#ef4444", "PC":"#e11d48"}
    vals   = [max(0, int(dist.get(k, 0))) for k in ORDER]
    bar_hs = [(min(v, BAG_MAX)/BAG_MAX) * water_h for v in vals]
    gap = 6
    inner_w = 84.0
    bar_w = (inner_w - gap*4)/5.0
    x0 = 30.0
    bars, labels_svg = [], []
    for i, (k, h) in enumerate(zip(ORDER, bar_hs)):
        x = x0 + i*(bar_w + gap)
        y = water_y + (water_h - h)
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="4" fill="{COLORS[k]}" />'
        )
        labels_svg.append(
            f'<text x="{x + bar_w/2:.1f}" y="{max(y+12, water_y+12):.1f}" '
            f'text-anchor="middle" font-size="9" font-weight="800" fill="#fff">{k}</text>'
        )

    gid = f"g_{blood_type}"

    # ผิวน้ำโค้งเล็กน้อย
    wave_amp = 5 + 6*(pct/100)
    wave_path = (
        f"M24,{water_y:.1f} "
        f"Q54,{water_y - wave_amp:.1f} 84,{water_y:.1f} "
        f"Q114,{water_y + wave_amp:.1f} 144,{water_y:.1f} "
        f"L144,198 24,198 Z"
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
        <!-- คราบแดง/ขอบ -->
        <filter id="rough-{gid}">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="1" seed="8" result="noise"/>
          <feColorMatrix type="saturate" values="0.2" in="SourceGraphic"/>
        </filter>
        <filter id="blood-smear-{gid}" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="2.2"/>
        </filter>
        <!-- เงาอักษร -->
        <filter id="textshadow-{gid}">
          <feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-color="#111827" flood-opacity="0.65"/>
        </filter>
      </defs>

      <!-- หูหิ้ว -->
      <circle cx="84" cy="10" r="7.5" fill="#eef2ff" stroke="#dbe0ea" stroke-width="3"/>
      <rect x="77.5" y="14" width="13" height="8" rx="3" fill="#e5e7eb"/>

      <!-- ตัวถุง: ขอบแดงเลอะ ๆ (สองชั้น) -->
      <g>
        <path d="M16,34 C16,18 32,8 52,8 L116,8 C136,8 152,18 152,34
                 L152,176 C152,195 136,206 116,206 L52,206 C32,206 16,195 16,176 Z"
              fill="#ffffff"
              stroke="#7f1d1d" stroke-width="6" opacity=".15" filter="url(#blood-smear-{gid})"/>
        <path d="M16,34 C16,18 32,8 52,8 L116,8 C136,8 152,18 152,34
                 L152,176 C152,195 136,206 116,206 L52,206 C32,206 16,195 16,176 Z"
              fill="#ffffff" stroke="#dc2626" stroke-width="3" filter="url(#rough-{gid})"/>
      </g>

      <!-- ของเหลว + กราฟ -->
      <g clip-path="url(#clip-{gid})">
        <path d="{wave_path}" fill="url(#liquid-{gid})"/>
        <g class="dist-group">
          {"".join(bars)}
          {"".join(labels_svg)}
        </g>
      </g>

      <!-- แถบไฮไลต์ -->
      <rect x="38" y="22" width="10" height="176" fill="url(#gloss-{gid})" opacity=".7" clip-path="url(#clip-{gid})"/>

      <!-- ป้าย max -->
      <g>
        <rect x="98" y="24" rx="10" ry="10" width="54" height="22" fill="#ffffff" stroke="#e5e7eb"/>
        <text x="125" y="40" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text>
      </g>

      <!-- ชื่อกรุ๊ป (หนา-ชัด + เงา) -->
      <text x="84" y="126" text-anchor="middle" font-size="32" font-weight="900"
            style="paint-order: stroke fill"
            stroke="{letter_stroke}" stroke-width="4"
            fill="{letter_fill}" filter="url(#textshadow-{gid})">{blood_type}</text>
    </svg>

    <div class="bag-caption">
      <div class="total">{min(total, BAG_MAX)} / {BAG_MAX} unit</div>
      <div style="font-size:12px">{label}</div>
      <div class="tip">เอาเมาส์วางบนถุงเพื่อดูสัดส่วน LPRC / PRC / FFP / Cryo(รวม) / PC</div>
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
    # แปลงข้อมูลสำหรับกราฟ/ถุง
    dist = normalize_products(get_stock_by_blood(bt))  # dict พร้อม Cryo = รวม

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
    dist_selected = normalize_products(get_stock_by_blood(selected))

    st_html(bag_svg_with_distribution(selected, int(total_selected), dist_selected), height=260, scrolling=False)

    # ตาราง+กราฟ Altair (ใช้ชื่อ UI)
    df = pd.DataFrame([{"product_type":k, "units":v} for k,v in dist_selected.items()])
    df = df.set_index("product_type").loc[ALL_PRODUCTS_UI].reset_index()

    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('product_type:N', title='ประเภทผลิตภัณฑ์ (LPRC, PRC, FFP, Cryo=รวม, PC)'),
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
            product = st.selectbox("ประเภทผลิตภัณฑ์", ["LPRC","PRC","FFP","PC"])  # Cryo เป็นยอดรวม ไม่ให้แก้ตรง ๆ
        with c2:
            qty = int(st.number_input("จำนวน (หน่วย)", min_value=1, max_value=1000, value=1, step=1))
        with c3:
            note = st.text_input("หมายเหตุ", placeholder="เหตุผลการทำรายการ เช่น นำเข้า/เบิกให้ผู้ป่วย/ทดแทนการหมดอายุ")

        current_total = int(total_selected)
        current_by_product = int(dist_selected.get(product, 0))

        b1, b2 = st.columns(2)
        with b1:
            if st.button("➕ นำเข้าเข้าคลัง", use_container_width=True):
                space = max(0, BAG_MAX - min(current_total, BAG_MAX))   # จำกัดรวมไม่เกิน 20
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
                take = min(qty, current_by_product)  # ไม่ให้ติดลบ
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
