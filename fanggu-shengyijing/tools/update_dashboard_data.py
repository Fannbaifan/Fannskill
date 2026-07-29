#!/usr/bin/env python3
"""更新 dashboard 数据文件
用法: python update_dashboard_data.py
从 content_data.json 生成 dashboard-data.js
"""
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).parent.parent
DATA_JSON = ROOT / "data" / "content_data.json"
DATA_JS = ROOT / "dashboard-data.js"


def make_content_json(item):
    """将 content_data.json 条目转为 dashboard 内嵌格式"""
    s = item.get('stats', {})
    return {
        "id": item['id'],
        "date": item.get('source_date', item.get('date', ''))[:10],
        "type": item.get('type', 'image'),
        "title": item.get('title', ''),
        "category": item.get('category', '待分类'),
        "link": item.get('link', ''),
        "transcript": item.get('transcript', ''),
        "transcriptStatus": item.get('transcript_status', ''),
        "copy": item.get('copy', ''),
        "stats": {
            "digg_count": s.get('digg_count', 0),
            "comment_count": s.get('comment_count', 0),
            "share_count": s.get('share_count', 0),
            "collect_count": s.get('collect_count', 0),
            "play_count": s.get('play_count', 0),
            "completion_rate": s.get('completion_rate'),
            "s5_completion_rate": s.get('s5_completion_rate'),
            "click_rate": s.get('click_rate'),
            "s2_bounce_rate": s.get('s2_bounce_rate'),
            "avg_play_duration": s.get('avg_play_duration'),
            "homepage_visits": s.get('homepage_visits', 0),
            "follower_gain": s.get('follower_gain', 0),
        },
        "deconstruction": item.get('deconstruction', {}),
        "content_type_douyin": item.get('content_type_douyin', ''),
        "audit_status": item.get('audit_status', ''),
    }


def main():
    data = json.loads(DATA_JSON.read_text(encoding='utf-8'))
    content = [make_content_json(c) for c in data]

    js = (
        '// 反骨生意经 · 内容数据\n'
        '// 自动生成，请勿手动编辑\n'
        f'// 生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}\n'
        f'// 内容条目: {len(content)}\n'
        'const CONTENT = ' + json.dumps(content, ensure_ascii=False, indent=2) + ';\n'
    )

    DATA_JS.write_text(js, encoding='utf-8')

    # JS 语法验证
    r = subprocess.run(
        ['node', '--check', str(DATA_JS)],
        capture_output=True, text=True, timeout=10
    )
    if r.returncode != 0:
        print(f"❌ 语法错误: {r.stderr[:200]}")
        return 1

    print(f"✅ dashboard-data.js 已更新 ({len(content)} 条)")
    print(f"   总播放: {sum(c['stats']['play_count'] for c in content):,}")
    print(f"   总点赞: {sum(c['stats']['digg_count'] for c in content):,}")
    return 0


if __name__ == '__main__':
    exit(main())
