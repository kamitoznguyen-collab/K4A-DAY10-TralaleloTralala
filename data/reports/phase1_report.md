# Baseline Data Pipeline & Observability Report (Phase 1)

> **Pipeline Phase:** Phase 1 — Clean Baseline & Ingestion Verification  
> **Generated At:** `2026-09-25T10:21:50.658811+00:00`  
> **Environment:** Ephemeral Great Expectations 1.x + Local ChromaDB Vector Index  
> **Author Role:** Observability & Reporting Lead (Khánh)

---

## 1. Executive Summary

Phase 1 establishes the clean baseline for the Day 10 Data Pipeline. The pipeline ingests academic metadata from Crossref, normalizes text into 5-layer embedding documents (`text_for_embedding`), indexes them into ChromaDB (`papers-baseline`), runs automated Data Quality verification via **Great Expectations 1.x**, enforces the **Freshness SLA**, and establishes benchmark performance over a standardized 10-question evaluation test set.

| Verification Pillar | Target Standard | Observed Status | Verdict |
| :--- | :--- | :---: | :---: |
| **Ingestion Completeness** | 20 – 30 academic records | **24 records** | ✅ MET |
| **Data Quality Gate (GX 1.x)** | 100% core expectations met | **7/7 (100.0%)** | ✅ PASSED |
| **Freshness SLA (<25% stale)** | Stale ratio <= 0.25 (180 days) | **4.2% (1/24 rows)** | ✅ COMPLIANT |
| **RAG Retrieval Hit Rate** | >= 90.0% on clean index | **100.0%** | ✅ MET |
| **Answer Semantic Token F1** | Baseline benchmark | **1.0000** | ✅ BASELINE |

---

## 2. Ingestion & Source Data Lineage

- **Source Provider:** `Local Raw Snapshot (Fallback)`
- **Preserved Raw Artifacts:**
  - `data/raw/crossref_response.json`: Raw unmodified API response preserving origin lineage.
  - `data/raw/crossref_records.json`: Parsed `PaperRecord` objects schema-conforming.
- **Clean Ingestion Output:**
  - `data/clean/papers_clean.csv` & `data/clean/papers_clean.json` (24 rows, 0 duplicate DOI).
- **Composite Context Structure (`text_for_embedding`):**
  Each record synthesizes 5 structured lines (`Title`, `Authors`, `Published`, `Categories`, `Summary`) stripped of XML/JATS tags and redundant whitespaces.

---

## 3. Data Observability Gate (Great Expectations 1.x)

Data validation is implemented with Great Expectations 1.x using the modern **Ephemeral Context** API (`gx.get_context(mode="ephemeral")`), preventing persistent configuration baggage while delivering deterministic in-memory validation.

### Expectation Suite Results
| # | Expectation Type | Validated Parameters | Result |
| :-: | :--- | :--- | :---: |
| 1 | `expect_table_row_count_to_be_between` | `min_value=20, max_value=30` | ✅ PASS |
| 2 | `expect_column_values_to_not_be_null` | `column=paper_id` | ✅ PASS |
| 3 | `expect_column_values_to_be_unique` | `column=paper_id` | ✅ PASS |
| 4 | `expect_column_values_to_not_be_null` | `column=title` | ✅ PASS |
| 5 | `expect_column_value_lengths_to_be_between` | `column=title, min_value=8` | ✅ PASS |
| 6 | `expect_column_values_to_not_be_null` | `column=text_for_embedding` | ✅ PASS |
| 7 | `expect_column_value_lengths_to_be_between` | `column=summary, min_value=30` | ✅ PASS |

- **Total Expectations Evaluated:** `7`
- **Passed Expectations:** `7`
- **Failed Expectations:** `0`
- **Overall Gate Status:** **✅ PASSED**

---

## 4. Freshness SLA Monitoring

Academic retrieval systems require recent literature to avoid serving obsolete citations. The Freshness SLA verifies that the proportion of papers older than **180 days** does not exceed **25%**.

| Freshness Metric | Value | Reference Standard |
| :--- | :--- | :--- |
| **Latest Publication Date** | `2026-07-22` | Most recent record in corpus |
| **Oldest Publication Date** | `2026-03-28` | Historical boundary |
| **Freshness Age Threshold** | `180 days` (~6 months) | Pipeline configuration SLA |
| **Stale Record Count (>180 days)** | `1` records | Records exceeding age threshold |
| **Stale Ratio** | `4.2%` (`1/24`) | **Threshold: <= 25.0%** |
| **Freshness SLA Verdict** | **✅ COMPLIANT** | Compliant with SLA |

> 📌 **Note on Baseline Freshness:** As of late September 2026, the oldest records in the snapshot (published late March 2026) have reached ~181 days. Because only a minimal fraction (1/24 = 4.2%) exceeds the 180-day threshold, the dataset safely respects the <= 25% threshold, yielding `is_fresh = True`.

---

## 5. Baseline RAG Benchmark & Retrieval Metrics

Using ChromaDB collection `papers-baseline` with sentence-transformer `all-MiniLM-L6-v2`:

| Metric Name | Baseline Value | Description |
| :--- | :---: | :--- |
| **Evaluation Test Samples** | `10` questions | 4 question categories: `summary`, `authors`, `date`, `categories` |
| **Retrieval Hit Rate** | **100.0%** | Fraction of queries where ground-truth document was retrieved in Top-K |
| **Mean Token F1** | **1.0000** | Unigram token overlap between RAG response and ground truth |
| **Judge Accuracy** | **100.0%** | LLM judge binary accuracy score |
| **Mean Judge Score** | **5.0000** | Normalized scalar quality score (0.0 – 1.0) |

### RAGAS Metrics\n```json\n{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}\n```

---

## 6. Phase 1 Sign-Off & Next Steps

All baseline gates passed successfully. The clean dataset, ChromaDB index, and evaluation test set are certified ready for Phase 2: **Synthetic Data Corruption & Resilience Analysis**.
