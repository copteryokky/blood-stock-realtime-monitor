# app.py
import os
from datetime import datetime
import pandas as pd
import streamlit as st

# ================== CONFIG ==================
st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")

# --------- CSS: ทำให้ตัวหนังสือ/ช่องกรอกใน sidebar ชัดเจน + ปุ่มเมนูเต็มแถบ ---------
st.markdown("""
<style>
/* พื้นหลัง sidebar */
section[data-testid="stSidebar"] { background:#2b3137; }

/* หัวข้อ/ข้อความใน sidebar ให้อ่านง่าย */
section[data-testid="stSidebar"] h1, 
section[data-testid="stSidebar"] h2, 
section[data-testid="stSidebar"] h3, 
section[data-testid="stSidebar"] p, 
section[data-testid="stSidebar"] label {
  color:#f3f4f6 !important;
}

/* กล่อง input ใน sidebar */
section[data-testid="stSidebar"] input[type="text"],
section[data-testid="stSidebar"] input[type="password"]{
  background:#ffffff !important; color:#111827 !important;
  border:2px solid #e5e7eb !important; border-radius:10px !important;
}
section[data-testid="stSidebar"] input::placeholder{ color:#9ca3af !important; }

/* autofill ของ Chrome */
input:-webkit-autofill, input:-webkit-autofill:focus{
  -webkit-box-shadow:0 0 0px 1000px #ffffff inset !important;
  -webkit-text-fill-color:#111827 !important;
}

/* ปุ่ม primary (Login) สีแดง */
section[data-testid="stSidebar"] button[kind="primary"]{
  background:#ef4444 !important; color:#fff !important; border:none !important; 
  border-radius:10px !important; font-weight:700;
}
section[data-testid="stSidebar"] button[kind="primary"]:hover{ filter:brightness(.95); }

/* ปุ่มเมนูด้านซ้ายให้เป็นปุ่มยาวทั้งแถบ */
.sidebar-nav button {
  width:100%; border-radius:12px; border:1px solid #e5e7eb; 
  background:#ffffff; color:#111827; padding:.6rem .9rem; font-weight:600;
}
.sidebar-nav button:hover { filter:brightness(.96); }
.sidebar-nav .active { outline:3px solid #ef4444; }

/* เนื้อหาหลักให้โล่งอ่านง่าย */
.block-container { padding-top:1.2rem; }
</style>
""", unsafe_allow_html=True)

# ================== STATE ==================
if "page" not in st.session_state: st.session_state.page = "home"     # home | intake | login
if "authed" not in st.session_state: st.session_state.authed = False
if "user" not in st.session_state: st.session_state.user = ""
DATA_PATH = "blood_intake.csv"

# โหลด/เตรียมตารางรับเลือด
def load_df():
    if os.path.exists(DATA_PATH):
        try:
            df = pd.read_csv(DATA_PATH, dtype=str).fillna("")
        except Exception:
            df = pd.DataFrame(columns=["ID","หมู่เลือด","รหัส","ว่าง","จอง","จำหน่าย","หมดอายุ","ค่าสถานะ"])
    else:
        df = pd.DataFrame(columns=["ID","หมู่เลือด","รหัส","ว่าง","จอง","จำหน่าย","หมดอายุ","ค่าสถานะ"])
    return df

def save_df(df: pd.DataFrame):
    df.to_csv(DATA_PATH, index=False)

def derive_status(row):
    # ตามที่ผู้ใช้กำหนด: ว่าง=เขียว, จอง=เหลือง, จำหน่าย=เทา, หมดอายุ=แดง
    def filled(v): return str(v).strip() != "" and str(v).strip() != "0"
    if filled(row.get("หมดอายุ", "")): return "หมดอายุ (แดง)"
    if filled(row.get("จำหน่าย", "")): return "จำหน่าย (เทา)"
    if filled(row.get("จอง", "")):    return "จอง (เหลือง)"
    if filled(row.get("ว่าง", "")):    return "ว่าง (เขียว)"
    return "—"

@st.cache_data(show_spinner=False)
def _now_text():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# ================== SIDEBAR ==================
with st.sidebar:
    st.markdown("### เมนู")
    # ปุ่มเมนู (ไม่ใช่ checkbox)
    nav_home = st.container()
    with st.container():
        c = st.container()
        with c:
            st.markdown('<div class="sidebar-nav">', unsafe_allow_html=True)
            b1 = st.button("หน้าหลัก", use_container_width=True, key="nav_home")
            b2 = st.button("กรอกเลือด", use_container_width=True, key="nav_intake")
            b3 = st.button("เข้าสู่ระบบ" if not st.session_state.authed else "ออกจากระบบ", 
                           use_container_width=True, key="nav_login")
            st.markdown("</div>", unsafe_allow_html=True)
    # กำหนดหน้า
    if b1: 
        st.session_state.page = "home"; st.rerun()
    if b2:
        st.session_state.page = "intake"; st.rerun()
    if b3:
        st.session_state.page = "login"
        st.rerun()

    st.divider()

    # ฟอร์มล็อกอิน (อยู่ใน sidebar และกด Enter ได้)
    st.markdown("### เข้าสู่ระบบ")
    if not st.session_state.authed:
        with st.form("login_form", clear_on_submit=False):
            user = st.text_input("Username", key="login_user", placeholder="พิมพ์ชื่อผู้ใช้ได้เลย")
            pwd  = st.text_input("Password", type="password", key="login_pwd", placeholder="ใส่รหัส = 1234")
            ok   = st.form_submit_button("Login", type="primary")
        if ok:
            if pwd.strip() == "1234":
                st.session_state.authed = True
                st.session_state.user = user.strip() or "ผู้ใช้งาน"
                st.success(f"เข้าสู่ระบบสำเร็จ • สวัสดี {st.session_state.user}")
                st.session_state.page = "home"
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง (กำหนดให้เป็น 1234)")
    else:
        st.success(f"ล็อกอินแล้ว • {st.session_state.user}")
        if st.button("Logout", type="secondary", use_container_width=True):
            st.session_state.authed = False
            st.session_state.user = ""
            st.session_state.page = "login"
            st.rerun()

# ================== MAIN CONTENT ==================
st.title("Blood Stock Real-time Monitor")
st.caption(f"อัปเดต: {_now_text()}")

df = load_df()

def page_home():
    st.subheader("ภาพรวม")
    st.info("นี่คือหน้าแสดงผลหลักของระบบ (ตัวอย่าง) — เมนูอยู่ซ้ายมือ, เข้าสู่ระบบเพื่อใช้งานเมนู 'กรอกเลือด'")

    st.markdown("#### ตารางสรุป (ตัวอย่างข้อมูลที่บันทึก)")
    if df.empty:
        st.write("— ยังไม่มีข้อมูลการกรอกเลือด —")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

def page_intake():
    st.subheader("กรอกเลือด (สำหรับเจ้าหน้าที่)")
    if not st.session_state.authed:
        st.warning("โปรดเข้าสู่ระบบก่อนจึงจะสามารถบันทึกข้อมูลได้")
        return

    with st.form("intake_form"):
        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            fid = st.text_input("ID", value="")
            btype = st.selectbox("หมู่เลือด", ["A","B","O","AB"])
        with c2:
            code = st.text_input("รหัส", value="")
            free = st.text_input("ว่าง", value="")
        with c3:
            reserve = st.text_input("จอง", value="")
            sold    = st.text_input("จำหน่าย", value="")
            expire  = st.text_input("หมดอายุ", value="")

        submitted = st.form_submit_button("บันทึกเข้าระบบ", type="primary")
    if submitted:
        new = {
            "ID": fid.strip(),
            "หมู่เลือด": btype,
            "รหัส": code.strip(),
            "ว่าง": free.strip(),
            "จอง": reserve.strip(),
            "จำหน่าย": sold.strip(),
            "หมดอายุ": expire.strip()
        }
        new["ค่าสถานะ"] = derive_status(new)
        df_new = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
        save_df(df_new)
        st.success("บันทึกเรียบร้อย")
        st.rerun()

    st.markdown("#### ตารางสรุปที่บันทึกแล้ว")
    df_now = load_df()
    if df_now.empty:
        st.write("— ยังไม่มีข้อมูล —")
    else:
        st.dataframe(df_now, use_container_width=True, hide_index=True)
        st.caption("หมายเหตุ: ค่าสถานะจะประเมินตามเงื่อนไข ว่าง=เขียว, จอง=เหลือง, จำหน่าย=เทา, หมดอายุ=แดง")

def page_login():
    st.subheader("เข้าสู่ระบบ")
    if st.session_state.authed:
        st.success(f"ล็อกอินแล้ว • {st.session_state.user}")
        st.write("คุณสามารถใช้งานเมนู **กรอกเลือด** ทางซ้ายได้ทันที")
    else:
        st.info("กรอก Username อะไรก็ได้ และรหัสผ่าน **1234** ในแถบซ้ายเพื่อเข้าสู่ระบบ")

# เรนเดอร์ตามหน้า
if st.session_state.page == "home":
    page_home()
elif st.session_state.page == "intake":
    page_intake()
else:
    page_login()
