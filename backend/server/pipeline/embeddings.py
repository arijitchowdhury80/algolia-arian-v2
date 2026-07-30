"""Task 5 (Track C.3) -- local embedding wrapper for the chat agent's grounding store.

Per the task-5 brief's patch #9 (locked): `sentence-transformers/all-MiniLM-L6-v2`,
384 dims, runs on CPU, no API key, no per-call cost -- consistent with this
project's standing preference for keyless/local infra over new paid API
dependencies (`reference-no-paid-mcp-keys-needed`, `detect-search`'s keyless
pattern). Do not swap this for a paid provider (OpenAI/Voyage embeddings)
without flagging that as a cost/credential decision for Arijit -- see the
task-5 report for the "is MiniLM adequate" evaluation that justifies keeping it.

The model is loaded lazily (module import must not require the model weights
to exist / network access -- keeps `chunking.py`/`chat_agent.py` importable
and their pure-logic tests fast even if this module's own model-load tests
are skipped in a given sandbox).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMS = 384


@lru_cache(maxsize=1)
def _load_model() -> Any:
    """Load (and cache) the local sentence-transformers model.

    Deferred import: `sentence_transformers` pulls in `torch`, which is slow
    to import and not needed by any module that only does chunking/prompt
    construction. Cached via lru_cache so repeated calls (one per audit run,
    or many in a test session) don't reload the model from disk each time.
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with the local MiniLM model. No network call.

    Returns one 384-dim vector (as a plain list[float], directly insertable
    into a pgvector `vector(384)` column) per input text, in input order.
    """
    if not texts:
        return []
    model = _load_model()
    vectors = model.encode(texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True)
    return [vector.tolist() for vector in vectors]
