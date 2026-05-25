// Fulltext index for hybrid keyword + metadata retrieval on ChildChunk nodes.
// Run after 01_constraints.cypher and 02_vector_index.cypher.

CREATE FULLTEXT INDEX childChunkSearch IF NOT EXISTS
FOR (n:ChildChunk)
ON EACH [n.text, n.keywords, n.column_name, n.table_name, n.sheet_name];
