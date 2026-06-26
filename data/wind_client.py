import subprocess
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List


class WindClient:
    def __init__(self):
        self.skill_dir = os.path.expanduser("~/.agents/skills/wind-mcp-skill")
        self.cli_path = os.path.join(self.skill_dir, "scripts", "cli.mjs")
        self._ensure_node()

    def _ensure_node(self):
        try:
            subprocess.run(["node", "--version"], capture_output=True, check=True)
        except Exception:
            raise EnvironmentError("未找到 Node.js，请先安装 Node.js")

    def _call_cli(self, server_type: str, tool_name: str, params: Dict[str, Any], retries: int = 2) -> Dict[str, Any]:
        params_json = json.dumps(params, ensure_ascii=False)

        cmd = [
            "node", self.cli_path,
            "call", server_type, tool_name,
            params_json
        ]

        last_error = None
        for attempt in range(retries + 1):
            try:
                result = subprocess.run(
                    cmd,
                    cwd=self.skill_dir,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=60
                )

                if result.returncode == 0:
                    try:
                        output = json.loads(result.stdout)
                        if "content" in output and output["content"]:
                            content = output["content"][0]
                            if "text" in content:
                                try:
                                    inner_data = json.loads(content["text"])
                                    if "data" in inner_data:
                                        return inner_data["data"]
                                    return inner_data
                                except json.JSONDecodeError:
                                    return {"text": content["text"]}
                            return content
                        return output
                    except json.JSONDecodeError:
                        return {"text": result.stdout.strip()}
                else:
                    # 进程崩溃（如 UV_HANDLE_CLOSING），记录错误并重试
                    try:
                        error = json.loads(result.stderr)
                    except json.JSONDecodeError:
                        error = {"message": result.stderr.strip()}
                    last_error = error
                    if attempt < retries:
                        time.sleep(1)
                        continue
                    return {"error": error}

            except subprocess.TimeoutExpired:
                last_error = {"message": "请求超时"}
                if attempt < retries:
                    time.sleep(1)
                    continue
                return {"error": last_error}
            except Exception as e:
                last_error = {"message": str(e)}
                if attempt < retries:
                    time.sleep(1)
                    continue
                return {"error": last_error}

        return {"error": last_error or {"message": "未知错误"}}



    def get_index_price(self, windcode: str, indexes: str) -> Dict[str, Any]:
        return self._call_cli(
            "index_data",
            "get_index_price_indicators",
            {"windcode": windcode, "indexes": indexes}
        )

    def get_stock_price(self, windcode: str, indexes: str) -> Dict[str, Any]:
        return self._call_cli(
            "stock_data",
            "get_stock_price_indicators",
            {"windcode": windcode, "indexes": indexes}
        )

    def get_index_kline(self, windcode: str, begin_date: str, end_date: str) -> Dict[str, Any]:
        return self._call_cli(
            "index_data",
            "get_index_kline",
            {"windcode": windcode, "begin_date": begin_date, "end_date": end_date}
        )

    def get_financial_news(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        return self._call_cli(
            "financial_docs",
            "get_financial_news",
            {"query": query, "top_k": top_k}
        )

    def get_financial_data(self, question: str) -> Dict[str, Any]:
        return self._call_cli(
            "analytics_data",
            "get_financial_data",
            {"question": question}
        )

    def get_index_basicinfo(self, question: str) -> Dict[str, Any]:
        return self._call_cli(
            "index_data",
            "get_index_basicinfo",
            {"question": question}
        )

    def get_index_fundamentals(self, question: str) -> Dict[str, Any]:
        return self._call_cli(
            "index_data",
            "get_index_fundamentals",
            {"question": question}
        )

    def get_prev_trading_day_volume(self, date: str) -> float:
        """获取前一交易日的沪深合计成交额"""
        dt = datetime.strptime(date, "%Y-%m-%d")
        # 往前找最近的工作日
        prev_date = None
        for i in range(1, 8):
            prev = dt - timedelta(days=i)
            if prev.weekday() < 5:  # 周一到周五
                prev_date = prev.strftime("%Y-%m-%d")
                break
        if not prev_date:
            return 0

        prev_volume = 0
        for code in ("000001.SH", "399001.SZ"):
            # 用 K 线接口取历史成交额，避免 get_index_price 只返回当日最新值
            data = self.get_index_kline(code, prev_date, prev_date)
            if isinstance(data, dict) and "error" not in data and "rows" in data:
                rows = data["rows"]
                columns = data.get("columns", [])
                col_names = [col.get("name", f"col_{i}") for i, col in enumerate(columns)]
                # 定位"成交额"列
                vol_idx = -1
                for i, name in enumerate(col_names):
                    if "成交额" in name:
                        vol_idx = i
                        break
                if vol_idx >= 0 and rows and rows[0] and vol_idx < len(rows[0]):
                    try:
                        prev_volume += float(rows[0][vol_idx])
                    except (ValueError, TypeError, IndexError):
                        pass
        return prev_volume

    def get_main_index_data(self, date: str) -> List[Dict[str, Any]]:
        indices = [
            ("000001.SH", "上证指数"),
            ("399001.SZ", "深证成指"),
            ("399006.SZ", "创业板指"),
            ("000016.SH", "上证50"),
            ("000905.SH", "中证500"),
            ("000852.SH", "中证1000")
        ]
        
        result = []
        for code, name in indices:
            data = self.get_index_price(code, "中文简称,最新成交价,涨跌幅,成交额,今日开盘价,今日最高价,今日最低价,前收盘价")
            if isinstance(data, dict) and "error" not in data and "rows" in data:
                rows = data["rows"]
                columns = data.get("columns", [])
                if rows and columns:
                    col_names = [col.get("name", f"col_{i}") for i, col in enumerate(columns)]
                    row_data = rows[0]
                    item = {"code": code, "name": name}
                    for i, val in enumerate(row_data):
                        if i < len(col_names):
                            col_name = col_names[i]
                            if col_name == "成交额":
                                try:
                                    item[col_name] = float(val)
                                except (ValueError, TypeError):
                                    item[col_name] = val
                            else:
                                item[col_name] = val
                    result.append(item)
        
        return result

    def get_market_overview(self, date: str) -> Dict[str, Any]:
        question = f"{date}A股市场概况包括涨跌家数、涨停跌停家数、全市场成交额"
        return self.get_financial_data(question)

    def get_sector_performance(self, date: str) -> Dict[str, Any]:
        question = f"{date}申万一级行业涨跌幅排名"
        return self.get_financial_data(question)

    def get_hot_concepts(self, date: str) -> Dict[str, Any]:
        question = f"{date}A股热门概念板块涨跌幅排名TOP10"
        return self.get_financial_data(question)

    def get_money_flow(self, date: str) -> Dict[str, Any]:
        question = f"{date} 申万一级行业主力资金净流入排名"
        return self.get_financial_data(question)

    def get_market_breadth(self, date: str) -> Dict[str, Any]:
        question = f"{date} A股全市场涨跌家数统计 涨停跌停家数"
        return self.get_financial_data(question)

    def get_global_indices(self, date: str) -> Dict[str, Any]:
        question = f"{date}全球主要指数涨跌幅包括道琼斯纳斯达克标普500日经225恒生指数"
        return self.get_financial_data(question)

    def get_futures_data(self, date: str) -> Dict[str, Any]:
        """获取股指期货和商品期货涨跌数据"""
        question = f"{date}股指期货IF IH IC IM主力合约涨跌幅 国债期货 沪金沪银沪铜涨跌幅"
        return self.get_financial_data(question)

    def fetch_all_data(self, date: str) -> dict:
        print(f"正在获取 {date} 的市场数据...")

        data = {
            "date": date,
            "main_indices": self.get_main_index_data(date),
            "market_overview": self.get_market_overview(date),
            "sector_performance": self.get_sector_performance(date),
            "hot_concepts": self.get_hot_concepts(date),
            "money_flow": self.get_money_flow(date),
            "market_breadth": self.get_market_breadth(date),
            "global_indices": self.get_global_indices(date),
            "futures": self.get_futures_data(date),
            "news": self.get_financial_news("A股今日行情", top_k=5)
        }

        # 获取前日成交额用于对比
        try:
            data["prev_day_volume"] = self.get_prev_trading_day_volume(date)
        except Exception as e:
            print(f"获取前日成交额失败: {e}")
            data["prev_day_volume"] = 0

        print("数据获取完成！")
        return data