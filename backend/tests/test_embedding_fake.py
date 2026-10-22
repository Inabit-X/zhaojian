import math

from app.providers.fake import FakeEmbeddingProvider


async def test_fake_embedding_is_deterministic() -> None:
    provider = FakeEmbeddingProvider(dimension=1536)
    first, second = await provider.embed_texts(["hello world", "hello world"])
    assert first == second
    assert len(first) == 1536


async def test_fake_embedding_is_normalized() -> None:
    provider = FakeEmbeddingProvider(dimension=256)
    [vector] = await provider.embed_texts(["照见自己，理解过去"])
    norm = math.sqrt(sum(value * value for value in vector))
    assert abs(norm - 1.0) < 1e-9


async def test_fake_embedding_handles_empty_input() -> None:
    provider = FakeEmbeddingProvider(dimension=16)
    assert await provider.embed_texts([]) == []
