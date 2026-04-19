"""NLP helpers: VADER sentiment + TF-IDF n-gram extraction on negative reviews."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


def _ensure_vader():
    import nltk
    from pathlib import Path

    # Add venv-local nltk_data first so the lexicon works without a
    # network download in sandboxed / cert-restricted environments.
    _local = Path(__file__).resolve().parents[1] / ".venv" / "nltk_data"
    if str(_local) not in nltk.data.path:
        nltk.data.path.insert(0, str(_local))

    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)


def vader_scores(texts: pd.Series) -> pd.DataFrame:
    """Return DataFrame with neg/neu/pos/compound columns aligned to input index."""
    _ensure_vader()
    from nltk.sentiment.vader import SentimentIntensityAnalyzer

    sia = SentimentIntensityAnalyzer()
    clean = texts.fillna("").astype(str)
    scores = clean.map(sia.polarity_scores)
    return pd.DataFrame(list(scores.values), index=texts.index)


def top_ngrams(
    texts: pd.Series,
    top_k: int = 20,
    ngram_range: tuple[int, int] = (2, 2),
    min_df: int = 5,
    max_df: float = 0.95,
) -> pd.DataFrame:
    """Return top-k TF-IDF n-grams with their scores."""
    clean = texts.fillna("").astype(str)
    clean = clean[clean.str.strip().astype(bool)]
    if len(clean) < min_df:
        return pd.DataFrame(columns=["ngram", "tfidf"])
    vec = TfidfVectorizer(
        ngram_range=ngram_range,
        stop_words="english",
        min_df=min_df,
        max_df=max_df,
        lowercase=True,
    )
    matrix = vec.fit_transform(clean)
    summed = np.asarray(matrix.sum(axis=0)).flatten()
    vocab = np.array(vec.get_feature_names_out())
    order = np.argsort(summed)[::-1][:top_k]
    return pd.DataFrame({"ngram": vocab[order], "tfidf": summed[order]})


def top_negative_ngrams_by_group(
    df: pd.DataFrame,
    text_col: str,
    group_col: str,
    sentiment_col: str,
    threshold: float = -0.3,
    top_k: int = 10,
    min_reviews: int = 50,
) -> pd.DataFrame:
    """For each group, compute top-k bigrams in reviews with compound sentiment < threshold."""
    frames = []
    neg = df[df[sentiment_col] < threshold]
    for group, sub in neg.groupby(group_col):
        if len(sub) < min_reviews:
            continue
        grams = top_ngrams(sub[text_col], top_k=top_k)
        if grams.empty:
            continue
        grams.insert(0, group_col, group)
        frames.append(grams)
    if not frames:
        return pd.DataFrame(columns=[group_col, "ngram", "tfidf"])
    return pd.concat(frames, ignore_index=True)
