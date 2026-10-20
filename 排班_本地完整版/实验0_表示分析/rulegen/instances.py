"""实例列表、读取、下界与训练/测试划分。"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import exp0lib as L  # noqa: E402

FEAT_DIR = os.path.join(os.path.dirname(HERE), "out9")
MAIN = ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]
FAM1 = sorted(f[:-5] for f in os.listdir(os.path.join(L.SRC, "requests_family")))
FAM2 = sorted(f[:-5] for f in os.listdir(os.path.join(L.SRC, "requests_family2")))
EXCLUDE = {"E12_1080h", "E23_1080h"}          # 所有方法都没有可行解


def path(inst):
    for d in ("requests", "requests_family", "requests_family2"):
        p = os.path.join(L.SRC, d, inst + ".json")
        if os.path.exists(p):
            return p
    raise FileNotFoundError(inst)


_cache = {}


def load(inst):
    if inst not in _cache:
        _cache[inst] = L.M.load_scenario(path(inst))
    return _cache[inst]


def lb(inst):
    """资源数下界（来自 features8 输出）"""
    return json.load(open(os.path.join(FEAT_DIR, inst + ".json"), encoding="utf-8"))["LB"]


def group(inst):
    return inst[0] if inst[0] in "EHM" and inst[1].isdigit() else "原"


def split():
    """训练集：新实例族（requests_family2）中每组按编号每隔 3 个取 1 个，共 15 个；其余全部为测试集（含原 16 个实例）。
    训练集只用于规则生成时的打分，测试集在规则确定后才使用。"""
    fam2 = [i for i in FAM2 if i not in EXCLUDE]
    train = []
    for g in "EHM":
        gi = [i for i in fam2 if i[0] == g]
        train += gi[::3][:5]
    test = [i for i in MAIN + FAM1 + fam2 if i not in train and i not in EXCLUDE]
    return train, test


if __name__ == "__main__":
    tr, te = split()
    print("训练", len(tr), tr)
    print("测试", len(te))
