# import streamlit as st
# import pandas as pd
# import sqlite3
# import json
# from datetime import datetime
# from io import BytesIO

# # =========================
# # CONFIG
# # =========================
# st.set_page_config(page_title="Real Estate OS", layout="wide")

# # =========================
# # DB
# # =========================
# conn = sqlite3.connect("data.db", check_same_thread=False)
# cursor = conn.cursor()

# cursor.execute("""
# CREATE TABLE IF NOT EXISTS records (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     data TEXT,
#     created_at TEXT
# )
# """)

# cursor.execute("""
# CREATE TABLE IF NOT EXISTS staging (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     data TEXT,
#     created_at TEXT
# )
# """)

# conn.commit()

# # =========================
# # FULL COLUMN SET (YOUR REQUEST)
# # =========================
# COLUMNS = [
#     "Street_Number","Address","City","City_Name","Zip","Volume","Page",
#     "Loan_Month","Loan_Year","Legal_Description_1",
#     "Mortgagor_First_Name","Mortgagor_Last_Name",
#     "Study","Notes","Drive_By","Comp","Bid","Tax",
#     "Original_Loan_Amount","Est_Unpaid_Bal","Assessed_Value",
#     "Property_Sq_Footage","Year_Of_Construction","Class",
#     "Loan_Type","Trustee","Auction_Sale_Time"
# ]

# # =========================
# # HELPERS
# # =========================
# def clean(df):
#     df = df.copy()
#     df.columns = df.columns.astype(str).str.strip().str.replace(" ", "_")
#     df = df.fillna("")
#     return df

# def to_json(row):
#     return json.dumps(row.to_dict(), default=str)

# def load(table):
#     df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
#     if df.empty:
#         return pd.DataFrame()

#     data = df["data"].apply(json.loads)
#     out = pd.json_normalize(data)
#     out["id"] = df["id"]
#     return out

# def save_to_staging(df):
#     for _, r in df.iterrows():
#         cursor.execute(
#             "INSERT INTO staging (data, created_at) VALUES (?,?)",
#             (to_json(r), str(datetime.now()))
#         )
#     conn.commit()

# def save_to_records(df):
#     for _, r in df.iterrows():
#         cursor.execute(
#             "INSERT INTO records (data, created_at) VALUES (?,?)",
#             (to_json(r), str(datetime.now()))
#         )
#     conn.commit()

# def delete_staging(ids):
#     cursor.executemany("DELETE FROM staging WHERE id=?", [(i,) for i in ids])
#     conn.commit()

# # =========================
# # SESSION STATE
# # =========================
# if "page" not in st.session_state:
#     st.session_state.page = "Dashboard"

# if "new_select_all" not in st.session_state:
#     st.session_state.new_select_all = False

# if "dup_select_all" not in st.session_state:
#     st.session_state.dup_select_all = False

# if "upload_key" not in st.session_state:
#     st.session_state.upload_key = 0

# # =========================
# # NAV
# # =========================
# st.title("🏡 Auction WorkSpace")

# c1, c2, c3, c4, c5, c6 = st.columns(6)

# if c1.button("Dashboard"): st.session_state.page = "Dashboard"
# if c2.button("Upload"): st.session_state.page = "Upload"
# if c3.button("Approval"): st.session_state.page = "Approval"
# if c4.button("Search"): st.session_state.page = "Search"
# if c5.button("Admin"): st.session_state.page = "Admin"
# if c6.button("Transformer"): st.session_state.page = "Transformer"

# # =========================
# # DASHBOARD
# # =========================
# if st.session_state.page == "Dashboard":

#     df = load("records")

#     st.subheader("📊 Dashboard")

#     if df.empty:
#         st.warning("No data")
#     else:
#         c1, c2, c3 = st.columns(3)
#         c1.metric("Total Records", len(df))
#         c2.metric("Cities", df.get("City", pd.Series()).nunique())
#         c3.metric("Zip Codes", df.get("Zip", pd.Series()).nunique())

#         st.dataframe(df, use_container_width=True)

# # =========================
# # UPLOAD
# # =========================
# elif st.session_state.page == "Upload":

#     st.subheader("📤 Upload Excel")

#     file = st.file_uploader("Upload", type=["xlsx"], key=st.session_state.upload_key)

#     if file:
#         df = pd.read_excel(file)
#         df = clean(df)

#         # ensure all columns exist
#         for c in COLUMNS:
#             if c not in df.columns:
#                 df[c] = ""

#         df = df[COLUMNS]

#         st.dataframe(df)

#         if st.button("Send to Approval"):
#             save_to_staging(df)
#             st.success("Sent to Approval")
#             st.session_state.page = "Approval"
#             st.rerun()

#     if st.button("Reset Upload"):
#         st.session_state.upload_key += 1
#         st.rerun()

# # =========================
# # APPROVAL (FULL FIXED)
# # =========================
# elif st.session_state.page == "Approval":

#     st.subheader("✅ Approval Center")

#     staging = load("staging")
#     records = load("records")

#     if staging.empty:
#         st.warning("No pending records")
#         st.stop()

#     staging = clean(staging)
#     records = clean(records)

#     # duplicate detection
#     def make_key(df):
#         df = df.copy()
#         return df.astype(str).agg("|".join, axis=1)

#     staging["key"] = make_key(staging)
#     records["key"] = make_key(records) if not records.empty else ""

#     existing = set(records["key"]) if not records.empty else set()
#     staging["is_dup"] = staging["key"].isin(existing)

#     new_df = staging[~staging["is_dup"]].copy()
#     dup_df = staging[staging["is_dup"]].copy()

#     # =========================
#     # METRICS
#     # =========================
#     c1, c2, c3 = st.columns(3)
#     c1.metric("Total", len(staging))
#     c2.metric("New", len(new_df))
#     c3.metric("Duplicates", len(dup_df))

#     st.divider()

#     # =========================
#     # CONTROL BUTTONS (FIXED MISSING FEATURES)
#     # =========================
#     c1, c2, c3, c4 = st.columns(4)

#     if c1.button("☑ Select All New"):
#         st.session_state.new_select_all = True

#     if c2.button("☑ Select All Duplicates"):
#         st.session_state.dup_select_all = True

#     if c3.button("🧹 Clear All Selections"):
#         st.session_state.new_select_all = False
#         st.session_state.dup_select_all = False

#     if c4.button("❌ Reject ALL (Delete Staging)"):
#         cursor.execute("DELETE FROM staging")
#         conn.commit()
#         st.warning("All staging rejected")
#         st.rerun()

#     st.divider()

#     # =========================
#     # TABLE RENDER FUNCTION
#     # =========================
#     def render_table(df, select_all, key_prefix):

#         if df.empty:
#             st.info("No data")
#             return pd.DataFrame()

#         df = df.copy()
#         df.insert(0, "Select", select_all)

#         edited = st.data_editor(
#             df.drop(columns=["key","is_dup"], errors="ignore"),
#             use_container_width=True,
#             hide_index=True,
#             key=key_prefix
#         )

#         return edited[edited["Select"] == True]

#     st.markdown("### 🆕 New Records")
#     new_selected = render_table(new_df, st.session_state.new_select_all, "new_table")

#     st.markdown("### 🔁 Duplicate Records")
#     dup_selected = render_table(dup_df, st.session_state.dup_select_all, "dup_table")

#     st.divider()

#     # =========================
#     # ACTIONS
#     # =========================
#     c1, c2 = st.columns(2)

#     if c1.button("✅ Approve Selected"):

#         final = pd.concat([new_selected, dup_selected], ignore_index=True)

#         if final.empty:
#             st.warning("No selection")
#             st.stop()

#         final = final.drop(columns=["key","is_dup","Select"], errors="ignore")

#         save_to_records(final)
#         delete_staging(final["id"].tolist() if "id" in final else [])

#         st.success(f"Approved {len(final)} records")
#         st.rerun()

#     if c2.button("❌ Reject Selected"):

#         selected_ids = pd.concat([new_selected, dup_selected]).get("id", pd.Series()).tolist()

#         delete_staging(selected_ids)

#         st.warning("Rejected selected records")
#         st.rerun()

# # =========================
# # SEARCH
# # =========================
# elif st.session_state.page == "Search":

#     st.subheader("🔍 Search")

#     df = load("records")

#     if df.empty:
#         st.warning("No data")
#         st.stop()

#     q = st.text_input("Search anything")

#     if q:
#         df = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)]

#     st.dataframe(df, use_container_width=True)

# # =========================
# # ADMIN
# # =========================
# elif st.session_state.page == "Admin":

#     st.subheader("⚙️ Admin")

#     df = load("records")
#     st.dataframe(df, use_container_width=True)

#     if st.button("DELETE ALL DATA"):
#         cursor.execute("DELETE FROM records")
#         conn.commit()
#         st.warning("Deleted all records")
#         st.rerun()

# # =========================
# # TRANSFORMER
# # =========================
# elif st.session_state.page == "Transformer":

#     st.subheader("🧪 Transformer")

#     file = st.file_uploader("Upload Excel", type=["xlsx"])

#     if file:
#         df = pd.read_excel(file)
#         df = clean(df)

#         for c in COLUMNS:
#             if c not in df.columns:
#                 df[c] = ""

#         df = df[COLUMNS]

#         st.session_state.transform_df = df

#     if st.session_state.transform_df is not None:

#         df = st.session_state.transform_df

#         df = st.data_editor(df, use_container_width=True, num_rows="dynamic")

#         st.session_state.transform_df = df

#         st.download_button("CSV", df.to_csv(index=False).encode(), "file.csv")

#         buffer = BytesIO()
#         with pd.ExcelWriter(buffer, engine="openpyxl") as w:
#             df.to_excel(w, index=False)

#         st.download_button("Excel", buffer.getvalue(), "file.xlsx")

import streamlit as st
import pandas as pd
import sqlite3
import json
from datetime import datetime
from io import BytesIO

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Auction WorkSpace", layout="wide")

# =========================
# DB CONNECTION
# =========================
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

# =========================
# SAFE MIGRATION (IMPORTANT FIX)
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT,
    dedupe_key TEXT,
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

# Ensure dedupe_key exists (prevents your crash)
cursor.execute("PRAGMA table_info(records)")
cols = [c[1] for c in cursor.fetchall()]

if "dedupe_key" not in cols:
    cursor.execute("ALTER TABLE records ADD COLUMN dedupe_key TEXT")

# Create index safely AFTER column exists
cursor.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS idx_dedupe_key
ON records(dedupe_key)
""")

conn.commit()

# =========================
# COLUMNS
# =========================
COLUMNS = [
    "Street_Number","Address","City","City_Name","Zip","Volume","Page",
    "Loan_Month","Loan_Year","Legal_Description_1",
    "Mortgagor_First_Name","Mortgagor_Last_Name",
    "Study","Notes","Drive_By","Comp","Bid","Tax",
    "Original_Loan_Amount","Est_Unpaid_Bal","Assessed_Value",
    "Property_Sq_Footage","Year_Of_Construction","Class",
    "Loan_Type","Trustee","Auction_Sale_Time"
]

# =========================
# HELPERS
# =========================
def clean(df):
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip().str.replace(" ", "_")
    return df.fillna("")

def to_json(row):
    return json.dumps(row.to_dict(), default=str)

def make_key(df):
    return (
        df["Street_Number"].astype(str).str.strip() + "|" +
        df["Address"].astype(str).str.lower().str.strip() + "|" +
        df["Zip"].astype(str).str.strip()
    )

def load(table):
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    if df.empty:
        return pd.DataFrame()

    data = df["data"].apply(json.loads)
    out = pd.json_normalize(data)
    out["id"] = df["id"]
    return out

def save_to_staging(df):
    for _, r in df.iterrows():
        cursor.execute(
            "INSERT INTO staging (data, created_at) VALUES (?,?)",
            (to_json(r), str(datetime.now()))
        )
    conn.commit()

def save_to_records(df):
    for _, r in df.iterrows():

        key = (
            f"{r.get('Street_Number','')}_"
            f"{r.get('Address','')}_"
            f"{r.get('Zip','')}"
        ).lower()

        try:
            cursor.execute(
                "INSERT INTO records (data, dedupe_key, created_at) VALUES (?,?,?)",
                (to_json(r), key, str(datetime.now()))
            )
        except sqlite3.IntegrityError:
            pass  # duplicate ignored safely

    conn.commit()

def delete_staging(ids):
    if not ids:
        return
    cursor.executemany("DELETE FROM staging WHERE id=?", [(i,) for i in ids])
    conn.commit()

# =========================
# SESSION STATE
# =========================
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "new_select_all" not in st.session_state:
    st.session_state.new_select_all = False

if "dup_select_all" not in st.session_state:
    st.session_state.dup_select_all = False

if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0

if "transform_df" not in st.session_state:
    st.session_state.transform_df = None

# =========================
# NAVIGATION
# =========================
st.title("🏡 Auction WorkSpace")

c1, c2, c3, c4, c5, c6 = st.columns(6)

if c1.button("Dashboard"): st.session_state.page = "Dashboard"
if c2.button("Upload"): st.session_state.page = "Upload"
if c3.button("Approval"): st.session_state.page = "Approval"
if c4.button("Search"): st.session_state.page = "Search"
if c5.button("Admin"): st.session_state.page = "Admin"
if c6.button("Transformer"): st.session_state.page = "Transformer"

# =========================
# DASHBOARD
# =========================
if st.session_state.page == "Dashboard":

    df = load("records")

    st.subheader("📊 Dashboard")

    if df.empty:
        st.warning("No data")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Records", len(df))
        c2.metric("Cities", df.get("City", pd.Series()).nunique())
        c3.metric("Zip Codes", df.get("Zip", pd.Series()).nunique())

        st.dataframe(df, use_container_width=True)

# =========================
# UPLOAD
# =========================
elif st.session_state.page == "Upload":

    st.subheader("📤 Upload Excel")

    file = st.file_uploader(
        "Upload",
        type=["xlsx"],
        key=st.session_state.upload_key
    )

    if file:
        try:
            # ✅ FORCE SAFE READ (fix openpyxl issue)
            df = pd.read_excel(file, engine="openpyxl", dtype=str)

            df = clean(df)

            # ✅ FIX: prevent Streamlit Arrow crash
            df = df.astype(str)

            # ensure all required columns exist
            for c in COLUMNS:
                if c not in df.columns:
                    df[c] = ""

            df = df[COLUMNS]

            # ✅ FIX: ensure no float Zip / mixed types crash
            if "Zip" in df.columns:
                df["Zip"] = df["Zip"].astype(str)

            st.dataframe(df, use_container_width=True)

            if st.button("Send to Approval"):
                save_to_staging(df)
                st.success("Sent to Approval")
                st.session_state.page = "Approval"
                st.rerun()

        except Exception as e:
            st.error(f"❌ Upload failed: {e}")

    if st.button("Reset Upload"):
        st.session_state.upload_key += 1
        st.rerun()
# =========================
# APPROVAL
# =========================
elif st.session_state.page == "Approval":

    st.subheader("✅ Approval Center")

    staging = load("staging")
    records = load("records")

    if staging.empty:
        st.warning("No pending records")
        st.stop()

    staging = clean(staging)
    records = clean(records)

    staging["key"] = make_key(staging)
    records["key"] = make_key(records) if not records.empty else ""

    existing = set(records["key"]) if not records.empty else set()
    staging["is_dup"] = staging["key"].isin(existing)

    new_df = staging[~staging["is_dup"]].copy()
    dup_df = staging[staging["is_dup"]].copy()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total", len(staging))
    c2.metric("New", len(new_df))
    c3.metric("Duplicates", len(dup_df))

    st.divider()

    # CONTROLS
    c1, c2, c3, c4 = st.columns(4)

    if c1.button("☑ Select All New"):
        st.session_state.new_select_all = True

    if c2.button("☑ Select All Duplicates"):
        st.session_state.dup_select_all = True

    if c3.button("🧹 Clear Selections"):
        st.session_state.new_select_all = False
        st.session_state.dup_select_all = False

    if c4.button("❌ Reject ALL"):
        cursor.execute("DELETE FROM staging")
        conn.commit()
        st.warning("All staging cleared")
        st.rerun()

    st.divider()

    def render(df, select_all, key):
        if df.empty:
            st.info("No data")
            return pd.DataFrame()

        df = df.copy()
        df.insert(0, "Select", select_all)

        edited = st.data_editor(
            df.drop(columns=["key","is_dup"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
            key=key
        )

        return edited[edited["Select"] == True]

    st.markdown("### 🆕 New Records")
    new_selected = render(new_df, st.session_state.new_select_all, "new_tbl")

    st.markdown("### 🔁 Duplicates")
    dup_selected = render(dup_df, st.session_state.dup_select_all, "dup_tbl")

    st.divider()

    c1, c2 = st.columns(2)

    if c1.button("✅ Approve Selected"):

        if new_selected.empty:
            st.warning("No new records selected")
            st.stop()

        final = new_selected.drop(columns=["key","is_dup","Select"], errors="ignore")

        save_to_records(final)

        ids = pd.concat([new_selected, dup_selected]).get("id", pd.Series()).tolist()
        delete_staging(ids)

        st.success(f"Approved {len(final)} records (duplicates skipped)")
        st.rerun()

    if c2.button("❌ Reject Selected"):

        ids = pd.concat([new_selected, dup_selected]).get("id", pd.Series()).tolist()
        delete_staging(ids)

        st.warning("Rejected selected records")
        st.rerun()

# =========================
# SEARCH
# =========================
elif st.session_state.page == "Search":

    st.subheader("🔍 Search")

    df = load("records")

    if df.empty:
        st.warning("No data")
        st.stop()

    q = st.text_input("Search")

    if q:
        df = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)]

    st.dataframe(df, use_container_width=True)

# =========================
# ADMIN
# =========================
elif st.session_state.page == "Admin":

    st.subheader("⚙️ Admin")

    df = load("records")
    st.dataframe(df, use_container_width=True)

    if st.button("DELETE ALL DATA"):
        cursor.execute("DELETE FROM records")
        conn.commit()
        st.warning("All deleted")
        st.rerun()

# =========================
# TRANSFORMER
# =========================
elif st.session_state.page == "Transformer":

    st.subheader("🧪 Transformer")

    file = st.file_uploader("Upload Excel", type=["xlsx"])

    if file:
        df = pd.read_excel(file)
        df = clean(df)

        for c in COLUMNS:
            if c not in df.columns:
                df[c] = ""

        df = df[COLUMNS]
        st.session_state.transform_df = df

    if st.session_state.transform_df is not None:

        df = st.session_state.transform_df
        df = st.data_editor(df, use_container_width=True, num_rows="dynamic")

        st.session_state.transform_df = df

        st.download_button("CSV", df.to_csv(index=False).encode(), "file.csv")

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as w:
            df.to_excel(w, index=False)

        st.download_button("Excel", buffer.getvalue(), "file.xlsx")
