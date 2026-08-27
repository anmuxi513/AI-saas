"""打包脚本：把 AImomo 门户打包成单个 exe（PyInstaller onefile）。

用法:
    python scripts/build_portal.py          # 默认: 打包门户（单个 AImomo.exe）
    python scripts/build_portal.py onefile  # 同上（显式）
    python scripts/build_portal.py onedir   # 目录版（调试用，启动更快）
    python scripts/build_portal.py downloader  # 可选: 独立模型下载工具（一般不需要）

产物:
    dist_portal/AImomo.exe       单文件桌面应用（双击即用，无黑窗）
    内置: 前端页面 + MNIST/EuroSAT 模型 + 应用内模型下载

说明:
    - 聊天模型（Qwen 约 1GB）不入包，由应用内「下载聊天模型」功能按需安装
    - 打包前请先 `cd frontend && npm run build` 确保 dist 最新
    - 首次启动 onefile 会解压到临时目录，稍慢属正常现象
"""
import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台默认 GBK，强制 UTF-8

import PyInstaller.__main__

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SEP = os.pathsep  # Windows: ';'
APP_NAME = "AImomo"


def data(src, dst):
    """--add-data 参数格式: 源路径;目标路径（打包后位于 _MEIPASS 下）"""
    return os.path.join(ROOT, src) + SEP + dst


def build(entry, name, work, extra=None, excludes=None, onefile=True, console=False):
    args = [
        entry,
        "--name", name,
        "--onefile" if onefile else "--onedir",
        "--noconfirm",
        "--clean",
        "--console" if console else "--noconsole",
        "--distpath", os.path.join(ROOT, "dist_portal"),
        "--workpath", os.path.join(ROOT, "build_portal", work),
        "--specpath", os.path.join(ROOT, "build_portal", work),
        "--icon", os.path.join(ROOT, "assets", "app.ico"),
        # 排除无用大模块（gradio 已退役；tkinter/matplotlib 用不到）
        "--exclude-module", "gradio",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "pydoc",
        "--exclude-module", "test",
    ]
    if excludes:
        args += excludes
    if extra:
        args += extra
    PyInstaller.__main__.run(args)


def build_portal(onefile=True):
    index = os.path.join(ROOT, "frontend", "dist", "index.html")
    if not os.path.isfile(index):
        print(f"❌ 缺少前端构建产物: {index}")
        print("   请先执行: cd frontend && npm run build")
        sys.exit(1)

    resources = [
        data("frontend/dist", "frontend/dist"),
        data("projects/mnist/deploy/mnist_cnn.onnx", "models"),
        data("projects/eurosat/models/eurosat_resnet18.onnx", "models"),
        data("datasets/eurosat/class_names.json", "datasets/eurosat"),
    ]
    add_data = []
    for r in resources:
        add_data += ["--add-data", r]
    # 让分析阶段能找到 projects/chat（app.py 运行时才 insert sys.path）
    add_data += ["--paths", os.path.join(ROOT, "projects", "chat")]
    # 桌面窗口（pywebview）：收集 WebView2 DLL + 后端模块（动态选择）+ 启动画面
    import webview as _wv
    wv_lib = os.path.join(os.path.dirname(_wv.__file__), "lib")
    add_data += ["--add-data", wv_lib + SEP + "webview/lib"]
    add_data += ["--hidden-import", "webview.platforms.edgechromium"]
    add_data += ["--add-data", os.path.join(ROOT, "server", "splash.html") + SEP + "splash.html"]

    mode = "单文件 exe" if onefile else "目录版"
    print(f"🔨 打包 AImomo（{mode}，含 ONNX 模型 + 前端）...")
    build("server/desktop.py", APP_NAME, "portal", add_data, onefile=onefile)
    return os.path.join(ROOT, "dist_portal", APP_NAME + ".exe" if onefile else APP_NAME)


def build_downloader():
    print("🔨 打包聊天模型下载工具（可选）...")
    excludes = []
    for mod in ("torch", "transformers", "torchvision", "onnxruntime",
                "pandas", "PIL", "IPython", "jedi", "matplotlib", "gradio"):
        excludes += ["--exclude-module", mod]
    build("server/tools/download_chat_model.py", "下载聊天模型", "downloader",
          excludes=excludes, onefile=True, console=True)
    return os.path.join(ROOT, "dist_portal", "下载聊天模型.exe")


def report(paths):
    print("\n✅ 打包完成！产物目录: dist_portal/")
    for p in paths:
        if os.path.isdir(p):
            total = sum(f.stat().st_size for f in os.scandir(p) if f.is_file())
            internal = os.path.join(p, "_internal")
            if os.path.isdir(internal):
                total += sum(f.stat().st_size
                             for f in os.scandir(internal) if f.is_file())
            for root, dirs, files in os.walk(os.path.join(p, "_internal")):
                if root == internal:
                    continue
                total += sum(os.path.getsize(os.path.join(root, f)) for f in files)
            print(f"   {os.path.basename(p)}: {total / 1024 / 1024:.0f} MB")
        else:
            print(f"   {os.path.basename(p)}: {os.path.getsize(p) / 1024 / 1024:.0f} MB")
    print("   双击「AImomo.exe」启动，桌面应用直接打开")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?",
                        choices=["onefile", "onedir", "downloader"], default="onefile")
    args = parser.parse_args()

    os.chdir(ROOT)
    if args.target == "onefile":
        report([build_portal(onefile=True)])
    elif args.target == "onedir":
        report([build_portal(onefile=False)])
    else:
        report([build_downloader()])


if __name__ == "__main__":
    main()
