import os, time
from datetime import datetime, date, datetime as dt
import pandas as pd
import altair as alt
import streamlit as st
from streamlit.components.v1 import html as st_html

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    def st_autorefresh(*args, **kwargs): return None

# ===== DB funcs =====
from db import init_db, get_all_status, get_stock_by_blood, adjust_stock, reset_stock

# ============ PAGE / THEME ============
st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")

# (คง CSS เดิมทั้งหมดของคุณไว้)
st.markdown("""<style>
.block-container{padding-top:1.0rem;}
h1,h2,h3{letter-spacing:.2px}
[data-testid="stSidebar"]{background:#2e343a;}
[data-testid="stSidebar"] .stButton>button{width:100%;background:#fff;color:#111827;border:1px solid #cbd5e1;border-radius:12px;font-weight:700;}
.flash{position:fixed; top:110px; right:24px; z-index:9999; color:#fff; padding:.7rem 1rem; border-radius:12px; font-weight:800; box-shadow:0 10px 24px rgba(0,0,0,.18)}
.flash.success{background:#16a34a}
.flash.error{background:#ef4444}
</style>""", unsafe_allow_html=True)

BAG_MAX, CRITICAL_MAX, YELLOW_MAX = 20, 4, 15
AUTH_PASSWORD = "1234"
FLASH_SECONDS = 2.5

RENAME_TO_UI = {"Plasma": "FFP", "Platelets": "PC"}
UI_TO_DB = {"LPRC": "LPRC", "PRC": "PRC", "FFP": "Plasma", "PC": "Platelets"}
ALL_PRODUCTS_UI = ["LPRC", "PRC", "FFP", "Cryo", "PC"]

STATUS_OPTIONS = ["ว่าง","จอง","จำหน่าย","Exp","หลุดจอง"]
STATUS_COLOR = {
    "ว่าง": "🟢 ว่าง","จอง": "🟠 จอง","จำหน่าย": "⚫ จำหน่าย","Exp": "🔴 Exp","หลุดจอง": "🔵 หลุดจอง",
}

# ====== STATE ======
def _init_state():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("page", "หน้าหลัก")
    st.session_state.setdefault("entries", pd.DataFrame())
    st.session_state.setdefault("activity", [])
_init_state()

def flash(msg, typ="success"):
    st.session_state["flash"] = {"text": msg, "type": typ, "until": time.time()+FLASH_SECONDS}

def show_flash():
    f = st.session_state.get("flash")
    if f and time.time() < f["until"]:
        st.markdown(f'<div class="flash {f["type"]}">{f["text"]}</div>', unsafe_allow_html=True)
    else:
        st.session_state["flash"] = None

def _safe_rerun():
    try: st.rerun()
    except Exception: st.experimental_rerun()

# ====== HELPERS ======
def compute_bag(total, max_cap=BAG_MAX):
    if total <= CRITICAL_MAX: return "red","วิกฤตใกล้หมด", int(total/max_cap*100)
    if total <= YELLOW_MAX: return "yellow","เพียงพอ", int(total/max_cap*100)
    return "green","ปกติ", int(min(total,max_cap)/max_cap*100)

def bag_color(s): return {"green":"#22c55e","yellow":"#f59e0b","red":"#ef4444"}[s]

def bag_svg(bt, total):
    s,_,pct = compute_bag(total)
    color = bag_color(s)
    letter = {"A":"#facc15","B":"#f472b6","O":"#60a5fa","AB":"#fff"}[bt]
    return f"""
    <svg width="160" height="200" viewBox="0 0 160 200">
      <rect x="20" y="10" rx="18" ry="18" width="120" height="180"
            fill="white" stroke="#800000" stroke-width="4"/>
      <rect x="25" y="{190 - (160*pct/100)}" width="110" height="{160*pct/100}"
            fill="{color}"/>
      <text x="80" y="105" text-anchor="middle" font-size="48"
            font-weight="700" stroke="#111" stroke-width="4" fill="{letter}">{bt}</text>
    </svg>
    """

def totals_overview(): return {r["blood_type"]:int(r["total"] or 0) for r in get_all_status()}
def normalize_products(rows):
    d={k:0 for k in ALL_PRODUCTS_UI}
    for r in rows:
        ui=RENAME_TO_UI.get(r["product_type"],r["product_type"])
        if ui in d: d[ui]+=int(r["units"])
    return d
def products_of(bt): return normalize_products(get_stock_by_blood(bt))

# ====== INIT DB ======
if not os.path.exists(os.getenv("BLOOD_DB_PATH","blood.db")):
    init_db()

# ====== SIDEBAR ======
with st.sidebar:
    if not st.session_state["logged_in"]:
        st.text_input("Username", key="username_input")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if pwd == AUTH_PASSWORD:
                st.session_state["logged_in"]=True
                st.session_state["username"]=st.session_state["username_input"] or "staff"
                flash("เข้าสู่ระบบสำเร็จ ✅")
                _safe_rerun()
            else: st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        st.success(f"เข้าสู่ระบบในชื่อ {st.session_state['username']}")
        if st.button("Logout"):
            st.session_state["logged_in"]=False
            _safe_rerun()
    st.divider()
    if st.button("หน้าหลัก"): st.session_state["page"]="หน้าหลัก"; _safe_rerun()
    if st.button("กรอกเลือด"): st.session_state["page"]="กรอกเลือด"; _safe_rerun()

# ====== HEADER ======
st.title("🩸 Blood Stock Real-time Monitor")
st.caption(f"อัปเดต: {datetime.now():%d/%m/%Y %H:%M:%S}")
show_flash()

# ====== PAGE: หน้าหลัก ======
if st.session_state["page"]=="หน้าหลัก":
    totals = totals_overview()
    bt_order=["A","B","O","AB"]
    cols = st.columns(4)
    for i,bt in enumerate(bt_order):
        with cols[i]:
            st.markdown(f"### ถุงเลือดกรุ๊ป {bt}")
            st_html(bag_svg(bt, totals.get(bt,0)),height=240)
    st.divider()
    st.subheader("📊 รายละเอียดกรุ๊ป O")
    df = pd.DataFrame([{"Product":k,"Units":v} for k,v in products_of("O").items()])
    chart = alt.Chart(df).mark_bar().encode(x="Product",y="Units",tooltip=["Product","Units"])
    st.altair_chart(chart,use_container_width=True)

    st.divider()
    if st.session_state["activity"]:
        st.subheader("📜 บันทึกความเคลื่อนไหวล่าสุด")
        st.dataframe(pd.DataFrame(st.session_state["activity"]),use_container_width=True)
    else:
        st.info("ยังไม่มีรายการ")

    st.divider()
    if st.session_state["logged_in"]:
        st.subheader("⚙️ เครื่องมือเจ้าหน้าที่")
        c1,c2 = st.columns(2)
        with c1:
            if st.button("🧹 ล้างเลือดออกทั้งหมด (Reset Stock)"):
                reset_stock()
                flash("รีเซ็ตสต็อกทั้งหมดเรียบร้อย ✅")
                _safe_rerun()

# ====== PAGE: กรอกเลือด ======
elif st.session_state["page"]=="กรอกเลือด":
    if not st.session_state["logged_in"]:
        st.warning("ต้องล็อกอินก่อนใช้งาน")
    else:
        st.subheader("กรอกเลือดใหม่")
        with st.form("blood_form"):
            c1,c2=st.columns(2)
            unit=c1.text_input("Unit number")
            exp=c2.date_input("Exp date",value=date.today())
            c3,c4=st.columns(2)
            group=c3.selectbox("Group",["A","B","O","AB"])
            comp=c4.selectbox("Component",["LPRC","PRC","FFP","PC"])
            status=st.selectbox("Status",STATUS_OPTIONS)
            note=st.text_input("หมายเหตุ")
            ok=st.form_submit_button("บันทึก")
        if ok:
            try:
                user=st.session_state["username"]
                qty = 1 if status in ["ว่าง","หลุดจอง"] else -1 if status in ["จำหน่าย","Exp"] else 0
                if qty!=0:
                    adjust_stock(group,UI_TO_DB[comp],qty,actor=user,note=note)
                st.session_state["activity"].insert(0,{
                    "เวลา":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ผู้ทำรายการ":user,"กรุ๊ป":group,"คอมโพเนนต์":comp,
                    "สถานะ":status,"จำนวน":qty,"หมายเหตุ":note
                })
                flash("บันทึกสำเร็จ ✅")
                _safe_rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

        st.divider()
        st.subheader("📥 นำเข้าข้อมูลจาก Excel / CSV")
        file = st.file_uploader("เลือกไฟล์ (.xlsx, .csv)")
        if file:
            try:
                if file.name.endswith(".csv"):
                    df = pd.read_csv(file)
                else:
                    df = pd.read_excel(file)
                if {"Group","Blood Components","Status"}.issubset(df.columns):
                    ok, fail = 0, 0
                    for _,r in df.iterrows():
                        g = str(r["Group"]).strip() or "A"
                        c = str(r["Blood Components"]).strip() or "LPRC"
                        s = str(r["Status"]).strip() or "ว่าง"
                        n = str(r.get("บันทึก",""))
                        try:
                            user=st.session_state["username"]
                            q = 1 if s in ["ว่าง","หลุดจอง"] else -1 if s in ["จำหน่าย","Exp"] else 0
                            if q!=0: adjust_stock(g,UI_TO_DB[c],q,actor=user,note=n)
                            ok+=1
                        except Exception: fail+=1
                    flash(f"อัปโหลดสำเร็จ {ok} รายการ{' ล้มเหลว '+str(fail) if fail else ''}")
                    _safe_rerun()
                else:
                    st.error("ไฟล์ไม่ถูกต้อง ต้องมีคอลัมน์ Group, Blood Components, Status")
            except Exception as e:
                st.error(f"ไม่สามารถอ่านไฟล์ได้: {e}")
