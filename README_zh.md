# PuppyCLI

[English](./README.md)

---

一个基于浏览器图形界面的本地 AI 助手工具，底层使用 [openai-agents-python](https://github.com/openai/openai-agents-python) 构建。PuppyCLI 接入 DeepSeek API，完全在你的 Windows 机器上运行。

## 功能

- **浏览器界面** — 简洁极简的对话界面，支持 Markdown、LaTeX 和图片渲染
- **流式输出** — 通过 WebSocket 实时流式传输回复
- **Agent 技能** — 从 [agentskills.io](https://agentskills.io) 安装社区技能（本地路径、GitHub、URL）
- **知识库** — 本地持久化知识存储，每次对话自动检索相关内容
- **PDF 处理** — 通过 MinerU 提取 PDF 文本（本地或云端 API）
- **PowerShell** — 在对话中直接执行命令（`!Get-Date`）
- **斜杠命令** — `/help`、`/theme`、`/lang`、`/export`、`/model`、`/skill`、`/kb`、`/pdf` 等
- **会话管理** — 重命名、删除、切换对话
- **双语切换** — 中文 / 英文界面一键切换
- **深色模式** — 明暗两种主题

## 安装

需要 Python 3.10 及以上版本。

```bash
pip install git+https://github.com/Albert-Libra/PuppyCLI.git
```

## 快速开始

```bash
puppy
```

自动打开默认浏览器访问 `http://127.0.0.1:8765`。在设置面板（⚙️）中配置你的 DeepSeek API 密钥。

```bash
# 自定义端口
puppy --port 8765

# 不自动打开浏览器
puppy --no-browser
```

## 配置

所有设置保存在 `~/PuppyCLI/config.yaml`：

| 键 | 说明 | 默认值 |
|-----|------|--------|
| `api_key` | DeepSeek API 密钥 | — |
| `model` | 模型名称 | `deepseek-chat` |
| `base_url` | API 接口地址 | `https://api.deepseek.com` |
| `data_dir` | 自定义数据目录 | `~/PuppyCLI` |
| `python_env` | Python 虚拟环境路径 | — |
| `mineru_token` | MinerU 云端 API 令牌 | — |

## 数据与隐私

- 所有数据**仅存储于本地** `~/PuppyCLI/` 目录下（可通过 `data_dir` 自定义路径）
- API 密钥保存在 `~/PuppyCLI/config.yaml`（明文，仅本地）
- 对话历史以 JSONL 格式存储在 `<data_dir>/sessions/`
- 知识库存储在 `<data_dir>/knowledge/`
- **无遥测、无统计、无数据外传**（仅向你配置的 LLM 服务商发起 API 调用）

## 项目结构

```
puppycli/
├── agent/          AI agent 运行器与工具
├── server/         FastAPI REST + WebSocket
├── session/        会话持久化
├── skill/          Agent 技能管理
├── knowledge/      本地知识库
├── processing/     PDF 及文档处理
├── config.py       YAML 配置管理
├── cli.py          命令行入口
├── app.py          FastAPI 应用
└── static/         前端 (HTML/CSS/JS)
```

## 文档

启动服务后，点击顶栏 📖 或访问 `/help/`。重新构建文档：

```bash
python scripts/build_docs.py
```

## 参与贡献

欢迎提交 Issue 和 Pull Request。请保持极简设计理念。

## 许可证

MIT
