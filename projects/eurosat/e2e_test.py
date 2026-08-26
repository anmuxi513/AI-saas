"""端到端测试: 用真实 EuroSAT 测试图验证部署服务 (模拟浏览器前端)。"""
import base64
import json
import random
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import urllib.request

# ---------- 路径 (数据集在仓库根 datasets/) ----------
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", ".."))
DATA_DIR = os.path.join(ROOT, "datasets", "eurosat")

# 从测试划分里随机抽 8 张真实遥感图
with open(os.path.join(DATA_DIR, "eurosat-test.txt")) as f:
    test_names = [line.strip() for line in f if line.strip()]
random.seed(7)
sample_names = random.sample(test_names, 8)

CN = {
    "AnnualCrop": "农作物", "Forest": "森林", "HerbaceousVegetation": "草本植被",
    "Highway": "高速公路", "Industrial": "工业区", "Pasture": "牧场",
    "PermanentCrop": "多年生作物", "Residential": "居民区", "River": "河流", "SeaLake": "海洋/湖泊",
}

ok = 0
for name in sample_names:
    cls = name.split("_")[0]
    path = os.path.join(DATA_DIR, "2750", cls, name)
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    req = urllib.request.Request(
        "http://localhost:8001/api/predict",
        data=json.dumps({"image": b64}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    top = data["results"][0]
    hit = top["name"] == CN.get(cls, cls)
    ok += hit
    mark = "✅" if hit else "❌"
    print(f"{mark} 真实: {CN.get(cls, cls):8s} | 预测: {top['name']:8s} ({top['prob']:.1%})")

print(f"\n端到端验证: 8 张猜对 {ok} 张 (服务 = 网页前端的后端)")
