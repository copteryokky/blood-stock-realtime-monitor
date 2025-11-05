# app.py
import os
from datetime import datetime
import pandas as pd
import streamlit as st

# ========= Basic Config =========
st.set_page_config(page_title="Blood Stock Real-time Monitor",
                   page_icon="🩸", layout="wide")

ADMIN_PIN = os.getenv("BLOOD_ADMIN_KEY", "1234")  # เปลี่ยนรหัสผ่านที่นี่

# --------- [Optional] DB hooks ----------
# เติมฟังก์ชันจริงของคุณได้ที่นี่ถ้าต้องการเชื่อม DB
def db_save_entries(df: pd.DataFrame):
    """เขียนบันทึกลงฐานข้อมูลจริงที่นี่ (ถ้าต้องการ)"""
    pass

def db_load_entries() -> pd.DataFrame | None:
    """อ่านบันทึกจากฐานข้อมูลจริงที่นี่ (ถ้าต้องการ)"""
    return None
# ----------------------------------------

# ========= Styles =========
st.markdown("""
<style>
/* ฟอนต์/สีโดยรวม */
h1,h2,h3 { letter-spacing:.2px }
.block-container { padding-top: 0.8rem; }

/* Header bar */
.header-bar {
  display:flex; align-items:center; justify-content:space-between;
  gap:1rem; padding:12px 6px 8px 6px; position:sticky; top:0; background:rgba(255,255,255,.92);
  border-bottom:1px solid #eef2f7; backdrop-filter: blur(8px); z-index:999;
}
.header-left { display:flex; align-items:center; gap:.75rem; }
.header-title { font-size:18px; font-weight:800; color:#0f172a; }
.header-sub { color:#64748b; font-size:12px; margin-top:-2px; }

/* user button (มุมขวาบน) */
.user-btn { border:1px solid #e5e7eb; background:#fff; border-radius:12px; padding:.4rem .6rem; }
.user-btn:hover { background:#f8fafc; }

/* sidebar nav */
.sidebar-title{ font-weight:800; color:#111827; font-size:14px; margin:8px 0 4px 2px; }
.nav-item { padding:8px 10px; border-radius:10px; cursor:pointer; display:flex; gap:.6rem; align-items:center; }
.nav-item:hover { background:#f3f4f6; }
.nav-item.active { background:#e6f0ff; border:1px solid #dbeafe; }
.nav-icon { width:18px; text-align:center; }
.nav-label { font-weight:700 }

/* data editor & dataframe font */
[data-testid="stDataFrame"] table { font-size:14px; }
[data-testid="stDataFrame"] th { font-size:14px; font-weight:700; color:#111827; }

/* status chip */
.chip { display:inline-flex; align-items:center; gap:.4rem; padding:.2rem .55rem; border-radius:999px; font-weight:700; font-size:12px; }
.chip.green { background:#ecfdf5; color:#065f46; }
.chip.yellow{ background:#fffbeb; color:#92400e; }
.chip.gray  { background:#f3f4f6; color:#374151; }
.chip.red   { background:#fef2f2; color:#991b1b; }
</style>
""", unsafe_allow_html=True)

# ========= Session Defaults =========
if "auth" not in st.session_state:
    st.session_state.auth = {"ok": False, "user": None, "show_login": False}

TABLE_COLUMNS = ["ID", "หมู่เลือด", "รหัส", "ว่าง", "จอง", "จำหน่าย", "หมดอายุ", "ค่าสถานะ"]
if "entries" not in st.session_state:
    # ลองโหลดจาก DB ถ้ามี
    loaded = db_load_entries()
    if isinstance(loaded, pd.DataFrame) and all(c in loaded.columns for c in TABLE_COLUMNS):
        st.session_state.entries = loaded[TABLE_COLUMNS].copy()
    else:
        st.session_state.entries = pd.DataFrame(columns=TABLE_COLUMNS)

# ========= Header (โลโก้ + ปุ่มล็อกอิน) =========
with st.container():
    st.markdown(
        """
        <div class="header-bar">
          <div class="header-left">
            <img src="https://upload.wikimedia.org/wikipedia/commons/4/4a/Blood_drop_icon.svg" height="24">
            <div>
              <div class="header-title">Blood Stock Real-time Monitor</div>
              <div class="header-sub">โรงพยาบาลมหาวิทยาลัยพะเยา คณะแพทยศาสตร์</div>
            </div>
          </div>
          <div>
            """,
        unsafe_allow_html=True,
    )

    col_login = st.columns([1])[0]
    if not st.session_state.auth["ok"]:
        if col_login.button("👤 เข้าสู่ระบบ", key="show_login_btn", use_container_width=False):
            st.session_state.auth["show_login"] = True
    else:
        c1, c2 = st.columns([0.72, 0.28])
        with c1:
            st.write(f"👋 ยินดีต้อนรับ **{st.session_state.auth['user']}**")
        with c2:
            if st.button("ออกจากระบบ", use_container_width=True):
                st.session_state.auth = {"ok": False, "user": None, "show_login": False}
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ========= Login Panel (บนสุด) =========
if st.session_state.auth["show_login"] and not st.session_state.auth["ok"]:
    with st.expander("🔒 เข้าสู่ระบบสำหรับเจ้าหน้าที่", expanded=True):
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password", value="")
            s1, s2 = st.columns([1, 4])
            with s1:
                ok = st.form_submit_button("เข้าสู่ระบบ")
            if ok:
                if p.strip() == ADMIN_PIN and len(u.strip()) > 0:
                    st.session_state.auth = {"ok": True, "user": u.strip(), "show_login": False}
                    st.success("เข้าสู่ระบบสำเร็จ")
                    st.rerun()
                else:
                    st.error("รหัสผ่านไม่ถูกต้อง (รหัสปัจจุบันคือ 1234)")

st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# ========= Sidebar Navigation =========
st.sidebar.markdown('<div class="sidebar-title">เมนูนำทาง</div>', unsafe_allow_html=True)
def nav_button(label, key, icon=""):
    active = st.session_state.get("page", "home") == key
    cls = "nav-item active" if active else "nav-item"
    with st.sidebar.container():
        if st.sidebar.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
            st.session_state.page = key
            st.rerun()

if "page" not in st.session_state:
    st.session_state.page = "home"

nav_button("หน้าหลัก", "home", "🏠")
with st.sidebar.expander("ลงข้อมูล", expanded=True):
    if st.sidebar.button("✏️  กรอกเลือด", use_container_width=True):
        st.session_state.page = "entry"
        st.rerun()
nav_button("รายงาน", "report", "📄")

# ========= Helpers =========
def derive_status_row(row: dict) -> str:
    """คืนค่า chip html ตามกฎสี"""
    try:
        w = int(row.get("ว่าง") or 0)
        r = int(row.get("จอง") or 0)
        s = int(row.get("จำหน่าย") or 0)
        e = int(row.get("หมดอายุ") or 0)
    except Exception:
        w = r = s = e = 0

    if e > 0:
        return '<span class="chip red">หมดอายุ</span>'
    if s > 0:
        return '<span class="chip gray">จำหน่าย</span>'
    if r > 0:
        return '<span class="chip yellow">จอง</span>'
    if w > 0:
        return '<span class="chip green">ว่าง</span>'
    return '<span class="chip gray">-</span>'

def enforce_columns(df: pd.DataFrame) -> pd.DataFrame:
    for c in TABLE_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[TABLE_COLUMNS].copy()

# ========= Pages =========
page = st.session_state.page

# ---------- หน้าแรก ----------
if page == "home":
    st.header("หน้าหลัก")
    st.write("พื้นที่นี้ใช้วางลิงก์/ข้อมูลสรุปรวมของระบบ หรือเชื่อมไปยังโมดูลอื่น ๆ ได้ในอนาคต")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("ดูรายงานรวม", use_container_width=True):
            st.session_state.page = "report"; st.rerun()
    with c2:
        if st.button("ไปที่กรอกเลือด", use_container_width=True):
            st.session_state.page = "entry"; st.rerun()
    with c3:
        st.info("เข้าสู่ระบบก่อนเพื่อใช้เมนูกรอกเลือด (ปุ่มมุมขวาบน)")

# ---------- ลงข้อมูล: กรอกเลือด ----------
elif page == "entry":
    st.header("กรอกเลือด")
    if not st.session_state.auth["ok"]:
        st.warning("ต้องเข้าสู่ระบบก่อนจึงจะใช้งานหน้านี้ได้ (กดปุ่มรูปคนมุมขวาบน)")
        st.stop()

    df = enforce_columns(st.session_state.entries)

    # ตั้งค่า default editors
    bp = ["A", "B", "O", "AB"]
    edited = st.data_editor(
        df,
        key="data_editor_blood",
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "ID": st.column_config.TextColumn("ID", help="เลข ID หรือข้อความใด ๆ"),
            "หมู่เลือด": st.column_config.SelectboxColumn("หมู่เลือด", options=bp, required=False),
            "รหัส": st.column_config.TextColumn("รหัส", help="รหัสถุง/บาร์โค้ด หรือข้อความก็ได้"),
            "ว่าง": st.column_config.TextColumn("ว่าง", help="จำนวน (เลข หรือข้อความ)"),
            "จอง": st.column_config.TextColumn("จอง", help="จำนวน (เลข หรือข้อความ)"),
            "จำหน่าย": st.column_config.TextColumn("จำหน่าย", help="จำนวน (เลข หรือข้อความ)"),
            "หมดอายุ": st.column_config.TextColumn("หมดอายุ", help="จำนวน (เลข หรือข้อความ)"),
            "ค่าสถานะ": st.column_config.Column("ค่าสถานะ", help="คำนวณอัตโนมัติ", disabled=True),
        }
    )

    # คำนวณค่าสถานะ (chip HTML)
    edited = enforce_columns(edited)
    edited["ค่าสถานะ"] = edited.apply(lambda r: derive_status_row(r.to_dict()), axis=1)

    # อัปเดต state + (Option) save DB
    st.session_state.entries = edited.copy()
    # db_save_entries(st.session_state.entries)  # เปิดใช้เมื่อเชื่อม DB จริง

    st.markdown("##### ตารางสรุป")
    # โชว์ตารางที่ render HTML ในคอลัมน์ค่าสถานะให้ชัด
    show = edited.copy()
    st.write(
        show.to_html(escape=False, index=False),
        unsafe_allow_html=True
    )

# ---------- รายงาน ----------
elif page == "report":
    st.header("รายงาน")
    df = enforce_columns(st.session_state.entries)
    if df.empty:
        st.info("ยังไม่มีข้อมูล")
    else:
        # รวมตามหมู่เลือด
        agg = (df.assign(
            ว่าง=lambda d: pd.to_numeric(d["ว่าง"], errors="coerce").fillna(0).astype(int),
            จอง=lambda d: pd.to_numeric(d["จอง"], errors="coerce").fillna(0).astype(int),
            จำหน่าย=lambda d: pd.to_numeric(d["จำหน่าย"], errors="coerce").fillna(0).astype(int),
            หมดอายุ=lambda d: pd.to_numeric(d["หมดอายุ"], errors="coerce").fillna(0).astype(int),
        )
        .groupby("หมู่เลือด", dropna=False)[["ว่าง", "จอง", "จำหน่าย", "หมดอายุ"]]
        .sum()
        .reset_index()
        )
        st.dataframe(agg, use_container_width=True, hide_index=True)

        # รวมทั้งหมด
        total = agg[["ว่าง", "จอง", "จำหน่าย", "หมดอายุ"]].sum()
        st.success(f"รวมทั้งหมด — ว่าง: {int(total['ว่าง'])} | จอง: {int(total['จอง'])} | จำหน่าย: {int(total['จำหน่าย'])} | หมดอายุ: {int(total['หมดอายุ'])}")
