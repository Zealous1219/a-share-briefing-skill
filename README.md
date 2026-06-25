# a-share-briefing-skill

A 股收盘简报生成 Skill，支持 Agent 模式和独立运行模式。

## 依赖

- **Wind MCP Skill**：官方免费 skill，必须安装，用于获取金融数据
  - 官网：https://aifinmarket.wind.com.cn/
  - 按照官网说明安装 skill 到 `~/.agents/skills/wind-mcp-skill`
- **Python 3.10+**
- **Node.js**（Wind MCP Skill 依赖）

> 核心运行**零第三方 Python 依赖**，仅使用标准库。仅在独立模式（调用外部 LLM）时需要 `openai` 包，见下方"独立模式"。

## 安装

```bash
git clone https://github.com/Zealous1219/a-share-briefing-skill.git
cd a-share-briefing-skill
pip install -r requirements.txt
cp config.example.json config.json
# 编辑 config.json，填入 wind_api_key
```

## 使用

### Agent 模式（推荐）

Agent 运行脚本获取数据，然后自行撰写分析：

```bash
python main.py -d YYYY-MM-DD --no-ai
```

- `--no-ai` 跳过外部 AI 调用
- 报告输出到 `reports/YYYY-MM-DD_A股收盘简报.md`
- 第 11-13 章（盘面结论、主线轮动、明日关注）为占位文本，由 Agent 撰写

### 独立模式

配置外部 LLM API，脚本自动生成完整报告：

1. 安装 AI 可选依赖：

```bash
pip install -r requirements-ai.txt
```

2. 编辑 `config.json`：设置 `ai_analysis.enabled = true`，填写 `api_key` 与 `base_url`
3. 运行：

```bash
python main.py -d YYYY-MM-DD
```

支持任何 OpenAI 兼容 API（OpenAI、Azure、国内中转、Ollama 等）。

## 配置

完整模板见 [config.example.json](config.example.json)，关键字段：

```json
{
    "wind_api_key": "你的 Wind API Key",
    "wind_api_url": "https://aifinmarket.wind.com.cn/",
    "output_dir": "./reports",
    "index_codes": {
        "shanghai": "000001.SH",
        "shenzhen": "399001.SZ",
        "chuangye": "399006.SZ",
        "sh50": "000016.SH",
        "zz500": "000905.SH",
        "zz1000": "000852.SH"
    },
    "hot_concepts_top_n": 10,
    "hot_industries_top_n": 10,
    "ai_analysis": {
        "enabled": false,
        "provider": "openai",
        "api_key": "",
        "model": "gpt-4o",
        "base_url": "",
        "timeout": 60
    }
}
```

| 字段 | 说明 |
|------|------|
| `wind_api_key` | Wind API 密钥，必填 |
| `output_dir` | 报告输出目录 |
| `index_codes` | 主要指数代码（通常无需修改） |
| `hot_concepts_top_n` / `hot_industries_top_n` | 热门概念 / 行业展示数量 |
| `ai_analysis.enabled` | 是否启用独立模式（调用外部 LLM） |
| `ai_analysis.base_url` | OpenAI 兼容 API 地址，留空使用官方 OpenAI |

## 项目结构

```
.
├── main.py                      # 主入口
├── config.example.json          # 配置模板
├── requirements.txt             # 依赖
├── SKILL.md                     # Agent Skill 定义
├── data/
│   ├── wind_client.py           # Wind API 客户端
│   └── ai_analyzer.py           # 外部 LLM 调用
├── templates/
│   └── report_template.py       # 报告模板
├── utils/
│   └── helpers.py               # 工具函数
└── reports/                     # 输出目录
```

## 报告章节

| # | 章节 | 来源 |
|---|------|------|
| 一 | 大盘概况（指数 + 成交额 + 放量/缩量对比） | Wind 数据 |
| 二 | 指数涨跌幅对比（Mermaid 柱状图） | Wind 数据 |
| 三 | 市值结构（上证50/中证500/中证1000 + Mermaid 图） | Wind 数据 |
| 四 | 市场广度（涨停/跌停统计） | Wind 数据 |
| 五 | 行业表现（申万 TOP10 涨跌 + Mermaid 对比图） | Wind 数据 |
| 六 | 热门概念（TOP10） | Wind 数据 |
| 七 | 资金流向（主力净流入 + 行业 TOP5） | Wind 数据 |
| 八 | 周边市场（全球指数） | Wind 数据 |
| 九 | 期货市场（股指/国债/商品期货） | Wind 数据 |
| 十 | 财经要闻（5 条新闻） | Wind 数据 |
| 十一 | 盘面结论 | Agent / LLM |
| 十二 | 主线轮动 | Agent / LLM |
| 十三 | 明日关注 | Agent / LLM |

## Agent Skill 设置

将 `SKILL.md` 复制到对应 Agent 的 skill 目录：

| Agent | 路径 |
|-------|------|
| Trae | `.trae/skills/a-share-briefing-skill/SKILL.md` |
| Claude Code | `.claude/skills/a-share-briefing-skill/SKILL.md` |
| Codex | `.codex/skills/a-share-briefing-skill/SKILL.md` |
| OpenClaw | `~/.openclaw/workspace/skills/a-share-briefing-skill/SKILL.md` |
| Antigravity | `~/.gemini/antigravity/skills/a-share-briefing-skill/SKILL.md`（全局）或 `<workspace>/.agent/skills/a-share-briefing-skill/SKILL.md`（项目级） |
| 通用 | `~/.agents/skills/a-share-briefing-skill/SKILL.md` |

## 常见问题

**Q: 为什么市场广度里只有涨停/跌停数据？**
A: Wind 自然语言 API 不直接返回全市场涨跌家数，仅返回涨跌停个股明细。

**Q: 资金流向里行业名称为什么被截断？**
A: Wind 返回的是 GICS 分类全称，脚本自动截取最后一段简化显示。

**Q: 前日成交额对比偶尔为 0？**
A: 通过额外 API 调用获取前一交易日数据，偶尔可能因 Wind 数据延迟而失败。

## 免责声明

本工具基于 Wind 数据自动生成，AI 分析部分仅供参考，不构成任何投资建议。市场有风险，投资需谨慎。
