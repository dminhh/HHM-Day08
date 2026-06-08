"""
Task 4 — Chunking & Indexing vào ChromaDB.

Lựa chọn kỹ thuật:
- Chunking: RecursiveCharacterTextSplitter (chunk_size=800, overlap=150)
  Lý do: Văn bản pháp luật và báo chí thường có đoạn dài, cần context đủ rộng.
  800 chars ≈ 100-150 tokens, phù hợp để giữ nguyên ý nghĩa pháp lý.
  Overlap 150 đảm bảo không mất thông tin tại điểm cắt.

- Embedding: paraphrase-multilingual-MiniLM-L12-v2 (384 dim)
  Lý do: Multilingual, hỗ trợ tiếng Việt tốt, nhẹ và nhanh (22M params).
  Phù hợp chạy local không cần GPU mạnh.

- Vector Store: ChromaDB persistent
  Lý do: Không cần Docker, dễ setup, hỗ trợ cosine similarity built-in.

Chạy: python -m src.task4_chunking_indexing
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DB_PATH = str(Path(__file__).parent.parent / "chroma_db")

# --- Chunking config ---
# chunk_size=800: đủ context cho câu hỏi pháp lý, không quá dài gây nhiễu
# chunk_overlap=150: tránh mất ngữ nghĩa tại điểm cắt
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# --- Embedding config ---
# paraphrase-multilingual-MiniLM-L12-v2: 384 dim, multilingual, nhanh
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
EMBEDDING_DIM = 384

COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "drug_law_docs")

_model: SentenceTransformer | None = None
_chroma_client: chromadb.PersistentClient | None = None
_collection = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"  Loading embedding model: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def get_chroma_collection():
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def load_documents() -> list[dict]:
    """Đọc toàn bộ markdown files từ data/standardized/."""
    documents = []
    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8").strip()
        if len(content) < 50:
            continue
        doc_type = "legal" if "legal" in str(md_file) else "news"
        documents.append({
            "content": content,
            "metadata": {
                "source": md_file.name,
                "source_path": str(md_file.relative_to(STANDARDIZED_DIR)),
                "type": doc_type,
            },
        })
        print(f"  Loaded: {md_file.name} ({len(content):,} chars, type={doc_type})")
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chunk documents dùng RecursiveCharacterTextSplitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", ".", " ", ""],
        length_function=len,
    )

    chunks = []
    for doc in documents:
        splits = splitter.split_text(doc["content"])
        for i, chunk_text in enumerate(splits):
            if len(chunk_text.strip()) < 30:
                continue
            chunks.append({
                "content": chunk_text.strip(),
                "metadata": {
                    **doc["metadata"],
                    "chunk_index": i,
                    "total_chunks": len(splits),
                },
            })
    return chunks


def index_to_chromadb(chunks: list[dict]) -> int:
    """Embed và lưu chunks vào ChromaDB. Trả về số chunks đã index."""
    model = get_embedding_model()
    collection = get_chroma_collection()

    # Clear collection cũ nếu có
    existing = collection.count()
    if existing > 0:
        print(f"  ⚠ Collection đã có {existing} docs. Xoá và index lại...")
        # Xoá toàn bộ
        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)

    batch_size = 64
    total = len(chunks)

    print(f"  Embedding & indexing {total} chunks (batch={batch_size})...")

    for start in tqdm(range(0, total, batch_size), desc="Indexing"):
        batch = chunks[start : start + batch_size]
        texts = [c["content"] for c in batch]
        embeddings = model.encode(texts, normalize_embeddings=True).tolist()

        ids = [str(uuid.uuid4()) for _ in batch]
        metadatas = [c["metadata"] for c in batch]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    return total


def run_pipeline():
    """Load → Chunk → Embed → Index."""
    print("=" * 60)
    print("Task 4: Chunking & Indexing")
    print(f"  Chunking: RecursiveCharacter (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Vector Store: ChromaDB @ {CHROMA_DB_PATH}")
    print("=" * 60)

    print("\n[1/3] Loading documents...")
    docs = load_documents()
    if not docs:
        print("✗ Không tìm thấy file markdown. Hãy chạy Task 3 trước.")
        return 0
    print(f"  → {len(docs)} documents loaded")

    print("\n[2/3] Chunking...")
    chunks = chunk_documents(docs)
    print(f"  → {len(chunks)} chunks tạo ra")

    print("\n[3/3] Indexing into ChromaDB...")
    indexed = index_to_chromadb(chunks)

    collection = get_chroma_collection()
    print(f"\n✓ Hoàn thành! {indexed} chunks đã index vào '{COLLECTION_NAME}'")
    print(f"  Total in DB: {collection.count()}")
    return indexed


if __name__ == "__main__":
    run_pipeline()
