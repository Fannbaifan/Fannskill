#!/usr/bin/env python3
"""
将 SiliconFlow SenseVoice 转录结果合并到 content_data.json
用高精度转录替换 Whisper small 的结果
"""
import json, pathlib

BASE = pathlib.Path(__file__).parent.parent

# 读取 content_data.json
with open(BASE / 'data' / 'content_data.json', 'r', encoding='utf-8') as f:
    content_data = json.load(f)

# 读取 SiliconFlow 转录结果
sf_dir = BASE / 'data' / 'transcripts_sf'
updated = 0

if sf_dir.exists():
    for tc_dir in sorted(sf_dir.iterdir()):
        if not tc_dir.is_dir():
            continue
        meta_path = tc_dir / 'metadata.json'
        tc_path = tc_dir / 'transcript.md'
        if not meta_path.exists() or not tc_path.exists():
            print(f"⏳ 跳过 {tc_dir.name} (转录未完成)")
            continue
        
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        sf_title = meta.get('title', '').strip()
        transcript = tc_path.read_text(encoding='utf-8').strip()
        stats = meta.get('stats', {})
        
        # 用标题前缀匹配（前8个字符）
        title_prefix = sf_title[:8] if len(sf_title) >= 8 else sf_title
        
        for record in content_data:
            if record['type'] != 'video':
                continue
            record_title = record.get('title', '').strip()
            record_prefix = record_title[:8] if len(record_title) >= 8 else record_title
            
            if title_prefix == record_prefix:
                old_len = len(record.get('transcript', '') or '')
                old_method = record.get('transcribeMethod', 'whisper_small')
                record['transcript'] = transcript
                record['transcriptStatus'] = 'done'
                record['transcribeMethod'] = 'siliconflow_sensevoice'
                # 更新 stats
                if stats.get('digg_count', 0) > 0:
                    record['stats'] = stats
                updated += 1
                print(f"✅ #{record['id']}: {record_title[:40]}")
                print(f"   {old_method}: {old_len} 字 → SenseVoice: {len(transcript)} 字")
                if old_len > 0:
                    print(f"   字数变化: {len(transcript) - old_len:+d}")
                print(f"   预览: {transcript[:120]}...")
                print()
                break
        else:
            print(f"⚠️ 未匹配: vid={meta.get('video_id')} title={sf_title[:40]}")

# 保存更新后的 content_data.json
with open(BASE / 'data' / 'content_data.json', 'w', encoding='utf-8') as f:
    json.dump(content_data, f, ensure_ascii=False, indent=2)

print(f"\n共更新 {updated} 条视频转录")

# 统计
done_count = sum(1 for r in content_data if r.get('transcriptStatus') == 'done')
total = len(content_data)
print(f"逐字稿完成度: {done_count}/{total}")

# 重新内嵌到 dashboard.html
import re
with open(BASE / 'dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

json_text = json.dumps(content_data, ensure_ascii=False, indent=2)
replacement = 'const CONTENT = ' + json_text + ';\n\nfunction loadData() {\n  // 数据已内嵌到本文件，无需 fetch\n  renderAll();\n}'

pattern = r'const CONTENT = \[[\s\S]*?\];\s*\n\s*function loadData\(\) \{[\s\S]*?\}\s*\}'
new_html, count = re.subn(pattern, lambda m: replacement, html, count=1)
print(f"\nDashboard 内嵌替换: {count}")

if count > 0:
    with open(BASE / 'dashboard.html', 'w', encoding='utf-8', newline='') as f:
        f.write(new_html)
    print(f"dashboard.html 已更新 ({len(new_html):,} bytes)")
else:
    print("⚠️ 未找到替换位置，dashboard.html 未更新")
