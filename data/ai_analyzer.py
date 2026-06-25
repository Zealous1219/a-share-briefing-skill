"""
AI 分析模块：调用大语言模型生成盘面结论、主线轮动、明日关注
支持 OpenAI 格式及兼容的第三方 API（如 Claude、国内大模型等）
"""

import json
import os
import re
from typing import Dict, Any, List, Optional

# 尝试导入 openai，未安装则给出友好提示
try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False


def load_ai_config() -> Dict[str, Any]:
    """从 config.json 读取 AI 配置"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("ai_analysis", {})


def build_market_prompt(
    date: str,
    indices: List[Dict],
    breadth: Dict,
    sectors: List[Dict],
    concepts: List[Dict],
    money_flow: Dict,
    global_indices: List[Dict],
    news: List[Dict]
) -> str:
    """构造发送给 AI 的市场数据 prompt"""

    # 指数概况
    index_lines = []
    for idx in indices:
        index_lines.append(
            f"- {idx['name']}: 收{idx['close']:.2f}, 涨跌幅{idx['pct_chg']:+.2f}%, 成交额{idx['volume']/1e8:.2f}亿"
        )
    index_text = "\n".join(index_lines)

    # 市场广度
    up = breadth.get("up_count", 0)
    down = breadth.get("down_count", 0)
    flat = breadth.get("flat_count", 0)
    limit_up = breadth.get("limit_up", 0)
    limit_down = breadth.get("limit_down", 0)
    median_pct = breadth.get("median_pct", 0)
    total_stocks = up + down + flat

    # 行业表现
    top5_sectors = sorted(sectors, key=lambda x: x.get("pct_chg", 0), reverse=True)[:5]
    bottom5_sectors = sorted(sectors, key=lambda x: x.get("pct_chg", 0))[:5]
    sector_text = "涨幅前五行业:\n" + "\n".join(
        [f"- {s['name']}: {s['pct_chg']:+.2f}%" for s in top5_sectors]
    ) + "\n\n跌幅前五行业:\n" + "\n".join(
        [f"- {s['name']}: {s['pct_chg']:+.2f}%" for s in bottom5_sectors]
    )

    # 热门概念
    top_concepts = sorted(concepts, key=lambda x: x.get("pct_chg", 0), reverse=True)[:5]
    concept_text = "\n".join([f"- {c['name']}: {c['pct_chg']:+.2f}%" for c in top_concepts])

    # 资金流向
    net_inflow = money_flow.get("net_inflow", 0)
    top_flow = sorted(money_flow.get("sector_flow", []), key=lambda x: x.get("net_inflow", 0), reverse=True)[:5]
    flow_text = f"主力资金净流入: {net_inflow/1e8:.2f}亿\n\n资金流入行业TOP5:\n" + "\n".join(
        [f"- {s['name']}: {s['net_inflow']/1e8:.2f}亿" for s in top_flow]
    )

    # 全球市场
    global_text = "\n".join([f"- {g['name']}: {g['pct_chg']:+.2f}%" for g in global_indices[:5]])

    # 财经要闻
    news_text = "\n".join([f"- {n.get('title', '')}" for n in news[:5]])

    prompt = f"""你是资深 A 股策略分析师。请根据以下 {date} 收盘数据，撰写三部分内容：

【一、盘面结论】（50-100字）
- 判断当日行情性质（如：普涨、分化、结构性行情、指数行情、缩量震荡等）
- 关键特征（大小盘分化、量能变化、情绪指标等）

【二、主线轮动】（50-100字）
- 今日最强主线是什么？驱动力？
- 资金在哪些板块间轮动？
- 前期热点是延续还是退潮？

【三、明日关注】（3条 bullet points）
- 基于今日走势和消息面，给出明日需要重点观察的信号

---

### 主要指数表现
{index_text}

### 市场广度
- 上涨家数: {up} / 下跌家数: {down} / 平盘: {flat} (共{total_stocks}只)
- 涨停: {limit_up}家 / 跌停: {limit_down}家
- 涨跌幅中位数: {median_pct:+.2f}%

### 行业表现
{sector_text}

### 热门概念 TOP5
{concept_text}

### 资金流向
{flow_text}

### 周边市场
{global_text}

### 财经要闻
{news_text}

---

请用中文输出，严格按以下格式：

**盘面结论**：<结论内容>

**主线轮动**：<主线内容>

**明日关注**：
1. <关注项1>
2. <关注项2>
3. <关注项3>
"""
    return prompt


def call_ai_api(prompt: str, config: Dict[str, Any]) -> str:
    """调用 AI API，返回原始文本"""
    if not _HAS_OPENAI:
        raise ImportError(
            "未安装 openai 包。请运行: pip install openai"
        )

    provider = config.get("provider", "openai")
    api_key = config.get("api_key", "")
    model = config.get("model", "gpt-4o")
    base_url = config.get("base_url", "")
    timeout = config.get("timeout", 60)

    if not api_key:
        raise ValueError("AI 分析已启用，但 config.json 中 ai_analysis.api_key 未配置")

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一位专业的 A 股策略分析师，擅长从数据中提取关键信号并给出简洁有力的市场判断。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=800,
        timeout=timeout,
    )

    return response.choices[0].message.content or ""


def parse_ai_response(text: str) -> Dict[str, str]:
    """从 AI 返回的文本中解析三部分内容"""
    result = {
        "conclusion": "",
        "main_line": "",
        "tomorrow_focus": ""
    }

    # 盘面结论
    conclusion_match = re.search(r'\*\*盘面结论\*\*[:：]\s*(.+?)(?=\*\*主线轮动\*\*|$)', text, re.DOTALL)
    if conclusion_match:
        result["conclusion"] = conclusion_match.group(1).strip()

    # 主线轮动
    main_line_match = re.search(r'\*\*主线轮动\*\*[:：]\s*(.+?)(?=\*\*明日关注\*\*|$)', text, re.DOTALL)
    if main_line_match:
        result["main_line"] = main_line_match.group(1).strip()

    # 明日关注
    tomorrow_match = re.search(r'\*\*明日关注\*\*[:：]\s*(.+?)$', text, re.DOTALL)
    if tomorrow_match:
        result["tomorrow_focus"] = tomorrow_match.group(1).strip()

    return result


def generate_ai_analysis(
    date: str,
    indices: List[Dict],
    breadth: Dict,
    sectors: List[Dict],
    concepts: List[Dict],
    money_flow: Dict,
    global_indices: List[Dict],
    news: List[Dict]
) -> Dict[str, str]:
    """
    主入口：调用 AI 生成盘面结论、主线轮动、明日关注
    如果未配置 AI 或调用失败，回退到规则判断
    """
    ai_config = load_ai_config()
    if not ai_config.get("enabled", False):
        return _fallback_analysis(indices, breadth, sectors, money_flow)

    try:
        prompt = build_market_prompt(date, indices, breadth, sectors, concepts, money_flow, global_indices, news)
        raw_text = call_ai_api(prompt, ai_config)
        parsed = parse_ai_response(raw_text)

        # 如果解析失败，使用回退
        if not parsed["conclusion"]:
            return _fallback_analysis(indices, breadth, sectors, money_flow)
        return parsed

    except Exception as e:
        print(f"[AI 分析调用失败: {e}]，使用规则回退...")
        return _fallback_analysis(indices, breadth, sectors, money_flow)


def _fallback_analysis(indices: List[Dict], breadth: Dict, sectors: List[Dict], money_flow: Dict) -> Dict[str, str]:
    """规则回退：当 AI 未启用或调用失败时使用"""
    up_count = breadth.get("up_count", 0)
    down_count = breadth.get("down_count", 0)
    median_pct = breadth.get("median_pct", 0)
    net_inflow = money_flow.get("net_inflow", 0)
    top_sectors = sorted(sectors, key=lambda x: x.get("pct_chg", 0), reverse=True)[:3]

    if down_count > up_count * 2:
        conclusion = "⚠️ **典型'指数行情'** — 指数上涨但个股普跌，市场分化明显。"
    elif up_count > down_count * 2:
        conclusion = "✅ **普涨行情** — 市场情绪高涨，赚钱效应明显。"
    else:
        conclusion = "📊 **震荡分化行情** — 指数震荡，板块轮动加速。"

    main_line = ""
    if top_sectors:
        main_line = "今日市场主线集中在：" + "、".join([s.get("name", "") for s in top_sectors])

    tomorrow_focus = ""
    if net_inflow > 100:
        tomorrow_focus += "1. 关注资金流入主线能否持续；\n"
    else:
        tomorrow_focus += "1. 关注量能是否跟进；\n"
    tomorrow_focus += "2. 观察强势板块是否出现分化；\n"
    tomorrow_focus += "3. 留意外围市场波动对A股的影响。"

    return {
        "conclusion": conclusion,
        "main_line": main_line,
        "tomorrow_focus": tomorrow_focus
    }
