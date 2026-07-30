#!/usr/bin/env python3
"""
抖音创作者中心 - 观众画像 DOM 抓取 v4
不强制关闭 Edge，检测登录状态，未登录时提示手动扫码
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import json, time, re, os

USERNAME = "YOUR_USERNAME"
USER_DATA_DIR = rf"C:\Users\{USERNAME}\AppData\Local\Microsoft\Edge\User Data"


def safe_goto(page, url, timeout=60000):
    for attempt in range(3):
        try:
            print(f"  导航到 {url[:70]}... (尝试 {attempt+1}/3)")
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            return True
        except PlaywrightTimeout:
            print(f"  超时，重试...")
            time.sleep(2)
    return False


def check_login(page):
    """检查是否已登录"""
    url = page.url
    title = page.title()
    print(f"  当前页面: {title}")
    print(f"  URL: {url[:80]}")
    
    # 如果跳转到登录页或 passport 页，说明未登录
    if "login" in url.lower() or "passport" in url.lower():
        return False
    
    # 检查页面上是否有登录相关的元素
    login_text = page.evaluate('''() => {
        const body = document.body.innerText;
        return body.includes("登录") || body.includes("扫码") || body.includes("手机号");
    }''')
    
    if login_text:
        return False
    
    return True


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
    print("=" * 50)
    print("抖音观众画像抓取 v4")
    print("=" * 50)
    print(f"用户数据目录: {USER_DATA_DIR}")
    print()
    
    with sync_playwright() as p:
        print("启动 Edge（复用现有登录态）...")
        
        try:
            browser = p.chromium.launch_persistent_context(
                USER_DATA_DIR,
                channel="msedge",
                headless=False,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
                viewport={"width": 1440, "height": 900}
            )
        except Exception as e:
            print(f"启动失败: {e}")
            print("尝试 chromium...")
            browser = p.chromium.launch_persistent_context(
                USER_DATA_DIR,
                headless=False,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
                viewport={"width": 1440, "height": 900}
            )
        
        page = browser.new_page()
        
        # ========== 检查登录状态 ==========
        print("\n检查登录状态...")
        if not safe_goto(page, "https://creator.douyin.com/"):
            print("❌ 无法打开页面")
            browser.close()
            return
        
        if not check_login(page):
            print("\n" + "=" * 50)
            print("⚠️  未检测到登录状态！")
            print("=" * 50)
            print("请在新打开的 Edge 浏览器窗口中：")
            print("  1. 扫码登录抖音创作者中心")
            print("  2. 登录完成后，回到这个终端窗口")
            print("  3. 按回车键继续")
            print("=" * 50)
            input("按回车继续...")
            
            # 重新检查
            page.reload()
            page.wait_for_timeout(3000)
            if not check_login(page):
                print("❌ 仍未登录，请确认已扫码登录后重新运行脚本")
                browser.close()
                return
        
        print("✅ 已登录！")
        
        # ========== 获取视频列表 ==========
        print("\n导航到作品分析...")
        if not safe_goto(page, "https://creator.douyin.com/creator-micro/data-center/content"):
            print("❌ 无法打开作品分析")
            browser.close()
            return
        
        print("获取视频列表...")
        
        # 先尝试点击「投稿列表」标签
        try:
            # 尝试多种选择器
            tab_selectors = [
                'text=投稿列表',
                '[class*="tab"]:has-text("投稿列表")',
                'button:has-text("投稿列表")',
                'div:has-text("投稿列表")',
            ]
            for sel in tab_selectors:
                try:
                    page.click(sel, timeout=3000)
                    print(f"  已点击「投稿列表」")
                    page.wait_for_timeout(3000)
                    break
                except:
                    continue
        except:
            print("  未找到「投稿列表」标签，尝试直接获取...")
        
        video_ids = page.evaluate('''() => {
            const ids = [];
            document.querySelectorAll('a[href*="item_id="]').forEach(a => {
                const m = a.href.match(/item_id=(\d+)/);
                if (m && !ids.find(x => x.id === m[1])) {
                    ids.push({id: m[1], title: a.textContent.trim().slice(0,80)});
                }
            });
            return ids.slice(0, 20);
        }''')
        
        print(f"找到 {len(video_ids)} 条视频")
        
        if not video_ids:
            print("⚠️ 没有找到视频")
            page.screenshot(path="debug_no_videos.png")
            print("已截图 debug_no_videos.png")
            browser.close()
            return
        
        # ========== 抓取观众画像 ==========
        results = []
        for i, v in enumerate(video_ids):
            print(f"\n[{i+1}/{len(video_ids)}] {v['title']}")
            
            url = f"https://creator.douyin.com/creator-micro/data-center/content/audience?item_id={v['id']}"
            if not safe_goto(page, url, timeout=45000):
                print("   ⚠️ 超时，跳过")
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
    
    # ========== 保存结果 ==========
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
