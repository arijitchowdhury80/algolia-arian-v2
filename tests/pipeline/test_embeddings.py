"""Tests for Task 5's local embedding wrapper.

These tests load the real `sentence-transformers/all-MiniLM-L6-v2` model
(local CPU inference, no API key, no network call at embed time -- the model
weights are cached on first download). This is the one test module in this
task that is genuinely slow/model-load-dependent; if the model cannot be
loaded in a given sandbox (no cached weights + no network), the whole module
is skipped rather than failing the rest of the suite.
"""

from __future__ import annotations

import pytest

from prism_platform.pipeline.embeddings import EMBEDDING_DIMS, EMBEDDING_MODEL_NAME, embed_texts

try:
    from prism_platform.pipeline.embeddings import _load_model

    _load_model()
    _MODEL_AVAILABLE = True
except Exception:  # pragma: no cover -- environment-dependent
    _MODEL_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _MODEL_AVAILABLE, reason="sentence-transformers model could not be loaded in this sandbox"
)


def test_embed_texts_returns_one_vector_per_input() -> None:
    vectors = embed_texts(["hello world", "goodbye world"])
    assert len(vectors) == 2


def test_embed_texts_vectors_have_expected_dimensionality() -> None:
    vectors = embed_texts(["a search relevance audit finding"])
    assert len(vectors[0]) == EMBEDDING_DIMS == 384


def test_embed_texts_empty_input_returns_empty_list() -> None:
    assert embed_texts([]) == []


def test_embed_texts_similar_texts_are_closer_than_dissimilar_ones() -> None:
    import math

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        return dot / (norm_a * norm_b)

    anchor, similar, different = embed_texts(
        [
            "Belk's site search has no typo tolerance for misspelled product queries.",
            "Belk's search results fail when a shopper misspells a product name.",
            "Belk was founded in 1888 and is headquartered in Charlotte, North Carolina.",
        ]
    )
    sim_similar = cosine(anchor, similar)
    sim_different = cosine(anchor, different)
    assert sim_similar > sim_different


def test_embedding_model_name_is_the_locked_no_credential_model() -> None:
    # Patch #9 locks this exact model -- a silent swap to a paid provider
    # (OpenAI/Voyage) is a cost/credential decision that needs Arijit's sign-off,
    # not something a future refactor should be able to change unnoticed.
    assert EMBEDDING_MODEL_NAME == "sentence-transformers/all-MiniLM-L6-v2"
