"""
Telegram message handlers.

Handles all incoming messages and routes them appropriately.

## 上下文管理说明

使用 `context.user_data` 存储每个用户的会话状态：

```python
context.user_data['session'] = {
    'title': str,           # 内容标题
    'source_url': str,      # 来源 URL
    'source_type': str,     # 来源类型 (youtube/article)
    'content': str,         # 原始内容（用于追问时提供上下文）
    'summary': str,         # AI 生成的总结
    'messages': [           # 对话历史（用于多轮对话）
        {'role': 'system', 'content': '...'},
        {'role': 'assistant', 'content': '总结内容'},
        {'role': 'user', 'content': '用户追问'},
        {'role': 'assistant', 'content': 'AI回答'},
    ]
}
```

关键点：
1. context.user_data 按用户 ID 隔离，不同用户互不影响
2. 数据存在内存中，Bot 重启会清空（可换 Redis 持久化）
3. messages 数组累积对话历史，实现多轮对话
"""

import asyncio
import logging
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from engram.core.types import Message, SourceType
from engram.extractors import ExtractorRegistry, YouTubeExtractor
from engram.extractors.screenshot import ScreenshotExtractor
from engram.llm import get_llm
from engram.llm.router import run_diagnostic
from engram.skills.review.coach import ReviewCoach
from engram.storage import get_storage

logger = logging.getLogger(__name__)

# Global instances (initialized on first use)
_extractor_registry: Optional[ExtractorRegistry] = None
_chat_id_file: Optional[Path] = None


def _save_chat_id(chat_id: int):
    """Persist chat_id for scheduler proactive messages."""
    global _chat_id_file
    if _chat_id_file is None:
        from engram.core.config import get_settings

        vault = Path(get_settings().vault_path)
        _chat_id_file = vault / ".engram_chat_id"
    _chat_id_file.write_text(str(chat_id))


def _load_chat_id() -> Optional[int]:
    """Load persisted chat_id."""
    global _chat_id_file
    if _chat_id_file is None:
        from engram.core.config import get_settings

        vault = Path(get_settings().vault_path)
        _chat_id_file = vault / ".engram_chat_id"
    if _chat_id_file.exists():
        try:
            return int(_chat_id_file.read_text().strip())
        except (ValueError, OSError):
            pass
    return None


def get_extractor_registry() -> ExtractorRegistry:
    """Get or create extractor registry."""
    global _extractor_registry
    if _extractor_registry is None:
        _extractor_registry = ExtractorRegistry()
    return _extractor_registry


def escape_markdown(text: str) -> str:
    """Escape Markdown special characters for Telegram."""
    escape_chars = [
        "_",
        "*",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ]
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text


# ============ Session Management ============
# 会话管理：存储和获取用户的对话上下文


def get_session(context: ContextTypes.DEFAULT_TYPE) -> Optional[dict]:
    """
    获取当前用户的会话数据。

    context.user_data 是 Telegram 框架提供的字典，
    按 user_id 自动隔离，每个用户有独立的存储空间。
    """
    return context.user_data.get("session")


def set_session(context: ContextTypes.DEFAULT_TYPE, session: dict):
    """
    设置当前用户的会话数据。

    会话数据包括：
    - title: 内容标题
    - source_url: 来源链接
    - source_type: 来源类型
    - content: 原始内容（截断版，用于上下文）
    - summary: AI 总结
    - messages: 对话历史数组
    """
    context.user_data["session"] = session


def clear_session(context: ContextTypes.DEFAULT_TYPE):
    """清除当前用户的会话数据。"""
    context.user_data.pop("session", None)


def has_active_session(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """检查用户是否有活跃的会话。"""
    return "session" in context.user_data


# ============ Review Session Management ============


def get_review_session(context: ContextTypes.DEFAULT_TYPE) -> Optional[dict]:
    """获取当前用户的复习会话。"""
    return context.user_data.get("review_session")


def set_review_session(context: ContextTypes.DEFAULT_TYPE, session: dict):
    """设置当前用户的复习会话。"""
    context.user_data["review_session"] = session


def clear_review_session(context: ContextTypes.DEFAULT_TYPE):
    """清除当前用户的复习会话。"""
    context.user_data.pop("review_session", None)


def has_review_session(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """检查用户是否有活跃的复习会话。"""
    return "review_session" in context.user_data


# ============ Command Handlers ============


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    clear_session(context)  # 清除旧会话
    _save_chat_id(update.effective_chat.id)
    welcome_message = """👋 你好！我是 *Engram* \\- 你的知识管理助手

我可以帮你：
📺 提取 YouTube 视频内容
📄 总结网页文章
💬 对内容进行追问
💾 保存到 Obsidian

*使用方法：*
1\\. 发送链接 → 获取总结
2\\. 继续提问 → 深入了解
3\\. 发送 /save → 保存笔记

输入 /help 查看更多帮助。
"""
    await update.message.reply_text(welcome_message, parse_mode="MarkdownV2")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_message = """📖 Engram 使用指南

【基础功能】
• 发送 YouTube 链接 → 获取视频总结
• 发送网页/微信文章链接 → 获取文章摘要

【追问对话】
• 总结后直接发文字提问
• 例如："详细说说第3点"
• 例如："有哪些工具推荐？"

【保存笔记】
• /save → 保存当前对话到 Obsidian
• /save 想法标题 → 指定保存的标题

【其他命令】
• /clear → 清除当前对话
• /status → 查看当前会话状态
"""
    await update.message.reply_text(help_message)


async def save_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /save command - 保存当前会话到 Obsidian。

    实现原理：
    1. 检查是否有活跃会话
    2. 格式化内容为 Markdown
    3. 调用 Storage 层写入文件
    """
    session = get_session(context)

    if not session:
        await update.message.reply_text(
            "❌ 没有可保存的内容\n\n" "先发送一个链接，我总结后你就可以保存了。"
        )
        return

    # 检查是否有自定义标题
    text = update.message.text or ""
    custom_title = text.replace("/save", "").strip()
    title = custom_title if custom_title else session.get("title", "Untitled")

    processing_msg = await update.message.reply_text("💾 正在保存...")

    try:
        # 格式化为 Markdown
        content = format_session_for_save(session, title)

        # 保存到 Obsidian
        storage = get_storage()

        # 生成文件名（去除特殊字符）
        safe_title = re.sub(r'[<>:"/\\|?*]', "", title)[:50]
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{date_str}-{safe_title}.md"

        # 保存到 Inbox 文件夹
        await storage.save_to_inbox(filename, content)

        # Mark note for spaced-repetition review
        filepath = str(storage.inbox_path / filename)
        try:
            from engram.core.config import get_settings

            coach = ReviewCoach(vault_path=get_settings().vault_path)
            coach.mark_for_review(filepath)
        except Exception as e:
            logger.warning(f"Failed to mark for review: {e}")

        await processing_msg.edit_text(
            f"✅ 已保存到 Obsidian\n\n"
            f"📄 {filename}\n"
            f"📁 位置：Inbox/\n\n"
            "发送新链接开始下一个话题。"
        )

        # 清除会话
        clear_session(context)

    except Exception as e:
        logger.error(f"Save error: {e}")
        await processing_msg.edit_text(f"❌ 保存失败：{str(e)}")


async def clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command - 清除当前会话。"""
    clear_session(context)
    clear_review_session(context)
    await update.message.reply_text("🗑️ 已清除当前对话\n\n发送新链接开始新话题。")


async def skip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /skip command - 跳过当前复习题。"""
    session = get_review_session(context)
    if not session:
        await update.message.reply_text("📭 当前没有复习会话")
        return

    from engram.core.config import get_settings

    coach = ReviewCoach(vault_path=get_settings().vault_path)
    questions = session["questions"]
    current_q = session["current_q"]

    session["answers"].append(
        {
            "question": questions[current_q]["question"],
            "user_answer": "（跳过）",
            "feedback": "⏭ 已跳过",
        }
    )

    session["current_q"] += 1

    if session["current_q"] < len(questions):
        next_q = session["current_q"]
        q = questions[next_q]
        set_review_session(context, session)
        await update.message.reply_text(
            f"⏭ 已跳过\n\n"
            f"*问题 {next_q + 1}/3：*\n{q['question']}\n\n"
            f"———\n回复你的答案，或 /skip 跳过",
            parse_mode="Markdown",
        )
    else:
        msg = await update.message.reply_text("🔄 完成复习...")
        await _finish_review(update, msg, context, session, coach)


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - 查看当前会话状态。"""
    session = get_session(context)

    if not session:
        await update.message.reply_text("📭 当前没有活跃的会话\n\n发送链接开始。")
        return

    msg_count = len(session.get("messages", [])) - 1  # 减去 system message
    await update.message.reply_text(
        f"📊 当前会话状态\n\n"
        f"📌 标题：{session.get('title', 'Unknown')}\n"
        f"🔗 来源：{session.get('source_type', 'Unknown')}\n"
        f"💬 对话轮数：{msg_count // 2}\n\n"
        f"可以继续提问，或 /save 保存，或 /clear 清除。"
    )


async def llmtest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /llmtest command - 诊断 LLM 连接和余额。"""
    msg = await update.message.reply_text("🔍 正在检测 LLM 连接...")
    try:
        report = await run_diagnostic()
        await msg.edit_text(report)
    except Exception as e:
        await msg.edit_text(f"❌ 诊断失败: {str(e)}")


async def review_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /review command - 开始知识复习。"""
    from engram.core.config import get_settings

    settings = get_settings()
    coach = ReviewCoach(vault_path=settings.vault_path)

    due_items = coach.get_due_items()

    if not due_items:
        await update.message.reply_text(
            "📭 当前没有需要复习的内容\n\n"
            "保存笔记后，第二天就会出现在复习列表里。\n"
            "复习间隔：1天 → 3天 → 7天 → 30天"
        )
        return

    item = due_items[0]
    questions = await coach.generate_questions(item["title"], item["summary"], item["review_count"])

    if not questions:
        await update.message.reply_text("❌ 生成复习题失败，请稍后再试")
        return

    review_session = {
        "title": item["title"],
        "filepath": item["filepath"],
        "review_count": item["review_count"],
        "questions": questions,
        "current_q": 0,
        "answers": [],
    }

    set_review_session(context, review_session)

    q = questions[0]
    await update.message.reply_text(
        f"📚 复习：*{item['title']}*\n"
        f"（第 {item['review_count'] + 1} 次复习）\n\n"
        f"*问题 1/3：*\n{q['question']}\n\n"
        f"———\n回复你的答案，或 /skip 跳过",
        parse_mode="Markdown",
    )


async def handle_review_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle user's answer during review session."""
    session = get_review_session(context)
    if not session:
        return

    from engram.core.config import get_settings

    coach = ReviewCoach(vault_path=get_settings().vault_path)

    current_q = session["current_q"]
    questions = session["questions"]

    if current_q >= len(questions):
        clear_review_session(context)
        return

    q = questions[current_q]

    processing_msg = await update.message.reply_text("🤔 评估中...")

    try:
        feedback = await coach.evaluate_answer(q["question"], q.get("answer", ""), text)

        session["answers"].append(
            {
                "question": q["question"],
                "user_answer": text,
                "feedback": feedback,
            }
        )

        session["current_q"] += 1
        next_q = session["current_q"]

        if next_q < len(questions):
            next_question = questions[next_q]
            set_review_session(context, session)

            await processing_msg.edit_text(
                f"{feedback}\n\n"
                f"*问题 {next_q + 1}/3：*\n{next_question['question']}\n\n"
                f"———\n回复你的答案，或 /skip 跳过",
                parse_mode="Markdown",
            )
        else:
            await _finish_review(update, processing_msg, context, session, coach)

    except Exception as e:
        logger.error(f"Review evaluation error: {e}")
        await processing_msg.edit_text(f"❌ 评估失败：{str(e)}")


async def _finish_review(update, processing_msg, context, session, coach):
    """Complete review session, generate summary, update state."""
    clear_review_session(context)

    qa_text = "\n\n".join(
        f"Q: {a['question']}\n你的回答: {a['user_answer']}\n反馈: {a['feedback']}"
        for a in session["answers"]
    )

    try:
        review_summary = await coach.generate_review_summary(session["title"], qa_text)
    except Exception:
        review_summary = "复习完成！"

    coach.advance_review_state(session["filepath"], session["review_count"])

    new_count = session["review_count"] + 1
    await processing_msg.edit_text(
        f"✅ 复习完成！\n\n"
        f"📝 *{session['title']}*\n\n"
        f"{review_summary}\n\n"
        f"———\n"
        f"📊 复习进度：{new_count}/4\n"
        f"⏭ 下次复习：{coach.get_next_interval(new_count)}天后\n\n"
        f"继续 /review 复习下一篇，或发送链接学习新内容",
        parse_mode="Markdown",
    )


# ============ Message Handlers ============


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming messages.

    路由逻辑：
    1. 包含 URL → 提取内容并总结（开始新会话）
    2. 纯文本 + 有会话 → 追问
    3. 纯文本 + 无会话 → 提示发送链接
    """
    message = update.message
    text = message.text or message.caption or ""

    _save_chat_id(update.effective_chat.id)
    logger.info(f"Received message: {text[:100]}...")

    # Extract URLs from message
    urls = extract_urls(text)

    if urls:
        # 有 URL → 处理链接（开始新会话）
        await handle_url_message(update, context, text, urls)
    elif message.document:
        await handle_document(update, context)
    elif message.photo:
        await handle_photo(update, context)
    elif has_review_session(context):
        await handle_review_answer(update, context, text)
    elif has_active_session(context):
        # 有活跃会话 → 追问
        await handle_followup(update, context, text)
    else:
        # 无会话，无链接 → 提示
        await update.message.reply_text(
            "💡 发送链接即可提取内容\n\n" "支持：YouTube、微信公众号、网页文章"
        )


async def handle_url_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    urls: list[str],
):
    """
    Handle message containing URL(s).

    处理流程：
    1. 提取内容（字幕/文章）
    2. LLM 总结
    3. 创建新会话，保存上下文
    4. 返回总结
    """
    url = urls[0]
    instruction = extract_instruction(text, url)

    processing_msg = await update.message.reply_text("🔄 正在处理...")

    try:
        # 提取内容
        registry = get_extractor_registry()
        extractor = await registry.get_extractor(url)

        if extractor is None:
            await processing_msg.edit_text(
                "❌ 暂不支持该类型的链接\n\n" "目前支持：YouTube、微信公众号、网页文章"
            )
            return

        await processing_msg.edit_text("🔄 正在提取内容...")
        result = await extractor.extract(url)

        llm = get_llm()

        # YouTube: use enhanced summarization with screenshot markers
        if result.source_type == SourceType.YOUTUBE and isinstance(extractor, YouTubeExtractor):
            summary = await _summarize_youtube_enhanced(
                update, processing_msg, extractor, url, result, instruction, llm
            )
        else:
            await processing_msg.edit_text("🔄 正在生成总结...")
            summary = await llm.summarize(result.content, instruction)

        # 创建会话上下文
        session = {
            "title": result.title,
            "source_url": url,
            "source_type": result.source_type.value,
            "content": result.content[:8000],
            "summary": summary,
            "messages": [
                {
                    "role": "system",
                    "content": f"""你是一个内容分析助手。用户刚刚阅读了以下内容的总结，现在可能会有追问。

内容标题：{result.title}
内容类型：{result.source_type.value}
内容摘要：
{summary}

原始内容（部分）：
{result.content[:4000]}

请基于以上内容回答用户的问题。如果问题超出内容范围，请如实说明。用中文回答。""",
                },
                {"role": "assistant", "content": summary},
            ],
        }
        set_session(context, session)

        # 格式化响应
        source_emoji = {
            "youtube": "📺",
            "article": "📄",
            "pdf": "📑",
            "image": "🖼️",
        }.get(result.source_type.value, "📎")

        response = f"""{source_emoji} {result.title}

{summary}

———
🔗 {url}

💬 可以继续提问，或 /save 保存笔记"""

        await processing_msg.edit_text(response)
        logger.info(f"Successfully processed URL: {url}")

    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        await processing_msg.edit_text(f"❌ 处理失败\n\n错误：{str(e)}")


async def _summarize_youtube_enhanced(
    update: Update,
    processing_msg,
    extractor: YouTubeExtractor,
    url: str,
    result,
    instruction: Optional[str],
    llm,
) -> str:
    """
    Enhanced YouTube summarization with structured Markdown and screenshots.

    Flow:
    1. Get timestamped transcript
    2. LLM generates structured Markdown with Screenshot markers
    3. Download video and extract frames at marked timestamps
    4. Replace markers with image references
    5. Send screenshots to Telegram
    6. Save to vault assets

    Falls back to normal summarization if any step fails.
    """
    video_id = extractor._extract_video_id(url)
    if not video_id:
        return await llm.summarize(result.content, instruction)

    timestamped = await extractor.get_timestamped_transcript(video_id)
    if not timestamped:
        logger.info("No timestamped transcript available, using normal summary")
        return await llm.summarize(result.content, instruction)

    await processing_msg.edit_text("🔄 正在生成结构化总结...")
    summary = await llm.summarize_youtube(timestamped, instruction)

    markers = ScreenshotExtractor.parse_markers(summary)
    if not markers:
        return summary

    await processing_msg.edit_text(f"🔄 正在下载视频并截取 {len(markers)} 张关键帧...")

    temp_dir = Path(tempfile.mkdtemp(prefix="engram_"))
    assets_dir = temp_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    screenshotter = ScreenshotExtractor(assets_dir=assets_dir)
    video_path = await screenshotter.download_video(url)

    if not video_path:
        logger.warning("Video download failed, returning summary without screenshots")
        return summary

    timestamps = [ts for _, ts in markers]
    frame_map = screenshotter.extract_frames(video_path, timestamps)

    if frame_map:
        summary = screenshotter.replace_markers(summary, frame_map, image_rel_path="../assets")

        storage = get_storage()
        for ts, frame_path in frame_map.items():
            try:
                await storage.save_asset(str(frame_path), frame_path.name)
            except Exception as e:
                logger.warning(f"Failed to save asset to vault: {e}")

        for ts, frame_path in frame_map.items():
            try:
                with open(frame_path, "rb") as f:
                    await update.message.reply_photo(f)
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.warning(f"Failed to send screenshot: {e}")

    screenshotter.cleanup()

    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    return summary


async def handle_followup(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
):
    """
    Handle follow-up questions (追问).

    实现多轮对话的关键：
    1. 获取会话中的 messages 历史
    2. 添加用户新问题
    3. 发送给 LLM（带完整历史）
    4. 保存 AI 回复到历史
    """
    session = get_session(context)
    if not session:
        return

    processing_msg = await update.message.reply_text("🤔 思考中...")

    try:
        # 添加用户问题到对话历史
        session["messages"].append({"role": "user", "content": text})

        # 调用 LLM（带完整对话历史）
        llm = get_llm()

        # 转换为 Message 对象
        messages = [Message(role=m["role"], content=m["content"]) for m in session["messages"]]

        response = await llm.chat(messages, temperature=0.7)
        answer = response.content

        # 保存 AI 回复到历史
        session["messages"].append({"role": "assistant", "content": answer})
        set_session(context, session)

        # 返回回答
        await processing_msg.edit_text(
            f"{answer}\n\n" f"———\n" f"💬 继续提问 | /save 保存 | /clear 清除"
        )

    except Exception as e:
        logger.error(f"Followup error: {e}")
        await processing_msg.edit_text(f"❌ 回答失败：{str(e)}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document upload (PDF, etc.)."""
    await update.message.reply_text("📑 文档处理功能开发中...\n\n" "目前支持：YouTube、网页文章")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo upload."""
    await update.message.reply_text("🖼️ 图片识别功能开发中...\n\n" "目前支持：YouTube、网页文章")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Error: {context.error}")
    if update and update.message:
        await update.message.reply_text("❌ 发生错误，请稍后重试")


# ============ Helper Functions ============


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(url_pattern, text)


def extract_instruction(text: str, url: str) -> Optional[str]:
    """Extract custom instruction from message."""
    url_index = text.find(url)
    if url_index > 0:
        instruction = text[:url_index].strip()
        if instruction:
            return instruction
    return None


def format_session_for_save(session: dict, title: str) -> str:
    """
    Format session data as Markdown for saving to Obsidian.

    生成的格式：
    ---
    title: xxx
    source: xxx
    date: xxx
    tags: [engram, xxx]
    ---

    # 标题

    ## 总结
    ...

    ## 对话记录
    ...
    """
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    source_type = session.get("source_type", "unknown")

    # YAML frontmatter
    content = f"""---
title: "{title}"
source: "{session.get('source_url', '')}"
source_type: {source_type}
created: {date_str}
tags: [engram, {source_type}]
---

# {title}

## 来源
{session.get('source_url', 'Unknown')}

## 总结
{session.get('summary', '')}

"""

    # 添加对话记录（如果有追问）
    messages = session.get("messages", [])
    conversation = []

    for msg in messages:
        if msg["role"] == "system":
            continue  # 跳过 system prompt
        elif msg["role"] == "user":
            conversation.append(f"**Q:** {msg['content']}")
        elif msg["role"] == "assistant" and len(conversation) > 0:
            # 跳过第一条（就是总结本身）
            conversation.append(f"**A:** {msg['content']}\n")

    if len(conversation) > 1:  # 有追问对话
        content += "## 对话记录\n\n"
        content += "\n".join(conversation[1:])  # 跳过第一个总结

    return content
