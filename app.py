import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path

st.set_page_config(page_title="UBO Charter", page_icon="🔎", layout="wide")
st.title("🔎 UBO Charter")
st.caption("Prototype • Upload evidence, map ownership, and calculate ownership percentages.")

st.warning(
    "Prototype only: extracted document text is not automatically verified. "
    "Review every ownership link against source evidence before using any result for KYC/AML decisions."
)

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
            pieces = []
            for sheet in book.sheet_names:
                df = pd.read_excel(book, sheet_name=sheet)
                pieces.append(f"[Sheet: {sheet}]\n{df.to_string(index=False)}")
            return "\n\n".join(pieces)
        if ext == ".csv":
            return pd.read_csv(BytesIO(raw)).to_string(index=False)
        if ext in [".txt", ".eml"]:
            return raw.decode("utf-8", errors="replace")
        return "Unsupported file type."
    except Exception as e:
        return f"Could not extract text: {e}"

st.header("1. Upload company documents")
uploads = st.file_uploader(
    "Select one or more documents",
    type=SUPPORTED,
    accept_multiple_files=True,
    help="Current prototype supports text-based PDF, DOCX, XLSX/XLS, CSV, TXT, and EML. Scanned PDFs and .msg email files need additional handling."
)

if uploads:
    st.success(f"{len(uploads)} document(s) uploaded in this session.")
    for i, file in enumerate(uploads):
        with st.expander(f"{file.name} — extracted text preview", expanded=(i == 0)):
            text = extract_text(file)
            st.text_area(
                "Review extracted text",
                value=text[:30000],
                height=220,
                key=f"preview_{i}"
            )
            st.caption("Preview is limited to the first 30,000 characters.")
else:
    st.info("Upload documents to preview their readable text. Files are processed in this app session; do not use confidential client data in an unsecured deployment.")

st.header("2. Build the ownership chain")
st.write("For this first version, enter verified ownership links manually. Automatic AI extraction will be added after we validate the calculation logic.")

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

def ownership_paths(edges, target_name):
    # Enumerate ownership paths from any owner to target; multiply percentages along each path.
    graph = {}
    for _, row in edges.iterrows():
        owner = str(row.get("Owner / shareholder", "")).strip()
        entity = str(row.get("Owned entity", "")).strip()
        pct = row.get("Direct ownership (%)", 0)
        if not owner or not entity or pd.isna(pct):
            continue
        try:
            pct = float(pct)
        except Exception:
            continue
        if pct < 0 or pct > 100:
            continue
        graph.setdefault(entity, []).append((owner, pct / 100.0))

    results = []
    def walk(entity, product, path, seen):
        for owner, pct in graph.get(entity, []):
            if owner in seen:
                continue
            new_product = product * pct
            new_path = [owner] + path
            results.append((owner, new_product * 100, " → ".join(new_path + [entity])))
            walk(owner, new_product, new_path, seen | {owner})

    walk(target_name, 1.0, [target_name], {target_name})
    return results

if st.button("Calculate ownership", type="primary"):
    if edited.empty:
        st.error("Add at least one ownership link.")
    else:
        invalid = edited[
            edited["Direct ownership (%)"].isna()
            | (edited["Direct ownership (%)"] < 0)
            | (edited["Direct ownership (%)"] > 100)
        ]
        if not invalid.empty:
            st.error("Ownership percentages must be between 0 and 100.")
        else:
            rows = ownership_paths(edited, target.strip())
            if not rows:
                st.warning("No ownership chain to the target was found. Check entity names and the direction of the ownership links.")
            else:
                out = pd.DataFrame(rows, columns=["Owner / shareholder", "Indirect ownership via each path (%)", "Ownership path"])
                out = out.sort_values("Indirect ownership via each path (%)", ascending=False)
                st.subheader(f"Ownership paths to {target}")
                st.dataframe(out, use_container_width=True, hide_index=True)
                st.caption("This prototype lists path-level indirect percentages. It does not yet consolidate multiple paths for the same person, assess control, or determine legal UBO status.")
                csv = out.to_csv(index=False).encode("utf-8")
                st.download_button("Download path results (CSV)", csv, "ubo_charter_ownership_paths.csv", "text/csv")

st.header("3. Planned next features")
st.markdown("""
- AI-assisted extraction of shareholders, entities, and percentages from uploaded documents
- Direct / indirect / consolidated total ownership calculations, including multiple ownership paths
- Ownership chart (individuals → intermediate entities → target company)
- Evidence references by document and page
- Review flags for missing, inconsistent, or conflicting information
- PDF / Excel report export
- Authentication and user-specific access (later phase)
""")
