# Claude prompt: update Phase 1 architecture document

Use this prompt with Claude (browser or API) when updating the Phase 1 architecture document. Attach the original `Neo4j_Architecture_Plan.docx` from this folder so Claude can align section numbering and wording with the first report.

---

## Prompt (copy everything below this line into Claude)

**Role:** You are a technical architect and technical writer for Data Axle. You are updating the **Phase 1** architecture document for the project **DA-Assistant-Neo** (Business Intelligence Platform with Neo4j GraphRAG).

**Input:** I am attaching the original document: `documentation/phase1/Neo4j_Architecture_Plan.docx` (browser-generated baseline from project start).

**Output:** Produce a **new, comprehensive Phase 1 architecture document** (Word or structured markdown suitable for Word) that:

1. Preserves the intent and professional tone of the original plan.
2. **Explicitly documents every deviation** from the original plan vs what was actually built.
3. Describes the **current end-to-end system** in detail: infrastructure, data model, ingestion, RAG, chat, frontend, APIs, configuration, and operational notes.
4. Uses **diagrams** (architecture, sequence, Neo4j graph, RAG pipeline) where helpful.
5. Includes a **"Changes from original plan"** section (table: Original intent → Current implementation → Rationale).
6. Ends with **Phase 1 success criteria**, **known limitations**, and **Phase 2 hooks** (SQL Lineage).

Do not invent features that are not listed below. If the original doc mentions something we did not build, mark it as "deferred" or "replaced by X."

---

### Project summary (current state)

**Product name:** Data Axle — Business Intelligence Platform (Neo4j GraphRAG Business Assistant)

**Purpose:** Client-isolated document ingestion and RAG chat over enterprise FRDs, Word, PDF, and Excel **data dictionaries**, with grounded answers (Direct answer, Summary, Details, Sources) and streaming LLM responses.

**Phase 1 scope:** Business Assistant only. SQL Lineage Explorer is stubbed (501 / disabled UI).

**Security (Phase 1):** No real authentication/SSO. Users self-register with `@data-axle.com` emails and select "Use as me." Restrict network access in production.

---

### Technology stack (as deployed)

| Layer | Technology |
|--------|------------|
| Frontend | Next.js 14 (App Router), React, Tailwind CSS, TypeScript |
| API | Django 5 + Django REST Framework |
| Graph + vectors | Neo4j 5 Community (Docker), APOC enabled |
| Task queue | Celery + Redis |
| LLM | Groq API via `langchain-groq` (`ChatGroq`, default `llama-3.1-8b-instant`, streaming) |
| Embeddings | Local `BAAI/bge-large-en-v1.5` (1024-dim, cosine) via `langchain-huggingface` |
| Parsing | `unstructured` (PDF, DOCX, TXT); `openpyxl` (XLSX/XLSM); `xlrd` (.xls); stdlib CSV |
| NLP chunking (narrative) | spaCy `en_core_web_sm` + tiktoken budgets |
| Optional rerank | Cross-encoder `ms-marco-MiniLM-L-6-v2` when `RERANK_ENABLED=true` |
| Storage | Local filesystem (`MEDIA_ROOT` / Docker volume); S3 backend code exists |
| Orchestration | LangChain LCEL RAG chain |

---

### Docker Compose services (document each)

1. **neo4j** — ports 7474/7687, volume `neo4j_data`, healthcheck.
2. **redis** — Celery broker/backend.
3. **api** — Django: migrate → `init_neo4j_schema` → `seed_clients` → `runserver:8000`. Mounts backend code, Neo4j Cypher scripts, upload volume.
4. **worker** — Celery worker `--concurrency=1`, HF model cache volume (`hf_cache`), runs `ingest_document` (embedding download ~1.3GB first run).
5. **frontend** (profile `ui`) — Next.js dev on 3000, `NEXT_PUBLIC_API_URL`.

Document startup order, env wiring (`NEO4J_URI`, `REDIS_URL`, `CELERY_BROKER_URL`, `MEDIA_ROOT`, `HF_HOME`), and that schema init runs **01_constraints → 02_vector_index → 03_fulltext_index → 04_migration_conversations**.

---

### Neo4j graph model (document labels, properties, relationships)

**Labels:** `Client`, `Document`, `Chunk`, `ChildChunk`, `User`, `Conversation`, `ChatMessage` (legacy `ChatMessage` may exist from older paths).

**Key relationships:**

- `(Client)-[:OWNS]->(Document)`
- `(Document)-[:HAS_CHUNK]->(Chunk)`
- `(Chunk)-[:NEXT {position}]->(Chunk)` — document order
- `(ChildChunk)-[:PART_OF]->(Chunk)` — parent context for retrieval
- `(User)-[:STARTED]->(Conversation)-[:FOR_CLIENT]->(Client)`
- `(Conversation)-[:HAS_MESSAGE]->(ChatMessage)`

**Document node:** `id`, `filename`, `file_type`, `file_path`, `file_size_bytes`, `status` (`processing` | `ready` | `error`), `error_message`, `uploaded_at`, `updated_at`.

**Chunk (parent):** `id`, `text`, `client_id`, `document_id`, `chunk_index`, `page_number`, `section_header`, `token_count`, plus **dictionary metadata:** `chunk_type` (`table` | `column` | `code_set` | `row`), `sheet_name`, `table_name`, `column_name`, `keywords`.

**ChildChunk (vector + keyword search target):** `id`, `text`, `embedding` (1024), `client_id`, `document_id`, `child_index`, same metadata fields as above.

**Indexes:**

- Vector: `chunk_embeddings` on `ChildChunk.embedding` (cosine, 1024).
- Fulltext: `childChunkSearch` on `text`, `keywords`, `column_name`, `table_name`, `sheet_name`.

**Client isolation:** All retrieval filters `client_id` on `ChildChunk` (and post-filter on vector query in Neo4j 5.x).

---

### Changes from the original architecture plan (must document)

| Area | Original plan (typical / from first doc) | Current implementation |
|------|------------------------------------------|-------------------------|
| Excel chunking | Row-based JSON batches in parent chunks | **Dual path:** generic row batching OR **data-dictionary** table/column/code_set chunks |
| Vector search | Single vector search, small k (~5) | **Hybrid:** vector + fulltext **RRF**, default **k=12**, over-fetch then dedupe |
| Retrieval | One-shot semantic search | **Multi-hop:** tables → columns/code_sets; **query expansion** (rule-based); fallback pass if low recall |
| Metadata | Mostly in chunk text / section_header | **First-class** `chunk_type`, `sheet_name`, `table_name`, `column_name`, `keywords` on nodes |
| Prompts | Single business FRD system prompt | **+ DATA_DICTIONARY_SYSTEM_PROMPT** when client has dictionary chunks |
| File types | XLSX + CSV upload | **Sheet-aware ingest** for XLSX, XLSM, **XLS** (xlrd), **CSV** (dedicated parser, not unstructured) |
| UI account setup | Separate user search band + inline client create on Assistant | **Manage Accounts** modal (Users + Clients tabs); **User picker** in global header; slim client dropdown on Assistant only |
| Conversations | May have been simpler chat history | **Per user + client** `Conversation` threads in Neo4j, SSE returns `conversation_id` |
| Auth | Placeholder | Still placeholder; `User` registry in Neo4j |
| Re-ingest | Not emphasized | **Required** after dictionary RAG upgrade for existing Excel dictionaries |

---

### Ingestion pipeline (step-by-step, document in detail)

1. **Upload** — `POST /api/documents/` with `client_id` + file; validate extension (`pdf`, `docx`, `xlsx`, `xlsm`, `xls`, `csv`, `txt`).
2. **Storage** — save to `{client_id}/{document_id}/{filename}`.
3. **Neo4j Document** — create with `status=processing`.
4. **Celery** — `ingest_document(document_id)` on worker.
5. **Parse** — `parse_document()` router:
   - XLSX/XLSM → `parse_excel` (openpyxl) → `rows_to_sheet_elements`
   - XLS → `parse_xls` (xlrd)
   - CSV → `parse_csv` (single logical sheet)
   - PDF/DOCX/TXT → `unstructured` generic
6. **Detect kind** — `detect_document_kind(elements)` → `data_dictionary` vs `generic_table`.
7. **Chunk:**
   - Dictionary → `DictionaryChunker`: per-table parent + per-column child; Code Sets sheet → `code_set` chunks.
   - Else → `ParentChildChunker`: narrative sentence split OR row batching by token budget.
8. **Embed** — `embed_texts()` on all child texts (BGE with query prompt on search side).
9. **Write graph** — `IngestionRepository.write_chunks()`; clear old chunks on re-ingest.
10. **Status** — `ready` or `error` with `error_message`.

Include element taxonomy: `SheetTitle`, `TableHeader`, `TableRow` (JSON rows with sheet + headers).

---

### RAG / chat pipeline (step-by-step, document in detail)

1. **Frontend** — `POST /api/chat/` SSE with `client_id`, `user_id`, `message`, optional `conversation_id`.
2. **Persist user message** — Neo4j `Conversation` + `ChatMessage`.
3. **Retrieve** (`retrieve_and_fit_context`):
   - If `MULTI_HOP_ENABLED`: `expand_query()` → hop1 table chunks → hop2 column/code_set (filter by table names) → RRF merge → fallback if fewer than 3 chunks.
   - Else: `hybrid_search()` per query.
   - **Hybrid:** vector query on `ChildChunk` + fulltext `childChunkSearch` → **RRF** (`RRF_K=60`) → dedupe by document/table/column → optional **cross-encoder rerank**.
4. **Token budget** — `fit_chunks_to_token_budget()`; prioritize column/code_set over table summaries; respect Groq TPM (~5500 request tokens).
5. **Context format** — labeled blocks: `[n] COLUMN | Table X | Sheet Y | file.pdf` + child text (`Table: … | Column: … | Definition: …`).
6. **LLM** — `DATA_DICTIONARY_SYSTEM_PROMPT` or `SYSTEM_PROMPT`; stream tokens via LangChain.
7. **Persist assistant message** + **sources** (chunk ids, section headers, document filenames).
8. **SSE events** — `conversation_id`, `token`, `done` + sources.

Note: **Conversation history is stored but not injected into the LLM prompt** in Phase 1 (only current message + retrieved context).

---

### Frontend features (document each screen and behavior)

**Global shell:** `AppShell` + `TopHeader` (Hamburger nav, Manage Accounts, Feedback placeholder, **UserPickerTrigger** with search dropdown).

**Home (`/`):** Hero, metric placeholders, feature tiles (Business Assistant active; SQL Lineage + Reserved disabled), **Manage Accounts** button, Open Assistant link.

**Manage Accounts modal:** Tabs — **Manage Users** (register `@data-axle.com`, filter, Use as me) | **Add & Manage Clients** (create client, select active client).

**Assistant (`/assistant`):** Three columns:

- Left: **Chat history** (conversations per user+client, new/delete/select).
- Center: Slim **client dropdown** only; **MessageThread** + **InputBar** (attach file); gated until `clientId` + `userId` set.
- Right: **Document Manager** — UploadZone (drag/drop), DocumentList, status polling every 5s while `processing`.

**Contexts:** `UserContext` (`localStorage` user id), `ClientContext` (`localStorage` client id).

**Lineage (`/lineage`):** Placeholder for Phase 2.

**Accepted uploads:** PDF, DOCX, TXT, XLSX, XLSM, XLS, CSV (see `frontend/src/lib/acceptedFileTypes.ts`).

---

### API catalog (include full table)

Document all endpoints from README:

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
| POST | `/api/chat/` | SSE streaming RAG |
| GET | `/api/chat/history/?client_id=` | Deprecated — use conversations API |

Phase 2 stubs (`501`): `/api/lineage/ingest/`, `/api/lineage/{table}/`, `/api/lineage/chat/`

---

### Configuration reference

Document `.env` keys:

- `GROQ_API_KEY`, `GROQ_MODEL`, `LLM_MAX_COMPLETION_TOKENS`, `LLM_MAX_REQUEST_TOKENS`, `LLM_TEMPERATURE`
- `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `RERANK_ENABLED`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
- `VECTOR_SEARCH_LIMIT` (default 12), `HYBRID_SEARCH_ENABLED`, `MULTI_HOP_ENABLED`, `FULLTEXT_SEARCH_LIMIT`, `RRF_K`
- `PARENT_CHUNK_TOKENS`, `CHILD_CHUNK_TOKENS`
- `REDIS_URL`, `CELERY_BROKER_URL`, `STORAGE_BACKEND`, `MEDIA_ROOT`, `CORS_ALLOWED_ORIGINS`
- `NEXT_PUBLIC_API_URL`

---

### Repository / code layout (for architects)

```
backend/apps/          clients, documents, chat, users, conversations, lineage (stub), core
backend/services/      parsing, chunking, graphrag (hybrid, multi_hop, query_expansion), langchain, embedding, neo4j/repositories, storage
frontend/src/          app (page, assistant, lineage), components (accounts, chat, documents, layout, users), context, lib (api, sse)
infrastructure/neo4j/  Cypher scripts 01-05
documentation/phase1/  Architecture plans and this prompt
```

Key backend modules:

- `services/parsing/` — `router`, `excel_parser`, `csv_parser`, `xls_parser`, `table_rows`, `dictionary_detect`, `parser` (unstructured)
- `services/chunking/` — `parent_child`, `dictionary_chunker`
- `services/graphrag/` — `hybrid_retriever`, `multi_hop`, `query_expansion`, `query_signals`, `retriever`
- `services/langchain/` — `streaming`, `rag_chain`, `prompts`, `retriever`, `embeddings`
- `apps/documents/tasks.py` — Celery ingest orchestration

---

### Operations and troubleshooting

- First ingest downloads embedding model (worker memory/time, ~1.3GB).
- Re-ingest Excel dictionaries after RAG metadata upgrade so `chunk_type`, `table_name`, `column_name`, and fulltext `keywords` exist on nodes.
- Neo4j warning on `error_message` property: documents use empty string on create to avoid schema warnings; harmless if warning still appears on legacy nodes.
- Groq free tier TPM limits; context trimming via `fit_chunks_to_token_budget`.
- Commands: `make schema`, `make seed`; `pytest -m "not slow"` for unit tests.

---

### Phase 2 (document as future, not Phase 1)

- `apps/lineage/`, disabled home tile, `/lineage` page, 501 APIs.
- `infrastructure/neo4j/03_phase2_labels.cypher` (if present) for SQL lineage schema.

---

### Document structure you should produce

1. Executive summary
2. Goals and non-goals (Phase 1)
3. **Delta from original Neo4j Architecture Plan** (table + narrative)
4. System context diagram
5. Deployment architecture (Docker)
6. Neo4j data model (ER-style + relationship list)
7. Ingestion flow (sequence diagram)
8. Parsing and chunking strategies (narrative vs table vs **data dictionary**)
9. RAG retrieval architecture (hybrid, multi-hop, expansion, rerank, token budget)
10. Chat and conversation model
11. Frontend UX architecture
12. API reference summary
13. Configuration and environment
14. Testing strategy
15. Limitations, risks, re-ingest requirements
16. Phase 2 outlook
17. Appendix: example chunk text formats (column chunk, code_set chunk, table parent)

**Style:** Professional, suitable for internal Data Axle stakeholders; use tables and diagrams; avoid marketing fluff.

---

## How to use

1. Open Claude (browser or project chat).
2. Attach `Neo4j_Architecture_Plan.docx` from this folder.
3. Optionally attach repo `README.md` as a secondary source.
4. Paste the prompt section above (from **Role:** through **Style:**).
5. Ask for output as `.docx` matching the tone/structure of the original plan.

---

*Generated for DA-Assistant-Neo — reflects implementation as of Phase 1 RAG dictionary improvements and UI consolidation.*
