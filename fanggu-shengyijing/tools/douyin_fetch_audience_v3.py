#!/usr/bin/env python3
"""
抖音创作者中心 - 观众画像 DOM 抓取 v3
修复超时问题，增加重试和更长的等待时间
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import json, time, re, os

USERNAME = "YOUR_USERNAME"
USER_DATA_DIR = rf"C:\Users\{USERNAME}\AppData\Local\Microsoft\Edge\User Data"


def kill_edge():
    print("正在关闭 Edge 进程...")
    os.system('taskkill /F /IM msedge.exe 2>nul')
    time.sleep(3)


def safe_goto(page, url, timeout=60000):
    """带重试的页面导航"""
    for attempt in range(3):
        try:
            print(f"  导航到 {url[:60]}... (尝试 {attempt+1}/3)")
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            return True
        except PlaywrightTimeout:
            print(f"  超时，重试...")
            time.sleep(2)
    return False


def extract_audience(page):
    """从观众分析页面提取数据"""
    page.wait_for_timeout(4000)
    
    texts = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('body *'))
            .map(el => el.textContent.trim())
            .filter(t => t.length > 0 && t.length < 50);
    }''')
    
    gender = {}
    age = {}
    region = {}
    
    for text in texts:
        m = re.search(r'(男|女)\s*(\d+(?:\.\d+)?)\s*%', text)
        if m:
            key = 'male' if m.group(1) == '男' else 'female'
            gender[key] = float(m.group(2))
        
        m = re.match(r'^(\d+[-+]\d+|\d+\+|[\u4e00-\u9fff]+)\s*(\d+(?:\.\d+)?)\s*%$', text)
        if m:
            age[m.group(1)] = float(m.group(2))
        
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
    }


def main():
    kill_edge()
    
    with sync_playwright() as p:
        print("启动 Edge...")
        
        try:
            browser = p.chromium.launch_persistent_context(
                USER_DATA_DIR,
                channel="msedge",
                headless=False,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
                viewport={"width": 1440, "height": 900}
            )
        except Exception as e:
            print(f"msedge 启动失败: {e}")
            print("尝试 chromium...")
            browser = p.chromium.launch_persistent_context(
                USER_DATA_DIR,
                headless=False,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
                viewport={"width": 1440, "height": 900}
            )
        
        page = browser.new_page()
        
        # 先到首页确认登录状态
        print("访问创作者中心首页...")
        if not safe_goto(page, "https://creator.douyin.com/"):
            print("❌ 无法打开页面，请检查网络")
            browser.close()
            return
        
        print(f"当前页面: {page.title()}")
        
        # 再到作品分析
        print("导航到作品分析...")
        if not safe_goto(page, "https://creator.douyin.com/creator-micro/data-center/content"):
            print("❌ 无法打开作品分析")
            browser.close()
            return
        
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
            return ids.slice(0, 15);
        }''')
        
        print(f"找到 {len(video_ids)} 条视频")
        
        if not video_ids:
            print("⚠️ 没有找到视频，可能未登录或页面结构不同")
            page.screenshot(path="debug_no_videos.png")
            print("已截图 debug_no_videos.png")
            browser.close()
            return
        
        results = []
        for i, v in enumerate(video_ids):
            print(f"\n[{i+1}/{len(video_ids)}] {v['title']}")
            
            url = f"https://creator.douyin.com/creator-micro/data-center/content/audience?item_id={v['id']}"
            if not safe_goto(page, url, timeout=45000):
                print("   ⚠️ 打开观众分析超时，跳过")
                continue
            
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
    print(f"\n📤 请把文件发给我")


if __name__ == '__main__':
    if USERNAME == "YOUR_USERNAME":
        print("❌ 请先修改 USERNAME = 'Fann'")
        exit(1)
    main()
