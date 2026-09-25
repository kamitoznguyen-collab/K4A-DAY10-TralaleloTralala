from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

MIN_DOCUMENTS = 10
# 10 cau, du 4 loai. Cau hoi dung dung cum tu ma `retrieval.qa._extract_answer` nhan dien,
# title dat trong nhay don de `answer_question` lookup chinh xac.
QUESTION_PLAN = ["summary", "authors", "date", "categories"] * 2 + ["summary", "authors"]
QUESTION_TEMPLATES = {
    "summary": "What is the summary of the paper '{title}'?",
    "authors": "Who authored the paper '{title}'?",
    "date": "When was the paper '{title}' published?",
    "categories": "What categories does the paper '{title}' belong to?",
}


def _ground_truth(row: pd.Series, question_type: str) -> str:
    if question_type == "summary":
        return first_sentence(row["summary"])
    if question_type == "authors":
        return row["authors_joined"]
    if question_type == "date":
        return row["published"]
    return row["categories_joined"]


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao 10 cau hoi benchmark (summary/authors/date/categories) tu cleaned dataframe."""
    candidates = df[
        ~df["title"].str.contains("'", regex=False)
        & (df["summary"].str.len() > 0)
        & (df["authors_joined"].str.len() > 0)
        & (df["categories_joined"].str.len() > 0)
    ].drop_duplicates("paper_id")
    candidates = candidates.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    if len(candidates) < MIN_DOCUMENTS:
        raise ValueError(f"Need at least {MIN_DOCUMENTS} usable documents to build the test set, got {len(candidates)}.")

    # Chon 10 paper trai deu tu moi -> cu (co ca bai moi nhat de do tac dong khi mat du lieu tuoi).
    step = len(candidates) / len(QUESTION_PLAN)
    picks = [candidates.iloc[int(position * step)] for position in range(len(QUESTION_PLAN))]

    test_set: list[dict[str, Any]] = []
    for number, (row, question_type) in enumerate(zip(picks, QUESTION_PLAN, strict=True), start=1):
        test_set.append(
            {
                "id": f"eval_{number:03d}",
                "question_type": question_type,
                "question": QUESTION_TEMPLATES[question_type].format(title=row["title"]),
                "ground_truth": _ground_truth(row, question_type),
                "ground_truth_doc_ids": [row["paper_id"]],
            }
        )

    write_json(output_path, test_set)
    return test_set
