import requests
import json
import os
import time
import random
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/"
}
UT = "bd1d9ddb04089700cf9c27f6f7426281"

# 东方财富 clist 接口的候选主机池，按优先级排序
PUSH2_CLIST_HOSTS = (
    "https://push2.eastmoney.com",
    "https://push2delay.eastmoney.com",
    "https://40.push2.eastmoney.com",
)

# 两次请求之间的最小间隔（秒），避免触发频率限制
MIN_INTERVAL = 1.5
_last_call_time = [0.0]


def em_get_with_fallback(path, params, timeout=10):
    """
    东财统一请求入口：域名轮换 + 指数退避重试。
    如果当前域名返回 502/503/504 或连接异常，自动切换到下一个域名重试。
    """
    last_exc = None
    for host in PUSH2_CLIST_HOSTS:
        url = f"{host}{path}"
        # 全局节流，避免请求过于密集
        wait = MIN_INTERVAL - (time.time() - _last_call_time[0])
        if wait > 0:
            time.sleep(wait + random.uniform(0.1, 0.3))
        _last_call_time[0] = time.time()

        try:
            res = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            # 如果是 502/503/504，记录异常并尝试下一个域名
            if res.status_code in (502, 503, 504):
                print(f"[降级] {host} 返回 {res.status_code}，切换下一个域名")
                last_exc = Exception(f"HTTP {res.status_code}")
                continue
            res.raise_for_status()
            return res
        except Exception as e:
            print(f"[降级] {host} 异常: {e}，切换下一个域名")
            last_exc = e
            # 指数退避：每次切换域名后等待更久
            time.sleep(1.0)

    raise last_exc or Exception("所有候选域名均不可用")


def fetch_rank(indicator, po):
    """获取行业资金流排名，indicator仅支持5day/10day，po=1流入/0流出"""
    params = {
        "pn": 1, "pz": 10, "np": 1, "fltt": 2, "invt": 2,
        "fs": "m:90+t:2", "fields": "f12,f14,f3,f62",
        "ut": UT, "fid": "f62", "po": po, "indicator": indicator
    }
    try:
        res = em_get_with_fallback("/api/qt/clist/get", params)
        data = res.json()
        items = []
        if data.get("data") and data["data"].get("diff"):
            for item in data["data"]["diff"]:
                items.append({
                    "name": item.get("f14", ""),
                    "change": item.get("f3", 0),
                    "main_net": round(item.get("f62", 0) / 100000000, 2)
                })
        return items
    except Exception as e:
        print(f"[警告] 排行接口 {indicator} po={po} 最终失败: {e}")
        return []


def main():
    sentiment_data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "periods": {}
    }

    # 抓取 10日 排行
    print("[信息] 抓取 10日 排行...")
    inflow_10d = fetch_rank("10day", 1)
    outflow_10d = fetch_rank("10day", 0)
    sentiment_data["periods"]["10d"] = {"inflow": inflow_10d, "outflow": outflow_10d}

    # 抓取 5日 排行
    print("[信息] 抓取 5日 排行...")
    inflow_5d = fetch_rank("5day", 1)
    outflow_5d = fetch_rank("5day", 0)
    sentiment_data["periods"]["5d"] = {"inflow": inflow_5d, "outflow": outflow_5d}

    os.makedirs("data", exist_ok=True)
    with open("data/sentiment.json", "w", encoding="utf-8") as f:
        json.dump(sentiment_data, f, ensure_ascii=False, indent=2)
    print("情绪数据保存完成。")


if __name__ == "__main__":
    main()
