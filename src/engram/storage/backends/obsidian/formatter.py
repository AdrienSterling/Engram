"""Markdown formatters for Obsidian."""

from datetime import datetime

from engram.core.types import Idea, InboxItem, KnowledgeArea, Material


class ObsidianFormatter:
    """Format content as Obsidian-compatible Markdown."""

    def format_idea(self, idea: Idea) -> str:
        """Format idea as Markdown."""
        now = datetime.now().strftime("%Y-%m-%d")

        return f"""---
tags: [灵感]
status: {idea.status}
created: {now}
updated: {now}
summary: "{idea.summary}"
energy: 中
---

# {idea.title}

## 一句话
{idea.summary}

---

## 迭代记录

| 日期 | 更新内容 |
|:---|:---|
| {now} | 初始想法（通过 Telegram 记录） |
"""

    def format_knowledge_area(self, area: KnowledgeArea) -> str:
        """Format knowledge area as Markdown."""
        now = datetime.now().strftime("%Y-%m-%d")

        return f"""---
tags: [知识领域]
created: {now}
updated: {now}
output_commitment: "{area.output_commitment}"
status: {area.status}
---

# {area.title}

## 输出承诺
{area.output_commitment}

## 我的当前理解
> 用自己的话写，这是内化的关键

（待补充）

## 知识地图
- [ ] 基础概念
- [ ] 应用场景
- [ ] 行业动态

## 收集的材料

| 日期 | 类型 | 标题 | 消化状态 | 核心收获 |
|:---|:---|:---|:---|:---|
| | | | | |

## 输出记录
（当你基于这个领域产出内容时记录在这里）
"""

    def format_material(self, material: Material) -> str:
        """Format material as Markdown."""
        now = material.captured_at.strftime("%Y-%m-%d %H:%M")
        source_emoji = {
            "youtube": "📺",
            "article": "📄",
            "pdf": "📑",
            "image": "🖼️",
            "text": "📝",
        }.get(material.source_type.value, "📎")

        return f"""---
source_type: {material.source_type.value}
source_url: "{material.source_url or ''}"
captured_at: {now}
user_query: "{material.user_query or ''}"
digest_status: {material.digest_status.value}
---

# {source_emoji} {material.title}

## 提取内容

{material.content}

## 核心收获

> 用自己的话写（消化后填写）

{material.core_insight or '（待补充）'}
"""

    def format_inbox_header(self) -> str:
        """Format inbox file header."""
        return """# 临时收集箱

> [!warning] 这里的内容会过期
> 7 天内未归档的内容将被清理。定期检查并决定去留。

---
"""

    def format_inbox_item(self, item: InboxItem) -> str:
        """Format single inbox item."""
        material = item.material
        captured = material.captured_at.strftime("%Y-%m-%d %H:%M")
        expires = item.expires_at.strftime("%Y-%m-%d %H:%M")

        source_emoji = {
            "youtube": "📺",
            "article": "📄",
            "pdf": "📑",
            "image": "🖼️",
            "text": "📝",
        }.get(material.source_type.value, "📎")

        return f"""
## {material.captured_at.strftime("%Y-%m-%d")}

### {source_emoji} {material.title}
- 来源：{material.source_url or 'N/A'}
- 捕获时间：{captured}
- 过期时间：{expires}
- 指令：{material.user_query or '总结'}
- 状态：pending
- 内容：

{material.content}

---
"""
