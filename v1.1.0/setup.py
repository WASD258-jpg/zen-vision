#!/usr/bin/env python3
"""zen-vision 一键配置：环境检查 -> 装依赖 -> 填 key -> 测试 -> 可选接入 MCP。
Windows 用户直接双击 setup.bat 即可。"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"


def step(msg):
    print(f"\n==> {msg}")


def ask(question, default="y"):
    answer = input(f"{question} [{'Y/n' if default == 'y' else 'y/N'}] ").strip().lower()
    if not answer:
        return default == "y"
    return answer in ("y", "yes")


def pip_install(package):
    print(f"安装 {package} ...")
    r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", package])
    if r.returncode != 0:
        sys.exit(f"安装 {package} 失败，请检查网络后重试")


def ensure_env():
    if ENV_FILE.exists():
        print("已检测到 .env，跳过配置。")
        return
    key = input("粘贴你的主源 API key（OpenCode Zen 的，去 opencode 里 /connect 选 OpenCode Zen 拿，免费）: ").strip()
    if not key:
        sys.exit("key 不能为空，本次配置取消（已安装的依赖不受影响）")
    lines = [
        f"VISION_API_KEY={key}",
        "VISION_BASE_URL=https://opencode.ai/zen/v1",
        "VISION_MODEL=mimo-v2.5-free",
    ]
    if ask("要不要配一个备用源（主源挂了自动切换，防单点故障）？", default="n"):
        fkey = input("备用源 API key（智谱 GLM-4.1V-Thinking-Flash 免费，去 bigmodel.cn 注册拿）: ").strip()
        if fkey:
            lines += [
                f"FALLBACK_API_KEY={fkey}",
                "FALLBACK_BASE_URL=https://open.bigmodel.cn/api/paas/v4",
                "FALLBACK_MODEL=glm-4.1v-thinking-flash",
            ]
    lines.append("LANG=zh")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("已生成 .env（此文件不会上传到 GitHub）")


def run_test():
    if not ask("现在测一张图？能正常出描述就说明配置成功了"):
        return
    path = input("把图片拖进来或输入完整路径: ").strip().strip('"')
    if not path:
        print("跳过测试。")
        return
    import vision
    try:
        text = vision.ask([vision.data_url(path)], "请简要描述这张图片。")
        print("\n--- 测试结果 ---")
        print(text)
        print("-----------------")
        print("配置成功！以后直接: python vision.py 图片.png [-q 问题] [--ocr]")
    except BaseException as e:
        print(f"测试失败：{e}，请检查 key 是否正确、网络是否通畅。")


def setup_mcp():
    if not ask("要不要接入 MCP（让 opencode / Claude Code / Codex 里的 deepseek 直接看图）？", default="n"):
        return
    pip_install("mcp>=1.0,<2")
    codex()
    claude()
    opencode()


def codex():
    cfg = Path(os.environ.get("USERPROFILE", Path.home())) / ".codex/config.toml"
    if not cfg.exists():
        print("未检测到 Codex，跳过。")
        return
    if "mcp_servers.vision" in cfg.read_text(encoding="utf-8", errors="ignore"):
        print("Codex 已配置过 vision，跳过。")
        return
    if not ask("接入 Codex（~/.codex/config.toml，自动备份）？"):
        return
    shutil.copy(cfg, str(cfg) + ".bak")
    cfg.open("a", encoding="utf-8").write(
        "\n[mcp_servers.vision]\n"
        f'command = "python"\n'
        f'args = ["{ROOT / "mcp_server.py"}"]\n'
        f'env = {{ CODEX_VISION_PROXY_ENV = "{ENV_FILE}" }}\n'
    )
    print("Codex 已接入。")


def claude():
    if not shutil.which("claude"):
        print("未检测到 Claude Code，跳过。")
        return
    if not ask("接入 Claude Code（claude mcp add）？"):
        return
    cmd = [
        "claude", "mcp", "add", "vision", "-s", "user",
        "-e", f"CODEX_VISION_PROXY_ENV={ENV_FILE}",
        "--", sys.executable, str(ROOT / "mcp_server.py"),
    ]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print("自动配置失败，可手动执行（Windows 注意：claude 若是 .ps1 shim 请直接调 claude.exe）:")
        print("  " + " ".join(cmd))


def opencode():
    cfg = Path(os.environ.get("USERPROFILE", Path.home())) / ".config/opencode/opencode.jsonc"
    if not cfg.exists():
        print("未检测到 opencode，跳过。")
        return
    print("\nopencode 请在 opencode.jsonc 的 mcp 节点里加（自动改 JSONC 容易出错，留给你贴）:")
    print("  \"vision\": {")
    print("    \"type\": \"local\",")
    print(f"    \"command\": [\"python\", \"{ROOT / 'mcp_server.py'}\"],")
    print(f"    \"environment\": {{ \"CODEX_VISION_PROXY_ENV\": \"{ENV_FILE}\" }},")
    print("    \"enabled\": true")
    print("  }")


def main():
    print("zen-vision 一键配置")
    print("===================")
    step("1/4 检查 Python")
    if sys.version_info < (3, 11):
        sys.exit("需要 Python 3.11+，当前 " + sys.version.split()[0])
    print("OK: " + sys.version.split()[0])
    step("2/4 安装依赖")
    pip_install("requests")
    step("3/4 配置 .env")
    ensure_env()
    step("4/4 测试 + 可选 MCP")
    run_test()
    setup_mcp()
    print("\n全部完成！用法：python vision.py 图片.png [-q 问题] [--ocr]")


if __name__ == "__main__":
    main()
