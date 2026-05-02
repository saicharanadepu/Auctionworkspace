import streamlit as st
import pandas as pd
import sqlite3
import json
import hashlib
from datetime import datetime
import re

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
# SESSION
# =========================
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "sel" not in st.session_state:
    st.session_state.sel = {}

# =========================
# SAFE DATAFRAME FIX (🔥 NEW CRITICAL FIX)
# =========================
def safe_dataframe(df):

    df = df.copy()

    # remove duplicate columns (CRITICAL FOR STREAMLIT)
    df = df.loc[:, ~df.columns.duplicated()]

    # convert complex objects (json/list/dict) to string
    for c in df.columns:
        df[c] = df[c].apply(lambda x: str(x) if isinstance(x, (dict, list)) else x)

    df = df.reset_index(drop=True)
    return df

# =========================
# COLUMN NORMALIZATION
# =========================
def normalize_columns(df):

    def clean(col):
        col = str(col).strip().lower()
        col = re.sub(r"[\s_\-]+", "", col)
        return col

    mapping = {
        "driveby": "drive_by",
        "drive_by": "drive_by",
        "drive by": "drive_by",
        "comp": "comp",
        "tax": "tax",
        "bid": "bid",
        "study": "study",
        "notes": "notes"
    }

    rename_map = {}
    for c in df.columns:
        rename_map[c] = mapping.get(clean(c), c)

    return df.rename(columns=rename_map)

# =========================
# CLEAN
# =========================
def clean_df(df):
    df = df.copy().fillna("")
    for c in df.columns:
        df[c] = df[c].astype(str).replace(["None", "nan", "NaN"], "")
    return df

# =========================
# VALIDATION (2+ REQUIRED)
# =========================
def is_valid_row(row):

    cols = ["drive_by", "comp", "tax", "bid"]

    filled = 0
    for c in cols:
        v = str(row.get(c, "")).strip().lower()
        if v not in ["", "none", "nan", "na"]:
            filled += 1

    return filled >= 2

# =========================
# HASH
# =========================
def row_hash(row):
    base = {
        "drive_by": str(row.get("drive_by", "")).strip().lower(),
        "comp": str(row.get("comp", "")).strip().lower(),
        "tax": str(row.get("tax", "")).strip().lower(),
        "bid": str(row.get("bid", "")).strip().lower(),
    }
    return hashlib.md5(json.dumps(base, sort_keys=True).encode()).hexdigest()

# =========================
# COLUMN ORDER
# =========================
def order_columns(df):

    priority = ["drive_by", "comp", "tax", "bid"]

    existing = [c for c in priority if c in df.columns]
    remaining = [c for c in df.columns if c not in existing and c != "select"]

    if "select" in df.columns:
        return ["select"] + existing + remaining
    return existing + remaining

# =========================
# SAFE SELECT COLUMN
# =========================
def add_select_column(df):
    df = df.copy()
    if "select" in df.columns:
        df = df.drop(columns=["select"])
    df.insert(0, "select", False)
    return df

# =========================
# LOAD
# =========================
def load(table):

    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)

    if df.empty:
        return pd.DataFrame()

    df["data"] = df["data"].apply(json.loads)
    out = pd.json_normalize(df["data"])

    out = normalize_columns(out)
    out = clean_df(out)

    out["id"] = df["id"]
    out["created_at"] = df["created_at"]

    out = out[out.apply(is_valid_row, axis=1)]

    return out

# =========================
# SAVE
# =========================
def save_staging(df):
    cursor.execute("DELETE FROM staging")
    conn.commit()

    df = df[df.apply(is_valid_row, axis=1)]

    for _, r in df.iterrows():
        cursor.execute(
            "INSERT INTO staging (data, created_at) VALUES (?,?)",
            (json.dumps(r.to_dict(), default=str), str(datetime.now()))
        )
    conn.commit()

def save_records(df):

    df = df[df.apply(is_valid_row, axis=1)]

    for _, r in df.iterrows():
        cursor.execute(
            "INSERT INTO records (data, created_at) VALUES (?,?)",
            (json.dumps(r.to_dict(), default=str), str(datetime.now()))
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
# DASHBOARD
# =========================
if st.session_state.page == "Dashboard":

    df = load("records")
    st.subheader("Dashboard")

    if not df.empty:
        df = add_select_column(df)
        df = order_columns(df)
        st.dataframe(safe_dataframe(df), use_container_width=True)

# =========================
# UPLOAD
# =========================
elif st.session_state.page == "Upload":

    file = st.file_uploader("Upload Excel", type=["xlsx"])

    if file:

        df = pd.read_excel(file)

        df = normalize_columns(df)
        df = clean_df(df)

        df = df[df.apply(is_valid_row, axis=1)]

        st.success(f"Valid rows: {len(df)}")

        df = add_select_column(df)
        df = order_columns(df)

        st.dataframe(safe_dataframe(df), use_container_width=True)

        if st.button("Send to Approval"):
            save_staging(df.drop(columns=["select"]))
            st.session_state.page = "Approval"
            st.rerun()

# =========================
# APPROVAL
# =========================
elif st.session_state.page == "Approval":

    staging = load("staging")
    records = load("records")

    if staging.empty:
        st.warning("No pending records")
        st.stop()

    staging = staging[staging.apply(is_valid_row, axis=1)]

    existing = set()
    if not records.empty:
        for _, r in records.iterrows():
            existing.add(row_hash(r))

    staging["row_hash"] = staging.apply(row_hash, axis=1)
    staging["is_dup"] = staging["row_hash"].isin(existing)

    new_df = staging[~staging["is_dup"]]
    dup_df = staging[staging["is_dup"]]

    c1, c2, c3 = st.columns(3)
    c1.metric("🆕 New", len(new_df))
    c2.metric("⚠️ Duplicates", len(dup_df))
    c3.metric("📦 Total", len(staging))

    st.subheader("NEW")
    if not new_df.empty:
        new_df = add_select_column(new_df)
        new_df = order_columns(new_df)
        st.dataframe(safe_dataframe(new_df), use_container_width=True)

    st.subheader("DUPLICATES")
    if not dup_df.empty:
        dup_df = add_select_column(dup_df)
        dup_df = order_columns(dup_df)
        st.dataframe(safe_dataframe(dup_df), use_container_width=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Submit", use_container_width=True):
            save_records(staging)
            delete_staging(staging["id"].tolist())
            st.rerun()

    with col2:
        if st.button("Reject", use_container_width=True):
            delete_staging(staging["id"].tolist())
            st.rerun()

    with col3:
        if st.button("Reset", use_container_width=True):
            st.session_state.sel = {}
            st.rerun()

# =========================
# SEARCH
# =========================
elif st.session_state.page == "Search":

    df = load("records")
    st.subheader("Search")

    q = st.text_input("Search")

    if q and not df.empty:
        df = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False, na=False)).any(axis=1)]

    df = add_select_column(df)
    df = order_columns(df)

    st.dataframe(safe_dataframe(df), use_container_width=True)

# =========================
# ADMIN
# =========================
elif st.session_state.page == "Admin":

    st.subheader("Admin")

    if st.button("Delete ALL Records"):
        cursor.execute("DELETE FROM records")
        conn.commit()
        st.rerun()

# =========================
# TRANSFORMER
# =========================
elif st.session_state.page == "Transformer":

    st.subheader("Transformer")

    file = st.file_uploader("Upload Excel", type=["xlsx"])

    if file:
        df = pd.read_excel(file)
        df = st.data_editor(df, use_container_width=True)

        st.download_button("Download CSV", df.to_csv(index=False), "file.csv")
