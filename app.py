# app.py
import os, io, time
from datetime import datetime, date
import pandas as pd
import streamlit as st

# ========== PAGE ==========
st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")

# ---------- THEME / CSS ----------
st.markdown("""
<style>
.block-container{padding-top:1.0rem;}
h1,h2,h3{letter-spacing:.2px}

/* Side info */
[data-testid="stSidebar"]{background:#2e343a;}
[data-testid="stSidebar"] .sidebar-title{color:#e5e7eb;font-weight:800;font-size:1.06rem;margin:6px 0 10px 4px}
[data-testid="stSidebar"] .stButton>button{width:100%; background:#fff; color:#111827; border:1px solid #cbd5e1; border-radius:12px; font-weight:700; justify-content:flex-start;}
[data-testid="stSidebar"] .stButton>button:hover{background:#f3f4f6}

/* Dataframe font */
[data-testid="stDataFrame"] table {font-size:14px;}
[data-testid="stDataFrame"] th {font-size:14px; font-weight:700; color:#111827;}

/* Badge Pills */
.badge-pill{display:inline-flex;align-items:center;gap:.4rem;padding:.2rem .55rem;border-radius:999px;font-weight:700;font-size:.86rem}
.badge-green{background:#ecfdf5;color:#065f46;border:1px solid #a7f3d0}
.badge-amber{background:#fff7ed;color:#9a3412;border:1px solid #fed7aa}
.badge-red{background:#fef2f2;color:#991b1b;border:1px solid #fecaca}
.badge-blue{background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe}

/* Top alert bar */
.alert-wrap{position:relative;margin:8px 0 12px 0;padding:.6rem .9rem;border-radius:12px;border:1px solid #fecaca;background:#fff1f2}
.alert-title{font-weight:800;color:#991b1b;display:flex;align-items:center;gap:.5rem}
.alert-pills{display:flex;gap:.5rem;margin-top:.3rem;flex-wrap:wrap}
.alert-pill{display:inline-flex;align-items:center;gap:.35rem;padding:.15rem .6rem;border-radius:999px;font-weight:700}
.alert-pill.red{background:#fee2e2;color:#991b1b;border:1px solid #fecaca}
.alert-pill.amber{background:#ffedd5;color:#9a3412;border:1px solid #fed7aa}
</style>
""", unsafe_allow_html=True)

# ---------- STATE ----------
DEFAULT_COLS = ["Created at (YYYY/MM/DD)","Exp date","วันหมดอายุนับถอยหลัง (วัน)","สถานะวันหมดอายุ","Unit number","Group","Blood Components","Status","สถานะ(สี)","บันทึก"]
if "entries" not in st.session_state:
    st.session_state["entries"] = pd.DataFrame(columns=DEFAULT_COLS)

# ---------- HELPERS ----------
def _today_str():
    return date.today().strftime("%Y/%m/%d")

def _to_date(obj):
    """คืนค่า date หรือ None (รับ str/date/pd.Timestamp/na) — ไม่ throw"""
    if obj is None or obj == "":
        return None
    if isinstance(obj, date) and not isinstance(obj, datetime):
        return obj
    if isinstance(obj, datetime):
        return obj.date()
    try:
        d = pd.to_datetime(obj, errors="coerce")
        if pd.isna(d): 
            return None
        return d.date()
    except Exception:
        return None

def days_left(exp_date_val):
    d = _to_date(exp_date_val)
    if d is None:
        return ""
    return (d - date.today()).days

def build_exp_badge(days:int):
    """
    ระดับแจ้งเตือน:
    - days >= 9: ปกติ (เขียว)
    - 5 <= days <= 8: ใกล้ครบกำหนด (ส้ม)
    - days == 4: แดง (ใกล้มาก) — แต่ยังไม่เร่งด่วน
    - 0 <= days <= 3: เร่งด่วน (แดง + ไซเรน)
    - days < 0: หมดอายุ (แดง)
    """
    if isinstance(days,str) or days=="":
        return '<span class="badge-pill badge-blue">ไม่ระบุวัน</span>'

    if days >= 9:
        return '<span class="badge-pill badge-green">ปกติ (เหลือ {} วัน)</span>'.format(days)
    if 5 <= days <= 8:
        return '<span class="badge-pill badge-amber">ใกล้ครบกำหนด (เหลือ {} วัน)</span>'.format(days)
    if days == 4:
        return '<span class="badge-pill badge-red">สีแดง (เหลือ 4 วัน)</span>'
    if 0 <= days <= 3:
        return '<span class="badge-pill badge-red">🚨 เร่งด่วน (เหลือ {} วัน)</span>'.format(days)
    # days < 0
    return '<span class="badge-pill badge-red">หมดอายุ (เกิน {} วัน)</span>'.format(abs(days))

def color_status_text(s: str) -> str:
    """คอลัมน์ 'สถานะ(สี)' ให้โชว์เป็น text/emoji (ไม่ใช้ HTML) เพื่อความนิ่งของ Data Editor"""
    if not s: return "ไม่ระบุ"
    t = s.strip()
    if "ปกติ" in t: return "🟢 ปกติ"
    if "ใกล้ครบกำหนด" in t: return "🟠 ใกล้ครบกำหนด"
    if "เร่งด่วน" in t or "สีแดง (เหลือ 4 วัน)" in t: return "🔴 เร่งด่วน/แดง"
    if "หมดอายุ" in t: return "🔴 หมดอายุ"
    return "🔵 ไม่ระบุ"

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """ทำให้ schema ตรง + คำนวณฟิลด์อนุพันธ์ทั้งหมด"""
    # 1) สร้างคอลัมน์หลักที่หายไป
    need = ["Created at (YYYY/MM/DD)","Exp date","Unit number","Group","Blood Components","Status","บันทึก"]
    for c in need:
        if c not in df.columns:
            df[c] = ""

    # 2) แปลงวันที่ + เติม created
    df["Created at (YYYY/MM/DD)"] = df["Created at (YYYY/MM/DD)"].apply(lambda x: _today_str() if x in ("", None, float("nan")) else \
                                                  (_to_date(x).strftime("%Y/%m/%d") if _to_date(x) else _today_str()))
    # Exp date เก็บแบบ date จริงไว้ใช้คำนวณ แต่ในตารางแสดงเป็น date
    exp_dates = df["Exp date"].apply(_to_date)
    df["Exp date"] = exp_dates.apply(lambda d: d.strftime("%Y/%m/%d") if d else "")

    # 3) Days Left + Badge
    df["วันหมดอายุนับถอยหลัง (วัน)"] = exp_dates.apply(lambda d: "" if d is None else (d - date.today()).days)

    # ค่าบัฟเฟอร์ HTML (เก็บไว้ในคอลัมน์ลับเพื่อ render แยก)
    df["_badge_html"] = df["วันหมดอายุนับถอยหลัง (วัน)"].apply(build_exp_badge)
    df["สถานะวันหมดอายุ"] = df["_badge_html"]  # คอลัมน์โชว์ (ใช้ st.markdown ใน cell)
    df["สถานะ(สี)"] = df["สถานะวันหมดอายุ"].apply(color_status_text)

    # 4) จัดลำดับคอลัมน์
    out = df.reindex(columns=DEFAULT_COLS, fill_value="")
    return out

def render_badge_cell(html: str):
    st.markdown(html, unsafe_allow_html=True)

# ---------- HEADER ----------
st.title("Blood Stock Real-time Monitor")
st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown('<div class="sidebar-title">เมนู</div>', unsafe_allow_html=True)
    st.button("หน้าหลัก", use_container_width=True)
    st.button("กรอกเลือด", use_container_width=True)
    st.button("ออกจากระบบ", use_container_width=True)

# ---------- INPUT FORM (single row quick add) ----------
st.subheader("กรอกเลือด (รายการเดี่ยว)")

c1,c2 = st.columns(2)
with c1:
    unit = st.text_input("Unit number", placeholder="เช่น U251110-001")
with c2:
    exp = st.date_input("Exp date", value=date.today())

c3,c4,c5 = st.columns(3)
with c3:
    group = st.selectbox("Group", ["A","B","O","AB"])
with c4:
    comp = st.selectbox("Blood Components", ["LPRC","PRC","FFP","PC","Cryo"])
with c5:
    status = st.selectbox("Status", ["ว่าง","จอง","จำหน่าย","Exp","หลุดจอง"])
note = st.text_input("บันทึก", placeholder="ระบุหมายเหตุ (ถ้ามี)")

if st.button("บันทึกรายการ", type="primary"):
    new = pd.DataFrame([{
        "Created at (YYYY/MM/DD)": _today_str(),
        "Exp date": exp.strftime("%Y/%m/%d"),
        "Unit number": unit,
        "Group": group,
        "Blood Components": comp,
        "Status": status,
        "บันทึก": note
    }])
    merged = pd.concat([st.session_state["entries"].drop(columns=[c for c in ["_badge_html"] if c in st.session_state["entries"].columns], errors="ignore"), new], ignore_index=True)
    st.session_state["entries"] = normalize_df(merged)
    st.success("บันทึกรายการแล้ว ✅")
    st.experimental_rerun()

# ---------- UPLOAD ----------
st.subheader("นำเข้าจาก Excel/CSV (อัปโหลดแล้วลงตารางอัตโนมัติ)")

uploaded = st.file_uploader("เลือกไฟล์ (.xlsx, .xls, .csv)", type=["xlsx","xls","csv"])
mode = st.radio("โหมดนำเข้า", ["รวมกับตาราง (merge/update)","แทนที่ทั้งหมด (replace)"], horizontal=True)

def _read_upload(file) -> pd.DataFrame:
    if file is None: 
        return pd.DataFrame()
    name = (file.name or "").lower()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(file)
        except Exception as e:
            st.error(f"อ่าน CSV ไม่สำเร็จ: {e}")
            return pd.DataFrame()
    # excel
    try:
        # ใช้ engine อัตโนมัติ ถ้าไม่มี openpyxl/pylxlsb จะ raise -> จับ error
        return pd.read_excel(file)
    except Exception as e:
        st.error("อ่าน Excel ไม่ได้ (อาจขาด openpyxl). แนะนำแก้ requirements.txt เพิ่มบรรทัด `openpyxl` หรืออัปโหลดไฟล์ CSV แทน.")
        st.info(f"รายละเอียดระบบ: {e}")
        return pd.DataFrame()

if uploaded:
    raw = _read_upload(uploaded)
    if not raw.empty:
        raw = raw.copy()
        # normalize คีย์ที่มักใช้กัน ให้ map ง่ายขึ้น
        # รองรับ header สะกดต่างกันเล็กน้อย
        col_map = {
            "created": "Created at (YYYY/MM/DD)",
            "created at": "Created at (YYYY/MM/DD)",
            "created_at": "Created at (YYYY/MM/DD)",
            "exp": "Exp date",
            "exp_date": "Exp date",
            "unit": "Unit number",
            "unit number": "Unit number",
            "group": "Group",
            "blood components": "Blood Components",
            "components": "Blood Components",
            "status": "Status",
            "note": "บันทึก",
            "remark": "บันทึก",
        }
        # map ที่ชื่อเหมือนเป๊ะก็จะคงไว้
        lower_cols = {c.lower():c for c in raw.columns}
        for k,v in col_map.items():
            if k in lower_cols and v not in raw.columns:
                raw.rename(columns={lower_cols[k]: v}, inplace=True)

        imp = raw[[c for c in raw.columns if c in ["Created at (YYYY/MM/DD)","Exp date","Unit number","Group","Blood Components","Status","บันทึก"]]].copy()

        # เติม created ถ้าไม่มี
        if "Created at (YYYY/MM/DD)" not in imp.columns:
            imp["Created at (YYYY/MM/DD)"] = _today_str()
        # normalize & compute
        imp_norm = normalize_df(imp)

        if mode.startswith("รวม"):
            base = st.session_state["entries"].drop(columns=[c for c in ["_badge_html"] if c in st.session_state["entries"].columns], errors="ignore")
            combined = pd.concat([base, imp_norm[base.columns.intersection(imp_norm.columns)].fillna("")], ignore_index=True, sort=False)
        else:
            combined = imp_norm

        # คีย์ซ้ำ ตัดซ้ำ (กำหนดคีย์เป็น Unit number + Exp date)
        if not combined.empty:
            combined["_key"] = combined["Unit number"].astype(str).str.strip() + "||" + combined["Exp date"].astype(str).str.strip()
            combined = combined.drop_duplicates("_key", keep="last").drop(columns=["_key"], errors="ignore")

        st.session_state["entries"] = normalize_df(combined)
        st.success(f"นำเข้า {len(imp_norm)} แถวสำเร็จ ✅")

# ---------- SUMMARY / BANNER ----------
df = st.session_state["entries"].copy()

# นับเร่งด่วน/ส้ม
urgent_cnt = 0
amber_cnt = 0
for txt in df.get("สถานะ(สี)", []):
    s = str(txt)
    if "เร่งด่วน" in s or "แดง" in s and "เหลือ 4 วัน" in s:
        urgent_cnt += 1
    elif "ใกล้ครบกำหนด" in s:
        amber_cnt += 1

st.markdown(f"""
<div class="alert-wrap">
  <div class="alert-title">⚠️ ระบบแจ้งเตือนวันหมดอายุ</div>
  <div class="alert-pills">
    <span class="alert-pill red">เร่งด่วน/แดง: <b>{urgent_cnt}</b></span>
    <span class="alert-pill amber">ใกล้ครบกำหนด: <b>{amber_cnt}</b></span>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------- TABLE (Editable where safe) ----------
st.subheader("ตารางสรุป (แก้ไขได้)")
if df.empty:
    st.info("ยังไม่มีข้อมูล")
else:
    # แสดง badge HTML ในคอลัมน์แยกทางซ้าย (อ่านง่าย)
    # แล้วคอลัมน์ "สถานะวันหมดอายุ" ซึ่งเป็น text จะไม่ editable
    show_cols = ["Created at (YYYY/MM/DD)","Exp date","วันหมดอายุนับถอยหลัง (วัน)",
                 "สถานะวันหมดอายุ","Unit number","Group","Blood Components","Status","สถานะ(สี)","บันทึก"]
    df = df.reindex(columns=show_cols)

    col_cfg = {
        "Created at (YYYY/MM/DD)": st.column_config.DateColumn("Created at (YYYY/MM/DD)", format="YYYY/MM/DD"),
        "Exp date": st.column_config.DateColumn("Exp date", format="YYYY/MM/DD"),
        "วันหมดอายุนับถอยหลัง (วัน)": st.column_config.NumberColumn("วันหมดอายุนับถอยหลัง (วัน)", disabled=True),
        "สถานะวันหมดอายุ": st.column_config.TextColumn("ค่าสถานะ (สี)", disabled=True, help="ค่าสถานะแสดงตามวันหมดอายุ"),
        "Unit number": st.column_config.TextColumn("Unit number"),
        "Group": st.column_config.SelectboxColumn("Group", options=["A","B","O","AB"]),
        "Blood Components": st.column_config.SelectboxColumn("Blood Components", options=["LPRC","PRC","FFP","PC","Cryo"]),
        "Status": st.column_config.SelectboxColumn("Status", options=["ว่าง","จอง","จำหน่าย","Exp","หลุดจอง"]),
        "สถานะ(สี)": st.column_config.TextColumn("สถานะ(สี)", disabled=True),
        "บันทึก": st.column_config.TextColumn("บันทึก"),
    }

    edited = st.data_editor(
        df, num_rows="dynamic", hide_index=True, use_container_width=True, column_config=col_cfg
    )

    # ถ้าแก้ไข -> normalize ใหม่ให้เสถียร
    if not edited.equals(df):
        tmp = edited.copy()

        # แปลงวันที่กลับเป็น string YYYY/MM/DD ให้สม่ำเสมอ
        def _fmt(d):
            dd = _to_date(d)
            return dd.strftime("%Y/%m/%d") if dd else ""
        tmp["Created at (YYYY/MM/DD)"] = tmp["Created at (YYYY/MM/DD)"].apply(_fmt)
        tmp["Exp date"] = tmp["Exp date"].apply(_fmt)

        # สร้าง schema มาตรฐาน + คำนวณอนุพันธ์อีกรอบ
        st.session_state["entries"] = normalize_df(tmp)
        st.success("อัปเดตตารางแล้ว ✅")
        st.experimental_rerun()

# ---------- FOOTER NOTE ----------
st.caption("✅ เสถียรขึ้น: คุมชนิดข้อมูลวันที่, กัน error ตอนนำเข้า, และคำนวณค่าสถานะทุกครั้งหลังแก้ไข/อัปโหลด")

