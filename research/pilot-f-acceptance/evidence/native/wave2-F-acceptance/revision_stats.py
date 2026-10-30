# -*- coding: utf-8 -*-
"""revision_stats.py — F 论文 Major Revision 所需全部数字的一次性复算。

预注册口径（与 main.tex / FINDINGS-F01.md 一致）：
  区域：n = 26..500，c = 0..n//2（b = n - c >= c，镜像对称半平面），共 62,819 格。
  p_code   = 2·Q(|b-c|/sqrt(n))            （被审 fallback，无连续性校正）
  p_exact  = min(1, 2·P(X <= c)),  X ~ Bin(n, 0.5)   （双侧 exact，倍增口径）
  p_cc     = P(chi2_1 >= (|b-c|-1)^2/n)    （标准 Edwards/Yates 连续性校正 McNemar）
  p_midp   = min(1, 2·P(X<=c) - P(X=c))    （双侧 mid-p）
  p_1s     = P(X <= c)                     （名义 α=0.05 单侧 exact 基准）
  p_chi2   = P(chi2_1 >= (b-c)^2/n)        （被审文件中的 chi2 变体）
  决策：p < 0.05 → promote；flip = 与 p_exact 的决策不一致。
"""
import json
import math
from scipy.stats import binomtest, chi2 as chi2_dist, norm

OUT = {}
Q = norm.sf  # survival function of standard normal

def p_code(b, c):
    n = b + c
    z = abs(b - c) / math.sqrt(n)
    return 2.0 * Q(z)

def p_exact(b, c):
    n = b + c
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2.0 ** n
    return min(1.0, 2.0 * tail)

def p_cc(b, c):
    n = b + c
    d = abs(b - c)
    if d == 0:
        return 1.0
    return float(chi2_dist.sf((d - 1) ** 2 / n, 1))

def p_midp(b, c):
    n = b + c
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2.0 ** n
    pmass = math.comb(n, k) / 2.0 ** n
    return min(1.0, max(0.0, 2.0 * tail - pmass))

def p_1s(b, c):
    n = b + c
    k = min(b, c)
    return sum(math.comb(n, i) for i in range(k + 1)) / 2.0 ** n

def p_chi2(b, c):
    n = b + c
    if b == c:
        return 1.0
    return float(chi2_dist.sf((b - c) ** 2 / n, 1))

# ---------- 1. 基础面 ----------
cells = 0
promo_code = 0
flips_code = 0            # code promotes, exact withholds (anti-conservative)
flips_code_cons = 0       # code withholds, exact promotes (conservative)
maxabs_code = 0.0; maxabs_code_at = None
ratio_max = 0.0; ratio_max_at = None
pcode_gt_pexact = 0; pcode_gt_max = 0.0; pcode_gt_c7 = 0
exemplar = None
rate200 = [0, 0]          # [flips, promotions] n<=200
for n in range(26, 501):
    for c in range(0, n // 2 + 1):
        b = n - c
        cells += 1
        pc, pe = p_code(b, c), p_exact(b, c)
        promo = pc < 0.05
        promo_code += promo
        epromo = pe < 0.05
        if promo and not epromo:
            flips_code += 1
            r = pe / pc   # strictness ratio: exact p / code p at promoted-then-withheld cells
            if r > ratio_max:
                ratio_max, ratio_max_at = r, (b, c, n)
        if epromo and not promo:
            flips_code_cons += 1
        if abs(pc - pe) > maxabs_code:
            maxabs_code, maxabs_code_at = abs(pc - pe), (b, c, n)
        if pc > pe:
            pcode_gt_pexact += 1
            pcode_gt_max = max(pcode_gt_max, pc)
            if c <= 7:
                pcode_gt_c7 += 1
        if (b, c) == (26, 0):
            exemplar = {"p_code": pc, "p_exact": pe}
        if n <= 200:
            if promo and not epromo:
                rate200[0] += 1
            if promo:
                rate200[1] += 1
OUT["basic"] = {
    "cells": cells, "promotions_code": promo_code, "flips_anti_cons": flips_code,
    "flips_cons": flips_code_cons, "max_abs_err_code": maxabs_code,
    "max_abs_err_at": maxabs_code_at, "flip_rate_bound500": flips_code / promo_code,
    "flip_rate_bound200": rate200[0] / rate200[1], "promotions_bound200": rate200[1],
    "flips_bound200": rate200[0],
    "pcode_gt_pexact_count": pcode_gt_pexact, "pcode_gt_pexact_max_pcode": pcode_gt_max,
    "pcode_gt_pexact_c_le_7": pcode_gt_c7, "exemplar_26_0": exemplar,
    # promotion-ratio = p_exact / p_code among flips (how much stricter the
    # exact reference is at the cells it withholds); max = 1.525 @ (19,8,27).
    "max_strictness_ratio_flip": ratio_max, "max_strictness_ratio_at": ratio_max_at,
}

# ---------- 2. 三方对比：CC 与 mid-p ----------
def variant_flips(pf):
    anti = cons = 0
    maxabs = 0.0; at = None
    ex18 = None
    for n in range(26, 501):
        for c in range(0, n // 2 + 1):
            b = n - c
            pv, pe = pf(b, c), p_exact(b, c)
            if pv < 0.05 and pe >= 0.05:
                anti += 1
            if pe < 0.05 and pv >= 0.05:
                cons += 1
            if abs(pv - pe) > maxabs:
                maxabs, at = abs(pv - pe), (b, c, n)
            if (b, c) == (18, 8):
                ex18 = pv
    return {"flips_anti_cons": anti, "flips_cons": cons, "max_abs_err": maxabs,
            "max_abs_err_at": at, "p_at_18_8_26": ex18}

OUT["cc"] = variant_flips(p_cc)
OUT["midp"] = variant_flips(p_midp)

# ---------- 3. 名义 α=0.05 单侧 exact 基准的方向对比 ----------
anti_1s = cons_1s = 0
ex_1s = None
for n in range(26, 501):
    for c in range(0, n // 2 + 1):
        b = n - c
        promo_code_ = p_code(b, c) < 0.05
        promo_1s = p_1s(b, c) < 0.05
        if promo_1s and not promo_code_:
            cons_1s += 1          # code withholds, benchmark promotes => conservative
        if promo_code_ and not promo_1s:
            anti_1s += 1          # code promotes, benchmark withholds => anti-conservative
        if (b, c) == (18, 8):
            ex_1s = {"p_code": p_code(b, c), "p_1s_exact": p_1s(b, c)}
OUT["benchmark_1s_nominal"] = {"conservative_cells": cons_1s, "anti_cons_cells": anti_1s,
                               "exemplar_18_8_26": ex_1s}

# ---------- 4. chi2 变体（§5 行校准） ----------
def chi2_flips(bound):
    anti = cons = 0
    maxabs = 0.0
    for n in range(26, bound + 1):
        for c in range(0, n // 2 + 1):
            b = n - c
            pv, pe = p_chi2(b, c), p_exact(b, c)
            if pv < 0.05 and pe >= 0.05:
                anti += 1
            if pe < 0.05 and pv >= 0.05:
                cons += 1
            maxabs = max(maxabs, abs(pv - pe))
    return {"flips_anti_cons": anti, "flips_cons": cons, "max_abs_err": maxabs}

OUT["chi2_bound200"] = chi2_flips(200)
OUT["chi2_bound500"] = chi2_flips(500)

# ---------- 4b. chi2 平局退化分解（stats.py:215 未钳制 vs 钳制口径） ----------
# 被审实现：chi2 = (|b-c|-1)^2/n 在 b==c 时得 1/n（应为 0）→ p=chi2.sf(1/n,1)
# 钳制口径（d==0 → p=1.0）隔离出「平局伪影」与「真渐近误差」两个成分。
def chi2_decomp(bound):
    tie_err = 0.0; tie_at = None
    nontie_err = 0.0; nontie_at = None
    tie_cells = 0
    flips_cons = flips_anti = 0
    for n in range(26, bound + 1):
        for c in range(0, n // 2 + 1):
            b = n - c
            d = abs(b - c)
            pe = p_exact(b, c)
            if d == 0:
                tie_cells += 1
                pv = float(chi2_dist.sf(1.0 / n, 1))   # unclamped, audited form
                if abs(pv - pe) > tie_err:
                    tie_err, tie_at = abs(pv - pe), (b, c, n)
                if pe < 0.05: flips_cons += 1
                continue
            pv = p_cc(b, c)   # clamped variant
            if abs(pv - pe) > nontie_err:
                nontie_err, nontie_at = abs(pv - pe), (b, c, n)
            if pe < 0.05 and pv >= 0.05: flips_cons += 1
            if pv < 0.05 and pe >= 0.05: flips_anti += 1
    return {"tie_cells": tie_cells, "tie_artifact_max_err": tie_err, "tie_at": tie_at,
            "nontie_asym_max_err": nontie_err, "nontie_at": nontie_at,
            "flips_cons": flips_cons, "flips_anti": flips_anti}

OUT["chi2_decomposition"] = {"bound200": chi2_decomp(200), "bound500": chi2_decomp(500)}

# ---------- 4c. 版本 pin（工件外化） ----------
import sys as _sys
import scipy
OUT["versions"] = {"python": _sys.version.split()[0], "scipy": scipy.__version__,
                   "machine": "Ubuntu 24.04 x86_64 (workspace host)"}

# ---------- 5. α 稳健性（headline flips at 各 α） ----------
def flips_at(alpha):
    cnt = 0
    for n in range(26, 501):
        for c in range(0, n // 2 + 1):
            b = n - c
            if p_code(b, c) < alpha and p_exact(b, c) >= alpha:
                cnt += 1
    return cnt
OUT["alpha_robustness"] = {str(a): flips_at(a) for a in (0.01, 0.025, 0.05, 0.10)}

# ---------- 6. 账本重判（read-only，解析 live 台账 evo_agent/EVOLUTION_LEDGER.md） ----------
# 口径修正：旧版把 frozen_v6 快照的 7 行（3 条冒烟 + E1–E4）硬编码当成本系统的进化账本，
# 但台账自身规则第 3–4 行写明「冒烟自检……不计入门禁统计」，且 live 台账实有 E1–E14。
# 本节改为解析 live 台账的 E 段、显式剔除「冒烟记录」区，并 fail-closed 校验条数与字段。
import os as _os
import re as _re

_LEDGER_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                             "..", "..", "evo_agent", "EVOLUTION_LEDGER.md")
_LEDGER_PATH = _os.path.normpath(_LEDGER_PATH)

with open(_LEDGER_PATH, encoding="utf-8") as _f:
    _txt = _f.read()

# 硬切掉「冒烟记录」区（台账规则：不计入门禁统计）
_main = _txt.split("## 冒烟记录")[0]
_blocks = _re.split(r"^## (E\d+)\s*$", _main, flags=_re.M)

ledger = []
_seen = []
for _i in range(1, len(_blocks), 2):
    _name, _body = _blocks[_i], _blocks[_i + 1]
    _b = _re.search(r"b\s*=\s*(\d+)", _body)
    _c = _re.search(r"c\s*=\s*(\d+)", _body)
    _p = _re.search(r"p\s*=\s*([\d.]+)", _body)
    _v = _re.search(r"裁决[：:]\s*(promote|hold)", _body)
    if not (_b and _c and _p and _v):
        raise SystemExit(f"ledger parse failed on {_name}: "
                         f"b={_b} c={_c} p={_p} verdict={_v}")
    ledger.append((_name, int(_b.group(1)), int(_c.group(1)),
                   float(_p.group(1)), _v.group(1)))
    _seen.append(_name)

# fail-closed：解析结果必须恰为 E1–E14，且与台账段落数一致
_expected = [f"E{i}" for i in range(1, 15)]
if _seen != _expected:
    raise SystemExit(f"ledger population check failed: parsed {_seen}, expected {_expected}")
if "SMOKE" in _main.upper():
    raise SystemExit("ledger population check failed: smoke records leaked into the gate region")

rejudge = []
agree = 0
for name, b, c, p_rec, verdict in ledger:
    n = b + c
    if n == 0:
        p_ex = 1.0
    else:
        p_ex = binomtest(min(b, c), n, 0.5, alternative="two-sided").pvalue
    p_ex = min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2.0 ** n) if n else 1.0
    v_ex = "promote" if (c > b and p_ex < 0.05) else "hold"
    ok = (v_ex == verdict) and abs(p_ex - p_rec) < 5.001e-5 + 1e-12
    agree += ok
    rejudge.append({"entry": name, "b": b, "c": c, "n": n, "p_recorded": p_rec,
                    "p_exact": round(p_ex, 7), "verdict_recorded": verdict,
                    "verdict_exact": v_ex, "agree": bool(ok)})
OUT["ledger_rejudgment"] = {"entries": len(rejudge), "agree": agree,
                            "max_n": max(r["n"] for r in rejudge),
                            "promotions_recorded": sum(1 for r in rejudge if r["verdict_recorded"] == "promote"),
                            "detail": rejudge}

# ---------- 7. 环级示例数字（R2-W4 插图，明确非本数据主张） ----------
OUT["loop_illustration"] = {"n_decisions": 145, "alpha_1s": 0.025,
                            "p_at_least_one_false_promo": 1 - (1 - 0.025) ** 145}

# ---------- 8. scipy 参考值交叉核验 ----------
OUT["scipy_refs"] = {
    "binomtest_18_8_26_two_sided": binomtest(8, 26, 0.5, alternative="two-sided").pvalue,
    "binomtest_14_13_27_two_sided": binomtest(13, 27, 0.5, alternative="two-sided").pvalue,
}

import os as _os
_out_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "revision_stats.json")
with open(_out_path, "w", encoding="utf-8") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1, default=float)

for k in ("basic", "cc", "midp", "benchmark_1s_nominal", "chi2_bound200",
          "chi2_bound500", "chi2_decomposition", "alpha_robustness",
          "ledger_rejudgment", "loop_illustration", "scipy_refs", "versions"):
    print(k, "=>", json.dumps(OUT[k], ensure_ascii=False, default=float)[:600])
