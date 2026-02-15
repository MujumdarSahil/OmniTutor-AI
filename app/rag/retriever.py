# -----------------------------------------------------------------------------
# app/rag/retriever.py — Retrieve top-k relevant chunks
# -----------------------------------------------------------------------------

import asyncio

from app.rag.embeddings import embed_texts
from app.rag.index import index_count, search_index


def retrieve_top_k(query: str, k: int = 3) -> list[str]:
    if index_count() == 0:
        return []
    query_emb = embed_texts([query])[0]
    return search_index(query_emb, k=k)


async def retrieve_top_k_async(query: str, k: int = 3) -> list[str]:
    if index_count() == 0:
        return []
    embeddings = await asyncio.to_thread(embed_texts, [query])
    query_emb = embeddings[0]
    return search_index(query_emb, k=k)
