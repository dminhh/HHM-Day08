"""
Group Project — RAG Chatbot
Nhóm HHM | AI20K Cohort 2 | Day 8

Pipeline: Hiếu (2A202600680) — retrieve + generate_with_citation
UI: Streamlit — chat interface, conversation memory, persistent history
"""

import sys
import json
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ─── Load .env ────────────────────────────────────────────────────────────────
_PERSONAL_DIR = Path(__file__).parent.parent / "personal_project" / "2A202600680-Nguyễn Đức Hiếu"
load_dotenv(_PERSONAL_DIR / ".env")

# ─── Import pipeline ──────────────────────────────────────────────────────────
_PERSONAL_SRC = _PERSONAL_DIR / "src"
sys.path.insert(0, str(_PERSONAL_SRC))

from task9_retrieval_pipeline import retrieve
from task10_generation import _call_llm, reorder_for_llm, format_context, SYSTEM_PROMPT

# ─── Conversation storage ─────────────────────────────────────────────────────
CONV_DIR = Path(__file__).parent / "conversations"
CONV_DIR.mkdir(exist_ok=True)


def _save_conv(conv: dict):
    (CONV_DIR / f"{conv['id']}.json").write_text(
        json.dumps(conv, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_all_convs() -> list[dict]:
    convs = []
    for f in sorted(CONV_DIR.glob("*.json"), reverse=True):
        try:
            convs.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return convs


def _load_conv(conv_id: str) -> dict | None:
    f = CONV_DIR / f"{conv_id}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return None


def _new_conv() -> dict:
    return {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:4],
        "title": "Cuộc hội thoại mới",
        "created_at": datetime.now().isoformat(),
        "messages": [],
    }


# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RAG Chatbot — Pháp Luật Ma Tuý",
    page_icon="⚖️",
    layout="wide",
)

# ─── Session state init ───────────────────────────────────────────────────────
if "conv" not in st.session_state:
    st.session_state.conv = _new_conv()
if "top_k" not in st.session_state:
    st.session_state.top_k = 5

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚖️ RAG Chatbot")
    st.caption("Pháp luật Việt Nam về ma tuý")
    st.divider()

    # Nút tạo cuộc trò chuyện mới
    if st.button("✏️ Cuộc trò chuyện mới", use_container_width=True, type="primary"):
        if st.session_state.conv["messages"]:
            _save_conv(st.session_state.conv)
        st.session_state.conv = _new_conv()
        st.rerun()

    st.divider()

    # Danh sách cuộc hội thoại cũ
    all_convs = _load_all_convs()
    current_id = st.session_state.conv["id"]

    if all_convs:
        st.markdown("**Lịch sử hội thoại**")
        for c in all_convs:
            label = c["title"][:35] + ("..." if len(c["title"]) > 35 else "")
            ts = c.get("created_at", "")[:10]
            is_active = c["id"] == current_id

            if st.button(
                f"{'▶ ' if is_active else ''}{label}\n_{ts}_",
                key=c["id"],
                use_container_width=True,
                type="secondary" if not is_active else "primary",
            ):
                if not is_active:
                    if st.session_state.conv["messages"]:
                        _save_conv(st.session_state.conv)
                    loaded = _load_conv(c["id"])
                    if loaded:
                        st.session_state.conv = loaded
                    st.rerun()
    else:
        st.caption("Chưa có lịch sử")

    st.divider()
    st.session_state.top_k = st.slider("Số chunks (top_k)", 3, 10, st.session_state.top_k)

    st.divider()
    st.markdown("**Gợi ý câu hỏi:**")
    for q in [
        "Hình phạt tàng trữ ma tuý là gì?",
        "Nghệ sĩ nào bị bắt vì ma tuý?",
        "Quy trình cai nghiện bắt buộc?",
        "Luật phòng chống ma tuý 2021?",
    ]:
        if st.button(q, use_container_width=True, key=f"sq_{q}"):
            st.session_state["prefill"] = q
            st.rerun()


# ─── Tiêu đề ──────────────────────────────────────────────────────────────────
conv = st.session_state.conv
st.title(f"⚖️ {conv['title']}")
st.caption("Hỏi về luật phòng chống ma tuý, hình phạt, cai nghiện, nghệ sĩ liên quan")


# ─── Render sources ───────────────────────────────────────────────────────────
def _render_sources(sources: list[dict]):
    if not sources:
        return
    with st.expander(f"📚 Nguồn tham khảo ({len(sources)} đoạn)"):
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
                st.markdown(f"`{score:.3f}` · `{via}`")
            st.caption(src["content"][:250] + ("..." if len(src["content"]) > 250 else ""))
            if i < len(sources):
                st.divider()


# ─── Hiển thị lịch sử ────────────────────────────────────────────────────────
for msg in conv["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            _render_sources(msg["sources"])


# ─── Generation có conversation memory ───────────────────────────────────────
def _generate(query: str, history: list[dict], top_k: int) -> dict:
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)

    # 3 turns gần nhất
    history_str = ""
    recent = [m for m in history if m["role"] in ("user", "assistant")][-6:]
    if recent:
        lines = [
            ("Người dùng" if m["role"] == "user" else "Trợ lý") + ": " + m["content"][:300]
            for m in recent
        ]
        history_str = "\n\nLịch sử hội thoại:\n" + "\n".join(lines)

    user_msg = f"Context:\n\n{context}{history_str}\n\n---\n\nCâu hỏi: {query}"
    answer = _call_llm(SYSTEM_PROMPT, user_msg)
    return {"answer": answer, "sources": chunks}


# ─── Xử lý prefill ───────────────────────────────────────────────────────────
prefill = st.session_state.pop("prefill", None)

# ─── Chat input ───────────────────────────────────────────────────────────────
prompt = st.chat_input("Nhập câu hỏi về pháp luật ma tuý...") or prefill

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    conv["messages"].append({"role": "user", "content": prompt})

    # Cập nhật title từ tin nhắn đầu tiên
    if len(conv["messages"]) == 1:
        conv["title"] = prompt[:60]

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm và tổng hợp..."):
            result = _generate(prompt, conv["messages"][:-1], st.session_state.top_k)

        st.markdown(result["answer"])
        if result["sources"]:
            _render_sources(result["sources"])

    # Lưu sources ở dạng gọn để tránh file quá nặng
    slim_sources = [
        {
            "content": s["content"][:300],
            "score": s.get("score", 0),
            "retrieval_source": s.get("retrieval_source", ""),
            "metadata": s.get("metadata", {}),
        }
        for s in result["sources"]
    ]

    conv["messages"].append({
        "role": "assistant",
        "content": result["answer"],
        "sources": slim_sources,
    })

    # Auto-save
    _save_conv(conv)
    st.rerun()
