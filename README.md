# UBO Charter — Starter Prototype

## What's included
- Streamlit interface
- Upload and text-preview for text-based PDF, DOCX, XLSX/XLS, CSV, TXT, and EML
- Manual ownership-link table
- Basic path-level indirect ownership calculations
- CSV export of path results

## Important limitations
This is a prototype, not a production KYC decisioning system. It does not yet perform AI extraction, OCR for scanned PDFs, consolidate multiple paths, determine legal UBO status, assess control/voting rights, or provide authentication. Always validate results against source documents.

## Run locally
1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run: `pip install -r requirements.txt`
4. Run: `streamlit run app.py`

## Google Colab
Streamlit is designed for persistent app hosting rather than a standard notebook cell. For initial testing, the simplest path is to run locally. If you want to use Colab, run the notebook launcher separately and use a temporary tunnel; do not upload confidential client data to a public tunnel.
