# 贡献指南

感谢你为 **a-share-briefing-skill** 贡献代码！本文档说明开发流程与规范。

## 行为准则

请保持友善与专业。辱骂、歧视或人身攻击将不被容忍，相关 Issue/PR 会被关闭。

## 开发环境

### 前置要求

- Python 3.10+
- Node.js（Wind MCP Skill 依赖）
- 已安装 [Wind MCP Skill](https://aifinmarket.wind.com.cn/) 到 `~/.agents/skills/wind-mcp-skill`
- 一个有效的 Wind API Key

### 本地搭建

```bash
git clone https://github.com/Zealous1219/a-share-briefing-skill.git
cd a-share-briefing-skill

# 创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 安装开发依赖（含 lint / type check / test 工具）
pip install -e ".[dev]"

# 仅使用独立模式时，额外安装 AI 依赖
pip install -e ".[ai]"

# 准备配置
cp config.example.json config.json
# 编辑 config.json 填入 wind_api_key
```

## 代码风格

本项目使用 [ruff](https://docs.astral.sh/ruff/) 进行 lint，[mypy](https://mypy-lang.org/) 进行类型检查。配置见 `pyproject.toml`。

提交前请本地跑一遍：

```bash
ruff check .
mypy .
```

### 基本约定

- 行宽上限 120 字符。
- **禁止使用裸 `except:`**，必须捕获具体异常类型（如 `except (ValueError, TypeError):`）。
- 类型注解：所有新增公开函数应带类型注解。
- 中文注释允许，但函数/变量命名使用英文。

## 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <subject>

<body>
```

常用 type：

| type     | 用途                       |
|----------|----------------------------|
| feat     | 新功能                     |
| fix      | Bug 修复                   |
| refactor | 重构（不改变行为）         |
| docs     | 文档变更                   |
| test     | 新增/修改测试              |
| chore    | 构建、依赖、配置等杂项      |
| perf     | 性能优化                   |

示例：

```
feat(wind_client): 支持自定义 Wind skill 安装路径
fix(report_template): 修复市场广度解析在空数据时的崩溃
docs(README): 更新安装说明
```

## 提交 Pull Request

1. 从 `master` 切出新分支：`git checkout -b feat/your-feature`
2. 完成开发并补充测试（如有解析逻辑变更，必须补单元测试）
3. 确保本地通过：
   ```bash
   ruff check .
   mypy .
   pytest
   ```
4. 推送分支并创建 PR，描述：
   - 改动目的
   - 是否有破坏性变更
   - 关联的 Issue（如 `Closes #12`）

### PR 审查重点

- 是否引入裸 `except:`
- 是否硬编码了密钥或本机绝对路径
- 解析逻辑是否覆盖 Wind 返回的多种数据结构（含空数据、错误返回）
- 文档是否同步更新

## 测试约定

测试位于 `tests/`，使用 pytest。建议为以下场景补 fixture：

- Wind 返回的标准 `{"data": [{"columns":..., "rows":...}]}` 结构
- Wind 自然语言返回的纯文本结构
- 空数据 / error 返回

```bash
pytest
```

## 报告安全问题

发现安全漏洞请**勿**公开 Issue。邮件联系仓库 Owner，或使用 GitHub Security Advisory 私密上报。

## 项目结构

详见 [README.md](README.md) 的"项目结构"章节。
