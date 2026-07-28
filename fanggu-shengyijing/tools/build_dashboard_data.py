#!/usr/bin/env python3
"""生成正确的工作台 HTML（含真实 OCR 数据）"""
import json
from pathlib import Path

ROOT = Path("C:/Users/Fann/WorkBuddy/Claw/fanggu-shengyijing")
OCR_DATA = json.loads((ROOT / "data/ocr_consolidated.json").read_text(encoding='utf-8'))
TRANSCRIPT_DATA = {}  # 占位，等待 large-v3 完成

# OCR ID → index ID 映射（基于实际处理结果）
OCR_ID_TO_INDEX = {
    "7658514047214465883": 1,   # 老板过来看看你的行业怎么拍
    "7650441877737027035": 2,   # 老板账号到底怎么实现无脚本拍摄
    "7667181892559772234": 3,   # 老板IP的五个选题
    "7659794056344823241": 4,   # 拍视频就是要放轻松
    "7660163894791720550": 6,   # 你是什么行业的
    "7658237711354804978": 11,  # 创始人IP打造公式
    "7658982392393674698": 12,  # 别对网红抱有滤镜
    "7665324132930708593": 15,  # 老板没想清楚流量
    "7661496914458667594": 16,  # 想有客户过来找你就要学会制造认知差
    "7660017332199212274": 17,  # 想要客户看了视频就来找你
}

# 构建内容数据（结合 OCR 真实数据）
content_records = []

# 19 条记录的索引信息（来自 video-index.md）
INDEX = [
    (1, "2025-08-01", "image", "老板过来看看你的行业怎么拍", "行业实操指导"),
    (2, "2025-08-07", "image", "老板账号到底怎么实现无脚本拍摄？", "方法论体系"),
    (3, "2025-08-08", "image", "老板IP的五个选题，精准获客！", "方法论体系"),
    (4, "2025-09-03", "image", "拍视频就是要放轻松", "心态与人设"),
    (5, "2025-09-13", "video", "代运营摆摊日记", "代运营实战"),
    (6, "2025-09-22", "image", "你是什么行业的？", "行业实操指导"),
    (7, "2025-10-01", "video", "老板们想要让你的作品在你的行业能爆必须遵循新逻辑", "行业实操指导"),
    (8, "2025-10-18", "article", "老板们当下需要的到底是什么？", "心态与人设"),
    (9, "2025-11-27", "video", "抖音改版后的流量机会", "流量与平台认知"),
    (10, "2025-11-30", "video", "为什么你公司拍的视频没有成交？", "避坑与反思"),
    (11, "2025-12-16", "image", "创始人IP打造公式", "方法论体系"),
    (12, "2026-01-12", "image", "别对网红抱有滤镜", "避坑与反思"),
    (13, "2026-02-14", "video", "企二代们要接盘，最大的资产是什么？", "流量与平台认知"),
    (14, "2026-03-05", "video", "一定要出人头地呀各位！", "心态与人设"),
    (15, "2026-04-01", "image", "最近做老板IP做下来发现很多老板没想清楚流量", "方法论体系"),
    (16, "2026-05-22", "image", "想有客户过来找你就要学会制造认知差", "行业实操指导"),
    (17, "2026-05-28", "image", "想要客户看了视频就来找你", "行业实操指导"),
    (18, "2026-06-08", "video", "老板做IP结尾送脚本", "方法论体系"),
    (19, "2026-06-10", "video", "同行拍个狗都能火，为啥我不行？", "避坑与反思"),
]

LINKS = {
    1: "https://v.douyin.com/piAvdg1Jap0/",
    2: "https://v.douyin.com/QywIMO7t5fg/",
    3: "https://v.douyin.com/zvlBZosmWd8/",
    4: "https://v.douyin.com/R1tymTYkTMA/",
    5: "https://v.douyin.com/LrWnkCqjsIo/",
    6: "https://v.douyin.com/zphMQzIQoKk/",
    7: "https://v.douyin.com/RmYi7D7fal8/",
    8: "https://v.douyin.com/aiOl1yJrCSo89",
    9: "https://v.douyin.com/Ro-WIY9sL8o/",
    10: "https://v.douyin.com/oNga4NG4Tdw/",
    11: "https://v.douyin.com/b4P2T5KlOW8/",
    12: "https://v.douyin.com/JWIYJHWmzEo/",
    13: "https://v.douyin.com/0d8dpwQuO9w/",
    14: "https://v.douyin.com/i9SIL6fGCoY/",
    15: "https://v.douyin.com/7ej95QxfgCs/",
    16: "https://v.douyin.com/u9qZTCv6R6Q/",
    17: "https://v.douyin.com/uQj-trnhC_Q/",
    18: "https://v.douyin.com/LpCXCupAWC4/",
    19: "https://v.douyin.com/-q1YdFNXX90/",
}

INDEX_TO_OCR_ID = {v: k for k, v in OCR_ID_TO_INDEX.items()}

for idx, date, type_, title, category in INDEX:
    record = {
        "id": idx,
        "date": date,
        "type": type_,
        "title": title,
        "category": category,
        "link": LINKS[idx],
        "stats": {"digg": 0, "comment": 0, "share": 0, "collect": 0, "play": 0},
        "transcript": None,
        "copy": None,
        "transcriptStatus": "none",
    }

    # 如果是图文且已 OCR
    ocr_id = INDEX_TO_OCR_ID.get(idx)
    if ocr_id and ocr_id in OCR_DATA:
        d = OCR_DATA[ocr_id]
        record["stats"] = d["stats"]
        record["image_count"] = d["image_count"]
        record["transcript"] = d["ocr_text"]
        record["transcriptStatus"] = "done"
        record["copy"] = d["title"]
    elif type_ == "video":
        record["transcriptStatus"] = "none"
        record["copy"] = title
    else:
        record["copy"] = title

    content_records.append(record)

# 保存 JSON 供工作台加载
(ROOT / "data/content_data.json").write_text(
    json.dumps(content_records, ensure_ascii=False, indent=2),
    encoding='utf-8'
)
print(f"✅ 已生成 data/content_data.json（含 {len(content_records)} 条）")
for r in content_records:
    mark = "OCR" if r['transcriptStatus'] == 'done' else "TODO"
    print(f"  #{r['id']:2d} [{r['type']:6s}] {mark} | {r['title'][:30]}")
