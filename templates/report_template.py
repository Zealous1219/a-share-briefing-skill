from datetime import datetime
from typing import Dict, Any, List
from utils.helpers import format_date, format_price, format_pct, format_number, color_pct


def parse_wind_data(data: Dict) -> Dict:
    if isinstance(data, list):
        all_rows = []
        all_columns = []
        for item in data:
            if isinstance(item, dict):
                if "rows" in item and "columns" in item:
                    rows = item["rows"]
                    columns = item["columns"]
                    col_names = [col.get("name", f"col_{i}") for i, col in enumerate(columns)]
                    for row in rows:
                        if isinstance(row, list):
                            row_dict = {}
                            for i, val in enumerate(row):
                                if i < len(col_names):
                                    row_dict[col_names[i]] = val
                            all_rows.append(row_dict)
                    all_columns.extend(columns)
                elif "text" in item:
                    return {"text": item["text"]}
        if all_rows:
            return {"rows": all_rows, "columns": all_columns}
        return {"raw": str(data)}
    
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], dict):
            data = data["data"]
        if "data" in data and isinstance(data["data"], list):
            inner = data["data"]
            # 处理 {"data": [{"columns": ..., "rows": ...}]} 嵌套结构
            if inner and isinstance(inner[0], dict) and "columns" in inner[0] and "rows" in inner[0]:
                all_rows = []
                all_columns = []
                for item in inner:
                    rows = item.get("rows", [])
                    columns = item.get("columns", [])
                    col_names = [col.get("name", f"col_{i}") for i, col in enumerate(columns)]
                    for row in rows:
                        if isinstance(row, list):
                            row_dict = {}
                            for i, val in enumerate(row):
                                if i < len(col_names):
                                    row_dict[col_names[i]] = val
                            all_rows.append(row_dict)
                    all_columns.extend(columns)
                if all_rows:
                    return {"rows": all_rows, "columns": all_columns}
                return {"raw": data}
            # 处理 {"data": [[...]], "columns": [...]} 平铺结构
            rows = data["data"]
            columns = data.get("columns", [])
            if columns and rows:
                col_names = [col.get("name", f"col_{i}") for i, col in enumerate(columns)]
                result = []
                for row in rows:
                    if isinstance(row, list):
                        item = {}
                        for i, val in enumerate(row):
                            if i < len(col_names):
                                item[col_names[i]] = val
                        result.append(item)
                return {"rows": result, "columns": columns}
            return {"raw": data}
        if "text" in data:
            return {"text": data["text"]}
        if "rows" in data and "columns" in data:
            rows = data["rows"]
            columns = data["columns"]
            col_names = [col.get("name", f"col_{i}") for i, col in enumerate(columns)]
            result = []
            for row in rows:
                if isinstance(row, list):
                    item = {}
                    for i, val in enumerate(row):
                        if i < len(col_names):
                            item[col_names[i]] = val
                    result.append(item)
            return {"rows": result, "columns": columns}
    return {"raw": str(data)}


def parse_index_data(index_data: List[Dict]) -> List[Dict]:
    parsed = []
    for idx in index_data:
        if isinstance(idx, dict) and "error" not in idx:
            parsed.append({
                "code": idx.get("code", ""),
                "name": idx.get("name", idx.get("中文简称", "")),
                "close": float(idx.get("最新成交价", 0) or 0),
                "pct_chg": float(idx.get("涨跌幅", 0) or 0),
                "volume": float(idx.get("成交额", 0) or 0),
                "open": float(idx.get("今日开盘价", 0) or 0),
                "high": float(idx.get("今日最高价", 0) or 0),
                "low": float(idx.get("今日最低价", 0) or 0),
                "prev_close": float(idx.get("前收盘价", 0) or 0)
            })
    return parsed


def parse_market_breadth(breadth_data, news_text: str = "") -> Dict:
    result = {"up_count": 0, "down_count": 0, "flat_count": 0, "limit_up": 0, "limit_down": 0, "median_pct": 0, "raw_text": str(breadth_data)}

    items = []
    if isinstance(breadth_data, list):
        items = breadth_data
    elif isinstance(breadth_data, dict) and "data" in breadth_data:
        items = breadth_data["data"] if isinstance(breadth_data["data"], list) else [breadth_data["data"]]

    # Wind 返回混合数据：聚合数字块（单行单列）+ 个股明细块（多行多列）
    # 优先提取聚合数字，跳过个股明细
    for item in items:
        if not isinstance(item, dict) or "rows" not in item or "columns" not in item:
            continue
        cols = item["columns"]
        rows = item["rows"]
        col_names = [col.get("name", "") for col in cols]

        # 聚合数字块：只有1列、1行，列名包含关键词
        if len(cols) == 1 and len(rows) == 1:
            col_name = col_names[0]
            try:
                val = int(float(rows[0][0]))
            except (ValueError, TypeError, IndexError):
                continue
            if "上涨家数" in col_name or "上涨只数" in col_name:
                result["up_count"] = val
            elif "下跌家数" in col_name or "下跌只数" in col_name:
                result["down_count"] = val
            elif "平盘家数" in col_name or "平盘只数" in col_name:
                result["flat_count"] = val
            elif "涨停家数" in col_name or "涨停只数" in col_name:
                result["limit_up"] = val
            elif "跌停家数" in col_name or "跌停只数" in col_name:
                result["limit_down"] = val
            continue

        # 个股明细块：跳过（聚合数字已获取）
        # 如果没有聚合数字，回退到从明细统计
        if result["up_count"] == 0 and result["down_count"] == 0:
            pct_idx = -1
            limit_idx = -1
            for i, name in enumerate(col_names):
                if "涨跌幅" in name and "排名" not in name:
                    pct_idx = i
                if "涨跌停状态" in name:
                    limit_idx = i
            for row in rows:
                if pct_idx >= 0 and pct_idx < len(row):
                    try:
                        pct = float(row[pct_idx])
                        if pct > 0.001:
                            result["up_count"] += 1
                        elif pct < -0.001:
                            result["down_count"] += 1
                        else:
                            result["flat_count"] += 1
                    except (ValueError, TypeError, IndexError):
                        pass
                if limit_idx >= 0 and limit_idx < len(row):
                    try:
                        limit_status = str(row[limit_idx]).strip()
                        if limit_status == "1":
                            result["limit_up"] += 1
                        elif limit_status == "-1":
                            result["limit_down"] += 1
                    except (IndexError, TypeError, ValueError):
                        pass

    # 如果聚合数字中 up+down < 1000，说明 Wind 返回的不是全市场数据
    # 尝试从新闻文本中提取全市场涨跌家数
    total = result["up_count"] + result["down_count"] + result["flat_count"]
    if total < 1000 and news_text:
        _extract_breadth_from_news(result, news_text)

    return result


def _extract_breadth_from_news(result: Dict, text: str):
    """从新闻文本中提取全市场涨跌家数"""
    import re
    # 匹配 "超4100家个股下跌" / "1100余家上涨" / "4200只下跌" 等
    up_patterns = [
        r'(\d{3,5})\s*(?:余|多|超)?\s*(?:家|只)\s*(?:个股\s*)?上涨',
        r'上涨\s*(?:个股\s*)?(?:超过|超)?\s*(\d{3,5})',
        r'上涨\s*(\d{3,5})\s*(?:家|只)',
    ]
    down_patterns = [
        r'(\d{3,5})\s*(?:余|多|超)?\s*(?:家|只)\s*(?:个股\s*)?下跌',
        r'下跌\s*(?:个股\s*)?(?:超过|超)?\s*(\d{3,5})',
        r'下跌\s*(\d{3,5})\s*(?:家|只)',
    ]
    for pat in up_patterns:
        m = re.search(pat, text)
        if m:
            result["up_count"] = int(m.group(1))
            break
    for pat in down_patterns:
        m = re.search(pat, text)
        if m:
            result["down_count"] = int(m.group(1))
            break


def parse_sectors(sector_data: Dict) -> List[Dict]:
    parsed = parse_wind_data(sector_data)
    
    if "rows" in parsed:
        sectors = []
        for row in parsed["rows"]:
            name = ""
            pct = 0
            for key, val in row.items():
                if "简称" in key or "name" in key.lower():
                    name = str(val)
                elif ("涨跌幅" in key or "pct" in key.lower() or "change" in key.lower()) and "排名" not in key:
                    pct = float(val) if isinstance(val, (int, float)) else 0
            if name:
                sectors.append({"name": name, "pct_chg": pct})
        return sorted(sectors, key=lambda x: x["pct_chg"], reverse=True)
    elif "text" in parsed:
        return _parse_sectors_from_text(parsed["text"])
    return []


def _parse_sectors_from_text(text: str) -> List[Dict]:
    lines = text.split("\n")
    sectors = []
    for line in lines:
        line = line.strip()
        if line and "%" in line:
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                pct_str = parts[-1].replace("%", "")
                try:
                    pct = float(pct_str)
                    sectors.append({"name": name, "pct_chg": pct})
                except ValueError:
                    pass
    return sectors


def parse_concepts(concept_data: Dict) -> List[Dict]:
    parsed = parse_wind_data(concept_data)
    
    if "rows" in parsed:
        concepts = []
        for row in parsed["rows"]:
            name = ""
            pct = 0
            for key, val in row.items():
                if "简称" in key or "name" in key.lower():
                    name = str(val)
                elif ("涨跌幅" in key or "pct" in key.lower()) and "排名" not in key:
                    pct = float(val) if isinstance(val, (int, float)) else 0
            if name:
                concepts.append({"name": name, "pct_chg": pct})
        return sorted(concepts, key=lambda x: x["pct_chg"], reverse=True)[:10]
    elif "text" in parsed:
        return _parse_concepts_from_text(parsed["text"])
    return []


def _parse_concepts_from_text(text: str) -> List[Dict]:
    lines = text.split("\n")
    concepts = []
    for line in lines:
        line = line.strip()
        if line and "%" in line:
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                pct_str = parts[-1].replace("%", "")
                try:
                    pct = float(pct_str)
                    concepts.append({"name": name, "pct_chg": pct})
                except ValueError:
                    pass
    return concepts[:10]


def parse_money_flow(money_flow_data: Dict) -> Dict:
    parsed = parse_wind_data(money_flow_data)

    # Wind 返回的数值单位为"元"，无需转换
    result = {"net_inflow": 0, "sector_flow": [], "raw_text": str(money_flow_data), "parsed_success": False}

    if "rows" in parsed:
        total_inflow = 0
        found_any = False
        for row in parsed["rows"]:
            for key, val in row.items():
                if "净流入" in key or "inflow" in key.lower():
                    if isinstance(val, (int, float)):
                        total_inflow += val
                        found_any = True
                        sector_name = ""
                        for k, v in row.items():
                            if "行业" in k or "板块" in k:
                                sector_name = str(v)
                                break
                        if sector_name:
                            result["sector_flow"].append({"name": sector_name, "net_inflow": val})
        result["net_inflow"] = total_inflow
        result["parsed_success"] = found_any
    elif "text" in parsed:
        import re
        inflow_match = re.search(r'净流入\s*([\d.]+)\s*(亿?)', parsed["text"])
        if inflow_match:
            val = float(inflow_match.group(1))
            if inflow_match.group(2) == "亿":
                val *= 100_000_000  # 亿 -> 元
            result["net_inflow"] = val
            result["parsed_success"] = True

    return result


def parse_global_indices(global_data: Dict) -> List[Dict]:
    parsed = parse_wind_data(global_data)
    
    if "rows" in parsed:
        indices = []
        for row in parsed["rows"]:
            name = ""
            pct = 0
            for key, val in row.items():
                if "简称" in key or "名称" in key or "name" in key.lower():
                    name = str(val)
                elif ("涨跌幅" in key or "pct" in key.lower()) and "排名" not in key:
                    pct = float(val) if isinstance(val, (int, float)) else 0
            if name:
                indices.append({"name": name, "pct_chg": pct})
        return indices
    elif "text" in parsed:
        return _parse_global_from_text(parsed["text"])
    return []


def _parse_global_from_text(text: str) -> List[Dict]:
    import re
    lines = text.split("\n")
    indices = []
    index_names = ["道琼斯", "纳斯达克", "标普500", "日经225", "恒生指数", "上证指数", "深证成指"]
    
    for line in lines:
        line = line.strip()
        if line and "%" in line:
            for name in index_names:
                if name in line:
                    pct_match = re.search(r'([+-]?\d+\.?\d*)\%', line)
                    if pct_match:
                        indices.append({"name": name, "pct_chg": float(pct_match.group(1))})
                    break
    return indices


def parse_news(news_data: Dict) -> List[Dict]:
    if isinstance(news_data, dict) and "items" in news_data:
        news = []
        for item in news_data["items"]:
            if isinstance(item, dict):
                title = item.get("title", "")
                if title and len(title) > 5:
                    news.append({"title": title, "content": item.get("content", "")})
        return news[:5]
    
    parsed = parse_wind_data(news_data)
    
    if "rows" in parsed:
        news = []
        for row in parsed["rows"]:
            title = ""
            for key, val in row.items():
                if "标题" in key or "title" in key.lower():
                    title = str(val)
                    break
            if title and len(title) > 10:
                news.append({"title": title})
        return news[:5]
    elif "text" in parsed:
        lines = parsed["text"].split("\n")
        news = []
        for line in lines:
            line = line.strip()
            if line and len(line) > 10:
                news.append({"title": line})
        return news[:5]
    return []


def generate_report(data: Dict[str, Any], date_str: str, ai_result: Dict[str, str] = None) -> str:
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    week_day_map = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
    week_day = week_day_map.get(date_obj.weekday(), "")
    
    parsed_indices = parse_index_data(data.get("main_indices", []))
    parsed_breadth = parse_market_breadth(data.get("market_breadth", {}))
    parsed_sectors = parse_sectors(data.get("sector_performance", {}))
    parsed_concepts = parse_concepts(data.get("hot_concepts", {}))
    parsed_money_flow = parse_money_flow(data.get("money_flow", {}))
    parsed_global = parse_global_indices(data.get("global_indices", {}))
    parsed_news = parse_news(data.get("news", {}))
    prev_day_volume = data.get("prev_day_volume", 0)
    futures_data = data.get("futures", {})

    if ai_result is None:
        ai_result = {"conclusion": "", "main_line": "", "tomorrow_focus": ""}

    report = f"""# 📊 A股收盘简报 | {date_str} {week_day}

---

"""

    report += render_market_overview(parsed_indices, date_str, prev_day_volume)
    report += render_index_chart(parsed_indices)
    report += render_market_cap_structure(parsed_indices)
    report += render_market_breadth(parsed_breadth)
    report += render_sector_performance(parsed_sectors)
    report += render_hot_concepts(parsed_concepts)
    report += render_money_flow(parsed_money_flow)
    report += render_global_markets(parsed_global)
    report += render_futures(futures_data)
    report += render_financial_news(parsed_news)
    report += render_ai_analysis(ai_result)
    report += render_footer(date_str)

    return report


def render_footer(date_str: str = "") -> str:
    from datetime import datetime
    gen_time = datetime.now().strftime("%Y年%m月%d日")
    return f"""

---

## 📌 数据来源与免责声明

- **数据来源**：万得 Wind 金融数据服务
- **数据日期**：{date_str} 收盘
- **生成时间**：{gen_time}
- **免责声明**：本简报基于 Wind 数据自动生成，AI 分析部分（如有）仅供参考，不构成任何投资建议。市场有风险，投资需谨慎。
"""


def render_market_overview(indices: List[Dict], date_str: str, prev_day_volume: float = 0) -> str:
    index_rows = ""
    total_volume = 0
    for idx in indices:
        close = idx['close']
        prev_close = idx.get('prev_close', 0)
        chg = close - prev_close if prev_close else 0
        open_p = idx.get('open', 0)
        high = idx.get('high', 0)
        low = idx.get('low', 0)
        index_rows += f"| {idx['name']} | {format_price(close)} | {color_pct(idx['pct_chg'])} | {chg:+.2f} | {format_number(idx['volume'])} | {format_price(prev_close)} | {format_price(open_p)} | {format_price(high)} | {format_price(low)} |\n"
        # 沪深合计只加上证指数+深证成指，其余指数是子集，加入会重复计算
        if idx['code'] in ('000001.SH', '399001.SZ'):
            total_volume += idx['volume']

    # 放量/缩量对比
    volume_comment = ""
    if prev_day_volume > 0:
        diff = total_volume - prev_day_volume
        diff_pct = (diff / prev_day_volume) * 100
        if diff > 0:
            volume_comment = f"- **较前日放量** {format_number(abs(diff))}（+{diff_pct:.1f}%）"
        else:
            volume_comment = f"- **较前日缩量** {format_number(abs(diff))}（{diff_pct:.1f}%）"

    return f"""## 📈 一、大盘概况

{format_date(date_str)} 是 A 股交易日，收盘数据已可用。

### 主要指数表现

| 指数 | 收盘价 | 涨跌幅 | 涨跌点 | 成交额(亿) | 前收盘 | 开盘 | 最高 | 最低 |
|------|--------|--------|--------|-----------|--------|------|------|------|
{index_rows if index_rows else "| - | - | - | - | - | - | - | - | - |\n"}

### 市场整体成交

- **沪深合计成交额**: **{format_number(total_volume)}**
{volume_comment if volume_comment else ""}

---

"""


def render_index_chart(indices: List[Dict]) -> str:
    if not indices:
        return ""
    
    names = [idx["name"] for idx in indices]
    pcts = [idx["pct_chg"] for idx in indices]

    names_str = ", ".join([f'"{n}"' for n in names])
    pcts_str = ", ".join([str(p) for p in pcts])

    return f"""## 📊 二、指数涨跌幅对比

```mermaid
xychart-beta
    title "主要指数涨跌幅 (%)"
    x-axis [{names_str}]
    y-axis "涨跌幅" -5 --> 5
    bar [{pcts_str}]
```

---

"""


def render_market_cap_structure(indices: List[Dict]) -> str:
    """市值结构分析：大小盘涨跌幅对比"""
    # 从 indices 中提取市值代表指数
    cap_map = {
        "上证50": "超大盘",
        "沪深300": "大盘",
        "中证500": "中盘",
        "中证1000": "小盘",
    }
    cap_indices = []
    for idx in indices:
        name = idx.get("name", "")
        if name in cap_map:
            cap_indices.append({
                "name": name,
                "pct_chg": idx.get("pct_chg", 0),
                "label": cap_map[name]
            })

    if len(cap_indices) < 2:
        return ""

    # 表格
    cap_rows = ""
    for c in cap_indices:
        cap_rows += f"| {c['name']} | {color_pct(c['pct_chg'])} | {c['label']} |\n"

    # Mermaid 柱状图
    names_str = ", ".join([f'"{c["name"]}"' for c in cap_indices])
    pcts_str = ", ".join([str(c["pct_chg"]) for c in cap_indices])

    # 规则回退评论
    pcts = {c["name"]: c["pct_chg"] for c in cap_indices}
    sz50 = pcts.get("上证50", 0)
    zz500 = pcts.get("中证500", 0)
    zz1000 = pcts.get("中证1000", 0)

    large_avg = sz50
    small_avg = (zz500 + zz1000) / 2 if zz1000 != 0 else zz500

    if small_avg > large_avg + 0.5:
        comment = "📌 **小盘强势领跑**，中证500/中证1000涨幅远超上证50，资金向中小市值扩散。"
    elif large_avg > small_avg + 0.5:
        comment = "📌 **大盘蓝筹占优**，上证50领涨，市场偏好核心资产。"
    elif abs(large_avg - small_avg) < 0.3:
        comment = "📌 **大小盘涨跌幅接近**，市场风格均衡。"
    else:
        comment = "📌 **风格分化明显**，大小盘走势不一致。"

    return f"""## 📊 三、市值结构 — 大小盘对比

| 指数 | 涨跌幅 | 特征 |
|------|--------|------|
{cap_rows}

```mermaid
xychart-beta
    title "大小盘涨跌幅对比 (%)"
    x-axis [{names_str}]
    y-axis "涨跌幅" -5 --> 5
    bar [{pcts_str}]
```

> {comment}

---

"""


def render_market_breadth(breadth: Dict) -> str:
    up_count = breadth.get("up_count", 0)
    down_count = breadth.get("down_count", 0)
    flat_count = breadth.get("flat_count", 0)
    limit_up = breadth.get("limit_up", 0)
    limit_down = breadth.get("limit_down", 0)
    median_pct = breadth.get("median_pct", 0)

    total = up_count + down_count + flat_count

    # 如果总数 < 1000，说明 Wind 返回的不是全市场数据，只展示涨停/跌停
    if total < 1000:
        return f"""## 📉 四、市场广度

### 涨跌停统计

| 指标 | 数值 |
|------|------|
| 涨停家数 | 📈 {limit_up} 家 |
| 跌停家数 | 📉 {limit_down} 家 |

> ⚠️ Wind 未返回全市场涨跌家数，仅展示涨停/跌停数据。全市场涨跌家数及中位数需通过其他数据源获取。

---

"""

    up_ratio = (up_count / total * 100) if total > 0 else 0
    down_ratio = (down_count / total * 100) if total > 0 else 0

    return f"""## 📉 四、市场广度

### 涨跌家数分布

```mermaid
pie title 涨跌家数分布
    "上涨 {up_count}" : {up_ratio:.1f}
    "下跌 {down_count}" : {down_ratio:.1f}
    "平盘 {flat_count}" : {100 - up_ratio - down_ratio:.1f}
```

### 关键统计

| 指标 | 数值 |
|------|------|
| 上涨家数 | {up_count} 家 |
| 下跌家数 | {down_count} 家 |
| 平盘家数 | {flat_count} 家 |
| 涨停家数 | 📈 {limit_up} 家 |
| 跌停家数 | 📉 {limit_down} 家 |
| 全市场中位数 | {color_pct(median_pct)} |

---

"""


def render_sector_performance(sectors: List[Dict]) -> str:
    gainers = sorted(sectors, key=lambda x: x.get("pct_chg", 0), reverse=True)[:10]
    losers = sorted(sectors, key=lambda x: x.get("pct_chg", 0))[:10]

    gainers_rows = ""
    for i, s in enumerate(gainers):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}"
        gainers_rows += f"| {medal} | {s.get('name', '')} | {color_pct(s.get('pct_chg', 0))} |\n"

    losers_rows = ""
    for i, s in enumerate(losers):
        rank = len(sectors) - i
        losers_rows += f"| {rank} | {s.get('name', '')} | {color_pct(s.get('pct_chg', 0))} |\n"

    # Mermaid 涨跌对比图（TOP5 vs 跌幅TOP5）
    top5 = gainers[:5]
    bottom5 = losers[:5]
    chart_names = [s.get('name', '').replace('(申万)', '') for s in top5 + bottom5]
    chart_pcts = [s.get('pct_chg', 0) for s in top5 + bottom5]
    names_str = ", ".join([f'"{n}"' for n in chart_names])
    pcts_str = ", ".join([str(p) for p in chart_pcts])

    # 行业分化评论（规则回退）
    up_count = sum(1 for s in sectors if s.get("pct_chg", 0) > 0)
    down_count = sum(1 for s in sectors if s.get("pct_chg", 0) < 0)
    total_sectors = len(sectors) if sectors else 1
    if up_count > total_sectors * 0.7:
        breadth_comment = "📈 **行业普涨**，多数板块收红。"
    elif down_count > total_sectors * 0.7:
        breadth_comment = "📉 **行业普跌**，多数板块调整。"
    else:
        breadth_comment = f"📊 **行业分化明显**，{up_count}涨/{down_count}跌。"
    if top5:
        breadth_comment += f" 涨幅第一：**{top5[0].get('name', '')}**（{top5[0].get('pct_chg', 0):+.2f}%）。"
    if bottom5:
        breadth_comment += f" 跌幅第一：**{bottom5[0].get('name', '')}**（{bottom5[0].get('pct_chg', 0):+.2f}%）。"

    return f"""## 🏢 五、行业表现

### 🔥 涨幅榜 TOP 10

| 排名 | 行业(申万一级) | 涨跌幅 |
|------|---------------|--------|
{gainers_rows if gainers else "| - | - | - |\n"}

### ❄️ 跌幅榜 TOP 10

| 排名 | 行业(申万一级) | 涨跌幅 |
|------|---------------|--------|
{losers_rows if losers else "| - | - | - |\n"}

```mermaid
xychart-beta
    title "行业涨跌幅TOP5 vs 跌幅TOP5 (%)"
    x-axis [{names_str}]
    y-axis "涨跌幅" -5 --> 5
    bar [{pcts_str}]
```

> {breadth_comment}

---

"""


def render_hot_concepts(concepts: List[Dict]) -> str:
    concepts_rows = ""
    for c in concepts[:10]:
        concepts_rows += f"| {c.get('name', '')} | {color_pct(c.get('pct_chg', 0))} |\n"

    top_concept = f"**{concepts[0].get('name', '')}**（{concepts[0].get('pct_chg', 0):+.2f}%）" if concepts else "**-**"

    return f"""## 💡 六、热门概念

| 概念 | 涨跌幅 |
|------|--------|
{concepts_rows if concepts else "| - | - |\n"}

> 📌 今日热门概念集中在 {top_concept} 等方向。

---

"""


def _simplify_sector_name(name: str) -> str:
    """简化 GICS 长行业名称，取最后一段"""
    if "--" in name:
        parts = name.split("--")
        return parts[-1].strip()
    return name


def render_money_flow(money_flow: Dict) -> str:
    net_inflow = money_flow.get("net_inflow", 0)
    parsed_success = money_flow.get("parsed_success", False)
    sector_flow = sorted(money_flow.get("sector_flow", []), key=lambda x: x.get("net_inflow", 0), reverse=True)[:5]

    sector_rows = ""
    for s in sector_flow:
        simple_name = _simplify_sector_name(s.get('name', ''))
        sector_rows += f"| {simple_name} | {format_number(s.get('net_inflow', 0))} |\n"

    # 资金流向评论：区分"真正 0 净流入"与"解析失败"
    if not parsed_success:
        flow_comment = "⚠️ **未能解析资金流向数据**，可能 Wind 未返回或格式不匹配。"
    elif net_inflow > 100 * 1e8:
        flow_comment = "🟢 **主力资金大幅净流入**，市场做多意愿强烈。"
    elif net_inflow > 0:
        flow_comment = "🟢 **主力资金小幅净流入**。"
    elif net_inflow > -100 * 1e8:
        flow_comment = "🔴 **主力资金小幅净流出**。"
    else:
        flow_comment = "🔴 **主力资金大幅净流出**，市场谨慎情绪升温。"

    return f"""## 💰 七、资金流向

### 主力资金概况

| 指标 | 数值 |
|------|------|
| 主力资金净流入 | {format_number(net_inflow)} |

### 资金流入行业 TOP5

| 行业 | 净流入 |
|------|--------|
{sector_rows if sector_rows else "| - | - |\n"}

> {flow_comment}

---

"""


def render_global_markets(global_indices: List[Dict]) -> str:
    if not global_indices:
        return ""

    global_rows = ""
    for idx in global_indices[:8]:
        global_rows += f"| {idx.get('name', '')} | {color_pct(idx.get('pct_chg', 0))} |\n"

    # 全球市场评论
    up_global = [g for g in global_indices if g.get("pct_chg", 0) > 0]
    down_global = [g for g in global_indices if g.get("pct_chg", 0) < 0]
    if len(up_global) > len(down_global):
        global_comment = "📌 全球市场多数上涨，外围情绪偏暖。"
    elif len(down_global) > len(up_global):
        global_comment = "📌 全球市场多数下跌，外围情绪偏弱。"
    else:
        global_comment = "📌 全球市场涨跌不一。"

    return f"""## 🌍 八、周边市场

| 指数 | 涨跌幅 |
|------|--------|
{global_rows}

> {global_comment}

---

"""


def parse_futures(futures_data: Dict) -> List[Dict]:
    """解析期货数据"""
    parsed = parse_wind_data(futures_data)
    futures = []
    if "rows" in parsed:
        for row in parsed["rows"]:
            name = ""
            pct = 0
            for key, val in row.items():
                if ("简称" in key or "名称" in key or "name" in key.lower()) and not name:
                    name = str(val)
                elif ("涨跌幅" in key or "pct" in key.lower()) and "排名" not in key:
                    try:
                        pct = float(val)
                    except (ValueError, TypeError):
                        pass
            if name:
                futures.append({"name": name, "pct_chg": pct})
    elif "text" in parsed:
        for line in parsed["text"].split("\n"):
            line = line.strip()
            if line and "%" in line:
                parts = line.split()
                if len(parts) >= 2:
                    pct_str = parts[-1].replace("%", "").replace("+", "")
                    try:
                        futures.append({"name": parts[0], "pct_chg": float(pct_str)})
                    except ValueError:
                        pass
    return futures


def render_futures(futures_data: Dict) -> str:
    futures = parse_futures(futures_data)
    if not futures:
        return ""

    futures_rows = ""
    for f in futures[:10]:
        futures_rows += f"| {f.get('name', '')} | {color_pct(f.get('pct_chg', 0))} |\n"

    return f"""## 📊 九、期货市场

| 品种 | 涨跌幅 |
|------|--------|
{futures_rows if futures_rows else "| - | - |\n"}

---

"""


def render_financial_news(news: List[Dict]) -> str:
    if not news:
        return ""
    
    news_rows = ""
    for n in news[:5]:
        news_rows += f"- {n.get('title', '')}\n"

    return f"""## 📰 十、财经要闻

{news_rows}

---

"""


def render_ai_analysis(ai_result: Dict[str, str]) -> str:
    conclusion = ai_result.get("conclusion", "")
    main_line = ai_result.get("main_line", "")
    tomorrow_focus = ai_result.get("tomorrow_focus", "")

    if not conclusion:
        conclusion = "（AI 分析未启用或未返回结果）"
    if not main_line:
        main_line = "（暂无）"
    if not tomorrow_focus:
        tomorrow_focus = "1. 关注量能变化；\n2. 观察板块分化；\n3. 留意外围市场影响。"

    return f"""## 🤖 十一、盘面结论

{conclusion}

---

## 🎯 十二、主线轮动

{main_line}

---

## 🔍 十三、明日关注

{tomorrow_focus}
"""