# Neo4j infrastructure

## Local development

Docker Compose runs **Neo4j 5 Community** with APOC enabled.

## Vector index

Phase 1 uses `chunk_embeddings` on `ChildChunk.embedding` (1024 dimensions, cosine).

## Client isolation

On Neo4j **2026.01+**, configure `filterable_properties` on the vector index for in-index `client_id` filtering.

On Neo4j 5.x, retrieval still filters with `WHERE cc.client_id = $clientId` after vector search — correct isolation, may be slower at scale.

## Production

Use **Neo4j AuraDB 2026.01+** and set `NEO4J_URI` in `.env` to your Aura bolt URI.
