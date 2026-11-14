"""Store and search vectors using PostgreSQL + pgvector."""
import json
from typing import Any
import psycopg
from psycopg.types.json import Jsonb

from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        """Retain connection settings and validate model dimensions."""
        if not database_url:
            raise ValueError("DATABASE_URL cannot be empty")
        if dimensions <= 0:
            raise ValueError(f"Invalid vector dimensions: {dimensions}")
        self.database_url = database_url
        self.dimensions = dimensions

    def create_schema(self) -> None:
        """Create table with vector column and metadata indexes."""
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS chunks (
                        chunk_id TEXT NOT NULL,
                        strategy TEXT NOT NULL,
                        document_id TEXT NOT NULL,
                        source TEXT NOT NULL,
                        page INTEGER NOT NULL,
                        section TEXT,
                        text TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding vector({self.dimensions}) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (chunk_id, strategy)
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_strategy ON chunks (strategy);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_section ON chunks (section);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_page ON chunks (page);")
            conn.commit()

    def count_chunks(self, strategy: str) -> int:
        """Return the count of stored chunks for a strategy."""
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM chunks WHERE strategy = %s;", (strategy,))
                row = cur.fetchone()
                return row[0] if row else 0

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Write stable IDs without duplicates; replace obsolete chunks per strategy and document."""
        if len(chunks) != len(vectors):
            raise ValueError(f"Chunks count ({len(chunks)}) does not match vectors count ({len(vectors)})")
        if not chunks:
            return

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                # Remove obsolete chunks for this document and strategy to support clean re-ingestion
                doc_ids = list(set(c.document_id for c in chunks))
                for doc_id in doc_ids:
                    cur.execute(
                        "DELETE FROM chunks WHERE strategy = %s AND document_id = %s;",
                        (strategy, doc_id),
                    )

                # Batch insert chunks
                insert_sql = """
                    INSERT INTO chunks (
                        chunk_id, strategy, document_id, source, page, section, text, metadata, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (chunk_id, strategy) DO UPDATE SET
                        text = EXCLUDED.text,
                        section = EXCLUDED.section,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding;
                """
                records = []
                for chunk, vector in zip(chunks, vectors):
                    if len(vector) != self.dimensions:
                        raise ValueError(f"Vector length {len(vector)} does not match store dimensions {self.dimensions}")
                    vec_str = "[" + ",".join(f"{x:.6f}" for x in vector) + "]"
                    section = chunk.metadata.get("section")
                    records.append((
                        chunk.chunk_id,
                        strategy,
                        chunk.document_id,
                        chunk.source,
                        chunk.page,
                        section,
                        chunk.text,
                        Jsonb(chunk.metadata),
                        vec_str,
                    ))

                cur.executemany(insert_sql, records)
            conn.commit()

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Filter metadata, rank by cosine distance (<=>), and return top-k matches."""
        if len(query_vector) != self.dimensions:
            raise ValueError(f"Query vector dimensions {len(query_vector)} != {self.dimensions}")

        vec_str = "[" + ",".join(f"{x:.6f}" for x in query_vector) + "]"

        where_clauses = ["strategy = %s"]
        where_params: list[Any] = [strategy]

        if filters:
            for key, val in filters.items():
                if key == "section":
                    where_clauses.append("section = %s")
                    where_params.append(val)
                elif key == "page":
                    where_clauses.append("page = %s")
                    where_params.append(int(val))
                else:
                    where_clauses.append("metadata->>%s = %s")
                    where_params.extend([key, str(val)])

        where_sql = " AND ".join(where_clauses)
        params = [vec_str, vec_str] + where_params + [top_k]

        query_sql = f"""
            SELECT
                chunk_id,
                text,
                1 - (embedding <=> %s::vector) AS cosine_similarity,
                embedding <=> %s::vector AS distance,
                page,
                source,
                document_id,
                section,
                metadata
            FROM chunks
            WHERE {where_sql}
            ORDER BY distance ASC
            LIMIT %s;
        """

        results: list[dict[str, Any]] = []
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query_sql, params)
                for row in cur.fetchall():
                    results.append({
                        "chunk_id": row[0],
                        "text": row[1],
                        "score": float(row[2]),
                        "distance": float(row[3]),
                        "page": int(row[4]),
                        "source": row[5],
                        "document_id": row[6],
                        "section": row[7],
                        "metadata": row[8],
                    })

        return results
