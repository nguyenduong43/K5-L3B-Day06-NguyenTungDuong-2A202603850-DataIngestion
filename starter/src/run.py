"""Orchestrate the Day 06 Data Ingestion and Benchmark Pipeline."""
import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf
from .store import PgVectorStore


def main() -> None:
    # 0. Load environment variables
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        sys.exit("Error: DATABASE_URL missing in starter/.env")

    model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
    print(f"=== Day 06: Data Ingestion & Benchmark Pipeline ===")
    print(f"Target Database: {database_url.split('@')[-1]}")
    print(f"Embedding Model: {model_name}\n")

    # 1. Load Corpus
    base_dir = Path(__file__).resolve().parents[1]
    pdf_path = base_dir / "data" / "anh-huong-mang-xa-hoi-doi-voi-sinh-vien.pdf"
    if not pdf_path.exists():
        sys.exit(f"Error: Corpus PDF not found at {pdf_path}")

    print(f"1. Loading corpus from: {pdf_path.name}")
    doc_id = "anh-huong-mang-xa-hoi"
    t0 = time.time()
    pages = load_pdf(pdf_path, document_id=doc_id, source=f"data/{pdf_path.name}")
    print(f"   -> Loaded {len(pages)} pages in {time.time() - t0:.2f}s.")

    # 2. Load Benchmark Questions
    bench_path = base_dir / "data" / "benchmark.json"
    if not bench_path.exists():
        sys.exit(f"Error: Benchmark not found at {bench_path}")

    with open(bench_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
    print(f"2. Loaded {len(questions)} benchmark questions ({sum(1 for q in questions if q['split'] == 'dev')} dev, {sum(1 for q in questions if q['split'] == 'test')} test).\n")

    # 3. Initialize Embedder and Store
    print("3. Initializing Gemini Embedder and PostgreSQL Vector Store...")
    embedder = MyEmbedder(model_name=model_name)
    print(f"   -> Using embedding model: {embedder.model_name} (dimensions: {embedder.dimensions})")
    store = PgVectorStore(database_url=database_url, dimensions=embedder.dimensions)
    store.create_schema()
    print("   -> Schema initialized successfully.")

    # 4. Generate Chunks for Strategy A and Strategy B
    print("\n4. Chunking:")
    # Strategy A: Fixed-size 500 chars, overlap 50 chars
    chunks_a = []
    for p in pages:
        chunks_a.extend(fixed_size(p, size=500, overlap=50))
    print(f"   - Strategy A (Fixed size 500, overlap 50): {len(chunks_a)} chunks")

    # Strategy B & C: By paragraph (max_size 800)
    chunks_b = []
    for p in pages:
        chunks_b.extend(by_paragraph(p, max_size=800))
    print(f"   - Strategy B/C (By paragraph, max 800): {len(chunks_b)} chunks")

    # 5. Embedding and Storing Chunks
    print("\n5. Embedding and Storing Chunks into pgvector...")
    # Strategy A
    stored_a = store.count_chunks("strategy_a")
    if stored_a == len(chunks_a):
        print(f"   - Strategy A: Reusing {stored_a} existing vectors in database.")
    else:
        print("   - Embedding Strategy A chunks...")
        t_a = time.time()
        texts_a = [c.text for c in chunks_a]
        vectors_a = embedder.embed_documents(texts_a)
        store.upsert("strategy_a", chunks_a, vectors_a)
        print(f"     -> Stored {len(chunks_a)} vectors for Strategy A in {time.time() - t_a:.2f}s.")

    # Strategy B (Used by Strategy B and C)
    stored_b = store.count_chunks("strategy_b")
    if stored_b == len(chunks_b):
        print(f"   - Strategy B/C: Reusing {stored_b} existing vectors in database.")
    else:
        print("   - Embedding Strategy B chunks...")
        t_b = time.time()
        texts_b = [c.text for c in chunks_b]
        vectors_b = embedder.embed_documents(texts_b)
        store.upsert("strategy_b", chunks_b, vectors_b)
        print(f"     -> Stored {len(chunks_b)} vectors for Strategy B/C in {time.time() - t_b:.2f}s.")

    # 6. Embedding Queries
    print("\n6. Embedding Benchmark Questions...")
    q_texts = [q["question"] for q in questions]
    q_vectors = [embedder.embed_query(q_txt) for q_txt in q_texts]
    print(f"   -> Embedded {len(q_vectors)} queries successfully.")

    # 7. Running Retrieval Benchmark for 3 Strategies
    print("\n7. Running Benchmark Retrieval (top_k=3)...")
    results = {}

    for strat_name, strat_label, store_key, use_filter in [
        ("Strategy A", "fixed_size_no_filter", "strategy_a", False),
        ("Strategy B", "paragraph_no_filter", "strategy_b", False),
        ("Strategy C", "paragraph_with_filter", "strategy_b", True),
    ]:
        print(f"   - Evaluating {strat_name} ({strat_label})...")
        traces = []
        for q, q_vec in zip(questions, q_vectors):
            filters = q.get("filter") if use_filter else None
            hits = store.search(strategy=store_key, query_vector=q_vec, top_k=3, filters=filters)
            trace = evaluate_query(question=q, hits=hits, strategy=strat_name)
            traces.append(trace)

        summary = summarize(traces)
        results[strat_name] = {
            "label": strat_label,
            "traces": traces,
            "summary": summary,
        }

    # 8. Print Results Summary
    print("\n" + "=" * 65)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 65)
    header = f"{'Strategy':<12} | {'Split':<6} | {'Hit@1':<10} | {'Evidence Hit@3':<16} | {'Filter Compliance':<18}"
    print(header)
    print("-" * 65)

    for strat_name in ["Strategy A", "Strategy B", "Strategy C"]:
        sum_dict = results[strat_name]["summary"]
        for sp in ["dev", "test", "all"]:
            sp_data = sum_dict.get(sp, {})
            h1 = f"{sp_data.get('hit_at_1', {}).get('ratio', 'N/A')} ({sp_data.get('hit_at_1', {}).get('rate', 0)*100:.1f}%)"
            h3 = f"{sp_data.get('evidence_hit_at_3', {}).get('ratio', 'N/A')} ({sp_data.get('evidence_hit_at_3', {}).get('rate', 0)*100:.1f}%)"
            fc = f"{sp_data.get('filter_compliance', {}).get('ratio', 'N/A')}"
            print(f"{strat_name:<12} | {sp:<6} | {h1:<10} | {h3:<16} | {fc:<18}")
        print("-" * 65)

    # 9. Save Traces to Root Results
    root_results_dir = Path(__file__).resolve().parents[2] / "results"
    root_results_dir.mkdir(parents=True, exist_ok=True)

    with open(root_results_dir / "all_traces.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    with open(root_results_dir / "traces_strategy_A.json", "w", encoding="utf-8") as f:
        json.dump(results.get("Strategy A", {}).get("traces", []), f, ensure_ascii=False, indent=2)

    with open(root_results_dir / "traces_strategy_B.json", "w", encoding="utf-8") as f:
        json.dump(results.get("Strategy B", {}).get("traces", []), f, ensure_ascii=False, indent=2)

    with open(root_results_dir / "traces_strategy_C.json", "w", encoding="utf-8") as f:
        json.dump(results.get("Strategy C", {}).get("traces", []), f, ensure_ascii=False, indent=2)

    summary_data = {
        "Strategy A": results.get("Strategy A", {}).get("summary", {}),
        "Strategy B": results.get("Strategy B", {}).get("summary", {}),
        "Strategy C": results.get("Strategy C", {}).get("summary", {}),
    }
    with open(root_results_dir / "benchmark_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    print(f"\nSaved all benchmark traces and summary files to: {root_results_dir}")


if __name__ == "__main__":
    main()
