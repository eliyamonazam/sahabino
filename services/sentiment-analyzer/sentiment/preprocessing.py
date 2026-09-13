"""Turns raw review text into the token list the classifier scores.

Pipeline: hazm normalization -> elongation collapsing -> hazm tokenization ->
stopword filtering (with sentiment-bearing words protected from removal).
"""

import re

import hazm
import regex

from sentiment.lexicon import INTENSIFIER_WORDS, NEGATION_WORDS, NEGATIVE_WORDS, NEUTRAL_WORDS, POSITIVE_WORDS

_normalizer = hazm.Normalizer()
# hazm's own module-level `word_tokenize()` helper constructs a fresh
# `WordTokenizer` on every call (~1s each, confirmed by timing it directly),
# which would make classifying ~17k reviews take hours; building one
# instance up front and reusing `.tokenize()` brings that down to
# microseconds per call.
_tokenizer = hazm.WordTokenizer()

# hazm's own stopword list is tuned for general topic-modeling cleanup, not
# sentiment preservation: it classifies "عالی" ("excellent") itself as a
# stopword (likely from its use as a formal adjective, e.g. "کمیته عالی" -
# "supreme committee"), alongside negation words like "نیست"/"نه"/"هیچ" and
# intensifiers like "خیلی"/"بسیار" that this classifier needs to see intact.
# Confirmed directly against hazm 0.12.1's stopwords_list() rather than
# assumed. Any word this classifier actually cares about is therefore
# exempted from stopword removal, regardless of hazm's own classification.
_STOPWORDS = set(hazm.stopwords_list())
_PROTECTED_WORDS = (
    set(POSITIVE_WORDS) | set(NEGATIVE_WORDS) | set(NEUTRAL_WORDS) | NEGATION_WORDS | set(INTENSIFIER_WORDS)
)
_STOPWORDS -= _PROTECTED_WORDS

# Informal Persian reviews commonly stretch a word for emphasis
# ("عالیییی", "عالیهههه"). Collapsing any run of 3+ identical characters
# down to one lets those collapse onto the plain lexicon entry ("عالی")
# instead of needing an entry for every possible repeat count.
_ELONGATION_RE = re.compile(r"(.)\1{2,}")

# hazm's tokenizer glues a run of emoji together into one token ("👍👍" ->
# a single "👍👍" token, not two "👍" tokens), which then never matches the
# single-emoji keys in EMOJI_SCORES. A token with no letters in it is split
# into individual grapheme clusters (via \X, so a base character plus a
# combining modifier like the variation selector on "❤️" stays together as
# one cluster instead of being torn apart) so each emoji can be scored on
# its own.
_HAS_LETTER_RE = regex.compile(r"[^\W\d_]", flags=regex.UNICODE)


def _split_symbol_run(token: str) -> list[str]:
    if len(token) <= 1 or _HAS_LETTER_RE.search(token):
        return [token]
    return regex.findall(r"\X", token)


def normalize_and_tokenize(text: str) -> list[str]:
    """Normalize, de-elongate, and tokenize review text into raw tokens."""
    normalized = _normalizer.normalize(text)
    de_elongated = _ELONGATION_RE.sub(r"\1", normalized)
    tokens = _tokenizer.tokenize(de_elongated)
    return [split for token in tokens for split in _split_symbol_run(token)]


def clean_tokens(tokens: list[str]) -> list[str]:
    """Drop stopwords, keeping any token this classifier assigns meaning to."""
    return [token for token in tokens if token not in _STOPWORDS]


def preprocess(text: str) -> list[str]:
    """Full pipeline: normalize, tokenize, and strip non-sentiment stopwords."""
    return clean_tokens(normalize_and_tokenize(text))
