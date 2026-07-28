#!/usr/bin/env python3
"""
抖音图文笔记 OCR 提取工具

功能：
1. 从抖音分享链接下载图文笔记的所有图片
2. 使用 rapidocr-onnxruntime 识别图片中的中文文字
3. 输出逐字稿 + 元数据

用法：
  python ocr_douyin.py "https://v.douyin.com/xxxxx/" -o ./output
  python ocr_douyin.py --batch links.txt -o ./output
"""

import os
import re
import sys
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/121.0.2277.107 Version/17.0 Mobile/15E148 Safari/604.1'
}


def parse_share_url(share_text: str) -> dict:
    """从分享文本解析图文信息（含图片 URL 列表）"""
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', share_text)
    if not urls:
        raise ValueError("未找到有效的分享链接")

    share_url = urls[0]
    share_response = requests.get(share_url, headers=HEADERS, allow_redirects=True)
    video_id = share_response.url.split("?")[0].strip("/").split("/")[-1]

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
    desc = data.get("desc", "").strip() or f"douyin_{video_id}"
    desc = re.sub(r'[\\/:*?"<>|]', '_', desc)

    result = {
        "title": desc,
        "video_id": video_id,
        "content_type": content_type,
        "images": [],
    }

    # 提取图片 URL 列表
    images = data.get("images", []) or []
    for img in images:
        url_list = img.get("url_list", [])
        if url_list:
            result["images"].append(url_list[0])

    # 图文笔记的统计
    stats = data.get("statistics", {}) or {}
    result["stats"] = {
        "digg_count": stats.get("digg_count", 0),
        "comment_count": stats.get("comment_count", 0),
        "share_count": stats.get("share_count", 0),
        "collect_count": stats.get("collect_count", 0),
        "play_count": stats.get("play_count", 0),
    }

    # 作者
    author = data.get("author", {}) or {}
    result["author"] = {
        "nickname": author.get("nickname", ""),
        "sec_uid": author.get("sec_uid", ""),
    }

    # 发布时间
    result["create_time"] = datetime.fromtimestamp(data.get("create_time", 0)).strftime("%Y-%m-%d %H:%M:%S")

    return result


def download_images(image_urls: list, save_dir: Path) -> list:
    """下载所有图片到本地目录"""
    save_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []
    for i, url in enumerate(image_urls, 1):
        ext = ".jpg"
        try:
            ext = "." + url.split("?")[0].split(".")[-1].split("/")[0]
            if len(ext) > 5 or ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                ext = ".jpg"
        except Exception:
            pass
        save_path = save_dir / f"image_{i:02d}{ext}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            save_path.write_bytes(r.content)
            saved_paths.append(save_path)
            print(f"  ✅ 已下载: {save_path.name} ({len(r.content)/1024:.1f}KB)")
        except Exception as e:
            print(f"  ❌ 下载失败: {e}")
    return saved_paths


def ocr_image(image_path: Path, engine) -> tuple:
    """对单张图片做 OCR，返回 (文本, 文字块列表)"""
    try:
        result, _ = engine(str(image_path))
        if not result:
            return "", []
        # result 格式: [[[box, text, score], ...]]
        blocks = [(b[1], b[2]) for b in result]
        text = "\n".join(b[0] for b in blocks)
        return text, blocks
    except Exception as e:
        return f"[OCR失败: {e}]", []


def ocr_note(share_text: str, output_dir: Path, engine=None):
    """完整流程：解析 -> 下载 -> OCR"""
    print(f"\n{'='*60}")
    print(f"处理链接: {share_text[:80]}...")
    print(f"{'='*60}")

    # 1. 解析
    print("[1/3] 解析分享链接...")
    info = parse_share_url(share_text)
    print(f"  标题: {info['title'][:60]}")
    print(f"  类型: {info['content_type']}")
    print(f"  ID: {info['video_id']}")
    print(f"  发布时间: {info['create_time']}")
    print(f"  数据: 赞{info['stats']['digg_count']} 评{info['stats']['comment_count']} "
          f"转{info['stats']['share_count']} 藏{info['stats']['collect_count']}")
    print(f"  图片数量: {len(info['images'])}")

    # 2. 下载图片
    note_dir = output_dir / info['video_id']
    print(f"[2/3] 下载图片到: {note_dir}")
    saved_paths = download_images(info['images'], note_dir)

    # 3. OCR
    if engine is None:
        print("[3/3] 跳过 OCR（未提供 engine）")
        full_text = ""
        per_image = {}
    else:
        print(f"[3/3] OCR 识别 {len(saved_paths)} 张图片...")
        per_image = {}
        texts = []
        for img_path in saved_paths:
            text, _ = ocr_image(img_path, engine)
            per_image[img_path.name] = text
            texts.append(f"=== {img_path.name} ===\n{text}")
            print(f"  ✅ {img_path.name}: {len(text)} 字")
        full_text = "\n\n".join(texts)

    # 保存结果
    note_dir.mkdir(parents=True, exist_ok=True)

    # metadata.json
    metadata = {
        "title": info['title'],
        "note_id": info['video_id'],
        "content_type": info['content_type'],
        "create_time": info['create_time'],
        "author": info['author'],
        "stats": info['stats'],
        "image_count": len(saved_paths),
        "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    (note_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    # transcript.md
    transcript_md = f"""# {info['title']}

| 属性 | 值 |
|------|----|
| 类型 | 图文 |
| ID | `{info['video_id']}` |
| 发布时间 | {info['create_time']} |
| 图片数 | {len(saved_paths)} |
| 点赞 | {info['stats']['digg_count']} |
| 评论 | {info['stats']['comment_count']} |
| 转发 | {info['stats']['share_count']} |
| 收藏 | {info['stats']['collect_count']} |
| 提取时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |

---

## OCR 提取的文字内容

{full_text if full_text else '⚠️ 尚未运行 OCR'}

---

## 备注

- 本文档由 `ocr_douyin.py` 自动生成
- 图片已下载到同目录 `image_*.jpg`
- 如需重新 OCR，删除此目录后重新运行
"""
    (note_dir / "transcript.md").write_text(transcript_md, encoding='utf-8')

    print(f"  📝 已保存: {note_dir}/transcript.md")
    print(f"  📊 已保存: {note_dir}/metadata.json")

    return {
        "id": info['video_id'],
        "title": info['title'],
        "text": full_text,
        "stats": info['stats'],
    }


def main():
    parser = argparse.ArgumentParser(description="抖音图文 OCR 提取")
    parser.add_argument("url", nargs="?", help="抖音分享链接/文本（含链接）")
    parser.add_argument("-i", "--input", help="批量链接文件（每行一个）")
    parser.add_argument("-o", "--output", default="./output", help="输出目录")
    parser.add_argument("--no-ocr", action="store_true", help="跳过 OCR，仅下载图片")
    args = parser.parse_args()

    if not args.url and not args.input:
        parser.print_help()
        return 1

    output_dir = Path(args.output)

    # 初始化 OCR engine
    engine = None
    if not args.no_ocr:
        print("加载 OCR 模型（首次需要下载模型文件，约 30MB）...")
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        print("✅ OCR 引擎就绪\n")

    # 处理
    if args.input:
        links = [l.strip() for l in Path(args.input).read_text(encoding='utf-8').splitlines() if l.strip()]
        for link in links:
            try:
                ocr_note(link, output_dir, engine)
            except Exception as e:
                print(f"❌ 处理失败: {link}\n   {e}\n")
    else:
        ocr_note(args.url, output_dir, engine)

    print(f"\n{'='*60}")
    print(f"✅ 全部完成。输出目录: {output_dir}")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
