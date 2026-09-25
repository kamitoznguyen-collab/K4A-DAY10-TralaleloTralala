# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Tralalelo Tralala`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3-DAY10-Tralalelo Tralala-DataPipeline`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Huy | | | Trưởng nhóm · RAG & Vector Index (`retrieval/index.py`, `testset.py`, ChromaDB), review & merge PR | `report/huy_report.md` |
| 2 | Quân | | | Pipeline Integrator (`core/`, `phase1.py`, `corruption_flow.py`) | `report/quan_report.md` |
| 3 | Việt Anh | | | Data Ingestion & Cleaning (`crossref.py`, `cleaning.py`, raw data) | `report/vietanh_report.md` |
| 4 | Nguyễn Khánh | | nguynkhanh57.9@gmail.com | Data Observability & Reporting (`quality.py` GX 1.x, `reporting.py`, Dashboard) | `report/khanh_report.md` |
| 5 | Lan | | | Corruption Suite & Testing (`corruption.py`, `tests/` pytest) | `report/Lan.md` |

*(Mỗi thành viên tự điền MSSV, email và phần cá nhân của mình bên dưới; mọi người phải có commit trên `main`.)*

---

## # Cá nhân

### ## Huy
- **Vai trò:** Trưởng nhóm · Phụ trách RAG, Vector Database & Benchmark Test Set.
- **Công việc chi tiết đã hoàn thành:**
  - Phân công công việc, theo dõi tiến độ các nhánh, review & merge PR vào `main`.
  - Xây dựng bộ 10 câu hỏi benchmark (đủ 4 loại `summary` / `authors` / `date` / `categories`) trong `src/evaluation/testset.py`.
  - Sửa manifest index lưu `persist_path` tương đối trong `src/retrieval/index.py` để chạy được trên máy khác.
  - Kiểm tra ChromaDB `papers-baseline` đủ 24 docs, baseline `retrieval_hit_rate = 1.0`; kiểm tra `agent.py` với provider `mock`.
- **Điều học được / Đóng góp chính:**
  - _(tự điền)_

### ## Quân
- **Vai trò:** Pipeline Integrator.
- **Công việc chi tiết đã hoàn thành:**
  - Kết nối luồng thực thi trong `src/pipelines/phase1.py` (CP3) và `src/pipelines/corruption_flow.py` (CP5), repair bằng cách clean lại từ raw snapshot.
  - Đảm bảo idempotent: chạy `run_corruption_flow.py` 2 lần cho `repaired_metrics.json` giống hệt nhau.
  - Dẫn live demo CP6.
- **Điều học được / Đóng góp chính:**
  - _(tự điền)_

### ## Việt Anh
- **Vai trò:** Phụ trách Ingestion, Làm sạch & Phục hồi dữ liệu.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API với cơ chế Fallback offline trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema, tính toán trường `age_days` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Hỗ trợ cơ chế Idempotent Repair phục hồi dữ liệu từ raw snapshot.
- **Điều học được / Đóng góp chính:**
  - _(tự điền)_

### ## Khánh - Phụ trách Data Observability & Reporting
- **Vai trò:** Data Observability & Reporting Lead (`src/observability/`).
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate theo chuẩn mới **Great Expectations 1.x** (ephemeral context, 4 expectations: row count, non-null, unique, length constraints) trong `src/observability/quality.py`.
  - Xây dựng cơ chế giám sát Freshness SLA (ngưỡng 180 ngày, giới hạn stale ratio <= 25%) trong `build_freshness_report()`.
  - Hoàn thiện module báo cáo `src/observability/reporting.py`: sinh báo cáo Baseline `phase1_report.md` và báo cáo đối chiếu 3 trạng thái `corruption_report.md` (Baseline vs Corrupted vs Repaired).
  - Xây dựng Web Dashboard trực quan (Bonus B1: `src/observability/dashboard.py` & `script/run_dashboard.py`) hiển thị ma trận 3 trạng thái, phân bố độ tuổi bài báo và tình trạng Data Quality theo thời gian thực.
  - Viết báo cáo cá nhân chi tiết tại `report/khanh_report.md`.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc hiện tượng Silent Failure trong các hệ thống RAG/AI: LLM vẫn tự tin trả lời sai khi dữ liệu bị lỗi nếu không có chốt kiểm soát dữ liệu Data Observability chặn lại trước Vector Database.
  - Kỹ thuật triển khai Ephemeral Context của Great Expectations 1.x kết hợp Freshness SLA để kiểm soát chất lượng dữ liệu end-to-end.

### ## Lan
- **Vai trò:** Phụ trách Corruption Suite & Unit Testing.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng 6 kịch bản làm hỏng dữ liệu chủ động trong `src/ingestion/corruption.py`.
  - Cấu hình và viết test suite toàn diện (`CP0`, `CP1`, `CP2`, `CP4`) với `pytest` không phụ thuộc vào code đồng đội bằng `conftest.py` độc lập.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu về cách dữ liệu có thể bị thoái hóa ngầm mà không gây lỗi runtime. Thành thạo kỹ năng TDD (Test-Driven Development) và fixture mock trong dự án thực tế.
