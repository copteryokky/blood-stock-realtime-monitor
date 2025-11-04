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

# ----------------- PAGE CONFIG & THEME TWEAK -----------------
st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")
st.markdown("""
<style>
.block-container{padding-top:1.2rem;}
h1,h2,h3{letter-spacing:.2px}
.badge{display:inline-flex;align-items:center;gap:.4rem;padding:.25rem .5rem;border-radius:999px;background:#f3f4f6}
.legend-dot{width:.7rem;height:.7rem;border-radius:999px;display:inline-block}
.stButton>button{border-radius:12px;padding:.55rem 1rem;font-weight:600}

/* ===== Blood bag look & hover reveal ===== */
.bag-wrap{display:flex;flex-direction:column;align-items:center;gap:8px}
.bag{transition:transform .18s ease, filter .18s ease}
.bag:hover{transform:translateY(-2px); filter: drop-shadow(0 8px 24px rgba(0,0,0,.12));}
.dist-bars{opacity:0; transition:opacity .2s ease;}
.bag:hover .dist-bars{opacity:1;}
.bag-caption{ text-align:center; line-height:1.2 }
.bag-caption .total{font-weight:700}
.bag-caption .tip{font-size:10px;color:#6b7280}
</style>
""", unsafe_allow_html=True)

# ----------------- CONFIG -----------------
BAG_MAX      = 20   # เต็มคลังของแต่ละกรุ๊ป
CRITICAL_MAX = 4    # 0–4 = แดง
YELLOW_MAX   = 15   # 5–15 = เหลือง  |  >=16 = เขียว

# ----------- helpers -----------
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

def bag_svg_with_distribution(blood_type: str, total: int, dist: dict) -> str:
    """
    ถุงเลือดสไตล์ใหม่ (gradient + gloss + shadow)
    และกราฟแท่งภายในถุง 'โผล่เฉพาะตอน hover'
    """
    status, label, pct = compute_bag(total)
    fill = bag_color(status)

    # ระดับน้ำ
    water_h = 162 * pct / 100.0
    water_y = 182 - water_h

    # ข้อมูลแท่งย่อย
    keys = ["PRC", "Platelets", "Plasma", "Cryo"]
    vals = [max(0, int(dist.get(k, 0))) for k in keys]
    bar_heights = [(min(v, BAG_MAX) / BAG_MAX) * water_h for v in vals]
    gap = 5
    bar_w = (78 - gap*3)/4.0
    bars = []
    x0 = 31
    for i, h in enumerate(bar_heights):
        x = x0 + i*(bar_w+gap)
        y = water_y + (water_h - h)
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
            f'fill="#2563eb" rx="3" class="bar" />'
        )

    gid = f"g_{blood_type}"

    return f"""
    <div class="bag-wrap">
      <svg class="bag" width="160" height="210" viewBox="0 0 140 190" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="shadow_{gid}" x="-20%" y="-20%" width="160%" height="160%">
            <feDropShadow dx="0" dy="6" stdDeviation="7" flood-opacity="0.18"/>
          </filter>
          <clipPath id="clip_{gid}">
            <path d="M30,22 C30,12 40,6 50,6 L90,6 C100,6 110,12 110,22 L110,155
                     C110,170 100,180 85,182 L45,182 C30,180 30,170 30,155 Z" />
          </clipPath>
          <linearGradient id="liquid_{gid}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"  stop-color="{fill}" stop-opacity=".95"/>
            <stop offset="100%" stop-color="{fill}" stop-opacity=".85"/>
          </linearGradient>
          <linearGradient id="gloss_{gid}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="rgba(255,255,255,.65)"/>
            <stop offset="100%" stop-color="rgba(255,255,255,0)"/>
          </linearGradient>
        </defs>

        <!-- หูหิ้ว -->
        <path d="M55,8 L55,0 M85,8 L85,0" stroke="#9ca3af" stroke-width="6" stroke-linecap="round"/>

        <!-- ตัวถุง -->
        <g filter="url(#shadow_{gid})">
          <path d="M30,22 C30,12 40,6 50,6 L90,6 C100,6 110,12 110,22 L110,155
                   C110,170 100,180 85,182 L45,182 C30,180 30,170 30,155 Z"
                fill="#ffffff" stroke="#e5e7eb" stroke-width="3"/>

          <!-- ของเหลว -->
          <rect x="31" y="{water_y:.1f}" width="78" height="{water_h:.1f}"
                fill="url(#liquid_{gid})" clip-path="url(#clip_{gid})"/>

          <!-- กราฟแท่ง (ซ่อน จน hover ค่อยขึ้น) -->
          <g class="dist-bars" clip-path="url(#clip_{gid})">
            {"".join(bars)}
          </g>

          <!-- เส้นผิวน้ำ -->
          <path d="M31,155 Q70,170 109,155" fill="none" stroke="rgba(0,0,0,0.10)"/>
          <!-- ไฮไลต์ -->
          <rect x="36" y="18" width="8" height="160" fill="url(#gloss_{gid})" opacity=".55" clip-path="url(#clip_{gid})"/>
        </g>

        <!-- ป้าย max -->
        <g>
          <rect x="76" y="15" rx="10" ry="10" width="50" height="22" fill="#ffffff" stroke="#e5e7eb"/>
          <text x="101" y="30" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text>
        </g>

        <!-- label กรุ๊ป -->
        <text x="70" y="120" text-anchor="middle" font-weight="bold" font-size="28" fill="#ffffff">{blood_type}</text>
      </svg>

      <div class="bag-caption">
        <div class="total">{min(total, BAG_MAX)} / {BAG_MAX} unit</div>
        <div style="font-size:12px">{label}</div>
        <div class="tip">เลื่อนเมาส์บนถุงเพื่อดูกราฟชนิดผลิตภัณฑ์</div>
      </div>
    </div>
    """

# ----------- init DB -----------
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()

ADMIN_KEY = os.environ.get("BLOOD_ADMIN_KEY", "1234")

# ----------- SIDEBAR -----------
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

# ----------- HEADER -----------
left, right = st.columns([3,1])
with left:
    st.title("Blood Stock Real-time Monitor")
    st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
with right:
    try:
        st.image("assets/header.jpg", use_container_width=True)
    except Exception:
        pass

# ----------- LEGEND -----------
c1, c2, c3 = st.columns(3)
c1.markdown('<span class="badge"><span class="legend-dot" style="background:#ef4444"></span> วิกฤตใกล้หมด 0–4</span>', unsafe_allow_html=True)
c2.markdown('<span class="badge"><span class="legend-dot" style="background:#f59e0b"></span> เพียงพอ 5–15</span>', unsafe_allow_html=True)
c3.markdown('<span class="badge"><span class="legend-dot" style="background:#22c55e"></span> ปกติ ≥16</span>', unsafe_allow_html=True)

# ----------- OVERVIEW -----------
overview = get_all_status()

# เรียงกรุ๊ปตามที่ต้องการ
blood_types = ["A", "B", "O", "AB"]

cols = st.columns(4)
selected = st.session_state.get("selected_bt")

for i, bt in enumerate(blood_types):
    info = next(d for d in overview if d["blood_type"] == bt)
    total = int(info.get("total", 0))
    # distribution เพื่อวาดในถุง
    dist_list = get_stock_by_blood(bt)  # [{product_type, units}]
    dist = { d["product_type"]: int(d["units"]) for d in dist_list }

    with cols[i]:
        st.markdown(f"### ถุงเลือดกรุ๊ป **{bt}**")
        st.markdown(bag_svg_with_distribution(bt, total, dist), unsafe_allow_html=True)
        if st.button(f"ดูรายละเอียดกรุ๊ป {bt}", key=f"btn_{bt}"):
            st.session_state["selected_bt"] = bt
            selected = bt

st.divider()

# ----------- DETAIL -----------
if not selected:
    st.info("กดเลือกรายละเอียดที่กรุ๊ปโลหิตด้านบน เพื่อดูสต็อกตามประเภทผลิตภัณฑ์และทำรายการเบิก/นำเข้า")
else:
    st.subheader(f"รายละเอียดกรุ๊ป {selected}")

    total_selected = next(d for d in overview if d["blood_type"] == selected)["total"]
    dist_selected_list = get_stock_by_blood(selected)
    dist_selected = { d["product_type"]: int(d["units"]) for d in dist_selected_list }
    st.markdown(bag_svg_with_distribution(selected, int(total_selected), dist_selected), unsafe_allow_html=True)

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

    # ---------- UPDATE MODE ----------
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
