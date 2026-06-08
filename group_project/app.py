"""
Group Project — RAG Chatbot
Nhóm HHM | AI20K Cohort 2 | Day 8

Pipeline: Hiếu (2A202600680) — retrieve + generate_with_citation
UI: Streamlit — chat interface, conversation memory, source display
"""

import sys
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ─── Load .env từ thư mục cá nhân của Hiếu ───────────────────────────────────
_PERSONAL_DIR = Path(__file__).parent.parent / "personal_project" / "2A202600680-Nguyễn Đức Hiếu"
load_dotenv(_PERSONAL_DIR / ".env")

# ─── Import pipeline từ src cá nhân của Hiếu ─────────────────────────────────
_PERSONAL_SRC = _PERSONAL_DIR / "src"
sys.path.insert(0, str(_PERSONAL_SRC))

from task9_retrieval_pipeline import retrieve
from task10_generation import _call_llm, reorder_for_llm, format_context, SYSTEM_PROMPT

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RAG Chatbot — Pháp Luật Ma Tuý",
    page_icon="⚖️",
    layout="wide",
)

# ─── Session state ────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {role, content, sources?}

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚖️ RAG Chatbot")
    st.markdown("**Chủ đề:** Pháp luật Việt Nam về ma tuý và các chất cấm")
    st.divider()

    top_k = st.slider("Số chunks tìm kiếm (top_k)", min_value=3, max_value=10, value=5)

    st.divider()
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("**Gợi ý câu hỏi:**")
    sample_questions = [
        "Hình phạt tàng trữ ma tuý là gì?",
        "Nghệ sĩ nào bị bắt vì ma tuý?",
        "Quy trình cai nghiện bắt buộc?",
        "Luật phòng chống ma tuý 2021 có điểm gì mới?",
    ]
    for q in sample_questions:
        if st.button(q, use_container_width=True, key=q):
            st.session_state["prefill"] = q
            st.rerun()

    st.divider()
    st.caption("Nhóm HHM | AI20K Cohort 2 | Day 8")


# ─── Tiêu đề ──────────────────────────────────────────────────────────────────
st.title("⚖️ Chatbot Pháp Luật Ma Tuý")
st.caption("Hỏi về luật phòng chống ma tuý, hình phạt, cai nghiện, nghệ sĩ liên quan")


# ─── Hiển thị source helper ───────────────────────────────────────────────────
def _render_sources(sources: list[dict]):
    with st.expander(f"📚 Nguồn tham khảo ({len(sources)} đoạn văn bản)"):
        for i, src in enumerate(sources, 1):
            meta = src.get("metadata", {})
            score = src.get("score", 0.0)
            via = src.get("retrieval_source", "hybrid")
            name = meta.get("source", f"Tài liệu {i}")
            doc_type = meta.get("type", "")

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**[{i}] {name}**" + (f" · _{doc_type}_" if doc_type else ""))
            with col2:
                st.markdown(f"`score: {score:.3f}` · `{via}`")

            st.caption(src["content"][:250] + ("..." if len(src["content"]) > 250 else ""))
            if i < len(sources):
                st.divider()


# ─── Hiển thị lịch sử chat ───────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            _render_sources(msg["sources"])


# ─── Generation có conversation memory ───────────────────────────────────────
def _generate(query: str, history: list[dict], top_k: int) -> dict:
    """RAG generation tích hợp conversation memory (3 turns gần nhất)."""
    chunks = retrieve(query, top_k=top_k)

    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)

    # Đưa 3 turns gần nhất vào prompt để hỗ trợ follow-up questions
    history_str = ""
    recent = [m for m in history if m["role"] in ("user", "assistant")][-6:]
    if recent:
        lines = []
        for m in recent:
            role = "Người dùng" if m["role"] == "user" else "Trợ lý"
            lines.append(f"{role}: {m['content'][:300]}")
        history_str = "\n\nLịch sử hội thoại gần đây:\n" + "\n".join(lines)

    user_msg = f"Context:\n\n{context}{history_str}\n\n---\n\nCâu hỏi: {query}"
    answer = _call_llm(SYSTEM_PROMPT, user_msg)

    return {"answer": answer, "sources": chunks}


# ─── Xử lý prefill từ nút sidebar ────────────────────────────────────────────
prefill = st.session_state.pop("prefill", None)

# ─── Chat input ───────────────────────────────────────────────────────────────
prompt = st.chat_input("Nhập câu hỏi về pháp luật ma tuý...") or prefill

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm và tổng hợp..."):
            result = _generate(
                prompt,
                st.session_state.messages[:-1],
                top_k=top_k,
            )

        st.markdown(result["answer"])
        if result["sources"]:
            _render_sources(result["sources"])

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
    })
