#!/usr/bin/env python3
"""抖音创作者中心 - 完整视频列表抓取
用法: python douyin_fetch_full.py
需要先在浏览器 F12 里找到视频列表 API 的 URL，替换下面的 BASE_URL
"""
from playwright.sync_api import sync_playwright
import json
import time
import re

# ============================================================
# 请替换下面这个 URL！
# 在浏览器 F12 → Network → XHR 里找到返回视频列表的请求，
# 右键 → Copy → Copy as cURL，把 URL 贴到这里
# ============================================================
BASE_URL = "PASTE_YOUR_API_URL_HERE"

# 或者，如果你知道 URL 结构，可以直接构造：
# BASE_URL = "https://creator.douyin.com/aweme/v1/creator/data/item/list/?..."

USER_DATA_DIR = r"C:\Users\YOUR_USERNAME\AppData\Local\Microsoft\Edge\User Data"


def fetch_all_videos():
    all_items = []
    cursor = 0
    page = 1
    
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            channel="msedge",
            headless=False  # 设为 True 可以后台运行
        )
        page_obj = browser.new_page()
        
        while True:
            # 构造翻页 URL
            url = BASE_URL
            if cursor > 0:
                # 替换或追加 cursor 参数
                if 'cursor=' in url:
                    url = re.sub(r'cursor=\d+', f'cursor={cursor}', url)
                else:
                    url += f"&cursor={cursor}"
            
            print(f"\n📄 正在获取第 {page} 页...")
            print(f"   URL: {url[:120]}...")
            
            resp = page_obj.goto(url)
            data = resp.json()
            
            if data.get('BaseResp', {}).get('StatusCode', 0) != 0:
                print(f"❌ API 错误: {data.get('BaseResp', {}).get('StatusMessage', 'unknown')}")
                break
            
            items = data.get('items', [])
            if not items:
                print("✅ 没有更多数据了")
                break
            
            all_items.extend(items)
            print(f"   获取到 {len(items)} 条，累计 {len(all_items)} 条")
            
            # 检查是否还有更多
            if not data.get('has_more', False):
                print("✅ has_more=false，抓取完成")
                break
            
            # 获取下一页的 cursor
            cursor = data.get('max_cursor', 0)
            if cursor == 0:
                print("⚠️ max_cursor 为 0，停止翻页")
                break
            
            page += 1
            time.sleep(1)  # 避免请求过快
        
        browser.close()
    
    # 保存结果
    result = {
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_items": len(all_items),
        "items": all_items
    }
    
    with open("douyin_data_full.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✅ 抓取完成！共 {len(all_items)} 条视频")
    print(f"📁 数据已保存到 douyin_data_full.json")
    print(f"\n请把 douyin_data_full.json 文件发给我")
    
    return result


if __name__ == '__main__':
    if BASE_URL == "PASTE_YOUR_API_URL_HERE":
        print("❌ 请先替换 BASE_URL！")
        print("   在浏览器 F12 → Network → XHR 里找到视频列表 API 的 URL")
        print("   右键请求 → Copy → Copy as cURL → 提取 URL 部分")
        exit(1)
    
    fetch_all_videos()
