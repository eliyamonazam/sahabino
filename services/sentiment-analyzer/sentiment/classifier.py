"""Lexicon-based 3-way sentiment classification for Persian review text.

See README.md for why this is a lexicon/rule-based classifier rather than a
pretrained model. The approach mirrors VADER (Hutto & Gilbert, 2014): sum a
per-token lexicon score, adjusted for nearby negation and intensifier words,
and threshold the total.
"""

from typing import Literal

from sentiment.lexicon import EMOJI_SCORES, INTENSIFIER_WORDS, NEGATION_WORDS, NEGATIVE_WORDS, POSITIVE_WORDS
from sentiment.preprocessing import preprocess

Sentiment = Literal["positive", "neutral", "negative"]

# How many tokens away a negation/intensifier can be and still apply to a
# sentiment word. Persian negation typically *follows* what it negates
# ("خوب نیست" - "[it's] not good"), unlike English, so both directions are
# checked, not just the preceding tokens.
_NEGATION_WINDOW = 2
_INTENSIFIER_WINDOW = 2


def _base_weight(token: str) -> int:
    if token in POSITIVE_WORDS:
        return POSITIVE_WORDS[token]
    if token in NEGATIVE_WORDS:
        return -NEGATIVE_WORDS[token]
    if token in EMOJI_SCORES:
        return EMOJI_SCORES[token]
    return 0


def score_tokens(tokens: list[str]) -> float:
    """Sum each sentiment-bearing token's weight, adjusted by nearby negation/intensifiers."""
    total = 0.0
    for i, token in enumerate(tokens):
        weight = _base_weight(token)
        if weight == 0:
            continue

        window_start = max(0, i - _NEGATION_WINDOW)
        window_end = min(len(tokens), i + _NEGATION_WINDOW + 1)
        neighborhood = tokens[window_start:i] + tokens[i + 1 : window_end]
        if any(word in NEGATION_WORDS for word in neighborhood):
            weight = -weight

        preceding = tokens[max(0, i - _INTENSIFIER_WINDOW) : i]
        multipliers = (INTENSIFIER_WORDS[word] for word in preceding if word in INTENSIFIER_WORDS)
        weight *= max(multipliers, default=1.0)

        total += weight
    return total


def score_review(content: str | None) -> float:
    """Preprocess and score raw review text. 0.0 for empty/no-signal content."""
    if not content or not content.strip():
        return 0.0
    return score_tokens(preprocess(content))


def classify_sentiment(content: str | None) -> Sentiment:
    """Classify a review's content into exactly one of positive/neutral/negative.

    A score of exactly 0 -- no sentiment words found, or a positive/negative
    balance that fully cancels out -- is neutral: the safe default when no
    clear opinion was detected, rather than a guess.
    """
    score = score_review(content)
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"
