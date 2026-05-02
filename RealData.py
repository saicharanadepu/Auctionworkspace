import streamlit as st
import pandas as pd
import sqlite3
import json
import hashlib
from datetime import datetime
from io import BytesIO

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Auction WorkSpace", layout="wide")

st.markdown("""
    <style>
        div[data-testid="stMetric"] {
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# =========================
# DB
# =========================
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS staging (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT,
    created_at TEXT
)
""")

conn.commit()

# =========================
# SESSION STATE
# =========================
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "sel" not in st.session_state:
    st.session_state.sel = {}

# =========================
# VALID FIELDS
# =========================
VALID_FIELDS = ["notes", "drive_by", "comp", "bid", "tax"]

# =========================
# CLEAN DATA
# =========================
def clean_df(df):
    df = df.copy()
    df = df.fillna("")
    for c in df.columns:
        df[c] = df[c].astype(str).replace(["None", "nan", "NaN"], "")
    return df

# =========================
# VALIDATION
# =========================
def is_valid_row(row, min_required=2):
    count = 0
    for col in VALID_FIELDS:
        val = str(row.get(col, "")).strip()
        if val not in ["", "None", "nan", "NaN"]:
            count += 1
    return count >= min_required

# =========================
# ROW HASH (CORE FIX FOR DUPLICATES)
# =========================
def row_hash(row):
    base = {k: str(row.get(k, "")).strip() for k in VALID_FIELDS}
    return hashlib.md5(json.dumps(base, sort_keys=True).encode()).hexdigest()

# =========================
# JSON
# =========================
def to_json(row):
    return json.dumps(row.to_dict(), default=str)

# =========================
# LOAD
# =========================
def load(table):
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)

    if df.empty:
        return pd.DataFrame()

    df["data"] = df["data"].apply(json.loads)
    out = pd.json_normalize(df["data"])

    out["id"] = df["id"]
    out["created_at"] = df["created_at"]

    return clean_df(out)

# =========================
# SAVE
# =========================
def save_staging(df):
    cursor.execute("DELETE FROM staging")
    conn.commit()

    for _, r in df.iterrows():
        cursor.execute(
            "INSERT INTO staging (data, created_at) VALUES (?,?)",
            (to_json(r), str(datetime.now()))
        )
    conn.commit()

def save_records(df):
    for _, r in df.iterrows():
        cursor.execute(
            "INSERT INTO records (data, created_at) VALUES (?,?)",
            (to_json(r), str(datetime.now()))
        )
    conn.commit()

def delete_staging(ids):
    if ids:
        cursor.executemany("DELETE FROM staging WHERE id=?", [(i,) for i in ids])
        conn.commit()

# =========================
# NAVIGATION
# =========================
st.title("🏡 Auction WorkSpace")

nav = st.columns(6)
pages = ["Dashboard", "Upload", "Approval", "Search", "Admin", "Transformer"]
icons = ["🏠", "📤", "✅", "🔍", "⚙️", "🧪"]

for i, p in enumerate(pages):
    with nav[i]:
        if st.button(f"{icons[i]} {p}", use_container_width=True):
            st.session_state.page = p

# =========================
# DASHBOARD (FIXED)
# =========================
if st.session_state.page == "Dashboard":

    df = load("records")
    st.subheader("📊 Dashboard")

    if df.empty:
        st.warning("No records found")
    else:
        # remove first 2 columns (id + data artifacts)
        df = df.iloc[:, 2:]

        st.dataframe(df, use_container_width=True)

# =========================
# UPLOAD
# =========================
elif st.session_state.page == "Upload":

    file = st.file_uploader("Upload Excel", type=["xlsx"])

    if file:
        df = pd.read_excel(file)
        df = clean_df(df)

        df = df[df.apply(lambda r: is_valid_row(r, 2), axis=1)]

        st.success(f"Valid rows: {len(df)}")
        st.dataframe(df, use_container_width=True)

        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            if st.button("🚀 Send to Approval", use_container_width=True):
                save_staging(df)
                st.session_state.page = "Approval"
                st.rerun()

# =========================
# APPROVAL (FULL FIXED LOGIC)
# =========================
elif st.session_state.page == "Approval":

    staging = load("staging")
    records = load("records")

    if staging.empty:
        st.warning("No pending data")
        st.stop()

    staging = clean_df(staging)

    # -------------------------
    # DUPLICATE FIX (REAL LOGIC)
    # -------------------------
    staging["row_hash"] = staging.apply(row_hash, axis=1)

    if not records.empty:
        records["row_hash"] = records.apply(row_hash, axis=1)
        existing_hashes = set(records["row_hash"])
    else:
        existing_hashes = set()

    staging["is_dup"] = staging["row_hash"].isin(existing_hashes)

    new_df = staging[~staging["is_dup"]]
    dup_df = staging[staging["is_dup"]]

    for i in staging["row_hash"]:
        st.session_state.sel.setdefault(i, False)

    # =========================
    # METRICS
    # =========================
    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("🆕 New", len(new_df))
    with c2:
        st.metric("⚠️ Duplicates", len(dup_df))
    with c3:
        st.metric("📦 Total", len(staging))

    st.markdown("---")

    # =========================
    # TABLE RENDER (FIXED)
    # =========================
    def render(df, title):

        st.subheader(title)

        if df.empty:
            st.info("No data")
            return

        c1, c2 = st.columns(2)

        with c1:
            if st.button(f"Select All {title}", use_container_width=True):
                for i in df["row_hash"]:
                    st.session_state.sel[i] = True

        with c2:
            if st.button(f"Clear {title}", use_container_width=True):
                for i in df["row_hash"]:
                    st.session_state.sel[i] = False

        df = df.copy()

        # remove UI column
        if "is_dup" in df.columns:
            df = df.drop(columns=["is_dup"])

        # move created_at last
        if "created_at" in df.columns:
            cols = [c for c in df.columns if c != "created_at"]
            cols.append("created_at")
            df = df[cols]

        # checkbox first column
        df.insert(0, "select", df["row_hash"].apply(lambda x: st.session_state.sel.get(x, False)))

        edited = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "select": st.column_config.CheckboxColumn("Select")
            },
            disabled=[col for col in df.columns if col != "select"]
        )

        for _, row in edited.iterrows():
            st.session_state.sel[row["row_hash"]] = bool(row["select"])

    render(new_df, "NEW")
    render(dup_df, "DUPLICATES")

    selected_hashes = [i for i, v in st.session_state.sel.items() if v]
    selected_df = staging[staging["row_hash"].isin(selected_hashes)]

    st.markdown("---")

    # =========================
    # ACTIONS
    # =========================
    b1, b2, b3 = st.columns(3)

    with b1:
        submit = st.button("✅ Submit", use_container_width=True)

    with b2:
        reject = st.button("❌ Reject", use_container_width=True)

    with b3:
        reset = st.button("🔄 Reset", use_container_width=True)

    if submit:
        save_records(selected_df)
        delete_staging(selected_df["id"].tolist())

        for h in selected_hashes:
            st.session_state.sel.pop(h, None)

        st.success(f"Submitted {len(selected_df)} records")
        st.rerun()

    if reject:
        delete_staging(selected_df["id"].tolist())

        for h in selected_hashes:
            st.session_state.sel.pop(h, None)

        st.warning(f"Rejected {len(selected_df)} records")
        st.rerun()

    if reset:
        st.session_state.sel = {}
        st.rerun()

# =========================
# SEARCH
# =========================
elif st.session_state.page == "Search":

    df = load("records")
    st.subheader("🔍 Search")

    q = st.text_input("Search")

    if q and not df.empty:
        df = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False, na=False)).any(axis=1)]

    st.dataframe(df, use_container_width=True)

# =========================
# ADMIN
# =========================
elif st.session_state.page == "Admin":

    st.subheader("⚙️ Admin")

    if st.button("Delete ALL Records", use_container_width=True):
        cursor.execute("DELETE FROM records")
        conn.commit()
        st.success("All records deleted")
        st.rerun()

# =========================
# TRANSFORMER
# =========================
elif st.session_state.page == "Transformer":

    st.subheader("🧪 Transformer")

    file = st.file_uploader("Upload Excel", type=["xlsx"])

    if file:
        df = pd.read_excel(file)
        df = st.data_editor(df, use_container_width=True)

        st.download_button("Download CSV", df.to_csv(index=False), "file.csv")

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as w:
            df.to_excel(w, index=False)

        st.download_button("Download Excel", buffer.getvalue(), "file.xlsx")
