# Data Axle — Business Intelligence Platform (Neo4j)

Neo4j-native **GraphRAG Business Assistant** with client-isolated vector search, parent-child chunking, async ingestion, Groq streaming LLM, and a Data Axle–themed Next.js UI.

## Architecture

- **Frontend:** Next.js 14, Tailwind CSS, App Router
- **Backend:** Django 5 + Django REST Framework
- **Graph + Vector DB:** Neo4j 5 Community (Docker)
- **Task queue:** Celery + Redis
- **AI orchestration:** LangChain (LCEL RAG chain, custom Neo4j retriever)
- **Embeddings:** Local `BAAI/bge-large-en-v1.5` (1024-dim) via `langchain-huggingface`
- **LLM:** Groq via `langchain-groq` (`ChatGroq`, e.g. `llama-3.1-8b-instant`, streaming)
- **Parsing:** `unstructured` (PDF/DOCX/TXT) with adaptive image OCR · **Tables:** `openpyxl` (XLSX/XLSM), `xlrd` (.xls), stdlib CSV — sheet-aware JSON rows
- **Data dictionary RAG:** Schema-aware table/column/code_set chunks · hybrid vector + Neo4j fulltext (RRF) · multi-hop retrieval · query expansion · `VECTOR_SEARCH_LIMIT=12` (configurable)
- **Chunking:** Parent/child graph; data dictionaries use per-column child chunks (not row batches)

## Quick start (Docker)

1. Copy environment file and set your Groq API key:

```bash
cp .env.example .env
# Edit .env — set GROQ_API_KEY
```

2. **First time** (build images, start stack, init Neo4j schema + sample clients):

```bash
make bootstrap
# or: docker compose build api worker && docker compose up -d
#     make schema && make seed
```

3. **Every day** (reuse images — no rebuild; code is bind-mounted from `./backend`):

```bash
make up
# or: docker compose up -d
```

Rebuild images only when `backend/requirements.txt` or `backend/Dockerfile` change:

```bash
make build
make up
```

Follow logs when needed: `make logs`

> Avoid `docker compose up --build` on every start — the backend image installs PyTorch, spaCy, and a ~1.3GB embedding model; rebuilds are slow on first run and unnecessary for normal Python edits.

4. Start the UI (optional — requires npm registry access during image build):

```bash
make build-ui
make up-ui
# or: docker compose --profile ui build frontend && docker compose --profile ui up -d
```

If the frontend Docker build times out on your network, run the UI on the host instead:

```bash
cd frontend
npm install
npm run dev
```

(API stays at http://localhost:8000, UI at http://localhost:3000.)

Neo4j schema init runs on first bootstrap (`make bootstrap` or `make schema`). Cypher scripts live in `backend/infrastructure/neo4j/` (vector + fulltext indexes). To re-run manually:

```bash
make schema
```

Optional: one-shot init via `.env` instead of `make bootstrap` — set `DOCKER_INIT_NEO4J_SCHEMA=1` and `DOCKER_SEED_CLIENTS=1`, run `docker compose up -d` once, then set both back to `0` for faster restarts.

### Narrative parsing with image OCR (PDF/DOCX)

Narrative files use a **two-phase adaptive parser**:

1. **Fast pass** — `partition_pdf(strategy="fast")` or `partition(auto)` for extractable text (unchanged for text-only documents).
2. **Detection** — embedded images in PDF/DOCX, empty `Image`/`Figure` markers, or low text density (scanned PDFs).
3. **Supplemental OCR** — hi_res image-block OCR for diagrams/flowcharts, or `ocr_only` for scanned pages; DOCX embedded images via Tesseract.

OCR text is merged with the fast pass, deduplicated, and chunked as normal `row` narrative content with `Figure (page N)` section headers.

**Re-ingest** PDF/DOCX files after enabling or upgrading OCR to pick up diagram text. Set `PARSER_IMAGE_OCR_ENABLED=false` in `.env` to disable supplemental OCR.

Optional env (see `.env.example`): `PARSER_MIN_IMAGE_COUNT`, `PARSER_TEXT_DENSITY_MIN`, `PARSER_OCR_LANGUAGES`, `PARSER_MAX_OCR_IMAGES`.

Rebuild Docker images after `requirements.txt` / `Dockerfile` changes (`make build`) — hi_res layout models and Tesseract language packs are installed in the worker image.

### Data dictionary RAG (Excel)

After deploying workbook dictionary RAG (multi-sheet profiles), **re-upload or re-ingest spreadsheets only** (`xlsx`, `xlsm`, `xls`, `csv`) so Neo4j receives workbook chunk types (`database`, `table_definition`, `table_catalog`, `column`, `code_set`, `overview`). PDF/DOCX/TXT already ingested do not need re-ingest unless replaced. Generic row spreadsheets (non-dictionary layout) still use row-based chunking.

**Manual QA (after re-ingest):**

Use any uploaded workbook + narrative document pair (no per-file code changes).

1. **Database metadata** — e.g. “What does the database represent?” (expect DATABASE chunks)
2. **Table purpose** — e.g. “What is the purpose of the Customer table?” (expect TABLE_DEF)
3. **List tables** — e.g. “List 5 tables in the dataset” (expect CATALOG; names only from context)
4. **Column + datatype** — e.g. “What is the definition and datatype of OrderId?” (expect COLUMN)
5. **Code set** — e.g. “What does code value X mean?” (expect CODE_SET)
6. **Mixed client** — upload spreadsheet + docx; ask a project/architecture question (expect ROW from docx)
7. **Cross-doc honesty** — ask how a project phase relates to the spreadsheet; if not linked in uploads, answer should say not documented
8. **Narrative-only client** — upload PDF/DOCX/TXT only; chat still works as before

Verify chunk coverage in Neo4j: `MATCH (cc:ChildChunk {client_id: $id}) RETURN cc.chunk_type, count(*)`.
Re-ingest spreadsheets when `table_catalog`, `table_definition`, or `database` counts are zero (old ingest).

Ops scripts (from repo root via Docker):

- `docker compose exec api python scripts/verify_workbook_chunks.py <client_id>` — chunk counts, catalog parse, ReportTitle rows
- `docker compose exec api python scripts/trace_retrieval.py <client_id> "List 5 tables in the dataset"` — retrieval routing trace
- `docker compose exec api python scripts/diagnose_workbook_ingest.py /path/to/workbook.xlsx` — local chunk dry-run (no Neo4j)

After workbook chunker changes (column dedupe), **re-ingest spreadsheets** so Neo4j matches the new canonical column rows.

Optional env tuning (`.env`):

- `VECTOR_SEARCH_LIMIT=12` (default)
- `HYBRID_SEARCH_ENABLED=true`
- `MULTI_HOP_ENABLED=true`
- `RERANK_ENABLED=true` (optional cross-encoder rerank)

5. Seed sample clients (optional, if you skipped `make bootstrap`):

```bash
make seed
```

6. Open the app:

- Frontend: http://localhost:3000
- API health: http://localhost:8000/api/health/
- Neo4j Browser: http://localhost:7474 (login `neo4j` / password from `.env`)

## Typical workflow

1. **Home → Manage users** — register `@data-axle.com` users and set yourself as the active user
2. Select or create a **client** in the Business Assistant
3. **Upload** documents — wait until status is `ready` (first run downloads the embedding model ~1.3GB)
4. Use **Chat history** (left panel) for multiple threads per user + client; **New** starts a fresh conversation
5. **Chat** — streamed Groq answers with structured markdown (Summary / Details / Sources)

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health/` | Neo4j + Redis health |
| GET/POST | `/api/clients/` | List / create clients |
| GET/POST | `/api/documents/?client_id=` | List / upload documents |
| GET | `/api/documents/{id}/status/` | Ingestion status |
| DELETE | `/api/documents/{id}/` | Delete document + graph chunks |
| PUT | `/api/documents/{id}/` | Re-upload (same document id) |
| GET/POST/PATCH | `/api/users/` | User registry (`@data-axle.com`) |
| GET | `/api/users/search/?q=` | User typeahead search |
| GET/POST | `/api/conversations/?user_id=&client_id=` | List / create chat threads |
| GET | `/api/conversations/{id}/messages/` | Messages for a thread |
| DELETE | `/api/conversations/{id}/` | Delete a thread |
| POST | `/api/chat/` | SSE streaming RAG (`user_id`, `conversation_id`, `client_id`, `message`) |
| GET | `/api/chat/history/?client_id=` | Deprecated — use conversations API |

Phase 2 stubs (`501`): `/api/lineage/ingest/`, `/api/lineage/{table}/`, `/api/lineage/chat/`

## Windows note (local pip, outside Docker)

`requirements.txt` uses `python-magic` (Linux/Docker). On Windows-only local installs, you may also need:

```bash
pip install python-magic-bin
```

## Local development (without full Docker)

Run Neo4j + Redis only:

```bash
docker compose up neo4j redis -d
```

Backend:

```bash
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp ../.env.example ../.env
python manage.py migrate
python manage.py init_neo4j_schema
python manage.py seed_clients
python manage.py runserver
# Separate terminal:
celery -A config worker -l info
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Project structure

```
backend/          Django API, Celery, Neo4j repositories, services/langchain (RAG)
frontend/         Next.js UI (Data Axle theme)
infrastructure/   Neo4j Cypher schema scripts
documentation/    Architecture plans
```

## Testing

```bash
cd backend
pytest -m "not slow"    # fast unit tests
pytest -m slow        # embedding model tests (downloads HF weights)
```

Integration tests require a running Neo4j instance (`NEO4J_URI` in `.env`).

## Configuration

See [`.env.example`](.env.example). Key settings:

- `GROQ_API_KEY` — required for chat
- `EMBEDDING_DIMENSIONS=1024` — must match the local embedding model
- `NEO4J_URI` — use Aura bolt URI for cloud deployments

## Phase 2 hooks

- `apps/lineage/` — stub API (501)
- `infrastructure/neo4j/03_phase2_labels.cypher` — documented SQL lineage schema
- Home UI — SQL Lineage Explorer tile disabled
- `/lineage` page — placeholder

## Security note

Phase 1 has **no authentication**. Restrict network access in production until SSO is added.
