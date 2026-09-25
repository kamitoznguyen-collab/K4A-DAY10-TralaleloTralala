# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin                 | Nội dung                                                                                          |
| :------------------------- | :------------------------------------------------------------------------------------------------- |
| **Họ và tên**     | Lại Bá Quân                                                                                     |
| **MSSV**             | 2A202602495                                                                                        |
| **Khóa / Lớp**     | K4A-DAY10                                                                                          |
| **Tên nhóm**       | Tralalelo Tralala                                                                                  |
| **Vai trò chính**  | Pipeline Integrator (`core/`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`) |
| **Repository**       | https://github.com/kamitoznguyen-collab/K4A-DAY10-TralaleloTralala                                 |
| **Ngày cập nhật** | 2026-09-25                                                                                         |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu chính

- **Điều phối toàn tuyến Baseline Pipeline (Checkpoint 3):**
  - Hiện thực hóa toàn bộ module `src/pipelines/phase1.py` theo đúng kiến trúc end-to-end được định nghĩa trong pseudo-code và tài liệu kỹ thuật.
  - Kết nối liên thông các mắt xích công việc từ các thành viên khác:
    - **Việt Anh (Ingestion & Cleaning):** Nạp `crossref_records.json` (hoặc fetch fallback), làm sạch dữ liệu thành DataFrame 24 dòng có `text_for_embedding` và `age_days`.
    - **Huy (Retrieval & Benchmark):** Đánh chỉ mục ChromaDB `papers-baseline` và sinh tập testset 10 câu hỏi (`test_set.json`).
    - **Khánh (Observability & Reporting):** Kích hoạt Data Quality Gate Great Expectations 1.x (`baseline_quality_report.json`), kiểm tra Freshness SLA (`freshness_report.json`), và xuất báo cáo markdown `data/reports/phase1_report.md`.
  - Đảm bảo entrypoint `python script/run_phase1.py` chạy trơn tru với exit code 0.

### Bảng phân định trách nhiệm liên quan đến CP3

| Module / Deliverable              | File / Hàm phụ trách                             | Input nhận vào                                            | Output bàn giao                               |        Trạng thái        |
| :-------------------------------- | :-------------------------------------------------- | :---------------------------------------------------------- | :--------------------------------------------- | :-------------------------: |
| **Baseline Pipeline (CP3)** | `src/pipelines/phase1.pyrun_phase1()`, `main()` | `Settings` cấu hình, snapshot `crossref_records.json` | 10 artifacts dữ liệu, metrics, reports sạch | **Hoàn thành 100%** |
| **Entrypoint script**       | `script/run_phase1.py`                            | Command line CLI                                            | Chạy trơn tru không lỗi (Exit code 0)      | **Hoàn thành 100%** |
| **Demo Agent Output**       | `src/retrieval/agent.pyrun_agent_question()`      | Clean Index, sample questions                               | `data/results/agent_demo_answers.json`       | **Hoàn thành 100%** |

---

## 3. Kết quả bàn giao Checkpoint 3 (CP3)

### Tín hiệu nghiệm thu thực tế

Khi chạy lệnh:

```bash
python script/run_phase1.py
```

Kết quả console in ra thành công:

```text
======================================================================
  DAY 10 — PHASE 1: BASELINE PIPELINE (CP3)
======================================================================
[CP3] [1/8] Ingestion: 24 raw records loaded from Local Raw Snapshot (Fallback).
[CP3] [2/8] Cleaning: 24 records cleaned (5-part text_for_embedding, age_days).
[CP3] [3/8] Artifacts: Saved clean CSV to 'data/clean/papers_clean.csv' and JSON to 'data/clean/papers_clean.json'.
[CP3] [4/8] Indexing: Building ChromaDB vector collection 'papers-baseline'...
[CP3]       ChromaDB collection 'papers-baseline' indexed with 24 documents.
[CP3] [5/8] Test Set: Generated 10 benchmark questions at 'data/eval/test_set.json'.
[CP3] [6/8] Evaluation: Running evaluation over 10 test questions...
[CP3]       Baseline Metrics: Retrieval Hit Rate = 100.0%, Token F1 = 1.0000, Judge Accuracy = 100.0%
[CP3] [7/8] Observability: Executing Great Expectations 1.x Quality Gate & Freshness SLA...
[CP3]       GX 1.x Quality Gate: PASSED (Success = True)
[CP3]       Freshness SLA: COMPLIANT (Stale ratio: 4.2%)
[CP3] [8/8] Report: Baseline report generated at 'data/reports/phase1_report.md'.
======================================================================
  [CP3] PHASE 1 BASELINE PIPELINE COMPLETED SUCCESSFULLY! (Exit Code 0)
======================================================================
```

### Danh mục Artifacts đã sinh ra đầy đủ

| STT | Tên Artifact           | Vị trí file                                 | Ý nghĩa / Giá trị thực tế                                |
| :-: | :---------------------- | :-------------------------------------------- | :------------------------------------------------------------- |
|  1  | `papers_clean.csv`    | `data/clean/papers_clean.csv`               | Dữ liệu sạch 24 dòng, 16 cột chuẩn hóa                  |
|  2  | `papers_clean.json`   | `data/clean/papers_clean.json`              | Dữ liệu sạch format JSON records                            |
|  3  | `ChromaDB Index`      | `data/chroma/`                              | Vector database chứa collection`papers-baseline`            |
|  4  | `Embeddings Manifest` | `data/embeddings/papers_embeddings.json`    | Manifest index lưu relative path portable                     |
|  5  | `Test Set`            | `data/eval/test_set.json`                   | 10 câu hỏi benchmark đa dạng 4 nhóm                       |
|  6  | `Baseline Metrics`    | `data/results/baseline_metrics.json`        | `retrieval_hit_rate: 1.0`, `mean_token_f1: 1.0`            |
|  7  | `Baseline Answers`    | `data/results/baseline_answers.json`        | Toàn bộ câu trả lời, contexts và judge score             |
|  8  | `Quality Report`      | `data/quality/baseline_quality_report.json` | GX 1.x Ephemeral: 7/7 expectations passed (`success: true`)  |
|  9  | `Freshness Report`    | `data/quality/freshness_report.json`        | Freshness SLA compliant (`is_fresh: true`, stale ratio 4.2%) |
| 10 | `Phase 1 Report`      | `data/reports/phase1_report.md`             | Báo cáo Markdown tổng hợp chi tiết toàn bộ Phase 1      |
| 11 | `Agent Demo Answers`  | `data/results/agent_demo_answers.json`      | Câu trả lời thử nghiệm của Agent RAG                     |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### 10 Bước triển khai trong `src/pipelines/phase1.py`

1. **Khởi tạo & Cấu hình:** Nạp `load_settings()`, xác định môi trường và đường dẫn lưu trữ.
2. **Ingestion an toàn (Resilient Ingestion):** Tự động phát hiện snapshot offline `crossref_records.json` để tránh lỗi `429 Too Many Requests` khi chạy nhiều lần, đồng thời sẵn sàng gọi live API khi `refresh_source=True`.
3. **Data Cleaning:** Tính toán `age_days` so với thời điểm chạy và cấu trúc 5 tầng `text_for_embedding` (Title, Authors, Published, Categories, Summary).
4. **Bảo tồn Dữ liệu:** Ghi nhận cả định dạng CSV lẫn JSON với UTF-8 encoding.
5. **ChromaDB Indexing:** Khởi tạo `LocalEmbeddingIndex`, sử dụng mô hình embedding chuẩn `all-MiniLM-L6-v2`, lập chỉ mục không gian Cosine HNSW.
6. **Benchmark Test Set:** Sinh bộ test 10 câu phủ 4 dạng nghiệp vụ (Summary, Authors, Date, Categories).
7. **RAG Evaluation:** Tính toán Retrieval Hit Rate, Token F1 và tích hợp LLM Judge (Gemini/structured output) đánh giá câu trả lời tự động.
8. **Data Quality Gate:** Tích hợp Great Expectations 1.x ephemeral mode kiểm định 4 quy tắc cốt lõi (row count 20-30, non-null, uniqueness, length).
9. **Freshness SLA:** Kiểm tra tỷ lệ dữ liệu cũ quá 180 ngày so với trần 25%.
10. **Báo cáo Markdown:** Gọi `generate_phase1_report()` từ module của Khánh để xuất bản artifact hoàn chỉnh.

---

## 5. Nhiệm vụ tiếp theo

- [X] **Hoàn thiện CP3:** `phase1.py`, `script/run_phase1.py`, sinh đủ 10 artifacts baseline.
- [ ] **Hoàn thiện CP5:** Triển khai `src/pipelines/corruption_flow.py` và `script/run_corruption_flow.py`, kiểm chứng tính Idempotent Repair và xuất báo cáo đối chiếu 3 trạng thái `data/reports/corruption_report.md`.
- [ ] **Dẫn Live Demo CP6:** Trình diễn luồng phục hồi dữ liệu trực tiếp trước Giảng viên và lớp.
