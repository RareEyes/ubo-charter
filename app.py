import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path

st.set_page_config(page_title="UBO Charter", page_icon="🔎", layout="wide")
st.title("🔎 UBO Charter")
st.caption("Prototype • Upload evidence, map ownership, and calculate ownership percentages.")
st.warning("Prototype only. Verify every ownership link against source evidence. This tool does not determine legal UBO status or control.")

SUPPORTED = ["pdf", "docx", "xlsx", "xls", "csv", "txt", "eml"]

def extract_text(uploaded_file):
    ext = Path(uploaded_file.name).suffix.lower()
    raw = uploaded_file.getvalue()
    try:
        if ext == ".pdf":
            import fitz
            doc = fitz.open(stream=raw, filetype="pdf")
            return "\n".join(page.get_text() for page in doc)
        if ext == ".docx":
            from docx import Document
            doc = Document(BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs)
        if ext in [".xlsx", ".xls"]:
            book = pd.ExcelFile(BytesIO(raw))
            return "\n\n".join(
                f"[Sheet: {sheet}]\n{pd.read_excel(BytesIO(raw), sheet_name=sheet).to_string(index=False)}"
                for sheet in book.sheet_names
            )
        if ext == ".csv":
            return pd.read_csv(BytesIO(raw)).to_string(index=False)
        if ext in [".txt", ".eml"]:
            return raw.decode("utf-8", errors="replace")
        return "Unsupported file type."
    except Exception as exc:
        return f"Could not extract text: {exc}"

st.header("1. Upload company documents")
uploads = st.file_uploader(
    "Select one or more documents",
    type=SUPPORTED,
    accept_multiple_files=True
)
if uploads:
    st.success(f"{len(uploads)} document(s) uploaded in this session.")
    for i, uploaded in enumerate(uploads):
        with st.expander(f"{uploaded.name} — extracted text preview", expanded=(i == 0)):
            st.text_area(
                "Review extracted text",
                value=extract_text(uploaded)[:30000],
                height=220,
                key=f"preview_{i}"
            )
else:
    st.info("Use dummy documents while testing. This prototype does not provide production-grade security.")

st.header("2. Build the ownership chain")
st.write("Each row means the owner holds the stated percentage of the owned entity.")
if "owners" not in st.session_state:
    st.session_state.owners = pd.DataFrame([
        {"Owner / shareholder": "Person A", "Owned entity": "Holding Company", "Direct ownership (%)": 60.0, "Evidence / page": "Example only"},
        {"Owner / shareholder": "Holding Company", "Owned entity": "Target Company", "Direct ownership (%)": 40.0, "Evidence / page": "Example only"},
    ])

edited = st.data_editor(
    st.session_state.owners,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Owner / shareholder": st.column_config.TextColumn(required=True),
        "Owned entity": st.column_config.TextColumn(required=True),
        "Direct ownership (%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=0.1, required=True),
        "Evidence / page": st.column_config.TextColumn(),
    },
    key="ownership_editor",
)
st.session_state.owners = edited
target = st.text_input("Target company to analyse", value="Target Company")

def ownership_paths(edges, target_name, max_depth=20):
    # Rows are owner -> owned entity. Traverse backwards from target.
    owners_by_entity = {}
    for _, row in edges.iterrows():
        owner = str(row.get("Owner / shareholder", "")).strip()
        entity = str(row.get("Owned entity", "")).strip()
        pct = row.get("Direct ownership (%)")
        if not owner or not entity or pd.isna(pct):
            continue
        pct = float(pct)
        if 0 <= pct <= 100:
            owners_by_entity.setdefault(entity.casefold(), []).append((owner, pct))

    results = []

    def walk(entity, product, chain, seen, depth):
