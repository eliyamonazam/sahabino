from sentiment.preprocessing import clean_tokens, normalize_and_tokenize, preprocess


def test_normalize_and_tokenize_splits_words():
    assert normalize_and_tokenize("این بازی افتضاحه!!") == ["این", "بازی", "افتضاحه", "!", "!"]


def test_normalize_and_tokenize_collapses_elongated_characters():
    # Informal reviews commonly stretch a word for emphasis ("عالیییی").
    assert normalize_and_tokenize("عالیییییی") == ["عالی"]
    assert normalize_and_tokenize("عالیهههه") == ["عالیه"]


def test_clean_tokens_removes_generic_function_words():
    tokens = ["این", "برنامه", "را", "دوست", "دارم", "و", "خوب", "است"]
    cleaned = clean_tokens(tokens)
    assert "این" not in cleaned
    assert "را" not in cleaned
    assert "و" not in cleaned
    assert "است" not in cleaned


def test_clean_tokens_protects_sentiment_words_hazm_would_otherwise_drop():
    # hazm's own stopwords_list() classifies "عالی" ("excellent") as a
    # stopword, along with negation words like "نیست" and intensifiers like
    # "خیلی" -- all of which this classifier needs intact. Confirmed against
    # hazm 0.12.1 directly, not assumed.
    tokens = ["خیلی", "عالی", "بود", "نیست"]
    cleaned = clean_tokens(tokens)
    assert "عالی" in cleaned
    assert "خیلی" in cleaned
    assert "نیست" in cleaned


def test_preprocess_runs_the_full_pipeline():
    assert preprocess("این بازی خیلی عالیه!") == ["بازی", "خیلی", "عالیه", "!"]
