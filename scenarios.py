"""Reproducible tests for the five original acceptance criteria."""

import json
from pathlib import Path

import config

SAMPLE_FILE = config.ROOT / "evaluation_samples.json"
HUMAN_EVALUATION_COUNT = 20
HUMAN_SAMPLE_COUNT = 20
AI_SAMPLE_COUNT = 20

SCENARIOS = [
    {
        "criterion": 1,
        "name": "verified human false positives",
        "kind": "classifications",
        "dataset": "verified_human",
        "sample_count": HUMAN_EVALUATION_COUNT,
        "target": "At most 1 of 20 verified human-written samples receives the high-confidence AI label in each trial.",
    },
    {
        "criterion": 2,
        "name": "verified AI-human score separation",
        "kind": "score_separation",
        "sample_count": AI_SAMPLE_COUNT,
        "target": "Mean AI combined score minus mean human combined score is at least 0.20 in each trial, using 20 verified samples per group.",
    },
    {
        "criterion": 3,
        "name": "label coverage and boundaries",
        "kind": "label_coverage",
        "target": "All three labels are reachable; every score from 0 through 1 maps to exactly one label, including threshold and adjacent cases.",
    },
    {
        "criterion": 4,
        "name": "valid appeals and append-only decisions",
        "kind": "appeals",
        "sample_count": 10,
        "target": "10/10 valid appeals are recorded as under_review in each trial, and each original decision remains in the audit log.",
    },
    {
        "criterion": 5,
        "name": "invalid submission handling",
        "kind": "invalid_submissions",
        "sample_count": 6,
        "target": "All six predefined invalid requests receive 4xx responses and create no valid classification decision in each trial.",
    },
]

INVALID_CASES = [
    {
        "case": "missing_text",
        "body": {"creator_id": "placeholder"},
    },
    {
        "case": "empty_text",
        "body": {"text": "", "creator_id": "placeholder"},
    },
    {
        "case": "whitespace_text",
        "body": {"text": " \t\n ", "creator_id": "placeholder"},
    },
    {
        "case": "nonstring_text",
        "body": {"text": 12345, "creator_id": "placeholder"},
    },
    {
        "case": "missing_creator_id",
        "body": {"text": "A valid text field without a creator ID."},
    },
    {
        "case": "text_over_5000_characters",
        "body": {"text": "x" * 5001, "creator_id": "placeholder"},
    },
]


def _validate_samples(
    samples: object,
    kind: str,
    expected_count: int,
    expected_authorship: str,
    dataset_provenance: dict,
) -> list[dict]:
    if not isinstance(samples, list) or len(samples) != expected_count:
        actual_count = len(samples) if isinstance(samples, list) else 0
        raise ValueError(
            f"{kind} dataset must contain exactly {expected_count} samples; "
            f"found {actual_count}."
        )

    required_fields = (
        (
            "dataset",
            "dataset_revision",
            "publication",
            "subset",
            "split",
            "row_id",
            "source_label",
            "pair_id",
            "question",
            "source_reference",
            "row_api_reference",
            "authorship_uncertainty",
        )
        if expected_authorship.startswith("dataset_labeled_")
        else ("verification_method", "evidence")
    )
    seen_ids = set()
    checked = []
    for index, sample in enumerate(samples, 1):
        if not isinstance(sample, dict):
            raise ValueError(f"{kind} sample {index} must be an object.")
        sample_id = sample.get("id")
        text = sample.get("text")
        provenance = sample.get("provenance")
        if not isinstance(sample_id, str) or not sample_id.strip():
            raise ValueError(f"{kind} sample {index} needs a nonempty id.")
        if sample_id in seen_ids:
            raise ValueError(f"Duplicate {kind} sample id: {sample_id}.")
        seen_ids.add(sample_id)
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{kind} sample {sample_id} needs nonempty text.")
        if len(text) > 5000:
            raise ValueError(
                f"{kind} sample {sample_id} exceeds the 5,000-character limit."
            )
        if not isinstance(provenance, dict):
            raise ValueError(f"{kind} sample {sample_id} needs provenance.")
        if provenance.get("authorship") != expected_authorship:
            raise ValueError(
                f"{kind} sample {sample_id} must declare "
                f"authorship={expected_authorship!r}."
            )
        for field in required_fields:
            value = provenance.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{kind} sample {sample_id} needs provenance.{field}."
                )
        if expected_authorship.startswith("dataset_labeled_"):
            dataset_fields = {
                "dataset": "dataset",
                "dataset_revision": "revision",
                "subset": "subset",
                "split": "split",
            }
            for sample_field, dataset_field in dataset_fields.items():
                if provenance[sample_field] != dataset_provenance[dataset_field]:
                    raise ValueError(
                        f"{kind} sample {sample_id} does not match the "
                        f"dataset_provenance.{dataset_field}."
                    )
        checked.append(sample)
    return checked


def load_samples() -> dict[str, list[dict] | dict]:
    """Load dataset-labeled pairs separately from verified human controls."""
    if not SAMPLE_FILE.is_file():
        raise FileNotFoundError(
            f"Missing {SAMPLE_FILE.name}: provide documented comparison samples "
            "for criterion 2 and verified human writing for criterion 1."
        )

    try:
        dataset = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read {SAMPLE_FILE.name}: {exc}") from exc

    if not isinstance(dataset, dict):
        raise ValueError(f"{SAMPLE_FILE.name} must contain a JSON object.")

    dataset_provenance = dataset.get("dataset_provenance")
    if not isinstance(dataset_provenance, dict):
        raise ValueError("evaluation_samples.json needs dataset_provenance.")
    for field in ("dataset", "revision", "publication", "license", "selection"):
        value = dataset_provenance.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"dataset_provenance.{field} is required.")

    human = _validate_samples(
        dataset.get("human"),
        "HC3 dataset-labeled human",
        HUMAN_SAMPLE_COUNT,
        "dataset_labeled_human",
        dataset_provenance,
    )
    ai = _validate_samples(
        dataset.get("ai"),
        "HC3 dataset-labeled ChatGPT",
        AI_SAMPLE_COUNT,
        "dataset_labeled_chatgpt",
        dataset_provenance,
    )
    verified_human_raw = dataset.get("verified_human", [])
    if not isinstance(verified_human_raw, list):
        raise ValueError("verified_human must be a list.")
    if verified_human_raw:
        verified_human = _validate_samples(
            verified_human_raw,
            "verified_human",
            HUMAN_EVALUATION_COUNT,
            "verified_human",
            dataset_provenance,
        )
    else:
        verified_human = []

    all_texts = [sample["text"] for sample in human + ai]
    if len(set(all_texts)) != len(all_texts):
        raise ValueError("HC3 comparison texts must be distinct.")
    if len(human) != len(ai):
        raise ValueError("HC3 human and ChatGPT groups must be matched.")
    for human_sample, ai_sample in zip(human, ai):
        human_provenance = human_sample["provenance"]
        ai_provenance = ai_sample["provenance"]
        if (
            human_provenance["pair_id"] != ai_provenance["pair_id"]
            or human_provenance["question"] != ai_provenance["question"]
            or human_provenance["row_id"] != ai_provenance["row_id"]
        ):
            raise ValueError(
                f"HC3 samples {human_sample['id']} and {ai_sample['id']} "
                "are not a matched question pair."
            )

    return {
        "human": human,
        "ai": ai,
        "verified_human": verified_human,
        "dataset_provenance": dataset_provenance,
    }


def validate() -> list[str]:
    """Validate fixed scenarios and report unavailable provenance data."""
    problems = []
    if len(INVALID_CASES) != 6:
        problems.append("criterion 5 must define exactly six invalid cases")
    if any(not isinstance(case.get("body"), dict) for case in INVALID_CASES):
        problems.append("each invalid-input case must contain a JSON object body")

    try:
        load_samples()
    except (FileNotFoundError, ValueError) as exc:
        problems.append(str(exc))

    return problems
