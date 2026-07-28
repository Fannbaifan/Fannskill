#!/usr/bin/env python3
"""Merge all video transcripts into content_data.json and add deconstruction."""
import json, pathlib, re
from datetime import datetime

BASE = pathlib.Path(__file__).parent.parent
DATA = BASE / 'data'
TRANSCRIPTS = DATA / 'transcripts'

# Mapping: video_id -> content_data.json id
VIDEO_MAP = {
    '7661967578214853234': 5,   # 代运营摆摊日记
    '7656846152641945481': 7,   # 老板们想要让你的作品在你的行业能爆
    '7651278298823037915': 9,   # 抖音改版后的流量机会 (already has transcript)
    '7654885112240946931': 10,  # 为什么你公司拍的视频没有成交？
    '7643034234999292530': 13,  # 企二代们要接盘
    '7663823275894194011': 14,  # 一定要出人头地呀各位！
    '7666428092697651827': 18,  # 老板做IP结尾送脚本
    '7664563454270984795': 19,  # 同行拍个狗都能火
}

# Read content_data.json
with open(DATA / 'content_data.json', 'r', encoding='utf-8') as f:
    content = json.load(f)

# Update each video record
for vid, cid in VIDEO_MAP.items():
    tc_dir = TRANSCRIPTS / vid
    tc_path = tc_dir / 'transcript.md'
    meta_path = tc_dir / 'metadata.json'
    
    if not tc_path.exists():
        print(f'  SKIP #{cid}: transcript.md not found at {tc_path}')
        continue
    
    transcript = tc_path.read_text(encoding='utf-8').strip()
    
    # Read metadata for stats
    meta = {}
    if meta_path.exists():
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
    
    stats = meta.get('stats', {})
    
    # Find the record
    for r in content:
        if r['id'] == cid:
            old_len = len(r.get('transcript') or '')
            r['transcript'] = transcript
            r['transcriptStatus'] = 'done'
            if stats:
                r['stats'] = {
                    'digg_count': stats.get('digg_count', 0),
                    'comment_count': stats.get('comment_count', 0),
                    'share_count': stats.get('share_count', 0),
                    'collect_count': stats.get('collect_count', 0),
                    'play_count': stats.get('play_count', 0),
                }
            # Update copy from desc if available
            if meta.get('desc') and (not r.get('copy') or r['copy'] == r['title']):
                r['copy'] = meta['desc']
            print(f'  #{cid}: transcript {old_len} -> {len(transcript)} chars, stats: 赞{stats.get("digg_count",0)} 评{stats.get("comment_count",0)} 转{stats.get("share_count",0)} 藏{stats.get("collect_count",0)}')
            break

# Now add deconstruction for all videos that have transcripts but no deconstruction
DECONSTRUCT_MAP = {
    5: {
        "选题角度": "代运营实战——以摆摊日记形式展示代运营能力，用真实场景证明'什么实力什么价格'。",
        "开头钩子": "标题'代运营摆摊日记'+ '什么实力什么价格不用多说了吧'——自信宣言式开场，用结果说话。",
        "内容结构": "实录式——以摆摊现场画面为主，展示代运营的实际操作过程。短视频形式，靠画面和氛围传递信息。",
        "情绪曲线": "好奇（代运营还能摆摊？）→认同（确实有实力）→信任（这价格值）。",
        "转化设计": "展示实力=最好的转化。'什么实力什么价格'直接传递价值主张，评论区'什么价格'形成询价入口。",
        "金句": ["什么实力什么价格不用多说了吧"],
        "数据洞察": "点赞26、评论1、收藏4。评论率低但有人询价，说明精准客户在看。摆摊日记系列适合持续做，每条展示一个实战案例。"
    },
    7: {
        "选题角度": "行业实操指导——讲行业爆款的新逻辑，指出过去的玩法已失效，需要遵循新规则。",
        "开头钩子": "'老板们想要让你的作品在你的行业能爆必须遵循新逻辑'——紧迫感+权威感开场，暗示不听就落后。",
        "内容结构": "观点输出式——从'旧玩法失效'到'新逻辑是什么'的递进。视频形式，口播为主。标注'全程由codex剪辑完成'展示AI工具应用。",
        "情绪曲线": "焦虑（旧玩法失效了？）→求知（新逻辑是什么）→行动（我要调整）。",
        "转化设计": "展示专业认知=建立信任。'codex剪辑'暗示技术能力，吸引想用AI做内容的老板。",
        "金句": ["必须遵循新逻辑", "全程由codex剪辑完成"],
        "数据洞察": "点赞5、转发2、收藏2。数据偏低，可能因为内容偏理论，缺乏具体案例。但'codex剪辑'这个标签有差异化。"
    },
    10: {
        "选题角度": "避坑与反思——直击老板痛点：为什么公司拍的视频没有成交？指出团队在做搞笑段子而非获客内容。",
        "开头钩子": "'显而易见的是你的团队给你做的是搞笑段子，是整蛊'——直接揭短，戳中老板的愤怒点。",
        "内容结构": "诊断式——先指出问题（团队在做错误的内容），再分析原因（搞笑≠获客），给出方向（要做获客内容）。",
        "情绪曲线": "愤怒（我的团队在浪费钱？）→反思（确实没成交）→求变（该怎么调整）。",
        "转化设计": "制造危机感=最好的获客钩子。老板看完会想'我的视频是不是也这样'，进而私信咨询。",
        "金句": ["你的团队给你做的是搞笑段子", "为什么你公司拍的视频没有成交"],
        "数据洞察": "点赞1、转发3。转发率最高（300%），说明老板会转发给团队看。这类'诊断型'内容适合做系列。"
    },
    13: {
        "选题角度": "流量与平台认知——企二代接盘的核心资产问题，切入家族企业传承话题。",
        "开头钩子": "'企二代们要接盘，最大的资产是什么？'——提问式钩子，制造悬念，吸引企二代和创业者。",
        "内容结构": "观点输出式——围绕'最大资产'展开讨论。标签'内容过于真实''万万想不到'暗示反常识答案。",
        "情绪曲线": "好奇（最大资产是什么？）→意外（不是钱？）→认同（确实如此）。",
        "转化设计": "标签'内容过于真实'强化人设。企二代话题天然有话题性，容易引发讨论。",
        "金句": ["企二代们要接盘，最大的资产是什么？"],
        "数据洞察": "点赞4、转发1、收藏1。数据偏低，企二代受众较窄。但话题差异化强，适合做垂直内容。"
    },
    14: {
        "选题角度": "心态与人设——'一定要出人头地'的情绪共鸣内容，激发创业者的拼搏精神。",
        "开头钩子": "'一定要出人头地呀各位！'——情绪宣言式开场，直接点燃共鸣。",
        "内容结构": "情绪输出式——以激励和共鸣为主，标签覆盖'老板''视频拍摄''IP打造'。",
        "情绪曲线": "共鸣→热血→行动。",
        "转化设计": "情绪共鸣型内容，靠人设吸引关注。适合做品牌声量，不直接获客。",
        "金句": ["一定要出人头地呀各位"],
        "数据洞察": "点赞24、收藏4。对于纯情绪内容来说数据不错。收藏4说明有人觉得值得反复看。这类内容适合间隔发布，维持账号活跃度。"
    },
    18: {
        "选题角度": "方法论体系——老板做IP的实操脚本，结尾直接送脚本，制造收藏价值。",
        "开头钩子": "'老板做IP结尾送脚本'——直接承诺价值，'送脚本'三个字就是收藏钩子。",
        "内容结构": "实操输出式——先讲方法论，结尾送现成脚本。标签覆盖'制造业''工厂''短视频运营'，定位精准。",
        "情绪曲线": "期待（要送脚本？）→获取（学到方法论）→满足（拿到脚本了）→行动（马上用）。",
        "转化设计": "'结尾送脚本'=最强收藏引导。制造业/工厂标签精准筛选目标客户。",
        "金句": ["老板做IP结尾送脚本"],
        "数据洞察": "点赞4、收藏3。收藏率75%极高！说明脚本类内容有极强收藏价值。这类'送模板/送脚本'内容应该多做。"
    },
    19: {
        "选题角度": "避坑与反思——解答'同行拍个狗都能火，为啥我不行'的流量焦虑，从内容质量vs推送机制角度破局。",
        "开头钩子": "'同行拍个狗都能火，为啥我不行？'——极度共鸣的吐槽式开场，每个做短视频的人都想过这个问题。",
        "内容结构": "反常识论证——先认同（任何视频都有100万人喜欢），再反转（但平台不会只推你一条），揭示流量分配的本质。",
        "情绪曲线": "共鸣（我也想问）→意外（原来不是质量问题）→理解（是推送机制问题）→行动（该怎么调整）。",
        "转化设计": "制造认知差——'你以为是质量问题，其实是推送机制问题'。这种认知反转天然引发关注和私信。",
        "金句": ["你就算下班随手去拍一张晚霞，也一定会有一百万人喜欢你的照片", "任何一条视频其实都是优质视频"],
        "数据洞察": "点赞2、转发1、收藏1。数据偏低，但内容质量很高。可能因为发布时间较新（7月20日）。这类'反常识'内容有长尾价值。"
    }
}

# Update deconstruction for videos
for cid, deconstruct in DECONSTRUCT_MAP.items():
    for r in content:
        if r['id'] == cid:
            if not r.get('deconstruct'):
                r['deconstruct'] = deconstruct
                r['deconstructStatus'] = 'done'
                print(f'  #{cid}: deconstruction added')
            break

# Also update #9 deconstruct (already had one but with base model transcript)
for r in content:
    if r['id'] == 9:
        r['transcriptNote'] = 'small模型转录'
        break

# Save
with open(DATA / 'content_data.json', 'w', encoding='utf-8') as f:
    json.dump(content, f, ensure_ascii=False, indent=2)

# Summary
done_tc = sum(1 for r in content if r.get('transcript'))
done_dc = sum(1 for r in content if r.get('deconstructStatus') == 'done')
print(f'\n总计: {len(content)} 条内容')
print(f'  有逐字稿/OCR: {done_tc} 条')
print(f'  有内容解构: {done_dc} 条')
print(f'  无内容: {len(content) - done_tc} 条 (第8条链接失效)')
