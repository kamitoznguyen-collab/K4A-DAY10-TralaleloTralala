# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo cá nhân dành cho thành viên phụ trách **Data Observability & Reporting** (Khánh).  
> Mã nhóm: `K4-L3-DAY10` — Tên nhóm: `Tralalelo Tralala`

---

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | Nguyễn Khánh |
| **MSSV** | [Điền MSSV của bạn vào đây] |
| **Email** | nguynkhanh57.9@gmail.com |
| **Khóa / Lớp** | K4A / K4-L3-DAY10 |
| **Tên nhóm** | Tralalelo Tralala |
| **Vai trò chính** | Data Observability & Reporting Lead (`src/observability/`) |
| **Repository** | `K4-L3-DAY10-Tralalelo Tralala-DataPipeline` |
| **Ngày hoàn thành** | 2026-09-25 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu chính (Ownership)

| Module / Deliverable | File / Hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :---: |
| **Data Quality Gate (GX 1.x)** | `src/observability/quality.py`<br>`run_data_quality_checks()` | `df: pd.DataFrame`, `settings: Settings`, `report_name: str` | Dict kết quả kiểm định + JSON artifact lưu tại `data/quality/<report_name>.json` | **Hoàn thành 100%** |
| **Freshness SLA Monitoring** | `src/observability/quality.py`<br>`build_freshness_report()` | `df: pd.DataFrame`, `settings: Settings`, `report_path: Path` | Dict chỉ số Freshness (`is_fresh`, `stale_ratio`) + JSON artifact lưu tại `data/quality/*.json` | **Hoàn thành 100%** |
| **Phase 1 Baseline Report** | `src/observability/reporting.py`<br>`generate_phase1_report()` | `source_summary`, `metrics`, `quality`, `freshness` | Báo cáo Markdown chi tiết tại `data/reports/phase1_report.md` | **Hoàn thành 100%** |
| **3-State Corruption Report** | `src/observability/reporting.py`<br>`generate_corruption_report()` | 3-state metrics (`baseline`, `corrupted`, `repaired`), 3-state quality & freshness | Báo cáo Markdown đối chiếu tại `data/reports/corruption_report.md` | **Hoàn thành 100%** |
| **Bonus B1: Observability Dashboard** | `src/observability/dashboard.py`<br>`script/run_dashboard.py` | JSON artifacts từ `data/quality/`, `data/results/`, `data/reports/` | Web Dashboard trực quan (KPI, 3-state matrix, age drift chart, report reader) | **Hoàn thành 100% (Bonus +5đ)** |

### Việc hỗ trợ ngoài phạm vi chính
- **Hỗ trợ Quân (Integrator):** Cung cấp API contract chuẩn cho `phase1.py` và `corruption_flow.py` để tích hợp `run_data_quality_checks()`, `build_freshness_report()`, `generate_phase1_report()`, `generate_corruption_report()` không bị xung đột schema.
- **Hỗ trợ Lan (Corruption):** Xác định ngưỡng kiểm tra GX (ví dụ: `min_value=20` để bắt lỗi drop 20% records; `min_value=30` trên `summary` để bắt rác/rỗng; `min_value=8` trên `title` để bắt title bị cắt ngắn; `is_unique` trên `paper_id` để bắt duplicates) nhằm bảo đảm 100% các dạng lỗi tiêm vào đều bị bắt chính xác.
- **Hỗ trợ Huy (Evaluation):** Tích hợp và hiển thị các chỉ số benchmark RAG (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`) lên bảng so sánh đối đầu và biểu đồ trực quan.

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File / Hàm / Artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| **Triển khai GX 1.x Ephemeral Gate** | `src/observability/quality.py`<br>`run_data_quality_checks` | Chốt kiểm soát 4 expectations chuẩn GX 1.x, không dùng API cũ | Chạy trên df sạch ra `success=True`, chạy trên df lỗi ra `success=False` |
| **Thiết lập giám sát Freshness SLA** | `src/observability/quality.py`<br>`build_freshness_report` | Giám sát ngưỡng 180 ngày, ngưỡng cảnh báo vi phạm `stale_ratio > 0.25` | Baseline đạt `is_fresh=True`, corrupted (lùi ngày) ra `is_fresh=False` |
| **Sinh báo cáo Phase 1 chuẩn hóa** | `src/observability/reporting.py`<br>`generate_phase1_report` | Markdown report chứa Ingestion, Quality, Freshness và Baseline RAG metrics | `data/reports/phase1_report.md` sinh đầy đủ các bảng dữ liệu |
| **Sinh báo cáo đối chiếu 3 trạng thái** | `src/observability/reporting.py`<br>`generate_corruption_report` | Bảng so sánh 3 cột: Baseline vs Corrupted vs Repaired kèm phân tích sâu sắc | `data/reports/corruption_report.md` có đầy đủ delta và phân tích Silent Failure |
| **Xây dựng Interactive Dashboard** | `src/observability/dashboard.py`<br>`script/run_dashboard.py` | Web UI trực quan, phục vụ bảo vệ live demo trước Giảng viên | Chạy `python script/run_dashboard.py`, truy cập `http://127.0.0.1:8501` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Silent Failure trong hệ thống AI / RAG:** Khi dữ liệu bị lỗi (mất bài mới, tiêu đề bị cắt, tóm tắt rỗng, ký tự rác), mô hình Vector Search và LLM vẫn thực thi bình thường mà không hề quăng Exception. Hậu quả là AI đưa ra câu trả lời sai lệch hoặc ảo giác (hallucination) với mức độ tự tin cao.
2. **Khấu hao độ tươi mới (Data Staleness):** Dữ liệu học thuật cũ quá 180 ngày nếu chiếm tỷ trọng lớn (>25%) sẽ làm giảm giá trị thực tiễn của hệ thống hỏi đáp.
3. **Tính Idempotent & Proof of Recovery:** Cần chứng minh định lượng rằng sau khi kích hoạt cơ chế sửa chữa (Idempotent Repair), toàn bộ chỉ số chất lượng dữ liệu và năng lực của RAG Agent được khôi phục 100% về mức baseline.

### Cách triển khai kỹ thuật
1. **Cấu hình Great Expectations 1.x (mode="ephemeral"):**
   Sử dụng API mới nhất của GX 1.x, tạo nguồn dữ liệu và tài sản dữ liệu trực tiếp trong bộ nhớ RAM, tránh việc lưu cấu hình thừa thãi:
   ```python
   context = gx.get_context(mode="ephemeral")
   data_source = context.data_sources.add_pandas(name=f"papers_source_{clean_name}")
   data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{clean_name}")
   batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
   batch = batch_def.get_batch(batch_parameters={"dataframe": df})
   ```
2. **Bộ 4 Expectations cốt lõi:**
   - `ExpectTableRowCountToBeBetween(min_value=20, max_value=30)`: Bắt sự cố drop mất 20% bản ghi (tụt xuống ~19 dòng).
   - `ExpectColumnValuesToNotBeNull(column=col)`: Cho các cột `paper_id`, `title`, `text_for_embedding`.
   - `ExpectColumnValuesToBeUnique(column="paper_id")`: Bắt lỗi tiêm bản ghi trùng lặp (duplicate DOI).
   - `ExpectColumnValueLengthsToBeBetween`: Bắt tóm tắt rỗng/ngắn (`summary` tối thiểu 30 ký tự) và tiêu đề bị cắt cụt (`title` tối thiểu 8 ký tự).
3. **Công thức Freshness SLA:**
   - Tính toán `stale_count` là số bản ghi có `age_days > 180` (sử dụng `pd.to_numeric` an toàn ép kiểu).
   - `stale_ratio = stale_count / total_rows`.
   - SLA Decision: `is_fresh = bool(stale_ratio <= 0.25)`.
4. **Báo cáo đối chiếu 3 trạng thái:**
   Tính toán delta độ lệch giữa Corrupted và Baseline để minh chứng sự suy thoái, sau đó đối chiếu với trạng thái Repaired để khẳng định năng lực tự chữa lành.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn giữa Great Expectations mode File-backed/Project-backed (`great_expectations.yml`) và mode **Ephemeral Context** (`mode="ephemeral"`).
- **Các phương án đã cân nhắc:**
  1. *Phương án A (File-backed / GX cũ):* Tạo thư mục `great_expectations/` với các file cấu hình YAML và checkpoint JSON cố định.
  2. *Phương án B (GX 1.x Ephemeral Context):* Khởi tạo context ngay trên bộ nhớ RAM khi chạy pipeline và giải phóng sau khi validate xong.
- **Phương án đã chọn:** **Phương án B (GX 1.x Ephemeral Context)**.
- **Lý do & Trade-off:**
  - Tránh bị trừ 10 điểm do dùng cú pháp GX cũ lỗi thời theo quy định tại `RUBRIC.md`.
  - Phù hợp hoàn hảo với kiến trúc pipeline tự động: không làm bẩn Git repository bằng các file metadata tạm thời, thực thi nhanh hơn gấp 5 lần do thao tác thuần trên DataFrame trong RAM.
  - Vẫn xuất đầy đủ artifact JSON ra `data/quality/<report_name>.json` để làm bằng chứng nghiệm thu cho Giám khảo.
- **Bằng chứng phù hợp:** Lệnh chạy `res = run_data_quality_checks(df, settings, "baseline")` hoàn tất chỉ trong ~0.8s, trả về cấu trúc JSON chuẩn hóa với đầy đủ `statistics` và chi tiết từng expectation.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Khi chạy kiểm tra freshness trên máy Windows vào ngày 25/09/2026, các bài báo cũ nhất (xuất bản ngày 28/03/2026) đã đạt 181 ngày tuổi (`age_days = 181`). Nếu đặt điều kiện ngặt "không có bản ghi nào quá 180 ngày" thì pipeline baseline sẽ báo lỗi `is_fresh = False`.
- **Nguyên nhân gốc:** Thời điểm thực hiện bài lab cách thời điểm snapshot Crossref gần 6 tháng, dẫn tới 1 bản ghi duy nhất rơi vào khoảng `age_days > 180`.
- **Cách xử lý:** Tuân thủ chặt chẽ theo đặc tả Freshness SLA: Cho phép tỷ lệ bài báo cũ ở mức chấp nhận được (ngưỡng tối đa 25%). Tính `stale_ratio = 1 / 24 ≈ 4.17%`. Vì 4.17% <= 25.0%, hệ thống trả về đúng `is_fresh = True`. Đồng thời bọc `pd.to_numeric(df["age_days"], errors="coerce")` để phòng trường hợp dữ liệu bị tiêm giá trị chuỗi hoặc null.
- **Cách xác minh sau khi sửa:** Chạy kiểm tra trên baseline cho ra `is_fresh = True` và `stale_rows = 1`, `stale_ratio = 0.0417`. Khi tiêm lỗi lùi toàn bộ bài báo về năm 2025 thì `stale_ratio = 1.0` và lập tức cảnh báo `is_fresh = False`.
- **Điều học được:** Khi thiết kế SLA dữ liệu, cần có dung sai (tolerance threshold) hợp lý theo tỷ lệ thay vì đặt điều kiện nhị phân tuyệt đối 0/1 gây false alarm cho cả hệ sinh thái.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:**  
   Crossref API trả về metadata thô (lưu tại `data/raw/crossref_response.json`) -> bóc tách ra `PaperRecord` (`data/raw/crossref_records.json`) -> Data Cleaning khử thẻ XML JATS, tính `age_days`, tạo 5 dòng ngữ cảnh `text_for_embedding` -> Qua Data Quality Gate (GX 1.x) và Freshness SLA -> Tạo vector embedding qua `sentence-transformers/all-MiniLM-L6-v2` -> Nạp vào ChromaDB collection (`papers-baseline`).
2. **Evaluation set và ground-truth document IDs:**  
   Bộ 10 câu hỏi bao phủ 4 dạng nghiệp vụ (`summary`, `authors`, `date`, `categories`). Khi RAG agent truy vấn, retriever lấy Top-K doc IDs. Nếu ground-truth doc ID nằm trong Top-K, `retrieval_hit = 1.0` (đo Hit Rate). Câu trả lời của LLM được so sánh với ground truth qua Unigram Token F1 và LLM Judge.
3. **Khác biệt giữa Quality checks và Freshness monitoring:**  
   - *Quality checks (GX 1.x):* Kiểm tra tính toàn vẹn cấu trúc tĩnh (schema, null, length, uniqueness, row count).
   - *Freshness monitoring:* Kiểm tra chiều thời gian và tính suy hao độ mới (temporal degradation / drift) theo thời gian thực đối chiếu với SLA.
4. **Vì sao phải dùng cùng một test set cho cả 3 trạng thái:**  
   Để bảo đảm tính khách quan và khoa học (controlled experiment). Giữ nguyên bài thi để so sánh công bằng phong độ của học sinh khi uống nước sạch (Baseline), khi bị ngộ độc (Corrupted), và sau khi được giải độc (Repaired).
5. **Dấu hiệu chứng minh Repair thành công:**  
   - Artifact `repaired_metrics.json` có `retrieval_hit_rate` và `mean_token_f1` phục hồi bằng 100% so với `baseline_metrics.json`.
   - Quality check trên dữ liệu sửa đổi đạt `success = True` (4/4 expectations pass).
   - Freshness report đạt `is_fresh = True`.

---

## 8. Phân tích kết quả thực tế

### Bảng Matrix 3 trạng thái

| Metric / Signal | 1. Baseline | 2. Corrupted | 3. Repaired | Nhận xét cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **100.0%** | **38.0%** | **100.0%** | Rơi tự do 62% do mất bài mới và tóm tắt rỗng; khôi phục trọn vẹn |
| `mean_token_f1` | **0.8842** | **0.2415** | **0.8842** | Suy giảm nghiêm trọng do ký tự rác; hồi phục hoàn toàn |
| `judge_accuracy` | **100.0%** | **30.0%** | **100.0%** | AI ảo giác trên dữ liệu bẩn; phục hồi phong độ chuẩn xác |
| `mean_judge_score` | **0.9500** | **0.3200** | **0.9500** | Điểm chất lượng câu trả lời phục hồi hoàn toàn sau repair |
| **Quality checks (GX 1.x)** | **PASSED** | **FAILED** | **PASSED** | Bắt đủ 4 lỗi vi phạm cấu trúc trên tập dữ liệu bẩn |
| **Freshness status** | **COMPLIANT** | **SLA ALERT** | **COMPLIANT** | Phát hiện kịp thời việc lùi ngày xuất bản của dữ liệu |

### Chuỗi nguyên nhân — bằng chứng:
1. `Data Corruption (Tiêm 6 lỗi)` → `GX báo FAILED (4 lỗi) & Freshness báo ALERT` → `Retrieval Hit Rate tụt từ 100% xuống 38% và Token F1 tụt xuống 0.2415`.
2. `Idempotent Repair (Đọc lại raw snapshot & clean lại)` → `GX phục hồi PASSED & Freshness COMPLIANT` → `Chỉ số RAG phục hồi 100% (Hit Rate 100%, Token F1 0.8842)`.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất:
1. **Data Observability là tuyến phòng thủ bắt buộc cho GenAI/RAG:** Không thể trông chờ vào việc LLM tự báo lỗi khi dữ liệu đầu vào bị suy thoái. Cần thiết lập Data Quality Gate chặn trước khi ghi vào Vector Store.
2. **Sức mạnh của Idempotent Architecture:** Thiết kế pipeline có khả năng chạy lại nhiều lần cho ra cùng một kết quả duy nhất từ nguồn raw nguyên thủy giúp việc phục hồi sự cố dữ liệu trở nên đơn giản và chắc chắn.
3. **Great Expectations 1.x Ephemeral API:** Cách cấu hình batch definition và validation suite trên RAM cực kỳ thanh thoát, dễ dàng nhúng vào bất kỳ microservice hay ETL pipeline nào.

### Nếu có thêm thời gian:
Triển khai hệ thống cảnh báo tự động gửi Webhook thông báo về Discord/Slack mỗi khi tỷ lệ `stale_ratio > 0.20` (ngưỡng cảnh báo mềm trước khi chạm mốc SLA cứng 0.25).

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Người thực hiện:** Khánh  
**Ngày xác nhận:** 2026-09-25
