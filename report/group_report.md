# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4              |
| Tên nhóm         | Tralalelo Tralala     |
| Repository         | https://github.com/kamitoznguyen-collab/K4A-DAY10-TralaleloTralala |
| Ngày hoàn thành | 2026-09-25               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Quang Huy | 2A202602421 | Trưởng nhóm · RAG & Vector Index | `src/evaluation/testset.py`, `src/retrieval/index.py`, `data/eval/test_set.json`, tích hợp nhánh |
| 2 | Lại Bá Quân | 2A202602495 | Pipeline Integrator | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `data/reports/*` |
| 3 | Đỗ Lê Việt Anh | 2A202602491 | Data Ingestion & Cleaning | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `data/raw/`, `data/clean/` |
| 4 | Nguyễn Thị Minh Khánh | 2A202602546 | Data Observability & Reporting | `src/observability/quality.py`, `reporting.py`, `dashboard.py`, `data/quality/` |
| 5 | Trần Thị Lan | 2A202602621 | Corruption Suite & Testing | `src/ingestion/corruption.py`, `tests/`, `data/results/corruption_log.json` |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm hoàn thành đủ CP0–CP5: ingestion Crossref với fallback offline, cleaning, index ChromaDB, test set 10 câu, quality gate Great Expectations 1.x, freshness SLA, bộ 6 corruption, repair idempotent và báo cáo đối chiếu 3 trạng thái. Kèm theo là bộ pytest 12 case và dashboard Streamlit (bonus). Baseline pipeline (`script/run_phase1.py`) sinh ra `data/clean/papers_clean.{csv,json}` (24 dòng), collection `papers-baseline` (24 docs), `data/eval/test_set.json`, `baseline_metrics.json`, `baseline_quality_report.json`, `freshness_report.json` và `phase1_report.md`.

Corruption ảnh hưởng rõ nhất tới agent là **drop latest**: mất 4 bài mới nhất làm `retrieval_hit_rate` giảm từ 1.0 xuống 0.8, vì 2/10 câu hỏi nhắm vào các bài đó. Về data quality, GX bắt được 3 lỗi (duplicate `paper_id`, summary rỗng, title bị cắt) và freshness chuyển sang vi phạm (27.3% bài stale > 25%). Repair bằng cách clean lại từ raw snapshot đưa mọi chỉ số về đúng baseline (hit rate 1.0, F1 1.0, GX pass, fresh), và chạy lại 2 lần cho kết quả giống hệt nhau.

Giới hạn quan trọng nhất: pipeline chạy với `LLM_PROVIDER=mock`, nên judge dùng heuristic fallback và `judge_accuracy` vẫn giữ 1.0 kể cả khi agent trả lời từ sai tài liệu. Chỉ `retrieval_hit_rate` và GX/freshness phát hiện được lỗi. Ngoài ra, row-count expectation (20–30) không bắt được việc mất 4 bài.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref snapshot (data/raw/crossref_response.json; API chỉ khi REFRESH_SOURCE=1)
    -> crossref_records.json (24 PaperRecord)
    -> cleaning: chuẩn hoá, dedupe, age_days, text_for_embedding
    -> embedding all-MiniLM-L6-v2 + ChromaDB (papers-baseline)
    -> evaluation baseline (test_set.json, 10 câu)
    -> GX 1.x quality + freshness SLA
    -> corruption 6 loại (seed 42) -> papers-corrupted -> re-evaluate
    -> repair: clean lại từ raw -> papers-repaired -> re-evaluate
    -> corruption_report.md (Baseline | Corrupted | Repaired)
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API / snapshot | Offline mặc định, retry 429/5xx + timeout 15s, bóc JATS, map `PaperRecord` | `data/raw/crossref_records.json` | Việt Anh |
| Cleaning          | 24 `PaperRecord` | Chuẩn hoá text/list, dedupe `paper_id`, `age_days`, `text_for_embedding`, sort `published` giảm dần | `data/clean/papers_clean.{csv,json}` | Việt Anh |
| Embedding/index   | Clean DataFrame | `all-MiniLM-L6-v2`, 3 collection tách biệt, manifest lưu path tương đối | `data/chroma/`, `data/embeddings/*.json` | Huy |
| Evaluation        | Clean DataFrame, index | 10 câu cố định, hit rate / token F1 / judge | `data/eval/test_set.json`, `data/results/*_metrics.json` | Huy |
| Observability     | DataFrame mỗi trạng thái | GX 1.x ephemeral (7 expectation), freshness 180 ngày / 25% | `data/quality/*.json` | Khánh |
| Corruption/repair | Clean DataFrame / raw records | 6 corruption seed 42; repair = clean lại từ raw | `data/clean/papers_clean_{corrupted,repaired}.*`, `corruption_log.json` | Lan (corruption), Quân + Việt Anh (repair) |
| Orchestration     | Settings | Thứ tự CP3 → CP5, in bảng 3 trạng thái | `data/reports/phase1_report.md`, `corruption_report.md` | Quân |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `mock`         |
| `LLM_MODEL`                | `mock`         |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 (`max_results=24`) |
| Retrieval `top_k`           | 4         |
| Freshness threshold          | 180 ngày, `stale_ratio <= 0.25` |
| Random seed, nếu có        | `random.Random(42)` (corruption) |

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

Test:

```bash
python script/run_tests.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công (exit 0) | 2026-09-25 10:21 UTC | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công (exit 0), chạy 2 lần cho metrics giống hệt | 2026-09-25 10:22 UTC | `data/results/{corrupted,repaired}_metrics.json`, `data/reports/corruption_report.md` |
| pytest            | 12/12 passed | 2026-09-25 | `tests/test_corruption.py` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API `/works` (snapshot `data/raw/crossref_response.json`) |
| Query/filter                | `agentic retrieval augmented generation large language model`; `from-pub-date:<run_date − 180d>,has-abstract:true` |
| Thời điểm lấy dữ liệu | Snapshot commit 2026-09-24; bài từ 2026-03-28 đến 2026-07-22 |
| Số record nhận được    | 24 items → 24 records |
| Cơ chế retry/backoff      | Retry với status 429/500/502/503/504, backoff `2**attempt`, timeout 15s; lỗi API → fallback về snapshot offline |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | str (DOI) | Có | Document ID, khoá chính | Thiếu → loại record; trùng → dedupe |
| `title` | str | Có | Tiêu đề (`title[0]`) | Thiếu → loại record |
| `summary` | str | Có | Abstract đã bóc JATS | Thiếu → loại record; null → `""` |
| `authors` / `authors_joined` | list[str] / str | Không | `"given family"`, nối bằng `", "` | Thiếu → list rỗng |
| `categories` / `categories_joined` | list[str] / str | Không | Crossref `subject` | Thiếu → list rỗng |
| `published` | str `YYYY-MM-DD` | Có | Ngày xuất bản (`published.date-parts`) | Giữ dạng chuỗi (ChromaDB không nhận Timestamp/None) |
| `age_days` | int | Có | `run_date − published` | Tính lại mỗi lần chạy |
| `summary_chars` | int | Có | Độ dài summary | Tính từ summary đã chuẩn hoá |
| `text_for_embedding` | str | Có | Văn bản đưa vào embedding | Sinh từ 5 trường |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Bóc tag `<jats:*>` khỏi abstract | Validity | 24 | So `crossref_response.json` với `papers_clean.json` |
| Loại record thiếu DOI/title/abstract | Completeness | 0 | 24 raw → 24 clean |
| Dedupe theo `paper_id` | Uniqueness | 0 | GX `column_values_to_be_unique` pass |
| Chuẩn hoá whitespace, `published` thành `YYYY-MM-DD` | Consistency | 24 | Schema `papers_clean.json` |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

Document ID là DOI Crossref (`paper_id`), được dùng làm id trong ChromaDB và trong `ground_truth_doc_ids`. `text_for_embedding` gồm 5 dòng `Title / Authors / Published / Categories / Summary`, để câu hỏi về tác giả, ngày hay chủ đề đều khớp ngữ nghĩa với vector. `age_days = (run_date.date() − published).days`, với `run_date` là thời điểm chạy pipeline (UTC). Baseline có `age_days` từ 65 đến 181.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10                 |
| Các `question_type`                    | `summary` (3), `authors` (3), `date` (2), `categories` (2) |
| Ground-truth document ID                 | `paper_id` của bài được hỏi; title đặt trong nháy đơn để `qa.py` lookup chính xác |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection                  | ChromaDB `data/chroma`: `papers-baseline` (24), `papers-corrupted` (22), `papers-repaired` (24) |
| Retrieval `top_k`                       | 4                   |
| LLM provider/model                       | `mock` / `mock` (judge dùng heuristic fallback) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (sha256 `c86c7ea0c12b…`) |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Giữ nguyên câu hỏi, ground truth và doc id thì mọi chênh lệch metric chỉ đến từ dữ liệu. `run_phase1.py` chỉ sinh lại test set khi chưa có file hoặc khi `REFRESH_TEST_SET=1`; `corruption_flow.py` đọc lại đúng file đó. Test set chọn tất định 10 bài trải đều từ mới đến cũ và luôn có bài mới nhất, để lỗi "drop latest" hiện ra trên metric.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | 24 items / 24 records |
| Cleaned dataset          | `data/clean/`                        | Có | 24 dòng, kèm bản corrupted/repaired |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/`   | Có | Manifest lưu `persist_path` tương đối |
| Evaluation set           | `data/eval/`                         | Có | 10 câu |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Kèm `baseline_answers.json` |
| Quality/freshness        | `data/quality/`                      | Có | Đủ 3 trạng thái |
| Baseline report          | `data/reports/phase1_report.md`      | Có | |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.0 | 10/10 câu có tài liệu đúng trong top-4 |
| `mean_token_f1`      |     1.0 | Câu trả lời trích đúng trường metadata của tài liệu đúng |
| `judge_accuracy`     |     1.0 | Judge heuristic (mock) chấm đúng cả 10 câu |
| `mean_judge_score`   |     5 | Điểm tối đa |
| Ragas, nếu có        | N/A | Bỏ qua: cần `RUN_RAGAS=1` và LLM thật |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `ExpectTableRowCountToBeBetween` | Completeness | 20–30 dòng | Pass (24) | `data/quality/baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`paper_id`, `title`, `text_for_embedding`) | Completeness | 0 null | Pass (0) | như trên |
| `ExpectColumnValuesToBeUnique` (`paper_id`) | Uniqueness | 0 trùng | Pass (0) | như trên |
| `ExpectColumnValueLengthsToBeBetween` (`summary`) | Validity | ≥ 30 ký tự | Pass (0 vi phạm) | như trên |
| `ExpectColumnValueLengthsToBeBetween` (`title`) | Validity | ≥ 8 ký tự | Pass (0 vi phạm) | như trên |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Clean dataset (`published`, `age_days`) → `data/quality/freshness_report.json` |
| Timestamp mới nhất       | 2026-07-22 (cũ nhất 2026-03-28) |
| Ngưỡng freshness         | 180 ngày; dataset fresh nếu `stale_ratio <= 0.25` |
| Trạng thái baseline      | Fresh (`is_fresh = true`) |
| Lý do                     | 1/24 bài (4.17%) đã quá 180 ngày tại 2026-09-25, thấp hơn ngưỡng 25% |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `drop_latest` | Xoá 20% bài mới nhất | 4 | Row count giảm, latest lùi | Latest 2026-07-22 → 2026-06-12; hit rate 1.0 → 0.8; row count 22 vẫn trong 20–30 nên GX không bắt | Clean lại từ raw |
| `blank_summary` | Gán `""` cho 15% summary | 3 | Summary length fail | GX `summary` length: 3 vi phạm | Clean lại từ raw |
| `inject_noise` | Chèn 8 ký tự rác vào summary | 3 | Text sai lệch | Không làm đổi metric (3 bài bị nhiễu không nằm trong test set); GX không bắt được vì summary vẫn đủ dài | Clean lại từ raw |
| `truncate_title` | Cắt title còn 3–7 ký tự | 3 | Title length fail | GX `title` length: 3 vi phạm | Clean lại từ raw |
| `stale_date` | Lùi `published` 181–365 ngày | 4 | Freshness vi phạm | Stale 6/22 = 27.3% → `is_fresh = false`; oldest 2025-05-04 | Clean lại từ raw |
| `duplicate_rows` | Nhân đôi 10% dòng | 2 | Unique fail | GX unique `paper_id`: 4 dòng trùng | Clean lại từ raw (dedupe) |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log có đủ 6 loại, mỗi loại ghi `type`, `num_rows` và danh sách `paper_ids` bị tác động. Tham số (tỉ lệ, seed 42) nằm trong code `corruption.py` chứ không ghi vào log.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Repair không sửa DataFrame bẩn. `corruption_flow.py` đọc lại `data/raw/crossref_records.json` (raw snapshot bất biến), chạy lại đúng `build_clean_dataframe`, build collection mới `papers-repaired` rồi evaluate bằng cùng test set. Vì nguồn là raw snapshot và các bước đều tất định, chạy lại cho kết quả giống hệt: `repaired_metrics.json` trùng khớp giữa 2 lần chạy. Kết quả repair được xác nhận độc lập bằng GX và freshness trên dữ liệu repaired, không chỉ dựa vào metric agent.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |      1.0 |       0.8 |      1.0 |                     −0.2 |            100% | 2 câu hỏi về bài bị `drop_latest` |
| `mean_token_f1`        |      1.0 |    0.9741 |      1.0 |                  −0.0259 |            100% | Agent trả lời bằng tài liệu gần giống |
| `judge_accuracy`       |      1.0 |       1.0 |      1.0 |                        0 |               — | Judge heuristic không phát hiện sai tài liệu |
| `mean_judge_score`     |        5 |       4.8 |        5 |                     −0.2 |            100% | `eval_001` bị chấm 3/5 |
| Quality checks pass/fail |   Pass (7/7) |  Fail (4/7 pass) |  Pass (7/7) |          3 expectation fail |            100% | unique, summary length, title length |
| Freshness status         | Fresh (4.17%) | Stale (27.27%) | Fresh (4.17%) |  +23.1 điểm % stale |            100% | `stale_date` đẩy vượt ngưỡng 25% |

Kết luận có quan hệ nhân quả:

1. `drop_latest` xoá 4 bài mới nhất → latest lùi về 2026-06-12, GX row count vẫn pass (22 dòng) → `retrieval_hit_rate` 1.0 → 0.8 do 2 câu (`eval_001`, `eval_002`) mất tài liệu đúng (`data/results/corrupted_answers.json`).
2. `duplicate_rows` + `blank_summary` + `truncate_title` + `stale_date` → GX fail 3 expectation và `is_fresh = false` → những lỗi này không làm tụt metric agent vì không rơi vào tài liệu của test set. Quality gate là tín hiệu duy nhất phát hiện chúng.
3. Repair (clean lại từ raw) → GX pass 7/7, stale 4.17% → toàn bộ metric agent về đúng baseline.

Kết quả khác kỳ vọng: `judge_accuracy` không giảm. Khi tài liệu đúng bị xoá, agent vẫn lấy tài liệu gần nhất để trả lời (ở `eval_002`, tài liệu khác trùng tác giả nên F1 vẫn 1.0), và judge heuristic của provider `mock` chấm "correct". Nhóm kiểm tra bằng cách đối chiếu `retrieved_doc_ids` với `ground_truth_doc_ids` trong `corrupted_answers.json`. Đây là silent failure mà chỉ metric dựa trên doc id và quality gate mới phát hiện.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Sau khi ghép `phase1.py` / `corruption_flow.py` với `quality.py`, các file `data/quality/*_quality_report.json` chứa đường dẫn tuyệt đối của máy chạy (`C:\Users\...`) trong `report_name` và trong `batch_id` của GX.
- **Nguyên nhân:** Pipeline truyền đường dẫn file đầy đủ vào tham số `report_name`, còn `quality.py` được viết với giả định đó chỉ là tên ngắn, nên ghi nguyên giá trị vào report và dùng để đặt tên datasource GX. Hai module đều đúng khi test riêng, chỉ lỗi khi ghép.
- **Cách xử lý:** `quality.py` chỉ giữ tên file (`Path(report_name).stem`) cho `report_name` và tên datasource; vị trí ghi file không đổi. Trước đó nhóm cũng giải quyết conflict hai phiên bản `quality.py` (giữ bản của Khánh vì `reporting.py` đọc đúng schema của bản này).
- **Cách xác minh:** Chạy lại `run_phase1.py` và `run_corruption_flow.py`, sau đó `grep` toàn bộ `data/` không còn đường dẫn máy; `report_name` giờ là `baseline_quality_report` / `corrupted_quality_report` / `repaired_quality_report`; pytest 12/12 pass.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Chạy với `LLM_PROVIDER=mock`, judge heuristic | `judge_accuracy` không phản ánh việc trả lời từ sai tài liệu | Chạy với LLM thật (`RUN_RAGAS=1`); kỳ vọng `judge_accuracy` corrupted < 1.0 |
| Row count 20–30 không bắt `drop_latest` (22 dòng) | Mất 17% dữ liệu mà GX vẫn pass | Thêm expectation so với baseline (giảm ≤ 5%) hoặc kiểm tra `latest_published`; kỳ vọng GX corrupted fail thêm 1 expectation |
| GX không bắt `inject_noise` | Summary bị nhiễu vẫn qua quality gate | Thêm expectation regex ký tự hợp lệ cho `summary`; đo số dòng vi phạm = 3 |
| Agent không từ chối khi retrieval kém | Trả lời tự tin từ tài liệu sai | Ngưỡng similarity cho top-1, dưới ngưỡng thì trả lời "không biết"; đo lại F1/judge ở trạng thái corrupted |
| Cột Baseline trong `corruption_report.md` cố định một số ô (stale ratio hiện `<= 25.0%`) | Báo cáo không hiện đúng 4.2% của baseline | Truyền `freshness_report.json` baseline vào `generate_corruption_report` |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
