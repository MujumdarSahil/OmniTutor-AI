# -----------------------------------------------------------------------------
# app/rag/ingest.py — Text chunking (500 words, overlap 50) + embed + store
# -----------------------------------------------------------------------------

import asyncio
import re

from app.rag.embeddings import embed_texts
from app.rag.index import add_to_index

CHUNK_SIZE_WORDS = 500
CHUNK_OVERLAP_WORDS = 50


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_WORDS, overlap: int = CHUNK_OVERLAP_WORDS) -> list[str]:
    words = re.findall(r"\S+|\s+", text)
    word_tokens = [w for w in words if w.strip()]
    if not word_tokens:
        return [text] if text.strip() else []
    step = chunk_size - overlap
    if step <= 0:
        step = 1
    chunks = []
    for start in range(0, len(word_tokens), step):
        end = min(start + chunk_size, len(word_tokens))
        chunk_words = word_tokens[start:end]
        chunk_str = " ".join(chunk_words)
        if chunk_str.strip():
            chunks.append(chunk_str)
        if end >= len(word_tokens):
            break
    return chunks if chunks else [text]


async def ingest_text(text: str) -> int:
    chunks = chunk_text(text)
    if not chunks:
        return 0
    embeddings = await asyncio.to_thread(embed_texts, chunks)
    await add_to_index(embeddings, chunks)
    return len(chunks)
