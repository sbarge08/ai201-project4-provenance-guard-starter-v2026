"""
Signal two: a simple style-shape heuristic.

Signal one reads the text for meaning. This one measures it *as text* — the
shape of it, without understanding a word.

It measures sentence-length variation, vocabulary diversity, and punctuation
density. The direction assigned to each feature is a scoring assumption, not a
universal distinction between human and AI writing.

    sentence_length_spread   do sentences vary in length, or march in step?
    type_token_ratio         how much of the vocabulary repeats?
    punctuation_density      how much punctuation, and how varied?

These features describe text shape, not meaning or authorship. Individual
writers and generated texts can both have varied or regular styles.

⚠️ **The blind spot, which you have to name in Milestone 1.**

This signal cannot read. It has no idea what the text says. Anything that
changes the shape without changing the substance moves it — adding typos,
breaking up sentences, pasting in a quotation. That is a very cheap thing for
someone to do on purpose, and unit 8's attack set will do it to you.

Call the measurements from a terminal to inspect their values:

    python stylometry.py "some text to look at"
"""

import re
import statistics
import unicodedata


def sentences(text: str) -> list[str]:
    """Split into sentences. Rough and good enough — given to you."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def words(text: str) -> list[str]:
    """Split into case-folded Unicode letter/number words."""
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)*", text.casefold(), flags=re.UNICODE)


# ── The three measures ───────────────────────────────────────────────────────

def sentence_length_spread(text: str) -> float:
    """
    Return the coefficient of variation of sentence word counts.

    Population standard deviation divided by the mean makes the measurement
    relative to the typical sentence length. Fewer than two nonempty sentences
    have no measurable spread, so they return 0.0.
    """
    lengths = [len(words(sentence)) for sentence in sentences(text)]
    lengths = [length for length in lengths if length > 0]
    if len(lengths) < 2:
        return 0.0

    mean_length = statistics.mean(lengths)
    if mean_length == 0:
        return 0.0
    return statistics.pstdev(lengths) / mean_length


def type_token_ratio(text: str) -> float:
    """
    Return the unique-word count divided by the total word count.

    The ratio is in [0, 1]. Text with no recognized words returns 0.0.
    """
    tokens = words(text)
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def punctuation_density(text: str) -> float:
    """
    Return Unicode punctuation characters divided by all text characters.

    This ratio is in [0, 1]. Empty text returns 0.0.
    """
    if not text:
        return 0.0
    punctuation_count = sum(
        unicodedata.category(char).startswith("P") for char in text
    )
    return punctuation_count / len(text)


# ── Combining them ───────────────────────────────────────────────────────────

def style_signal(text: str) -> float:
    """
    Combine three normalized style features with equal weight.

    Less sentence-length variation and a lower unique-word ratio contribute
    more AI-like evidence. Punctuation density is scaled against 10% of all
    characters, capped at 1, and higher scaled density contributes more
    AI-like evidence. These are heuristic directions, not universal facts
    about human or AI writing. Missing sentence or word measurements contribute
    a neutral 0.5; whitespace-only text returns 0.5.
    """
    if not text.strip():
        return 0.5

    sentence_parts = sentences(text)
    sentence_lengths = [len(words(sentence)) for sentence in sentence_parts]
    sentence_lengths = [length for length in sentence_lengths if length > 0]
    if len(sentence_lengths) < 2:
        spread_score = 0.5
    else:
        spread_score = 1.0 / (1.0 + sentence_length_spread(text))

    tokens = words(text)
    vocabulary_score = 1.0 - type_token_ratio(text) if tokens else 0.5

    punctuation_score = min(punctuation_density(text) / 0.10, 1.0)
    return round(
        (spread_score + vocabulary_score + punctuation_score) / 3.0,
        4,
    )


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "The system works well. It handles most cases correctly and provides "
        "good results. Users generally find it easy to use and understand."
    )

    print(f"{len(sentences(text))} sentences, {len(words(text))} words\n")
    print(f"sentence_length_spread   {sentence_length_spread(text)}")
    print(f"type_token_ratio         {type_token_ratio(text)}")
    print(f"punctuation_density      {punctuation_density(text)}")
    print(f"style_signal             {style_signal(text)}   (higher = more likely AI)")
