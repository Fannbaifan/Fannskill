#!/usr/bin/env python3
"""
抖音创作者中心 - 观众画像 + 导出数据抓取 v7
使用 expect_download 接管下载，从页面文本抓取视频列表
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import json, time, re, os

USER_DATA_DIR = r"D:\HuaweiMoveData\Users\Fann\AppData\Local\Microsoft\Edge\User Data"
DOWNLOAD_DIR = r"D:\HuaweiMoveData\Users\Fann\Downloads"


def safe_goto(page, url, timeout=60000):
    for attempt in range(3):
        try:
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            return True
        except PlaywrightTimeout:
            time.sleep(2)
    return False


def extract_audience(page):
    """从观众分析页面提取数据"""
    page.wait_for_timeout(3000)
    
    texts = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('body *'))
            .map(el => el.textContent.trim())
            .filter(t => t.length > 0 && t.length < 50);
    }''')
    
    gender, age, region = {}, {}, {}
    
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
    
    return {"gender": gender, "age": age, "region": dict(sorted(region.items(), key=lambda x: -x[1])[:5])}


def click_export_with_download(page):
    """使用 expect_download 点击导出并保存文件"""
    print("  点击导出数据...")
    
    try:
        with page.expect_download(timeout=30000) as download_info:
            page.click('text=导出数据', timeout=5000)
        
        download = download_info.value
        filepath = os.path.join(DOWNLOAD_DIR, "douyin_export.xlsx")
        download.save_as(filepath)
        print(f"  ✓ 已保存: {filepath}")
        
        # 解析
        import pandas as pd
        df = pd.read_excel(filepath)
        
        return {
            "file": "douyin_export.xlsx",
            "total_play": int(df['播放量'].sum()) if '播放量' in df.columns else 0,
            "total_like": int(df['点赞量'].sum()) if '点赞量' in df.columns else 0,
            "total_comment": int(df['评论量'].sum()) if '评论量' in df.columns else 0,
            "total_share": int(df['分享量'].sum()) if '分享量' in df.columns else 0,
            "total_collect": int(df['收藏量'].sum()) if '收藏量' in df.columns else 0,
            "items_count": len(df)
        }
    
    except Exception as e:
        print(f"  ⚠ 导出失败: {e}")
        return None


def get_videos_from_page(page):
    """从页面文本抓取视频列表（不依赖 item_id 链接）"""
    print("  从页面抓取视频...")
    
    # 获取页面上所有文本
    all_texts = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('body *'))
            .map(el => el.textContent.trim())
            .filter(t => t.length > 5 && t.length < 200);
    }''')
    
    # 找包含 # 号的文本（通常是视频标题）
    videos = []
    seen = set()
    for text in all_texts:
        if '#' in text and text not in seen:
            seen.add(text)
            videos.append({"title": text[:100], "index": len(videos)})
    
    return videos[:20]


def fetch_single_audience(page, video_index):
    """抓取单条视频的观众画像"""
    try:
        # 回到投稿列表
        if not safe_goto(page, "https://creator.douyin.com/creator-micro/data-center/content"):
            return None
        
        # 点击投稿列表标签
        for _ in range(5):
            try:
                page.click('text=投稿列表', timeout=2000)
                break
            except:
                time.sleep(1)
        
        page.wait_for_timeout(3000)
        
        # 点击第 video_index 条视频的「分析详情」
        # 尝试找到所有包含"分析详情"的按钮/链接
        detail_links = page.query_selector_all('text=分析详情')
        if video_index < len(detail_links):
            detail_links[video_index].click()
            page.wait_for_timeout(3000)
        else:
            return None
        
        # 点击「观众分析」标签
        for _ in range(5):
            try:
                page.click('text=观众分析', timeout=2000)
                print("    已点击观众分析")
                break
            except:
                time.sleep(1)
        
        # 滚动触发图表加载
        page.mouse.wheel(0, 500)
        page.wait_for_timeout(2000)
        page.mouse.wheel(0, 500)
        page.wait_for_timeout(2000)
        
        return extract_audience(page)
    
    except Exception as e:
        print(f"    错误: {e}")
        return None


def main():
    print("=" * 50)
    print("抖音数据抓取 v7")
    print("=" * 50)
    
    with sync_playwright() as p:
        print("\n启动 Edge...")
        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            channel="msedge",
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
            viewport={"width": 1440, "height": 900}
        )
        page = browser.new_page()
        
        # 登录检查
        print("\n检查登录...")
        if not safe_goto(page, "https://creator.douyin.com/"):
            print("❌ 无法打开")
            browser.close()
            return
        
        if "login" in page.url.lower():
            print("⚠️ 请扫码登录，按回车继续")
            input()
            page.reload()
            page.wait_for_timeout(3000)
        
        print("✅ 已登录")
        
        # 进入作品分析
        print("\n进入作品分析...")
        safe_goto(page, "https://creator.douyin.com/creator-micro/data-center/content")
        
        # 点击投稿列表
        print("\n点击投稿列表...")
        for _ in range(10):
            try:
                page.click('text=投稿列表', timeout=2000)
                print("  ✓ 已点击")
                break
            except:
                time.sleep(1)
        
        page.wait_for_timeout(4000)
        
        # 导出数据
        print("\n导出数据...")
        export_data = click_export_with_download(page)
        if export_data:
            print(f"  总播放: {export_data.get('total_play', 0):,}")
        
        # 获取视频列表
        print("\n获取视频列表...")
        videos = get_videos_from_page(page)
        print(f"  找到 {len(videos)} 条")
        
        # 抓取观众画像
        print("\n抓取观众画像...")
        results = []
        for i, v in enumerate(videos[:10]):
            print(f"\n[{i+1}/{min(len(videos),10)}] {v['title'][:50]}")
            
            profile = fetch_single_audience(page, i)
            if profile:
                results.append({"title": v['title'], "audience": profile})
                print(f"   性别: {profile['gender']}")
                print(f"   年龄: {profile['age']}")
            else:
                print("   跳过")
        
        browser.close()
    
    # 保存
    output = {
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "export_data": export_data,
        "total_videos": len(videos),
        "audience_count": len(results),
        "videos": results
    }
    
    with open("douyin_audience_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✅ 完成！")
    print(f"   导出: {'✓' if export_data else '✗'}")
    print(f"   画像: {len(results)} 条")
    print(f"   文件: douyin_audience_data.json")


if __name__ == '__main__':
    main()
