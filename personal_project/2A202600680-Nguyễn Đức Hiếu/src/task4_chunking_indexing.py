"""
Task 4 — Chunking & Indexing vào Vector Store.

Lựa chọn:
  - Chunking: RecursiveCharacterTextSplitter
      chunk_size=800: đủ dài để giữ ngữ cảnh điều khoản pháp luật (thường dài)
      overlap=100: giữ liên tục ngữ nghĩa giữa 2 chunk liền kề
  - Embedding: BAAI/bge-m3 (1024 dim)
      Lý do: multilingual SOTA, hỗ trợ tiếng Việt tốt nhất trong các model open-source
  - Vector Store: FAISS (IndexFlatIP + normalized vectors = cosine similarity)
      Lý do: lưu file trực tiếp (.index + .json), không phụ thuộc server/process lifecycle

Cài đặt:
    pip install faiss-cpu langchain-text-splitters sentence-transformers
"""

import json
from pathlib import Path

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
INDEX_DIR = Path(__file__).parent.parent / "data" / "faiss_index"
FAISS_FILE = INDEX_DIR / "vectors.index"
CHUNKS_FILE = INDEX_DIR / "chunks.json"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024


def load_documents() -> list[dict]:
    """Đọc toàn bộ markdown files từ data/standardized/."""
    documents = []
    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        if not content.strip():
            continue
        doc_type = "legal" if "legal" in md_file.parts else "news"
        documents.append({
            "content": content,
            "metadata": {"source": md_file.name, "type": doc_type},
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chunk documents bằng RecursiveCharacterTextSplitter."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for doc in documents:
        splits = splitter.split_text(doc["content"])
        for i, chunk_text in enumerate(splits):
            if not chunk_text.strip():
                continue
            chunks.append({
                "content": chunk_text,
                "metadata": {**doc["metadata"], "chunk_index": i},
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Embed toàn bộ chunks bằng BAAI/bge-m3."""
    from sentence_transformers import SentenceTransformer

    print(f"  Loading model: {EMBEDDING_MODEL} ...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    texts = [c["content"] for c in chunks]
    embeddings = model.encode(
        texts,
        batch_size=16,
        show_progress_bar=True,
        normalize_embeddings=True,  # cosine similarity via inner product
    )

    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb.tolist()
    return chunks


def index_to_faiss(chunks: list[dict]):
    """Lưu chunks vào FAISS index + JSON metadata."""
    import faiss
    import numpy as np

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    embeddings = np.array([c["embedding"] for c in chunks], dtype="float32")

    # IndexFlatIP với normalized vectors = cosine similarity
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(embeddings)

    # Dùng serialize_index thay vì write_index để tránh lỗi đường dẫn Unicode trên Windows
    FAISS_FILE.write_bytes(faiss.serialize_index(index))

    # Lưu nội dung và metadata riêng
    chunk_data = [{"content": c["content"], "metadata": c["metadata"]} for c in chunks]
    CHUNKS_FILE.write_text(json.dumps(chunk_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  FAISS index: {index.ntotal} vectors @ {FAISS_FILE.name}")
    print(f"  Chunk data : {CHUNKS_FILE.name} ({CHUNKS_FILE.stat().st_size // 1024} KB)")


def run_pipeline():
    """Chạy toàn bộ pipeline: load → chunk → embed → index."""
    print("=" * 55)
    print("Task 4: Chunking & Indexing")
    print(f"  Chunking : RecursiveCharacter (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Store    : FAISS @ {INDEX_DIR}")
    print("=" * 55)

    docs = load_documents()
    print(f"\nLoaded  : {len(docs)} documents")

    chunks = chunk_documents(docs)
    print(f"Chunks  : {len(chunks)} chunks")

    chunks = embed_chunks(chunks)
    print(f"Embedded: {len(chunks)} chunks")

    index_to_faiss(chunks)
    print("\nDone — FAISS index ready")


if __name__ == "__main__":
    run_pipeline()
