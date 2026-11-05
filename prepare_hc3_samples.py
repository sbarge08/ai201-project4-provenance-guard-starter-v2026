#!/usr/bin/env python3
"""Create a pinned, deterministic HC3 paired-sample evaluation file."""

import argparse
import datetime as dt
import json
import urllib.parse
import urllib.request
from pathlib import Path

DATASET = "Hello-SimpleAI/HC3"
REVISION = "4d0ff18143b5a7e1b1e79beb540c04549d1e59d3"
SUBSET = "wiki_csai"
SPLIT = "train"
SAMPLE_COUNT = 20
ROWS_TO_FETCH = 100
PUBLICATION = (
    "Guo et al. (2023), How Close is ChatGPT to Human Experts? "
    "Comparison Corpus, Evaluation, and Detection, arXiv:2301.07597."
)
PAPER_URL = "https://arxiv.org/abs/2301.07597"
DATASET_URL = f"https://huggingface.co/datasets/{DATASET}"
LICENSE_NOTE = (
    "The Hugging Face dataset card declares CC-BY-SA-4.0 and states that "
    "stricter source-dataset licenses apply. The project copyright table "
    "identifies the wiki_csai source as Wikipedia under CC-BY-SA."
)


def fetch_rows() -> list[dict]:
    query = urllib.parse.urlencode({
        "dataset": DATASET,
        "config": SUBSET,
        "split": SPLIT,
        "offset": 0,
        "length": ROWS_TO_FETCH,
        "revision": REVISION,
    })
    url = f"https://datasets-server.huggingface.co/rows?{query}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AI201-Provenance-Guard/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
        raise ValueError("HC3 rows API returned an unexpected response.")
    return payload["rows"]


def sample_record(row_item: dict, answer: str, label: str, answer_field: str) -> dict:
    row = row_item["row"]
    row_id = str(row["id"])
    row_index = int(row_item["row_idx"])
    pair_id = f"{SUBSET}:{row_id}"
    row_api = (
        "https://datasets-server.huggingface.co/rows?"
        + urllib.parse.urlencode({
            "dataset": DATASET,
            "config": SUBSET,
            "split": SPLIT,
            "offset": row_index,
            "length": 1,
            "revision": REVISION,
        })
    )
    return {
        "id": f"HC3-WIKI-CSAI-{row_index:05}-{label.upper()}",
        "text": answer,
        "provenance": {
            "authorship": f"dataset_labeled_{label}",
            "dataset": DATASET,
            "dataset_revision": REVISION,
            "publication": PUBLICATION,
            "subset": SUBSET,
            "split": SPLIT,
            "row_id": row_id,
            "row_index": row_index,
            "source_label": answer_field,
            "pair_id": pair_id,
            "question": row["question"],
            "source_reference": (
                f"{DATASET_URL}/viewer/{SUBSET}/{SPLIT}?row={row_index}"
            ),
            "row_api_reference": row_api,
            "authorship_uncertainty": (
                "The HC3 row labels this answer as human and identifies the "
                "Wikipedia source, but supplies no individual author identity or "
                "independent authorship verification."
                if label == "human"
                else
                "The HC3 row labels this answer as ChatGPT-generated. The "
                "published row does not provide an individual generation "
                "timestamp or exact serving-model version."
            ),
        },
    }


def build_samples(rows: list[dict]) -> dict:
    human_samples = []
    ai_samples = []
    seen_texts = set()
    seen_questions = set()

    for row_item in sorted(rows, key=lambda item: int(item["row_idx"])):
        row = row_item.get("row", {})
        question = row.get("question")
        human_answers = row.get("human_answers")
        chatgpt_answers = row.get("chatgpt_answers")
        if (
            not isinstance(question, str)
            or not question.strip()
            or not isinstance(human_answers, list)
            or not isinstance(chatgpt_answers, list)
            or not human_answers
            or not chatgpt_answers
        ):
            continue

        human_text = human_answers[0]
        ai_text = chatgpt_answers[0]
        if (
            not isinstance(human_text, str)
            or not human_text.strip()
            or len(human_text) > 5000
            or not isinstance(ai_text, str)
            or not ai_text.strip()
            or len(ai_text) > 5000
            or human_text == ai_text
            or human_text in seen_texts
            or ai_text in seen_texts
            or question in seen_questions
        ):
            continue

        human_samples.append(
            sample_record(row_item, human_text, "human", "human_answers")
        )
        ai_samples.append(
            sample_record(row_item, ai_text, "chatgpt", "chatgpt_answers")
        )
        seen_texts.update((human_text, ai_text))
        seen_questions.add(question)
        if len(human_samples) == SAMPLE_COUNT:
            break

    if len(human_samples) != SAMPLE_COUNT:
        raise ValueError(
            f"Pinned HC3 rows yielded {len(human_samples)} eligible pairs; "
            f"expected {SAMPLE_COUNT}."
        )

    return {
        "dataset_provenance": {
            "dataset": DATASET,
            "revision": REVISION,
            "publication": PUBLICATION,
            "publication_url": PAPER_URL,
            "dataset_url": DATASET_URL,
            "subset": SUBSET,
            "split": SPLIT,
            "license": LICENSE_NOTE,
            "chatgpt_model_context": (
                "The paper describes ChatGPT as based on the GPT-3.5 series; "
                "the individual rows do not identify an exact serving version "
                "or generation timestamp."
            ),
            "selection": (
                "At the pinned revision, scan wiki_csai/train rows in "
                "ascending row_idx and take the first 20 with nonempty question, "
                "nonempty first human_answers and chatgpt_answers, each answer "
                "at most 5,000 characters, distinct answer texts, and a question "
                "not previously selected. Selection does not inspect classifier "
                "scores."
            ),
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(
                timespec="seconds"
            ),
            "verified_human_samples_available": 0,
        },
        "human": human_samples,
        "ai": ai_samples,
        "verified_human": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "evaluation_samples.json",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        parser.error(f"{args.output} already exists; pass --force to replace it.")

    samples = build_samples(fetch_rows())
    args.output.write_text(
        json.dumps(samples, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {SAMPLE_COUNT} matched HC3 human/ChatGPT pairs to {args.output}"
    )


if __name__ == "__main__":
    main()
