# Bài Tập Nhóm — HHM Day 8 RAG Pipeline

## Thành Viên Nhóm

| Thành viên | MSSV | GitHub branch cá nhân |
|-----------|------|----------------------|
| Nguyễn Đức Hiếu | 2A202600680 | `personal/2A202600680-NguyenDucHieu` |
| Nguyễn Thành Huy | 2A202600764 | `personal/2A202600764-NguyenThanhHuy` |
| Hồ Đức Minh | 2A202600888 | `personal/2A202600888-HoDucMinh` |

---

## Cấu Trúc Thư Mục Nhóm

```
group_project/
├── app.py                        ← Hiếu làm (Chatbot UI)
├── requirements.txt              ← Hiếu làm
├── evaluation/
│   ├── golden_dataset.json       ← Huy làm (≥15 Q&A)
│   ├── eval_pipeline.py          ← Huy làm (chạy 4 metrics)
│   └── results.md                ← Minh làm (báo cáo A/B)
└── README.md                     ← Minh làm (cập nhật architecture + hướng dẫn chạy)
```

---

## Phân Công Chi Tiết

### Nguyễn Đức Hiếu — 2A202600680 | Chatbot UI & Integration

**Nhiệm vụ:**
- [ ] `group_project/app.py` — Xây dựng giao diện chat bằng Streamlit hoặc Chainlit
- [ ] Tích hợp `retrieve()` từ `task9_retrieval_pipeline.py` và `generate_with_citation()` từ `task10_generation.py`
- [ ] Conversation memory — lưu lịch sử chat, hỗ trợ follow-up questions
- [ ] Hiển thị source documents và relevance score trong UI
- [ ] `group_project/requirements.txt`

**Cách chạy sau khi xong:**
```bash
streamlit run group_project/app.py
# hoặc
chainlit run group_project/app.py
```

**Commit convention:**
```
feat(group/ui): <mô tả>
```

---

### Nguyễn Thành Huy — 2A202600764 | Golden Dataset & Evaluation

**Nhiệm vụ:**
- [ ] `group_project/evaluation/golden_dataset.json` — Tạo ≥15 cặp Q&A theo format:
```json
[
  {
    "question": "Hình phạt cho tội tàng trữ ma tuý là gì?",
    "expected_answer": "...",
    "expected_context": "..."
  }
]
```
- [ ] `group_project/evaluation/eval_pipeline.py` — Script chạy evaluation với **DeepEval hoặc RAGAS**
- [ ] Chạy đủ 4 metrics:
  - Faithfulness (câu trả lời có bám đúng context?)
  - Answer Relevance (câu trả lời có đúng câu hỏi?)
  - Context Recall (retriever có lấy đủ evidence?)
  - Context Precision (context có bao nhiêu % hữu ích?)

**Cài đặt:**
```bash
pip install deepeval
# hoặc
pip install ragas
```

**Commit convention:**
```
feat(group/eval): <mô tả>
```

---

### Hồ Đức Minh — 2A202600888 | A/B Comparison & Report

**Nhiệm vụ:**
- [ ] Chạy A/B comparison ≥2 configs (ví dụ: có reranking vs không reranking, hoặc hybrid vs dense-only)
- [ ] `group_project/evaluation/results.md` — Báo cáo gồm:
  - Bảng điểm metrics của từng config
  - Phân tích worst performers (câu hỏi nào trả lời kém nhất, tại sao)
  - Đề xuất cải tiến
- [ ] Cập nhật `group_project/README.md`:
  - Vẽ/mô tả architecture diagram
  - Hướng dẫn chạy app và eval pipeline

**Commit convention:**
```
feat(group/report): <mô tả>
docs(group): <mô tả>
```

---

## Quy Trình Làm Việc (Git Workflow)

### Bước 1 — Clone repo về máy
```bash
git clone https://github.com/dminhh/HHM-Day08.git
cd HHM-Day08
```

### Bước 2 — Tạo branch cá nhân và làm việc
```bash
git checkout main
git pull origin main
git checkout -b personal/<MSSV>-<TenKhongDau>
# Làm việc, commit thường xuyên
git add group_project/...
git commit -m "feat(group/...): mô tả"
git push origin personal/<MSSV>-<TenKhongDau>
```

### Bước 3 — Tạo Pull Request vào main
- Vào GitHub → New pull request
- Base: `main` ← Compare: `personal/<branch của bạn>`
- Nhắn nhóm review và merge

---

## Timeline

| Giai đoạn | Nội dung |
|-----------|----------|
| Ngay bây giờ | Mỗi người clone repo, tạo branch, bắt đầu làm |
| Sớm nhất có thể | Hiếu xong app.py để Huy + Minh test eval pipeline |
| Trước buổi trình bày | Merge tất cả vào main, test chạy được end-to-end |

---

## Điểm Số

| Tiêu chí | Điểm | Người phụ trách |
|----------|------|----------------|
| RAG Chatbot demo hoạt động | 8 | Hiếu |
| Tích hợp pipeline các thành viên | 4 | Hiếu |
| Kiến trúc rõ ràng + README | 3 | Minh |
| Chất lượng câu trả lời (citation, đúng nội dung) | 3 | Hiếu |
| Golden dataset ≥15 Q&A | 3 | Huy |
| Chạy eval ≥4 metrics | 4 | Huy |
| A/B comparison ≥2 configs + phân tích | 3 | Minh |
| Báo cáo worst performers | 2 | Minh |
| **Tổng** | **30** | |
