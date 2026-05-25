# Claude prompt — Phase 1 architecture document (v3 as-built)

**How to use:** Attach `documentation/phase1/DA_BI_Platform_Neo4j_Architecture_v2.docx` to Claude. Optionally attach `README.md`. Copy everything below the horizontal rule into Claude.

---

## Prompt (copy from here)

**Role:** You are a technical architect and technical writer for Data Axle. You are producing an **updated Phase 1 as-built architecture document** for **DA-Assistant-Neo** (Business Intelligence Platform — Neo4j GraphRAG Business Assistant).

**Inputs:**

1. **Attached baseline:** `DA_BI_Platform_Neo4j_Architecture_v2.docx` (v2.0 as-built, May 2026). This document already describes deviations from the original v1.0 *planning* doc (`Neo4j_Architecture_Plan.docx`). Treat v2 as the starting point, not the source of truth for implementation details.
2. **Authoritative implementation facts below** (from the live repo as of May 2026). Where v2 disagrees with these facts, **the repo facts win**. Document every gap explicitly in a new section: **"Changes since Architecture v2.0"**.

**Output:** A new comprehensive Phase 1 document (Word `.docx` or structured markdown suitable for Word) that:

- Preserves professional tone and stakeholder readability of v2.
- Includes **three delta layers:** (A) v1 plan → v2 as-built, (B) v2 as-built → current code, (C) consolidated "current as-built" narrative.
- Describes **every step** of ingestion, retrieval, chat/SSE, and frontend UX.
- Uses architecture diagrams, sequence diagrams, Neo4j graph diagram, and RAG routing decision flow where helpful.
- Does **not** invent features not listed below. Mark deferred items clearly.

---

### Project summary

| Item | Value |
|------|--------|
| Product | DA-Assistant-Neo — Data Axle Business Intelligence Platform |
| Phase 1 scope | Business Assistant: upload, async ingest, hybrid GraphRAG chat, conversations, document manager |
| Out of scope | SQL Lineage (stub 501), SSO/auth, conversation history in LLM prompt |
| Security | Self-register `@data-axle.com`, "Use as me"; no passwords; restrict network in prod |

---

### Technology stack (deployed)

| Layer | Technology |
|--------|------------|
| Frontend | Next.js 14 App Router, React, TypeScript, Tailwind |
| API | Django 5 + DRF |
| Graph + vectors | Neo4j 5 Community (Docker), APOC |
| Queue | Celery + Redis |
| LLM | Groq via `langchain-groq` (`ChatGroq`, default `llama-3.1-8b-instant`, streaming) |
| Embeddings | Local `BAAI/bge-large-en-v1.5` (1024-dim, cosine) via `langchain-huggingface` |
| Parsing | `unstructured` (PDF/DOCX/TXT); `openpyxl` (XLSX/XLSM); `xlrd` (.xls); stdlib CSV |
| Narrative chunking | spaCy `en_core_web_sm` + tiktoken budgets |
| Optional rerank | `ms-marco-MiniLM-L-6-v2` when `RERANK_ENABLED=true` (default false) |
| Orchestration | LangChain LCEL: prompt → ChatGroq → StrOutputParser |
| Storage | Local `MEDIA_ROOT` (Docker volume); S3 backend code exists, not configured |

---

### Docker Compose (document each service)

| Service | Role |
|---------|------|
| **neo4j** | `neo4j:5-community` + APOC; ports 7474/7687; volume `neo4j_data`; healthcheck |
| **redis** | Celery broker/backend |
| **api** | Django; entrypoint `docker/api-entrypoint.sh`; `migrate` → optional `init_neo4j_schema` / `seed_clients` via env → `runserver:8000`; bind-mount `./backend`, Cypher at `./infrastructure/neo4j`, uploads volume |
| **worker** | Same image; `celery -A config worker --concurrency=1`; `HF_HOME` / `hf_cache` volume (~1.3GB BGE download on first ingest |
| **frontend** (profile `ui`) | Next.js dev :3000; `NEXT_PUBLIC_API_URL` |

**Env flags for one-shot init:** `DOCKER_RUN_MIGRATE`, `DOCKER_INIT_NEO4J_SCHEMA`, `DOCKER_SEED_CLIENTS` (see README `make bootstrap`).

**Make targets:** `bootstrap`, `up`, `build`, `schema`, `seed`, `build-ui`, `up-ui`, `logs`.

---

### Neo4j schema init (order)

Scripts under `infrastructure/neo4j/` (also mounted in `backend/infrastructure/neo4j/`):

1. `01_constraints.cypher` — uniqueness on Client, Document, ChildChunk, User, Conversation, ChatMessage
2. `02_vector_index.cypher` — HNSW `chunk_embeddings` on `ChildChunk.embedding` (1024, cosine)
3. `03_fulltext_index.cypher` — `childChunkSearch` on text, keywords, column_name, table_name, sheet_name
4. `04_migration_conversations.cypher` — Conversation / ChatMessage graph
5. `05_chunk_metadata.cypher` — chunk metadata indexes/constraints (present in repo; v2 may omit)
6. `03_phase2_labels.cypher` — Phase 2 SQL lineage labels (documented, not active in Phase 1)

**Client isolation:** `client_id` on every `ChildChunk`; vector query over-fetches then post-filters (Neo4j 5 Community, not 2026.01 in-index filter).

---

### Graph model (current)

**Labels:** `Client`, `Document`, `Chunk` (parent), `ChildChunk`, `User`, `Conversation`, `ChatMessage`

**Relationships:**

- `(Client)-[:OWNS]->(Document)`
- `(Document)-[:HAS_CHUNK]->(Chunk)`
- `(Chunk)-[:NEXT {position}]->(Chunk)`
- `(ChildChunk)-[:PART_OF]->(Chunk)`
- `(User)-[:STARTED]->(Conversation)-[:FOR_CLIENT]->(Client)`
- `(Conversation)-[:HAS_MESSAGE]->(ChatMessage)`

**ChildChunk `chunk_type` values (current — important vs v2):**

| Type | Meaning |
|------|---------|
| `database` | Dictionary / DB metadata sheet |
| `table_definition` | Per-table purpose/definition |
| `table_catalog` | Table list / catalog sheet |
| `column` | Per-column field definition (deduped per normalized column name) |
| `code_set` | Permissible values |
| `overview` | Intro / worksheet overview |
| `row` | Narrative or generic table row batches (PDF/DOCX/TXT or non-dictionary Excel) |
| `table` | Legacy dictionary path only (backward compat in old multi_hop) |

v2 doc often says `table|column|code_set|row` only — **update to the table above**.

---

### Changes since Architecture v2.0 (must document — repo wins)

| Area | v2.0 doc says | Current code |
|------|---------------|--------------|
| Excel dictionary chunker | `DictionaryChunker`, `detect_document_kind` → table/column/code_set | **`WorkbookDictionaryChunker`** + **`is_workbook_dictionary()`**; per-**sheet profiles** (`DATABASE`, `TABLE_CATALOG`, `FIELD`→column, `CODE_SET`, `OVERVIEW`, `SKIP`) via `sheet_profiles.py` |
| Chunk types | `table`, `column`, `code_set`, `row` | **`database`, `table_definition`, `table_catalog`, `column`, `code_set`, `overview`, `row`** |
| Column quality | One chunk per column row | **`_dedupe_column_children`**: best chunk per normalized column (prefers Definition + Datatype) |
| Retrieval | Generic `multi_hop_search` table→column | **`workbook_multi_hop_search`**: intent-based (`catalog`, `table`, `database`, `column`, `code`, `general`); **anchor chunks** (`fetch_anchor_chunks`, `pin_anchor_chunks`); catalog **abstain** if no parseable catalog; **synthetic catalog** from distinct `table_definition` table names |
| Mixed clients | Not detailed | **`client_is_mixed`**: workbook + narrative (`row`) chunks; **`mixed_document_search`** with domain split; **`MIXED_SYSTEM_PROMPT`** |
| Query routing | `MULTI_HOP_ENABLED` → multi_hop | **`_retrieve_chunks`** in `streaming.py`: workbook intent, mixed domain, catalog fast-path, narrative-only `hybrid_search(chunk_types=["row"])` |
| Prompts | 2 prompts (FRD + dictionary) | **3 prompts:** `SYSTEM_PROMPT`, `DATA_DICTIONARY_SYSTEM_PROMPT`, **`MIXED_SYSTEM_PROMPT`** |
| Context assembly | Generic labeled blocks | **Catalog:** inject "Allowed table names" prefix; **table intent:** verbatim table definition prefix; **catalog abstain** short-circuit message |
| Token budget | column/code_set > table | **Intent-specific modes:** `workbook_table`, `workbook_database`, `workbook_catalog`, `workbook_column`, `workbook_code`, `narrative`, `mixed`; **`_apply_mixed_slot_reservation`** for row chunks |
| Query signals | Basic expansion | **`parse_query_signals`**: entity table, column name, sheet hint, code-set intent |
| FULLTEXT_SEARCH_LIMIT | 12 in v2 env table | Default **15** in `base.py` |
| Ops scripts | Not in v2 | `scripts/verify_workbook_chunks.py`, `trace_retrieval.py`, `diagnose_workbook_ingest.py` |
| Manual QA | Generic dictionary tests | README **8 workbook QA scenarios** (database, table purpose, list tables, column+datatype, code set, mixed, cross-doc honesty, narrative-only) |

Also retain v2's **v1→v2** deltas (Groq vs OpenAI, BGE 1024 vs 3072, hybrid RRF, Manage Accounts modal, conversations in Neo4j, etc.) — do not drop them.

---

### Ingestion pipeline (every step)

1. **Upload** — `POST /api/documents/` multipart: `file` + `client_id`; extensions: pdf, docx, txt, xlsx, xlsm, xls, csv.
2. **Storage** — `{MEDIA_ROOT}/{client_id}/{document_id}/{filename}` via storage backend.
3. **Neo4j** — `Document` node `status=processing`.
4. **Celery** — `ingest_document(document_id)` on worker (concurrency=1).
5. **Read file** — temp copy from storage.
6. **Parse** — `parse_document(path, file_type)`:
   - XLSX/XLSM → openpyxl → `ParsedElement` rows (`SheetTitle`, `TableHeader`, `TableRow` JSON)
   - XLS → xlrd
   - CSV → single sheet
   - PDF/DOCX/TXT → unstructured
7. **Chunker selection** (spreadsheets only):
   - If `is_workbook_dictionary(elements)` → **`WorkbookDictionaryChunker.chunk()`** (sheet profiles, catalog aggregation, column dedupe)
   - Else → **`ParentChildChunker.chunk_elements()`** (row batches or narrative)
   - Non-spreadsheet → ParentChildChunker (spaCy sentences / narrative)
8. **Embed** — `embed_texts()` on all child texts; BGE query prefix on search side.
9. **Graph write** — `IngestionRepository.clear_document_chunks` then `write_chunks` (parents + children with embeddings and metadata).
10. **Status** — `ready` or `error` + `error_message`.

**Re-ingest:** Required for spreadsheets after workbook chunker/RAG upgrades; PDF/DOCX/TXT only if replaced. PUT re-upload preserves document id.

---

### RAG / chat pipeline (every step)

#### A. Frontend → API

1. User sets **user** (UserContext/localStorage) and **client** (ClientContext).
2. Optional: select/create **Conversation** in left panel.
3. **POST /api/chat/** JSON: `{ client_id, user_id, message, conversation_id? }`.
4. **SSE** (`text/event-stream`): events `conversation_id` → repeated `token` → `done` + `sources`; errors as `{ error }`. Header `X-Conversation-Id` also set.
5. Frontend `lib/sse.ts` parses `data: {...}` lines; `MessageThread` renders streaming markdown.

#### B. API persistence (before LLM)

1. Create conversation if no `conversation_id`.
2. Persist **user** `ChatMessage`.
3. Auto-title conversation from first user message (60 chars).
4. **`retrieve_and_fit_context(client_id, message)`** — retrieval + budget + prompt flags (not streamed yet).

#### C. Retrieval routing (`_retrieve_chunks`)

Decision tree (document as flowchart):

1. `wb_intent = classify_workbook_query(message)` — catalog | table | database | column | code | general.
2. If **catalog** intent AND `client_has_workbook_chunks` → **`workbook_multi_hop_search`** (catalog path).
3. Else if **`client_is_mixed`** (workbook + row chunks):
   - `domain = classify_query_domain(message)` — narrative | workbook | general
   - narrative → `hybrid_search(..., chunk_types=["row"])`
   - workbook or strong workbook intent → `workbook_multi_hop_search`
   - else → **`mixed_document_search`** (RRF narrative + workbook with slot split)
4. Else if `MULTI_HOP_ENABLED` AND workbook chunks → `multi_hop_search` (delegates to workbook path when workbook chunks exist).
5. Else → **`hybrid_search`** (default FRD/narrative clients).

#### D. `workbook_multi_hop_search` (detail)

1. `parse_query_signals` + `expand_query` (rule-based synonyms).
2. `intent = classify_workbook_query`.
3. **`fetch_anchor_chunks`** — must-have chunks (database node, catalog chunk, table_definition for named table, column lookup).
4. **Primary hybrid searches** per expanded query with `chunk_types` from `intent_chunk_types`, optional `table_names`, `column_names`, `sheet_hint` filters.
5. **Secondary hop** — column/code_set chunks filtered by table names from primary (skipped for table/database/catalog/code-only intents per `NO_COLUMN_SECONDARY_INTENTS`).
6. **RRF merge** primary + secondary; fallback if &lt;3 hits.
7. **Rerank** (if enabled) → **`pin_anchor_chunks`** → return.

#### E. `hybrid_search` (detail)

1. Embed query (BGE).
2. Vector: top `VECTOR_SEARCH_LIMIT` on `ChildChunk` with `client_id` post-filter.
3. Fulltext: `childChunkSearch` top `FULLTEXT_SEARCH_LIMIT` (if `HYBRID_SEARCH_ENABLED`).
4. **RRF** with `RRF_K=60`; dedupe by document/table/column; optional cross-encoder rerank.

#### F. Context fit + prompts (`_fit_context`)

1. Select system prompt: dictionary / mixed / FRD via `resolve_use_dictionary_prompt` + `client_is_mixed` + domain.
2. `budget_mode = resolve_budget_mode` (intent-specific).
3. Inject catalog chunk if missing for catalog queries.
4. `fit_chunks_to_token_budget` under `LLM_MAX_REQUEST_TOKENS` (~5500).
5. Catalog abstain if list-tables question but no parseable catalog.
6. Format context: catalog table-name prefix, table-definition verbatim prefix, or standard `_chunk_label` blocks.
7. Stream via LCEL `stream_rag_tokens` with matching `DATA_DICTIONARY_RAG_PROMPT` | `MIXED_RAG_PROMPT` | `RAG_PROMPT`.

#### G. After stream

1. Persist **assistant** message + **sources** (chunk id, section_header, page, document_id, filename).
2. SSE `done` with sources.

**Limitation (unchanged):** Prior conversation messages are **not** in the LLM prompt — only current question + retrieved context.

---

### Frontend (every feature)

| Screen / component | Behavior |
|--------------------|----------|
| **Home `/`** | Hero, metric placeholders, feature tiles (Assistant active; Lineage + Reserved disabled), Manage Accounts, Open Assistant |
| **Manage Accounts modal** | Tabs: Users (register `@data-axle.com`, filter, Use as me) \| Clients (create, select active) |
| **TopHeader** | Nav, Manage Accounts, Feedback placeholder, **UserPickerTrigger** (search `/api/users/search/`) |
| **Assistant `/assistant`** | 3 columns: Chat history (list/new/delete/select conversations) \| Chat (client dropdown, MessageThread, InputBar attach) \| Documents (UploadZone drag-drop, DocumentList, **5s polling** while processing) |
| **Lineage `/lineage`** | Phase 2 placeholder |
| **Contexts** | `UserContext`, `ClientContext` → localStorage |
| **Gating** | Chat/upload disabled until `userId` + `clientId` |

---

### API catalog (complete)

Include all endpoints from README § API endpoints plus Phase 2 stubs (`501`): `/api/lineage/ingest/`, `/api/lineage/{table}/`, `/api/lineage/chat/`.

---

### Configuration reference

Document `.env.example`: Groq, embedding, Neo4j, Redis/Celery, `VECTOR_SEARCH_LIMIT`, `HYBRID_SEARCH_ENABLED`, `MULTI_HOP_ENABLED`, `FULLTEXT_SEARCH_LIMIT`, `RRF_K`, `RERANK_ENABLED`, chunk token sizes, CORS, Docker init flags, `NEXT_PUBLIC_API_URL`.

---

### Code layout (for architects)

```
backend/apps/       clients, documents, chat, users, conversations, lineage (stub), core
backend/services/   parsing (router, excel, csv, xls, sheet_profiles), chunking (parent_child, workbook_chunker),
                    graphrag (hybrid_retriever, multi_hop, workbook_rag, query_expansion, query_signals, metadata_lookup),
                    langchain (streaming, rag_chain, prompts), embedding, neo4j/repositories, storage, llm/token_budget
frontend/src/       app/, components/, context/, lib/api, lib/sse
infrastructure/neo4j/  Cypher 01–05 + phase2 + seed
documentation/phase1/  architecture docs
```

---

### Testing & operations

- `pytest -m "not slow"` unit; `slow` for real embeddings; integration needs Neo4j.
- First worker ingest downloads BGE ~1.3GB.
- Re-ingest spreadsheets after workbook chunker changes.
- Groq TPM trimming via token budget.

---

### Document structure to produce

1. Executive summary  
2. Goals / non-goals (Phase 1)  
3. **Delta: v1 plan → v2 as-built** (summarize from attached v2 §3)  
4. **Delta: v2 as-built → current implementation** (use table above)  
5. System context + actors  
6. Deployment (Docker + make + env)  
7. Neo4j data model (with **current chunk_type** enum)  
8. Ingestion sequence diagram + sheet profile table  
9. RAG architecture + **retrieval routing decision diagram**  
10. Workbook multi-hop + mixed-client paths (detailed)  
11. Chat / SSE / conversation model  
12. Frontend UX  
13. API reference  
14. Configuration  
15. Code layout  
16. Testing & operations (include QA scenarios from README)  
17. Limitations & re-ingest rules  
18. Phase 2 outlook  
19. Appendix: example chunk texts for `database`, `table_definition`, `table_catalog`, `column`, `code_set`, `row`

**Style:** Professional, internal Data Axle stakeholders; tables and diagrams; no marketing fluff. Do not invent features absent from this prompt or the attached v2 doc.

---

*End of prompt*
