#!/usr/bin/env python3
"""
抖音创作者中心 - 观众画像 + 导出数据抓取 v5
路径已写死，无需修改
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import json, time, re, os, glob

# ============================================================
# 路径已写死，无需修改
# ============================================================
USER_DATA_DIR = r"D:\HuaweiMoveData\Users\Fann\AppData\Local\Microsoft\Edge\User Data"
DOWNLOAD_DIR = r"D:\HuaweiMoveData\Users\Fann\Downloads"


def safe_goto(page, url, timeout=60000):
    for attempt in range(3):
        try:
            print(f"  导航... (尝试 {attempt+1}/3)")
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            return True
        except PlaywrightTimeout:
            print(f"  超时，重试...")
            time.sleep(2)
    return False


def click_tab_and_wait(page):
    """点击投稿列表标签并等待加载"""
    print("  尝试点击「投稿列表」...")
    
    # 等待标签出现
    for _ in range(10):
        try:
            # 用文本定位
            page.click('text=投稿列表', timeout=2000)
            print("  ✓ 已点击「投稿列表」")
            break
        except:
            time.sleep(1)
    
    # 等待列表加载（等页面上出现 item_id 链接）
    print("  等待列表加载...")
    for _ in range(15):
        has_items = page.evaluate('''() => {
            return document.querySelectorAll('a[href*="item_id="]').length > 0;
        }''')
        if has_items:
            print("  ✓ 列表已加载")
            return True
        time.sleep(1)
    
    print("  ⚠ 列表未加载")
    return False


def get_video_list(page):
    """获取视频列表"""
    return page.evaluate('''() => {
        const ids = [];
        document.querySelectorAll('a[href*="item_id="]').forEach(a => {
            const m = a.href.match(/item_id=(\\d+)/);
            if (m && !ids.find(x => x.id === m[1])) {
                ids.push({id: m[1], title: a.textContent.trim().slice(0,80)});
            }
        });
        return ids;
    }''')


def extract_audience(page):
    """提取观众画像"""
    page.wait_for_timeout(4000)
    
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


def click_export_and_parse(page):
    """点击导出数据并解析下载的文件"""
    print("  尝试点击「导出数据」...")
    
    # 清理旧的下载文件
    for f in glob.glob(os.path.join(DOWNLOAD_DIR, "作品列表*")):
        try:
            os.remove(f)
            print(f"  清理旧文件: {f}")
        except:
            pass
    
    # 点击导出按钮
    clicked = False
    for _ in range(5):
        try:
            page.click('text=导出数据', timeout=3000)
            print("  ✓ 已点击「导出数据」")
            clicked = True
            break
        except:
            time.sleep(1)
    
    if not clicked:
        print("  ⚠ 未找到导出按钮")
        return None
    
    # 等待下载完成
    print("  等待下载...")
    for _ in range(30):
        files = glob.glob(os.path.join(DOWNLOAD_DIR, "作品列表*"))
        if files:
            filepath = files[0]
            print(f"  ✓ 下载完成: {os.path.basename(filepath)}")
            
            # 解析文件
            import pandas as pd
            try:
                if filepath.endswith('.xlsx'):
                    df = pd.read_excel(filepath)
                else:
                    df = pd.read_csv(filepath)
                
                # 提取汇总数据
                total_play = df['播放量'].sum() if '播放量' in df.columns else 0
                total_like = df['点赞量'].sum() if '点赞量' in df.columns else 0
                total_comment = df['评论量'].sum() if '评论量' in df.columns else 0
                total_share = df['分享量'].sum() if '分享量' in df.columns else 0
                total_collect = df['收藏量'].sum() if '收藏量' in df.columns else 0
                
                return {
                    "file": os.path.basename(filepath),
                    "total_play": int(total_play),
                    "total_like": int(total_like),
                    "total_comment": int(total_comment),
                    "total_share": int(total_share),
                    "total_collect": int(total_collect),
                    "items_count": len(df)
                }
            except Exception as e:
                print(f"  解析失败: {e}")
                return {"file": os.path.basename(filepath), "error": str(e)}
        
        time.sleep(1)
    
    print("  ⚠ 下载超时")
    return None


def main():
    print("=" * 50)
    print("抖音数据抓取 v5")
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
        print("\n检查登录状态...")
        if not safe_goto(page, "https://creator.douyin.com/"):
            print("❌ 无法打开页面")
            browser.close()
            return
        
        url = page.url
        if "login" in url.lower() or "passport" in url.lower():
            print("\n⚠️ 未登录！请在浏览器中扫码登录，然后按回车继续")
            input("按回车继续...")
            page.reload()
            page.wait_for_timeout(3000)
        
        print("✅ 已登录")
        
        # 进入作品分析
        print("\n进入作品分析...")
        if not safe_goto(page, "https://creator.douyin.com/creator-micro/data-center/content"):
            print("❌ 失败")
            browser.close()
            return
        
        # 点击投稿列表
        if not click_tab_and_wait(page):
            print("❌ 无法加载列表")
            browser.close()
            return
        
        # 获取视频列表
        video_ids = get_video_list(page)
        print(f"\n找到 {len(video_ids)} 条视频")
        
        # 导出数据
        print("\n导出数据...")
        export_data = click_export_and_parse(page)
        if export_data:
            print(f"  总播放: {export_data.get('total_play', 0):,}")
            print(f"  总点赞: {export_data.get('total_like', 0):,}")
            print(f"  总评论: {export_data.get('total_comment', 0):,}")
        
        # 抓取观众画像
        print("\n抓取观众画像...")
        results = []
        for i, v in enumerate(video_ids[:15]):  # 先抓前15条
            print(f"\n[{i+1}/{min(len(video_ids),15)}] {v['title'][:50]}")
            
            url = f"https://creator.douyin.com/creator-micro/data-center/content/audience?item_id={v['id']}"
            if safe_goto(page, url, timeout=45000):
                profile = extract_audience(page)
                results.append({"item_id": v['id'], "title": v['title'], "audience": profile})
                print(f"   性别: {profile['gender']}")
                print(f"   年龄: {profile['age']}")
            else:
                print("   超时")
        
        browser.close()
    
    # 保存结果
    output = {
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "export_data": export_data,
        "total_videos": len(video_ids),
        "audience_count": len(results),
        "videos": results
    }
    
    with open("douyin_audience_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✅ 完成！")
    print(f"   导出数据: {'✓' if export_data else '✗'}")
    print(f"   观众画像: {len(results)} 条")
    print(f"   文件: douyin_audience_data.json")


if __name__ == '__main__':
    main()
