# PuppyCLI

[English](./README.md)

---

一个基于浏览器图形界面的本地 AI 助手工具，底层使用 [openai-agents-python](https://github.com/openai/openai-agents-python) 构建。PuppyCLI 可接入任意 OpenAI 兼容 API（默认使用 DeepSeek），完全在你的 Windows 机器上运行。

## 功能

- **浏览器界面** — 简洁极简的对话界面，支持 Markdown、LaTeX（KaTeX）、代码高亮和图片渲染
- **流式输出** — 通过 WebSocket 实时流式传输回复
- **Agent 技能** — 从 [agentskills.io](https://agentskills.io) 安装社区技能（本地路径、GitHub 仓库或 URL）；自动将面向 CLI 的技能适配为浏览器前端
- **知识库** — 本地持久化知识存储，支持关键词加权搜索评分；每次对话自动检索并注入相关内容
- **PDF 处理** — 通过 MinerU 提取 PDF 文本（免费本地模式，或使用 token 的云端 API）
- **网页搜索** — 通过本地 MCP 服务器或 DuckDuckGo 后备方案搜索互联网（免费，无需配置）
- **网页抓取** — 从任意 URL 提取可读文本内容
- **PowerShell** — 在对话中直接执行命令（`!Get-Date`）；危险的文件修改命令需要用户确认
- **斜杠命令** — `/help`、`/theme`、`/lang`、`/export`、`/model`、`/skill`、`/kb`、`/pdf` 等
- **会话管理** — 创建、重命名、删除、切换对话；自动生成对话摘要
- **双语切换** — 中文 / 英文界面一键切换
- **深色模式** — 明暗两种主题

## 安装

需要 Python 3.10 及以上版本。

```bash
pip install --no-cache-dir git+https://github.com/Albert-Libra/PuppyCLI.git
```

## 快速开始

```bash
puppy
```

自动打开默认浏览器访问 `http://127.0.0.1:8765`。首次运行时，交互式设置向导会引导你完成配置。

```bash
puppy --port 8080        # 自定义端口
puppy --host 0.0.0.0     # 绑定到所有网络接口
puppy --no-browser       # 不自动打开浏览器
puppy --setup            # 重新运行配置向导
puppy --update           # 从 GitHub 更新到最新版本
puppy --uninstall        # 卸载 PuppyCLI（可选择是否删除所有数据）
```

## 配置

所有设置保存在 `~/PuppyCLI/config.yaml`：

| 键 | 说明 | 默认值 |
|-----|------|--------|
| `api_key` | API 密钥（DeepSeek 或其他 OpenAI 兼容服务商） | — |
| `model` | 模型名称 | `deepseek-chat` |
| `base_url` | API 接口地址 | `https://api.deepseek.com` |
| `theme` | 界面主题（`light` 或 `dark`） | `light` |
| `data_dir` | 自定义数据目录 | `~/PuppyCLI` |
| `python_env` | Python 虚拟环境路径（用于代码执行） | — |
| `mineru_token` | MinerU 云端 API 令牌（可选；本地模式无需令牌） | — |

API 密钥、模型、接口地址、主题、Python 环境路径和数据目录也可以在网页界面的设置面板（⚙️）中修改。

## 数据与隐私

- 所有数据**仅存储于本地** `~/PuppyCLI/` 目录下（可通过 `data_dir` 自定义路径）
- API 密钥保存在 `~/PuppyCLI/config.yaml`（明文，仅本地）
- 对话历史以 JSONL 格式存储在 `<data_dir>/sessions/`
- 知识库存储在 `<data_dir>/knowledge/`
- 已安装技能存储在 `<data_dir>/skills/`
- **无遥测、无统计、无数据外传**（仅向你配置的 LLM 服务商以及你选择启用的可选服务发起调用：MinerU 云端、MCP 服务器、DuckDuckGo）

## 项目结构

```
puppycli/
├── agent/          AI agent 运行器与内置工具（PowerShell、网页搜索、网页抓取、知识库搜索、PDF）
├── server/         FastAPI REST API 与 WebSocket 处理
├── session/        会话持久化（JSONL + 元数据索引）
├── skill/          Agent 技能管理（安装、适配、还原）与注册表搜索
├── knowledge/      本地知识库（JSONL，关键词加权搜索）
├── processing/     PDF 处理（MinerU 本地或云端）
├── providers/      MCP Streamable HTTP 客户端（外部工具服务器）
├── config.py       YAML 配置管理
├── cli.py          命令行入口（`puppy` 命令）
├── app.py          FastAPI 应用工厂
├── update.py       更新检查器（24 小时缓存，GitHub 版本对比）
└── static/         前端（HTML/CSS/JS — 单页应用）
```

## 文档

启动服务后，点击顶栏 📖 图标或访问 `/help/`。重新构建 API 文档：

```bash
python scripts/build_docs.py
```

## 参与贡献

欢迎提交 Issue 和 Pull Request。请保持极简设计理念。

## 许可证

MIT
