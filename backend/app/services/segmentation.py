"""把粘贴的咨询全文切成带说话人的话语段（规则版，不依赖模型）。"""

import re
from typing import Any

MAX_SEGMENTS = 500
MAX_SEGMENT_CHARS = 4000

# 行首说话人标记，如「咨询师：」「来访者:」
_SPEAKER_RE = re.compile(r"^(咨询师|治疗师|老师|辅导员|来访者|学生|来访)\s*[：:]\s*(.*)$")
_SPEAKER_MAP = {
    "咨询师": "counselor",
    "治疗师": "counselor",
    "老师": "counselor",
    "辅导员": "counselor",
    "来访者": "client",
    "学生": "client",
    "来访": "client",
}


def _split_long(text: str) -> list[str]:
    """把超过单段上限的文本按句末标点切分并合并。"""
    if len(text) <= MAX_SEGMENT_CHARS:
        return [text.strip()] if text.strip() else []

    sentences = re.split(r"(?<=[。！？；!?;])", text)
    pieces: list[str] = []
    buffer = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(buffer) + len(sentence) > MAX_SEGMENT_CHARS and buffer:
            pieces.append(buffer.strip())
            buffer = ""
        while len(sentence) > MAX_SEGMENT_CHARS:
            pieces.append(sentence[:MAX_SEGMENT_CHARS].strip())
            sentence = sentence[MAX_SEGMENT_CHARS:]
        buffer += sentence
    if buffer.strip():
        pieces.append(buffer.strip())
    return [piece for piece in pieces if piece]


def parse_transcript(text: str) -> list[dict[str, Any]]:
    """按行解析说话人；无标记的整行记为 unknown，超长行自动切分。"""
    segments: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        speaker = "unknown"
        content = line
        match = _SPEAKER_RE.match(line)
        if match:
            speaker = _SPEAKER_MAP[match.group(1)]
            content = match.group(2).strip()
        if not content:
            continue
        for piece in _split_long(content):
            segments.append(
                {"speaker": speaker, "text": piece, "idx": len(segments)}
            )
            if len(segments) >= MAX_SEGMENTS:
                return segments

    if not segments and text.strip():
        for piece in _split_long(text.strip()):
            segments.append(
                {"speaker": "unknown", "text": piece, "idx": len(segments)}
            )
            if len(segments) >= MAX_SEGMENTS:
                break
    return segments


def normalize_segments(raw_segments: list[Any]) -> list[dict[str, Any]]:
    """把手工分段统一成 idx 连续、文本去空白的字典列表。"""
    segments: list[dict[str, Any]] = []
    for item in raw_segments:
        text = str(getattr(item, "text", "")).strip()
        if not text:
            continue
        speaker = str(getattr(item, "speaker", "unknown"))
        start_ms = getattr(item, "start_ms", None)
        end_ms = getattr(item, "end_ms", None)
        for piece in _split_long(text):
            segments.append(
                {
                    "speaker": speaker,
                    "text": piece,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                }
            )
            if len(segments) >= MAX_SEGMENTS:
                return segments
    for idx, segment in enumerate(segments):
        segment["idx"] = idx
    return segments


def render_transcript(segments: list[dict[str, Any]]) -> str:
    """把分段重新拼成带说话人标签的全文，用于落库与展示。"""
    labels = {"client": "来访者", "counselor": "咨询师", "unknown": ""}
    lines = []
    for segment in segments:
        label = labels.get(str(segment.get("speaker")), "")
        prefix = f"{label}：" if label else ""
        lines.append(f"{prefix}{segment['text']}")
    return "\n".join(lines)
