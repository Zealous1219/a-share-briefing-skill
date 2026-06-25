import argparse
from datetime import datetime, timedelta
from data.wind_client import WindClient
from data.ai_analyzer import generate_ai_analysis
from templates.report_template import (
    generate_report,
    parse_index_data,
    parse_market_breadth,
    parse_sectors,
    parse_concepts,
    parse_money_flow,
    parse_global_indices,
    parse_news,
)
from utils.helpers import save_report, load_config


def get_trading_date(date_str: str = None) -> str:
    if date_str:
        return date_str
    
    today = datetime.now()
    if today.weekday() >= 5:
        if today.weekday() == 5:
            today = today - timedelta(days=1)
        else:
            today = today - timedelta(days=2)
    
    return today.strftime("%Y-%m-%d")


def main():
    parser = argparse.ArgumentParser(description="A股收盘简报生成器")
    parser.add_argument("-d", "--date", type=str, help="指定日期 (格式: YYYY-MM-DD)")
    parser.add_argument("--no-ai", action="store_true", help="跳过 AI 分析，使用规则回退")
    args = parser.parse_args()
    
    date = get_trading_date(args.date)
    print(f"生成 {date} 的A股收盘简报...")
    
    wind_client = WindClient()
    data = wind_client.fetch_all_data(date)
    
    # 解析数据用于 AI 分析
    parsed_indices = parse_index_data(data.get("main_indices", []))
    parsed_news = parse_news(data.get("news", {}))
    # 把新闻标题拼接为文本，供市场广度解析做回退提取
    news_text = " ".join([n.get("title", "") for n in parsed_news])
    parsed_breadth = parse_market_breadth(data.get("market_breadth", {}), news_text)
    parsed_sectors = parse_sectors(data.get("sector_performance", {}))
    parsed_concepts = parse_concepts(data.get("hot_concepts", {}))
    parsed_money_flow = parse_money_flow(data.get("money_flow", {}))
    parsed_global = parse_global_indices(data.get("global_indices", {}))
    
    # AI 分析
    ai_result = None
    if not args.no_ai:
        print("正在生成 AI 分析...")
        ai_result = generate_ai_analysis(
            date=date,
            indices=parsed_indices,
            breadth=parsed_breadth,
            sectors=parsed_sectors,
            concepts=parsed_concepts,
            money_flow=parsed_money_flow,
            global_indices=parsed_global,
            news=parsed_news,
        )
    
    report_content = generate_report(data, date, ai_result)
    
    filepath = save_report(report_content, date)
    print(f"简报已生成：{filepath}")


if __name__ == "__main__":
    main()
