#!/usr/bin/env python3
"""
抖音数据常驻服务 - 本地后台运行，暴露 HTTP API
双击运行后长期待命，Workbuddy 通过 HTTP 请求调用

启动: python server.py
端口: 5000

API:
  GET /get_data          → 获取所有视频列表+数据
  GET /get_audience      → 获取所有视频的观众画像
  GET /get_audience/<id> → 获取指定视频的观众画像
  GET /health            → 健康检查
"""
from flask import Flask, jsonify, request
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import json, time, re, os, threading, atexit

app = Flask(__name__)

# ============================================================
# 配置 - 修改这里的用户名
# ============================================================
USERNAME = "Fann"
USER_DATA_DIR = rf"C:\Users\{USERNAME}\AppData\Local\Microsoft\Edge\User Data"

# 浏览器实例（单例）
_browser = None
_page = None
_lock = threading.Lock()


def kill_edge():
    os.system('taskkill /F /IM msedge.exe 2>nul')
    time.sleep(3)


def get_browser():
    global _browser, _page
    if _browser is None:
        with _lock:
            if _browser is None:
                kill_edge()
                pw = sync_playwright().start()
                _browser = pw.chromium.launch_persistent_context(
                    USER_DATA_DIR,
                    channel="msedge",
                    headless=False,
                    args=["--no-sandbox", "--disable-setuid-sandbox"],
                    viewport={"width": 1440, "height": 900}
                )
                _page = _browser.new_page()
    return _browser, _page


def safe_goto(page, url, timeout=60000):
    for attempt in range(3):
        try:
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            return True
        except PlaywrightTimeout:
            print(f"超时，重试 {attempt+1}/3...")
            time.sleep(2)
    return False


def extract_audience_from_page(page):
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


# ======================== API 路由 ========================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "douyin-data-service", "version": "1.0"})


@app.route('/get_data', methods=['GET'])
def get_data():
    """获取全部视频列表和数据"""
    try:
        browser, page = get_browser()
        
        if not safe_goto(page, "https://creator.douyin.com/"):
            return jsonify({"status": "error", "message": "无法打开创作者中心"}), 500
        
        if not safe_goto(page, "https://creator.douyin.com/creator-micro/data-center/content"):
            return jsonify({"status": "error", "message": "无法打开作品分析"}), 500
        
        video_ids = page.evaluate('''() => {
            const ids = [];
            document.querySelectorAll('a[href*="item_id="]').forEach(a => {
                const m = a.href.match(/item_id=(\d+)/);
                if (m && !ids.find(x => x.id === m[1])) {
                    ids.push({id: m[1], title: a.textContent.trim().slice(0,80)});
                }
            });
            return ids;
        }''')
        
        return jsonify({
            "status": "success",
            "total": len(video_ids),
            "videos": video_ids
        })
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/get_audience', methods=['GET'])
def get_all_audience():
    """获取所有视频的观众画像"""
    try:
        browser, page = get_browser()
        
        if not safe_goto(page, "https://creator.douyin.com/creator-micro/data-center/content"):
            return jsonify({"status": "error", "message": "无法打开作品分析"}), 500
        
        video_ids = page.evaluate('''() => {
            const ids = [];
            document.querySelectorAll('a[href*="item_id="]').forEach(a => {
                const m = a.href.match(/item_id=(\d+)/);
                if (m && !ids.find(x => x.id === m[1])) {
                    ids.push({id: m[1], title: a.textContent.trim().slice(0,80)});
                }
            });
            return ids;
        }''')
        
        results = []
        for v in video_ids:
            url = f"https://creator.douyin.com/creator-micro/data-center/content/audience?item_id={v['id']}"
            if safe_goto(page, url, timeout=45000):
                profile = extract_audience_from_page(page)
                results.append({
                    "item_id": v['id'],
                    "title": v['title'],
                    "audience": profile
                })
            else:
                results.append({
                    "item_id": v['id'],
                    "title": v['title'],
                    "audience": {"error": "timeout"}
                })
        
        return jsonify({
            "status": "success",
            "total": len(results),
            "videos": results
        })
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/get_audience/<item_id>', methods=['GET'])
def get_single_audience(item_id):
    """获取指定视频的观众画像"""
    try:
        browser, page = get_browser()
        url = f"https://creator.douyin.com/creator-micro/data-center/content/audience?item_id={item_id}"
        
        if not safe_goto(page, url, timeout=45000):
            return jsonify({"status": "error", "message": "超时"}), 500
        
        profile = extract_audience_from_page(page)
        return jsonify({"status": "success", "item_id": item_id, "audience": profile})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/get_full_report', methods=['GET'])
def get_full_report():
    """获取完整报告：视频列表 + 每条视频的观众画像"""
    try:
        browser, page = get_browser()
        
        if not safe_goto(page, "https://creator.douyin.com/creator-micro/data-center/content"):
            return jsonify({"status": "error", "message": "无法打开作品分析"}), 500
        
        video_ids = page.evaluate('''() => {
            const ids = [];
            document.querySelectorAll('a[href*="item_id="]').forEach(a => {
                const m = a.href.match(/item_id=(\d+)/);
                if (m && !ids.find(x => x.id === m[1])) {
                    ids.push({id: m[1], title: a.textContent.trim().slice(0,80)});
                }
            });
            return ids;
        }''')
        
        results = []
        total = len(video_ids)
        
        for i, v in enumerate(video_ids):
            url = f"https://creator.douyin.com/creator-micro/data-center/content/audience?item_id={v['id']}"
            if safe_goto(page, url, timeout=45000):
                profile = extract_audience_from_page(page)
                results.append({
                    "item_id": v['id'],
                    "title": v['title'],
                    "audience": profile
                })
                print(f"[{i+1}/{total}] {v['title'][:40]} - 性别:{profile['gender']} 年龄:{profile['age']}")
            else:
                results.append({
                    "item_id": v['id'],
                    "title": v['title'],
                    "audience": {"error": "timeout"}
                })
        
        # 保存到本地文件
        report = {
            "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(results),
            "videos": results
        }
        with open("douyin_audience_data.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return jsonify({"status": "success", "total": len(results), "videos": results, "saved_to": "douyin_audience_data.json"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/shutdown', methods=['POST'])
def shutdown():
    """关闭服务"""
    global _browser
    if _browser:
        _browser.close()
        _browser = None
    os._exit(0)


def cleanup():
    global _browser
    if _browser:
        _browser.close()


atexit.register(cleanup)


if __name__ == '__main__':
    print("=" * 50)
    print("抖音数据常驻服务 v1.0")
    print("=" * 50)
    print(f"端口: 5000")
    print(f"用户: {USERNAME}")
    print()
    print("API 列表:")
    print("  GET http://127.0.0.1:5000/get_data          - 视频列表+数据")
    print("  GET http://127.0.0.1:5000/get_audience       - 全部观众画像")
    print("  GET http://127.0.0.1:5000/get_audience/<id>   - 单条画像")
    print("  GET http://127.0.0.1:5000/get_full_report     - 完整报告")
    print("  GET http://127.0.0.1:5000/health              - 健康检查")
    print()
    print("双击本文件即可启动，或在终端运行: python server.py")
    print()
    
    app.run(port=5000, host='127.0.0.1', debug=False)
