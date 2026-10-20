"""服务器环境检查：核数、Python / numpy / scipy 版本、能否访问 LLM 接口（只测连通，不发送也不打印密钥）。"""
import json, multiprocessing as mp, os, platform, sys, urllib.request
import common as C

print("Python", sys.version.split()[0], platform.platform())
print("CPU 核数", mp.cpu_count(), "→ auto 会用", C.nprocs("auto"), "个进程")
try:
    import numpy; print("numpy", numpy.__version__)
except Exception as e:
    print("缺 numpy：", e)
try:
    import scipy; print("scipy", scipy.__version__)
except Exception:
    print("缺 scipy（分析脚本需要）：pip install scipy")
tr, te = C.I.split()
print("训练实例", len(tr), "测试实例", len(te))
cfg = os.path.join(C.EXP0, "llm_config.json")
try:
    base = json.load(open(cfg, encoding="utf-8"))["api_base"].rstrip("/")
    try:
        urllib.request.urlopen(urllib.request.Request(base, method="HEAD"), timeout=8)
        print("LLM 接口可以访问：", base)
    except urllib.error.HTTPError as e:
        print("LLM 接口可以访问（HTTP", e.code, "，属正常）：", base)
    except Exception as e:
        print("LLM 接口访问不了：", base, type(e).__name__, "→ LLM 部分留在 Windows 上跑")
except Exception as e:
    print("没读到 llm_config.json：", e)
