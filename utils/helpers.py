import json
import os
from datetime import datetime
from typing import Dict, Any


def load_config() -> Dict[str, Any]:
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def format_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y年%m月%d日")
    except (ValueError, TypeError):
        return date_str


def format_number(num: float) -> str:
    if num >= 100000000:
        return f"{num/100000000:.2f}亿"
    elif num >= 10000:
        return f"{num/10000:.2f}万"
    return f"{num:.2f}"


def format_price(price: float) -> str:
    return f"{price:.2f}"


def format_pct(pct: float) -> str:
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"


def get_report_filename(date_str: str) -> str:
    return f"{date_str}_A股收盘简报.md"


def save_report(content: str, date_str: str) -> str:
    config = load_config()
    output_dir = config["output_dir"]
    ensure_dir(output_dir)
    filename = get_report_filename(date_str)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def color_pct(pct: float) -> str:
    if pct > 0:
        return f"**{format_pct(pct)}**"
    elif pct < 0:
        return f"~~{format_pct(pct)}~~"
    return format_pct(pct)