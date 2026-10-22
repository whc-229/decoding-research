"""臂的统一写法（测试集验证、采集共用）：
  dec5                         逐班基因（容量预判 + 回溯修复）
  K0.25:default                稀疏偏离 + 默认规则（= dec9）
  K0.25:<规则文件.py>          稀疏偏离 + 规则代码（LLM / GP 导出的规则，经 compile_rule 受限执行）；相对路径相对 rulegen/
  K0.25:nn:<参数.npz>          稀疏偏离 + 神经网络规则；相对路径相对 neural/
  X0.75:<规则写法>             扩展布局的稀疏偏离（ruledec_ext，任务 D），规则写法同 K 开头；基因长度随 K 变化，见 nvar()
CSV 里的臂名可以另起：  显示名=写法，例如  K0.25:LLM(r35)=K0.25:out/score/best_rule.py
"""
import os
import common as C
import nnrule as N

_cache = {}


def parse(s):
    """'名=写法' → (名, 写法)"""
    if "=" in s:
        a, b = s.split("=", 1)
        return a, b
    return s, s


def rule_of(spec):
    if spec in _cache:
        return _cache[spec]
    k, src = spec.split(":", 1)                  # k = K0.25 / X0.75 之类，规则只看 src
    if src == "default":
        rule = C.R.default_rule
    elif src.startswith("nn:"):
        p = src[3:]
        rule = N.load(p if os.path.isabs(p) else os.path.join(C.HERE, p))
    else:
        p = src if os.path.isabs(src) else os.path.join(C.RULEGEN, src)
        rule = C.R.compile_rule(open(p, encoding="utf-8").read())
    _cache[spec] = rule
    return rule


def decoder(spec):
    """写法 → 解码函数 (sc, x) → Result"""
    if spec == "dec5":
        return lambda sc, x: C.L.decode(sc, x, "dec5")
    kf = float(spec.split(":", 1)[0][1:])
    rule = rule_of(spec)
    if spec[0] == "X":
        import ruledec_ext as X
        return lambda sc, x: X.decode_rule(sc, x, rule, kf)
    return lambda sc, x: C.R.decode_rule(sc, x, rule, kf)


def nvar(spec, sc):
    """写法 → 基因长度：dec5 与 K 开头的原布局都是 nvar(dec5)；X 开头的扩展布局随 K 变化"""
    if spec[0] == "X":
        import ruledec_ext as X
        return X.nvar(sc, float(spec.split(":", 1)[0][1:]))
    return C.L.nvar(sc, "dec5")
