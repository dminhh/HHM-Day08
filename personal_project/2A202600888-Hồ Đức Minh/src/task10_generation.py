"""
Task 10 — Generation Có Citation

1. reorder_for_llm(): Sắp xếp chunks theo pattern "Lost in the Middle"
   - Chunk quan trọng nhất → đầu và cuối
   - Chunk ít quan trọng hơn → giữa
   Lý do: LLM có xu hướng bỏ qua thông tin ở giữa context dài
   (Liu et al., 2023 - Lost in the Middle)

2. format_context(): Format chunks thành context string có metadata cho citation

3. generate_with_citation(): Gọi LLM với system prompt yêu cầu trả lời có citation

LLM: OpenAI GPT-4o-mini (nếu có OPENAI_API_KEY), fallback về mock answer
top_p=0.9: đủ đa dạng, tránh lặp lại
top_k (max_tokens)=1024: đủ dài cho câu trả lời pháp lý có citation
"""

import os
from dotenv import load_dotenv

from src.task9_retrieval_pipeline import retrieve

load_dotenv()

SYSTEM_PROMPT = """Answer the following question comprehensively.
For every statement of fact or claim, immediately insert a citation
in brackets linking to the specific source
(e.g., [Author/Platform Name, Year]).
If the information is not explicitly stated in the provided context
or knowledge base, state 'I cannot verify this information'
rather than guessing."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """
    Sắp xếp chunks theo pattern tránh "Lost in the Middle".

    Pattern: [rank1, rank3, rank5, ..., rank4, rank2]
    - Quan trọng nhất (rank 1) ở đầu
    - Quan trọng thứ hai (rank 2) ở cuối
    - Ít quan trọng hơn ở giữa

    Args:
        chunks: List chunks đã rerank, sorted descending theo score

    Returns:
        List chunks được sắp xếp lại
    """
    if len(chunks) <= 2:
        return chunks

    # Tách: vị trí chẵn → đầu list, vị trí lẻ → cuối list (đảo ngược)
    front = chunks[::2]   # index 0, 2, 4, ...
    back = chunks[1::2]   # index 1, 3, 5, ...
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """
    Format chunks thành context string với source metadata cho citation.

    Args:
        chunks: List of {'content': str, 'score': float, 'metadata': dict}

    Returns:
        Formatted context string
    """
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("metadata", {}).get("source", f"source_{i}")
        # Bỏ extension để tên gọn hơn
        source_name = source.replace(".md", "").replace(".pdf", "").replace(".doc", "")
        parts.append(f"[{source_name}]\n{chunk['content']}")

    return "\n\n---\n\n".join(parts)


def generate_with_citation(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.3,
) -> dict:
    """
    Generate câu trả lời có citation từ RAG pipeline.

    1. Retrieve context chunks (Task 9)
    2. Reorder để tránh lost in the middle
    3. Format context với source metadata
    4. Gọi LLM với system prompt yêu cầu citation

    Args:
        query: Câu hỏi của user
        top_k: Số chunks dùng làm context
        score_threshold: Ngưỡng fallback PageIndex

    Returns:
        {'answer': str, 'sources': list[str], 'chunks_used': int}
    """
    # Bước 1: Retrieve
    chunks = retrieve(query, top_k=top_k, score_threshold=score_threshold)

    if not chunks:
        return {
            "answer": "I cannot verify this information — không tìm được context liên quan.",
            "sources": [],
            "chunks_used": 0,
        }

    # Bước 2: Reorder
    reordered = reorder_for_llm(chunks)

    # Bước 3: Format context
    context = format_context(reordered)
    sources = list({
        c.get("metadata", {}).get("source", "unknown")
        for c in reordered
    })

    # Bước 4: Gọi LLM
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key:
        answer = _call_openai(query, context, api_key)
    else:
        # Fallback mock khi không có API key
        answer = (
            f"[Mock answer — cần OPENAI_API_KEY]\n\n"
            f"Câu hỏi: {query}\n\n"
            f"Context từ {len(reordered)} chunks đã được retrieve. "
            f"Nguồn: {', '.join(sources)}"
        )

    return {
        "answer": answer,
        "sources": sources,
        "chunks_used": len(reordered),
    }


def _call_openai(query: str, context: str, api_key: str) -> str:
    """Gọi OpenAI API để generate câu trả lời có citation."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    user_prompt = f"""Context:
{context}

Question: {query}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        # top_p=0.9: cân bằng giữa đa dạng và chính xác
        # max_tokens=1024: đủ dài cho câu trả lời pháp lý có citation
        top_p=0.9,
        max_tokens=1024,
        temperature=0.3,
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    query = "Hình phạt cho tội tàng trữ trái phép chất ma tuý là gì?"
    print(f"Query: {query}\n")
    result = generate_with_citation(query, top_k=5)
    print(f"Answer:\n{result['answer']}")
    print(f"\nSources: {result['sources']}")
    print(f"Chunks used: {result['chunks_used']}")
