"""
Task 10 — Generation Có Citation (RAG + FPT Cloud LLM).

LLM config:
  - model: gpt-oss-20b (FPT Cloud, OpenAI-compatible API)
  - temperature=0.3: RAG cần factual, ít hallucination → temperature thấp
  - top_p=0.9: nucleus sampling, giữ diversity hợp lý nhưng không lan man
  - max_tokens=1500: đủ dài cho câu trả lời pháp luật chi tiết

Document reordering (Lost-in-the-Middle prevention):
  Input:  [1, 2, 3, 4, 5]  (sorted by score desc)
  Output: [1, 3, 5, 4, 2]  (best ở đầu và cuối, kém quan trọng ở giữa)

Chạy: python -m src.task10_generation
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

from .task9_retrieval_pipeline import retrieve

# override=True: đảm bảo giá trị trong .env ghi đè mọi env var có sẵn trong system
load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://mkp-api.fptcloud.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-oss-20b")

# temperature=0.3: RAG cần câu trả lời factual, không sáng tạo
# top_p=0.9: nucleus sampling — đủ diverse, không quá random
# top_k=5: đủ evidence, tránh context quá dài gây lost-in-middle
# max_tokens=4000: gpt-oss-20b là reasoning model — cần nhiều tokens cho
#   chain-of-thought (reasoning field) trước khi sinh content thực sự.
#   Nếu max_tokens < ~500, model chưa kịp viết content, chỉ còn reasoning.
TEMPERATURE = 0.3
TOP_P = 0.9
TOP_K = 5
MAX_TOKENS = 4000

SYSTEM_PROMPT = """Bạn là trợ lý pháp lý chuyên về luật ma tuý Việt Nam.
Trả lời câu hỏi bằng tiếng Việt, dựa HOÀN TOÀN vào context được cung cấp.

Quy tắc citation bắt buộc:
- Mọi thông tin pháp lý phải có citation dạng [Tên văn bản, Điều X] hoặc [Nguồn, Năm]
- Ví dụ: [Luật PCMT 2021, Điều 3], [VnExpress, 2026], [BLHS 2015, Điều 248]
- Nếu thông tin KHÔNG có trong context → trả lời "Tôi không thể xác minh thông tin này từ nguồn hiện có"
- KHÔNG được suy đoán hoặc thêm thông tin ngoài context
- Cấu trúc câu trả lời rõ ràng, có đoạn văn tách biệt"""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """
    Sắp xếp chunks tránh "Lost in the Middle" effect.

    Nghiên cứu Liu et al. 2023 cho thấy LLM nhớ tốt thông tin ở
    đầu và cuối context, quên thông tin ở giữa.

    Strategy: odd-indexed chunks (rank 1,3,5...) đặt đầu tiên,
    even-indexed chunks (rank 2,4,...) đặt ngược lại ở cuối.

    Input  (score desc): [rank1, rank2, rank3, rank4, rank5]
    Output:              [rank1, rank3, rank5, rank4, rank2]
    """
    if len(chunks) <= 2:
        return chunks

    top_half = chunks[::2]       # indices 0,2,4... (odd ranks = more relevant)
    bottom_half = chunks[1::2]   # indices 1,3,5... (even ranks = less relevant)
    return top_half + bottom_half[::-1]


def format_context(chunks: list[dict]) -> str:
    """
    Format chunks thành context string với source labels để LLM cite.
    """
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", f"Document {i}")
        doc_type = meta.get("type", "unknown")
        score = chunk.get("score", 0.0)
        content = chunk["content"].strip()

        parts.append(
            f"[Tài liệu {i} | Nguồn: {source} | Loại: {doc_type} | Score: {score:.3f}]\n"
            f"{content}"
        )
    return "\n\n---\n\n".join(parts)


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """
    End-to-end RAG generation với citation dùng FPT Cloud LLM (OpenAI-compatible).

    Pipeline:
        1. Retrieve chunks (hybrid search + reranking)
        2. Reorder để tránh lost-in-the-middle
        3. Format context với source labels
        4. Build prompt với SYSTEM_PROMPT
        5. Gọi LLM API (OpenAI SDK, FPT Cloud endpoint)
        6. Return {answer, sources, retrieval_source}

    Args:
        query:  Câu hỏi
        top_k:  Số chunks đưa vào context

    Returns:
        {
            'answer': str,           — câu trả lời có citation
            'sources': list[dict],   — các chunks dùng làm context
            'retrieval_source': str  — 'hybrid' | 'pageindex'
        }
    """
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY chưa được set trong .env."
        )

    # Step 1: Retrieve
    print(f"  Retrieving context (top_k={top_k})...")
    chunks = retrieve(query, top_k=top_k)

    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có (không tìm thấy context).",
            "sources": [],
            "retrieval_source": "none",
        }

    # Step 2: Reorder (lost-in-the-middle prevention)
    reordered = reorder_for_llm(chunks)

    # Step 3: Format context
    context_str = format_context(reordered)

    # Step 4: Build user message
    user_message = (
        f"Context từ cơ sở tri thức:\n\n"
        f"{context_str}\n\n"
        f"{'='*60}\n\n"
        f"Câu hỏi: {query}"
    )

    # Step 5: Call LLM (OpenAI SDK với FPT Cloud base_url)
    client = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
    )

    response = client.chat.completions.create(
        model=LLM_MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    msg = response.choices[0].message
    # gpt-oss-20b là reasoning model: content có thể None nếu model đang
    # trong giai đoạn reasoning. Fallback sang reasoning field nếu cần.
    answer = msg.content or getattr(msg, "reasoning", None) or "Tôi không thể xác minh thông tin này từ nguồn hiện có."

    # Step 6: Return
    retrieval_source = chunks[0].get("source", "hybrid") if chunks else "none"
    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
        "usage": {
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0,
        },
    }


if __name__ == "__main__":
    test_queries = [
        "Hình phạt cho tội tàng trữ trái phép chất ma tuý theo pháp luật Việt Nam?",
        "Những nghệ sĩ nào đã bị bắt vì liên quan tới ma tuý gần đây?",
        "Luật Phòng chống ma tuý 2021 quy định gì về cai nghiện bắt buộc?",
    ]

    for q in test_queries:
        print(f"\n{'='*70}")
        print(f"Q: {q}")
        print("=" * 70)
        result = generate_with_citation(q)
        print(f"\nA:\n{result['answer']}")
        n_src = len(result["sources"])
        usage = result.get("usage", {})
        print(f"\n[{n_src} nguồn | via {result['retrieval_source']} | "
              f"tokens: {usage.get('input_tokens',0)}in/{usage.get('output_tokens',0)}out]")
