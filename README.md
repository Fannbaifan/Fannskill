# Fannskill — 反骨生意经账号内容管理系统

抖音账号「反骨生意经」的内容资产管理工作台。

## 目录结构

```
Fannskill/
├── 工作台/
│   └── index.html              # 总入口工作台
├── fanggu-shengyijing/
│   ├── dashboard.html           # 账号管理工作台（21条内容）
│   ├── data/
│   │   ├── content_data.json    # 全部内容数据（逐字稿+解构+互动数据）
│   │   ├── ocr_consolidated.json
│   │   ├── ocr/                 # 10条图文OCR结果（含原图）
│   │   ├── transcripts/         # Whisper转录结果
│   │   └── transcripts_sf/      # SiliconFlow SenseVoice高精度转录
│   └── tools/
│       ├── transcribe_siliconflow.py  # SenseVoice API转录工具
│       ├── transcribe_douyin.py       # Whisper本地转录工具
│       ├── ocr_douyin.py             # 图文OCR工具
│       ├── batch_ocr_notes.py        # 批量OCR
│       ├── build_dashboard_data.py   # 数据构建
│       ├── merge_transcripts.py      # Whisper转录合并
│       ├── merge_sf_transcripts.py   # SenseVoice转录合并
│       └── add_deconstruction.py     # 内容解构
```

## 当前状态

- 总内容：21条
- 逐字稿/OCR完成：20/21
- 内容解构完成：20/21
- 待补：第8条文章（链接失效）

## 工具链

- **SiliconFlow SenseVoice API** — 视频转录（免费、中文优化、30秒/条）
- **RapidOCR (onnxruntime)** — 图文OCR
- **faster-whisper** — 本地转录（备用）

## 使用

直接打开 `工作台/index.html` 或 `fanggu-shengyijing/dashboard.html`。
