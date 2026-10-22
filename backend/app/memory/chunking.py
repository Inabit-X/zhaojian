"""事件切片。中文优先按段落/句末切，英文按句末/空格切，最后硬切。

切片只服务检索：不改变原文语义，不生成摘要。
"""

import re

# 从强到弱的分隔符，命中即在此断开
_SEPARATORS = (
    "\n\n",
    "\n",
    "。",
    "！",
    "？",
    "；",
    ". ",
    "! ",
    "? ",
    "; ",
    "，",
    ", ",
    " ",
)

_WHITESPACE_RE = re.compile(r"[ \t]+")


def _find_cut(text: str, start: int, end: int) -> int:
    """从 end 向前找最近的句子边界，找不到则退回硬切。"""
    window = text[start:end]
    best = -1
    for separator in _SEPARATORS:
        index = window.rfind(separator)
        if index > best:
            best = index
    if best == -1:
        return end
    return start + best + 1


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """按段落与句末标点切片，合并到目标长度并保留重叠。"""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            cut = _find_cut(text, start, end)
            # 断点太靠前会让切片过短，此时宁可硬切
            if cut > start + chunk_size // 2:
                end = cut
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks
