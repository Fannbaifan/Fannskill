#!/usr/bin/env python3
"""
抖音创作者中心 - 观众画像 DOM 抓取（不依赖 API）
在本地 Windows 上运行，复用 Edge 浏览器登录态

用法:
  1. pip install playwright
  2. playwright install msedge
  3. 关闭所有 Edge 窗口
  4. python douyin_fetch_audience_dom.py

输出: douyin_audience_data.json
"""
from playwright.sync_api import sync_playwright
import json, time, re

# ============================================================
# 请修改为你电脑的实际用户名
# ============================================================
USERNAME = "YOUR_USERNAME"

USER_DATA_DIR = rf"C:\Users\{USERNAME}\AppData\Local\Microsoft\Edge\User Data"


def extract_gender(page):
    """从页面 DOM 提取性别分布"""
    # 尝试多种选择器
    selectors = [
        '[class*="gender"]',
        '[class*="sex"]',
        '.gender-distribution',
        '.sex-distribution',
        '[data-e2e*="gender"]',
    ]
    
    gender_data = {}
    
    # 方法1：直接找包含"男""女"的文本元素
    try:
        # 找页面中所有文本，匹配 "男 XX%" 和 "女 XX%"
        all_text = page.evaluate('''() => {
            const texts = [];
            document.querySelectorAll('*').forEach(el => {
                if (el.children.length === 0) {
                    const t = el.textContent.trim();
                    if (t && (t.includes('男') || t.includes('女'))) {
                        texts.push(t);
                    }
                }
            });
            return texts;
        }''')
        
        for text in all_text:
            # 匹配 "男 60%" 或 "女 40%"
            m = re.search(r'(男|女)\s*(\d+(?:\.\d+)?)\s*%', text)
            if m:
                gender = 'male' if m.group(1) == '男' else 'female'
                gender_data[gender] = float(m.group(2))
    except:
        pass
    
    return gender_data


def extract_age(page):
    """从页面 DOM 提取年龄分布"""
    age_data = {}
    
    try:
        # 找页面中所有文本，匹配年龄区间和百分比
        all_text = page.evaluate('''() => {
            const texts = [];
            document.querySelectorAll('*').forEach(el => {
                if (el.children.length === 0) {
                    const t = el.textContent.trim();
                    if (t && (/^\d+[-~]\d+/.test(t) || /^\d+\+/.test(t) || /^\d+岁以下/.test(t))) {
                        texts.push(t);
                    }
                }
            });
            return texts;
        }''')
        
        # 同时找百分比
        percent_texts = page.evaluate('''() => {
            const texts = [];
            document.querySelectorAll('*').forEach(el => {
                if (el.children.length === 0) {
                    const t = el.textContent.trim();
                    if (t && /^\d+(?:\.\d+)?\s*%$/.test(t)) {
                        texts.push(t);
                    }
                }
            });
            return texts;
        }''')
        
        # 尝试配对
        for i, age_text in enumerate(all_text[:len(percent_texts)]):
            age_range = age_text
            percent_str = percent_texts[i] if i < len(percent_texts) else ''
            m = re.search(r'(\d+(?:\.\d+)?)\s*%', percent_str)
            if m:
                age_data[age_range] = float(m.group(1))
    except:
        pass
    
    return age_data


def extract_region(page):
    """从页面 DOM 提取地域分布（Top 5）"""
    region_data = {}
    
    try:
        # 找省份名称 + 百分比
        all_text = page.evaluate('''() => {
            const texts = [];
            document.querySelectorAll('*').forEach(el => {
                if (el.children.length === 0) {
                    const t = el.textContent.trim();
                    // 匹配省份名 + 百分比
                    if (t && /^(北京|上海|天津|重庆|河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|台湾|内蒙古|广西|西藏|宁夏|新疆|香港|澳门)\s*\d+(\.\d+)?\s*%$/.test(t)) {
                        texts.push(t);
                    }
                }
            });
            return texts;
        }''')
        
        for text in all_text[:5]:
            m = re.match(r'(.+?)\s*(\d+(?:\.\d+)?)\s*%', text)
            if m:
                region_data[m.group(1)] = float(m.group(2))
    except:
        pass
    
    return region_data


def extract_all_from_page(page):
    """从当前页面提取所有可见的画像数据"""
    # 等待页面加载
    page.wait_for_timeout(3000)
    
    # 截图保存（调试用）
    # page.screenshot(path="audience_debug.png")
    
    gender = extract_gender(page)
    age = extract_age(page)
    region = extract_region(page)
    
    return {
        "gender": gender,
        "age": age,
        "region": region,
        "raw_texts": page.evaluate('''() => {
            // 返回页面上所有可见文本，用于调试
            return Array.from(document.querySelectorAll('body *'))
                .map(el => el.textContent.trim())
                .filter(t => t.length > 0 && t.length < 100)
                .slice(0, 200);
        }''')
    }


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            channel="msedge",
            headless=False,  # 先看效果
            viewport={"width": 1440, "height": 900}
        )
        page = browser.new_page()
        
        # ========== 第一步：到创作者中心作品列表 ==========
        print("打开创作者中心...")
        page.goto("https://creator.douyin.com/")
        page.wait_for_timeout(5000)
        
        # 点击「数据中心」→「作品分析」
        # 或者直接访问作品分析页面
        print("导航到作品分析...")
        page.goto("https://creator.douyin.com/creator-micro/data-center/content")
        page.wait_for_timeout(5000)
        
        # ========== 第二步：获取所有视频链接 ==========
        print("获取视频列表...")
        
        # 找页面上所有视频条目
        video_links = page.evaluate('''() => {
            const links = [];
            document.querySelectorAll('a[href*="/data-center/content/"]').forEach(a => {
                const match = a.href.match(/item_id=(\d+)/);
                if (match) {
                    links.push({
                        item_id: match[1],
                        title: a.textContent.trim().slice(0, 60)
                    });
                }
            });
            return links;
        }''')
        
        print(f"找到 {len(video_links)} 条视频")
        
        # 去重
        seen = set()
        unique_videos = []
        for v in video_links:
            if v['item_id'] not in seen:
                seen.add(v['item_id'])
                unique_videos.append(v)
        
        print(f"去重后 {len(unique_videos)} 条")
        
        # ========== 第三步：逐条打开观众分析 ==========
        results = []
        
        for i, video in enumerate(unique_videos):
            item_id = video['item_id']
            title = video['title']
            
            print(f"\n[{i+1}/{len(unique_videos)}] {title}")
            
            # 打开观众分析页面
            audience_url = f"https://creator.douyin.com/creator-micro/data-center/content/audience?item_id={item_id}"
            page.goto(audience_url)
            page.wait_for_timeout(4000)
            
            # 提取数据
            profile = extract_all_from_page(page)
            
            results.append({
                "item_id": item_id,
                "title": title,
                "audience": profile
            })
            
            print(f"   性别: {profile['gender']}")
            print(f"   年龄: {profile['age']}")
            print(f"   地域: {profile['region']}")
            
            time.sleep(1)
        
        browser.close()
    
    # ========== 保存结果 ==========
    output = {
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(results),
        "videos": results
    }
    
    with open("douyin_audience_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✅ 完成！共抓取 {len(results)} 条视频的画像")
    print(f"📁 保存到 douyin_audience_data.json")
    print(f"\n📤 请把 douyin_audience_data.json 发给我")


if __name__ == '__main__':
    if USERNAME == "YOUR_USERNAME":
        print("❌ 请先修改脚本里的 USERNAME 变量！")
        exit(1)
    main()
