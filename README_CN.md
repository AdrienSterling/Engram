# Engram

> AI 驱动的知识捕获与内化系统
>
> 让知识在大脑中留下真正的痕迹

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

[English](README.md) | [中文](README_CN.md)

## 什么是 Engram？

**Engram**（记忆痕迹）：神经科学术语，指大脑中存储记忆的物理变化。

Engram 是一个个人知识助手，帮助你：
- **捕获**：从 YouTube、文章、PDF、图片中提取内容
- **归档**：将信息分配到项目（做事）或知识领域（学习）
- **内化**：通过输出承诺确保真正学会，而非单纯收藏
- **输出**：输出到个人网站或其他平台

## 核心理念

> "收藏不等于学会。没有输出的知识不是知识。"

基于认知科学原理：
- **两条路径**：「做」（项目驱动）vs「懂」（学习驱动）
- **输出承诺**：每个知识领域都需要承诺产出点什么
- **7 天过期**：未归档的内容自动过期，避免数字囤积
- **主动回顾**：追踪消化状态，确保真正内化

## 功能特性

- **多源提取**：YouTube（字幕+Whisper转录）、网页文章、微信公众号
- **智能归档**：将内容分配到项目或知识领域
- **多轮对话**：对总结内容进行追问，深入理解
- **会话保存**：保存对话记录到 Obsidian
- **多模型支持**：OpenAI、DeepSeek、Groq（Whisper）
- **多存储后端**：Obsidian (Git)、Notion、Google Docs（计划中）
- **多平台**：Telegram（已实现）、Discord、CLI（计划中）

## 使用方式

### Telegram Bot 命令

| 命令 | 功能 |
|------|------|
| `/start` | 开始使用，查看帮助 |
| `/help` | 显示详细帮助 |
| `/save` | 保存当前对话到 Obsidian |
| `/save 标题` | 指定标题保存 |
| `/clear` | 清除当前会话 |
| `/status` | 查看当前会话状态 |

### 典型工作流

```
1. 发送 YouTube/文章链接 → 获取 AI 总结
2. 直接发文字追问 → "详细说说第3点"
3. 继续追问 → "有什么实际应用？"
4. 满意后 /save → 保存笔记到 Obsidian
```

### 会话上下文管理

Engram 会自动保存每次对话的上下文：
- **原始内容**：用于追问时引用原文细节
- **对话历史**：支持多轮问答
- **自动清理**：发送新链接自动开始新会话

技术实现：使用 `context.user_data` 存储用户会话状态，详见 [handlers.py](src/engram/platforms/telegram/handlers.py) 中的注释。

## 快速开始

### 前置要求

- Python 3.10+
- Telegram Bot Token（从 [@BotFather](https://t.me/BotFather) 获取）
- OpenAI API Key（或其他 LLM 提供商）

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourname/engram.git
cd engram

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的配置
```

### 运行

```bash
# 运行 Bot
python -m engram.platforms.telegram.bot
```

### Docker 部署

```bash
# 使用 Docker Compose 构建并运行
docker compose up -d
```

## 架构

```
src/engram/
├── core/           # 核心类型和配置
├── llm/            # LLM 抽象层
├── extractors/     # 内容提取器
├── agents/         # 业务逻辑 Agent
├── storage/        # 存储后端
└── platforms/      # 平台适配器（Telegram 等）
```

## 配置说明

查看 [.env.example](.env.example) 了解所有配置选项。

关键配置：
- `TELEGRAM_TOKEN`：Telegram Bot Token（必需）
- `VAULT_PATH`：Obsidian vault 路径（必需）
- `DEFAULT_LLM`：默认 LLM 提供商 (`openai` / `deepseek`)
- `OPENAI_API_KEY`：OpenAI API Key
- `DEEPSEEK_API_KEY`：DeepSeek API Key（推荐，更便宜）
- `GROQ_API_KEY`：Groq API Key（用于 Whisper 音频转录）

### YouTube 视频转录

对于没有字幕的 YouTube 视频，Engram 使用 Groq Whisper API 进行音频转录：
- 免费额度：约 30 小时/月
- 成本：$0.04/小时（vs OpenAI $0.36/小时）
- 配置：设置 `GROQ_API_KEY` 环境变量即可启用

## 文档

- [架构设计](docs/zh/架构设计.md)
- [配置说明](docs/zh/配置说明.md)
- [部署指南](docs/zh/部署指南.md)
- [存储后端](docs/zh/存储后端.md)

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

MIT License - 查看 [LICENSE](LICENSE) 了解详情。

## 致谢

- 灵感来源于 [Tiago Forte 的 PARA 方法](https://fortelabs.com/blog/para/)
- 基于 [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 构建
