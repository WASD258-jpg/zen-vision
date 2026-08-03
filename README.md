# zen-vision

给纯文本模型（DeepSeek 等）装上眼睛：用免费多模态模型把图片转成文字描述——单文件脚本、零下载、零成本。

[English](README_EN.md) | 中文

![运行效果：vision.py 描述一张网页截图](photo/02-run-example.png)

## 这是什么

DeepSeek 很强，但"瞎"——看不到你贴的截图，`view_image` 全被拒。这个项目让纯文本模型也能"看图"：把图片交给免费的多模态模型（OpenCode Zen `mimo-v2.5-free`），转成文字描述，再交给 DeepSeek 推理。不换主模型、不花一分钱、不依赖任何第三方下载。

核心思路一句话：**多模态翻译官 = 截图 + 视觉模型 + 文字描述 + DeepSeek**（学术上叫 *Describe-then-Reason*）。

## 功能特性

- **多源自动切换**：主源 OpenCode Zen，备用源智谱（免费），主源挂了自动切换；`.env` 填 `VISION3_*`/`VISION4_*`… 可继续扩展
- **单文件**：`vision.py`，唯一依赖 `requests`，不用编译、不用跑服务
- **三种模式**：描述、问答（`-q`）、逐字 OCR（`--ocr`）
- **运行时换模型**：`/vision-model` 指令，随时切 zen / zhipu / glm / v3 / v4… / auto
- **MCP 集成**：`describe_image` / `ocr_image` / `set_vision_model` 工具，接入 opencode、Claude Code、Codex
- **一键配置**：`setup.py` / `setup.bat`，自动装依赖、引导填 key、可选接入 MCP
- **兼容性好**：`.env` 读取免疫 Windows BOM；HTTP 用 `requests` 免疫 Cloudflare 拦截

## 你能用它做什么

- 看一张截图：`python vision.py 图片.png`
- 针对图片提问：`python vision.py 图片.png -q "主色是什么"`
- 逐字转写报错弹窗：`python vision.py 图片.png --ocr`
- 一次对比多张图：`python vision.py a.png b.png`
- 切换视觉模型：`python vision.py /vision-model zhipu`
- 让 opencode / Claude Code / Codex 里的 DeepSeek 直接看图（MCP）

## 快速开始

Windows 双击 `setup.bat`，或任意平台执行 `python setup.py`，跟着引导走：

1. 粘贴主源 API key（opencode 里 `/connect` 选 OpenCode Zen，免费）
2. （可选）粘贴备用源 key（智谱 `glm-4.1v-thinking-flash`，免费）
3. 完成，直接 `python vision.py 图片.png`

![痛点：纯文本模型看不到粘贴的截图](photo/01-pain-point.png)

## 配置

在 `vision.py` 同目录建 `.env`，主源三行必填，其余可选：

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

### 新增模型源

想加第三个、第四个视觉源？照抄三行，编号递增：

```dotenv
VISION3_API_KEY=你的key
VISION3_BASE_URL=https://你的端点/v1
VISION3_MODEL=你的模型ID
```

规则：命名 `VISION{N}_API_KEY` / `VISION{N}_BASE_URL` / `VISION{N}_MODEL`，N 从 3 递增；端点须为 OpenAI 兼容且支持 `image_url`；填了自动进 fallback 链（zen → zhipu → v3 → v4 → …）；`/vision-model v3` 可强制切换。

## 接入 MCP（让 agent 直接看图）

`mcp_server.py` 把 `vision.py` 暴露为三个工具：`describe_image`（看图）、`ocr_image`（转写）、`set_vision_model`（切换模型）。装依赖后按你的 agent 接入：

```powershell
pip install "mcp>=1.0,<2"
```

**opencode** — 编辑 `~/.config/opencode/opencode.jsonc`，在 `mcp` 节点加：

```jsonc
"vision": {
  "type": "local",
  "command": ["python", "E:\\path\\to\\mcp_server.py"],
  "environment": { "CODEX_VISION_PROXY_ENV": "E:\\path\\to\\.env" },
  "enabled": true
}
```

**Claude Code** — 一条命令（`-s user` 全局生效）：

```powershell
claude mcp add vision -s user -e "CODEX_VISION_PROXY_ENV=E:\path\to\.env" -- python E:\path\to\mcp_server.py
```

**Codex CLI** — 编辑 `~/.codex/config.toml`，追加：

```toml
[mcp_servers.vision]
command = "python"
args = ["E:\\path\\to\\mcp_server.py"]
env = { CODEX_VISION_PROXY_ENV = "E:\\path\\to\\.env" }
```

配完**重启 agent**，然后直接说"看看这张图 `E:\xxx\shot.png`"即可，DeepSeek 会自动调用工具。

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
| `photo/` | 本 README 使用的截图 |

常见问题：**为什么用 `requests` 不用 `urllib`？** `urllib` 的 TLS 指纹被 Zen 前面的 Cloudflare 识别拦截（403，error code 1010），`requests` 实测能过。**`.env` 为什么用 `utf-8-sig` 读？** Windows PowerShell 写文件会带 BOM，普通读法 key 会悄悄匹配失败，`utf-8-sig` 自动剥掉。

## 致谢

思路与核心代码大量参考 [Anionex/codex-vision-proxy](https://github.com/Anionex/codex-vision-proxy)（MIT）——一个精炼的"图转文字"工具包。本仓库把它适配到 OpenCode Zen 的免费档，补上 Windows 的排雷，并打包成单文件自包含脚本。

## 更新日志

### v1.1.0
- 多源自动切换：主源 OpenCode Zen，备用源智谱（免费），可加 `VISION3_*`/`VISION4_*`… 扩展
- `/vision-model` 指令：运行时查看/切换模型，含 `/`、`/help` 帮助
- MCP 新增 `set_vision_model` 工具
- 修复：备用源模型改为实测可用的 `glm-4.1v-thinking-flash`

### v1.0.0
- 初版发布：单源（OpenCode Zen `mimo-v2.5-free`）、描述/问答/OCR、一键配置、双语 README

## 许可

[MIT](LICENSE)
