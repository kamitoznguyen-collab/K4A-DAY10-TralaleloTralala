# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đỗ Lê Việt Anh |
| MSSV               | 2A202602491 |
| Email              | dlvietanh2k4@gmail.com |
| Khóa/Lớp         | K4 |
| Tên nhóm         | Tralalelo Tralala |
| Vai trò chính    | Data Ingestion & Cleaning (`crossref.py`, `cleaning.py`, raw data) |
| Repository         | https://github.com/kamitoznguyen-collab/K4A-DAY10-TralaleloTralala |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Parse Crossref payload (CP0) | `src/ingestion/crossref.py` · `parse_crossref_payload` | JSON Crossref `/works` (`message.items`) | `list[PaperRecord]` (11 trường) | Hoàn thành |
| Thu thập + bảo toàn raw data (CP0) | `crossref.py` · `fetch_source_records`, `load_raw_records` | `Settings` (query, filter, `max_results`, `REFRESH_SOURCE`) | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Làm sạch dữ liệu (CP1) | `src/ingestion/cleaning.py` · `build_clean_dataframe` | `list[PaperRecord]`, `run_date` | DataFrame sạch 16 cột (hợp đồng dữ liệu của nhóm) | Hoàn thành |

Phần của mình là **đầu nguồn** của pipeline: mọi module phía sau đều đọc DataFrame do `build_clean_dataframe` tạo ra — Khánh (`quality.py`: GX + freshness dựa trên `age_days`, `summary`, `paper_id`), Huy (`index.py` lấy `text_for_embedding` + metadata `published`/`authors_joined`/`categories_joined`; `testset.py` lấy ground truth), Lan (`corruption.py` làm hỏng chính DataFrame này) và Quân (`phase1.py`, `corruption_flow.py`).

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Kiểm tra luồng repair (clean lại từ raw) | Quân · `corruption_flow.py` (CP5) | Bước repair của Quân gọi lại đúng `load_raw_records` + `build_clean_dataframe` của mình. Chạy `python script/run_corruption_flow.py` → repaired 24 dòng, GX 7/7, metric bằng baseline; chạy lần 2 cho `repaired_metrics.json` và `repaired_answers.json` giống hệt từng byte (idempotent). |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Bóc tag `<jats:p>`, chuẩn hóa text, map DOI/title/author/subject/date/URL, bỏ record thiếu DOI/title/abstract và DOI trùng | `crossref.py` · `parse_crossref_payload` | 24 `PaperRecord` | So sánh output với `data/raw/crossref_records.json` → trùng khớp 24/24 |
| Mặc định đọc snapshot offline; chỉ gọi API khi `REFRESH_SOURCE=1`, retry 429/5xx, timeout 30s, lỗi thì fallback snapshot | `crossref.py` · `fetch_source_records` | Lệnh CP0 in `Đã tải 24 bài báo` | Lệnh nghiệm thu CP0 + test giả lập 429 và mất mạng |
| Chuẩn hóa, dedupe theo `paper_id`, tính `age_days`, tạo cột phụ và `text_for_embedding`, sort `published` giảm dần | `cleaning.py` · `build_clean_dataframe` | Lệnh CP1 in `Clean thành công 24 dòng` | Lệnh nghiệm thu CP1 + test dữ liệu bẩn |

Output cụ thể phần việc của mình tạo ra: `data/clean/papers_clean.json` (24 dòng) do `python script/run_phase1.py` sinh ra từ `crossref_records.json` qua `build_clean_dataframe`. Từ DataFrame này, baseline đạt `retrieval_hit_rate = 1.0`, GX `success = True`, freshness `stale_ratio = 0.0417` (1/24).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Dữ liệu Crossref thô không dùng được ngay cho RAG: abstract lẫn tag JATS XML, title là mảng, tác giả tách `given`/`family`, ngày ở dạng `date-parts` lồng nhau, có thể thiếu trường hoặc trùng DOI. API công khai còn hay trả `429 Too Many Requests`. Phần mình biến dữ liệu này thành một bảng sạch, có schema cố định, **tái lập được** (chạy lại ra cùng kết quả) để cả nhóm build index, đo metric và làm repair.

### Cách triển khai

**Ingestion (`crossref.py`):**
- `_clean_text` bóc mọi tag bằng regex `<[^>]+>`, `html.unescape` các entity (`&amp;`), rồi `normalize_whitespace`. Trường dạng mảng (`title`) lấy phần tử đầu.
- Tác giả = `"given family"`, nếu không có thì dùng `name` (tác giả là tổ chức). `subject` được dedupe giữ thứ tự; `primary_category` = subject đầu tiên.
- `published` lấy ngày đầu tiên có trong `published` → `published-print` → `published-online` → `issued` → `created`; `date-parts` thiếu tháng/ngày thì mặc định `01`. `updated` lấy từ `updated`/`deposited`/`indexed`/`created`, không có thì bằng `published`.
- `pdf_url` = link đầu tiên có content-type PDF, không có thì bằng `abs_url` (`URL` hoặc `https://doi.org/<DOI>`).
- Bỏ record thiếu DOI/title/abstract (không có abstract thì không có nội dung để embed) và DOI trùng (so sánh không phân biệt hoa thường).
- `fetch_source_records` **mặc định đọc snapshot**; chỉ gọi API khi `REFRESH_SOURCE=1` hoặc chưa có snapshot. Retry tối đa 3 lần cho 429/500/502/503/504, tôn trọng header `Retry-After`, nếu không thì backoff 2s, 4s. Hết lượt thì fallback về snapshot. Raw response chỉ bị ghi đè khi API trả 200; `crossref_records.json` luôn được ghi lại.

**Cleaning (`cleaning.py`):**
- Chuẩn hóa text và list (bỏ phần tử rỗng/trùng). Ngày được chuẩn về chuỗi `YYYY-MM-DD`, không parse được → `""`.
- Bỏ dòng thiếu `paper_id`/`title`; dedupe theo `paper_id`, giữ bản có `updated` mới nhất.
- `age_days = (run_date.date() - published).days`; `authors_joined`/`categories_joined` nối bằng `", "`; `summary_chars`; `text_for_embedding` gồm 5 dòng `Title / Authors / Published / Categories / Summary`.
- Sort `published` giảm dần (`paper_id` làm khóa phụ để thứ tự ổn định) và trả về đúng 16 cột theo hợp đồng dữ liệu.
- **Không** lọc summary rỗng/ngắn ở bước clean: đó là việc của quality gate (GX), nếu clean lặng lẽ xóa đi thì GX sẽ không bao giờ thấy lỗi.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Crossref JSON (`message.items[]`: `DOI`, `title[]`, `abstract`, `author[]`, `subject[]`, `published.date-parts`, `created.date-time`, `URL`, `link[]`); `Settings`; `run_date` (UTC) |
| Output                         | `list[PaperRecord]`; `crossref_response.json`, `crossref_records.json`; DataFrame 16 cột: `paper_id`, `title`, `summary`, `authors`, `categories`, `primary_category`, `published`, `updated`, `abs_url`, `pdf_url`, `comment`, `age_days` (int), `authors_joined`, `categories_joined`, `summary_chars` (int), `text_for_embedding` |
| Module phụ thuộc             | `core/config.py` (`Settings`, `Paths`), `core/utils.py` (`read_json`, `write_json`, `normalize_whitespace`, `compact_join`), `requests`, `pandas` |
| Module sử dụng output        | `pipelines/phase1.py`, `observability/quality.py`, `retrieval/index.py`, `evaluation/testset.py`, `ingestion/corruption.py`, `pipelines/corruption_flow.py` (repair) |
| Điều kiện lỗi cần xử lý | API 429/503/timeout/mất mạng → fallback snapshot; không có snapshot → `RuntimeError` rõ ràng; abstract có tag JATS/entity; thiếu tác giả/subject; `date-parts` chỉ có năm; ngày không hợp lệ → `""`; DOI trùng; ChromaDB không nhận metadata `Timestamp`/`None` → giữ ngày dạng chuỗi |

### Cách xác minh

```bash
python -c "import chromadb, great_expectations, sentence_transformers; print('Môi trường sẵn sàng')"
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
git status --short data/raw/   # không có thay đổi sau khi fetch ghi lại crossref_records.json
LLM_PROVIDER=mock python script/run_phase1.py
LLM_PROVIDER=mock python script/run_corruption_flow.py   # chạy 2 lần, so sánh repaired_metrics.json
```

- **Kết quả mong đợi:** `Môi trường sẵn sàng`, `Đã tải 24 bài báo`, `Clean thành công 24 dòng`; `crossref_records.json` sau khi ghi lại không đổi; phase 1 chạy hết với 24 docs.
- **Kết quả thực tế:** Đúng như mong đợi (Python 3.12.10 trong `.venv`). Output của `parse_crossref_payload` trùng 24/24 record với snapshot. Test thêm: record trùng giữ bản `updated` mới hơn, whitespace thừa được chuẩn hóa, ngày `"not a date"` → `published = ""`, title rỗng bị loại; giả lập API trả 429 (3 lần gọi) và `ConnectionError` → cả hai fallback về snapshot, vẫn ra 24 record. Phase 1: `ChromaDB collection 'papers-baseline' indexed with 24 documents`, GX `PASSED`, freshness `COMPLIANT (4.2%)`. Corruption flow: `Repaired data cleanly rebuilt (24 rows)`, `IDEMPOTENT REPAIR VERIFIED`; lần chạy thứ 2 thoát với exit code 0 và `repaired_metrics.json` không đổi.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `data/clean/papers_clean.json`, `data/results/baseline_metrics.json`, `data/quality/freshness_report.json`. Commit: `d0ea007 feat(ingestion): implement Crossref ingestion and cleaning (CP0, CP1)`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** `fetch_source_records` có thể lấy dữ liệu từ Crossref API (dữ liệu mới) hoặc từ snapshot có sẵn. Crossref là nguồn sống: mỗi lần gọi API có thể trả tập bài khác, trong khi test set 10 câu và `ground_truth_doc_ids` của Huy được sinh từ đúng 24 bài trong snapshot.
- **Các phương án đã cân nhắc:**
  1. Luôn gọi API, chỉ dùng snapshot khi lỗi (đúng nghĩa đen của pseudo-code).
  2. Mặc định đọc snapshot, chỉ gọi API khi bật `REFRESH_SOURCE=1`; API lỗi thì vẫn fallback snapshot.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Với phương án 1, mỗi lần chạy thành công sẽ **ghi đè** `crossref_response.json` bằng tập bài khác → test set không còn khớp tài liệu, metric baseline/corrupted/repaired không so sánh được, và lần chạy repair không idempotent. Phương án 2 ưu tiên reproducibility; vẫn giữ được khả năng lấy dữ liệu mới có kiểm soát (cả nhóm thống nhất mới bật cờ). Ngoài ra raw response chỉ bị ghi khi API trả 200, nên một lần gọi lỗi không bao giờ làm hỏng bản gốc.
- **Bằng chứng quyết định phù hợp:** Sau khi chạy lệnh CP0, `git status` không thấy thay đổi trong `data/raw/`. Baseline (`run_phase1.py`) và Repaired (`run_corruption_flow.py`, clean lại từ cùng raw snapshot) cho metric giống hệt nhau: hit rate 1.0, token F1 1.0, judge score 5. Chạy `run_corruption_flow.py` hai lần cho `repaired_metrics.json` giống hệt từng byte.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Không phải lỗi runtime mà là rủi ro phát hiện khi đọc hợp đồng dữ liệu: nếu `published` được parse thành `pd.Timestamp` (hoặc `NaT`/`None` khi thiếu), `index.py` sẽ đưa giá trị đó vào metadata ChromaDB — ChromaDB chỉ nhận `str`/`int`/`float`/`bool` nên sẽ lỗi khi build index; đồng thời câu hỏi loại `date` so khớp ground truth dạng chuỗi `YYYY-MM-DD`.
- **Lệnh hoặc bước tái hiện:** Đọc `src/retrieval/index.py` (metadata `"published": row["published"]`) và `src/retrieval/qa.py` (trả về `metadata["published"]` làm đáp án).
- **Nguyên nhân gốc:** Cách làm tự nhiên là `pd.to_datetime` cả cột để tính `age_days`, việc này đổi kiểu cột `published` từ chuỗi sang datetime.
- **Cách xử lý:** Chỉ parse ngày trong hàm `_normalize_date` rồi trả lại chuỗi ISO (`""` khi không parse được); `age_days` tính từng dòng bằng `date.fromisoformat`. Cột `published`/`updated` luôn là chuỗi.
- **Cách xác minh sau khi sửa:** Assert mọi giá trị trong `published`, `authors_joined`, `categories_joined`, `title`, `paper_id` đều có kiểu `str`; `run_phase1.py` build collection `papers-baseline` đủ 24 docs không lỗi; `baseline_metrics.json` có `judge_accuracy = 1.0` (bao gồm câu hỏi loại `date`).
- **Điều học được:** Kiểu dữ liệu cũng là một phần của hợp đồng dữ liệu: một thay đổi kiểu "vô hại" ở bước clean có thể làm hỏng một module ở cách đó 3 bước.

Vấn đề còn mở:

- **Phạm vi bị ảnh hưởng:** Dòng có `published = ""` hiện nhận `age_days = -1`, nên `build_freshness_report` (đếm `age_days > 180`) sẽ **không** coi dòng đó là stale — một bài mất ngày xuất bản có thể lọt qua freshness SLA.
- **Những gì đã loại trừ:** Snapshot hiện tại không có bài nào thiếu ngày (24/24 có `published`), và `corruption.py` không làm rỗng ngày, nên metric hiện tại không bị ảnh hưởng.
- **Bước tiếp theo:** Thống nhất với Khánh thêm expectation `published` không rỗng / khớp regex `^\d{4}-\d{2}-\d{2}$` trong `quality.py`; kiểm chứng bằng một DataFrame có 1 dòng `published = ""` → GX phải trả `success = False`.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Crossref → vector index:** `fetch_source_records` lấy JSON Crossref (snapshot hoặc API), lưu nguyên bản vào `crossref_response.json`, parse thành `PaperRecord` và lưu `crossref_records.json`. `build_clean_dataframe` chuẩn hóa, dedupe, tính `age_days` và ghép `text_for_embedding`. `LocalEmbeddingIndex.build` embed `text_for_embedding` bằng `all-MiniLM-L6-v2` và ghi vào collection ChromaDB `papers-baseline`, kèm metadata (`published`, `authors_joined`, `categories_joined`) để agent trả lời.
2. **Evaluation set:** `testset.py` sinh 10 câu thuộc 4 loại (summary/authors/date/categories); mỗi câu có `ground_truth` (giá trị đúng) và `ground_truth_doc_ids` (`paper_id` của bài chứa đáp án). `retrieval_hit_rate` kiểm tra top-k tài liệu truy xuất có chứa doc id đúng không; `mean_token_f1` và judge so câu trả lời của agent với `ground_truth`.
3. **Quality checks vs freshness:** GX kiểm tra **tính đúng/đủ về cấu trúc** của từng bản chụp dữ liệu (số dòng, không null, `paper_id` duy nhất, độ dài summary/title). Freshness kiểm tra **độ cũ theo thời gian** (tỉ lệ `age_days > 180` phải ≤ 25%). Dữ liệu có thể đúng cấu trúc nhưng đã ôi, hoặc còn mới nhưng hỏng cấu trúc — nên cần cả hai.
4. **Cùng test set cho 3 trạng thái:** Để thay đổi của metric chỉ đến từ dữ liệu. Nếu sinh lại test set trên dữ liệu corrupted thì câu hỏi về bài bị xóa sẽ biến mất và hit rate trông vẫn "tốt" — che mất đúng lỗi cần đo.
5. **Repair thành công khi:** Repaired có GX `success = True`, `is_fresh = True`, đủ 24 dòng và các metric (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`) quay về bằng baseline; chạy repair lần 2 cho `repaired_metrics.json` giống hệt (idempotent). Đối chiếu qua `repaired_metrics.json`, `corrupted_quality_report.json` và `corruption_report.md`.

## 8. Phân tích kết quả

> **Nguồn số liệu:** `main` @ `48ab9c3`, `LLM_PROVIDER=mock`, ngày chạy 2026-09-25. Cột **Baseline** lấy từ `python script/run_phase1.py` (`data/results/baseline_metrics.json`, `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json`). Cột **Corrupted/Repaired** lấy từ `python script/run_corruption_flow.py` (`data/results/corrupted_metrics.json`, `repaired_metrics.json`, `corruption_log.json`, `data/quality/corrupted_*`/`repaired_*`, `data/reports/corruption_report.md`). Cả 3 trạng thái dùng chung test set 10 câu `data/eval/test_set.json`.

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |       0.8 |      1.0 | 2/10 câu mất tài liệu đúng vì `drop_latest` xóa 4 bài mới nhất |
| `mean_token_f1`      |      1.0 |    0.9741 |      1.0 | Tụt ít: agent vẫn trả lời bằng tài liệu gần giống |
| `judge_accuracy`     |      1.0 |       1.0 |      1.0 | Không phản ánh lỗi (judge heuristic khi chạy `mock`) |
| `mean_judge_score`   |        5 |       4.8 |        5 | Chỉ 1 câu bị chấm thấp hơn |
| Quality checks (GX)    |   `True` (7/7) |   `False` (4/7) |   `True` (7/7) | Corrupted fail 3 expectation: unique `paper_id`, độ dài `summary`, độ dài `title` |
| Freshness status       | `True` (1/24 stale, 4.17%) | `False` (6/22 stale, 27.27%) | `True` (1/24 stale, 4.17%) | `stale_date` đẩy tỉ lệ vượt ngưỡng 25% |

Corruption log: `drop_latest` 4 dòng, `blank_summary` 3, `inject_noise` 3, `truncate_title` 3, `stale_date` 4, `duplicate_rows` 2 → 24 → 22 dòng.

### Kết luận từ số liệu

1. **Data corruption → signal → metric:** `drop_latest` + `duplicate_rows` + `blank_summary` + `truncate_title` + `stale_date` → GX `success = False` (3 expectation fail) và `is_fresh = False` (27.27% > 25%) → `retrieval_hit_rate` 1.0 → 0.8, `mean_token_f1` 1.0 → 0.9741, `mean_judge_score` 5 → 4.8.
2. **Repair → signal → metric:** chạy lại `load_raw_records` + `build_clean_dataframe` từ `crossref_records.json` (không sửa tay DataFrame bẩn) → GX `True`, `is_fresh = True`, đủ 24 dòng → mọi metric quay về đúng baseline.

Corruption nào ảnh hưởng rõ nhất và vì sao?

`drop_latest` ảnh hưởng rõ nhất đến RAG: tài liệu đúng không còn trong index nên retrieval không thể trúng, dẫn tới hit rate mất 0.2. `duplicate_rows`, `blank_summary`, `truncate_title` không làm tụt metric (các bài bị ảnh hưởng không nằm trong đáp án của test set hoặc bản trùng vẫn truy xuất được) nhưng GX vẫn bắt được. Nhìn từ vai trò ingestion, điều này cho thấy giá trị của việc giữ raw snapshot: lỗi xóa dữ liệu không thể "sửa" trên DataFrame bẩn, chỉ có thể khôi phục bằng cách clean lại từ bản gốc.

Kết quả nào khác với kỳ vọng ban đầu?

Mình kỳ vọng row-count expectation sẽ bắt được việc mất 4 bài, nhưng 22 dòng vẫn nằm trong ngưỡng cho phép nên expectation này vẫn pass — GX fail là nhờ `paper_id` trùng và độ dài summary/title. Mình cũng kỳ vọng `judge_accuracy` giảm theo hit rate, nhưng nó vẫn là 1.0 vì với provider `mock` judge chạy heuristic và agent trả lời bằng tài liệu gần nhất thay vì nói "không biết". Chỉ `retrieval_hit_rate` (dựa trên `ground_truth_doc_ids`) cùng GX/freshness phát hiện được lỗi.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Raw data phải được bảo toàn nguyên bản và pipeline phải tái lập được. Việc mặc định đọc snapshot giúp baseline và repaired cho kết quả giống hệt nhau; nếu mỗi lần chạy lại kéo dữ liệu mới từ API thì không có mốc nào để so sánh.
2. **Data quality/observability:** Bước clean không nên "giấu" dữ liệu xấu. Mình chủ động không lọc summary rỗng/ngắn trong `cleaning.py` để GX là nơi quyết định và báo lỗi rõ ràng; kiểu dữ liệu (ngày là chuỗi) cũng là một phần của hợp đồng giữa các module.
3. **Ảnh hưởng của data đến RAG agent:** Dữ liệu hỏng không gây lỗi runtime — agent vẫn trả lời trơn tru và judge vẫn chấm đúng — nhưng retrieval đã sai tài liệu. Phải đo bằng doc id ground truth và chặn bằng quality gate trước khi dữ liệu vào vector store.

### Nếu có thêm thời gian

Bổ sung **schema/contract check ngay sau ingestion** (trước bước clean): kiểm tra `crossref_records.json` có đủ 11 trường, `published` khớp `YYYY-MM-DD`, `paper_id` duy nhất, và cảnh báo khi `age_days = -1` (thiếu ngày) — lấp lỗ hổng freshness nêu ở mục 6. Đo cải thiện bằng cách thêm một kịch bản corruption "blank published date": hiện tại freshness không phát hiện được; sau cải thiện, check phải trả `False` trong khi dữ liệu sạch vẫn `True`, và thêm pytest cho cả hai trường hợp.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đỗ Lê Việt Anh
**Ngày xác nhận:** 2026-09-25
