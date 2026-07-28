#!/usr/bin/env python3
"""批量 OCR 所有图文笔记"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ocr_douyin import ocr_note
from rapidocr_onnxruntime import RapidOCR

NOTES = [
    ("https://v.douyin.com/QywIMO7t5fg/", "老板账号到底怎么实现无脚本拍摄"),
    ("https://v.douyin.com/zvlBZosmWd8/", "老板IP的五个选题"),
    ("https://v.douyin.com/R1tymTYkTMA/", "拍视频就是要放轻松"),
    ("https://v.douyin.com/zphMQzIQoKk/", "你是什么行业的"),
    ("https://v.douyin.com/b4P2T5KlOW8/", "创始人IP打造公式"),
    ("https://v.douyin.com/JWIYJHWmzEo/", "别对网红抱有滤镜"),
    ("https://v.douyin.com/7ej95QxfgCs/", "老板没想清楚流量"),
    ("https://v.douyin.com/u9qZTCv6R6Q/", "想有客户过来找你就要学会制造认知差"),
    ("https://v.douyin.com/uQj-trnhC_Q/", "想要客户看了视频就来找你"),
]

print("加载 OCR 模型...")
engine = RapidOCR()
print(f"✅ OCR 引擎就绪\n")

output_dir = Path("./data/ocr")
output_dir.mkdir(parents=True, exist_ok=True)

results = []
for i, (url, title) in enumerate(NOTES, 1):
    print(f"\n[{i}/{len(NOTES)}] 处理: {title}")
    try:
        result = ocr_note(url, output_dir, engine)
        results.append(result)
    except Exception as e:
        print(f"❌ 失败: {e}")

print(f"\n{'='*60}")
print(f"✅ 批量完成，共成功 {len(results)}/{len(NOTES)} 条")
print(f"   输出目录: {output_dir}")
