#!/usr/bin/env python3
"""
抖音视频逐字稿提取工具

功能：
1. 从抖音分享链接下载无水印视频
2. 提取音频
3. 使用 faster-whisper 本地转录（无需 API Key）

用法：
  python transcribe_douyin.py "https://v.douyin.com/xxxxx/" -o ./output
  python transcribe_douyin.py --batch links.txt -o ./output
"""

import os
import re
import sys
import json
import shutil
import tempfile
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

import requests
import imageio_ffmpeg

# 获取 ffmpeg 可执行文件路径
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/121.0.2277.107 Version/17.0 Mobile/15E148 Safari/604.1'
}


def parse_share_url(share_text: str) -> dict:
    """从分享文本中提取无水印视频链接和信息"""
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', share_text)
    if not urls:
        raise ValueError("未找到有效的分享链接")

    share_url = urls[0]
    share_response = requests.get(share_url, headers=HEADERS, allow_redirects=True)
    video_id = share_response.url.split("?")[0].strip("/").split("/")[-1]

    # 判断是视频还是图文
    if "note" in share_response.url or "image" in share_response.url:
        share_url = f'https://www.iesdouyin.com/share/note/{video_id}'
        content_type = "note"
    else:
        share_url = f'https://www.iesdouyin.com/share/video/{video_id}'
        content_type = "video"

    response = requests.get(share_url, headers=HEADERS)
    response.raise_for_status()

    pattern = re.compile(
        pattern=r"window\._ROUTER_DATA\s*=\s*(.*?)</script>",
        flags=re.DOTALL,
    )
    find_res = pattern.search(response.text)

    if not find_res or not find_res.group(1):
        raise ValueError("从HTML中解析视频信息失败")

    json_data = json.loads(find_res.group(1).strip())
    VIDEO_ID_PAGE_KEY = "video_(id)/page"
    NOTE_ID_PAGE_KEY = "note_(id)/page"

    original_video_info = None
    content_type = "video"

    loader_data = json_data.get("loaderData", {})
    if loader_data.get(VIDEO_ID_PAGE_KEY):
        original_video_info = loader_data[VIDEO_ID_PAGE_KEY].get("videoInfoRes")
        content_type = "video"
    elif loader_data.get(NOTE_ID_PAGE_KEY):
        original_video_info = loader_data[NOTE_ID_PAGE_KEY].get("videoInfoRes")
        content_type = "note"

    if not original_video_info:
        raise Exception("无法从JSON中解析视频或图集信息")

    data = original_video_info["item_list"][0]

    # 获取视频/图文信息
    desc = data.get("desc", "").strip() or f"douyin_{video_id}"
    desc = re.sub(r'[\\/:*?"<>|]', '_', desc)

    result = {
        "title": desc,
        "video_id": video_id,
        "content_type": content_type,
        "url": None,
        "images": [],
    }

    if content_type == "video" and "video" in data:
        video_url = data["video"]["play_addr"]["url_list"][0].replace("playwm", "play")
        result["url"] = video_url
    elif content_type == "note":
        # 图文作品，提取图片URL
        if "images" in data:
            for img in data["images"]:
                if "url_list" in img and img["url_list"]:
                    result["images"].append(img["url_list"][0])

    # 提取统计数据
    stats = data.get("statistics", {})
    result["stats"] = {
        "digg_count": stats.get("digg_count", 0),
        "comment_count": stats.get("comment_count", 0),
        "share_count": stats.get("share_count", 0),
        "collect_count": stats.get("collect_count", 0),
        "play_count": stats.get("play_count", 0),
    }

    # 提取作者信息
    author = data.get("author", {})
    result["author"] = {
        "nickname": author.get("nickname", ""),
        "sec_uid": author.get("sec_uid", ""),
    }

    # 提取创建时间
    create_time = data.get("create_time", 0)
    if create_time:
        result["create_time"] = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M:%S")
    else:
        result["create_time"] = ""

    # 提取标签
    text_extra = data.get("text_extra", [])
    tags = []
    for item in text_extra:
        if item.get("hashtag_name"):
            tags.append(item["hashtag_name"])
    result["tags"] = tags

    return result


def download_video(video_info: dict, output_dir: Path) -> Path:
    """下载视频文件"""
    if not video_info.get("url"):
        raise ValueError("没有视频下载链接（可能是图文作品）")

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{video_info['video_id']}.mp4"
    filepath = output_dir / filename

    print(f"  正在下载视频: {video_info['title']}")

    response = requests.get(video_info['url'], headers=HEADERS, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0

    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = downloaded / total_size * 100
                    print(f"\r  下载进度: {progress:.1f}%", end="", flush=True)

    print(f"\n  视频下载完成: {filepath}")
    return filepath


def extract_audio(video_path: Path, output_dir: Path = None) -> Path:
    """使用 ffmpeg 从视频中提取音频"""
    if output_dir:
        audio_path = output_dir / (video_path.stem + ".mp3")
    else:
        audio_path = video_path.with_suffix('.mp3')

    print(f"  正在提取音频...")

    cmd = [
        FFMPEG_EXE,
        '-i', str(video_path),
        '-vn',  # 不要视频
        '-acodec', 'libmp3lame',
        '-q:a', '2',
        '-y',  # 覆盖
        str(audio_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # 尝试不带 libmp3lame
        cmd2 = [
            FFMPEG_EXE,
            '-i', str(video_path),
            '-vn',
            '-acodec', 'mp3',
            '-q:a', '2',
            '-y',
            str(audio_path)
        ]
        result2 = subprocess.run(cmd2, capture_output=True, text=True)
        if result2.returncode != 0:
            # 最后尝试 aac
            audio_path = audio_path.with_suffix('.m4a')
            cmd3 = [
                FFMPEG_EXE,
                '-i', str(video_path),
                '-vn',
                '-acodec', 'aac',
                '-y',
                str(audio_path)
            ]
            result3 = subprocess.run(cmd3, capture_output=True, text=True)
            if result3.returncode != 0:
                raise Exception(f"音频提取失败: {result3.stderr[:500]}")

    print(f"  音频提取完成: {audio_path}")
    return audio_path


def transcribe_audio(audio_path: Path, model_size: str = "large-v3",
                     initial_prompt: str = None) -> str:
    """
    使用 faster-whisper 本地转录音频

    model_size 选项: tiny, base, small, medium, large-v3
    initial_prompt: 领域术语提示词，帮助模型识别专业词汇
    """
    print(f"  正在加载 Whisper 模型 ({model_size})...")

    from faster_whisper import WhisperModel

    # 使用 CPU，int8 量化以减少内存占用
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    # 默认提示词：短视频运营/流量/商业领域高频术语
    if initial_prompt is None:
        initial_prompt = (
            "以下是抖音短视频运营、商业IP、流量算法相关的中文口播内容。"
            "关键词包括：抖音、流量、算法、推流、关联、泛化、识别、博取、"
            "马太效应、双塔召回模型、深度学习、特征、标签、用户画像、"
            "创作者、内容运营、转化率、私域、公域、获客、IP、人设、"
            "老板、创业、供应链、品牌、信任、成交、操盘手、代运营。"
        )

    print(f"  正在转录音频（模型: {model_size}, CPU模式, 可能需要数分钟）...")

    segments, info = model.transcribe(
        str(audio_path),
        language="zh",
        beam_size=10,
        best_of=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        initial_prompt=initial_prompt,
        condition_on_previous_text=True,
        no_speech_threshold=0.6,
        compression_ratio_threshold=2.4,
    )

    full_text = []
    for segment in segments:
        full_text.append(segment.text.strip())

    text = "".join(full_text)
    print(f"  转录完成，文字长度: {len(text)} 字")
    return text


def process_video(share_link: str, output_dir: str = "./output", model_size: str = "large-v3",
                  save_video: bool = False, save_audio: bool = False) -> dict:
    """处理单个视频：下载 → 提取音频 → 转录"""
    output_base = Path(output_dir)

    print(f"\n{'='*60}")
    print(f"处理链接: {share_link}")
    print(f"{'='*60}")

    # 1. 解析链接
    print("\n[1/4] 解析分享链接...")
    video_info = parse_share_url(share_link)
    print(f"  标题: {video_info['title']}")
    print(f"  类型: {video_info['content_type']}")
    print(f"  ID: {video_info['video_id']}")
    if video_info.get('create_time'):
        print(f"  发布时间: {video_info['create_time']}")
    if video_info.get('tags'):
        print(f"  标签: #{' #'.join(video_info['tags'])}")
    if video_info.get('stats'):
        s = video_info['stats']
        print(f"  数据: 赞{s['digg_count']} 评{s['comment_count']} 转{s['share_count']} 藏{s['collect_count']}")

    # 创建输出文件夹
    video_folder = output_base / video_info['video_id']
    video_folder.mkdir(parents=True, exist_ok=True)

    # 保存元数据
    meta_path = video_folder / "metadata.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(video_info, f, ensure_ascii=False, indent=2)

    # 2. 图文作品 - 不需要转录
    if video_info['content_type'] == 'note':
        print("\n[跳过] 这是图文作品，不需要语音转录")
        print(f"  图片数量: {len(video_info.get('images', []))}")

        # 保存信息
        transcript_path = video_folder / "info.md"
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(f"# {video_info['title']}\n\n")
            f.write(f"| 属性 | 值 |\n|------|----|\n")
            f.write(f"| 类型 | 图文 |\n")
            f.write(f"| ID | `{video_info['video_id']}` |\n")
            if video_info.get('create_time'):
                f.write(f"| 发布时间 | {video_info['create_time']} |\n")
            if video_info.get('tags'):
                f.write(f"| 标签 | #{' #'.join(video_info['tags'])} |\n")
            if video_info.get('stats'):
                s = video_info['stats']
                f.write(f"| 点赞 | {s['digg_count']} |\n")
                f.write(f"| 评论 | {s['comment_count']} |\n")
                f.write(f"| 转发 | {s['share_count']} |\n")
                f.write(f"| 收藏 | {s['collect_count']} |\n")
            f.write(f"| 提取时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |\n\n")
            f.write(f"---\n\n## 图片URL\n\n")
            for i, url in enumerate(video_info.get('images', []), 1):
                f.write(f"{i}. {url}\n")

        return {"video_info": video_info, "text": None, "output_path": str(video_folder), "skipped": True}

    # 3. 下载视频
    print(f"\n[2/4] 下载视频...")
    video_path = download_video(video_info, video_folder)

    # 4. 提取音频
    print(f"\n[3/4] 提取音频...")
    audio_path = extract_audio(video_path, video_folder)

    # 5. 转录
    print(f"\n[4/4] 语音转录...")
    text = transcribe_audio(audio_path, model_size)

    # 保存逐字稿
    transcript_path = video_folder / "transcript.md"
    with open(transcript_path, 'w', encoding='utf-8') as f:
        f.write(f"# {video_info['title']}\n\n")
        f.write(f"| 属性 | 值 |\n|------|----|\n")
        f.write(f"| 类型 | 视频 |\n")
        f.write(f"| ID | `{video_info['video_id']}` |\n")
        if video_info.get('create_time'):
            f.write(f"| 发布时间 | {video_info['create_time']} |\n")
        if video_info.get('tags'):
            f.write(f"| 标签 | #{' #'.join(video_info['tags'])} |\n")
        if video_info.get('stats'):
            s = video_info['stats']
            f.write(f"| 点赞 | {s['digg_count']} |\n")
            f.write(f"| 评论 | {s['comment_count']} |\n")
            f.write(f"| 转发 | {s['share_count']} |\n")
            f.write(f"| 收藏 | {s['collect_count']} |\n")
        f.write(f"| 提取时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |\n\n")
        f.write(f"---\n\n## 逐字稿\n\n{text}\n")

    print(f"\n  逐字稿已保存: {transcript_path}")

    # 清理临时文件
    if not save_video:
        video_path.unlink(missing_ok=True)
    if not save_audio:
        audio_path.unlink(missing_ok=True)

    # 打印预览
    preview = text[:300] + "..." if len(text) > 300 else text
    print(f"\n  逐字稿预览:\n  {preview}\n")

    return {"video_info": video_info, "text": text, "output_path": str(video_folder), "skipped": False}


def main():
    parser = argparse.ArgumentParser(
        description="抖音视频逐字稿提取工具（本地 Whisper 转录，无需 API Key）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("link", nargs="?", help="抖音分享链接或包含链接的文本")
    parser.add_argument("--batch", "-b", help="批量处理文件，每行一个链接")
    parser.add_argument("--output", "-o", default="./output", help="输出目录")
    parser.add_argument("--model", "-m", default="large-v3",
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper 模型大小（默认 large-v3，精度最高）")
    parser.add_argument("--save-video", "-v", action="store_true", help="保留下载的视频")
    parser.add_argument("--save-audio", "-a", action="store_true", help="保留提取的音频")

    args = parser.parse_args()

    if args.batch:
        with open(args.batch, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        print(f"批量处理 {len(links)} 个链接...")
        results = []
        for i, link in enumerate(links, 1):
            print(f"\n[{i}/{len(links)}]")
            try:
                result = process_video(link, args.output, args.model, args.save_video, args.save_audio)
                results.append({"link": link, "success": True, **result})
            except Exception as e:
                print(f"  ❌ 失败: {e}")
                results.append({"link": link, "success": False, "error": str(e)})

        # 汇总
        print(f"\n{'='*60}")
        print(f"批量处理完成: {sum(1 for r in results if r['success'])}/{len(results)} 成功")
        print(f"{'='*60}")

    elif args.link:
        process_video(args.link, args.output, args.model, args.save_video, args.save_audio)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
