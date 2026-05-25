CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
FOR (c:ChildChunk) ON (c.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1024,
    `vector.similarity_function`: 'cosine'
  }
};
