# zen-vision

给纯文本模型（DeepSeek 等）装上眼睛：用**免费多模态模型**把图片转成文字描述，零成本、零下载、单文件脚本。

## 版本

| 版本 | 状态 | 核心内容 |
|---|---|---|
| [v1.1.0](v1.1.0/) | 最新 | 多源自动切换（OpenCode Zen + 智谱备用）、`/vision-model` 运行时换模型、MCP `set_vision_model` 工具、指令帮助菜单 |
| [v1.0.0](v1.0.0/) | 已发布 | 单源（OpenCode Zen `mimo-v2.5-free`）、描述/问答/OCR、一键配置、双语 README |

每个版本目录自带完整 README 与脚本。使用前进入对应版本目录执行 `setup.bat`（Windows）或 `python setup.py`，按引导填入 API key。

## 快速使用

```powershell
cd v1.1.0
python vision.py 图片.png [-q 问题] [--ocr]     # 看图
python vision.py /vision-model list             # 查看/切换视觉模型
```

## 安全说明

- `.env`（含 API key）与 `.vision-model` 均被 `.gitignore` 忽略，**不会进入仓库**
- 所有版本目录相同规则
