from app.memory.chunking import split_text


def test_short_text_single_chunk() -> None:
    assert split_text("今天很累。", 400, 50) == ["今天很累。"]


def test_empty_text_returns_nothing() -> None:
    assert split_text("   ", 400, 50) == []


def test_long_text_respects_chunk_size() -> None:
    text = "这是第一句话。" * 100
    chunks = split_text(text, 50, 10)
    assert len(chunks) > 1
    assert all(len(chunk) <= 50 for chunk in chunks)
    assert all(chunk.strip() for chunk in chunks)


def test_overlap_is_smaller_than_chunk_size() -> None:
    text = "一段没有标点的超长文本" * 60
    chunks = split_text(text, 40, 5)
    assert len(chunks) > 1
    assert all(len(chunk) <= 40 for chunk in chunks)
