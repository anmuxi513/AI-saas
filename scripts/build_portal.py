"""打包脚本：把统一门户服务打包成绿色版（PyInstaller onedir）。

用法:
    python scripts/build_portal.py            # 打包全部
    python scripts/build_portal.py portal     # 只打包门户服务
    python scripts/build_portal.py downloader # 只打包聊天模型下载工具

产物:
    dist_portal/AI训练平台.exe        门户服务（双击启动）
    dist_portal/下载聊天模型.exe       一键下载 Qwen 模型（约 1GB，国内镜像）

说明:
    - 打包包含: 前端构建产物 + MNIST/EuroSAT ONNX 模型 + 类别表
    - 不包含: Qwen 聊天权重（用户运行「下载聊天模型.exe」按需获取）
    - 两个程序必须分开构建目录，避免 PyInstaller 模块图缓存串包
      （否则下载工具会错误带上门户的 torch/transformers 依赖）
    - 打包前请先 `cd frontend && npm run build` 确保 dist 最新
"""
import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台默认 GBK，强制 UTF-8

import PyInstaller.__main__

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SEP = os.pathsep  # Windows: ';'


def data(src, dst):
    """--add-data 参数格式: 源路径;目标路径（打包后位于 _MEIPASS 下）"""
    return os.path.join(ROOT, src) + SEP + dst


def build(entry, name, work, extra=None, excludes=None):
    args = [
        entry,
        "--name", name,
        "--onedir",
        "--noconfirm",
        "--clean",
        "--console",
        "--distpath", os.path.join(ROOT, "dist_portal"),
        "--workpath", os.path.join(ROOT, "build_portal", work),
        "--specpath", os.path.join(ROOT, "build_portal", work),
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


def build_portal():
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

    print("🔨 打包门户服务（含 ONNX 模型 + 前端）...")
    build("server/app.py", "AI训练平台", "portal", add_data)
    return os.path.join(ROOT, "dist_portal", "AI训练平台")


def build_downloader():
    print("🔨 打包聊天模型下载工具...")
    # 强制排除门户的大依赖（PyInstaller 模块图磁盘缓存可能串包，双保险）
    excludes = []
    for mod in ("torch", "transformers", "torchvision", "onnxruntime",
                "pandas", "PIL", "IPython", "jedi", "matplotlib", "gradio"):
        excludes += ["--exclude-module", mod]
    build("server/tools/download_chat_model.py", "下载聊天模型", "downloader", excludes=excludes)
    return os.path.join(ROOT, "dist_portal", "下载聊天模型")


def report(paths):
    print("\n✅ 打包完成！产物目录: dist_portal/")
    for p in paths:
        if os.path.isdir(p):
            total = sum(f.stat().st_size
                        for f in os.scandir(p) if f.is_file())
            internal = os.path.join(p, "_internal")
            if os.path.isdir(internal):
                total += sum(f.stat().st_size
                             for f in os.scandir(internal) if f.is_file())
            # _internal 子目录（torch 等）递归统计
            for root, dirs, files in os.walk(os.path.join(p, "_internal")):
                if root == internal:
                    continue
                total += sum(os.path.getsize(os.path.join(root, f)) for f in files)
            print(f"   {os.path.basename(p)}: {total / 1024 / 1024:.0f} MB")
    print("   双击「AI训练平台.exe」启动，浏览器打开 http://localhost:6660")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", choices=["portal", "downloader", "all"], default="all")
    args = parser.parse_args()

    os.chdir(ROOT)
    if args.target == "all":
        # 必须在独立进程分别打包：PyInstaller 模块图缓存进程级共享，
        # 同进程连续打包会把门户的 torch/transformers 依赖串进下载工具
        import subprocess
        subprocess.run([sys.executable, os.path.abspath(__file__), "portal"], check=True)
        subprocess.run([sys.executable, os.path.abspath(__file__), "downloader"], check=True)
        report([os.path.join(ROOT, "dist_portal", "AI训练平台"),
                os.path.join(ROOT, "dist_portal", "下载聊天模型")])
        return

    built = []
    if args.target == "portal":
        built.append(build_portal())
    else:
        built.append(build_downloader())
    report(built)


if __name__ == "__main__":
    main()
