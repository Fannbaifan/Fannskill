# 项目长期记忆 - 反骨生意经

## 账号信息
- **账号名：** 反骨生意经
- **平台：** 抖音
- **归属：** 用户自有账号
- **内容方向：** 老板IP打造 / 创始人IP / 短视频运营方法论 / 内容获客
- **内容形式：** 图文为主（52.6%），视频次之（42.1%），偶尔发文章
- **核心标签：** #老板IP #创始人IP #这是本宫自己写的 #一般人不告诉他
- **内容时间跨度：** 2025-08 至 2026-06（已归档21条）

## 技能体系
- **fanggu-shengyijing** — 自有账号内容管理（链接/逐字稿/数据归档）
- **外部爆款分析技能** — 分析他人爆款内容，反哺本账号运营
- 两者职责分离，不可混用

## 内容管理规范
- 每条内容归档格式：日期_标题.md
- 视频索引维护在 `data/video-index.md`
- 数据汇总维护在 `data/data-summary.md`
- 完整逐字稿标记 ✅完整，部分描述标记 ✅描述，未获取标记 ❌待补

## 前端/HTML 开发铁律（不可反复犯的错）

1. **JSON 内嵌到 HTML `<script>` 时，绝对不能用 `re.subn(repl_string)` 直接替换。** 原因：`repl` 字符串中的反斜杠会被正则引擎当作替换模板解析，导致 `\n`、`\uXXXX` 等转义序列被解释成真实字符，从而破坏 JavaScript 语法，页面脚本整体失效（表现为导航点击无反应）。
   - ✅ 正确做法：使用 `re.subn(pattern, lambda m: replacement_string, ...)`，让 replacement 原样插入。
   - ✅ 或者用字符串拼接：`new_html = html[:start] + replacement + html[end:]`。
   - ✅ 写完后必须用 `node -e "new Function(script)"` 验证 JS 语法。

2. **每次更新 dashboard/workshop 类 HTML 后，必须验证：**
   - 左侧/顶部导航点击能正常切换视图
   - 没有浏览器控制台报错（特别是 SyntaxError）
   - 如果是本地双击打开，确保没有依赖 `fetch` 本地文件

3. **工作台入口固定规则（不可再反复出现点击无反应）：**
   - 主入口统一放在 `C:/Users/Fann/WorkBuddy/Claw/工作台/index.html`
   - 新增工作流必须在该页面以卡片形式注册
   - 所有项目级 dashboard 必须通过工作台入口可到达
   - **入口卡片的跳转链接必须用绝对 `file:///` 路径**，并附加 `onclick` 兜底，禁止用相对路径。因为 WorkBuddy 预览面板对相对路径的 file:// 导航支持不稳定，会导致点击无反应。
   - **必须自带缓存刷新：** 每次点击跳转时给 URL 追加 `?v=` + Date.now() 时间戳，防止 WorkBuddy 预览面板显示旧缓存内容（用户看到 18/19 而不是 20/21）。
   - **跳转方式多重兜底：** 优先 `window.open(url, '_blank')`，其次 `window.location.href`，再次 `window.location.replace`，最后显示可复制路径让用户手动打开。
   - **更新完必须验证：** 用 `node -e "new Function(script)"` 验证 JS 语法；重新打开工作台预览确认数字已刷新、点击有响应。

4. **内容数据同步规则：**
   - `data/content_data.json` 与 `dashboard.html` 内嵌数据必须保持一致。
   - 新增/修改内容后，必须重新执行内嵌脚本，不能手动改 HTML 里的数据。
