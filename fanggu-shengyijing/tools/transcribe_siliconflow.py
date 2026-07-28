#!/usr/bin/env python3
"""
SiliconFlow SenseVoice 转录工具
用硅基流动免费 API 转录抖音视频，比本地 Whisper 快 10 倍以上。

用法:
  python tools/transcribe_siliconflow.py <分享链接> [--api-key sk-xxx] [-o output_dir]
  python tools/transcribe_siliconflow.py --batch tools/video_links.txt [--api-key sk-xxx] [-o output_dir]

API Key 获取: https://cloud.siliconflow.cn/ (免费注册即可)
或设置环境变量: SILICONFLOW_API_KEY=sk-xxx

特点:
  - 免费、不限量
  - 中文识别效果好（SenseVoiceSmall 模型）
  - 30-90 秒一条视频
  - 支持单条和批量
"""
import argparse, json, os, re, sys, time, pathlib, subprocess
from datetime import datetime

import requests

# === 配置 ===
SILICONFLOW_API_URL = "https://api.siliconflow.cn/v1/audio/transcriptions"
SILICONFLOW_MODEL = "FunAudioLLM/SenseVoiceSmall"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/121.0.2277.107 Version/17.0 Mobile/15E148 Safari/604.1'
}

FFMPEG_PATH = None
def get_ffmpeg():
    global FFMPEG_PATH
    if FFMPEG_PATH:
        return FFMPEG_PATH
    try:
        import imageio_ffmpeg
        FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        FFMPEG_PATH = 'ffmpeg'
    return FFMPEG_PATH


def parse_share_url(share_url):
    """解析抖音分享链接，返回 video_id"""
    share_url = share_url.strip()
    # 提取链接
    url_match = re.search(r'https?://[^\s]+', share_url)
    if url_match:
        share_url = url_match.group()
    
    resp = requests.get(share_url, headers=HEADERS, allow_redirects=True)
    final_url = resp.url
    
    # 从 URL 中提取 video_id
    parts = final_url.split('?')[0].strip('/').split('/')
    video_id = parts[-1]
    
    if not video_id.isdigit():
        raise ValueError(f"无法从 URL 提取 video_id: {final_url}")
    
    return video_id


def get_video_info(video_id):
    """获取视频信息和下载地址"""
    url = f'https://www.iesdouyin.com/share/video/{video_id}'
    resp = requests.get(url, headers=HEADERS)
    
    pattern = re.compile(r'window\._ROUTER_DATA\s*=\s*(.*?)</script>', re.DOTALL)
    match = pattern.search(resp.text)
    if not match:
        raise ValueError("无法获取视频数据")
    
    data = json.loads(match.group(1).strip())
    loader = data.get('loaderData', {})
    
    for key in loader:
        page_data = loader[key]
        if page_data and 'videoInfoRes' in page_data:
            info = page_data['videoInfoRes']
            if info.get('item_list'):
                return info['item_list'][0]
    
    raise ValueError("未找到视频信息")


def download_video(video_url, output_path):
    """下载视频"""
    resp = requests.get(video_url, headers=HEADERS, stream=True, timeout=60)
    total = int(resp.headers.get('content-length', 0))
    downloaded = 0
    with open(output_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=1024*1024):
            f.write(chunk)
            downloaded += len(chunk)
    return output_path


def extract_audio(video_path, audio_path):
    """用 FFmpeg 提取音频"""
    ffmpeg = get_ffmpeg()
    cmd = [
        ffmpeg, '-i', str(video_path),
        '-vn', '-acodec', 'libmp3lame', '-ab', '128k', '-ar', '16000', '-ac', '1',
        str(audio_path), '-y'
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 错误: {result.stderr.decode('utf-8', errors='ignore')[:500]}")
    return audio_path


def transcribe_siliconflow(audio_path, api_key):
    """调用 SiliconFlow SenseVoice API 转录音频"""
    file_size = os.path.getsize(audio_path)
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"音频文件过大: {file_size/1024/1024:.1f}MB > 50MB")
    
    headers = {"Authorization": f"Bearer {api_key}"}
    
    with open(audio_path, 'rb') as f:
        files = {
            "file": (os.path.basename(audio_path), f, "audio/mpeg"),
            "model": (None, SILICONFLOW_MODEL),
        }
        print(f"  正在调用 SiliconFlow API...")
        resp = requests.post(SILICONFLOW_API_URL, headers=headers, files=files, timeout=120)
    
    if resp.status_code != 200:
        raise RuntimeError(f"API 错误 ({resp.status_code}): {resp.text[:300]}")
    
    result = resp.json()
    return result.get('text', '')


def process_single(share_url, output_dir, api_key):
    """处理单条视频"""
    print(f"\n[1/4] 解析分享链接...")
    video_id = parse_share_url(share_url)
    print(f"  ID: {video_id}")
    
    print(f"[2/4] 获取视频信息...")
    item = get_video_info(video_id)
    title = item.get('desc', '').strip()
    stats = item.get('statistics', {})
    create_time = item.get('create_time', 0)
    
    # 获取无水印视频 URL
    video_url = None
    if 'video' in item and 'play_addr' in item['video']:
        urls = item['video']['play_addr']['url_list']
        if urls:
            video_url = urls[0].replace('playwm', 'play')
    if not video_url:
        raise ValueError("无法获取视频下载地址")
    
    print(f"  标题: {title[:50]}")
    print(f"  数据: 赞{stats.get('digg_count',0)} 评{stats.get('comment_count',0)} 转{stats.get('share_count',0)} 藏{stats.get('collect_count',0)}")
    
    # 创建输出目录
    out_dir = pathlib.Path(output_dir) / video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[3/4] 下载视频 + 提取音频...")
    video_path = out_dir / f"{video_id}.mp4"
    audio_path = out_dir / f"{video_id}.mp3"
    
    download_video(video_url, video_path)
    extract_audio(video_path, audio_path)
    
    print(f"[4/4] SiliconFlow 转录...")
    transcript = transcribe_siliconflow(audio_path, api_key)
    print(f"  转录完成，文字长度: {len(transcript)} 字")
    
    # 保存逐字稿
    tc_path = out_dir / 'transcript.md'
    tc_path.write_text(transcript, encoding='utf-8')
    
    # 保存元数据
    meta = {
        'video_id': video_id,
        'title': title,
        'desc': title,
        'stats': {
            'digg_count': stats.get('digg_count', 0),
            'comment_count': stats.get('comment_count', 0),
            'share_count': stats.get('share_count', 0),
            'collect_count': stats.get('collect_count', 0),
            'play_count': stats.get('play_count', 0),
        },
        'create_time': create_time,
        'create_date': datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S') if create_time else '',
        'transcribe_method': 'siliconflow_sensevoice',
        'transcribe_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    meta_path = out_dir / 'metadata.json'
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    
    # 删除视频和音频文件节省空间
    video_path.unlink(missing_ok=True)
    audio_path.unlink(missing_ok=True)
    
    print(f"  逐字稿已保存: {tc_path}")
    print(f"  预览: {transcript[:200]}...")
    
    return transcript


def main():
    parser = argparse.ArgumentParser(description='SiliconFlow SenseVoice 抖音视频转录')
    parser.add_argument('input', help='分享链接或批量文件路径')
    parser.add_argument('--batch', action='store_true', help='批量模式')
    parser.add_argument('--api-key', default=os.environ.get('SILICONFLOW_API_KEY', ''), help='SiliconFlow API Key')
    parser.add_argument('-o', '--output', default='./data/transcripts', help='输出目录')
    
    args = parser.parse_args()
    
    if not args.api_key:
        print("错误: 需要提供 SiliconFlow API Key")
        print("  方式1: --api-key sk-xxx")
        print("  方式2: 设置环境变量 SILICONFLOW_API_KEY")
        print("  免费获取: https://cloud.siliconflow.cn/")
        sys.exit(1)
    
    if args.batch:
        with open(args.input, 'r', encoding='utf-8') as f:
            links = [l.strip() for l in f if l.strip() and not l.startswith('#')]
        print(f"批量处理 {len(links)} 个链接...")
        
        success = 0
        for i, link in enumerate(links, 1):
            print(f"\n[{i}/{len(links)}]")
            print("=" * 60)
            try:
                process_single(link, args.output, args.api_key)
                success += 1
            except Exception as e:
                print(f"  ❌ 失败: {e}")
        
        print(f"\n批量处理完成: {success}/{len(links)} 成功")
    else:
        process_single(args.input, args.output, args.api_key)


if __name__ == '__main__':
    main()
