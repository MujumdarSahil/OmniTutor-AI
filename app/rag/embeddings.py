# -----------------------------------------------------------------------------
# app/rag/embeddings.py — RAG embeddings (sentence-transformers, all-MiniLM-L6-v2)
# -----------------------------------------------------------------------------

from typing import Any

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
_embedding_model: Any = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()
