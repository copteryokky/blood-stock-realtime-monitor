import os, time
from datetime import datetime, date, datetime as dt
import pandas as pd
import altair as alt
import streamlit as st
from streamlit.components.v1 import html as st_html

# ===== optional autorefresh =====
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    def st_autorefresh(*args, **kwargs): return None

# ===== DB funcs (ของเดิม) =====
from db import init_db, get_all_status, get_stock_by_blood, adjust_stock

# ============ PAGE / THEME ============
st.set_page_config(page_title="Blood Stock Real-time Monitor", page_icon="🩸", layout="wide")
st.markdown("""
<style>
.block-container{padding-top:1.0rem;}
h1,h2,h3{letter-spacing:.2px}

/* badge legend */
.badge{display:inline-flex;align-items:center;gap:.4rem;padding:.25rem .5rem;border-radius:999px;background:#f3f4f6}
.legend-dot{width:.7rem;height:.7rem;border-radius:999px;display:inline-block}

/* ===== Sidebar ===== */
[data-testid="stSidebar"]{background:#2e343a;}
[data-testid="stSidebar"] .sidebar-title{color:#e5e7eb;font-weight:800;font-size:1.06rem;margin:6px 0 10px 4px}

/* --- User card --- */
[data-testid="stSidebar"] .user-card{
  display:flex; align-items:center; gap:.8rem;
  background:linear-gradient(135deg,#39424a,#2f343a);
  border:1px solid #475569; border-radius:14px; padding:.75rem .9rem; margin:.5rem .2rem 1rem .2rem;
  box-shadow:0 8px 22px rgba(0,0,0,.25);
}
[data-testid="stSidebar"] .user-avatar{
  width:40px; height:40px; border-radius:999px; background:#ef4444; color:#fff; font-weight:900;
  display:flex; align-items:center; justify-content:center; letter-spacing:.5px;
  box-shadow:0 0 0 3px rgba(239,68,68,.25);
}
[data-testid="stSidebar"] .user-meta{display:flex; flex-direction:column; line-height:1.1}
[data-testid="stSidebar"] .user-meta .label{font-size:.75rem; color:#cbd5e1}
[data-testid="stSidebar"] .user-meta .name{font-size:1rem; color:#fff; font-weight:800}

/* ปุ่มเมนู */
[data-testid="stSidebar"] .stButton>button{
  width:100%; background:#ffffff; color:#111827; border:1px solid #cbd5e1;
  border-radius:12px; font-weight:700; justify-content:flex-start;
}
[data-testid="stSidebar"] .stButton>button:hover{background:#f3f4f6}

/* ฟอร์ม LOGIN */
[data-testid="stSidebar"] label{ color:#f3f4f6 !important; font-weight:700; }
[data-testid="stSidebar"] input[type="text"],
[data-testid="stSidebar"] input[type="password"]{
  background:#ffffff !important; color:#111827 !important;
  border:2px solid #e5e7eb !important; border-radius:10px !important; font-weight:600 !important;
  caret-color:#111827 !important;
}
[data-testid="stSidebar"] input::placeholder{ color:#6b7280 !important; opacity:1 !important; }
[data-testid="stSidebar"] input:focus{
  outline:none !important; border-color:#ef4444 !important;
  box-shadow:0 0 0 3px rgba(239,68,68,.25) !important;
}
[data-testid="stSidebar"] button[kind="primary"]{
  width:100%; background:#ef4444 !important; color:#ffffff !important;
  border:none !important; border-radius:10px !important; font-weight:800;
}
[data-testid="stSidebar"] button[kind="primary"]:hover{ filter:brightness(.95); }

/* DataFrame */
[data-testid="stDataFrame"] table {font-size:14px;}
[data-testid="stDataFrame"] th {font-size:14px; font-weight:700; color:#111827;}
</style>
""", unsafe_allow_html=True)

# ============ CONFIG ============
BAG_MAX       = 20
CRITICAL_MAX  = 4
YELLOW_MAX    = 15
AUTH_PASSWORD = "1234"
FLASH_SECONDS = 2.5

# ===== mapping ผลิตภัณฑ์ =====
RENAME_TO_UI    = {"Plasma": "FFP", "Platelets": "PC"}
UI_TO_DB        = {"LPRC":"LPRC","PRC":"PRC","FFP":"Plasma","PC":"Platelets"}
ALL_PRODUCTS_UI = ["LPRC","PRC","FFP","Cryo","PC"]

# ===== สถานะ =====
STATUS_OPTIONS = ["ว่าง","จอง","จำหน่าย","Exp","หลุดจอง"]
STATUS_COLOR   = {
    "ว่าง": "🟢 ว่าง",
    "จอง": "🟠 จอง",
    "จำหน่าย": "⚫ จำหน่าย",
    "Exp": "🔴 Exp",
    "หลุดจอง": "🔵 หลุดจอง",
}

# ============ STATE ============
def _init_state():
    st.session_state.setdefault("logged_in", True)  # เดโม่ให้ใช้งานได้ทันที
    st.session_state.setdefault("username", "staff")
    st.session_state.setdefault("page", "กรอกเลือด")
    st.session_state.setdefault("selected_bt", None)
    st.session_state.setdefault("flash", None)

    cols = ["Exp date","Unit number","Group","Blood Components",
            "Status","ค่าสถานะ","สถานะ(สี)","บันทึก","จองเมื่อ"]
    if "entries" not in st.session_state:
        st.session_state["entries"] = pd.DataFrame(columns=cols)
    else:
        for c in cols:
            if c not in st.session_state["entries"].columns:
                st.session_state["entries"][c] = ""
        st.session_state["entries"] = st.session_state["entries"][cols]
_init_state()

# ============ HELPERS ============
def _safe_rerun():
    try: st.rerun()
    except Exception: st.experimental_rerun()

def compute_bag(total: int, max_cap=BAG_MAX):
    t = max(0, int(total))
    if t <= CRITICAL_MAX: status, label = "red", "วิกฤตใกล้หมด"
    elif t <= YELLOW_MAX: status, label = "yellow", "เพียงพอ"
    else: status, label = "green", "ปกติ"
    pct = max(0, min(100, int(round(100 * min(t, max_cap) / max_cap))))
    return status, label, pct

def bag_color(status: str) -> str:
    return {"green":"#22c55e", "yellow":"#f59e0b", "red":"#ef4444"}[status]

def normalize_products(rows):
    d = {name: 0 for name in ALL_PRODUCTS_UI}
    for r in rows:
        name = str(r.get("product_type","")).strip()
        ui = RENAME_TO_UI.get(name, name)
        if ui in d and ui != "Cryo":
            d[ui] += int(r.get("units",0))
    return d

def get_global_cryo():
    total = 0
    for bt in ["A","B","O","AB"]:
        rows = get_stock_by_blood(bt)
        for r in rows:
            name = str(r.get("product_type","")).strip()
            ui = RENAME_TO_UI.get(name, name)
            if ui != "Cryo":
                total += int(r.get("units",0))
    return total

# ===== SVG ถุง (ขอบสีเลือดหมู) =====
def bag_svg(blood_type: str, total: int) -> str:
    status, _label, pct = compute_bag(total, BAG_MAX)
    fill = bag_color(status)
    letter_fill = {"A":"#facc15","B":"#f472b6","O":"#60a5fa","AB":"#ffffff"}.get(blood_type, "#ffffff")

    inner_h = 148.0; inner_y0 = 40.0
    water_h = inner_h * pct / 100.0
    water_y = inner_y0 + (inner_h - water_h)
    gid = f"g_{blood_type}"
    wave_amp = 5 + 6*(pct/100)
    wave_path = f"M24,{water_y:.1f} Q54,{water_y - wave_amp:.1f} 84,{water_y:.1f} Q114,{water_y + wave_amp:.1f} 144,{water_y:.1f} L144,198 24,198 Z"

    return f"""
<div>
  <style>
    .bag-wrap{{display:flex;flex-direction:column;align-items:center;gap:10px;
               font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial}}
    .bag{{transition:transform .18s ease, filter .18s ease}}
    .bag:hover{{transform:translateY(-2px); filter:drop-shadow(0 10px 22px rgba(0,0,0,.12));}}
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
      </defs>

      <circle cx="84" cy="10" r="7.5" fill="#eef2ff" stroke="#dbe0ea" stroke-width="3"/>
      <rect x="77.5" y="14" width="13" height="8" rx="3" fill="#e5e7eb"/>

      <g>
        <path d="M16,34  C16,18 32,8 52,8 L116,8 C136,8 152,18 152,34
                 L152,176 C152,195 136,206 116,206 L52,206 C32,206 16,195 16,176 Z"
              fill="#ffffff" stroke="#5a0f16" stroke-width="7" opacity=".22"/>
        <path d="M16,34  C16,18 32,8 52,8 L116,8 C136,8 152,18 152,34
                 L152,176 C152,195 136,206 116,206 L52,206 C32,206 16,195 16,176 Z"
              fill="#ffffff" stroke="#800000" stroke-width="3"/>
      </g>

      <g clip-path="url(#clip-{gid})">
        <path d="{wave_path}" fill="url(#liquid-{gid})"/>
      </g>

      <g>
        <rect x="98" y="24" rx="10" ry="10" width="54" height="22" fill="#ffffff" stroke="#e5e7eb"/>
        <text x="125" y="40" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text>
      </g>

      <text x="84" y="126" text-anchor="middle" font-size="32" font-weight="900"
            style="paint-order: stroke fill" stroke="#111827" stroke-width="4"
            fill="{letter_fill}">{blood_type}</text>
    </svg>
  </div>
</div>"""

# ============ INIT DB ============
if not os.path.exists(os.environ.get("BLOOD_DB_PATH", "blood.db")):
    init_db()

# ============ HEADER ============
st.title("Blood Stock Real-time Monitor")
st.caption(f"อัปเดต: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# ===== Utils: diff วัน =====
def days_left(exp_val):
    if pd.isna(exp_val) or exp_val == "":
        return ""
    d = pd.to_datetime(exp_val, errors="coerce")
    if pd.isna(d): return ""
    return (d.date() - date.today()).days

def days_since(ts_str):
    if not ts_str: return None
    try:
        d = pd.to_datetime(ts_str, errors="coerce")
        if pd.isna(d): return None
        return (date.today() - d.date()).days
    except Exception:
        return None

# ===== Auto: จองเกิน 3 วัน => หลุดจอง =====
def apply_auto_unreserve(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for idx, row in df.iterrows():
        status = str(row.get("Status","")).strip()
        booked_at = str(row.get("จองเมื่อ","")).strip()
        if status == "จอง":
            passed = days_since(booked_at)
            if passed is not None and passed > 3:
                df.at[idx, "Status"]   = "หลุดจอง"
    df["ค่าสถานะ"] = df["Status"].astype(str)
    df["สถานะ(สี)"] = df["Status"].map(lambda s: STATUS_COLOR.get(s, s))
    return df

# ===== Normalizers =====
GROUP_SET   = {"A","B","O","AB"}
COMP_SET    = set(ALL_PRODUCTS_UI)
STATUS_SET  = set(STATUS_OPTIONS)

def normalize_status(v:str)->str:
    if not v: return ""
    t = str(v).strip()
    m = {"available":"ว่าง","free":"ว่าง","book":"จอง","reserved":"จอง",
         "sold":"จำหน่าย","exp":"Exp","expired":"Exp","unreserved":"หลุดจอง"}
    t_low = t.lower()
    return m.get(t_low, t)

def normalize_component(v:str)->str:
    if not v: return ""
    t = str(v).strip().upper()
    alias = {"PLASMA":"FFP","PLATELETS":"PC"}
    return alias.get(t, t)

def coerce_date(val):
    if pd.isna(val) or val=="":
        return ""
    try:
        d = pd.to_datetime(val, errors="coerce", dayfirst=False)
        if pd.isna(d):
            d = pd.to_datetime(val, errors="coerce", dayfirst=True)
        if pd.isna(d): return ""
        return d.date().strftime("%Y/%m/%d")
    except Exception:
        return ""

# ============ PAGES ============
st.subheader("กรอกเลือด")

# ---------- ฟอร์มเพิ่มมือ ----------
with st.form("blood_entry_form", clear_on_submit=True):
    c1,c2 = st.columns(2)
    with c1:
        unit_number = st.text_input("Unit number")
    with c2:
        exp_date = st.date_input("Exp date", value=date.today())
    c3,c4 = st.columns(2)
    with c3:
        group = st.selectbox("Group", ["A","B","O","AB"])
    with c4:
        status = st.selectbox("Status", STATUS_OPTIONS, index=0)
    c5,c6 = st.columns(2)
    with c5:
        component = st.selectbox("Blood Components", ["LPRC","PRC","FFP","Cryo","PC"])
    with c6:
        note = st.text_input("บันทึก")
    submitted = st.form_submit_button("บันทึกรายการ", use_container_width=True)

if submitted:
    exp_str = exp_date.strftime("%Y/%m/%d") if isinstance(exp_date, date) else str(exp_date)
    booked_at = dt.now().strftime("%Y-%m-%d %H:%M:%S") if status == "จอง" else ""
    new_row = {
        "Exp date": exp_str,
        "Unit number": unit_number,
        "Group": group,
        "Blood Components": component,
        "Status": status,
        "ค่าสถานะ": status,
        "สถานะ(สี)": STATUS_COLOR.get(status, status),
        "บันทึก": note,
        "จองเมื่อ": booked_at,
    }
    base = st.session_state["entries"].copy()

    # กันซ้ำ: key = (Unit number, Group, Component)
    key = (new_row["Unit number"], new_row["Group"], new_row["Blood Components"])
    if not base.empty:
        mask = (base["Unit number"]==key[0]) & (base["Group"]==key[1]) & (base["Blood Components"]==key[2])
        if mask.any():
            base.loc[mask, list(new_row.keys())] = pd.Series(new_row)
        else:
            base = pd.concat([base, pd.DataFrame([new_row])], ignore_index=True)
    else:
        base = pd.DataFrame([new_row])

    st.session_state["entries"] = apply_auto_unreserve(base)
    st.success("บันทึกรายการแล้ว ✅")

# ---------- อัปโหลด Excel/CSV แบบเสถียร ----------
st.markdown("### นำเข้าจาก Excel/CSV (อัปโหลดแล้วลงตารางอัตโนมัติ)")
up_file = st.file_uploader("เลือกไฟล์ (.xlsx, .xls, .csv)", type=["xlsx","xls","csv"])

mode = st.radio("โหมดนำเข้า", ["รวมกับตาราง (merge/update)", "แทนที่ทั้งหมด (replace)"], horizontal=True)
sheet_name = None
if up_file is not None and up_file.name.lower().endswith((".xlsx",".xls")):
    try:
        xls = pd.ExcelFile(up_file)
        sheet_name = st.selectbox("เลือกชีต", xls.sheet_names, index=0)
    except Exception:
        sheet_name = None

if up_file is not None:
    try:
        if up_file.name.lower().endswith(".csv"):
            raw = pd.read_csv(up_file)
        else:
            raw = pd.read_excel(up_file, sheet_name=sheet_name)

        st.write("**พรีวิวจากไฟล์**", raw.head(10))

        # map columns ไทย/อังกฤษ
        col_map = {
            "exp date":"Exp date","วันที่หมดอายุ":"Exp date","expire date":"Exp date","exp":"Exp date",
            "unit number":"Unit number","รหัสหน่วย":"Unit number","unit":"Unit number",
            "group":"Group","หมู่เลือด":"Group",
            "blood components":"Blood Components","ผลิตภัณฑ์":"Blood Components","component":"Blood Components",
            "status":"Status","สถานะ":"Status",
            "note":"บันทึก","บันทึก":"บันทึก","remark":"บันทึก",
            "bookedat":"จองเมื่อ","จองเมื่อ":"จองเมื่อ","reserved at":"จองเมื่อ"
        }
        ren = {}
        for c in raw.columns:
            k = str(c).strip()
            key = k.lower()
            ren[c] = col_map.get(key, k)
        df = raw.rename(columns=ren)

        # ให้แน่ใจว่ามีคอลัมน์หลัก
        for c in ["Exp date","Unit number","Group","Blood Components","Status","บันทึก","จองเมื่อ"]:
            if c not in df.columns: df[c] = ""

        # ตัดแถวว่างจริง ๆ (ทุกหลักค่าว่าง)
        df = df.loc[~(df[["Exp date","Unit number","Group","Blood Components","Status","บันทึก"]].astype(str).apply(lambda r: "".join(r), axis=1).str.strip()=="")].copy()

        # Normalize
        df["Exp date"] = df["Exp date"].apply(coerce_date)
        df["Group"] = df["Group"].astype(str).str.strip().str.upper()
        df["Blood Components"] = df["Blood Components"].apply(normalize_component)
        df["Status"] = df["Status"].apply(normalize_status)
        df["จองเมื่อ"] = df["จองเมื่อ"].astype(str).str.strip()

        # Validate และรายงาน error
        errors = []
        if not set(df["Group"].unique()) <= GROUP_SET|{""}:
            bad = sorted(set(df["Group"].unique()) - GROUP_SET - {""})
            errors.append(f"Group ไม่ถูกต้อง: {bad}")
        if not set(df["Blood Components"].unique()) <= COMP_SET|{""}:
            bad = sorted(set(df["Blood Components"].unique()) - COMP_SET - {""})
            errors.append(f"Blood Components ไม่ถูกต้อง: {bad}")
        if not set(df["Status"].unique()) <= STATUS_SET|{""}:
            bad = sorted(set(df["Status"].unique()) - STATUS_SET - {""})
            errors.append(f"Status ไม่ถูกต้อง: {bad}")

        if errors:
            st.error("พบข้อผิดพลาดในการตรวจสอบข้อมูล:\n- " + "\n- ".join(errors))
        else:
            # เติมอนุพันธ์ / สี
            df["ค่าสถานะ"] = df["Status"]
            df["สถานะ(สี)"] = df["Status"].map(lambda s: STATUS_COLOR.get(s, s))

            # รวมกับ state
            base = st.session_state["entries"].copy()
            if mode.startswith("แทนที่ทั้งหมด"):
                base = pd.DataFrame(columns=["Exp date","Unit number","Group","Blood Components",
                                             "Status","ค่าสถานะ","สถานะ(สี)","บันทึก","จองเมื่อ"])

            # กันซ้ำด้วย key
            if base.empty:
                merged = df[["Exp date","Unit number","Group","Blood Components",
                             "Status","ค่าสถานะ","สถานะ(สี)","บันทึก","จองเมื่อ"]].copy()
            else:
                key_cols = ["Unit number","Group","Blood Components"]
                base["_key"] = base[key_cols].astype(str).agg("|".join, axis=1)
                df["_key"]   = df[key_cols].astype(str).agg("|".join, axis=1)

                # update ที่ซ้ำ
                update_mask = base["_key"].isin(df["_key"])
                if update_mask.any():
                    to_update = base.loc[update_mask, "_key"].tolist()
                    upd_rows = df.set_index("_key").loc[to_update]
                    base.loc[update_mask, ["Exp date","Unit number","Group","Blood Components",
                                           "Status","ค่าสถานะ","สถานะ(สี)","บันทึก","จองเมื่อ"]] = \
                        upd_rows[["Exp date","Unit number","Group","Blood Components",
                                  "Status","ค่าสถานะ","สถานะ(สี)","บันทึก","จองเมื่อ"]].values

                # append ที่ไม่ซ้ำ
                add_df = df.loc[~df["_key"].isin(base["_key"]), ["Exp date","Unit number","Group","Blood Components",
                                                                 "Status","ค่าสถานะ","สถานะ(สี)","บันทึก","จองเมื่อ"]]
                merged = pd.concat([base.drop(columns=["_key"], errors="ignore"), add_df], ignore_index=True)

            # auto หลุดจอง
            merged = apply_auto_unreserve(merged)
            st.session_state["entries"] = merged
            st.success("นำเข้าข้อมูลสำเร็จ ✅")

    except Exception as e:
        st.error(f"นำเข้าไม่สำเร็จ: {e}")

# ---------- ตารางสรุป ----------
st.markdown("### ตารางสรุป (แก้ไขได้)")
df_vis = st.session_state["entries"].copy()
parsed = pd.to_datetime(df_vis["Exp date"], errors="coerce")
df_vis["Exp date"] = parsed.dt.date
df_vis["วันหมดอายุนับถอยหลัง (วัน)"] = df_vis["Exp date"].apply(lambda d: "" if pd.isna(pd.to_datetime(d)) else (d - date.today()).days)

cols_show = ["Exp date","วันหมดอายุนับถอยหลัง (วัน)",
             "Unit number","Group","Blood Components",
             "Status","ค่าสถานะ","สถานะ(สี)","บันทึก","จองเมื่อ"]
df_vis = df_vis.reindex(columns=cols_show)

col_cfg = {
    "Exp date": st.column_config.DateColumn("Exp date", format="YYYY/MM/DD"),
    "วันหมดอายุนับถอยหลัง (วัน)": st.column_config.NumberColumn("วันหมดอายุนับถอยหลัง (วัน)", disabled=True),
    "Unit number": st.column_config.TextColumn("Unit number"),
    "Group": st.column_config.SelectboxColumn("Group", options=["A","B","O","AB"]),
    "Blood Components": st.column_config.SelectboxColumn("Blood Components", options=ALL_PRODUCTS_UI),
    "Status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS),
    "ค่าสถานะ": st.column_config.TextColumn("ค่าสถานะ", disabled=True),
    "สถานะ(สี)": st.column_config.TextColumn("สถานะ(สี)", disabled=True),
    "บันทึก": st.column_config.TextColumn("บันทึก"),
    "จองเมื่อ": st.column_config.TextColumn("จองเมื่อ", help="เวลาที่เริ่มจอง (ใช้ตรวจเกิน 3 วัน)"),
}

edited = st.data_editor(
    df_vis, num_rows="dynamic", use_container_width=True, hide_index=True, column_config=col_cfg
)

# sync กลับเมื่อแก้ไข + auto หลุดจอง + อัปเดต booked time ถ้าเปลี่ยนเป็น "จอง"
if not edited.equals(df_vis):
    out = edited.copy()

    def _d2str(x):
        if pd.isna(x): return ""
        if isinstance(x, (datetime, pd.Timestamp)): return x.date().strftime("%Y/%m/%d")
        if isinstance(x, date): return x.strftime("%Y/%m/%d")
        try:
            return pd.to_datetime(x, errors="coerce").date().strftime("%Y/%m/%d")
        except Exception:
            return str(x)

    out["Exp date"] = out["Exp date"].apply(_d2str)

    def _set_booked(row):
        stt = str(row.get("Status",""))
        booked = str(row.get("จองเมื่อ","")).strip()
        if stt == "จอง" and booked == "":
            return dt.now().strftime("%Y-%m-%d %H:%M:%S")
        return booked
    out["จองเมื่อ"] = out.apply(_set_booked, axis=1)

    out = apply_auto_unreserve(out)

    st.session_state["entries"] = out[["Exp date","Unit number","Group","Blood Components",
                                       "Status","ค่าสถานะ","สถานะ(สี)","บันทึก","จองเมื่อ"]].reset_index(drop=True)
    st.success("อัปเดตตารางแล้ว ✅")
