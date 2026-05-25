// Optional backfill for legacy chunks missing metadata (run manually if needed).
// Re-ingesting Excel data dictionaries is the recommended path.

MATCH (cc:ChildChunk)
WHERE cc.chunk_type IS NULL
SET cc.chunk_type = 'row',
    cc.keywords = coalesce(cc.keywords, '');

MATCH (c:Chunk)
WHERE c.chunk_type IS NULL
SET c.chunk_type = 'row',
    c.keywords = coalesce(c.keywords, '');
