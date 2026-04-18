CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS qa_vector_chunks (
    id INTEGER NOT NULL PRIMARY KEY,
    source_type VARCHAR(32) NOT NULL,
    source_id INTEGER NOT NULL,
    lesson_id INTEGER NULL,
    section_id INTEGER NULL,
    page_no INTEGER NULL,
    chunk_text TEXT NOT NULL,
    metadata_json JSON NULL,
    embedding vector(1024) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qa_vector_chunks_embedding
ON qa_vector_chunks USING hnsw (embedding vector_cosine_ops);
