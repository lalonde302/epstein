## Epstein DOJ PDFs: download + OCR + semantic search

This repo contains a small CLI to:

- Download **all PDF links** from one (or more) `justice.gov` pages into `data/pdfs/`
- Extract text (and optionally **OCR** scanned PDFs) into `data/text/`
- Embed + index into a local vector DB (`data/chroma/`) for **semantic search**
- (WIP) A web UI (Azure Static Web Apps) in `frontend/` that will eventually expose semantic search

### Quickstart

#### 1) Create a venv + install Python deps

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 2) (Recommended) Install OCR system dependencies (macOS)

These DOJ PDFs are often **image scans**. For reliable extraction, install OCR tooling:

```bash
brew install tesseract ghostscript ocrmypdf
```

If you skip this, the pipeline will still work, but scanned PDFs may yield little/no text.

#### 3) Download PDFs from a DOJ page

```bash
python -m epstein download --url "https://www.justice.gov/..."
```

Optionally pass multiple URLs:

```bash
python -m epstein download --url "https://www.justice.gov/..." --url "https://www.justice.gov/..."
```

#### 4) Extract/OCR + build embeddings index

```bash
python -m epstein ingest --ocr
```

#### 5) Semantic search

```bash
python -m epstein query --q "flight logs to palm beach" --k 8
```

### Data layout

- `data/pdfs/`: downloaded PDFs
- `data/ocr_pdfs/`: OCR’d PDFs (searchable PDFs) if `--ocr`
- `data/text/`: extracted text per PDF (one `.txt` per PDF)
- `data/chroma/`: persistent vector store
- `data/manifests/`: download manifest(s)

### Notes

- This tool only downloads **PDF links present on the page(s)** you pass. If DOJ adds pagination or additional index pages, pass each page URL.
- The embedding model defaults to a small local model (`sentence-transformers/all-MiniLM-L6-v2`) to avoid API keys.

### Web app (Azure Static Web Apps)

- **frontend**: `frontend/` (Vite + React + TypeScript)
- **api**: `api/` (Azure Functions stub with `GET /api/search`)

To run locally (after installing Node deps):

```bash
cd frontend
npm install
npm run dev
```

SWA will be configured to:

- **App location**: `frontend`
- **Api location**: `api`
- **Output location**: `frontend/dist`

