#!/usr/bin/env python3
"""
抖音创作者中心 - 完整抓取脚本（翻页 + 观众画像）
在本地 Windows 上运行，复用 Edge 浏览器登录态

用法:
  1. pip install playwright
  2. playwright install msedge
  3. 关闭所有 Edge 窗口
  4. python douyin_fetch_all.py

输出: douyin_data_full.json (包含所有视频数据和观众画像)
"""
from playwright.sync_api import sync_playwright
import json, time, re

# ============================================================
# 请修改为你电脑的实际用户名
# ============================================================
USERNAME = "YOUR_USERNAME"

USER_DATA_DIR = rf"C:\Users\{USERNAME}\AppData\Local\Microsoft\Edge\User Data"

# 视频列表 API URL（从浏览器 F12 复制）
ITEM_LIST_URL = (
    "https://creator.douyin.com/web/api/creator/item/list?"
    "count=10&order_by=1&fields=metrics%2Creview%2Cvisibility"
    "&need_cooperation=true"
    "&start_time=1777478400000&end_time=1785340799000"
    "&need_long_article=true"
)

# 观众画像 API 模板（需要替换 {item_id}）
AUDIENCE_URL_TEMPLATE = (
    "https://creator.douyin.com/web/api/creator/data/audience/profile?"
    "item_id={item_id}&period=total"
)


def fetch_items(page):
    """翻页抓取所有视频"""
    all_items = []
    cursor = 0
    pg = 1
    
    while True:
        url = ITEM_LIST_URL
        if cursor > 0:
            url += f"&cursor={cursor}"
        
        print(f"📄 第{pg}页...")
        
        resp = page.goto(url)
        data = resp.json()
        
        if data.get('BaseResp', {}).get('StatusCode', 0) != 0:
            print(f"   ❌ {data.get('BaseResp', {}).get('StatusMessage', '')}")
            break
        
        items = data.get('items', [])
        if not items:
            break
        
        all_items.extend(items)
        print(f"   {len(items)}条，累计{len(all_items)}条")
        
        if not data.get('has_more'):
            break
        
        cursor = data.get('max_cursor', 0)
        if not cursor:
            break
        pg += 1
        time.sleep(1)
    
    return all_items


def fetch_audience(page, item_id):
    """抓取单条视频的观众画像"""
    url = AUDIENCE_URL_TEMPLATE.format(item_id=item_id)
    try:
        resp = page.goto(url, timeout=10000)
        return resp.json()
    except:
        return None


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            channel="msedge",
            headless=False,  # 先看效果，成功后可改 True
            viewport={"width": 1280, "height": 800}
        )
        page = browser.new_page()
        
        # ========== 第一步：抓取视频列表 ==========
        print("=" * 50)
        print("第一步：抓取视频列表")
        print("=" * 50)
        
        items = fetch_items(page)
        print(f"\n✅ 视频列表抓取完成：{len(items)} 条")
        
        if not items:
            print("❌ 没有抓到数据，请检查是否已登录抖音创作者中心")
            browser.close()
            return
        
        # ========== 第二步：抓取观众画像 ==========
        print(f"\n{'='*50}")
        print("第二步：抓取观众画像（可能需要几分钟）")
        print("=" * 50)
        
        for i, item in enumerate(items):
            item_id = item.get('id', '')
            desc = item.get('description', '')[:40]
            
            print(f"\n[{i+1}/{len(items)}] {desc}")
            
            audience = fetch_audience(page, item_id)
            if audience and audience.get('BaseResp', {}).get('StatusCode') == 0:
                item['audience_profile'] = audience
                print(f"   ✅ 画像获取成功")
            else:
                print(f"   ⚠️ 画像获取失败")
            
            time.sleep(0.5)  # 避免请求过快
        
        browser.close()
    
    # ========== 保存结果 ==========
    result = {
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_items": len(items),
        "items": items
    }
    
    output_file = "douyin_data_full.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✅ 全部完成！")
    print(f"   视频: {len(items)} 条")
    print(f"   文件: {output_file}")
    print(f"\n📤 请把 {output_file} 发给我")


if __name__ == '__main__':
    if USERNAME == "YOUR_USERNAME":
        print("❌ 请先修改脚本里的 USERNAME 变量！")
        exit(1)
    main()
