# sentiment-analyzer

Classifies every Play Store review's `content` into `positive` / `neutral` /
`negative` and writes the result back to the `sentiment` column on
storage-consumer's `reviews` table (the project spec's bonus sentiment
analysis feature).

Like `network-analyzer`, this isn't a long-running daemon: it's a **batch CLI
tool** (`python -m sentiment.main`) that processes every `reviews` row with
`sentiment IS NULL` once and exits. It's meant to be run with `docker compose
run --rm sentiment-analyzer`, not brought up with the rest of the stack via
`up -d`.

## Why a lexicon, not a model

The obvious "real classifier" here is a pretrained Persian sentiment model
via `transformers` (e.g. one of HooshvareLab's ParsBERT sentiment
fine-tunes). That was tried first and rejected for this project, for
reasons specific to this dataset and this environment, not in general:

- **The reviews are overwhelmingly short and colloquial.** A manual sample
  of this project's own `reviews` table is dominated by one- or two-word
  reviews ("عالی", "خوبه", "افتضاح", "مزخرفه"), often with elongated spelling
  ("عالیییییی") or an emoji standing in for the entire review. A transformer
  fine-tuned on longer, more formal review text is arguably overkill for
  "one word plus optional emoji," and a lexicon plus a few hand-written
  rules (negation, intensifiers, character-elongation, emoji) directly
  targets exactly that structure.
- **Image size and runtime cost.** `torch` + `transformers` plus a
  downloaded model checkpoint would take this batch tool's image from the
  ~340MB it is now (`python:3.12-slim` + `hazm` + SQLAlchemy/asyncpg — no
  heavy ML runtime) to multiple GB, and CPU-only inference over ~17.5k rows
  would take meaningfully longer than the lexicon approach's few seconds
  (see Performance below). For a tool meant to be run ad hoc with `docker
  compose run --rm`, that's a real cost for marginal benefit on this
  particular dataset.
- **Determinism and testability.** The classifier here is a plain function
  with no model weights to download, version, or mock in tests — the unit
  tests in `tests/test_classifier.py` exercise the exact same code path
  that runs in production, with no stubbing required.

The approach taken instead is a **lexicon/rule-based classifier**, the same
family as VADER (Hutto & Gilbert, 2014) for English: a hand-curated Persian
sentiment word list (`sentiment/lexicon.py`), scored per-token with
adjustments for nearby negation and intensifier words, then thresholded into
the three categories. This is a well-established, legitimate approach to
sentiment analysis in its own right (not a "placeholder" — see the manual
verification below), just a different one than "run a big pretrained
model."

**Known limitations of this choice**, for honesty: it will not catch
sentiment expressed through typos it doesn't recognize (e.g. "بینزیر" for
"بی‌نظیر"), words outside its ~150-entry lexicon, or sentiment that depends
on real-world/contextual understanding rather than word choice. A
transformer model would likely do better on genuinely long, nuanced reviews;
there are very few of those in this dataset. Vulgar/slang insults that do
appear in the real data (e.g. profanity used to mean "this is garbage") are
deliberately **not** added to the checked-in lexicon file, so a handful of
profanity-only negative reviews fall through to `neutral` rather than
`negative`.

## How it works

1. **`sentiment/preprocessing.py`**: hazm `Normalizer` (fixes character
   variants like `ي`→`ی`, spacing), then a regex step that collapses any run
   of 3+ identical characters down to one (so "عالیهههه" and "عالیییی" both
   collapse onto a form the lexicon recognizes), then hazm's `WordTokenizer`.
   A further step splits any token made entirely of non-letter characters
   (emoji, punctuation) into individual grapheme clusters, since hazm's
   tokenizer glues a run of emoji into a single token ("👍👍" → one token,
   not two) — confirmed directly rather than assumed. Finally, hazm's
   stopword list is applied, **except** for any word this classifier
   actually scores on: hazm's `stopwords_list()` classifies "عالی"
   ("excellent") itself as a stopword, along with negation words
   ("نیست"/"نه"/"هیچ") and intensifiers ("خیلی"/"بسیار") — all confirmed
   directly against hazm 0.12.1, not assumed. Blindly applying the full
   stopword list would silently strip the exact words this classifier
   depends on.
2. **`sentiment/lexicon.py`**: hand-curated word lists collected from a
   manual sample of this project's own review data (see the module
   docstring) — positive/negative words with a strength weight, a small
   neutral list, negation triggers, intensifier multipliers, and an emoji
   sentiment map (deliberately excluding 😂/🤣, which show up in this
   dataset mocking a complaint about as often as expressing real amusement).
3. **`sentiment/classifier.py`**: sums each sentiment-bearing token's
   weight, flipping the sign if a negation word is within 2 tokens in
   *either* direction (Persian negation typically follows what it negates —
   "خوب نیست" is "[it's] **not** good" — unlike English), and scaling by an
   intensifier's multiplier if one precedes it. A positive total is
   `positive`, negative is `negative`, and exactly zero (including "no
   sentiment words found at all") is `neutral`.
4. **`sentiment/main.py`**: repeatedly fetches up to `SENTIMENT_BATCH_SIZE`
   rows where `sentiment IS NULL`, classifies and writes each one, commits
   the batch, and logs progress — until a fetch comes back empty.

Verified against this project's real data (not just the unit tests' hand
picked examples): classifying all ~17.5k live reviews split
11,085 `positive` / 5,303 `neutral` / 1,172 `negative` — a distribution that
matches the visibly praise-heavy nature of this dataset (see Day 10's
Metabase notes) rather than collapsing onto one label.

## Idempotency

Every batch selects only `sentiment IS NULL` rows, so a run stopped partway
through (or one racing new reviews inserted concurrently by
storage-consumer) simply leaves fewer, or more, rows for the next run — no
separate resume state is needed. storage-consumer's own upsert logic already
never overwrites an existing `sentiment` value on a re-scrape, so the two
services can run concurrently without either one clobbering the other.

## Schema

This service does **not** own the `reviews` table — it's owned by
storage-consumer's own Alembic history (see that service's README). This
service only needs its own connection (same `POSTGRES_*` environment
variable convention as every other service) and a minimal, partial
SQLAlchemy mapping of the columns it actually reads/writes
(`sentiment/models/review.py`: `review_id`, `content`, `sentiment`) — no
Alembic setup of its own, since it creates no schema.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `SENTIMENT_BATCH_SIZE` | `500` | Rows fetched, classified, and committed per round trip. |

Plus the standard `POSTGRES_*` variables shared by every service.

## Performance

Classifying is fast: all ~17,560 currently-live reviews were processed
(read, classified, and written back) in about 5 seconds inside the
container, at roughly 2,800 reviews/second for the classification logic
itself. This was run for real against the live stack (not just measured on
a sample) — see the Day 11 log entry. At that rate, a much larger review
table (e.g. 10x today's size) would still finish in under a minute; the
bottleneck at that scale would be Postgres round trips, not the classifier.

## Image size

`python:3.12-slim` plus `hazm` and its (non-ML) dependencies plus
SQLAlchemy/asyncpg builds to about 340MB — no `torch`/`transformers`, per
the "why a lexicon" reasoning above.

## Tests

`tests/test_preprocessing.py` and `tests/test_classifier.py` test the
preprocessing and classification-decision logic directly against hand-picked
Persian review examples (several copied near-verbatim from this project's
own data) with obviously distinct sentiment — no mocking needed, since this
approach has no heavy model dependency to isolate from. `tests/test_persistence.py`
covers the `sentiment IS NULL` fetch/update logic and end-to-end idempotency
against a real Postgres test database (`POSTGRES_TEST_DB_SENTIMENT_ANALYZER`),
following this repo's usual "no mocking Postgres itself" convention — the
`reviews` table is created there from DDL hand-copied from
storage-consumer's migration (same pattern as `app-list-api-django`'s
`conftest.py` for the `apps` table it likewise doesn't own).

Since the image doesn't include the test suite or dev dependencies, run
tests with the service directory bind-mounted over `/app`, same as
`network-analyzer`:

```bash
docker compose run --rm -v "$(pwd)/services/sentiment-analyzer:/app" -e POSTGRES_HOST=postgres sentiment-analyzer \
  sh -c "pip install -r requirements-dev.txt && pytest"
```
