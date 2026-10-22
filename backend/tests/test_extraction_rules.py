"""规则抽取与 JSON 解析的单元测试。"""

import asyncio

import pytest

from app.services.extraction import (
    extract_facts,
    parse_json_object,
    rule_based_facts,
)


def test_rule_based_extracts_emotion_and_behavior() -> None:
    """情绪词与行为词应各命中，引文必须来自对应原文。"""
    segments = [
        {"idx": 0, "text": "我最近很焦虑。"},
        {"idx": 1, "text": "晚上总是睡不着。"},
    ]
    facts = rule_based_facts(segments)
    kinds = {item["kind"] for item in facts}
    source = {item["idx"]: item["text"] for item in segments}

    assert "emotion" in kinds
    assert "behavior" in kinds
    assert all(item["quote"] in source[item["segment_idx"]] for item in facts)


def test_risk_short_circuits_other_rules() -> None:
    """出现风险词时只保留风险事实。"""
    segments = [{"idx": 0, "text": "我不想活了，觉得没意思。"}]
    facts = rule_based_facts(segments)

    assert len(facts) == 1
    assert facts[0]["kind"] == "risk"


def test_no_match_returns_empty() -> None:
    """无关键词时不臆造事实。"""
    assert rule_based_facts([{"idx": 0, "text": "今天天气不错。"}]) == []


def test_extract_facts_falls_back_to_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM 抛错时回退规则抽取，不向上抛异常。"""

    async def boom(*args: object, **kwargs: object) -> list[dict]:
        raise ValueError("bad llm output")

    monkeypatch.setattr("app.services.extraction.llm_facts", boom)
    facts, generated_by = asyncio.run(
        extract_facts([{"idx": 0, "text": "我很焦虑"}], use_llm=True)
    )

    assert generated_by == "rule"
    assert facts


def test_parse_json_object_handles_code_fence() -> None:
    """兼容模型常见的 ```json 围栏输出。"""
    text = '```json\n{"facts": [{"kind": "emotion"}]}\n```'
    data = parse_json_object(text)

    assert data["facts"][0]["kind"] == "emotion"


def test_parse_json_object_raises_on_garbage() -> None:
    """非 JSON 文本应抛 ValueError，由调用方回退。"""
    with pytest.raises(ValueError):
        parse_json_object("这不是 JSON")
