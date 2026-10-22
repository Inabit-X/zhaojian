"""记录模板与内容解析的单元测试。"""

from app.schemas.record import RecordSections
from app.services.record_template import template_sections


def test_template_maps_evidence_numbers() -> None:
    """模板应带 [E#] 引用，且可被 RecordSections 接受。"""
    facts = [
        {"kind": "presenting_issue", "quote": "最近睡不好", "value": {}},
        {"kind": "cognition", "quote": "我觉得自己没用", "value": {}},
        {"kind": "homework", "quote": "下周记录睡眠", "value": {}},
    ]
    sections = template_sections(facts)

    assert "[E1]" in sections["presenting"]
    assert "非诊断" in sections["formulation"]
    assert "[E3]" in sections["plan"]
    RecordSections(**sections)


def test_template_empty_marks_not_mentioned() -> None:
    """空事实时明确写“未提及”，不补全内容。"""
    sections = template_sections([])

    assert sections["observations"] == "未提及"
    assert sections["plan"] == "未提及，待咨询师补充"
    RecordSections(**sections)
