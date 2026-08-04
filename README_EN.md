# zen-vision

Give text-only models (DeepSeek and friends) real eyes using **free multimodal models** 鈥?a single-file script, zero downloads, zero cost.

English | [涓枃](README.md)

![Running: vision.py describing a webpage screenshot](photo/02-run-example.png)

## What is this

DeepSeek is powerful but blind 鈥?it can't see pasted screenshots, every `view_image` call is rejected, and error dialogs have to be read to it by hand.

![Pain point: a text-only model cannot see the pasted screenshot](photo/01-pain-point.png)

This project lets text-only models "see": an image is sent to a free multimodal model (OpenCode Zen `mimo-v2.5-free`), converted into a text description, and handed to DeepSeek for reasoning. **No model swap, no cost, nothing to download.**

The core idea in one line: **translation = screenshot + vision model + text description + DeepSeek** (aka *Describe-then-Reason*).

## Features

- **Multi-source failover**: primary OpenCode Zen, fallback Zhipu (free), auto-switch on failure; extend with `VISION3_*`/`VISION4_*`... in `.env`
- **Single file**: `vision.py`, the only dependency is `requests`. No build, no service.
- **Three modes**: describe, ask (`-q`), verbatim OCR (`--ocr`)
- **Runtime model switch**: `/vision-model` command (zen / zhipu / glm / v3 / v4... / auto)
- **MCP integration**: `describe_image` / `ocr_image` / `set_vision_model` tools for opencode, Claude Code, Codex
- **One-click setup**: `setup.py` / `setup.bat`
- **Hardened**: BOM-proof `.env` loading; `requests` instead of `urllib` to pass Cloudflare
- **Live vision (watch)**: monitor screen / video / camera 鈥?local pixel-diff change detection (zero API calls), describe only when something changes

## What you can do with it

- Look at a screenshot: `python vision.py image.png`
- Ask about an image: `python vision.py image.png -q "dominant color?"`
- Transcribe an error dialog verbatim: `python vision.py image.png --ocr`
- Compare multiple images: `python vision.py a.png b.png`
- Switch vision model at runtime: `python vision.py /vision-model zhipu`
- Let DeepSeek inside opencode / Claude Code / Codex see images (see MCP section below)
- Live screen monitoring: `python watch.py screen`
- Analyze a video: `python watch.py video video.mp4`
- Camera monitoring: `python watch.py camera`

A vision Q&A round trip 鈥?the model describes what it sees, then identifies the subject:

![Vision Q&A example](photo/05-identify-role.png)

## Quick start

On Windows double-click `setup.bat`, or run `python setup.py` on any platform:

1. **Paste your primary API key**: in opencode run `/connect`, pick OpenCode Zen, copy the key from the opened page

   ![OpenCode Zen API key page](photo/04-zen-api-key.png)

2. **(Optional) Add a fallback**: paste a Zhipu key (`glm-4.1v-thinking-flash`, free) 鈥?auto-switches if the primary fails
3. **Done**: `python vision.py image.png` just works

## Configuration

Create a `.env` file next to `vision.py`. The three primary lines are required; everything else is optional:

| Variable | Required | Description |
|---|---|---|
| `VISION_API_KEY` | Yes | Primary API key (OpenCode Zen) |
| `VISION_BASE_URL` | No (default) | `https://opencode.ai/zen/v1` |
| `VISION_MODEL` | Yes | Primary model `mimo-v2.5-free` |
| `FALLBACK_API_KEY` | No | Fallback API key (Zhipu, free) |
| `FALLBACK_BASE_URL` | No | `https://open.bigmodel.cn/api/paas/v4` |
| `FALLBACK_MODEL` | No | Fallback model `glm-4.1v-thinking-flash` |
| `VISION3_API_KEY` etc. | No | More fallback sources (optional) |
| `LANG` | No | `zh` (Chinese) or `en` (English); defaults to Chinese |

```dotenv
VISION_API_KEY=oc-...
VISION_BASE_URL=https://opencode.ai/zen/v1
VISION_MODEL=mimo-v2.5-free
FALLBACK_API_KEY=your-zhipu-key
FALLBACK_BASE_URL=https://open.bigmodel.cn/api/paas/v4
FALLBACK_MODEL=glm-4.1v-thinking-flash
LANG=zh
```

![The .env file](photo/03-env-config.png)

> Save it with any text editor 鈥?the script handles Windows encoding quirks automatically.

### Adding a model source

Want a third or fourth vision source? Copy three lines, incrementing the number:

```dotenv
VISION3_API_KEY=your-key
VISION3_BASE_URL=https://your-endpoint/v1
VISION3_MODEL=your-model-id
```

Rules: name them `VISION{N}_API_KEY` / `VISION{N}_BASE_URL` / `VISION{N}_MODEL`, N starting at 3; the endpoint must be OpenAI-compatible and accept `image_url`; once filled they join the failover chain (zen 鈫?zhipu 鈫?v3 鈫?v4 鈫?...); force one with `/vision-model v3`.

## MCP integration (let agents see images)

MCP is a protocol that lets agents call external tools. This project's `mcp_server.py` provides three tools:

| Tool | Purpose | Example |
|---|---|---|
| `describe_image` | Describe / answer questions about an image | Let DeepSeek analyze a screenshot |
| `ocr_image` | Transcribe visible text verbatim | Read an error dialog |
| `set_vision_model` | Switch the vision model | Use Zhipu, or back to auto |

**Step 1 鈥?install the dependency:**

```powershell
pip install "mcp>=1.0,<2"
```

**Step 2 鈥?wire it into your agent** (pick one)

**opencode:**
1. Find the config file `~/.config/opencode/opencode.jsonc` (on Windows it lives in `.config\opencode\opencode.jsonc` under your user directory)
2. Open it in a text editor, add inside the `"mcp": { ... }` braces:

   ```jsonc
   "vision": {
     "type": "local",
     "command": ["python", "YOUR-ABSOLUTE-PATH\\mcp_server.py"],
     "environment": { "CODEX_VISION_PROXY_ENV": "YOUR-ABSOLUTE-PATH\\.env" },
     "enabled": true
   }
   ```

   Replace `YOUR-ABSOLUTE-PATH` with the full folder path containing `mcp_server.py` (e.g. `D:\tools\zen-vision`)
3. Save, then **fully quit and reopen opencode**
4. Verify: run `opencode mcp list` 鈥?you should see `vision connected`

**Claude Code:** run one command (replace the path):

```powershell
claude mcp add vision -s user -e "CODEX_VISION_PROXY_ENV=YOUR-ABSOLUTE-PATH\.env" -- python YOUR-ABSOLUTE-PATH\mcp_server.py
```

After restarting, `claude mcp list` should show `vision ... Connected`.

**Codex CLI:**
1. Edit `~/.codex/config.toml`
2. Append at the end:

   ```toml
   [mcp_servers.vision]
   command = "python"
   args = ["YOUR-ABSOLUTE-PATH\\mcp_server.py"]
   env = { CODEX_VISION_PROXY_ENV = "YOUR-ABSOLUTE-PATH\\.env" }
   ```

3. Restart Codex

**Step 3 鈥?use it.** Once wired up, just say: "look at this image `YOUR-IMAGE-PATH\shot.png`" 鈥?the agent calls the tool automatically.

> Back up config files before editing. All paths above are placeholders 鈥?replace them with your own.

## How it works

```
Your text-only model (DeepSeek)
        鈹? asks to "see" an image
        鈻?vision.py / mcp_server.py
        鈹? image -> base64 data URL
        鈻?Vision API (multi-source: zen 鈫?zhipu 鈫?v3 鈫?...)
        鈹? model describes the image
        鈻?text description / verbatim OCR
        鈻?DeepSeek (text-only) 鈫?now it "sees"
```

The image never reaches DeepSeek. A vision model describes it, and the description is what your text-only model reasons over 鈥?*Describe-then-Reason* ([Prism](https://arxiv.org/abs/2406.14544), NeurIPS 2024).

## Security

- `.env` (API keys) and the `.vision-model` state file are gitignored 鈥?never committed
- Free models may collect data during the free period 鈥?don't send passwords or sensitive screenshots
- Free tiers are time-limited; if a source goes away, the failover chain takes over, or change the `.env` endpoint

## Going deeper

| File | Purpose |
|---|---|
| `vision.py` | Single-file CLI: describe / Q&A / OCR / model-switch commands |
| `mcp_server.py` | MCP server: `describe_image` / `ocr_image` / `set_vision_model` |
| `setup.py` / `setup.bat` | One-click setup |
| `.env.example` | Configuration template |
| `watch.py` | Live vision: monitor screen/video/camera, describe on change |
| `photo/` | Screenshots used in this README |

FAQ:

**Why `requests` and not `urllib`?** `urllib`'s TLS fingerprint gets flagged by Cloudflare in front of OpenCode Zen (403, error code 1010); `requests` passes.

**Why read `.env` with `utf-8-sig`?** Windows PowerShell writes a BOM, which would silently break key matching; `utf-8-sig` strips it.

**Which free Zen models can see images?** Only `mimo-v2.5-free` accepts image input; the other free models reject images with HTTP 400.

## Credits

Inspired by and largely built on [Anionex/codex-vision-proxy](https://github.com/Anionex/codex-vision-proxy) (MIT) 鈥?a beautifully small image-to-text toolkit. This repo adapts it to OpenCode Zen's free tier, adds Windows pitfall fixes, and packages it as a single self-contained script.

## Changelog

### v1.2.0
- New live-vision `watch.py`: monitor screen / video / camera; local pixel-diff change detection (zero API calls), describes only on change; debounce + cooldown to avoid false/duplicate reports

### v1.1.0
- Multi-source failover: primary OpenCode Zen, fallback Zhipu (free); extend with `VISION3_*`/`VISION4_*`...
- `/vision-model` command: view/switch model at runtime, with `/` `/help` help menu
- MCP `set_vision_model` tool added
- Fix: fallback model changed to tested `glm-4.1v-thinking-flash`

### v1.0.0
- Initial release: single source (OpenCode Zen `mimo-v2.5-free`), describe/Q&A/OCR, one-click setup, bilingual README

## License

[MIT](LICENSE)
