# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Quang Huy                     |
| MSSV               | 2A202602421                   |
| Email              | kamitoznguyen@gmail.com |
| Khóa/Lớp         | K4              |
| Tên nhóm         | Tralalelo Tralala     |
| Vai trò chính    | Trưởng nhóm · RAG & Vector Index · Benchmark Test Set |
| Repository         | https://github.com/kamitoznguyen-collab/K4A-DAY10-TralaleloTralala |
| Ngày hoàn thành | 2026-09-25               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Benchmark test set (CP2) | `src/evaluation/testset.py` · `build_test_set` | Clean DataFrame (24 dòng) | `data/eval/test_set.json` (10 câu) | Hoàn thành |
| Index manifest portable | `src/retrieval/index.py` · `_relative_persist_path`, `load` | ChromaDB `data/chroma/` | `data/embeddings/papers_embeddings*.json` với `persist_path` tương đối | Hoàn thành |
| Kiểm tra agent với provider `mock` | `src/retrieval/agent.py` | Index baseline | Ghi chú cho CP3 (demo cần `try/except`) | Hoàn thành |

`testset.py` là đầu vào của `evaluation/metrics.py::evaluate_pipeline` cho cả 3 trạng thái (Baseline / Corrupted / Repaired), nên Quân (`phase1.py`, `corruption_flow.py`) và Khánh (`reporting.py`) phụ thuộc trực tiếp vào output này. Index manifest là thứ mà mọi bước evaluate dùng để load lại ChromaDB.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Phân công & theo dõi tiến độ | Cả nhóm · `docs/TEAM.md` | Bảng phân công 5 người trên `main` |
| Tích hợp các nhánh vào `main` | Khánh (`feat/khanh-observability`), Lan (`nan-bi`) | Giải quyết conflict `docs/TEAM.md`, `src/observability/quality.py` (giữ bản của Khánh vì `reporting.py` dùng đúng schema của bản đó); merge commit `7357f23` |
| Kiểm thử tích hợp | Việt Anh, Khánh, Lan | CP0–CP2 pass; pytest của Lan 12/12 pass; GX trên dữ liệu corrupted trả `success=False` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Sinh 10 câu hỏi đủ 4 loại, có ground-truth doc id | `src/evaluation/testset.py` | `data/eval/test_set.json` | Lệnh nghiệm thu CP2 (mục 4) |
| Manifest index không còn hardcode đường dẫn tuyệt đối | `src/retrieval/index.py` | `persist_path = "data/chroma"` | Đọc manifest + `LocalEmbeddingIndex.load()` |
| Kiểm tra ChromaDB 3 collection tách biệt | `papers-baseline` / `papers-corrupted` / `papers-repaired` | 24 / 22 / 24 docs | `index.collection.count()` |
| Kiểm tra agent với `mock` | `src/retrieval/agent.py` | `build_agent` OK, `run_agent_question` raise `NotImplementedError` | Chạy thử với `LLM_PROVIDER=mock` |

Output cụ thể: lệnh CP2 in `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test`. Với test set này, baseline đạt `retrieval_hit_rate = 1.0`, và hit rate tụt còn `0.8` khi dữ liệu bị corrupt. Như vậy test set đủ nhạy để phát hiện mất dữ liệu.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Cần một bộ câu hỏi cố định, có đáp án và doc id chuẩn, để đo retrieval/answer quality **giống nhau** trên cả 3 trạng thái dữ liệu. Nếu test set thay đổi giữa các lần chạy thì không thể so sánh. Đồng thời index phải load được trên máy khác (máy giám khảo) mà không phụ thuộc đường dẫn tuyệt đối.

### Cách triển khai

- **Test set:** lọc các bài có đủ summary/authors/categories và title không chứa dấu `'` (vì `qa.py` tách title bằng regex `'([^']+)'`). Sắp xếp theo `published` giảm dần (tie-break bằng `paper_id`), rồi chọn 10 bài trải đều từ mới nhất tới cũ nhất, trong đó luôn có bài mới nhất. Các loại câu hỏi xoay vòng `summary, authors, date, categories` (3 summary, 3 authors, 2 date, 2 categories). Câu hỏi dùng đúng cụm từ mà `retrieval/qa.py::_extract_answer` nhận diện (`Who authored`, `When was`, `What categories`). Ground truth lấy từ cột tương ứng: `authors_joined`, `published`, `categories_joined`, còn summary lấy câu đầu tiên.
- **Index:** khi build, `persist_path` được lưu tương đối với `project_dir` (`data/chroma`); khi load, nếu là đường dẫn tương đối thì ghép lại với `project_dir`. Nếu thư mục Chroma nằm ngoài project thì vẫn giữ đường dẫn tuyệt đối (fallback) để không làm hỏng trường hợp đặc biệt.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Clean DataFrame: `paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined` |
| Output                         | List 10 dict: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids` → ghi `data/eval/test_set.json` |
| Module phụ thuộc             | `ingestion/cleaning.py`, `core/utils.py` (`first_sentence`, `write_json`) |
| Module sử dụng output        | `evaluation/metrics.py`, `pipelines/phase1.py`, `pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | Ít hơn 10 bài hợp lệ → `ValueError`; title có dấu `'` bị loại; bài thiếu summary/authors/categories bị loại |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
```

- **Kết quả mong đợi:** `Sinh được 10 câu hỏi test`, đủ 4 loại câu hỏi, mọi `ground_truth_doc_ids` đều có trong dataset.
- **Kết quả thực tế:** `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test`, loại: `authors`, `categories`, `date`, `summary`. Manifest có `persist_path = "data/chroma"`, `load()` trả về 24 docs.
- **Artifact/log:** `data/eval/test_set.json`, `data/embeddings/papers_embeddings.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn 10 bài nào trong 24 bài để làm test set.
- **Các phương án đã cân nhắc:** (1) chọn ngẫu nhiên; (2) chọn 10 bài mới nhất; (3) chọn trải đều từ mới nhất tới cũ nhất.
- **Phương án đã chọn:** (3) trải đều, luôn có bài mới nhất.
- **Lý do:** Không dùng random nên chạy lại vẫn ra cùng một test set (reproducible, bắt buộc để so sánh 3 trạng thái). Có bài mới nhất nên lỗi "drop latest" làm tụt hit rate. Trải đều thì các loại lỗi khác (stale date, blank summary, noise…) cũng có cơ hội chạm vào test set, trong khi phương án (2) chỉ phản ánh nhóm bài mới.
- **Bằng chứng quyết định phù hợp:** `retrieval_hit_rate` Baseline `1.0` → Corrupted `0.8`. Cả 2 câu trượt (`eval_001`, `eval_002`) đều hỏi về các bài mới nhất bị `drop_latest` xoá, đúng như mục đích chọn bài mới nhất vào test set.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Manifest `data/embeddings/papers_embeddings.json` lưu `"persist_path": "D:\\..."`, tức đường dẫn tuyệt đối trên máy người build.
- **Lệnh hoặc bước tái hiện:** Build index trên một máy, clone repo sang thư mục/máy khác rồi gọi `LocalEmbeddingIndex.load(settings)`.
- **Nguyên nhân gốc:** `build()` ghi `str(persist_path)` sau khi resolve thành đường dẫn tuyệt đối, và `load()` dùng thẳng giá trị này nên trỏ tới thư mục không tồn tại trên máy khác. Đây cũng là lỗi hardcode path bị trừ điểm trong rubric.
- **Cách xử lý:** Thêm `_relative_persist_path()` để lưu đường dẫn tương đối với `project_dir`; `load()` ghép lại với `project_dir` nếu đường dẫn không tuyệt đối.
- **Cách xác minh sau khi sửa:** Build index trong một bản clone ở thư mục khác: manifest chứa `persist_path = "data/chroma"`; `LocalEmbeddingIndex.load()` load lại được 24 docs và `search()` trả về top-3.
- **Điều học được:** Artifact được commit vào repo (manifest, JSON report) phải độc lập với máy chạy. Mọi đường dẫn nên lưu tương đối với gốc project và chỉ resolve khi dùng.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Từ Crossref đến vector index:** `crossref.py` đọc snapshot offline `data/raw/crossref_response.json` (chỉ gọi API khi `REFRESH_SOURCE=1`), bóc tag JATS, map thành `PaperRecord` và ghi `crossref_records.json`. `cleaning.py` chuẩn hoá text, dedupe theo `paper_id`, tính `age_days` và ghép `text_for_embedding` (Title/Authors/Published/Categories/Summary). `index.py` embed cột đó bằng `all-MiniLM-L6-v2` và nạp vào collection ChromaDB tương ứng với trạng thái (`papers-baseline`/`-corrupted`/`-repaired`), kèm manifest JSON để load lại.
2. **Evaluation set và ground-truth doc id:** mỗi câu hỏi gắn với đúng 1 `paper_id`. `retrieval_hit_rate` = tỉ lệ câu mà doc id đúng nằm trong top-k kết quả retrieve, đo phần *retrieval*. `mean_token_f1` và `judge_accuracy` so câu trả lời với `ground_truth`, đo phần *answer*. Có doc id nên phân biệt được "trả lời đúng nhờ tìm đúng tài liệu" với "trả lời trùng hợp từ tài liệu khác".
3. **Quality checks khác freshness:** quality checks (GX 1.x) kiểm tra *cấu trúc/nội dung* tại một thời điểm: số dòng, không null, `paper_id` unique, độ dài summary/title. Freshness kiểm tra *tuổi dữ liệu* so với SLA: tỉ lệ bài có `age_days > 180` phải ≤ 25%. Dữ liệu có thể hợp lệ về schema nhưng vẫn cũ, và ngược lại.
4. **Vì sao dùng cùng test set:** để mọi chênh lệch metric chỉ đến từ dữ liệu. Nếu đổi test set thì không biết metric tụt là do dữ liệu hỏng hay do câu hỏi khó hơn.
5. **Repair thành công dựa trên:** `data/quality/*` (GX `success=True`, `is_fresh=True`), `repaired_metrics.json` quay về bằng baseline, và `corruption_report.md` so 3 trạng thái. Repair phải idempotent: chạy lại cho cùng kết quả vì luôn clean lại từ raw snapshot chứ không vá tay dữ liệu bẩn.

## 8. Phân tích kết quả

> Số liệu đo trên code `main` @ `56788c9` với `LLM_PROVIDER=mock`, theo đúng luồng CP3/CP5: clean → index → evaluate; corrupt bằng `corrupt_clean_dataframe`; repair bằng cách clean lại từ `crossref_records.json`. Cùng một test set 10 câu cho cả 3 trạng thái. Khi `script/run_phase1.py` và `script/run_corruption_flow.py` hoàn thiện, cần đối chiếu lại với `data/results/*_metrics.json`.

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |       0.8 |      1.0 | 2/10 câu mất tài liệu đúng do `drop_latest` |
| `mean_token_f1`      |      1.0 |    0.9741 |      1.0 | Tụt ít vì agent vẫn trả lời bằng tài liệu khác có nội dung gần giống |
| `judge_accuracy`     |      1.0 |       1.0 |      1.0 | Không phát hiện được lỗi (xem phân tích bên dưới) |
| `mean_judge_score`   |        5 |       4.8 |        5 | Chỉ `eval_001` bị chấm 3/5 |
| Quality checks (GX)    |   `True` |   `False` |   `True` | Corrupted fail 3 expectation: unique `paper_id`, độ dài summary, độ dài title |
| Freshness status       | `True` (1/24 stale, 4.17%) | `False` (6/22 stale, 27.27%) | `True` (1/24 stale, 4.17%) | Stale date đẩy tỉ lệ stale vượt ngưỡng 25% |

Corruption log: `drop_latest` 4 dòng, `blank_summary` 3, `inject_noise` 3, `truncate_title` 3, `stale_date` 4, `duplicate_rows` 2 (24 → 22 dòng).

### Kết luận từ số liệu

1. **Corruption → signal → metric:** `drop_latest` + `duplicate_rows` + `truncate_title` + `blank_summary` + `stale_date` → GX `success=False` (fail unique, độ dài summary, độ dài title) và `is_fresh=False` (27.27% > 25%) → `retrieval_hit_rate` 1.0 → 0.8, `mean_token_f1` 1.0 → 0.974, `mean_judge_score` 5 → 4.8.
2. **Repair → signal → metric:** clean lại từ raw snapshot → GX `success=True`, `is_fresh=True`, lại đủ 24 docs → mọi metric quay về đúng bằng baseline (hit rate 1.0, F1 1.0, judge score 5).

Corruption nào ảnh hưởng rõ nhất và vì sao?

`drop_latest` ảnh hưởng rõ nhất tới RAG: cả 2 câu trượt (`eval_001`, `eval_002`) đều hỏi về bài bị xoá. Các lỗi khác (noise, title bị cắt, summary rỗng) rơi vào bài không nằm trong test set nên không làm tụt metric, nhưng GX vẫn bắt được. Điều này cho thấy quality gate cần thiết: nếu chỉ nhìn metric RAG thì đã bỏ sót 3/6 loại lỗi.

Kết quả nào khác với kỳ vọng ban đầu?

Mình kỳ vọng `judge_accuracy` tụt cùng hit rate, nhưng nó vẫn là `1.0`. Kiểm tra `corrupted_answers.json`: khi tài liệu gốc bị xoá, agent **không trả lời "không biết"** mà lấy tài liệu gần nhất để trả lời. Ở `eval_002`, tài liệu khác trùng tác giả nên token F1 vẫn 1.0. Judge đang chạy ở chế độ heuristic fallback (`mock` không gọi được LLM evaluator) nên chấm "correct". Đây chính là **silent failure**: câu trả lời nghe hợp lý nhưng dựa trên sai tài liệu. Chỉ `retrieval_hit_rate` (dựa trên ground-truth doc id) và GX/freshness mới phát hiện được. Row-count expectation (20–30) cũng không bắt được việc mất 4 bài vì 22 dòng vẫn trong ngưỡng.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** pipeline phải reproducible. Test set chọn tất định, raw snapshot bất biến, repair bằng cách chạy lại từ raw, artifact lưu đường dẫn tương đối. Thiếu một trong các điều này thì không so sánh được 3 trạng thái.
2. **Data quality/observability:** quality check và freshness bổ sung cho nhau. Trong lần đo này, 3/6 loại lỗi không làm tụt metric RAG, chỉ GX/freshness bắt được. Kiểm soát dữ liệu phải đặt *trước* vector DB chứ không chờ metric agent.
3. **Ảnh hưởng tới RAG agent:** khi mất tài liệu, agent vẫn trả lời tự tin bằng tài liệu gần nhất, và judge heuristic không phát hiện ra. Metric dựa trên ground-truth doc id đáng tin hơn metric chấm câu trả lời.

### Nếu có thêm thời gian

- Thêm expectation so sánh với baseline, ví dụ số dòng không được giảm quá 5% so với lần chạy trước, để bắt `drop_latest` mà row-count 20–30 bỏ sót. Đo bằng cách chạy lại corruption flow và kiểm tra GX có fail thêm expectation này không.
- Cho agent trả lời "không biết" khi điểm similarity của top-1 thấp hơn ngưỡng, rồi so `judge_accuracy` ở trạng thái corrupted trước/sau: kỳ vọng judge accuracy tụt theo hit rate thay vì giữ 1.0.

## 10. Cam kết của thành viên

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Quang Huy
**Ngày xác nhận:** 2026-09-25
