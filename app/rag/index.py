# -----------------------------------------------------------------------------
# app/rag/index.py — FAISS in-memory index + metadata list
# -----------------------------------------------------------------------------

import asyncio
from typing import Any

import numpy as np

_rag_lock = asyncio.Lock()
_faiss_index: Any = None
_metadata_list: list[dict] = []
_index_dim: int | None = None


def _get_index_dim() -> int:
    from app.rag.embeddings import embed_texts
    dummy = embed_texts(["dummy"])
    return len(dummy[0])


def get_faiss_index():
    global _faiss_index, _index_dim
    if _faiss_index is None:
        import faiss
        _index_dim = _get_index_dim()
        _faiss_index = faiss.IndexFlatL2(_index_dim)
    return _faiss_index


def get_metadata_list() -> list[dict]:
    return _metadata_list


def index_count() -> int:
    return len(_metadata_list)


async def add_to_index(embeddings: list[list[float]], chunks: list[str]) -> None:
    global _metadata_list
    async with _rag_lock:
        index = get_faiss_index()
        arr = np.array(embeddings, dtype=np.float32)
        index.add(arr)
        base = len(_metadata_list)
        for i, chunk in enumerate(chunks):
            _metadata_list.append({"text": chunk, "chunk_index": base + i})


def search_index(query_embedding: list[float], k: int = 3) -> list[str]:
    if index_count() == 0:
        return []
    index = get_faiss_index()
    arr = np.array([query_embedding], dtype=np.float32)
    _, indices = index.search(arr, min(k, index.ntotal))
    meta = get_metadata_list()
    return [meta[int(i)]["text"] for i in indices[0] if 0 <= int(i) < len(meta)]
