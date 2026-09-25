# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Quang Huy                     |
| MSSV               | 2A202602421                   |
| Khóa/Lớp         | K4              |
| Tên nhóm         | Tralalelo Tralala     |
| Vai trò chính    | Trưởng nhóm · RAG & Vector Index · Benchmark Test Set |
| Repository         | https://github.com/kamitoznguyen-collab/K4A-DAY10-TralaleloTralala |
| Ngày hoàn thành | [YYYY-MM-DD]               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Benchmark test set (CP2) | `src/evaluation/testset.py` · `build_test_set` | Clean DataFrame (24 dòng) | `data/eval/test_set.json` (10 câu) | Hoàn thành |
| Index manifest portable | `src/retrieval/index.py` · `_relative_persist_path`, `load` | ChromaDB `data/chroma/` | `data/embeddings/papers_embeddings*.json` với `persist_path` tương đối | Hoàn thành |
| Kiểm tra agent với provider `mock` | `src/retrieval/agent.py` | Index baseline | Ghi chú cho CP3 (demo cần `try/except`) | Hoàn thành |

`testset.py` là đầu vào của `evaluation/metrics.py::evaluate_pipeline` cho cả 3 trạng thái (Baseline / Corrupted / Repaired), nên Quân (`phase1.py`, `corruption_flow.py`) và Khánh (`reporting.py`) phụ thuộc trực tiếp vào output này.

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
| Kiểm tra ChromaDB | collection `papers-baseline` | 24 docs | `index.collection.count()` |

Output cụ thể: lệnh CP2 in `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test`; index baseline load lại được từ manifest với 24 docs.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Cần một bộ câu hỏi cố định, có đáp án và doc id chuẩn, để đo retrieval/answer quality giống nhau trên cả 3 trạng thái dữ liệu. Đồng thời index phải load được trên máy khác (máy giám khảo) mà không phụ thuộc đường dẫn tuyệt đối.

### Cách triển khai

- **Test set:** lọc các bài có đủ summary/authors/categories và title không chứa dấu `'` (vì `qa.py` tách title bằng regex `'([^']+)'`). Sắp xếp theo `published` giảm dần rồi chọn 10 bài trải đều từ mới nhất tới cũ nhất, trong đó luôn có bài mới nhất để lỗi "drop latest" của CP4 làm tụt hit rate thấy rõ. Phân bổ loại câu `summary, authors, date, categories` xoay vòng (3 summary, 3 authors, 2 date, 2 categories). Câu hỏi dùng đúng cụm từ mà `retrieval/qa.py::_extract_answer` nhận diện (`Who authored`, `When was`, `What categories`).
- **Index:** khi build, `persist_path` được lưu tương đối với `project_dir` (`data/chroma`); khi load, nếu là đường dẫn tương đối thì ghép lại với `project_dir`.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Clean DataFrame: `paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined` |
| Output                         | List 10 dict: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids` |
| Module phụ thuộc             | `ingestion/cleaning.py`, `core/utils.py` (`first_sentence`, `write_json`) |
| Module sử dụng output        | `evaluation/metrics.py`, `pipelines/phase1.py`, `pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | Ít hơn 10 bài hợp lệ → `ValueError`; title có dấu `'` bị loại |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
```

- **Kết quả mong đợi:** `Sinh được 10 câu hỏi test`, đủ 4 loại câu hỏi.
- **Kết quả thực tế:** `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test`, loại: `authors`, `categories`, `date`, `summary`.
- **Artifact/log:** `data/eval/test_set.json`, `data/embeddings/papers_embeddings.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn 10 bài nào trong 24 bài để làm test set.
- **Các phương án đã cân nhắc:** (1) chọn ngẫu nhiên; (2) chọn 10 bài mới nhất; (3) chọn trải đều từ mới nhất tới cũ nhất.
- **Phương án đã chọn:** (3) trải đều, có bài mới nhất.
- **Lý do:** Không dùng random nên chạy lại vẫn ra cùng một test set (reproducible). Có bài mới nhất nên lỗi "drop latest" làm tụt hit rate. Trải đều thì các loại lỗi khác (stale date, blank summary…) cũng có cơ hội chạm vào test set, trong khi phương án (2) chỉ phản ánh nhóm bài mới.
- **Bằng chứng quyết định phù hợp:** [Điền `retrieval_hit_rate` Baseline vs Corrupted từ `data/results/baseline_metrics.json` và `corrupted_metrics.json`.]

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Manifest `data/embeddings/papers_embeddings.json` lưu `"persist_path": "D:\\..."` (đường dẫn tuyệt đối trên máy người build).
- **Lệnh hoặc bước tái hiện:** Build index trên một máy, clone repo sang thư mục/máy khác rồi gọi `LocalEmbeddingIndex.load(settings)`.
- **Nguyên nhân gốc:** `build()` ghi `str(persist_path)` sau khi resolve thành đường dẫn tuyệt đối, và `load()` dùng thẳng giá trị này.
- **Cách xử lý:** Thêm `_relative_persist_path()` để lưu đường dẫn tương đối với `project_dir`; `load()` ghép lại với `project_dir` nếu đường dẫn không tuyệt đối.
- **Cách xác minh sau khi sửa:** Manifest chứa `persist_path = "data/chroma"`; `LocalEmbeddingIndex.load()` load lại được 24 docs và `search()` trả về top-3.
- **Điều học được:** [Tự điền.]

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

[Tự viết bằng lời của bạn cho 5 câu hỏi trong mẫu.]

## 8. Phân tích kết quả

> Điền sau khi chạy `python script/run_phase1.py` và `python script/run_corruption_flow.py` (lấy số từ `data/results/*.json`, không tự đặt số).

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      [ ] |       [ ] |      [ ] | [Nhận xét]              |
| `mean_token_f1`      |      [ ] |       [ ] |      [ ] | [Nhận xét]              |
| `judge_accuracy`     |      [ ] |       [ ] |      [ ] | [Nhận xét]              |
| `mean_judge_score`   |      [ ] |       [ ] |      [ ] | [Nhận xét]              |
| Quality checks         |      [ ] |       [ ] |      [ ] | [Nhận xét]              |
| Freshness status       |      [ ] |       [ ] |      [ ] | [Nhận xét]              |

### Kết luận từ số liệu

1. [Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi].
2. [Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi hoặc chưa phục hồi].

Corruption nào ảnh hưởng rõ nhất và vì sao?

[Phân tích dựa trên số liệu.]

Kết quả nào khác với kỳ vọng ban đầu?

[Nêu kết quả, giả thuyết và cách đã kiểm tra.]

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. [Tự điền]
2. [Tự điền]
3. [Tự điền]

### Nếu có thêm thời gian

[Tự điền]

## 10. Cam kết của thành viên

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Quang Huy
**Ngày xác nhận:** [YYYY-MM-DD]
