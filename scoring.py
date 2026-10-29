"""
Combining the two signals and mapping a score to a reader-facing label.

`combine_signals` is where your false-positive decision from Milestone 1
actually gets made. Everything above it — the labels, the appeal path — is
downstream of a number this function produced.

`score_to_label` is where you stop writing for a machine and start writing for
a person. A score of 0.62 means nothing to a writer.

⚠️ Your README's **Signals and Scoring** section has to name the file and
function holding your combining rule. The grader checks your code against what
you claim, so that line should read `scoring.py::combine_signals`.
"""

import math

import config


def combine_signals(model_score: float, style_score: float) -> float:
    """
    Combine two 0–1 signals using the configurable weighted average.

    Both inputs point the same way: higher means more AI-like evidence. The
    result is an AI-likeness score, not a probability of authorship.

    Weights are normalized by their sum, so configurable positive weights
    still produce a bounded weighted average. Both scores must be finite values
    in [0, 1]; weights must be finite, nonnegative, and not both zero.
    """
    if not math.isfinite(model_score) or not 0.0 <= model_score <= 1.0:
        raise ValueError("model_score must be a finite number from 0.0 to 1.0")
    if not math.isfinite(style_score) or not 0.0 <= style_score <= 1.0:
        raise ValueError("style_score must be a finite number from 0.0 to 1.0")

    model_weight = config.WEIGHT_MODEL_SIGNAL
    style_weight = config.WEIGHT_STYLE_SIGNAL
    total_weight = model_weight + style_weight
    if (
        not math.isfinite(model_weight)
        or not math.isfinite(style_weight)
        or not math.isfinite(total_weight)
        or model_weight < 0
        or style_weight < 0
        or total_weight == 0
    ):
        raise ValueError("Signal weights must be finite, nonnegative, and not both zero")

    combined = (
        model_weight * model_score + style_weight * style_score
    ) / total_weight
    return round(min(max(combined, 0.0), 1.0), 4)


def score_to_label(score: float) -> tuple[str, str]:
    """
    Turn an AI-likeness score into a guess and reader-facing explanation.

    Returns:
        A pair of machine-readable guess and full label sentence.

    This is a heuristic label based on AI-like evidence, not proof or a
    calibrated probability of authorship.
    """
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError("score must be a finite number from 0.0 to 1.0")
    if not 0.0 < config.HUMAN_THRESHOLD < config.AI_THRESHOLD < 1.0:
        raise ValueError("thresholds must satisfy 0 < HUMAN_THRESHOLD < AI_THRESHOLD < 1")

    if score >= config.AI_THRESHOLD:
        return (
            "ai",
            "High-confidence AI-like patterns: this system's signals are "
            "strongly associated with AI-generated writing. This is not proof "
            "of authorship.",
        )
    if score <= config.HUMAN_THRESHOLD:
        return (
            "human",
            "High-confidence human-like patterns: this system's signals are "
            "strongly associated with human writing. This is not proof of "
            "authorship.",
        )
    return (
        "unsure",
        "The signals are inconclusive. This system cannot determine who wrote "
        "the text.",
    )


def classification_confidence(score: float, guess: str) -> float:
    """
    Return a heuristic margin score for the selected label, not a probability.

    Confidence is 0.5 at a label boundary and approaches 1.0 deeper inside
    that label's score region. For unsure, it is greatest at the band midpoint.
    """
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError("score must be a finite number from 0.0 to 1.0")

    human_threshold = config.HUMAN_THRESHOLD
    ai_threshold = config.AI_THRESHOLD
    if not 0.0 < human_threshold < ai_threshold < 1.0:
        raise ValueError("thresholds must satisfy 0 < HUMAN_THRESHOLD < AI_THRESHOLD < 1")

    expected_guess, _ = score_to_label(score)
    if guess != expected_guess:
        raise ValueError("guess must match the label for score")

    if guess == "human":
        margin = (human_threshold - score) / human_threshold
    elif guess == "ai":
        margin = (score - ai_threshold) / (1.0 - ai_threshold)
    else:
        midpoint = (human_threshold + ai_threshold) / 2.0
        half_band = (ai_threshold - human_threshold) / 2.0
        margin = 1.0 - abs(score - midpoint) / half_band

    return round(0.5 + 0.5 * min(max(margin, 0.0), 1.0), 4)


def label_ranges() -> list[tuple[str, str]]:
    """
    The score range each label covers. Your README needs these beside the
    label text — given to you so the numbers can't drift apart from config.py.
    """
    return [
        ("high-confidence human", f"0.00 – {config.HUMAN_THRESHOLD:.2f} (inclusive)"),
        ("unsure", f"({config.HUMAN_THRESHOLD:.2f}, {config.AI_THRESHOLD:.2f})"),
        ("high-confidence AI", f"{config.AI_THRESHOLD:.2f} – 1.00 (inclusive)"),
    ]
