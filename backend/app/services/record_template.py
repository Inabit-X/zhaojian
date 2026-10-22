"""四段记录草稿：规则模板保底 + 可选 LLM 增强。

输出只基于已抽取的事实条目，每条附 [E#] 引用；未提及的内容必须显式写「未提及」。
"""

from typing import Any

from app.core.exceptions import ProviderError
from app.providers.base import LLMProvider
from app.providers.factory import get_llm_provider
from app.schemas.record import RecordSections
from app.services.extraction import parse_json_object

SECTION_KEYS = ("presenting", "observations", "formulation", "plan")
EMPTY = "未提及"
_PLAN_EMPTY = "未提及，待咨询师补充"


def _clean(text: str) -> str:
    """压缩空白并截断，避免单条引用过长。"""
    return " ".join(text.split())[:300]


def template_sections(facts: list[dict[str, Any]]) -> dict[str, str]:
    """按事实类别填四段模板；每条事实带 [E#] 引用。"""
    groups: dict[str, list[str]] = {key: [] for key in SECTION_KEYS}
    for idx, fact in enumerate(facts, start=1):
        kind = str(fact.get("kind", "unclear"))
        quote = fact.get("quote")
        if not quote:
            value = fact.get("value")
            if isinstance(value, dict):
                quote = str(value.get("text", ""))
        line = f"{_clean(str(quote))} [E{idx}]"
        if kind in {"presenting_issue", "event"}:
            groups["presenting"].append(line)
        elif kind in {"emotion", "behavior", "relationship", "resource", "risk"}:
            groups["observations"].append(line)
        elif kind == "cognition":
            groups["formulation"].append(line)
        elif kind in {"intervention", "homework"}:
            groups["plan"].append(line)

    sections = {
        "presenting": "；".join(groups["presenting"]) or EMPTY,
        "observations": "；".join(groups["observations"]) or EMPTY,
        "formulation": (
            "咨询师待核对的假设（非诊断）：" + "；".join(groups["formulation"])
            if groups["formulation"]
            else EMPTY
        ),
        "plan": "；".join(groups["plan"]) or _PLAN_EMPTY,
    }
    return sections


_SECTIONS_SYSTEM_PROMPT = """你是心理咨询记录草稿助手，只做文书整理，不做诊断或治疗决策。
输入是从本次会谈中抽取的事实条目，每行格式为 [E编号] 类别：原文。
输出 JSON：{"presenting": "...", "observations": "...", "formulation": "...", "plan": "..."}
四段含义：presenting=主诉与背景；observations=咨询师观察到的情绪/行为/关系；
formulation=待核对的个案假设（必须注明非诊断）；plan=后续计划或作业。
规则：
1. 只使用输入事实，不补充、不推断未出现的信息；
2. 没有对应信息时写「未提及」；
3. 每条陈述后保留 [E编号] 引用；
4. 使用中文、客观、简洁；
5. 不出现诊断名称、药物建议或疗效承诺。"""


async def llm_sections(
    facts: list[dict[str, Any]], provider: LLMProvider
) -> dict[str, str] | None:
    """调用 LLM 生成四段；结构不合法时返回 None 由调用方回退模板。"""
    lines = []
    for idx, fact in enumerate(facts, start=1):
        quote = fact.get("quote") or ""
        if not quote:
            value = fact.get("value")
            if isinstance(value, dict):
                quote = str(value.get("text", ""))
        lines.append(f"[E{idx}] {fact.get('kind', 'unclear')}：{_clean(str(quote))}")

    raw = await provider.generate(
        [
            {"role": "system", "content": _SECTIONS_SYSTEM_PROMPT},
            {"role": "user", "content": "\n".join(lines)},
        ],
        temperature=0.2,
        max_tokens=2000,
    )
    data = parse_json_object(raw)
    sections: dict[str, str] = {}
    for key in SECTION_KEYS:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            return None
        sections[key] = value.strip()[:5000]
    return sections


async def generate_sections(
    facts: list[dict[str, Any]], *, use_llm: bool
) -> tuple[dict[str, str], str]:
    """返回 (sections, generated_by)；LLM 失败或未配置时回退规则模板。"""
    if use_llm and facts:
        try:
            provider = get_llm_provider()
            sections = await llm_sections(facts, provider)
            if sections is not None:
                return sections, "llm"
        except (NotImplementedError, ProviderError, ValueError):
            pass
    return template_sections(facts), "rule"


__all__ = [
    "EMPTY",
    "SECTION_KEYS",
    "RecordSections",
    "generate_sections",
    "llm_sections",
    "template_sections",
]
