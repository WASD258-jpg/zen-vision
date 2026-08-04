# zen-vision

给纯文本模型（DeepSeek 等）装上眼睛：用免费多模态模型把图片转成文字描述——单文件脚本、零下载、零成本。

[English](README_EN.md) | 中文

![运行效果：vision.py 描述一张网页截图](photo/02-run-example.png)

## 这是什么

DeepSeek 很强，但"瞎"——看不到你贴的截图，`view_image` 全被拒，报错图只能靠肉眼翻译给它听。

![痛点：纯文本模型看不到粘贴的截图](photo/01-pain-point.png)

这个项目让纯文本模型也能"看图"：把图片交给免费的多模态模型（OpenCode Zen `mimo-v2.5-free`），转成文字描述，再交给 DeepSeek 推理。**不换主模型、不花一分钱、不需要下载任何东西**。

核心思路一句话：**多模态翻译官 = 截图 + 视觉模型 + 文字描述 + DeepSeek**（学术上叫 *Describe-then-Reason*）。

## 功能特性

- **多源自动切换**：主源 OpenCode Zen，备用源智谱（免费），主源挂了自动切换；`.env` 填 `VISION3_*`/`VISION4_*`… 可继续扩展
- **单文件**：`vision.py`，唯一依赖 `requests`，不用编译、不用跑服务
- **三种模式**：描述、问答（`-q`）、逐字 OCR（`--ocr`）
- **运行时换模型**：`/vision-model` 指令，随时切 zen / zhipu / glm / v3 / v4… / auto
- **MCP 集成**：`describe_image` / `ocr_image` / `set_vision_model` 工具，接入 opencode、Claude Code、Codex
- **一键配置**：`setup.py` / `setup.bat`，自动装依赖、引导填 key、可选接入 MCP
- **兼容性好**：`.env` 读取免疫 Windows BOM；HTTP 用 `requests` 免疫 Cloudflare 拦截
- **实时视力（watch）**：监控屏幕 / 视频 / 摄像头，本地检测画面变化（零 API），有变化才调模型描述

## 你能用它做什么

- 看一张截图：`python vision.py 图片.png`
- 针对图片提问：`python vision.py 图片.png -q "主色是什么"`
- 逐字转写报错弹窗：`python vision.py 图片.png --ocr`
- 一次对比多张图：`python vision.py a.png b.png`
- 切换视觉模型：`python vision.py /vision-model zhipu`
- 让 opencode / Claude Code / Codex 里的 DeepSeek 直接看图（见下文 MCP 章节）
- 实时监控屏幕：`python watch.py screen`
- 分析视频：`python watch.py video 视频.mp4`
- 摄像头监控：`python watch.py camera`

一轮视觉问答——模型先描述所见，再识别主体：

![视觉问答示例](photo/05-identify-role.png)

## 快速开始

Windows 双击 `setup.bat`，或任意平台执行 `python setup.py`，跟着引导走：

1. **粘贴主源 API key**：opencode 里执行 `/connect` 选 OpenCode Zen，浏览器弹出页面里复制 key（下图红框处）粘贴

   ![OpenCode Zen API 密钥页面](photo/04-zen-api-key.png)

2. **（可选）配备用源**：粘贴智谱 key（`glm-4.1v-thinking-flash`，免费），主源挂了自动切换
3. **完成**：直接 `python vision.py 图片.png` 就能用

## 配置

在 `vision.py` 同目录建一个 `.env` 文件（记事本新建即可），主源三行必填，其余可选：

| 变量 | 必填 | 说明 |
|---|---|---|
| `VISION_API_KEY` | 是 | 主源 API key（OpenCode Zen） |
| `VISION_BASE_URL` | 否（有默认） | `https://opencode.ai/zen/v1` |
| `VISION_MODEL` | 是 | 主源模型 `mimo-v2.5-free` |
| `FALLBACK_API_KEY` | 否 | 备用源 API key（智谱，免费） |
| `FALLBACK_BASE_URL` | 否 | `https://open.bigmodel.cn/api/paas/v4` |
| `FALLBACK_MODEL` | 否 | 备用源模型 `glm-4.1v-thinking-flash` |
| `VISION3_API_KEY` 等 | 否 | 更多备用源（自选） |
| `LANG` | 否 | `zh`（中文）或 `en`（英文），默认中文 |

```dotenv
VISION_API_KEY=oc-...
VISION_BASE_URL=https://opencode.ai/zen/v1
VISION_MODEL=mimo-v2.5-free
FALLBACK_API_KEY=你的智谱key
FALLBACK_BASE_URL=https://open.bigmodel.cn/api/paas/v4
FALLBACK_MODEL=glm-4.1v-thinking-flash
LANG=zh
```

![.env 文件示例](photo/03-env-config.png)

> 放心用记事本保存，脚本已兼容 Windows 的编码问题，不会读不到 key。

### 新增模型源

想加第三个、第四个视觉源？照抄三行，编号递增：

```dotenv
VISION3_API_KEY=你的key
VISION3_BASE_URL=https://你的端点/v1
VISION3_MODEL=你的模型ID
```

规则：命名 `VISION{N}_API_KEY` / `VISION{N}_BASE_URL` / `VISION{N}_MODEL`，N 从 3 递增；端点须为 OpenAI 兼容且支持 `image_url`；填了自动进 fallback 链（zen → zhipu → v3 → v4 → …）；`/vision-model v3` 可强制切换。

## 接入 MCP（让 agent 直接看图）

MCP 是一个让 agent 调用外部工具的协议。本项目的 `mcp_server.py` 提供三个工具：

| 工具 | 作用 | 例子 |
|---|---|---|
| `describe_image` | 看一张图并描述 / 回答 | 让 DeepSeek 分析截图 |
| `ocr_image` | 逐字转写图中文字 | 读报错弹窗 |
| `set_vision_model` | 切换视觉模型 | 换智谱 / 换回自动 |

**第 1 步：装依赖**（一条命令）：

```powershell
pip install "mcp>=1.0,<2"
```

**第 2 步：按你用的 agent 接入**（三选一）

**opencode：**
1. 找到配置文件 `~/.config/opencode/opencode.jsonc`（Windows 下在你的用户目录下的 `.config\opencode\opencode.jsonc`）
2. 用记事本打开，在 `"mcp": { ... }` 的大括号里加一段：

   ```jsonc
   "vision": {
     "type": "local",
     "command": ["python", "你的绝对路径\\mcp_server.py"],
     "environment": { "CODEX_VISION_PROXY_ENV": "你的绝对路径\\.env" },
     "enabled": true
   }
   ```

   把"你的绝对路径"换成 `mcp_server.py` 所在文件夹的完整路径（例如 `D:\tools\zen-vision`）
3. 保存，**完全退出 opencode 再重开**
4. 验证：终端执行 `opencode mcp list`，看到 `vision connected` 即成功

**Claude Code：** 终端执行一条命令（替换成你的路径）：

```powershell
claude mcp add vision -s user -e "CODEX_VISION_PROXY_ENV=你的绝对路径\.env" -- python 你的绝对路径\mcp_server.py
```

重启后 `claude mcp list` 看到 `vision ... Connected` 即成功。

**Codex CLI：**
1. 编辑 `~/.codex/config.toml`
2. 末尾追加：

   ```toml
   [mcp_servers.vision]
   command = "python"
   args = ["你的绝对路径\\mcp_server.py"]
   env = { CODEX_VISION_PROXY_ENV = "你的绝对路径\\.env" }
   ```

3. 重启 Codex

**第 3 步：使用**。配好之后，直接对 agent 说："看看这张图 `你的图片路径\shot.png`"，它就会自动调用工具看图。

> 改配置前先备份原文件。以上路径均为示例占位，请替换成你自己的实际路径。

## 原理

```
你的纯文本模型（DeepSeek）
        │  想看一张图
        ▼
vision.py / mcp_server.py
        │  图片 → base64 data URL
        ▼
视觉 API（多源：zen → zhipu → v3 → ...）
        │  模型描述图片
        ▼
文字描述 / 逐字 OCR
        ▼
DeepSeek（纯文本）→ 现在它"看见"了
```

图片永远不会直接进 DeepSeek：由视觉模型描述，纯文本模型拿描述做推理——*Describe-then-Reason*（[Prism](https://arxiv.org/abs/2406.14544), NeurIPS 2024）。

## 安全

- `.env`（含 API key）与 `.vision-model` 状态文件被 `.gitignore` 忽略，不会进入仓库
- 免费模型在免费期间可能收集数据用于模型改进——不要发送含密码、身份证等敏感信息的截图
- 免费是限时的：Zen 的 free 模型可能下架，届时多源备用链会自动接管，或改 `.env` 换端点

## 深入

| 文件 | 用途 |
|---|---|
| `vision.py` | 单文件 CLI：描述 / 问答 / OCR / 换模型指令 |
| `mcp_server.py` | MCP server：`describe_image` / `ocr_image` / `set_vision_model` |
| `setup.py` / `setup.bat` | 一键配置 |
| `.env.example` | 配置模板 |
| `watch.py` | 实时视力：监控屏幕/视频/摄像头，变化时自动描述 |
| `photo/` | 本 README 使用的截图 |

### 依赖说明（可选安装，控制硬盘占用）

| 功能 | 依赖 | 大小 | 是否必须 |
|---|---|---|---|
| `vision.py`（描述 / 问答 / OCR） | `requests` | ~1 MB | 必须 |
| `watch.py` screen（屏幕监控） | `pillow` | ~4 MB | 推荐（setup 默认装） |
| `watch.py` video / camera | `opencv-python` | ~90 MB | **可选**（不需要可不装） |

`setup.py` 安装时会询问是否装视频/摄像头支持；只要纯看图 + 屏幕监控，本地依赖约 **5 MB** 即可，远低于完整版 ~100 MB。

常见问题：

**为什么用 `requests` 不用 `urllib`？** `urllib` 的 TLS 指纹被 Zen 前面的 Cloudflare 识别拦截（403，error code 1010），`requests` 实测能过。

**`.env` 为什么用 `utf-8-sig` 读？** Windows PowerShell 写文件会带 BOM，普通读法 key 会悄悄匹配失败，`utf-8-sig` 自动剥掉。

**Zen 免费模型里哪些能看图？** 实测只有 `mimo-v2.5-free` 支持图像输入，其余 free 模型发图全部 HTTP 400。

## 致谢

思路与核心代码大量参考 [Anionex/codex-vision-proxy](https://github.com/Anionex/codex-vision-proxy)（MIT）——一个精炼的"图转文字"工具包。本仓库把它适配到 OpenCode Zen 的免费档，补上 Windows 的排雷，并打包成单文件自包含脚本。

## 更新日志

### v1.3.0
- **磁盘缓存**：同图同问秒回（200MB 上限自动清理），`/cache` 指令 + MCP `cache_list` / `cache_clear` 可翻看历史描述
- **watch 变化摘要**：触发时对比变化前后两帧，描述"从什么变成了什么"
- **精简**：watch 去掉 numpy（纯 PIL），依赖分层安装（`opencv-python` 可选）
- 新增 watch 实战演示图（CS 对局监控效果）

### v1.2.0
- 新增实时视力 `watch.py`：监控屏幕 / 视频 / 摄像头，本地像素差检测变化（零 API 调用），有变化才调视觉模型描述；防抖 + 冷却避免误报、重复报

### v1.1.0
- 多源自动切换：主源 OpenCode Zen，备用源智谱（免费），可加 `VISION3_*`/`VISION4_*`… 扩展
- `/vision-model` 指令：运行时查看/切换模型，含 `/`、`/help` 帮助
- MCP 新增 `set_vision_model` 工具
- 修复：备用源模型改为实测可用的 `glm-4.1v-thinking-flash`

### v1.0.0
- 初版发布：单源（OpenCode Zen `mimo-v2.5-free`）、描述/问答/OCR、一键配置、双语 README

## 许可

[MIT](LICENSE)
