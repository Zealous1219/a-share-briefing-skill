---
name: "a-share-briefing-skill"
description: "Agent-agnostic skill for generating A-share market closing briefings. Fetches Wind data via CLI, then the Agent itself writes the qualitative analysis. No external LLM API required."
---

# A 股收盘简报 Skill

一个跨 Agent 通用的 A 股收盘简报生成 Skill。

**核心理念**：AI Agent 自身就是分析引擎。脚本只负责获取数据，盘面结论、主线轮动、明日关注由 Agent 直接撰写。

## When to Invoke

- 用户要求"收盘简报"、"今日大盘"、"A股行情总结"
- 用户要求复盘当日 A 股市场
- 用户要求生成指定日期的收盘报告

## Prerequisites

1. **Wind MCP Skill** 已安装（全局路径 `~/.agents/skills/wind-mcp-skill`）
2. **Python 3.10+**
3. **Node.js**（Wind MCP Skill 依赖）
4. **Wind API Key**（填入 `config.json`）

## Quick Start for Agent

> **前置条件**（任何 Agent 平台通用）：① 项目代码已 `git clone` 到本地；② Wind MCP Skill 已安装到 `~/.agents/skills/wind-mcp-skill`；③ `config.json` 已填入 `wind_api_key`。SKILL.md 仅是使用说明，Agent 需上述环境就绪后才能运行 `python main.py`。

Agent 收到"生成收盘简报"指令后，执行以下两步：

### Step 1: Fetch Data

```bash
cd <project-path>
python main.py -d YYYY-MM-DD --no-ai   # WSL/Linux 用 python3
```

- `--no-ai` 跳过外部 AI 调用（Agent 自身就是 AI）
- 报告输出到 `reports/YYYY-MM-DD_A股收盘简报.md`
- 此时第 11-13 章节（盘面结论、主线轮动、明日关注）为占位文本

### Step 2: Agent Writes Analysis

Agent 读取报告，根据数据撰写三个章节：

1. **盘面结论**：判断行情性质（普涨/分化/结构性行情），指出关键特征和核心矛盾
2. **主线轮动**：识别当日最强主线及驱动力，分析风格切换信号
3. **明日关注**：基于今日走势、消息面、外围环境，给出 3-5 条观察要点

Agent 用撰写的内容替换报告中的占位文本，保存文件即可。

## Data Sections for Analysis

Agent 撰写分析时应重点参考以下数据：

| 章节 | 分析要点 |
|------|---------|
| 大盘概况 | 指数涨跌、成交额、放量/缩量、涨跌点 |
| 市值结构 | 上证50 vs 中证500/1000，大小盘风格 |
| 市场广度 | 涨停/跌停家数，多空力量对比 |
| 行业表现 | 领涨/领跌板块，行业分化程度 |
| 热门概念 | 最强主题概念及涨幅 |
| 资金流向 | 主力资金方向，行业净流入 |
| 期货市场 | 股指期货升贴水，商品期货异动 |
| 周边市场 | 外围环境，全球情绪 |
| 财经要闻 | 消息面驱动因素 |

## Installation (for End Users)

```bash
git clone https://github.com/Zealous1219/a-share-briefing-skill.git
cd a-share-briefing-skill
pip install -r requirements.txt
cp config.example.json config.json
# 编辑 config.json，填入 wind_api_key
```

## Agent Skill Setup

### Trae

Copy `SKILL.md` to `.trae/skills/a-share-briefing-skill/SKILL.md`.

### Claude Code

Copy `SKILL.md` to `.claude/skills/a-share-briefing-skill/SKILL.md`.

### Codex
Copy `SKILL.md` to `.codex/skills/a-share-briefing-skill/SKILL.md`.

### OpenClaw
Copy `SKILL.md` to `~/.openclaw/workspace/skills/a-share-briefing-skill/SKILL.md`.

### Antigravity
Copy `SKILL.md` to `~/.gemini/antigravity/skills/a-share-briefing-skill/SKILL.md`（全局）或 `<workspace>/.agent/skills/a-share-briefing-skill/SKILL.md`（项目级）.

### Generic
Copy `SKILL.md` to `~/.agents/skills/a-share-briefing-skill/SKILL.md`.

## Standalone Mode (Optional)

如果不想通过 Agent 使用，也可以配置外部 LLM API 让脚本自动生成分析：

1. 编辑 `config.json`，设置 `ai_analysis.enabled = true` 并填写 `api_key`
2. 安装 AI 依赖：`pip install -r requirements-ai.txt`
3. 运行：`python main.py -d YYYY-MM-DD`

支持任何 OpenAI 兼容 API（OpenAI、Azure、国内中转、Ollama 等）。

## Output

报告保存到 `reports/YYYY-MM-DD_A股收盘简报.md`，包含 13 个章节：

1. 大盘概况（指数 + 成交额 + 放量/缩量对比）
2. 指数涨跌幅对比（Mermaid 柱状图）
3. 市值结构（上证50/中证500/中证1000 + Mermaid 图）
4. 市场广度（涨停/跌停统计）
5. 行业表现（申万 TOP10 涨跌 + Mermaid 对比图）
6. 热门概念（TOP10）
7. 资金流向（主力净流入 + 行业 TOP5）
8. 周边市场（全球指数）
9. 期货市场（股指/国债/商品期货）
10. 财经要闻（5 条新闻）
11. 盘面结论（Agent 撰写）
12. 主线轮动（Agent 撰写）
13. 明日关注（Agent 撰写）

## Architecture

```
.
├── main.py                      # 主入口
├── config.example.json          # 配置模板
├── requirements.txt             # 依赖
├── SKILL.md                     # 本文件（Agent Skill 定义）
├── README.md                    # 用户文档
├── data/
│   ├── wind_client.py           # Wind API 客户端
│   └── ai_analyzer.py           # 外部 LLM 调用（独立模式用）
├── templates/
│   └── report_template.py       # 报告模板引擎
├── utils/
│   └── helpers.py               # 工具函数
└── reports/                     # 输出目录
```

## Notes

- Wind 自然语言 API 不直接返回全市场涨跌家数，仅返回涨停/跌停个股明细
- 资金流向行业名称使用 GICS 分类，脚本自动截取最后一段简化
- 前日成交额对比通过额外 API 调用获取，偶尔可能因数据延迟失败
- 项目内无硬编码路径，可移植到任何支持 Python + Node.js 的环境
