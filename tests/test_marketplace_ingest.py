from src.marketplace_ingest import chunk_document


def test_chunk_document_preserves_order_and_bounds():
    text = "seller asset buyer update order handoff"
    assert chunk_document(text, size=2) == ["seller asset", "buyer update", "order handoff"]

