# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Tralalelo Tralala`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3-DAY10-Tralalelo Tralala-DataPipeline`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Quân | | | Trưởng nhóm / Pipeline Integrator (`core/`, `phase1.py`, `corruption_flow.py`) | `report/quan_report.md` |
| 2 | Việt Anh | | | Data Ingestion & Cleaning (`crossref.py`, `cleaning.py`, raw data) | `report/vietanh_report.md` |
| 3 | Huy | | | RAG & Vector Index (`retrieval/index.py`, `testset.py`, ChromaDB) | `report/huy_report.md` |
| 4 | Nguyễn Khánh | | nguynkhanh57.9@gmail.com | Data Observability & Reporting (`quality.py` GX 1.x, `reporting.py`, Dashboard) | `report/khanh_report.md` |
| 5 | Lan | | | Corruption Suite & Testing (`corruption.py`, `tests/`) | `report/lan_report.md` |

*(Nếu nhóm có 3 hoặc 5-6 thành viên, xem bảng phân công chi tiết theo vai trò trong file `CHECKPOINTS.md`)*.

---

## # Cá nhân

### ## HoVaTen1-MSSV1
- **Vai trò:** Trưởng nhóm & Điều phối Pipeline.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình hệ thống `core/config.py` và đường dẫn artifacts `core/utils.py`.
  - Kết nối luồng thực thi trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Kiểm tra tính nhất quán của các artifacts và theo dõi Contributor tracking trên GitHub nhánh `main`.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc về thiết kế Idempotent Pipeline và quản lý trạng thái luồng dữ liệu đa tầng.

### ## HoVaTen2-MSSV2
- **Vai trò:** Phụ trách Ingestion, Làm sạch & Phục hồi dữ liệu.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API với cơ chế Fallback offline trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema, tính toán trường `age_days` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Thực thi cơ chế Idempotent Repair phục hồi dữ liệu từ raw snapshot.
- **Điều học được / Đóng góp chính:**
  - Kỹ thuật truy vết nguồn gốc dữ liệu (Data Lineage) và bảo toàn raw snapshot trước khi biến đổi.

### ## HoVaTen3-MSSV3
- **Vai trò:** Phụ trách RAG, Vector Database & Embedding.
- **Công việc chi tiết đã hoàn thành:**
  - Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2`.
  - Nạp và quản lý 3 collection riêng biệt trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
  - Xây dựng QA Agent truy vấn ngữ cảnh chính xác theo tài liệu.
- **Điều học được / Đóng góp chính:**
  - Cách cô lập các không gian vector để so sánh khách quan giữa dữ liệu sạch và dữ liệu bị lỗi.

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
