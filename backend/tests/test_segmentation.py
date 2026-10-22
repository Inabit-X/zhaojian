"""分段与说话人解析的纯函数测试。"""

from app.services.segmentation import (
    MAX_SEGMENT_CHARS,
    normalize_segments,
    parse_transcript,
    render_transcript,
)


def test_parse_transcript_with_speaker_labels() -> None:
    """行首说话人标签应被识别，且 idx 连续。"""
    text = (
        "咨询师：最近睡眠怎么样？\n"
        "来访者：不太好，总是醒。\n"
        "来访者：白天也没精神。"
    )
    segments = parse_transcript(text)

    assert [item["speaker"] for item in segments] == [
        "counselor",
        "client",
        "client",
    ]
    assert [item["idx"] for item in segments] == [0, 1, 2]
    assert segments[0]["text"] == "最近睡眠怎么样？"


def test_parse_transcript_without_labels() -> None:
    """没有标签时整段记为 unknown，仍可抽取。"""
    segments = parse_transcript("今天聊了聊最近的压力。")
    assert len(segments) == 1
    assert segments[0]["speaker"] == "unknown"
    assert segments[0]["idx"] == 0


def test_parse_transcript_splits_long_line() -> None:
    """超长单行应按句号切成多段，且每段不超过上限。"""
    text = "来访者：" + ("我最近很焦虑。" * 600)
    segments = parse_transcript(text)

    assert len(segments) > 1
    assert all(len(item["text"]) <= MAX_SEGMENT_CHARS for item in segments)


def test_render_transcript_round_trip() -> None:
    """分段渲染后应保留说话人标签。"""
    segments = parse_transcript("咨询师：你好\n来访者：老师好")
    rendered = render_transcript(segments)
    assert "咨询师：你好" in rendered
    assert "来访者：老师好" in rendered


def test_normalize_segments_strips_and_reindexes() -> None:
    """手工分段应去空白、去掉空段并重新编号。"""

    class Item:
        """测试用的最小分段对象。"""

        def __init__(self, speaker: str, text: str) -> None:
            """保存说话人与文本。"""
            self.speaker = speaker
            self.text = text
            self.start_ms = None
            self.end_ms = None

    segments = normalize_segments(
        [Item("client", "  你好  "), Item("counselor", "   ")]
    )
    assert len(segments) == 1
    assert segments[0]["text"] == "你好"
    assert segments[0]["idx"] == 0
