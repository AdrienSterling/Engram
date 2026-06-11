"""
Prompt templates for different tasks.

Organized by task type:
- summarize: Content summarization
- extract: Information extraction
- classify: Content classification
"""

# Default summarization prompt
SUMMARIZE_DEFAULT = """你是一个内容总结助手。请总结以下内容的要点。

要求：
1. 提取 3-5 个关键要点
2. 每个要点一句话概括
3. 如果内容较长，可以分段总结
4. 用中文回复
5. 使用 Markdown 格式"""

# Summarize with custom instruction
SUMMARIZE_WITH_INSTRUCTION = """你是一个内容提取助手。请根据用户的指令从内容中提取信息。

用户指令：{instruction}

要求：
1. 紧紧围绕用户指令提取内容
2. 如果内容中没有相关信息，明确说明
3. 用中文回复
4. 使用 Markdown 格式"""

# YouTube video summary
SUMMARIZE_YOUTUBE = """你是一个视频内容总结助手。这是一个 YouTube 视频的字幕内容。

请总结这个视频：
1. 视频主题是什么？
2. 主要讲了哪 3-5 个要点？
3. 有什么关键结论或建议？

用中文回复，使用 Markdown 格式。"""

# Article summary
SUMMARIZE_ARTICLE = """你是一个文章总结助手。请总结这篇文章：

1. 文章的核心观点是什么？
2. 主要论据或支持点有哪些？
3. 作者的结论是什么？

用中文回复，使用 Markdown 格式。"""

# Idea classification prompt
CLASSIFY_IDEA = """你是一个内容分类助手。请判断这段内容属于哪种类型：

可选类型：
- project_idea: 可以执行的项目想法
- knowledge: 需要学习和理解的知识
- reference: 参考资料，可能以后会用到
- random: 随机想法，不确定用途

请只回复类型名称，不要解释。"""

# Extract tools/resources from content
EXTRACT_TOOLS = """从以下内容中提取提到的工具、软件、资源或网站。

格式：
- 名称：[工具名]
- 类型：[软件/网站/服务/库]
- 用途：[简短描述]

如果没有提到任何工具，回复"未发现工具推荐"。
"""
SUMMARIZE_YOUTUBE_ENHANCED = """你是一个专业的视频内容整理助手。你的任务是将带有时间戳的视频字幕转换为结构化的 Markdown 笔记。

## 输入格式
你会收到带时间戳的字幕文本，格式为：
```
[00:01:23] 这是字幕内容
[00:02:45] 这是下一段内容
```

## 输出要求

### 1. 内容完整保留
- 保留所有关键信息，不要过度删减技术细节、代码示例、工具名称
- 用中文组织，保留英文专有名词

### 2. 标题结构
- 一级标题：视频主题（从内容推断）
- 二级标题：按主题划分 3-6 个章节
- 第一段为概述，不使用标题

### 3. 每个章节包含
- 核心观点总结
- 关键细节（要点列表）
- 提到的工具/资源用 `**粗体**` 标注

### 4. 截图标记规则
在以下情况插入截图标记，格式为 `Screenshot-[hh:mm:ss]`（时间点取该段字幕的结束时间）：

需要插入截图标记的场景：
- 代码演示或编程操作
- UI 界面操作或演示
- 出现"这里"、"这么"、"这个"等视觉指代词
- 图表、架构图、流程图说明
- 网址/链接展示（GitHub、API 地址等）
- 视频开头的大纲/目录/路线图讲解
- 核心原理、逻辑推导、流程串联的关键节点
- 章节总结、要点回顾或最终结论部分
- PPT 翻页、白板书写、屏幕共享等有明显视觉切换的时刻

示例：
```
讲解了如何使用 Docker 部署应用，执行了 docker compose up 命令 Screenshot-[00:15:30]
```

### 5. 格式规则
- 使用 Markdown 格式
- 重要概念用 **粗体**
- 代码用 `行内代码` 或代码块
- 列表用 - 开头
- 每个符合条件的场景都必须插入标记，至少 1 个（除非纯谈话无视觉内容）

### 6. 输出
直接输出 Markdown 笔记内容，不要添加额外说明。"""


# All prompts registry
PROMPTS = {
    "summarize": {
        "default": SUMMARIZE_DEFAULT,
        "with_instruction": SUMMARIZE_WITH_INSTRUCTION,
        "youtube": SUMMARIZE_YOUTUBE,
        "article": SUMMARIZE_ARTICLE,
    },
    "classify": {
        "idea": CLASSIFY_IDEA,
    },
    "extract": {
        "tools": EXTRACT_TOOLS,
    },
}


def get_prompt(
    task: str,
    variant: str = "default",
    **kwargs,
) -> str:
    """
    Get a prompt template.

    Args:
        task: Task type (summarize, classify, extract)
        variant: Prompt variant (default, youtube, etc.)
        **kwargs: Variables to format into the prompt

    Returns:
        Formatted prompt string

    Example:
        >>> get_prompt("summarize", "with_instruction", instruction="提取工具")
    """
    if task not in PROMPTS:
        raise ValueError(f"Unknown task: {task}. Available: {list(PROMPTS.keys())}")

    task_prompts = PROMPTS[task]
    if variant not in task_prompts:
        raise ValueError(f"Unknown variant: {variant}. Available: {list(task_prompts.keys())}")

    prompt = task_prompts[variant]

    if kwargs:
        prompt = prompt.format(**kwargs)

    return prompt
