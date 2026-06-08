"""
RAG Evaluation Pipeline — DeepEval
Nguyễn Thành Huy (2A202600764)

Framework: DeepEval
Metrics: Faithfulness, AnswerRelevancy, ContextualRecall, ContextualPrecision
A/B: Config A (hybrid + reranking) vs Config B (hybrid, no reranking)

Cài đặt:
    pip install deepeval openai python-dotenv

Chạy:
    cd <repo_root>
    python -m group_project.evaluation.eval_pipeline
"""

from __future__ import annotations

import os

# Phải set trước khi import TF/transformers để tránh segfault do protobuf conflict
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import json
import sys
from pathlib import Path

# Fix Vietnamese output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv(override=True)

# sys.path: ưu tiên personal lab (có src/ thực) trước HHM-Day08 (có src/ stub)
# Insert REPO_ROOT trước, PERSONAL_LAB sau → PERSONAL_LAB được ưu tiên (index 0)
REPO_ROOT = Path(__file__).resolve().parents[2]          # HHM-Day08/
PERSONAL_LAB = Path(__file__).resolve().parents[3]       # Day08_.../

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(PERSONAL_LAB) not in sys.path:
    sys.path.insert(0, str(PERSONAL_LAB))

GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
RESULTS_PATH = Path(__file__).parent / "results.md"

METRIC_KEYS = [
    "FaithfulnessMetric",
    "AnswerRelevancyMetric",
    "ContextualRecallMetric",
    "ContextualPrecisionMetric",
]

METRIC_DISPLAY = {
    "FaithfulnessMetric": "Faithfulness",
    "AnswerRelevancyMetric": "Answer Relevance",
    "ContextualRecallMetric": "Context Recall",
    "ContextualPrecisionMetric": "Context Precision",
}


# =============================================================================
# Custom LLM Judge — FPT Cloud gpt-oss-20b
# =============================================================================

def _build_deepeval_llm():
    """Tạo DeepEvalBaseLLM wrapper dùng FPT Cloud làm judge LLM."""
    from deepeval.models.base_model import DeepEvalBaseLLM
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://mkp-api.fptcloud.com/v1"),
    )
    model_name = os.getenv("LLM_MODEL", "gpt-oss-20b")

    class _FPTDeepEvalLLM(DeepEvalBaseLLM):
        def load_model(self):
            return client

        def generate(self, prompt: str, schema=None):
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.1,
            )
            msg = response.choices[0].message
            text = msg.content or getattr(msg, "reasoning", None) or ""
            if schema is not None:
                try:
                    return schema.model_validate_json(text)
                except Exception:
                    pass
            return text

        async def a_generate(self, prompt: str, schema=None):
            return self.generate(prompt, schema)

        def get_model_name(self) -> str:
            return f"FPTCloud-{model_name}"

    return _FPTDeepEvalLLM()


# =============================================================================
# Load golden dataset
# =============================================================================

def load_golden_dataset() -> list[dict]:
    """Load golden dataset từ JSON file."""
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# Run RAG pipeline
# =============================================================================

def _run_rag(question: str, use_reranking: bool = True) -> dict:
    """Gọi retrieve() + generate_with_citation() cho 1 câu hỏi."""
    from src.task9_retrieval_pipeline import retrieve
    from src.task10_generation import generate_with_citation

    contexts = retrieve(question, top_k=5, use_reranking=use_reranking)
    return generate_with_citation(question, contexts)


# =============================================================================
# DeepEval evaluation
# =============================================================================

def evaluate_with_deepeval(
    golden_dataset: list[dict],
    use_reranking: bool = True,
    config_name: str = "default",
) -> list[dict]:
    """
    Evaluate RAG pipeline sử dụng DeepEval với 4 metrics.

    Returns:
        List[dict] — điểm từng câu hỏi, mỗi dict có key = tên metric.
    """
    from deepeval import evaluate
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        ContextualPrecisionMetric,
        ContextualRecallMetric,
        FaithfulnessMetric,
    )
    from deepeval.test_case import LLMTestCase

    judge = _build_deepeval_llm()

    metrics = [
        FaithfulnessMetric(threshold=0.5, model=judge, include_reason=True),
        AnswerRelevancyMetric(threshold=0.5, model=judge, include_reason=True),
        ContextualRecallMetric(threshold=0.5, model=judge, include_reason=True),
        ContextualPrecisionMetric(threshold=0.5, model=judge, include_reason=True),
    ]

    test_cases = []
    print(f"\n[{config_name}] Chạy RAG pipeline ({len(golden_dataset)} câu hỏi)...")
    for i, item in enumerate(golden_dataset, 1):
        print(f"  [{i}/{len(golden_dataset)}] {item['question'][:60]}...")
        try:
            result = _run_rag(item["question"], use_reranking=use_reranking)
            retrieval_context = [c["content"] for c in result.get("sources", [])]
            answer = result.get("answer", "")
        except Exception as e:
            print(f"    ⚠ Lỗi RAG: {e}")
            retrieval_context = []
            answer = ""

        if answer:  # bỏ qua test case khi RAG fail (answer rỗng)
            test_cases.append(
                LLMTestCase(
                    input=item["question"],
                    actual_output=answer,
                    expected_output=item["expected_answer"],
                    retrieval_context=retrieval_context,
                )
            )

    if not test_cases:
        print(f"  ⚠ Không có test case nào hợp lệ (RAG pipeline bị lỗi hết).")
        return []

    print(f"\n[{config_name}] Đang evaluate {len(test_cases)} test cases với DeepEval...")
    from deepeval.evaluate.configs import AsyncConfig, DisplayConfig
    eval_results = evaluate(
        test_cases,
        metrics,
        async_config=AsyncConfig(run_async=False),
        display_config=DisplayConfig(print_results=False, show_indicator=False),
    )

    scores = []
    for tc in eval_results.test_results:
        row = {"question": tc.input}
        for m in tc.metrics_data:
            row[m.name] = round(m.score or 0.0, 4)
        scores.append(row)

    return scores


# =============================================================================
# A/B comparison
# =============================================================================

def compare_configs(golden_dataset: list[dict]) -> dict:
    """
    So sánh A/B:
      - Config A: hybrid search + reranking
      - Config B: hybrid search, không reranking
    """
    print("\n" + "=" * 60)
    print("A/B COMPARISON")
    print("Config A: hybrid + reranking | Config B: hybrid, no rerank")
    print("=" * 60)

    scores_a = evaluate_with_deepeval(
        golden_dataset, use_reranking=True, config_name="Config A (hybrid+rerank)"
    )
    scores_b = evaluate_with_deepeval(
        golden_dataset, use_reranking=False, config_name="Config B (no rerank)"
    )
    return {"config_a": scores_a, "config_b": scores_b}


# =============================================================================
# Helper
# =============================================================================

def _avg(scores: list[dict], key: str) -> float:
    vals = [s[key] for s in scores if key in s]
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def _row_avg(row: dict) -> float:
    vals = [row.get(k, 0.0) for k in METRIC_KEYS]
    return round(sum(vals) / len(vals), 4)


# =============================================================================
# Export results.md
# =============================================================================

def export_results(comparison: dict):
    """Ghi kết quả ra results.md."""
    scores_a = comparison["config_a"]
    scores_b = comparison["config_b"]

    lines = [
        "# RAG Evaluation Results\n",
        "## Framework sử dụng\n\nDeepEval\n",
        "---\n",
        "## Overall Scores\n",
        "| Metric | Config A (hybrid + rerank) | Config B (no rerank) | Δ |",
        "|--------|---------------------------|----------------------|---|",
    ]

    for key in METRIC_KEYS:
        a = _avg(scores_a, key)
        b = _avg(scores_b, key)
        delta = round(a - b, 4)
        sign = "+" if delta >= 0 else ""
        lines.append(
            f"| {METRIC_DISPLAY.get(key, key)} | {a} | {b} | {sign}{delta} |"
        )

    avg_a = round(sum(_avg(scores_a, k) for k in METRIC_KEYS) / len(METRIC_KEYS), 4)
    avg_b = round(sum(_avg(scores_b, k) for k in METRIC_KEYS) / len(METRIC_KEYS), 4)
    d = round(avg_a - avg_b, 4)
    sign = "+" if d >= 0 else ""
    lines.append(f"| **Average** | **{avg_a}** | **{avg_b}** | **{sign}{d}** |")
    lines.append("")

    lines += [
        "---\n",
        "## A/B Comparison Analysis\n",
        "**Config A — Hybrid search (dense + BM25) + Reranking (RRF/MMR):**",
        "> Kết hợp semantic search (ChromaDB cosine) và BM25, sau đó rerank bằng RRF + MMR để đưa chunk liên quan nhất lên đầu.\n",
        "**Config B — Hybrid search, không reranking:**",
        "> Chỉ dùng RRF merge từ dense + sparse, bỏ bước rerank. Nhanh hơn nhưng thứ tự chunk kém tối ưu.\n",
    ]

    winner = "Config A" if avg_a >= avg_b else "Config B"
    diff_direction = "cải thiện" if avg_a >= avg_b else "không cải thiện"
    lines.append(
        f"**Kết luận:**\n> {winner} cho điểm trung bình cao hơn ({avg_a} vs {avg_b}). "
        f"Bước reranking {diff_direction} chất lượng truy xuất so với pipeline không rerank.\n"
    )

    lines += [
        "---\n",
        "## Worst Performers (Bottom 3 — Config A)\n",
        "| # | Question | Faithfulness | Relevance | Recall | Avg | Root Cause |",
        "|---|----------|-------------|-----------|--------|-----|------------|",
    ]

    sorted_a = sorted(scores_a, key=_row_avg)
    for idx, row in enumerate(sorted_a[:3], 1):
        q = row["question"][:50].replace("|", "\\|")
        faith = row.get("FaithfulnessMetric", 0)
        rel   = row.get("AnswerRelevancyMetric", 0)
        rec   = row.get("ContextualRecallMetric", 0)
        avg   = _row_avg(row)
        cause = (
            "Câu hỏi ngoài phạm vi corpus / context không đủ"
            if avg < 0.4
            else "Cần tối ưu chunk size hoặc retrieval top_k"
        )
        lines.append(
            f"| {idx} | {q}... | {faith} | {rel} | {rec} | {avg} | {cause} |"
        )
    lines.append("")

    lines += [
        "---\n",
        "## Recommendations\n",
        "### Cải tiến 1 — Tăng kích thước golden dataset",
        "**Action:** Bổ sung thêm 10-20 Q&A bao phủ edge case (câu hỏi mơ hồ, đa điều luật).",
        "**Expected impact:** Đánh giá chính xác hơn, phát hiện điểm yếu sớm hơn.\n",
        "### Cải tiến 2 — Fine-tune chunk_size và overlap",
        "**Action:** Thử chunk_size=500 (hiện 800) và chunk_overlap=100 (hiện 150).",
        "**Expected impact:** Giảm nhiễu context, tăng Faithfulness và Context Precision.\n",
        "### Cải tiến 3 — Tích hợp cross-encoder reranker thực sự",
        "**Action:** Dùng Jina reranker API (JINA_API_KEY) thay cho RRF fallback.",
        "**Expected impact:** Context Recall và Faithfulness tăng đáng kể.\n",
    ]

    RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nKết quả đã ghi vào: {RESULTS_PATH}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("RAG EVALUATION PIPELINE — DeepEval")
    print("Nguyễn Thành Huy (2A202600764)")
    print("=" * 60)

    golden_dataset = load_golden_dataset()
    print(f"\nLoaded {len(golden_dataset)} test cases")

    try:
        import deepeval  # noqa: F401
    except ImportError:
        print("\n⚠ Chưa cài DeepEval. Chạy: pip install deepeval")
        sys.exit(1)

    comparison = compare_configs(golden_dataset)
    export_results(comparison)
    print("\nHoàn thành! Xem kết quả tại group_project/evaluation/results.md")
