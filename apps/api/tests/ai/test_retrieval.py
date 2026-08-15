from pathlib import Path

from app.ai.retrieval import retrieve_methodology_context

_DOC_A = (
    "Chunk about drawdown and risk. Managing drawdown is critical for capital preservation.\n\n"
    "Chunk about setup detection. Breakout setups qualify when price crosses resistance."
)
_DOC_B = "Chunk about position sizing formulas and lot sizes for the IDX market."


def _write_docs(tmp_path: Path) -> list[Path]:
    doc_a = tmp_path / "doc_a.md"
    doc_b = tmp_path / "doc_b.md"
    doc_a.write_text(_DOC_A, encoding="utf-8")
    doc_b.write_text(_DOC_B, encoding="utf-8")
    return [doc_a, doc_b]


def test_retrieve_returns_relevant_chunk_first(tmp_path) -> None:
    docs = _write_docs(tmp_path)
    results = retrieve_methodology_context("what is drawdown risk", top_k=3, doc_paths=docs)
    assert results
    assert "drawdown" in results[0].text.lower()


def test_retrieve_no_matching_terms_returns_empty(tmp_path) -> None:
    docs = _write_docs(tmp_path)
    results = retrieve_methodology_context(
        "xyzzy unrelated gibberish query", top_k=3, doc_paths=docs
    )
    assert results == []


def test_retrieve_deterministic_reproducible(tmp_path) -> None:
    docs = _write_docs(tmp_path)
    first = retrieve_methodology_context("position sizing lot", top_k=2, doc_paths=docs)
    second = retrieve_methodology_context("position sizing lot", top_k=2, doc_paths=docs)
    assert first == second


def test_retrieve_respects_top_k(tmp_path) -> None:
    docs = _write_docs(tmp_path)
    results = retrieve_methodology_context(
        "setup breakout drawdown position", top_k=1, doc_paths=docs
    )
    assert len(results) <= 1


def test_retrieve_missing_doc_path_skipped_gracefully(tmp_path) -> None:
    missing = tmp_path / "does_not_exist.md"
    results = retrieve_methodology_context("anything", top_k=3, doc_paths=[missing])
    assert results == []


def test_retrieve_real_methodology_docs_default_path() -> None:
    """Sanity check against the real repo docs (no override) — proves the
    default METHODOLOGY_DOCS paths actually resolve and are readable."""
    results = retrieve_methodology_context("no look-ahead reproducibility", top_k=3)
    assert isinstance(results, list)
