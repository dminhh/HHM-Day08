"""
Task 10 — Generation Có Citation.

Pipeline:
    1. Retrieve chunks (Task 9)
    2. Reorder chunks để tránh "lost in the middle"
    3. Format context với source labels
    4. Call LLM (auto-detect OpenAI / Anthropic / Gemini)
    5. Return answer có citation [Nguồn, Năm]

Tham số generation:
    temperature=0.3: RAG cần factual, ít sáng tạo → thấp
    top_p=0.9: nucleus sampling, giữ diversity trong câu chữ nhưng không quá random
    max_tokens=1024: đủ dài cho câu trả lời có citation

Cài đặt (chọn 1):
    pip install openai          # nếu dùng OpenAI
    pip install anthropic       # nếu dùng Anthropic Claude
    pip install google-generativeai  # nếu dùng Gemini

Thêm API key vào .env:
    OPENAI_API_KEY=sk-...
    ANTHROPIC_API_KEY=sk-ant-...
    GEMINI_API_KEY=AI...
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    from .task9_retrieval_pipeline import retrieve
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from task9_retrieval_pipeline import retrieve


# =============================================================================
# CONFIGURATION
# =============================================================================

TOP_K = 5          # 5 chunks: đủ evidence, không gây lost in the middle
TOP_P = 0.9        # nucleus sampling — diverse nhưng coherent
TEMPERATURE = 0.3  # thấp vì RAG cần factual accuracy
MAX_TOKENS = 1024

SYSTEM_PROMPT = """Bạn là trợ lý pháp lý. Trả lời câu hỏi bằng tiếng Việt dựa CHỈ vào context được cung cấp.

Quy tắc:
- Mỗi khẳng định PHẢI có trích dẫn nguồn dạng [Tên nguồn, Năm/Điều khoản]
- Nếu context không đủ thông tin, trả lời: "Tôi không thể xác minh thông tin này từ nguồn hiện có"
- Không suy đoán hay thêm thông tin ngoài context
- Cấu trúc câu trả lời rõ ràng, có đoạn văn"""


# =============================================================================
# DOCUMENT REORDERING — tránh "lost in the middle"
# =============================================================================

def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """
    Sắp xếp chunks để tránh "lost in the middle" (Liu et al. 2023).

    LLM nhớ thông tin ĐẦU và CUỐI tốt hơn GIỮA.
    → Đặt chunks quan trọng nhất ở đầu và cuối.

    Input (sorted by score desc): [1, 2, 3, 4, 5]  (1=best)
    Output:                       [1, 3, 5, 4, 2]
    """
    if len(chunks) <= 2:
        return chunks

    top = chunks[::2]       # index 0, 2, 4 → đặt ở đầu
    bottom = chunks[1::2]   # index 1, 3    → đặt ở cuối (reversed)
    return top + bottom[::-1]


# =============================================================================
# CONTEXT FORMATTING
# =============================================================================

def format_context(chunks: list[dict]) -> str:
    """Format chunks thành context string cho prompt."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", f"Source {i}")
        doc_type = meta.get("type", "unknown")
        parts.append(
            f"[Tài liệu {i} | Nguồn: {source} | Loại: {doc_type}]\n"
            f"{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


# =============================================================================
# LLM CALL — auto-detect provider
# =============================================================================

def _call_llm(system: str, user: str) -> str:
    """Auto-detect API key và gọi LLM tương ứng."""

    # Anthropic Claude
    if os.getenv("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text

    # OpenAI
    if os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI
        client = OpenAI()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_tokens=MAX_TOKENS,
        )
        return resp.choices[0].message.content

    # Google Gemini
    if os.getenv("GEMINI_API_KEY"):
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system,
            generation_config={"temperature": TEMPERATURE, "top_p": TOP_P, "max_output_tokens": MAX_TOKENS},
        )
        return model.generate_content(user).text

    raise EnvironmentError(
        "Chưa có API key. Thêm vào file .env:\n"
        "  ANTHROPIC_API_KEY=sk-ant-...\n"
        "  OPENAI_API_KEY=sk-...\n"
        "  GEMINI_API_KEY=AI..."
    )


# =============================================================================
# MAIN GENERATION
# =============================================================================

def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """
    End-to-end RAG generation có citation.

    Returns:
        {
            'answer': str,           # câu trả lời có citation
            'sources': list[dict],   # chunks đã dùng
            'retrieval_source': str  # 'hybrid' hoặc 'pageindex'
        }
    """
    # 1. Retrieve
    chunks = retrieve(query, top_k=top_k)

    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "retrieval_source": "none",
        }

    # 2. Reorder (tránh lost in the middle)
    reordered = reorder_for_llm(chunks)

    # 3. Format context
    context = format_context(reordered)

    # 4. Build prompt
    user_message = f"Context:\n\n{context}\n\n---\n\nCâu hỏi: {query}"

    # 5. Call LLM
    answer = _call_llm(SYSTEM_PROMPT, user_message)

    # 6. Return
    retrieval_source = chunks[0].get("retrieval_source", "hybrid") if chunks else "none"
    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    queries = [
        "Hình phạt cho tội tàng trữ trái phép chất ma tuý theo pháp luật Việt Nam?",
        "Những nghệ sĩ nào đã bị bắt vì liên quan tới ma tuý?",
        "Quy trình cai nghiện bắt buộc theo Luật Phòng chống ma tuý?",
    ]

    for q in queries:
        print(f"\n{'='*70}")
        print(f"Q: {q}")
        print("=" * 70)
        result = generate_with_citation(q)
        print(f"\nA: {result['answer']}")
        print(f"\n[{len(result['sources'])} chunks | via {result['retrieval_source']}]")
