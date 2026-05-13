"""Sentence embeddings for semantic dedup.

The model (all-MiniLM-L6-v2, 384 dims — pinned in the Posting.embedding
column) is loaded lazily so workers that don't need it (e.g. API replicas)
don't pay the startup cost.
"""

from __future__ import annotations

from functools import lru_cache

EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def _model():
    # Imported lazily so the package can be used without the ml extra.
    from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def embed(text: str) -> list[float]:
    if not text:
        return [0.0] * EMBEDDING_DIM
    model = _model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()
