"""Lightweight RAG over local methodology docs — term-overlap scoring
over paragraph-level chunks, no vector store or embeddings API. Chosen
over a full embedding-based RAG because no vector-DB infra exists yet in
this stack (Redis arrives in Phase 10) and the corpus here is small
(a handful of markdown docs) — term overlap is deterministic, testable
without a network call, and sufficient at this scale.
"""

import re
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]

METHODOLOGY_DOCS = [
    _REPO_ROOT / "QUANT-TRADING-RULES.md",
    _REPO_ROOT / "MASTER-PRD.md",
]

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]*")


@dataclass(frozen=True, slots=True)
class DocChunk:
    source: str
    text: str


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(text)}


def _load_chunks(doc_paths: list[Path]) -> list[DocChunk]:
    chunks: list[DocChunk] = []
    for path in doc_paths:
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        for paragraph in raw.split("\n\n"):
            stripped = paragraph.strip()
            if len(stripped) < 20:  # skip near-empty/heading-only fragments
                continue
            chunks.append(DocChunk(source=path.name, text=stripped))
    return chunks


def retrieve_methodology_context(
    query: str, top_k: int = 3, doc_paths: list[Path] | None = None
) -> list[DocChunk]:
    """Returns the top_k chunks by term-overlap score against `query`.
    Deterministic and reproducible: identical query and corpus always
    produce the same ranking (ties broken by original document order)."""
    chunks = _load_chunks(doc_paths if doc_paths is not None else METHODOLOGY_DOCS)
    if not chunks:
        return []

    query_terms = _tokenize(query)
    if not query_terms:
        return []

    scored = [
        (len(query_terms & _tokenize(chunk.text)), index, chunk)
        for index, chunk in enumerate(chunks)
    ]
    scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [chunk for _, _, chunk in scored[:top_k]]
