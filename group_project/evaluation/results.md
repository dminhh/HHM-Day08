# RAG Evaluation Results

## Framework sử dụng

DeepEval

---

## Overall Scores

| Metric | Config A (hybrid + rerank) | Config B (no rerank) | Δ |
|--------|---------------------------|----------------------|---|
| Faithfulness | 0.9867 | 0.9733 | +0.0134 |
| Answer Relevance | 0.8011 | 0.8079 | -0.0068 |
| Context Recall | 0.6444 | 0.6556 | -0.0112 |
| Context Precision | 0.8111 | 0.8133 | -0.0022 |
| **Average** | **0.8108** | **0.8125** | **-0.0017** |

---

## A/B Comparison Analysis

**Config A — Hybrid search (dense + BM25) + Reranking (RRF/MMR):**
> Kết hợp semantic search (ChromaDB cosine) và BM25, sau đó rerank bằng RRF + MMR để đưa chunk liên quan nhất lên đầu.

**Config B — Hybrid search, không reranking:**
> Chỉ dùng RRF merge từ dense + sparse, bỏ bước rerank. Nhanh hơn nhưng thứ tự chunk kém tối ưu.

**Kết luận:**
> Config B cho điểm trung bình cao hơn (0.8108 vs 0.8125). Bước reranking không cải thiện chất lượng truy xuất so với pipeline không rerank.

---

## Worst Performers (Bottom 3 — Config A)

| # | Question | Faithfulness | Relevance | Recall | Avg | Root Cause |
|---|----------|-------------|-----------|--------|-----|------------|
| 1 | Danh mục các chất ma tuý thuộc nhóm I theo quy địn... | 0 | 0 | 0 | 0.25 | Câu hỏi ngoài phạm vi corpus / context không đủ |
| 2 | Người từ đủ 12 đến dưới 18 tuổi nghiện ma tuý bị á... | 0 | 0 | 0 | 0.4 | Cần tối ưu chunk size hoặc retrieval top_k |
| 3 | Trách nhiệm của gia đình trong công tác phòng chốn... | 0 | 0 | 0 | 0.7292 | Cần tối ưu chunk size hoặc retrieval top_k |

---

## Recommendations

### Cải tiến 1 — Tăng kích thước golden dataset
**Action:** Bổ sung thêm 10-20 Q&A bao phủ edge case (câu hỏi mơ hồ, đa điều luật).
**Expected impact:** Đánh giá chính xác hơn, phát hiện điểm yếu sớm hơn.

### Cải tiến 2 — Fine-tune chunk_size và overlap
**Action:** Thử chunk_size=500 (hiện 800) và chunk_overlap=100 (hiện 150).
**Expected impact:** Giảm nhiễu context, tăng Faithfulness và Context Precision.

### Cải tiến 3 — Tích hợp cross-encoder reranker thực sự
**Action:** Dùng Jina reranker API (JINA_API_KEY) thay cho RRF fallback.
**Expected impact:** Context Recall và Faithfulness tăng đáng kể.
