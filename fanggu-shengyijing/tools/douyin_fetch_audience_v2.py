#!/usr/bin/env python3
"""
抖音创作者中心 - 观众画像 DOM 抓取 v2
修复 Edge 启动问题
"""
from playwright.sync_api import sync_playwright
import json, time, re, os

USERNAME = "YOUR_USERNAME"
USER_DATA_DIR = rf"C:\Users\{USERNAME}\AppData\Local\Microsoft\Edge\User Data"


def kill_edge():
    """强制关闭所有 Edge 进程"""
    print("正在关闭 Edge 进程...")
    os.system('taskkill /F /IM msedge.exe 2>nul')
    time.sleep(2)


def extract_audience(page):
    """从观众分析页面提取数据"""
    page.wait_for_timeout(3000)
    
    # 获取页面上所有可见文本
    texts = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('body *'))
            .map(el => el.textContent.trim())
            .filter(t => t.length > 0 && t.length < 50);
    }''')
    
    gender = {}
    age = {}
    region = {}
    
    for text in texts:
        # 性别
        m = re.search(r'(男|女)\s*(\d+(?:\.\d+)?)\s*%', text)
        if m:
            key = 'male' if m.group(1) == '男' else 'female'
            gender[key] = float(m.group(2))
        
        # 年龄
        m = re.match(r'^(\d+[-+]\d+|\d+\+|[\u4e00-\u9fff]+)\s*(\d+(?:\.\d+)?)\s*%$', text)
        if m:
            age[m.group(1)] = float(m.group(2))
        
        # 地域（省份 + 百分比）
        provinces = ['北京','上海','天津','重庆','河北','山西','辽宁','吉林','黑龙江',
                     '江苏','浙江','安徽','福建','江西','山东','河南','湖北','湖南',
                     '广东','海南','四川','贵州','云南','陕西','甘肃','青海','台湾',
                     '内蒙古','广西','西藏','宁夏','新疆','香港','澳门']
        for prov in provinces:
            m = re.match(rf'^{prov}\s*(\d+(?:\.\d+)?)\s*%$', text)
            if m:
                region[prov] = float(m.group(1))
                break
    
    return {
        "gender": gender,
        "age": age,
        "region": dict(sorted(region.items(), key=lambda x: -x[1])[:5]),
        "_debug_texts": texts[:30]  # 调试用
    }


def main():
    kill_edge()
    
    with sync_playwright() as p:
        print("启动 Edge...")
        
        # 尝试用 channel=msedge 启动
        try:
            browser = p.chromium.launch_persistent_context(
                USER_DATA_DIR,
                channel="msedge",
                headless=False,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
                viewport={"width": 1440, "height": 900}
            )
        except Exception as e:
            print(f"msedge channel 失败: {e}")
            print("尝试用 chromium 启动...")
            browser = p.chromium.launch_persistent_context(
                USER_DATA_DIR,
                headless=False,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
                viewport={"width": 1440, "height": 900}
            )
        
        page = browser.new_page()
        
        # 到作品分析页面
        print("导航到作品分析...")
        page.goto("https://creator.douyin.com/creator-micro/data-center/content")
        page.wait_for_timeout(5000)
        
        # 获取视频列表
        print("获取视频列表...")
        video_ids = page.evaluate('''() => {
            const ids = [];
            document.querySelectorAll('a[href*="item_id="]').forEach(a => {
                const m = a.href.match(/item_id=(\d+)/);
                if (m && !ids.find(x => x.id === m[1])) {
                    ids.push({id: m[1], title: a.textContent.trim().slice(0,50)});
                }
            });
            return ids.slice(0, 15);  // 先抓前15条
        }''')
        
        print(f"找到 {len(video_ids)} 条视频")
        
        results = []
        for i, v in enumerate(video_ids):
            print(f"\n[{i+1}/{len(video_ids)}] {v['title']}")
            
            url = f"https://creator.douyin.com/creator-micro/data-center/content/audience?item_id={v['id']}"
            page.goto(url)
            
            profile = extract_audience(page)
            results.append({
                "item_id": v['id'],
                "title": v['title'],
                "audience": profile
            })
            
            print(f"   性别: {profile['gender']}")
            print(f"   年龄: {profile['age']}")
            print(f"   地域: {profile['region']}")
        
        browser.close()
    
    # 保存
    output = {
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(results),
        "videos": results
    }
    
    with open("douyin_audience_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✅ 完成！{len(results)} 条")
    print(f"📁 douyin_audience_data.json")


if __name__ == '__main__':
    if USERNAME == "YOUR_USERNAME":
        print("❌ 请先修改 USERNAME！")
        exit(1)
    main()
