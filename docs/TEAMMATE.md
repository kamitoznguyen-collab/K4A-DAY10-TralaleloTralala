# Phân Công Công Việc Nhóm — Day 10 Data Pipeline

> Thành viên: **Quân · Việt Anh · Khánh · Huy · Lan** (5 người)
> Tài liệu gốc: [CHECKPOINTS.md](CHECKPOINTS.md) · [Guide.md](Guide.md) · [RUBRIC.md](RUBRIC.md)

---

## 0. Kết quả kiểm tra CP0 (hiện trạng repo)

| Hạng mục CP0 | Trạng thái | Ghi chú |
| :--- | :---: | :--- |
| Python 3.11 – 3.13 | ❌ | Máy đang kiểm tra **chưa cài Python** (`python` chỉ là shortcut Microsoft Store, `py -0p` → không có bản nào). Mỗi người tự kiểm tra máy mình. |
| `.venv` + `pip install -e .` | ❌ | Chưa có `.venv`. Bắt buộc `pip install -e .` vì `script/*.py` import theo package trong `src/`. |
| File `.env` | ⚠️ | Đã có, `LLM_PROVIDER=gemini` nhưng **mọi API key đều trống** → `build_llm()` sẽ raise. Không có key thì đặt `LLM_PROVIDER=mock`. **Không commit `.env`** (-20đ). |
| `data/raw/crossref_response.json` | ✅ | 24 items, `abstract` có tag `<jats:p>` cần bóc. |
| `data/raw/crossref_records.json` | ✅ | 24 records, `published` từ 2026-03-28 → 2026-07-22. |
| `src/ingestion/crossref.py`, `cleaning.py` | ✅ | Việt Anh đã merge vào `main` (commit `d0ea007`): đủ 3 hàm Crossref + `build_clean_dataframe`. |

**Kết luận:** phần code CP0/CP1 của Việt Anh đã có trên `main`. Mỗi người còn phải tự setup môi trường (Python + `.venv` + `.env`) rồi chạy lệnh nghiệm thu CP0/CP1 để xác nhận.

### Setup môi trường (mọi thành viên đều làm)
```powershell
python --version                      # phải là 3.11 / 3.12 / 3.13
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
Copy-Item .env.example .env           # nếu chưa có; không key thì LLM_PROVIDER=mock
python -c "import chromadb, great_expectations, sentence_transformers; print('Môi trường sẵn sàng')"
```

---

## 1. Bảng phân công tổng

| Thành viên | Vai trò | File phụ trách | Checkpoint chính |
| :--- | :--- | :--- | :---: |
| **Quân** | Trưởng nhóm · Pipeline Integrator | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `.env`/setup, merge PR | CP0 setup, CP3, CP5, CP6 |
| **Việt Anh** | Data Ingestion & Cleaning | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py` | CP0, CP1 |
| **Khánh** | Data Observability & Reporting | `src/observability/quality.py`, `src/observability/reporting.py` | CP1, CP3, CP5 |
| **Huy** | RAG Index & Evaluation | `src/evaluation/testset.py`, `src/retrieval/index.py` (sửa), `src/retrieval/agent.py` (kiểm tra) | CP2, CP3 |
| **Lan** | Corruption Suite & Testing | `src/ingestion/corruption.py`, `tests/` (pytest) | CP4, Bonus B3 |

Việc chung: mỗi người **tự viết phần cá nhân** trong [TEAM.md](TEAM.md) và `report/individual_report.md` (-5đ/người nếu thiếu), và **phải có commit trên `main`**.

---

## 2. Chi tiết từng người

### 🧭 Quân — Trưởng nhóm / Pipeline Integrator
**Việc cần làm**
1. **CP0:** hướng dẫn cả nhóm setup, thống nhất `.env` (`LLM_PROVIDER=mock` khi chưa có key), điền phần đầu của `TEAM.md`.
2. **CP3 — `phase1.py` `main()`:** `load_settings` → `fetch_source_records` → `build_clean_dataframe` → lưu `clean_csv`/`clean_json` → `LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)` → `build_test_set` (chỉ sinh lại khi chưa có file hoặc `REFRESH_TEST_SET=1`) → `evaluate_pipeline` → `run_data_quality_checks` + `build_freshness_report` → `generate_phase1_report`. Demo agent bọc `try/except` (provider `mock` không hỗ trợ tool-calling).
3. **CP5 — `corruption_flow.py` `main()`:** load baseline → `corrupt_clean_dataframe` → lưu artifact corrupted → build index `corrupted_embeddings_json` → evaluate → quality + freshness → **repair: đọc lại `raw_records_json` rồi clean lại từ đầu** (không sửa tay df bẩn) → build index `repaired_embeddings_json` → evaluate → `generate_corruption_report`. In bảng 3 trạng thái ra console.
4. Kiểm tra tính idempotent: chạy `run_corruption_flow.py` 2 lần, `repaired_metrics.json` phải giống hệt nhau.
5. **CP6:** dẫn live demo, review/merge PR, chạy end-to-end lần cuối trên máy sạch.

**Nghiệm thu:** `python script/run_phase1.py` và `python script/run_corruption_flow.py` chạy xong không lỗi.

---

### 📥 Việt Anh — Ingestion & Cleaning
**Việc cần làm**
1. **CP0 — `crossref.py`:**
   - `parse_crossref_payload(payload)`: duyệt `payload["message"]["items"]`, map:
     `DOI→paper_id`, `title[0]→title`, `abstract` (bóc `<jats:*>` bằng regex + `normalize_whitespace`) `→summary`, `author[]→"given family"`, `subject→categories`, `subject[0]→primary_category`, `published.date-parts[0]→"YYYY-MM-DD"`, `created.date-time[:10]→updated`, `URL→abs_url/pdf_url`, `comment="Crossref record <DOI>"`. Bỏ record thiếu DOI/title/abstract.
   - `fetch_source_records(settings)`: **mặc định đọc snapshot offline**; chỉ gọi API khi `settings.refresh_source=True` (retry cho 429/503, timeout). API lỗi → fallback về `raw_api_response`. Luôn ghi lại `raw_records_json`.
     > ⚠️ Gọi API thật sẽ **ghi đè snapshot** bằng dữ liệu khác 24 bài → test set/metrics lệch. Chỉ refresh khi cả nhóm thống nhất.
   - `load_raw_records(path)`: `read_json` → `[PaperRecord(**r) for r in ...]`.
2. **CP1 — `cleaning.py` `build_clean_dataframe`:** chuẩn hóa text, dedupe theo `paper_id`, tính `age_days = (run_date.date() - published).days`, tạo `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding` (5 dòng Title/Authors/Published/Categories/Summary — xem [Guide.md](Guide.md) Bước 3). Sort theo `published` giảm dần.
   - `published` **giữ dạng chuỗi** `YYYY-MM-DD`, null → `""` (ChromaDB metadata không nhận Timestamp/None).
3. **Hỗ trợ Quân** hàm repair (clean lại từ raw) ở CP5.

**Nghiệm thu:** lệnh CP0 in `Đã tải 24 bài báo`, lệnh CP1 in `Clean thành công 24 dòng`.

---

### 🔎 Khánh — Observability & Reporting
**Việc cần làm**
1. **CP1 — `quality.py` `run_data_quality_checks`:** dùng **GX 1.x** (ephemeral context như trong [CHECKPOINTS.md](CHECKPOINTS.md) CP1 — không dùng API cũ, -10đ). 4 expectations:
   - `ExpectTableRowCountToBeBetween` (vd. 20 – 30)
   - `ExpectColumnValuesToNotBeNull` cho `paper_id`, `title`, `text_for_embedding`
   - `ExpectColumnValuesToBeUnique` cho `paper_id`
   - `ExpectColumnValueLengthsToBeBetween` cho `summary` (bắt summary rỗng/ngắn) và `title` (bắt title bị cắt < 8 ký tự)
   Trả về dict có khóa `success` (bool) + chi tiết từng expectation; ghi JSON vào `data/quality/<report_name>.json`.
2. **`build_freshness_report`:** `latest_published`, `oldest_published`, `stale_rows` (`age_days > 180`), `total_rows`, `stale_ratio`, `is_fresh = stale_ratio <= 0.25`. Ghi JSON.
   > Lưu ý: tính đến 25/09/2026 bài cũ nhất đã khoảng 181 ngày → baseline có ít nhất 1 dòng stale, vẫn phải ra `is_fresh=True`.
3. **CP3/CP5 — `reporting.py`:** `generate_phase1_report` (nguồn, metrics, quality, freshness) và `generate_corruption_report` (bảng **Baseline | Corrupted | Repaired** cho hit rate, token F1, judge accuracy, GX success, is_fresh, kèm phần phân tích).
4. *(Bonus B1, nếu còn thời gian)* dashboard Streamlit đọc `data/quality/` và `data/results/`.

**Nghiệm thu:** lệnh CP1 in `Quality check status = True` trên dữ liệu sạch, và `False` trên dữ liệu corrupted.

---

### 🧠 Huy — RAG Index & Evaluation
**Việc cần làm**
1. **CP2 — `testset.py` `build_test_set`:** sinh **10 câu**, đủ 4 loại `summary` / `authors` / `date` / `categories`. Câu hỏi phải khớp luật trong [qa.py](../src/retrieval/qa.py):
   - authors: `Who authored '<title>'?` → ground_truth = `authors_joined`
   - date: `When was '<title>' published?` → ground_truth = `published`
   - categories: `What categories does '<title>' belong to?` → ground_truth = `categories_joined`
   - summary: `What is '<title>' about?` → ground_truth = câu đầu của `summary`
   - Title đặt trong **nháy đơn** để lookup chính xác; bỏ qua title có dấu `'`.
   - Nên chọn cả **bài mới nhất** (để corruption "drop latest" làm tụt hit rate thấy rõ).
   - Mỗi item có: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.
2. **Sửa `index.py`:** manifest đang lưu `persist_path` **tuyệt đối** (`D:\...`) → máy giám khảo `load()` lỗi và dính -5đ hardcode path. Đổi sang đường dẫn tương đối so với `project_dir` và resolve lại khi load.
3. Kiểm tra ChromaDB: collection `papers-baseline` có đủ 24 docs; ba collection baseline/corrupted/repaired tách biệt.
4. Kiểm tra `agent.py` với `mock`: nếu `create_agent` lỗi do `bind_tools`, báo Quân để bọc `try/except` ở demo.

**Nghiệm thu:** lệnh CP2 in `Sinh được 10 câu hỏi test`; `baseline_metrics.json` có `retrieval_hit_rate` cao (≈1.0).

---

### 🧪 Lan — Corruption Suite & Testing
**Việc cần làm**
1. **CP4 — `corruption.py` `corrupt_clean_dataframe`:** dùng seed cố định (`random.Random(42)`) để chạy lặp lại ra cùng kết quả. Làm đủ 6 lỗi:
   1. Drop latest records (~20% bài mới nhất)
   2. Blank summary (gán `""`, **không** gán `None`)
   3. Inject noise vào summary (ký tự rác)
   4. Truncate title (< 8 ký tự)
   5. Stale date (lùi `published` > 180 ngày + cập nhật `age_days`)
   6. Duplicate rows
   Sau đó rebuild `text_for_embedding`, ghi `corruption_log.json` (loại lỗi, số dòng, danh sách `paper_id` bị ảnh hưởng). **Không sửa df gốc** (dùng `df.copy()`).
2. **Bonus B3 — `tests/`:** pytest cho `parse_crossref_payload`, `build_clean_dataframe` (24 dòng, không trùng, có `age_days`), GX (sạch → True, bẩn → False), `corrupt_clean_dataframe` (log đủ 6 loại), `build_test_set` (10 câu, đủ 4 loại). Thêm script chạy một lệnh.
3. Hỗ trợ Khánh phần phân tích trong `corruption_report.md`.

**Nghiệm thu:** lệnh CP4 trong [Guide.md](Guide.md) in `Corrupted N dòng`; `corruption_log.json` có đủ 6 loại lỗi.

---

## 3. Hợp đồng dữ liệu giữa các module (để làm song song)

**Clean DataFrame** (Việt Anh xuất ra, mọi người dùng):

| Cột | Kiểu | Ghi chú |
| :--- | :--- | :--- |
| `paper_id`, `title`, `summary` | str | không null, `summary` rỗng → `""` |
| `authors`, `categories` | list[str] | |
| `primary_category`, `published`, `updated`, `abs_url`, `pdf_url`, `comment` | str | `published` = `YYYY-MM-DD` |
| `age_days` | int | tính theo `run_date` |
| `authors_joined`, `categories_joined` | str | nối bằng `", "` |
| `summary_chars` | int | |
| `text_for_embedding` | str | 5 dòng Title/Authors/Published/Categories/Summary |

Trong lúc chờ `cleaning.py`, Khánh/Huy/Lan có thể tạm tạo df giả từ `data/raw/crossref_records.json` theo đúng schema trên để viết code trước.

---

## 4. Thứ tự phụ thuộc & timeline

```text
CP0 (0-30')    Mọi người: setup env        Việt Anh: crossref.py
CP1 (30-65')   Việt Anh: cleaning.py       Khánh: quality.py      Huy/Lan: viết code trên df giả
CP2 (65-95')   Huy: testset.py + index     Lan: corruption.py     Khánh: reporting.py
CP3 (95-120')  Quân: phase1.py  ← cần crossref + cleaning + quality + testset + phase1 report
CP4 (120-165') Lan: chạy corruption, đo corrupted_metrics      Lan: bắt đầu tests/
CP5 (165-210') Quân + Việt Anh: corruption_flow + repair   Khánh: corruption_report.md
CP6 (210-240') Quân: demo · Cả nhóm: TEAM.md + report cá nhân + nộp LMS (từng người)
```

## 5. Quy tắc Git
- Mỗi người làm trên nhánh riêng: `feat/<ten>-<module>` (vd. `feat/vietanh-crossref`), mở PR vào `main`, **Quân review & merge**.
- Không commit: `.env`, `.venv/`, `data/chroma/` (binary DB). Commit các artifact JSON/MD dùng làm bằng chứng chấm điểm.
- Không bịa số liệu trong báo cáo: mọi con số phải lấy từ `data/results/*.json` sau khi chạy thật (-20đ).
