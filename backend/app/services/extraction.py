"""事实抽取：规则版保底 + 可选 LLM 增强。

原则：
- 每条事实必须带原文 quote，且 quote 必须出现在对应话语段里；
- 抽取结果只是「候选事实」，不生成诊断或治疗建议；
- LLM 不可用或输出不合法时静默回退规则版。
"""

import json
import re
from typing import Any

from app.core.exceptions import ProviderError
from app.providers.base import LLMProvider
from app.providers.factory import get_llm_provider
from app.services.segmentation import MAX_SEGMENTS

FACT_KINDS = (
    "presenting_issue",
    "event",
    "emotion",
    "cognition",
    "behavior",
    "relationship",
    "resource",
    "intervention",
    "homework",
    "risk",
    "unclear",
)

_RISK_WORDS = (
    "自杀",
    "自残",
    "不想活",
    "活不下去",
    "死了算了",
    "伤害自己",
    "割腕",
    "跳楼",
    "轻生",
)

_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("presenting_issue", ("主诉", "困扰", "问题", "最近", "睡不着", "焦虑")),
    (
        "emotion",
        (
            "焦虑", "紧张", "害怕", "恐惧", "难过", "伤心", "低落",
            "愤怒", "生气", "委屈", "羞耻", "内疚", "孤独", "无助",
            "绝望", "开心", "平静", "放松",
        ),
    ),
    (
        "cognition",
        (
            "觉得", "认为", "应该", "必须", "总是", "从不",
            "我不行", "没人", "都是我", "完蛋", "没用",
        ),
    ),
    (
        "behavior",
        (
            "失眠", "睡不着", "熬夜", "回避", "不去", "逃课",
            "哭泣", "自伤", "酗酒", "刷手机", "运动", "联系", "求助",
        ),
    ),
    (
        "relationship",
        (
            "室友", "同学", "父母", "妈妈", "爸爸",
            "男朋友", "女朋友", "老师", "导师", "家里",
        ),
    ),
    ("resource", ("喜欢", "擅长", "支持", "帮助", "朋友", "爱好", "运动", "音乐")),
    ("intervention", ("咨询师建议", "我们试试", "放松训练", "呼吸", "布置")),
    ("homework", ("作业", "练习", "记录", "尝试", "下周", "回去")),
    ("event", ("这次", "上次", "后来", "当时", "那天")),
)


def _normalize(text: str) -> str:
    """去掉所有空白，便于做 quote 包含校验。"""
    return re.sub(r"\s+", "", text)


def rule_based_facts(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按关键词为每个话语段抽取至多三条候选事实；命中风险词时只保留风险。"""
    facts: list[dict[str, Any]] = []
    for segment in segments:
        text = str(segment["text"])
        risk_hit = next((word for word in _RISK_WORDS if word in text), None)
        if risk_hit:
            facts.append(
                {
                    "segment_idx": segment["idx"],
                    "kind": "risk",
                    "value": {"text": text[:200], "keyword": risk_hit},
                    "quote": text[:300],
                    "confidence": 0.4,
                }
            )
            continue

        matched: list[tuple[str, str]] = []
        for kind, words in _RULES:
            hit = next((word for word in words if word in text), None)
            if hit is not None:
                matched.append((kind, hit))
            if len(matched) >= 3:
                break
        for kind, hit in matched:
            facts.append(
                {
                    "segment_idx": segment["idx"],
                    "kind": kind,
                    "value": {"text": text[:200], "keyword": hit},
                    "quote": text[:300],
                    "confidence": 0.35,
                }
            )
    return facts


_EXTRACTION_SYSTEM_PROMPT = """你是临床访谈信息抽取器，只做事实整理，不做诊断。
输入是带编号的咨询对话片段，每行格式为 [编号] 文本。
输出 JSON：
{"facts": [{"segment_idx": 0, "kind": "emotion",
            "value": {"text": "简述"}, "quote": "原文片段", "confidence": 0.0}]}
规则：
1. kind 只能是 presenting_issue/event/emotion/cognition/behavior/relationship/
   resource/intervention/homework/risk/unclear；
2. quote 必须逐字来自对应编号的原文，不得改写或拼接；
3. 只记录明确说到的内容，不推断、不补全、不做诊断；
4. 没有可抽取内容时返回 {"facts": []}；
5. 最多输出 40 条。"""


def parse_json_object(raw: str) -> dict[str, Any]:
    """从模型输出中截取第一个 JSON 对象并解析。"""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("未找到 JSON 对象")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("JSON 根节点不是对象")
    return data


async def llm_facts(
    segments: list[dict[str, Any]], provider: LLMProvider
) -> list[dict[str, Any]]:
    """调用 LLM 抽取并逐条校验 quote 与 kind；不合法的条目直接丢弃。"""
    numbered = "\n".join(
        f"[{segment['idx']}] {str(segment['text'])[:800]}"
        for segment in segments[:80]
    )
    raw = await provider.generate(
        [
            {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": numbered},
        ],
        temperature=0,
        max_tokens=2500,
    )
    data = parse_json_object(raw)
    items = data.get("facts", [])
    if not isinstance(items, list):
        return []

    by_idx = {int(segment["idx"]): segment for segment in segments}
    facts: list[dict[str, Any]] = []
    for item in items[:60]:
        if not isinstance(item, dict):
            continue
        try:
            segment_idx = int(item["segment_idx"])
        except (KeyError, TypeError, ValueError):
            continue
        segment = by_idx.get(segment_idx)
        if segment is None:
            continue
        kind = str(item.get("kind", "")).strip()
        quote = str(item.get("quote", "")).strip()
        if kind not in FACT_KINDS or not quote:
            continue
        if _normalize(quote) not in _normalize(str(segment["text"])):
            continue
        value = item.get("value")
        if not isinstance(value, dict):
            value = {"text": quote[:200]}
        confidence = item.get("confidence", 0.6)
        try:
            confidence_value = min(max(float(confidence), 0.0), 1.0)
        except (TypeError, ValueError):
            confidence_value = 0.6
        facts.append(
            {
                "segment_idx": segment_idx,
                "kind": kind,
                "value": value,
                "quote": quote[:300],
                "confidence": confidence_value,
            }
        )
    return facts


async def extract_facts(
    segments: list[dict[str, Any]], *, use_llm: bool
) -> tuple[list[dict[str, Any]], str]:
    """返回 (facts, generated_by)；LLM 失败或无结果时回退规则版。"""
    if use_llm:
        try:
            provider = get_llm_provider()
            facts = await llm_facts(segments[:MAX_SEGMENTS], provider)
            if facts:
                return facts, "llm"
        except (NotImplementedError, ProviderError, ValueError):
            pass
    return rule_based_facts(segments), "rule"
