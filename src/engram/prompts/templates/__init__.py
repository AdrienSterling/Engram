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

如果没有提到任何工具，回复"未发现工具推荐"。"""


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
