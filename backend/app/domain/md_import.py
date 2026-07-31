"""Markdown FAQ 解析（纯函数，零框架依赖，可单测）。

约定：一个 md 文件含多条 FAQ，按标题切分——
  - 取文件中出现的最高标题层级（# 优先，其次 ##…）作为条目分隔；
  - 标题文本 -> title，标题到下一个同级/更高级标题之间的正文 -> content；
  - 标题前的引言、代码块内的 # 均忽略；空 content 的条目跳过。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass
class ParsedItem:
    title: str
    content: str


def parse_markdown_faq(text: str) -> list[ParsedItem]:
    lines = (text or "").splitlines()

    # 1) 找出所有标题（跳过代码块内的 #），确定分隔层级 = 最小的标题级数
    in_fence = False
    headings: list[tuple[int, int, str]] = []  # (line_idx, level, title)
    for i, line in enumerate(lines):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING.match(line)
        if m:
            headings.append((i, len(m.group(1)), m.group(2).strip()))

    if not headings:
        return []

    split_level = min(h[1] for h in headings)
    anchors = [h for h in headings if h[1] == split_level]

    # 2) 每个分隔标题到下一个分隔标题之间为一条；正文里保留更深层级的小标题
    items: list[ParsedItem] = []
    for idx, (line_idx, _lvl, title) in enumerate(anchors):
        end = anchors[idx + 1][0] if idx + 1 < len(anchors) else len(lines)
        body = "\n".join(lines[line_idx + 1 : end]).strip()
        if body:
            items.append(ParsedItem(title=title[:256], content=body))
    return items
