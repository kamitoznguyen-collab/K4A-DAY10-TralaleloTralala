# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | Lại Bá Quân |
| **MSSV** | 2A202602495 |
| **Khóa / Lớp** | K4A-DAY10 |
| **Tên nhóm** | Tralalelo Tralala |
| **Vai trò chính** | Pipeline Integrator (`core/`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`) |
| **Repository** | https://github.com/kamitoznguyen-collab/K4A-DAY10-TralaleloTralala |
| **Ngày cập nhật** | 2026-09-25 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu chính
- **Điều phối toàn tuyến Baseline Pipeline (Checkpoint 3):**
  - Hiện thực hóa toàn bộ module `src/pipelines/phase1.py` theo đúng kiến trúc end-to-end được định nghĩa trong pseudo-code và tài liệu kỹ thuật.
  - Kết nối liên thông các mắt xích công việc: Ingestion (`crossref.py`) $\rightarrow$ Cleaning (`cleaning.py`) $\rightarrow$ Vector Indexing (`retrieval/index.py`) $\rightarrow$ Test Set (`testset.py`) $\rightarrow$ Evaluation (`metrics.py`) $\rightarrow$ Observability Gate & Freshness SLA (`quality.py`) $\rightarrow$ Baseline Report (`reporting.py`).
  - Đảm bảo entrypoint `python script/run_phase1.py` chạy trơn tru với exit code 0.

- **Điều phối toàn tuyến Corruption Flow & Idempotent Repair (Checkpoint 5):**
  - Hiện thực hóa module `src/pipelines/corruption_flow.py` và script thực thi `script/run_corruption_flow.py`.
  - Kết hợp bộ công cụ tiêm 6 lỗi dữ liệu của Lan (`src/ingestion/corruption.py`) để đo lường định lượng mức độ suy thoái (Silent Failure) của hệ thống RAG và kích hoạt cảnh báo từ Great Expectations 1.x & Freshness SLA.
  - Xây dựng cơ chế **Idempotent Self-Healing / Repair**: tái cấu trúc dữ liệu sạch từ nguồn raw snapshot tin cậy (`crossref_records.json`), tái lập chỉ mục ChromaDB (`papers-repaired`) và chứng minh độ phục hồi 100%.
  - Tích hợp hàm `generate_corruption_report()` của Khánh để xuất bản báo cáo đối chiếu 3 trạng thái tại `data/reports/corruption_report.md`.
  - Đảm bảo tính Idempotent: chạy nhiều lần vẫn ra đúng kết quả phục hồi tối ưu giống hệt nhau.

### Bảng phân định trách nhiệm chi tiết (CP3 & CP5)

| Module / Deliverable | File / Hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :---: |
| **Baseline Pipeline (CP3)** | `src/pipelines/phase1.py`<br>`run_phase1()`, `main()` | `Settings` cấu hình, snapshot `crossref_records.json` | 10 artifacts dữ liệu, metrics, reports sạch | **Hoàn thành 100%** |
| **Baseline Entrypoint** | `script/run_phase1.py` | Command line CLI | Chạy trơn tru không lỗi (Exit code 0) | **Hoàn thành 100%** |
| **Corruption Flow & Repair (CP5)** | `src/pipelines/corruption_flow.py`<br>`run_corruption_flow()`, `main()` | Baseline artifacts, raw snapshot | Ma trận so sánh 3 trạng thái, các artifacts corrupted & repaired | **Hoàn thành 100%** |
| **Corruption Entrypoint** | `script/run_corruption_flow.py` | Command line CLI | Chạy trơn tru không lỗi (Exit code 0) | **Hoàn thành 100%** |
| **3-State Comparison Report** | `src/observability/reporting.py`<br>`generate_corruption_report()` | 3-state metrics, quality & freshness dicts | `data/reports/corruption_report.md` | **Hoàn thành 100%** |

---

## 3. Kết quả bàn giao Checkpoint 3 (CP3)

### Tín hiệu nghiệm thu thực tế CP3
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

---

## 4. Kết quả bàn giao Checkpoint 5 (CP5)

### Tín hiệu nghiệm thu thực tế CP5
Khi chạy lệnh:
```bash
python script/run_corruption_flow.py
```
Console in ra ma trận so sánh 3 trạng thái rõ ràng và ấn tượng:
```text
================================================================================
  DATA OBSERVABILITY & 3-STATE COMPARISON MATRIX (CP5)
================================================================================
  Metric / Indicator           | Baseline       | Corrupted      | Repaired      
  ----------------------------------------------------------------------------
  Record Count                 | 24             | 22             | 24            
  GX 1.x Quality Gate          | PASSED         | FAILED (Alarm) | PASSED        
  Freshness SLA (180d)         | COMPLIANT      | VIOLATED       | COMPLIANT     
  Retrieval Hit Rate           | 100.0%         | 80.0%          | 100.0%        
  Answer Mean Token F1         | 1.0000         | 0.9741         | 1.0000        
  LLM Judge Accuracy           | 100.0%         | 100.0%         | 100.0%        
================================================================================
  [CP5] IDEMPOTENT REPAIR VERIFIED: REPAIRED STATE 100% RECOVERS BASELINE PERFORMANCE
================================================================================
```

### Bảng đối chiếu định lượng chi tiết 3 trạng thái

| Chỉ số / Trụ cột kiểm tra | 1. Baseline (Sạch) | 2. Corrupted (Tiêm lỗi) | 3. Repaired (Phục hồi) | Mức độ phục hồi |
| :--- | :---: | :---: | :---: | :---: |
| **Số lượng bản ghi** | 24 dòng | 22 dòng (drop/dup) | 24 dòng | 🟢 Khôi phục 100% |
| **Data Quality Gate (GX 1.x)** | **✅ PASSED** (7/7) | **❌ FAILED** (Báo động đỏ) | **✅ PASSED** (7/7) | 🟢 Khôi phục 100% |
| **Freshness SLA (<25% stale)** | **✅ COMPLIANT** (4.2%) | **⚠️ VIOLATED** (27.3%) | **✅ COMPLIANT** (4.2%) | 🟢 Chuẩn hóa hoàn toàn |
| **Retrieval Hit Rate** | **100.0%** | **80.0%** (Suy giảm 20%) | **100.0%** | 🟢 Khôi phục 100% |
| **Answer Mean Token F1** | **1.0000** | **0.9741** (Suy giảm) | **1.0000** | 🟢 Khôi phục 100% |
| **LLM Judge Accuracy** | **100.0%** | **100.0%** | **100.0%** | 🟢 Duy trì ổn định |

### Danh mục Artifacts đã sinh ra cho CP5

| STT | Tên Artifact | Vị trí file | Ý nghĩa kỹ thuật |
| :-: | :--- | :--- | :--- |
| 1 | `corruption_log.json` | `data/results/corruption_log.json` | Nhật ký chi tiết 6 loại lỗi đã tiêm vào dữ liệu |
| 2 | `papers_clean_corrupted.csv` | `data/clean/papers_clean_corrupted.csv` | File CSV chứa dữ liệu sau khi bị tiêm lỗi |
| 3 | `papers_clean_corrupted.json` | `data/clean/papers_clean_corrupted.json` | Dữ liệu lỗi định dạng JSON |
| 4 | `corrupted_metrics.json` | `data/results/corrupted_metrics.json` | Đo lường sụt giảm: Hit Rate 80.0%, F1 0.9741 |
| 5 | `corrupted_quality_report.json` | `data/quality/corrupted_quality_report.json` | GX 1.x bắt lỗi thành công (`success: false`) |
| 6 | `corrupted_freshness_report.json`| `data/quality/corrupted_freshness_report.json`| Cảnh báo vi phạm SLA độ tươi mới |
| 7 | `papers_clean_repaired.csv` | `data/clean/papers_clean_repaired.csv` | Dữ liệu sau khi phục hồi sạch hoàn toàn |
| 8 | `papers_clean_repaired.json` | `data/clean/papers_clean_repaired.json` | Dữ liệu phục hồi định dạng JSON |
| 9 | `repaired_metrics.json` | `data/results/repaired_metrics.json` | Đo lường phục hồi: Hit Rate 100.0%, F1 1.0000 |
| 10 | `repaired_quality_report.json` | `data/quality/repaired_quality_report.json` | GX 1.x nghiệm thu đạt chuẩn (`success: true`) |
| 11 | `repaired_freshness_report.json`| `data/quality/repaired_freshness_report.json`| SLA độ tươi mới trở về mức an toàn (4.2%) |
| 12 | `corruption_report.md` | `data/reports/corruption_report.md` | Báo cáo Markdown đối chiếu 3 trạng thái hoàn chỉnh |

---

## 5. Giải thích phần kỹ thuật đã thực hiện

### Hiện tượng Silent Failure & Ý nghĩa của Chốt kiểm soát
1. **Hiện tượng Silent Failure:** Khi dữ liệu bị tiêm 6 lỗi (cắt ngắn tiêu đề, xóa rỗng summary, nhồi ký tự rác, lùi ngày, nhân bản dòng), toàn bộ quy trình nhúng vector ChromaDB và LLM vẫn chạy trơn tru mà không hề văng Exception. Tuy nhiên, chất lượng tìm kiếm bị suy giảm trầm trọng (Retrieval Hit Rate sụt từ 100% xuống 80%). Nếu không có Data Observability, lỗi này sẽ âm thầm lọt vào môi trường sản xuất.
2. **Vai trò của GX 1.x & Freshness SLA:** Ngay khi dữ liệu bẩn xuất hiện, Quality Gate Great Expectations 1.x lập tức báo động đỏ (`success: false`) và Freshness Monitor phát hiện tỷ lệ bài báo cũ vượt trần 25% (`is_fresh: false`), chặn đứng dữ liệu bẩn trước khi người dùng cuối bị ảnh hưởng.
3. **Cơ chế Idempotent Repair:** Tự động kích hoạt luồng tái tạo dữ liệu từ snapshot thô bất biến (`crossref_records.json`). Quá trình này có tính chất **Idempotent** (chạy $N$ lần vẫn cho ra cùng một trạng thái nhất quán), xóa bỏ hoàn toàn dữ liệu bẩn và phục hồi Retrieval Hit Rate về mức 100%.

---

## 6. Kế hoạch tiếp theo (CP6)

- [x] **Hoàn thiện CP3:** Baseline Pipeline chạy trơn tru (`run_phase1.py`), sinh đầy đủ artifacts và báo cáo baseline.
- [x] **Hoàn thiện CP5:** Corruption Flow & Idempotent Repair chạy trơn tru (`run_corruption_flow.py`), xuất bảng đối chiếu 3 trạng thái và chứng minh phục hồi 100%.
- [ ] **CP6: Live Demo trên bảng:** Sẵn sàng trình chiếu trực tiếp `run_phase1.py`, `run_corruption_flow.py` và giải trình cơ chế Idempotent Self-healing trước Giảng viên và lớp.
