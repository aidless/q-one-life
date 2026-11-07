#!/usr/bin/env python3
"""bench-noise-floor — 读一份长表投票记录，判定「榜单读数是否可读」。

问题
----
当一个 benchmark 的金标由模型投票/概率平均生成时，把生成金标的模型自己放进榜里
打分，得到的就是这把尺子的**噪声下限**（ceiling）。若该下限高于榜上任何参赛系统，
则榜上任何名次差都不可解释为能力差。

用法
----
    python3 audit.py votes.csv [--gold majority|mean_prob|both] [--loo]
    python3 audit.py votes.csv --systems-col model --judges-col judge

--gold both
    两种金标口径各跑一遍完整流水线，再并排报告：判决是否翻转、名次是否翻转。
    为什么值得单独一个模式：可读性**不是**数据集的客观属性，而是你声明的参数。
    实测同一份 Jev 问句档（14,292 题）在 majority 下判 UNREADABLE、在 mean_prob 下
    判 MARGINAL，同一批系统名次也跟着换位。不做对照就不知道自己报的名次有多少是
    口径造出来的。

输入（长表 CSV，必需列）
------------------------
    item_id     同一道题的稳定标识
    role        "judge"（参与生成金标）或 "system"（参赛系统）
    actor       该行的投票者 id（judge 名或 system 名）
    answer      该投票者给出的答案（字符串或数值）
可选列
    slice       数据子集切片（如 dataset / task / workflow）。有它则报 macro（切片等权）
    answer_prob 该投票者对自己答案的置信度/概率（0~1）。给了就额外算校准
    case_id     配对 bootstrap 用；缺省用 item_id

输出（stdout）
--------------
    1. 金标构成与分歧诊断（两位 judge 的分歧率、谁赢、是否退化为加权投票）
    2. 噪声下限：judge 打自己参与生成的金标能得多少（含自身 / 留一法 leave-one-out）
    3. 榜单：每个 system 的 macro / micro 准确率，以及两口径之差
    4. 配对 bootstrap：与榜首的差是否显著、相邻名次里有几组是平局
    5. 结论行：VERDICT
    6. 校准（可选）：ECE / Brier / 可靠性分箱
    7. --gold both 时额外的口径对照表：判决/名次/下限的翻转位

依赖：numpy, pandas。scipy 可选（用于精确检验回退）。
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from math import lgamma, exp, log

# ---------------------------------------------------------------- 归一化

# 留一法地板的**解释**在 m=2 时退化。eq:loo 定义 floor_c(g)=acc_{c^-}(g)，c^- 是剔除
# g 自己那一票后由余下 m-1 个生成器重建的金标。m>=3 时 c^- 仍是「共识」，量到的是
# g 对共识的自复现率；m=2 时 c^- 只剩一个生成器，c^- 就是那个生成器的答案，量到的
# 是**生成器之间的一致率**。两者都算得出来，但性质不同，不能不加标注地混为一谈。
# 这里只降级**解释**，不拒绝计算：m=2 的量有定义、也有用（它就是两把尺的对齐度），
# 编造一个「不可估计」反而丢掉了真信息；正确做法是把它照算并显式打标签。
MIN_LOO_GENERATORS = 3
LOO_LABEL_SELF = "self_reproduction"
LOO_LABEL_DEGENERATE = "inter_generator_agreement"


def norm_answer(v) -> str:
    """答案归一。铁律：先试数值解析，再剔标点。

    否则 "2.0" 会被剔成 "20"，与 "2" 不等 —— 这条在工作区 AGENTS.md 第 9 条有实测教训。
    """
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if isinstance(v, (bool, np.bool_)):
        return "true" if v else "false"
    if isinstance(v, (int, float, np.integer, np.floating)):
        # 数值型：统一浮点表示，让 2 与 2.0 相等，-0 归 0
        f = float(v)
        if f == int(f) and abs(f) < 1e15:
            return str(int(f))
        return repr(round(f, 10))
    s = str(v).strip().lower()
    # 字符串型：先试能否解析成数值（"2.0" -> "2"）
    try:
        f = float(s)
    except (TypeError, ValueError):
        pass
    else:
        if f == int(f) and abs(f) < 1e15:
            return str(int(f))
        return repr(round(f, 10))
    # 非数值：折叠空白 + 去首尾标点
    s = " ".join(s.split())
    return s.strip(" \t\n.,;:!?\"'()[]{}<>-_/\\|`~@#$%^&*+")


def norm_actor(v) -> str:
    return " ".join(str(v).strip().split())


# ---------------------------------------------------------------- 金标构造


class Gold:
    """由 judge 行构造金标。两种口径都算，用来暴露「名次是金标构造的产物」。"""

    def __init__(
        self,
        majority: Dict[str, str],
        mean_prob: Optional[Dict[str, str]],
        counts: Dict[str, Dict[str, int]],
        judges: List[str],
        n_judges: Dict[str, int],
        conf_sum: Dict[str, float],
    ):
        self.majority = majority
        self.mean_prob = mean_prob
        self.counts = counts
        self.judges = judges
        self.n_judges = n_judges
        self.conf_sum = conf_sum
        # 平票口径与平票题清单，由 build_gold 填。tie_rule != "unmeasured" 时
        # 才有 tie_items 需要报；unmeasured 下平票题只是没进金标表。
        self.tie_rule = "unmeasured"
        self.tie_items: Dict[str, List[str]] = {}

    def get(self, item: str, method: str) -> str:
        return (self.mean_prob if method == "mean_prob" else self.majority).get(item, "")

    def votes(self, item: str) -> Dict[str, int]:
        return self.counts.get(item, {})


def build_gold(
    jdf: pd.DataFrame,
    have_prob: bool,
    tie_rule: str = "unmeasured",
) -> Gold:
    """构造金标。

    平票裁决规则（`tie_rule`）——这是本函数唯一会左右判决的设计选择：

    - ``unmeasured``（默认，也是唯一可用于判决的口径）：平票意味着**没有任何
      生成器对这一题形成多数**，按分母纪律（未测到 ≠ 测成另一个答案），该题
      **不进金标表**；其 row 在计分时从分子和分母同时剔除，并单独报覆盖率。
    - ``lexicographic``：旧行为，平票取字典序最小者。**仅保留用于敏感性对照**。
      它的危险性实测过：decision 语料 1520 题里 436 题（28.6%）是 1-1 平票，
      该规则在这些题上裁出的「金标」由答案字符串的字典序决定，方向系统性偏向
      一侧（164 题归 anthropic / 272 题归 openai），且榜首本身会换人
      （claude-opus-5 73.19 ↔ gpt-5.6-sol 72.63，margin 摆动 4.65 点）。那是序列化
      顺序的性质、不是基准的性质，所以不得用于判决。
    - ``drop``：等价于 ``unmeasured``，保留旧名以便脚本调用。

    ``majority[item]`` 缺键即表示该题无金标，调用方必须当「未测到」处理；
    ``Gold.get()`` 对缺失返回空串，与该语义一致。
    """
    if tie_rule not in ("unmeasured", "lexicographic", "drop"):
        sys.exit(f"[FATAL] 未知的 tie_rule={tie_rule!r}；可用：unmeasured|lexicographic|drop")
    counts: Dict[str, Dict[str, int]] = {}
    n_judges: Dict[str, int] = {}
    conf_sum: Dict[str, float] = {}
    majority: Dict[str, str] = {}
    tie_items: Dict[str, List[str]] = {}      # 平票题 -> 各方答案（供报告披露）
    mean_prob_ties: Dict[str, List[str]] = {}  # 加权口径里顶票**浮点恰等**的题（顺序依赖，只登记不改判）
    mean_prob: Optional[Dict[str, str]] = {} if have_prob else None

    for item, grp in jdf.groupby("item_id", sort=False):
        c: Dict[str, int] = {}
        for a in grp["answer_n"].tolist():
            if a == "":
                continue
            c[a] = c.get(a, 0) + 1
        counts[item] = c
        if c:
            w = plurality_winner(c)
            if w is not None:
                majority[item] = w
            else:
                # 顶票没有唯一持有者 = 没有任何生成器形成多数 => 未测到，不是测错
                tie_items[item] = sorted(c.keys())
                if tie_rule == "lexicographic":      # 仅供敏感性对照
                    majority[item] = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        n_judges[item] = int(len(grp))

    if mean_prob is not None:
        for item, grp in jdf.groupby("item_id", sort=False):
            acc: Dict[str, float] = {}
            wsum = 0.0
            for a, p in zip(grp["answer_n"].tolist(), grp["answer_prob"].tolist()):
                if a == "" or not np.isfinite(p):
                    continue
                acc[a] = acc.get(a, 0.0) + float(p)
                wsum += float(p)
            if acc and wsum > 0:
                # 只取一层下标：max(dict.items()) 返回的就是 (答案, 权重) 这一对，
                # 再 [0] 一次会把答案**截成首字母**。上面 majority 那行为什么要两层？
                # 因为 sorted() 返回的是列表，要先取第 0 个元素再取键。
                # 2026-10-16 实测：多字符标签下这里长期返回 'v' 而不是 'vendor_only'，
                # 于是 question 语料的 mean_prob 金标全量截断（详见 selftest 的
                # case_gold_labels_are_answers_cast —— 旧夹具标签只有 'A'/'B'，
                # 首字母与全长逐字相同，56 个 case 一起绿着把这个 bug 盖住了）。
                mean_prob[item] = max(acc.items(), key=lambda kv: (kv[1], kv[0]))[0]
                if sum(1 for v in acc.values() if v == max(acc.values())) > 1:
                    mean_prob_ties[item] = sorted(acc.keys())
        # 只在全部 item 都有概率时才启用该口径，避免半残
        if len(mean_prob) < len(counts):
            mean_prob = None

    judges = sorted({norm_actor(a) for a in jdf["actor"].tolist()})
    g = Gold(majority, mean_prob, counts, judges, n_judges, conf_sum)
    g.tie_rule = tie_rule
    g.tie_items = tie_items
    g.mean_prob_ties = mean_prob_ties
    return g


def leave_one_out(
    gold: Gold, method: str, votes: Dict[Tuple[str, str], str], probs: Dict[Tuple[str, str], float]
) -> Dict[str, Dict[str, str]]:
    """真·留一法金标 c^-：返回 {judge g: {item: label}}。

    eq:loo 定义 c^- 是「剔除 g 自己那一票、由余下 m-1 个生成器重建的金标」，
    所以每个生成器必须有**自己那张** c^- 表。旧实现把全部 judge 的票累加进
    同一张表再对每个 judge 复用它 —— 那张表就是含自身金标 c（与 c 的唯一差别
    是平票裁决方向），不是 c^-。这不是精度差异而是定义错误：真 LOO 少了
    自己那一票的支撑，地板系统性更低，verdict 会因此翻转（实测三档全翻）。
    实测机制证据：旧实现那张表与 c 逐题不同的 item 数恰好等于 1-1 平票的
    item 数（question 799=799、decision 436=436），mean_prob 下因浮点无平票
    而逐题相同（diff=0）。

    m=2 时 c^- 只剩一个生成器，金标退化成「另一个 judge 的答案」，此时量到的
    是 judge 间一致率而不是自复现率。定义上仍然成立，但必须标出来
    （调用方据此写 loo_degenerate_m），否则读者会以为它和 m>=3 同性质。
    """
    mode = method if gold.mean_prob is not None else "majority"
    out: Dict[str, Dict[str, str]] = {}
    for g in gold.judges:
        per_item: Dict[str, str] = {}
        for item in gold.n_judges:
            acc: Dict[str, float] = {}
            for j in gold.judges:
                if j == g:                      # <== 剔除自己：eq:loo 的定义所在
                    continue
                a = votes.get((item, j), "")
                if a == "":
                    continue
                if mode == "mean_prob":
                    p = probs.get((item, j), float("nan"))
                    if not np.isfinite(p):
                        p = 1.0 / max(1, gold.n_judges[item] - 1)
                    acc[a] = acc.get(a, 0.0) + float(p)
                else:
                    acc[a] = acc.get(a, 0.0) + 1.0
            if not acc:
                # 剔除自己后该题没有剩余票 -> c^- 在此题**无定义**，不能补一个值。
                # 该题会被 scored_rows 剔除，留在表里会让「没定义」静默变成「全错」。
                continue
            if plurality_winner(acc) is not None:
                per_item[item] = plurality_winner(acc)
            elif gold.tie_rule == "lexicographic":
                # 仅供敏感性对照；unmeasured 下平票同样视为未测到（c^- 无定义）。
                per_item[item] = sorted(acc.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            # else: unmeasured —— 剔除自己后仍是平票 => c^- 无定义，该题不写入。
        out[g] = per_item
    return out


# ---------------------------------------------------------------- 打分


def plurality_winner(counts):
    """顶票判据的唯一实现：**顶票有唯一持有者**才算形成多数，并列即未测到。

    2026-10-12 修。旧实现是 `max(c) * 2 != sum(c)`，那既不是多数也不是顶票判据，
    而是"顶票恰好等于其余之和"这个偶然形状，两个方向都错：
      · 漏判：`12 / 12 / 1`、`9 / 9 / 5 / 7`、`11 / 11 / 3` 这类顶票并列 + 第三派拿剩票
        的题不被当作平票，于是金标落到 `sorted(-count, label)` 的**答案字符串顺序**上。
        本线实测 m=25 四档共 19 题（factuality 2 / coherence 13 / relevance 4），
        而正文当时写着"平票不进金标"。
      · 误废：`4 / 2 / 2` 有唯一的顶票持有者（4 票，占全部 8 票的一半，是合法的
         plurality 领先者），旧规则却把它判成平票并从金标里删掉。实测 preference 档
        有 5 题因此缺席。
    两个方向都是**判决的输入**，所以这条改动必须同时被 `build_gold` 与 `leave_one_out`
    共用（各写一遍就会漂移，漂移的那一份会安静地改变地板与榜首的分母）。
    """
    if not counts:
        return None
    mx = max(counts.values())
    if sum(1 for v in counts.values() if v == mx) != 1:
        return None
    return next(k for k, v in counts.items() if v == mx)



def agreement(
    sdf: pd.DataFrame, gold_map: Dict[str, str], key: str = "item_id"
) -> pd.Series:
    """逐行是否命中金标。**没有金标的行返回 NaN（未测到），不是 0（全错）**。

    这是承重语义，不是细节。旧实现把「金标表里没这一项」和「答案不等」一起判成
    False，于是**没测到**被写成**测了全错**：问句档有 1188 题（14292 的 8.3%）根本
    不在 judge 标注集内（judge 行数为 0）却有系统作答，实测把各系统 macro 压低
    1.0~5.9 点，榜首 opus 被压 1.51 点。这个缺陷只发生在「按 actor 打分」这条
    路径上 —— 分子里的 judge 行全部有金标，只有系统的分母掺了未测题。

    NaN 而非 0 还让下游口径自洽：macro_micro 的 groupby/sum 跳过 NaN 而 count 只数
    非 NaN，等于「只按被计分的行数算分母」；bootstrap 里某 case 全 NaN 则该轮无定义，
    沿用既有的「剔除无效轮次」路径，而不是补 0 造出一个假的窄 CI。
    """
    g = sdf[key].map(gold_map)
    scored = sdf[key].isin(gold_map).to_numpy()
    hit = (sdf["answer_n"].to_numpy() == g.to_numpy()).astype(float)
    return pd.Series(np.where(scored, hit, np.nan), index=sdf.index)


# ------------------------------------------------------- 聚类结构：ICC 与设计效应
#
# 为什么要单独算 ICC：bootstrap 按 case 整簇还是按 item 逐条，CI 宽度差一个量级
# （实测本库 judge-vs-contestant margin：item 级 [+0.29,+5.55] 不跨 0，
#   case 级 [-0.14,+6.27] 跨 0）。选错单位会让「显著/不显著」的结论翻转，
# 而选哪个单位不是审美问题 —— 由数据的聚类结构决定。
#
# 用 ICC(agree) 而不是 Pearson r：ICC(agree) 对**系统性偏移**敏感，
# （与 r 的差是 2·bias²）而 ICC(cons) 不敏感。这里恰好相反？
# 不，这里恰好是「同一批人/模型在两个 gold 上各答一次」的双向设计，
# 两条测量有共同的方法方差，ICC(agree) 才对应「两次测量能否互换」这个问题。
#
# 定义（Shrout & Fleiss 1979 的 two-way random, absolute agreement, single）：
#   ICC(agree) = (MSR − MSE) / (MSR + (k−1)·MSE + k·(MSC − MSE)/n)
# 其中 n=被测对象数（本处=case），k=每个 case 的重复测量数（本处=2 条测量）。
# 分母含 (MSC − MSE)/n 这一项，所以它是**绝对一致**，允许系统偏移拉开分数。
def self_grading_overlap(df: pd.DataFrame,
                         judges: Optional[pd.DataFrame] = None) -> Dict[str, object]:
    """检测「参赛系统与判官是同一批 actor」这个自评问题。

    这不是可选项而是必检项：若同一批模型既是被测对象又是判官，
    地板线由被测者参与构造，任何「判官能读出系统差异」的结论都内生偏乐观。

    实测 JudgeSense 四个档**全部**如此（facts/coherence/relevance/preference）：
    system 表与 judge 表的 (actor, item_id) 键集合完全相同（交集 25/25），
    答案逐字一致（1.0000）。注意这**必须跨表查** —— 单张表里 role 是常量
    （system 表全是 system、judge 表全是 judge），跨表取交集才查得出来。
    所以 `judges` 参数给判官表；不给就退化成单表内 role 交叉检查。

    缺 actor 列时返回 `checkable=False, self_grading=None` 而不是 False ——
    「没数据」不等于「没问题」，两者不可混同。
    """
    if df is None or "actor" not in getattr(df, "columns", []):
        return {"checkable": False, "self_grading": None,
                "reason": "表无 actor 列，无法区分系统与判官"}
    if judges is not None and "actor" in getattr(judges, "columns", []):
        as_sys = set(map(str, df["actor"].unique()))
        as_judge = set(map(str, judges["actor"].unique()))
        cross = True
    else:
        if "role" not in df.columns:
            return {"checkable": False, "self_grading": None,
                    "reason": "表无 role 列，且未给 --judges-file（跨表自评检查不可用）",
                    "n_actors": int(df["actor"].nunique())}
        roles = df.groupby("actor")["role"].apply(lambda x: set(map(str, x)))
        as_sys = {a for a, rs in roles.items() if "system" in rs}
        as_judge = {a for a, rs in roles.items() if "judge" in rs}
        cross = False
    both = sorted(as_sys & as_judge)
    n = len(as_sys | as_judge)
    ov = len(both)
    return {"checkable": True, "n_actors_total": int(n),
            "n_actors_as_system": len(as_sys), "n_actors_as_judge": len(as_judge),
            "overlap": ov,
            "overlap_fraction": (float(ov) / n) if n else float("nan"),
            "self_grading": bool(ov > 0),
            "self_grading_actors": both, "cross_table": bool(cross),
            "note": ("参赛系统与判官是同一批 actor（跨表取交集）：判官在给自己评分。"
                     "地板线由被测者参与构造，结论系统性偏乐观，"
                     "引用本文数字时必须一并声明这一点。"
                     if ov else "未发现自评重叠。")}


def _load_judges_for_overlap(path: Optional[str]) -> Optional[pd.DataFrame]:
    """读判官表只为做自评重叠检测；读不了就返回 None，绝不让检查崩掉主流程。"""
    if not path:
        return None
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as e:  # noqa: BLE001
        print(f"  [WARN] --judges-file 读不了（{e}），自评重叠检查将只覆盖单表")
        return None



def icc_two_way_absolute_agree(M: np.ndarray) -> Dict[str, float]:
    """双向随机、绝对一致、单次测量的 ICC(agree)（= ICC(A,1)）。

    M 形状 (n_targets, k_raters)，要求无缺失。返回判别所需的全部中间量，
    因为 ICC 单独一个数无法审计 —— 分母里那两项各自多大必须能看见。
    """
    M = np.asarray(M, dtype=float)
    n, k = M.shape
    if n < 2 or k < 2:
        return {"icc": float("nan"), "reason": f"n/k 不足 (n={n}, k={k})"}
    grand = float(M.mean())
    row_mean = M.mean(axis=1)              # 每个 case 的行均值
    col_mean = M.mean(axis=0)              # 每条测量的列均值
    ss_rows = k * float(((row_mean - grand) ** 2).sum())
    ss_cols = n * float(((col_mean - grand) ** 2).sum())
    ss_tot = float(((M - grand) ** 2).sum())
    ss_err = ss_tot - ss_rows - ss_cols
    ms_rows = ss_rows / (n - 1)
    ms_cols = ss_cols / (k - 1)
    ms_err = ss_err / ((n - 1) * (k - 1))
    denom = ms_rows + (k - 1) * ms_err + k * (ms_cols - ms_err) / n
    icc = (ms_rows - ms_err) / denom if denom != 0 else float("nan")
    # 单个 case 的平均方差：把 ICC 翻译成「重测需要多少条独立测量才够稳」
    return {"icc": float(icc), "n_targets": int(n), "k_raters": int(k),
            "ms_rows": float(ms_rows), "ms_cols": float(ms_cols),
            "ms_error": float(ms_err),
            "col_means": [float(x) for x in col_mean],
            "grand_mean": grand,
            "systematic_offset": float(abs(col_mean[0] - col_mean[1]))}


def icc_bootstrap_ci(M: np.ndarray, n_boot: int = 2000, seed: int = 20261001,
                     alpha: float = 0.05) -> Dict[str, float]:
    """ICC(A,1) 的 items 级 bootstrap 置信区间。

    为什么必须有：审稿意见 3.7 指出正文声称使用 ICC absolute-agreement 却不给
    点估计的区间 —— 一个没有区间的系数无法与「量级接近 0」区分开，而我们的
    四档 ICC 恰好落在 0.19~0.46 这段「既非 0 也非 1」的区域，不给区间读者
    无法判断某个任务的相关性是否可与 0 分辨。

    重抽样单位是 **item（行）**：ICC 的定义域是「同一批 item 上的两个测量」，
    重抽样 item 才对应「换一批题会得到怎样的 ICC」。因此这里不用 case 级单位
    —— 那是给 top-vs-bottom 差值的重抽样用的，量不同不可混。

    返回 lo95/hi95/n_valid/n_boot/seed/unit；有效轮次不足时返回 status 说明，
    绝不给一个用 0 补齐的假区间（与 bootstrap_diff_two_units 同一纪律）。
    """
    M = np.asarray(M, dtype=float)
    n, k = M.shape
    if n < 2 or k < 2:
        return {"status": "NOT_COMPUTABLE", "reason": f"n/k 不足 (n={n}, k={k})"}
    rng = np.random.default_rng(int(seed))
    vals: list[float] = []
    for _ in range(int(n_boot)):
        idx = rng.integers(0, n, size=n)
        got = icc_two_way_absolute_agree(M[idx, :])["icc"]
        if np.isfinite(got):
            vals.append(float(got))
    if len(vals) < max(50, int(0.5 * n_boot)):
        return {"status": "INSUFFICIENT_ROUNDS", "n_valid": len(vals),
                "n_boot": int(n_boot),
                "reason": "有效轮次不足半数，不给区间"}
    arr = np.asarray(vals, dtype=float)
    lo, hi = np.percentile(arr, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"status": "OK", "lo95": float(lo), "hi95": float(hi),
            "n_valid": int(arr.size), "n_boot": int(n_boot), "seed": int(seed),
            "unit": "item",
            "note": "重抽样单位为 item（行）：ICC 的定义域是同一批 item 上的两个测量，"
                    "换一批题才对应 ICC 的抽样变异；case 级单位是给差值用的，量不同。"}


def design_effect(icc: float, k: int) -> float:
    """设计效应 deff = 1 + (k−1)·ICC。

    k 条重复测量聚在一起时，有效独立样本量 = n / deff。
    这是「为什么 case 级 bootstrap 的 CI 更宽」的定量理由。
    """
    if not np.isfinite(icc):
        return float("nan")
    if k < 1:
        return float("nan")
    # k=1 时公式给出 1.0（无重复测量 ⇒ 无设计效应），必须返回这个值而不是 NaN：
    # 「没有聚类」是一个**可判定的结论**（deff=1，有效样本量=n），与「算不出来」
    # 不是一回事。此前对 k<2 一律返回 NaN，把可判定的事实写成了不可算。
    return 1.0 + (k - 1) * float(icc)


def bootstrap_diff_two_units(
    pairs: List[Tuple[str, np.ndarray, np.ndarray]],
    n_boot: int = 10000, seed: int = 20261001,
) -> Dict[str, Dict[str, float]]:
    """同一对测量同时按 item 级与 case 级重采样，返回两种单位的 CI。

    两者**必须并列报告**：item 级把同一 case 内的多条观测当独立，
    忽略聚类 ⇒ CI 偏窄（假显著）；case 级保守但若 case 数太少则过宽。
    论文只报其中一种，等于替读者做了选择 —— 选择权必须在读者手上。
    """
    by_case: Dict[str, List[int]] = {}
    for idx, (case_id, _a, _b) in enumerate(pairs):
        by_case.setdefault(str(case_id), []).append(idx)
    case_keys = sorted(by_case)

    # --- item 级：逐条重采样下标 ---
    m = len(pairs)
    if m == 0:
        return {}
    A = np.array([float(x[1]) for x in pairs])
    B = np.array([float(x[2]) for x in pairs])
    out: Dict[str, Dict[str, float]] = {}
    rng = np.random.default_rng(seed)
    idx_item = rng.integers(0, m, size=(n_boot, m))
    d_item = A[idx_item].mean(axis=1) - B[idx_item].mean(axis=1)
    finite = np.isfinite(d_item)
    di = d_item[finite]
    out["item"] = {"diff": float(100.0 * (A.mean() - B.mean())),
                   "lo95": float(100.0 * np.percentile(di, 2.5)) if di.size else float("nan"),
                   "hi95": float(100.0 * np.percentile(di, 97.5)) if di.size else float("nan"),
                   "n_units": m, "n_valid": int(di.size),
                   "unit": "item"}

    # --- case 级：整簇重采样；簇内所有条目一起动 ---
    n_case = len(case_keys)
    A_c = np.array([np.nanmean(A[v]) for v in by_case.values()])
    B_c = np.array([np.nanmean(B[v]) for v in by_case.values()])
    rng2 = np.random.default_rng(seed + 1)
    idx_case = rng2.integers(0, n_case, size=(n_boot, n_case))
    d_case = A_c[idx_case].mean(axis=1) - B_c[idx_case].mean(axis=1)
    finite_c = np.isfinite(d_case)
    dc = d_case[finite_c]
    out["case"] = {"diff": float(100.0 * (A_c.mean() - B_c.mean())),
                   "lo95": float(100.0 * np.percentile(dc, 2.5)) if dc.size else float("nan"),
                   "hi95": float(100.0 * np.percentile(dc, 97.5)) if dc.size else float("nan"),
                   "n_units": n_case, "n_valid": int(dc.size),
                   "unit": "case"}
    for u in out.values():
        u["crosses_zero"] = bool(u["lo95"] <= 0 <= u["hi95"])
        u["n_boot"] = int(n_boot)
    # 符号稳定性：点估计为正而 CI 含 0，与「点估计本身在重采样下会翻面」
    # 是两件不同的事，后者更强——它说明这个差在本数据上根本站不住。
    # 分开报：frac_negative = P(Δ<0)，frac_crosses = P(Δ 落在 0 两侧)。
    d_all = np.concatenate([di, dc]) if di.size and dc.size else (di if di.size else dc)
    if d_all.size:
        out["_sign_stability"] = {
            "frac_negative_item": float(100.0 * (di < 0).mean()) if di.size else None,
            "frac_negative_case": float(100.0 * (dc < 0).mean()) if dc.size else None,
            "note": "percent of bootstrap rounds whose Δ has the opposite sign "
                    "to the point estimate; 0 means the sign never flipped.",
        }
    return out


def macro_micro(hit: pd.Series, sl: pd.Series) -> Tuple[float, float]:
    """macro = 切片等权平均；micro = 逐条平均。两口径之差本身就是信号。

    NaN（未测到）被整条剔除，不进分子也不进分母。
    """
    hit = pd.Series(hit, dtype=float)
    ok = hit.notna().to_numpy()
    if not ok.any():
        return float("nan"), float("nan")
    hit_v = hit.to_numpy()[ok]
    sl_v = (sl.to_numpy() if isinstance(sl, np.ndarray) else sl.to_numpy())[ok]
    micro = 100.0 * float(hit_v.mean())
    sl_s = pd.Series(sl_v)
    if sl_s.nunique(dropna=True) <= 1:
        return micro, micro
    per = pd.DataFrame({"h": hit_v, "s": sl_v}).groupby("s", dropna=True)["h"].mean() * 100.0
    return float(per.mean()), micro


# ---------------------------------------------------------------- 统计


def paired_bootstrap(
    a: np.ndarray, b: np.ndarray, n_boot: int = 10000, seed: int = 20261001
) -> Tuple[float, float, float]:
    """配对 bootstrap：返回 (mean_diff, lo95, hi95)，lo>0 表示 a 显著优于 b。"""
    if a.size == 0 or a.size != b.size:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, a.size, size=(n_boot, a.size))
    d = (a[idx] - b[idx]).mean(axis=1)
    return float((a - b).mean()), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def holm_bonferroni(pvals: List[float], alpha: float = 0.05) -> Dict[str, object]:
    """Holm-Bonferroni 逐步降序校正（控制族系错误率 FWER）。

    为什么必须做：本文一次跑出 24 组「各系统 vs 榜首」的配对检验。
    在 α=0.05 上逐个判显著，即使**全部**系统真实无差异，
    期望也有 1−0.95^24 ≈ 70% 的机会至少错报一次。逐个 p 值本身没错，
    但「有多少个系统与榜首不可区分」这句话需要的是族系校正后的结论。

    Holm 比 Bonferroni 更保守吗？不——Holm **更不**保守（控制同样 FWER 但
    功效更高），且不需要独立性假设，故优于 Bonferroni。BH 只控 FDR，
    与本文要的「宁可漏报不可错报」不合，故不作为主口径。

    返回校正后 p 值与拒绝标志（p_adj ≤ α）。单调性是 Holm 的定义性质：
    实现里显式累积 **max**（不是 min —— 方向搞反会系统性低估校正 p 值，
    被抓出来的证据见函数体注释）。已与 statsmodels 的 holm 逐项对齐。
    """
    ps = [float(x) for x in pvals]
    m = len(ps)
    if m == 0:
        return {"n_tests": 0, "alpha": alpha, "p_adjusted": [], "reject": [],
                "n_rejected": 0, "n_rejected_uncorrected": 0,
                "fwer_under_global_null": 0.0}
    order = sorted(range(m), key=lambda i: ps[i])
    adj = [0.0] * m
    # Holm 第 k 小 p 的校正值 = max_{j<=k} (m-j+1)·p_(j)，**累积 max**。
    # 踩过的坑：先写成累积 min（反向遍历）得出 [0.010, 0.072, 0.216, ...]，
    # 而 statsmodels/教科书给的是 [0.010, 0.072, 0.312, ...] —— 第 3 项起
    # 系统性偏小 0.096，8/10 项偏小 0.399。症状是**低估**校正后的 p 值，
    # 会把本该不显著的检验放行。已与 statsmodels 逐项对齐。
    running = -1.0
    for rank, i in enumerate(order):
        # (m - rank) 是该 p 位置的检验数（rank 从 0 起）
        running = max(running, (m - rank) * ps[i])
        adj[i] = min(1.0, running)
    rej = [bool(a <= alpha) for a in adj]
    n_rej = int(sum(rej))
    # 未校正逐个读：这是**同一批 p 值的另一种判法**，不是另一族检验。
    uncorr = int(sum(1 for p in ps if p <= alpha))
    # 结构不变式：Holm 是把 α 逐步收紧的收缩程序，它的拒绝集必须是未校正拒绝集的
    # **子集**。这条不是装饰——本函数曾被写成累积 min（见上面注释），那种实现系统性
    # **低估**校正后 p 值，症状正是放行本该不显著的检验，也就是子集关系被打破。
    # 判据若永不可能红就是死条款：把 adj 改成累积 min 的那版夹具（tests/
    # test_revision_round3.py）会在这里 raise，实测过。
    if n_rej > uncorr:
        raise SystemExit(f"FATAL Holm 拒绝 {n_rej} 个 > 未校正拒绝 {uncorr} 个："
                         f"族系校正不可能比不校正更宽松，校正实现有错")
    return {"method": "holm-bonferroni", "n_tests": m, "alpha": alpha,
            "p_adjusted": [round(a, 8) for a in adj],
            "reject": rej, "n_rejected": n_rej,
            "n_rejected_uncorrected": uncorr,
            # 1−(1−α)^m 是**全部 m 个原假设为真时**未校正程序至少给出一个假拒绝的概率
            # （该程序在此情形下的族系错误率）。它不是"本库拒绝里有百分之多少是错的"
            # ——后者需要知道有多少原假设为假，本数据算不出来。10-15 第二轮评审 R1-M4
            # 指的就是这个区别：旧 note 把它叫「期望错报率」，正文跟着照印，等于工具与
            # 稿件一起把 FWER 说成了 false-discovery proportion。
            "fwer_under_global_null": round(1 - (1 - alpha) ** m, 6),
            "note": "控制族系错误率（FWER）。"
                    f"若这 {m} 个原假设全为真，逐个在 α={alpha} 下不校正检验"
                    f"至少给出一个假拒绝的概率为 "
                    f"{100 * (1 - (1 - alpha) ** m):.1f}%"
                    f"（{m} 个检验，α={alpha}）；这是**全球零假设下该程序的族系错误率**，"
                    f"不是本库拒绝中假拒绝的比例，后者本数据不可算。"
                    f"同一批 p 值逐个读显著 {uncorr} 个，Holm 后 {n_rej} 个。"}


def mde_from_ci(ci_lo: float, ci_hi: float, alpha_z: float = 1.959963985) -> float:
    """由 95%CI 半宽反推最小可检测差（MDE）：halfwidth = z · SE ⇒ MDE = halfwidth。

    本文判决门槛 δ = 2.0 点。若 MDE > δ，则本研究**没有功效**在 δ 上做出判决，
    「不显著」应读作「本研究测不出来」，而不是「效应不存在」。这个换算是
    论文里必须写的：只报 p 值不报 MDE，等于把「无功效」说成「无效应」。
    """
    lo, hi = float(ci_lo), float(ci_hi)
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return float("nan")
    return float((hi - lo) / 2.0)


def power_at_delta(delta: float, mde: float) -> float:
    """δ 处的近似功效（双侧，正态近似）。

    z = δ / SE，SE = MDE / 1.96。功效 ≈ Φ(−z_crit − δ/SE) + 1 − Φ(z_crit − δ/SE)。
    这是**近似**（假设检验统计量正态、效应量已知），只能用于判断
    「本研究大概够不够力」，不得当作精确功效报告。
    """
    if not (np.isfinite(mde) and mde > 0):
        return float("nan")
    zc = 1.959963985
    se = mde / zc
    lam = abs(float(delta)) / se
    from math import erf, sqrt
    Phi = lambda z: 0.5 * (1 + erf(z / sqrt(2)))
    return float(Phi(-zc - lam) + 1 - Phi(zc - lam))


def mcnemar_exact(b: int, c: int) -> float:
    """二项精确检验：配对不一致里 a 赢 b 赢，H0 p=0.5。

    踩过的坑：直接 `sum(comb(n,i)) / 2**n` 在 n≈1024 就 OverflowError
    （分歧上万时很常见）。优先用 scipy 的精确二项检验；没有 scipy 时
    退回对数域求和（lgamma），并夹在 [0,1]。
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    try:
        from scipy.stats import binomtest

        return float(binomtest(k, n, 0.5, alternative="two-sided").pvalue)
    except Exception:  # scipy 缺失或异常 -> 对数域兜底
        log_num = 0.0
        for i in range(0, k + 1):
            log_num += lgamma(n + 1) - lgamma(i + 1) - lgamma(n - i + 1)
        try:
            tail = exp(log_num - n * log(2.0))
        except OverflowError:
            tail = 0.0
        return float(min(1.0, max(0.0, 2.0 * tail)))


# ---------------------------------------------------------------- 校准


def calibration(pred: np.ndarray, correct: np.ndarray, n_bins: int = 10) -> Dict[str, object]:
    pred = np.asarray(pred, dtype=float)
    correct = np.asarray(correct, dtype=float)
    # 两边都要 finite：correct 侧的 NaN 是「该行没金标、未被计分」。只筛 pred 会把
    # 这些行留在分母里，让 ECE/Brier 静默变成 NaN（correct.mean() 遇 NaN 全污染）。
    ok = np.isfinite(pred) & np.isfinite(correct)
    pred, correct = pred[ok], correct[ok]
    if pred.size == 0:
        return {"n": 0}
    bins = np.clip((pred * n_bins).astype(int), 0, n_bins - 1)
    ece, rows, wsum = 0.0, [], 0.0
    for b in range(n_bins):
        m = bins == b
        k = int(m.sum())
        if k == 0:
            continue
        conf, acc = float(pred[m].mean()), float(correct[m].mean())
        ece += k / pred.size * abs(acc - conf)
        rows.append(
            {
                "bin": f"[{b / n_bins:.1f},{(b + 1) / n_bins:.1f})",
                "n": k,
                "mean_conf": round(conf, 4),
                "acc": round(acc, 4),
                "gap": round(acc - conf, 4),
            }
        )
        wsum += k
    return {
        "n": int(pred.size),
        "ECE": round(ece, 4),
        "Brier": round(float(np.mean((pred - correct) ** 2)), 4),
        "mean_conf": round(float(pred.mean()), 4),
        "acc": round(float(correct.mean()), 4),
        "bins": rows,
    }


# ---------------------------------------------------------------- 主流程


def load(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    need = {"item_id", "role", "actor", "answer"}
    missing = need - set(df.columns)
    if missing:
        sys.exit(f"[FATAL] 缺少必需列: {sorted(missing)}；实际列={list(df.columns)}")
    df["actor"] = df["actor"].map(norm_actor)
    df["answer_n"] = df["answer"].map(norm_answer)
    df["role"] = df["role"].str.strip().str.lower()
    df = df[df["actor"] != ""].copy()
    if df.empty:
        sys.exit("[FATAL] 归一后没有有效行（actor 全空？）")
    have_prob = "answer_prob" in df.columns
    if have_prob:
        # 只在真能解析成数值时才算「有概率列」；全空/全非数值应视作没有置信度，
        # 否则下游会拿 NaN 静默算出一个假的校准段。
        df["answer_prob"] = pd.to_numeric(df["answer_prob"], errors="coerce")
        if not np.isfinite(df["answer_prob"].to_numpy(dtype=float)).any():
            have_prob = False
            df["answer_prob"] = np.nan
    else:
        df["answer_prob"] = np.nan
    if "slice" not in df.columns:
        df["slice"] = "all"
    df["slice"] = df["slice"].fillna("all")
    if "case_id" not in df.columns:
        df["case_id"] = df["item_id"]
    df["case_id"] = df["case_id"].astype(str)
    return df, have_prob


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="benchmark noise-floor audit")
    ap.add_argument("csv")
    ap.add_argument("--gold", default="majority",
                    choices=["majority", "mean_prob", "both"],
                    help="金标口径。both = 两种口径各跑一遍并并排对照（默认 majority）")
    ap.add_argument("--loo", action="store_true", default=True,
                    help="同时给出留一法噪声下限（默认开）")
    ap.add_argument("--no-loo", dest="loo", action="store_false")
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--bins", type=int, default=10)
    ap.add_argument("--json", help="同时把结论写到这个 JSON")
    ap.add_argument("--judges-file",
                    help="判官表 CSV（role=judge）。给这个文件才能检出"
                         "「系统与判官是同一批 actor」的自评问题 —— 单表查不出来"
                         "（system 表 role 全是 system，必须跨表取交集）")
    ap.add_argument("--gold-file", help="外部金标 CSV（必须含 item_id,gold 两列）")
    ap.add_argument("--tie-rule", default="unmeasured",
                    choices=["unmeasured", "lexicographic"],
                    help="平票裁决。默认 unmeasured=平票视为未测到（该题不进金标表，"
                         "从分子分母同时剔除）；lexicographic=按答案字符串字典序裁决，"
                         "仅供敏感性对照，不得用于判决")
    args = ap.parse_args(argv)
    # 每次运行把**自身源码哈希**打进 stdout。理由：代码改了、日志没重跑，
    # 两者在磁盘上看起来同样合法，而论文里每个数字都声称「可从落盘证据重算」。
    # 没有这行就无法事后判断一条 log_*.txt 是哪一版代码的输出；
    # 2026-10-05 实测踩中：改了 audit.py 之后 9 条 log_audit_*.txt 仍是旧版输出，
    # 新字段（地板稳健性 / 弃权率 / 符号稳定性）一条都查不到，而 manifest 与
    # 三道闸全部照样 PASS —— 没有任何一道门会发现这件事。
    try:
        import hashlib as _h
        import pathlib as _pl
        _self = _h.sha256(_pl.Path(__file__).resolve().read_bytes()).hexdigest()
    except Exception:
        _self = "unavailable"
    print(f"[0] audit.py sha256 = {_self}")

    # 外部金标是**另一把尺**，不能和 --gold 口径混用：
    # --gold both 是「同一把判官尺子的两种口径」，外部金标下没有这个概念。
    if args.gold_file:
        if args.gold != "majority":
            sys.exit(f"[FATAL] --gold-file 是外部金标路径，不能与 --gold {args.gold} 同时使用。")
        # 注意：run_external_gold 返回的是结论 dict，必须丢掉再 return 0。
        # 直接 return 会让 `SystemExit(dict)` 把整个 dict 打到 stderr 且 rc=1，
        # 成功运行反而被判失败（与 run_one 同一个坑）。
        run_external_gold(args)
        return 0
    if args.gold == "both":
        return run_both(args)
    # 注意：run_one 返回的是结论 dict，必须在这里丢掉再 return 0。
    # 直接 `return run_one(...)` 会让 `SystemExit(dict)` 变成
    # 「往 stderr 打整个 dict + 退出码 1」，rc=1 而 rc=0 的正向 case 全红。
    run_one(args, args.gold)
    return 0


# ---------------------------------------------------------------- 两种口径并排

def _norm_method(gold: Gold, method: str) -> str:
    """mean_prob 不可用时回落 majority，并说明原因（否则用户以为跑了 mean_prob）。"""
    if method == "mean_prob" and gold.mean_prob is None:
        print("[WARN] 无 answer_prob 或覆盖不全，mean_prob 口径不可用，回落 majority。")
        return "majority"
    return method


# ------------------------------------------------- 外部金标（人类/第三方真值）

# 外部金标下没有「判官参与构造金标」这回事，所以留一法下限**无定义**。
# 不能拿同一套三档判决硬套：那是拿一把不存在的尺子量东西。
# 这里的下限改用「判官群体中位数」作参照基线 —— 它回答的是另一个问题：
# 「最好的判官是否显著好于典型判官」，而不是「判官能否复现自己造的金标」。
EXT_METHOD = "human_gold"


def load_external_gold(path: str) -> Dict[str, str]:
    """读外部金标 CSV：必须有 item_id,gold 两列。

    刻意**不接受** --gold-file 里再指定口径：外部真值没有 majority/mean_prob
    之分，硬造一个「外部金标的两种口径」只会制造伪敏感性。
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = {"item_id", "gold"} - set(df.columns)
    if missing:
        sys.exit(f"[FATAL] --gold-file 缺少必需列: {sorted(missing)}；实际列={list(df.columns)}")
    g: Dict[str, str] = {}
    conflict = 0
    for it, gl in zip(df["item_id"].tolist(), df["gold"].tolist()):
        v = norm_answer(gl)
        if not v:
            continue
        if it in g and g[it] != v:
            conflict += 1
        g[it] = v
    if not g:
        sys.exit("[FATAL] --gold-file 里没有任何非空 gold。")
    if conflict:
        print(f"[WARN] --gold-file 有 {conflict} 行同一 item 给出不同 gold（取最后一个）。")
    return g


def _cluster_bootstrap_diff(
    cells: Dict[str, Tuple[np.ndarray, np.ndarray]],
    cells_top: Dict[str, Tuple[np.ndarray, np.ndarray]],
    slice_levels: List[str],
    case_levels: List[str],
    n_boot: int,
    seed: int,
) -> Tuple[float, float, float]:
    """按 case 整簇重采样，返回 (Δmacro, lo95, hi95)。点估计与 CI 同为 macro 口径。

    与 run_one 里的实现保持同一聚合语义：slice 内先按命中和/条数聚合，
    再对 slice 等权平均。这样 w 全 1 时重采样不改变点估计，CI 不会系统偏移。
    """
    si = {s: i for i, s in enumerate(slice_levels)}
    ci_ = {c: i for i, c in enumerate(case_levels)}
    S = np.zeros((len(slice_levels), len(case_levels)))
    N = np.zeros((len(slice_levels), len(case_levels)))
    S2 = np.zeros_like(S)
    N2 = np.zeros_like(N)
    for (sname, cname), (hs, ns) in cells.items():
        S[si[sname], ci_[cname]], N[si[sname], ci_[cname]] = hs, ns
    for (sname, cname), (hs, ns) in cells_top.items():
        S2[si[sname], ci_[cname]], N2[si[sname], ci_[cname]] = hs, ns

    def macro(Sx, Nx, idx):
        num = Sx[:, idx].sum(axis=1)
        den = Nx[:, idx].sum(axis=1)
        ok = den > 0
        if not ok.any():
            return float("nan")
        # 必须与 macro_micro() 同为**百分点**：那里算的是 hit.mean()*100。
        # 漏乘 100 的症状是 Δ=-2.40 却给出 CI=[-0.05,+0.01]（差 100 倍），
        # 而且点估计会掉到 CI 之外 —— 这正是 [4] 的自洽性守卫要抓的。
        return float((num[ok] / den[ok]).mean()) * 100.0

    base = macro(S, N, np.arange(len(case_levels))) - macro(
        S2, N2, np.arange(len(case_levels))
    )
    rng = np.random.default_rng(seed)
    d = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        idx = rng.integers(0, len(case_levels), size=len(case_levels))
        d[b] = macro(S, N, idx) - macro(S2, N2, idx)
    good = np.isfinite(d)
    if not good.any():
        return float("nan"), float("nan"), float("nan")
    d = d[good]
    return base, float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def run_external_gold(args) -> dict:
    """外部金标路径（A 路：尺子 = 人类/第三方真值）。

    与 run_one（B 路：尺子 = 判官共识）是**两个不同的问题**，绝不混算：
      · B 路问「没有人类真值时，这张榜能不能读」——下限是留一法自复现率。
      · A 路问「有了独立真值，判官里谁更好」——下限不存在，留一法无定义，
        改用群体中位数作参照基线。
    两条路的数字不可互相校验，只能各自成立。
    """
    P = print
    df, have_prob = load(args.csv)
    ext = load_external_gold(args.gold_file)
    n_all = df["item_id"].nunique()
    cov = int((df["item_id"].isin(ext)).sum())
    df = df[df["item_id"].isin(ext)].copy()
    if df.empty:
        sys.exit("[FATAL] votes 与 --gold-file 没有交集 item。")
    hit_item = df["item_id"].nunique()
    if hit_item < 1:
        sys.exit("[FATAL] 交集为 0。")

    P("=" * 78)
    P(f"bench-noise-floor  |  gold={EXT_METHOD}(外部金标)  |  items={hit_item}"
      f"  slices={df['slice'].nunique()}")
    P("=" * 78)

    P("\n[8] 外部金标入口")
    P(f"  gold 文件：{args.gold_file}")
    P(f"  覆盖：{hit_item}/{n_all} items 被外部金标命中"
      f"（丢弃无金标 item，不按缺金标算错）")
    P(f"  role=judge 行 = {int((df['role']=='judge').sum())}（外部金标下不需要判官投票来构造金标）")
    P("  [重要] 本路**不使用** [2] 的留一法下限：外部金标没有判官参与构造，"
      "留一法在此无定义。")
    P("          下限改用「判官群体中位数」作参照基线，回答的是"
      "『最好的判官是否明显好于典型判官』。")
    P("  [重要] 中位数是**顺序统计量**，只有所有判官同分母时才有意义；"
      "本路在 [9] 段把榜单强制收敛到各判官题集的交集上。")

    def score(sub: pd.DataFrame) -> Tuple[float, float, np.ndarray]:
        hit = agreement(sub, ext)
        ma, mi = macro_micro(hit, sub["slice"])
        return ma, mi, np.asarray(hit, dtype=float)

    P("\n[9] 各判官打外部金标（= 判官复现外部真值的准确率）")
    # 所有判官必须打**同一批题**：外部金标路没有 LOO 地板，但它的「群体中位数」
    # 参照基线把 25 个判官放在一列里排名。分母不同的判官同列 = 不可比的名次。
    # 实测 preference 档 claude-sonnet 只答 68/520、claude-opus-4-7 只答 316/520，
    # 其余 23 个满覆盖 520 —— 同一列里混了三个分母。
    common = None
    for _a, _s in df.groupby("actor", sort=False):
        _it = set(_s["item_id"])
        common = _it if common is None else (common & _it)
    common = common or set()
    # 交集为 0 时**不能**硬退出：「彼此不可比」本身就是结论，要报出来。
    # 退路是保持各判官各自的题集，把所有两两比较标成不可比，并声明中位数
    # 混了分母、不可引用。硬退出只会把一个可报告的测量变成一次崩溃。
    mixed_domain = not common
    if mixed_domain:
        df_aligned = df
        P(f"  [同域失败] 各判官题集**没有交集** -> 无法收敛到同一题域；"
          f"榜单仍按各判官自身题集列出，但所有两两比较标为『不可比』，"
          f"群体中位数混了分母、**不可引用**")
    else:
        df_aligned = df[df["item_id"].isin(common)]
    if not mixed_domain and df_aligned["item_id"].nunique() != hit_item:
        P(f"  [同域修正] 各判官题集交集 = {len(common)} items"
          f"（金标域 {hit_item} items）-> 榜单与中位数基线一律按交集算，"
          f"否则不同分母的判官会同列排名")
    rows = []
    for a, sub in df_aligned.groupby("actor", sort=False):
        ma, mi, hit = score(sub)
        rows.append({"system": a, "macro": ma, "micro": mi, "n": int(len(sub)),
                     "hit": hit, "case": sub["case_id"].to_numpy(),
                     "slice": sub["slice"].to_numpy(),
                     "item_id": sub["item_id"].to_numpy()})
    rows.sort(key=lambda r: -r["macro"])
    for r in rows:
        P(f"  {short_name(r['system']):<40}{r['macro']:>8.2f}%{r['micro']:>8.2f}%{r['n']:>7}")
    if not rows:
        sys.exit("[FATAL] 没有任何 actor。")
    top = rows[0]
    macro_list = [r["macro"] for r in rows]
    med = float(np.median(macro_list))
    spread = top["macro"] - rows[-1]["macro"]
    P(f"  => 榜首 {top['system']} macro={top['macro']:.2f}%  "
      f"群体中位数={med:.2f}%  全榜跨度={spread:.2f} 个百分点")

    P(f"\n[10] 配对 bootstrap（{args.n_boot} 次，按 case 整簇重采样；"
      f"点估计与 CI 同为 macro 口径）")
    cases = list(np.unique(np.concatenate([r["case"] for r in rows])))
    sls = list(np.unique(np.concatenate([r["slice"] for r in rows])))

    def cells_of(r):
        tmp = pd.DataFrame({"s": np.asarray(r["slice"]), "c": np.asarray(r["case"]),
                            "h": np.asarray(r["hit"], dtype=float)})
        g = tmp.groupby(["s", "c"], sort=True)["h"].agg(["sum", "count"])
        return {(s, c): (float(row["sum"]), float(row["count"])) for (s, c), row in g.iterrows()}

    top_cells = cells_of(top)
    top_items = list(top["item_id"])
    top_pos = {v: i for i, v in enumerate(top_items)}
    # 按 item 身份对齐到榜首的题序：JudgeSense 实测 relevance 有 3/25、
    # preference 有 4/25 个 judge 的行序与榜首不同，逐位比较会把题配错。
    aligned_ok, aligned_hit = {}, {}
    for r in rows:
        pos = {v: i for i, v in enumerate(r["item_id"])}
        keep = [pos[v] for v in top_items if v in pos]
        aligned_ok[r["system"]] = len(keep) >= 2
        aligned_hit[r["system"]] = np.asarray(r["hit"], dtype=float)[keep] if keep else np.array([])
    sig_vs_top = []
    P(f"  {'system':<50}{'Δmacro':>9}{'95%CI':>20}{'McNemar p':>12}")
    for r in rows[1:]:
        lo_, hi_, p, comparable = float("nan"), float("nan"), float("nan"), False
        h1, h2 = aligned_hit[r["system"]], top["hit"]
        if aligned_ok[r["system"]] and len(h1) == len(h2):
            _d, lo_, hi_ = _cluster_bootstrap_diff(cells_of(r), top_cells, sls, cases,
                                                   args.n_boot, 20261001)
            b = int(np.sum((h1 == 1) & (h2 == 0)))
            c_ = int(np.sum((h1 == 0) & (h2 == 1)))
            p = mcnemar_exact(b, c_)
            comparable = True
        tie = (lo_ <= 0 <= hi_) if (np.isfinite(lo_) and np.isfinite(hi_)) else True
        sig_vs_top.append((r["system"], (not tie) and comparable, r["macro"] - top["macro"],
                           lo_, hi_, p))
        note = "   平局" if comparable and tie else ("   显著" if comparable
                                                     else "   不可比（共同题集不足）")
        P(f"  {short_name(r['system']+' vs '+top['system']):<50}"
          f"{r['macro']-top['macro']:>9.2f}{f'[{lo_:+.2f},{hi_:+.2f}]':>20}{p:>12.4f}{note}")
    # ---- 多重比较校正与最小可检测效应 ----
    #
    # 上面 24 组配对检验逐个看 p<0.05 是不诚实的：即使**全部**系统真实无差异，
    # 不校正逐个 α 检验至少给出一个假拒绝的概率（该程序在全球零假设下的 FWER）
    # = 1−0.95^24 ≈ 70.8%。注意这个 70.8% 说的是**程序**在全为真时的表现，
    # 不是"我们这批拒绝里有 70.8% 是错的"——后者要知道有多少原假设为假，算不出。
    # 而本文真正要说的是「有多少个系统与榜首不可区分」，这句话需要族系校正后的结论。
    # 同时给出 MDE：若本研究在 δ=2.0 点上的功效不足，则「不显著」只能读作
    # 「测不出来」，不能读作「效应不存在」。
    holm = holm_bonferroni([x[5] for x in sig_vs_top if np.isfinite(x[5])], alpha=0.05)
    multi = {
        "holm": holm,
        "per_system": [
            {"system": x[0], "p_mcnemar": (round(float(x[5]), 8) if np.isfinite(x[5])
                                           else None),
             "ci_lo95": (round(float(x[3]), 4) if np.isfinite(x[3]) else None),
             "ci_hi95": (round(float(x[4]), 4) if np.isfinite(x[4]) else None),
             "mde": (round(mde_from_ci(x[3], x[4]), 4)
                     if np.isfinite(x[3]) and np.isfinite(x[4]) else None)}
            for x in sig_vs_top
        ],
        "delta_threshold_points": 2.0,
    }
    mdes = [v["mde"] for v in multi["per_system"] if v["mde"] is not None]
    if mdes:
        med_mde = float(np.median(mdes))
        multi["mde_median"] = round(med_mde, 4)
        multi["power_at_delta"] = round(power_at_delta(2.0, med_mde), 4)
        multi["power_note"] = (
            f"以中位 MDE={med_mde:.2f} 点、SE=MDE/1.96 反推，δ=2.0 点处的近似功效为 "
            f"{multi['power_at_delta']:.2f}。功效 <0.8 意味着「本研究的 MDE 已超过判决"
            f"门槛 δ=2.0」，此时 δ 档的判决没有统计效力，只能报 UNDECIDABLE。")
        P(f"\n[10c] 多重比较与可检测下限")
        P(f"  Holm-Bonferroni（{holm['n_tests']} 个配对检验，FWER 控制）："
          f"校正后显著 {holm['n_rejected']} 个，同一批 p 值逐个读不校正显著 "
          f"{holm['n_rejected_uncorrected']} 个")
        P(f"  若这 {holm['n_tests']} 个原假设全为真，不校正逐个 α=0.05 检验"
          f"至少一个假拒绝的概率（该程序的 FWER）= "
          f"{100 * (1 - 0.95 ** max(1, holm['n_tests'])):.1f}%"
          f"；这不是本库拒绝里假拒绝的比例")
        P(f"  中位 MDE = {med_mde:.2f} 点 ⇒ δ=2.0 点处近似功效 ≈ "
          f"{multi['power_at_delta']:.2f}")
        if multi["power_at_delta"] < 0.8:
            P(f"  [重要] MDE({med_mde:.2f}) > 判决门槛 δ=2.0：本研究在 δ 档**没有功效**，"
              f"该档判决不可下。'不显著' = 测不出来，不是效应不存在。")

    n_tie = sum(1 for x in sig_vs_top if not x[1] and np.isfinite(x[3]))
    n_nc = sum(1 for x in sig_vs_top if not np.isfinite(x[3]))
    P(f"  => 对榜首 {n_tie}/{len(sig_vs_top)} 组是统计平局"
      f"（{len(sig_vs_top)-n_tie-n_nc} 组可区分"
      + (f"，{n_nc} 组不可比" if n_nc else "") + "）")
    # 自洽性守卫（与 run_one [4] 段同一把尺）：点估计必须落在自己的 95%CI 内。
    # 这条守卫真在做事 —— 本函数第一版漏乘 100，Δ=-2.40 却报 CI=[-0.05,+0.01]，
    # 正是被它抓出来的。CI 与点估计不同量纲时重采样毫无意义，却不会报错。
    for _nm, _, _dl, _lo, _hi, _p in sig_vs_top:
        if np.isfinite(_lo) and np.isfinite(_hi) and not (_lo - 0.51 <= _dl <= _hi + 0.51):
            P(f"  [WARN] {_nm}: Δ={_dl:+.2f} 落在 95%CI [{_lo:+.2f},{_hi:+.2f}] 之外，"
              f"点估计与 CI 口径不一致，结果不可用。")

    # ---- 10b. 聚类结构：ICC、设计效应、两种 bootstrap 单位、macro/micro 消融
    #
    # [10] 的 CI 只报 case 级（整簇重采样）。只报一种单位 = 替读者做了选择：
    # item 级把同一 case 内的多条观测当独立 → CI 偏窄 → 可能假显著；
    # case 级保守，但若 case 数少则过宽。这里把两种都算出来，并给出 ICC
    # 作为「到底该信哪个」的定量依据（deff = 1 + (k−1)·ICC）。
    P(f"\n[10b] 聚类结构与双 bootstrap 单位（榜首 = {top['system']}）")

    # ---- ICC 的诚实口径 ----
    #
    # ⚠️ 本库**没有重复测量**：每个 (actor, item) 恰一行（实测 12500 行 / 12500 键），
    # 且 repeat/ab_order 两列装的是答案文本而非重复序号（值域 = ACCURATE/INACCURATE/
    # UNCLEAR），说明上游导出的列名与内容错位。因此 ICC(A,1) 在「同一判官重测同一题」
    # 这个标准设定下**不可算** —— 没有第二次读数可作相关。
    #
    # 所以这里算的是**判官间** ICC：把每个判官在每个题上的命中（0/1）当作一条测量，
    # item 作被测对象（行），judge 作重复测量（列）。它回答的是
    # 「题目难度的判官间一致性有多高」，**不是**「同一判官重测有多可靠」。
    # 两者不可互换：前者被题目异质性撑高，后者只含随机误差。
    # 报数时必须带 icc_kind 字段说明口径，否则读者会当成重测信度。
    cluster_stats: Dict[str, object] = {}
    icc_top_vs_bottom = None
    if not mixed_domain:
        per_judge = {}
        for _a, _s in df_aligned.groupby("actor", sort=False):
            h = agreement(_s, ext)
            per_judge[str(_a)] = dict(zip([str(x) for x in _s["item_id"]],
                                          np.asarray(h, dtype=float)))
        judge_names = sorted(per_judge)
        shared = sorted(set.intersection(*[set(v.keys()) for v in per_judge.values()])) \
            if judge_names else []
        if len(shared) >= 2 and len(judge_names) >= 2:
            M = np.array([[per_judge[j][it] for j in judge_names] for it in shared],
                         dtype=float)
            icc_between = icc_two_way_absolute_agree(M)
            # 相对 ICC：分母去掉 (k−1)·MSE，只留 MSR 与 (MSC−MSE)/n。
            # k 很大时这一项差别明显，两个都报，读者可自行判断。
            n_t, k_t = icc_between["n_targets"], icc_between["k_raters"]
            msr, msc, mse = (icc_between["ms_rows"], icc_between["ms_cols"],
                             icc_between["ms_error"])
            icc_between["icc_relative"] = float(
                (msr - mse) / (msr + k_t * (msc - mse) / n_t)) if n_t else float("nan")
            icc_between["icc_kind"] = (
                "inter-judge（行=item，列=judge，每 judge 一条命中 0/1 测量）。"
                "本库无重复测量（每 (actor,item) 恰一行；repeat/ab_order 列内容为答案"
                "文本，非重复序号），故不可算同判官重测的 ICC(A,1)。"
                "本值被题目异质性撑高，不能当作重测信度。")
            # ICC 的 item 级 bootstrap CI（审稿 3.7 要求）。
            # 区间必须在**同一批 shared items** 上算，与点估计同域。
            try:
                icc_between["ci95"] = icc_bootstrap_ci(M, n_boot=2000, seed=20261001)
            except Exception as _e:      # noqa: BLE001 — 区间算不出时如实降级
                icc_between["ci95"] = {"status": "ERROR", "reason": str(_e)[:200]}
            cluster_stats["icc_inter_judge"] = icc_between
            # 弃权率（2026-10-05 评审 B6 新增）：answer 不在金标取值域内 ⇒
            # 该题上没给出可比答案。与「答错」必须分开计数：混在一起报
            # 「准确率」会把一个会明确弃权的模型说成不称职；而 floor_robustness
            # 的 min 分位也会被弃权行为单独决定（preference 档实测 26.6%）。
            # 必须用**归一化后**的金标取值（load_external_gold 已跑过
            # norm_answer），直接拿 ext.values() 去比对原始 answer 会全部落空 ——
            # 实测导致每个判官弃权率都报 100%。
            gold_vals = set(ext.values())
            abstention = {}
            for jname, jsub in df_aligned.groupby("actor", sort=False):
                ans = pd.Series([norm_answer(v) for v in jsub["answer"]],
                                index=jsub.index).astype(str)
                n_tot = int(len(ans))
                n_out = int((~ans.isin(gold_vals)).sum())
                abstention[str(jname)] = {
                    "n_items": n_tot,
                    "n_abstain": n_out,
                    "abstain_pct": round(100.0 * n_out / n_tot, 2) if n_tot else None,
                }
            ranked = sorted(abstention.items(), key=lambda kv: -(kv[1]["abstain_pct"] or 0.0))
            cluster_stats["abstention_by_actor"] = abstention
            cluster_stats["abstention_worst"] = [
                {"actor": k, "abstain_pct": v["abstain_pct"], "n_items": v["n_items"]}
                for k, v in ranked[:3]
            ]
            P(f"  弃权率（answer 不在金标取值域内）最高的判官："
              + ", ".join(f"{e['actor']} {e['abstain_pct']:.1f}%"
                          for e in cluster_stats["abstention_worst"]))
            # ICC 的 item 级 bootstrap CI（审稿 3.7 要求）。
            # 区间必须在**同一批 shared items** 上算，与点估计同域。
            try:
                icc_between["ci95"] = icc_bootstrap_ci(M, n_boot=2000, seed=20261001)
            except Exception as _e:      # noqa: BLE001 — 区间算不出时如实降级
                icc_between["ci95"] = {"status": "ERROR", "reason": str(_e)[:200]}
            cluster_stats["icc_inter_judge"] = icc_between
            kbar = float(np.mean([len(v) for v in per_judge.values()]))
            cluster_stats["design_effect_judges"] = round(
                design_effect(icc_between["icc"], k_t), 4)
            P(f"  ICC(agree, 判官间) = {icc_between['icc']:.4f}"
              f"（n={n_t} items × k={k_t} judges；相对一致 ICC = "
              f"{icc_between['icc_relative']:.4f}）")
            P(f"  [口径] 判官间一致，非同判官重测 —— 本库无重复测量，"
              f"该值含题目异质性，不可当重测信度引用。")
            P(f"  设计效应 deff(k={k_t}) = {cluster_stats['design_effect_judges']:.3f}")
        else:
            P("  [WARN] 共同题域或判官数不足 2，ICC 不可算。")

    # ---- 双 bootstrap 单位：榜首 vs 榜尾（可逐题配对的那种比较）----
    if not mixed_domain and len(rows) >= 2:
        top_, bot_ = rows[0], rows[-1]
        pos_t = {str(v): i for i, v in enumerate(top_["item_id"])}
        pos_b = {str(v): i for i, v in enumerate(bot_["item_id"])}
        common_items = [v for v in pos_t if v in pos_b]
        case_of = {str(it): str(c) for it, c in zip(top_["item_id"], top_["case"])}
        pr = [(case_of[it], float(top_["hit"][pos_t[it]]),
               float(bot_["hit"][pos_b[it]])) for it in common_items]
        two = bootstrap_diff_two_units(pr, n_boot=args.n_boot, seed=20261001)
        cluster_stats["top_vs_bottom_two_units"] = two
        cluster_stats["top_vs_bottom"] = {
            "top": top_["system"], "bottom": bot_["system"],
            "n_common_items": len(common_items),
            "macro_diff": round(top_["macro"] - bot_["macro"], 4),
            "micro_diff": round(top_["micro"] - bot_["micro"], 4),
        }
        cluster_stats["macro_vs_micro_ablation"] = {
            "macro_diff_top_vs_bottom": cluster_stats["top_vs_bottom"]["macro_diff"],
            "micro_diff_top_vs_bottom": cluster_stats["top_vs_bottom"]["micro_diff"],
            "delta_macro_minus_micro": round(
                cluster_stats["top_vs_bottom"]["macro_diff"]
                - cluster_stats["top_vs_bottom"]["micro_diff"], 4),
            "note": "macro=切片等权，micro=逐条等权。两者之差是**聚合口径敏感性**，"
                    "与 bootstrap 单位（item/case 聚类）是两件独立的事："
                    "换口径改的是点估计，换单位改的是 CI 宽度。",
        }
        for u in ("item", "case"):
            stx = two.get(u)
            if stx:
                P(f"  榜首 vs 榜尾，按 {stx['unit']} 级重采样："
                  f"Δ={stx['diff']:+.2f} 点 "
                  f"95%CI=[{stx['lo95']:+.2f},{stx['hi95']:+.2f}]"
                  f"{'（跨 0）' if stx['crosses_zero'] else '（不跨 0）'}"
                  f"  n_units={stx['n_units']}")
        # 符号稳定性：Δ 的**符号**在重采样下会不会翻面。这比「CI 含不含 0」
        # 更强：CI 含 0 仍可能是绝大多数轮次同号、少数几轮拉宽区间；
        # 符号翻面率接近 50% 则说明这个差在本数据上根本站不住。
        ss = two.get("_sign_stability")
        if ss and ss.get("frac_negative_case") is not None:
            fi, fc = ss["frac_negative_item"], ss["frac_negative_case"]
            P(f"  符号稳定性：Δ<0 的重采样轮次占比 item 级 {fi:.1f}%、"
              f"case 级 {fc:.1f}%（0% = 符号从未翻面）")
            if max(fi or 0.0, fc or 0.0) >= 20.0:
                P(f"    [注意] case 级下有 {fc:.1f}% 的轮次给出**相反符号**的差。"
                  "这个方向在重采样下不稳定，报『榜首更强』需要同时报出这一项。")
        # 地板稳健性：中位数未必代表典型判官，min 也未必是最差判官的能力。
        fr_bits = []
        if not mixed_domain and len(macro_list) >= 2:
            lo1 = min(macro_list)
            lo2 = sorted(macro_list)[1]
            P(f"  地板稳健性：min={lo1:.2f}%  2nd-min={lo2:.2f}%  "
              f"median={med:.2f}%  max={max(macro_list):.2f}%"
              f"（中位数处并列 {sum(1 for v in macro_list if abs(v-med) < 1e-9)} 个）")
            # 阈值取 3 点：preference 档实测 lo2−lo1 = 3.12 点、中位数处
            # 并列 5 个、且榜尾靠 26.6% 弃权垫底 —— 这些单独看都不算极端，
            # 合起来才是「地板下沿只由一个判官决定」。5 点太松（实测不触发）。
            if lo2 - lo1 > 3.0:
                P(f"    [注意] 最小与次小之间差 {lo2-lo1:.2f} 点：地板的下沿由**一个**判官决定。"
                  f"榜尾是 {rows[-1]['system']}（{lo1:.2f}%）。")
            if (med - lo2) / max(1e-9, max(macro_list) - lo1) < 0.5:
                P(f"    [注意] 中位数离下沿比离上沿近：榜首比中位数高 "
                  f"{top['macro']-med:.2f} 点，但榜首比最差判官高 "
                  f"{top['macro']-lo1:.2f} 点 —— 两个数字都要报。")
        tvb = cluster_stats["top_vs_bottom"]
        P(f"  macro/micro 消融：Δmacro={tvb['macro_diff']:+.2f} 点 vs "
          f"Δmicro={tvb['micro_diff']:+.2f} 点（两口径差 "
          f"{cluster_stats['macro_vs_micro_ablation']['delta_macro_minus_micro']:+.2f} 点）")
        if (two.get("item") and two.get("case")
                and two["item"]["crosses_zero"] != two["case"]["crosses_zero"]):
            P(f"  [注意] 两种 bootstrap 单位给出**相反的显著性结论**"
              f"（item 级{'不' if two['item']['crosses_zero'] else ''}跨 0，"
              f"case 级{'不' if two['case']['crosses_zero'] else ''}跨 0）。"
              f"只报一种单位就是在替读者做选择，两种都必须出现在正文。")
    else:
        P("  [跳过] 题域混了分母或不足两个系统，双单位 bootstrap 不适用。")


    P("\n[11] 结论")
    margin = top["macro"] - med
    if mixed_domain:
        # 题域混了分母 => 中位数不是顺序统计量、margin 不可引用。
        # 报 NOT_COMPARABLE 而不是 READABLE/UNREADABLE：那三个词都暗示
        # 「在同一把尺上比过了」，而这里根本没建立起一把尺。
        verdict = "NOT_COMPARABLE"
        P("  VERDICT = NOT_COMPARABLE")
        P(f"    各判官题集无交集 => 不存在共同题域，中位数 {med:.2f}% 混了分母、不可引用，"
          f"榜首与中位数之差 {margin:+.2f} 点也不构成判据")
        P("    这是测量本身失败，不是测量结果差：先补齐共同题集再比。")
    elif top["macro"] > med + 1e-9 and margin < 2.0:
        verdict = "NEAR_MEDIAN_ACTOR"
        P("  VERDICT = NEAR_MEDIAN_ACTOR")
        P(f"    榜首 {top['macro']:.2f}% 仅比群体中位数 {med:.2f}% 高 {margin:.2f} 点"
          f"（< 2.0 门槛）")
        P("    报『最佳判官』是误导：最好的那个并不明显好于典型判官。")
    elif margin >= 2.0:
        verdict = "ABOVE_MEDIAN_ACTOR"
        P(f"  VERDICT = ABOVE_MEDIAN_ACTOR（榜首比群体中位数高 {margin:.2f} 点）")
        P(f"    注意：这里的『下限』是参照基线（群体中位数），**不是**判官自复现率；"
          f"外部金标下不存在后者。")
        P(f"    另有 {n_tie}/{len(sig_vs_top)} 组对榜首平局 -> 报『第 N 名』"
          f"前先看是否落在同一不可区分组里。")
    else:
        verdict = "AT_OR_BELOW_MEDIAN_ACTOR"
        P("  VERDICT = AT_OR_BELOW_MEDIAN_ACTOR")
        P(f"    榜首 {top['macro']:.2f}% 不高于群体中位数 {med:.2f}%")
    if spread < 5.0:
        P(f"  [附] 全榜跨度仅 {spread:.2f} 点 -> 报『与榜首不可区分的一组』"
          f"比报『第 N 名』诚实。")

    out = {
        "gold_method": EXT_METHOD,
        "gold_source": str(args.gold_file),
        "n_items": int(hit_item),
        "n_items_before_filter": int(n_all),
        "n_items_common_to_all_actors": int(len(common)),
        "judges": [r["system"] for r in rows],
        "ceiling_loo_macro": None,
        "floor_basis": "median_of_actors（外部金标下留一法无定义）",
        "floor_median_macro": round(med, 4),
        # 地板的稳健性快照（2026-10-05 评审 B6 新增）。只报 median 会把
        # 「地板由谁决定」这件事藏起来：preference 档 25 个判官里
        # claude-sonnet 弃权 26.6%，把地板从 59.375 拉到 39.06，
        # 一个标注者的行为决定了「最差判官」是谁。四个分位并排给出，
        # 读者能自己看出地板离 2nd-min 有多远。
        "floor_robustness": {
            "min": round(float(min(macro_list)), 4),
            "second_min": round(float(sorted(macro_list)[1]), 4) if len(macro_list) > 1 else None,
            "median": round(med, 4),
            "max": round(float(max(macro_list)), 4),
            "n_actors": len(macro_list),
            "ties_at_median": int(sum(1 for v in macro_list if abs(v - med) < 1e-9)),
            "bottom_actor": rows[-1]["system"],
            "bottom_actor_macro": round(rows[-1]["macro"], 4),
            "note": "min/second_min/median/max 都是**同一批判官在共同题域上的 macro**；"
                    "bottom_actor 若只靠弃权行为（answer 不在金标取值域内）垫底，"
                    "min 就不是「最差判官的能力」而是「它的弃权率」。"
                    "调用方必须同时读 clustering.abstention_by_actor。",
        },

        "abstention_worst": (
            cluster_stats.get("abstention_worst") if not mixed_domain else None),
        # 顺序统计量的前提：所有判官同分母。记录同域后的 n 与原始 n 供核对。
        "median_computed_on_common_items": not mixed_domain,
        "common_items_empty": mixed_domain,
        "rows_dropped_for_alignment": int(len(df) - len(df_aligned)),
        "leaderboard": [
            {"system": r["system"], "macro": round(r["macro"], 4),
             "micro": round(r["micro"], 4), "n": r["n"],
             "n_items_before_alignment": int(df[df["actor"] == r["system"]]["item_id"].nunique())}
            for r in rows
        ],
        "ties_vs_top": n_tie,
        "compared": len(sig_vs_top),
        "verdict": verdict,
        "multiplicity": multi,
        "self_grading_check": self_grading_overlap(
            df, _load_judges_for_overlap(getattr(args, "judges_file", None))),
        "clustering": cluster_stats,
    }
    if getattr(args, "json", None):
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, ensure_ascii=False)
        P(f"\n[JSON] -> {args.json}")
    return out


def short_name(name: str) -> str:
    """截断但保持可区分：模型名差异常在尾部（…/deepseek-v4-pro vs -flash）。"""
    return name if len(name) <= 39 else "…" + name[-38:]


def _rank_map(rows: List[dict]) -> Dict[str, int]:
    return {r["system"]: i + 1 for i, r in enumerate(rows)}


def _gold_coverage(df: pd.DataFrame, sdf: pd.DataFrame, gold_map: Dict[str, str]) -> dict:
    """金标覆盖率：分母的定义必须可读，不能只存在于日志行里。

    「没测到」与「测了全错」在数值上差一个分母，在论证上差一整个结论。
    问句档实测 14292 题里有 1188 题根本不在 judge 标注集内（judge 行数为 0），
    却有 9 个系统在上面作答 3232 行；把这些行算成全错会把各系统压低 1.0~5.9 点。
    """
    items_all = set(df["item_id"].unique())
    items_gold = set(gold_map)
    per_sys = {}
    for s, sub in sdf.groupby("actor", sort=False):
        scored = int(sub["item_id"].isin(gold_map).sum())
        per_sys[s] = {
            "rows_total": int(len(sub)),
            "rows_scored": scored,
            "coverage": round(scored / len(sub), 6) if len(sub) else float("nan"),
        }
    tot_rows = int(len(sdf))
    tot_scored = sum(v["rows_scored"] for v in per_sys.values())
    return {
        "items_total": len(items_all),
        "items_with_gold": len(items_gold),
        "items_without_gold": len(items_all - items_gold),
        "item_coverage": (round(len(items_gold) / len(items_all), 6) if items_all
                          else float("nan")),
        "rows_total": tot_rows,
        "rows_scored": tot_scored,
        "rows_unscored": tot_rows - tot_scored,
        "row_coverage": (round(tot_scored / tot_rows, 6) if tot_rows else float("nan")),
        "policy": "rows whose item has no gold label are excluded from both numerator "
                  "and denominator (unmeasured, not measured-and-wrong)",
        "per_system": per_sys,
    }


def domain_membership_ok(rows, floor_set) -> bool:
    """同域闸的判据本身：每个系统的**实计分题集**必须与地板题集是同一个集合。

    为什么单列成函数：判据要能被直接测试。走完整流水线是测不出分歧的 ——
    上游已经把地板与榜首一起限制到公共留一域 U 上（见 [定义域提示] 那段），
    所以成员相等在现有路径里**由构造保证**，计数判据只是它的一个代理。
    代理会失效的那一刻是上游对齐被改掉的时候：那时成员判据仍然拦得住，
    计数判据拦不住（两个大小相同、成员不同的题集照样放行）。
    """
    if not rows or not floor_set:
        return False
    return all(set(r.get("scored_set") or set()) == set(floor_set) for r in rows)


def _digest(items) -> str:
    """题集的短摘要：让读者能核「两侧是不是同一批题」，而不必随报告发布全部题号。"""
    import hashlib
    return hashlib.sha256("|".join(sorted(str(i) for i in items)).encode()).hexdigest()[:16]


def _leaderboard(df: pd.DataFrame, sdf: pd.DataFrame, gold_map: Dict[str, str]
                 ) -> Tuple[List[dict], Dict[str, np.ndarray]]:
    """按 actor 打金标，同时记录「可计分行」的掩码与覆盖率。

    分母纪律（承重）：只对**有金标的行**计分。无金标的 item 是「没测到」，
    计入分母等于把未测题算成全错。返回值里的 per-system n 是实计分行数，
    另给 n_items_unscored 供报告显式披露覆盖率。
    """
    rows: List[dict] = []
    detail: Dict[str, np.ndarray] = {}
    for s, sub in sdf.groupby("actor", sort=False):
        hit = agreement(sub, gold_map)
        ma, mi = macro_micro(hit, sub["slice"])
        scored = int(hit.notna().sum())
        _ids = np.asarray(sub["item_id"])
        _hit = np.asarray(hit, dtype=float)
        rows.append({"system": s, "macro": ma, "micro": mi, "n": scored,
                     "n_rows": int(len(sub)), "n_items_unscored": int(len(sub)) - scored,
                     "hit": _hit, "case": sub["case_id"].to_numpy(),
                     "slice": sub["slice"].to_numpy(),
                     "item_id": _ids,
                     # 实计分题集（= 有金标的那些行）。同域闸按**成员**判，
                     # 不按 |题集| 判：两个大小相同、成员不同的题集不是同一个分母。
                     "scored_set": set(_ids[~np.isnan(_hit)].tolist())})
        detail[s] = np.asarray(hit, dtype=float)
    rows.sort(key=lambda r: -r["macro"])
    return rows, detail


def run_both(args) -> int:
    """同一份数据跑两种金标口径，并排报告判决与名次的翻转位。

    判定原则（踩过的坑）：**能翻转的东西必须显式报出来**，而不是让用户自己比两屏输出。
    只看单口径输出的人会把「口径选得好」误当成「结论稳」——而 §[7] 的表就是用来
    戳破这一点的。另外，两次运行共用的 judge 分歧诊断只打印一次（它在 [1] 段，
    与口径无关），否则对照表前后会重复两遍让人以为有两个数据集。
    """
    a = run_one(args, "majority")
    b = run_one(args, "mean_prob")

    P = print
    ma, mb = a["gold_method"], b["gold_method"]

    def dump(payload) -> None:
        if getattr(args, "json", None):
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            P(f"\n[JSON] -> {args.json}")

    if ma == mb:
        # mean_prob 不可用时已回落成 majority —— 这时两遍输出逐字相同，
        # 再打对照表会给人「跑了两种口径」的错觉。直接说明并返回。
        P("\n" + "=" * 78)
        P(f"[7] 口径对照表  |  跳过：{ma} 下 mean_prob 不可用（见上方 [WARN]），"
          f"两种口径实为同一把尺。")
        P("=" * 78)
        P("  -> 补 answer_prob 列（或用 --gold majority 明确只要一种口径）才能做对照。")
        dump({"gold_comparison": "skipped", "reason": f"{ma} 下 mean_prob 不可用",
              "methods": {ma: a}})
        return 0

    ra, rb = a["leaderboard"], b["leaderboard"]
    P("\n" + "=" * 78)
    P(f"[7] 口径对照表  |  {ma}  vs  {mb}  |  items={a['n_items']}")
    P("=" * 78)

    # 判决是否翻转
    if a["verdict"] == b["verdict"]:
        P(f"  VERDICT 两种口径一致 = {a['verdict']}")
    else:
        P(f"  [翻转] VERDICT: {ma} -> {a['verdict']}   |   {mb} -> {b['verdict']}")
        P(f"         下限 {a['ceiling_loo_macro']}% / {b['ceiling_loo_macro']}%  vs 榜首 "
          f"{ra[0]['macro']}% / {rb[0]['macro']}%")
        P("         => 这份榜单的可读性由金标口径决定，不是数据集的客观属性。"
          "报结论时必须写明 gold=什么。")

    # 榜首是否换人
    P(f"\n  {'system':<40}{ma+' macro':>16}{mb+' macro':>16}{'Δ':>9}{'名次':>12}")
    ra_m = {r["system"]: r["macro"] for r in ra}
    rb_m = {r["system"]: r["macro"] for r in rb}
    rk_a, rk_b = _rank_map(ra), _rank_map(rb)
    names = sorted(set(rk_a) | set(rk_b), key=lambda s: (rk_a.get(s, 99), rk_b.get(s, 99)))
    flips = []
    for i, s in enumerate(names):
        ma_ = ra_m.get(s)
        mb_ = rb_m.get(s)
        ra_rank = rk_a.get(s, 0)
        rb_rank = rk_b.get(s, 0)
        moved = ra_rank != rb_rank
        if moved:
            flips.append((s, ra_rank, rb_rank))
        d = (mb_ - ma_) if (ma_ is not None and mb_ is not None) else None
        P(f"  {short_name(s):<40}{ma_:>15.2f}%{mb_:>15.2f}%"
          f"{(d if d is not None else float('nan')):>9.2f}"
          f"{f'{ra_rank} -> {rb_rank}':>12}" + ("  <== 换位" if moved else ""))

    if flips:
        P(f"\n  [名次敏感] {len(flips)}/{len(names)} 个系统换位: "
          + ", ".join(f"{short_name(s)} {x}->{y}" for s, x, y in flips))
        # 换位是否只是噪声：相邻两名差多少
        for s, x, y in flips:
            if s in ra_m and s in rb_m:
                others_a = sorted((v for k, v in ra_m.items() if k != s), reverse=True)
                others_b = sorted((v for k, v in rb_m.items() if k != s), reverse=True)
                P(f"    {short_name(s):<36} 换位幅度 {x - y} 位；"
                  f"该系统 macro {ra_m[s]:.2f} -> {rb_m[s]:.2f}"
                  f"（{rb_m[s]-ra_m[s]:+.2f} 点）")
    else:
        P("  名次在两种口径下完全一致 -> 榜单名次对金标口径稳健。")

    # 下限与 judge 自洽性差异
    P(f"\n  噪声下限(含自身) {a['ceiling_inclusive_macro']}% / {b['ceiling_inclusive_macro']}%"
      f"   留一法 {a['ceiling_loo_macro']}% / {b['ceiling_loo_macro']}%")
    P(f"  两 judge 互差 {a['judge_macro_gap']} 点 / {b['judge_macro_gap']} 点")
    dump({
        "gold_comparison": "compared",
        "verdict_flipped": a["verdict"] != b["verdict"],
        "n_systems": len(names),
        "n_rank_flips": len(flips),
        "rank_flips": [{"system": s, f"{ma}": x, mb: y} for s, x, y in flips],
        "systems": [
            {"system": s,
             f"{ma}_macro": ra_m.get(s), f"{mb}_macro": rb_m.get(s),
             f"{ma}_rank": rk_a.get(s), f"{mb}_rank": rk_b.get(s)}
            for s in names
        ],
        "methods": {ma: a, mb: b},
    })
    return 0


def run_one(args, method: str) -> dict:
    """单口径跑完整流水线。返回结构化结论供 --gold both 对照。

    打印仍留在这里（不拆成纯计算函数）：[4] 段的守卫要对着逐行输出说话
    （点估计是否落在自己 CI 内、聚合口径是否等于点估计），拆开就得把字符串
    当返回值来回传，反而更容易出静默不一致。
    """
    df, have_prob = load(args.csv)
    jdf = df[df["role"] == "judge"].copy()
    sdf = df[df["role"] == "system"].copy()
    if jdf.empty:
        sys.exit("[FATAL] 没有 role=judge 的行：无法构造金标，也就无从谈噪声下限。")
    if sdf.empty:
        sys.exit("[FATAL] 没有 role=system 的行：本工具要判的是『榜单读数可不可读』。")

    gold = build_gold(jdf, have_prob, args.tie_rule)
    method = _norm_method(gold, method)
    gold_map = gold.mean_prob if method == "mean_prob" else gold.majority
    votes = {(r.item_id, r.actor): r.answer_n for r in jdf.itertuples()}
    probs = {
        (r.item_id, r.actor): (r.answer_prob if have_prob else float("nan"))
        for r in jdf.itertuples()
    }

    P = print
    P("=" * 78)
    P(f"bench-noise-floor  |  gold={method}  |  items={df['item_id'].nunique()}"
      f"  slices={df['slice'].nunique()}")
    P("=" * 78)

    # ---- 1. 金标构成与分歧诊断
    P("\n[1] 金标构成与 judge 分歧诊断")
    n_items = len(gold.n_judges)
    disagree = sum(1 for c in gold.counts.values() if len(c) > 1)
    k = min(gold.n_judges.values()) if gold.n_judges else 0
    tie_or_alien = sum(1 for c in gold.counts.values() if c and max(c.values()) <= 1.0 and len(c) > 1)
    P(f"  judges: {', '.join(gold.judges)}")
    P(f"  items={n_items}  有分歧 items={disagree} ({100.0*disagree/max(1,n_items):.1f}%)"
      f"  无任何一致项={tie_or_alien}")
    # 平均自报置信度：均值投票退化为加权投票的探针
    if have_prob:
        for j in gold.judges:
            s = [r.answer_prob for r in jdf.itertuples() if r.actor == j and np.isfinite(r.answer_prob)]
            if s:
                P(f"    {j:<28} 平均自报置信度 {np.mean(s):.4f}  (n={len(s)})")
        if len(gold.judges) == 2 and len(gold.judges) == 2:
            ms = []
            for j in gold.judges:
                s = [r.answer_prob for r in jdf.itertuples() if r.actor == j and np.isfinite(r.answer_prob)]
                ms.append(np.mean(s) if s else float("nan"))
            if np.isfinite(ms[0]) and np.isfinite(ms[1]):
                ratio = ms[0] / ms[1] if ms[1] > 0 else float("inf")
                flag = "  <== 均值投票已退化为加权投票" if ratio > 1.05 or ratio < 0.95 else ""
                P(f"    置信度不对称比 = {ratio:.3f}x{flag}")
    # 胜率：两 judge 直接对撞的 items 上谁被金标选中
    if len(gold.judges) == 2:
        j0, j1 = gold.judges
        w0 = w1 = neither = 0
        for item in gold.n_judges:
            a0, a1 = votes.get((item, j0), ""), votes.get((item, j1), "")
            if a0 == "" or a1 == "" or a0 == a1:
                continue
            g = gold_map.get(item, "")
            if g == a0:
                w0 += 1
            elif g == a1:
                w1 += 1
            else:
                neither += 1
        tot = w0 + w1 + neither
        if tot:
            P(f"  两 judge 对撞 {tot} items：金标判 {j0}={w0} ({100.0*w0/tot:.1f}%) / "
              f"{j1}={w1} ({100.0*w1/tot:.1f}%) / 两者皆非={neither} ({100.0*neither/tot:.1f}%)")
            if neither:
                P(f"    [注意] {neither} items 的金标答案**不是任何 judge 给过的答案**"
                  f"（构造规则的副产物，不是共识）")

    # ---- 2. 噪声下限
    P("\n[2] 噪声下限 —— judge 打自己参与生成的金标")
    floor_rows = []
    loo_maps = leave_one_out(gold, method, votes, probs) if args.loo else None
    # eq:loo 给的是**每个生成器自己的** c^-，floor 由「榜首必须跨过的那个数」决定。
    # 论文 §Threat Model 明写「the maximum over generators is the relevant bound,
    # since a leader must clear all of them」=> 取 max，不是 min。旧代码取 min，
    # 也就是拿「最容易跨过的那个生成器」当门槛 —— 方向反了。
    #
    # LOO 地板与榜首的分母必须一致。真 LOO 的 c^- 只在「剔除 g 后仍有票」的题上
    # 有定义，而各 g 的定义域**大小不同**（实测 question 档 anthropic 12902 /
    # openai 12608 个 item）。若地板取各自定义域、榜首取全金标域，
    # margin = 榜首 - 地板 就是两个不同分母相减。修法：取公共题域
    # U = 所有生成器都产出了 c^- 标签的题，**地板与榜首都在 U 上算**。
    # 两组数都写进 JSON（floor_per_generator[].loo_macro / .loo_macro_u），
    # 下游能验证判决用的是同域的那一个。
    loo_domain: set = set()
    if loo_maps:
        loo_domain = set.intersection(*[set(m) for m in loo_maps.values()])
        # 地板域与榜单域**结构性地无法对齐**，这不是可以靠取交集修掉的 bug。
        # 地板打的是 c^- 标签（= 剔除 g 后另一个生成器那一票），榜单打的是主金标。
        # 平票口径 unmeasured 下主金标只存在于「两生成器本来投合」的题上；
        # 而在那些题上 c^- 恒等于生成器自己的答案 ⇒ 地板被钉死在 100.00%。
        # （决策档实测：两 judge 一致 1084 题 / 平票 436 题；取交集后地板 100.00%。）
        # 反方向也不行：分歧题（唯一带信号的题）在 unmeasured 下没有主金标。
        # 结论：unmeasured 下这个量测不出地板，判决必须 fail-closed 到
        # UNDECIDABLE_DOMAIN_MISMATCH，而不是把两个分母相减出一个假的 margin。
        # 曾在这里试过 loo_domain &= set(gold_map)，结果地板塌成 100% —— 已回退。
        n_loo_only = len(loo_domain - set(gold_map))
        if n_loo_only:
            P(f"  [定义域不可对齐] 公共留一域 {len(loo_domain)} items 中有 {n_loo_only} 题"
              f"没有主金标（{args.tie_rule} 口径下的平票题）。地板在这 "
              f"{len(loo_domain)} 题上算，榜首只能在 {len(loo_domain)-n_loo_only} 题上算：")
            P("    两侧分母不同，margin 无意义。注意这**不是**取交集能修的："
              "在两生成器投合的题上 c^- 恒等于生成器自己的答案，")
            P(f"    取交集会让地板塌成 100.00%（决策档实测），比原来更糟。"
              f"要把地板与榜单压到同一批题上，")
            P(f"    唯一办法是换平票口径（--tie-rule lexicographic）。")
    # 地板侧的逐行数组只留在内存里，不进 floor_rows —— 那份字典要被 JSON 序列化，
    # numpy 数组进去会让 json.dump 炸掉。判决用的 margin 需要对地板做重采样，
    # 而重采样必须拿到与榜首同一套 (slice, case, hit) 三元组。
    floor_u_rows: Dict[str, Dict[str, np.ndarray]] = {}
    for j in gold.judges:
        sub = jdf[jdf["actor"] == j]
        # 含自身口径在金标域 gold_map 上算（c 的定义域）。
        hit = agreement(sub, gold_map)
        ma, mi = macro_micro(hit, sub["slice"])
        rec = {"judge": j, "macro": round(ma, 2), "micro": round(mi, 2),
               "loo_macro": None, "loo_n": None, "loo_macro_u": None}
        # 原始精度另存一份：ceiling 与 margin **必须**从未取整的值算出来。
        # 10-12 实测：旧代码把 loo_macro_u 先 round(...,2) 再 max()，于是
        # margin = 4 位榜首 − 2 位地板，coherence 凭空得到 +0.0036 的"越过地板"，
        # 而同一档配对 bootstrap 的 97.5% 上界正好是 0.0 —— 点估计被自己的区间否证，
        # 由 make_m25_summary.py 的自洽守卫拦下（rc=4，摘要没落盘）。
        rec["_macro_raw"] = float(ma)
        rec["_loo_raw"] = None
        rec["_loo_u_raw"] = None
        if loo_maps is not None:
            hitl = agreement(sub, loo_maps[j])
            mal, _ = macro_micro(hitl, sub["slice"])
            rec["loo_macro"] = round(mal, 2)
            rec["_loo_raw"] = float(mal)
            rec["loo_n"] = int(hitl.notna().sum())
            if loo_domain:
                sub_u = sub[sub["item_id"].isin(loo_domain)]
                hitu = agreement(sub_u, loo_maps[j])
                mau, _ = macro_micro(hitu, sub_u["slice"])
                rec["loo_macro_u"] = round(mau, 2)
                rec["_loo_u_raw"] = float(mau)
                floor_u_rows[j] = {"hit": np.asarray(hitu, dtype=float),
                                   "slice": sub_u["slice"].to_numpy(),
                                   "case": sub_u["case_id"].to_numpy()}
        floor_rows.append(rec)
        extra = (f"   留一法 macro={rec['loo_macro']:.2f}%  (n={rec['loo_n']})"
                 + (f"  同域U={rec['loo_macro_u']:.2f}%" if rec["loo_macro_u"] is not None else "")
                 if rec["loo_macro"] is not None else "")
        P(f"  {j:<28} macro={ma:6.2f}%  micro={mi:6.2f}%{extra}")
    incl = [r["macro"] for r in floor_rows]
    loo_v = [r["loo_macro_u"] for r in floor_rows if r["loo_macro_u"] is not None]
    loo_all = [r["loo_macro"] for r in floor_rows if r["loo_macro"] is not None]
    # 判决与 margin 用原始精度；上面那三列只供打印与逐档披露。
    incl_raw = [r["_macro_raw"] for r in floor_rows if r.get("_macro_raw") is not None]
    loo_u_raw = [r["_loo_u_raw"] for r in floor_rows if r.get("_loo_u_raw") is not None]
    loo_raw = [r["_loo_raw"] for r in floor_rows if r.get("_loo_raw") is not None]
    ceiling_incl = max(incl_raw) if incl_raw else (max(incl) if incl else None)
    ceiling_loo = (max(loo_u_raw) if loo_u_raw else (max(loo_raw) if loo_raw else None))
    if ceiling_loo is None and loo_v:
        ceiling_loo = max(loo_v)   # 退化回退：只在原始列全缺时才会走到这里
    if loo_domain and set(gold_map) - loo_domain:
        P(f"  [定义域提示] 公共留一题域 U={len(loo_domain)} items，比金标域少 "
          f"{len(set(gold_map) - loo_domain)} items（这些题上 c^- 无定义）"
          f" -> 地板与榜首都在 U 上算，保证同分母")
    P(f"  => 含自身口径下限（偏高侧）        = {ceiling_incl:.2f}%   "
      f"（min={min(incl):.2f}%，含自身把自己抬分 ⇒ 是**保守偏高**的一侧）")
    if ceiling_loo is not None:
        P(f"  => 真留一法口径下限（eq:loo）     = {ceiling_loo:.2f}%   <== 用这个判榜")
        if loo_all and max(loo_all) - min(loo_all) > 2.0:
            P(f"     [敏感性] 各自定义域上的真留一下限 max={max(loo_all):.2f}% / "
              f"min={min(loo_all):.2f}%（差 {max(loo_all)-min(loo_all):.2f} 点）"
              f" —— 差值来自定义域不同，不可直接比较；判决用同域值。")
        if len(gold.judges) < MIN_LOO_GENERATORS:
            P(f"     [定义退化的声明] m={len(gold.judges)} < {MIN_LOO_GENERATORS}："
              f"剔除 g 自己那一票后只剩 {max(1, len(gold.judges)-1)} 个生成器，"
              "c^- 的金标退化成「另一个生成器的答案」。此时这个量是**生成器之间的一致率**，"
              "不是 c 的自复现率，性质与 m≥3 不同，必须显式标注后才可引用。")
    ceiling = ceiling_loo if ceiling_loo is not None else ceiling_incl
    _thin = [r["judge"] for r in floor_rows
             if (r.get("loo_n") or 0) < 30 and r.get("loo_macro") is not None]
    if _thin and len(_thin) == len(floor_rows):
        P(f"  [支撑提示] 全部 {len(_thin)} 个生成器的留一计分行数 <30 —— "
          "地板由极薄的支撑算出，读数本身不可引用。")
    gap_j = max(incl) - min(incl)
    note_j = ("两 judge 完全一致（0.00 点），这把金标内部自洽，噪声下限仍非零是因为"
              "judge 要和自己共同构造的答案对齐" if gap_j < 0.05
              else "同一批题、同一把尺，差这么多 = 金标构造本身就带噪")
    P(f"  => 两 judge 互差 = {gap_j:.2f} 个百分点（{note_j}）")

    # ---- 3. 榜单
    # 有 LOO 时，榜单也收敛到公共题域 U：floor 用 U 算、榜首也必须用 U 算，
    # 否则 [5] 的 margin 是两个分母相减。U 为空（无可用 c^-）时退回金标域。
    lb_domain = loo_domain if loo_domain else set(gold_map)
    # 曾在这里再与「各 system 作答题集的交集」取交集，想让榜单内部同域。
    # **已回退**：那会让只答了少数题的 system 直接从榜单上消失（实测自测 case 18
    # 的 sys-sparse 覆盖 2/12 个 case，交集后它一行不剩，于是「无定义重采样
    # 轮次」这份披露永远不会打印）。这与论文 §3.1 的「未测到 ≠ 测错、未测到必须
    # 显式披露」正好相反：不是把稀疏系统算成全错，而是把它从报告里删掉。
    # 正确做法是**不统一分母，而是把分母如实报出来**：每个 system 各按自己答了
    # 且有金标的题计分，稀疏部分记进 n_items_unscored；当各 system 分母不等时，
    # 判决层 fail-closed（见 UNDECIDABLE_DOMAIN_MISMATCH），而不是偷偷改题集。
    P(f"\n[3] 榜单（system 打同一把金标{'，与地板同域 U' if loo_domain else ''}）")
    lb_df = df[df["item_id"].isin(lb_domain)] if loo_domain else df
    lb_sdf = lb_df[lb_df["role"] == "system"]
    rows, _ = _leaderboard(lb_df, lb_sdf, gold_map)
    P(f"  {'system':<40}{'macro':>9}{'micro':>9}{'n':>7}{'未测':>7}{'Δmacro-micro':>14}")
    for r in rows:
        P(f"  {short_name(r['system']):<40}{r['macro']:>8.2f}%{r['micro']:>8.2f}%{r['n']:>7}"
          f"{r['n_items_unscored']:>7}{r['macro']-r['micro']:>14.2f}")
    n_unscored_any = [r for r in rows if r["n_items_unscored"]]
    if n_unscored_any:
        tot_u = sum(r["n_items_unscored"] for r in rows)
        tot_n = sum(r["n_rows"] for r in rows)
        P(f"  => 金标覆盖：{tot_n - tot_u}/{tot_n} 行被计分"
          f"（{tot_u} 行所在 item 无金标，**已剔除而非记全错**，逐系统见「未测」列）")
    top = rows[0]
    spread_macro = top["macro"] - rows[-1]["macro"]
    spread_micro = top["micro"] - rows[-1]["micro"]
    P(f"  榜首 {top['system']} macro={top['macro']:.2f}%  全榜跨度 macro={spread_macro:.2f}"
      f" / micro={spread_micro:.2f} 个百分点")
    macro_sens = [r for r in rows if abs(r["macro"] - r["micro"]) >= 5.0]
    if macro_sens:
        P(f"  [口径敏感] 对 macro/micro 口径差 ≥5 点的系统 {len(macro_sens)} 个: "
          + ", ".join(f"{r['system']}({r['macro']-r['micro']:+.1f})" for r in macro_sens))
        P("            -> 这些系统的名次取决于聚合口径，不是能力差。")

    # ---- 4. 配对 bootstrap（口径必须与 [3] 的点估计一致 = macro）
    P(f"\n[4] 配对 bootstrap（{args.n_boot} 次重采样，按 case 整簇重采样；"
      f"点估计与 CI 同为 macro 口径）")
    cases = np.unique(np.concatenate([r["case"] for r in rows]))
    case_index = {c: i for i, c in enumerate(cases)}
    # 切片轴必须取**全库唯一**值，所有 system 共用同一套行号 ——
    # 否则两个 system 的第 k 行不是同一件事，差值无从谈起。
    # （踩过的坑：用 factorize(...)[0].size 当行数拿到的是 item 数 1524 而非
    #   slice 数 4，矩阵变成 1524×705，1520 个全 NaN 行被 boot_macro 补成 0，
    #   CI 塌缩成 0.01 点宽且整体偏正。）
    slice_levels = list(np.unique(np.concatenate([r["slice"] for r in rows])))
    slice_index = {s: i for i, s in enumerate(slice_levels)}

    # 聚合口径必须**逐字复刻** macro_micro()：slice 内按 item 等权，
    # 再对 slice 等权平均。而不是「slice 内先按 case 求均值」——
    # 两者在「同一 case 的 item 数」不等时不同。问句档各系统 item 数不同
    # （12080~13836，case 数都是 705），按 case 均值会把点估计挤到 CI 之外
    # （实测 haiku Δ=-12.61 配 [-11.99,-11.17]）。
    # 正确做法：按 (slice, case) 存**命中和**与**条数**，重采样时按 case 的
    # 重数加权 —— num/den = sum(h*w)/sum(w)，w 全 1 时逐字等于点估计。
    def slice_case_cells(r):
        tmp = pd.DataFrame({"s": np.asarray(r["slice"]),
                            "c": np.asarray(r["case"]),
                            "h": np.asarray(r["hit"], dtype=float)})
        g = tmp.groupby(["s", "c"], sort=True)["h"].agg(["sum", "count"])
        S = np.zeros((len(slice_levels), len(cases)))
        N = np.zeros((len(slice_levels), len(cases)))
        for (sname, cname), row in g.iterrows():
            si, ci = slice_index[sname], case_index[cname]
            S[si, ci], N[si, ci] = float(row["sum"]), float(row["count"])
        return S, N

    mats = {r["system"]: slice_case_cells(r) for r in rows}
    rng = np.random.default_rng(20261001)
    boot_idx = rng.integers(0, len(cases), size=(args.n_boot, len(cases)))

    def boot_macro(S: np.ndarray, N: np.ndarray) -> np.ndarray:
        """按 case 整簇重采样后重算 macro。

        缺 case 的处理（踩过的坑）：某 system 只覆盖部分 case 时，一次重采样
        可能一个 case 都没抽中 -> 该 system 这一轮**无定义**（全 NaN）。
        这不是数值噪声，是这一轮算不出值，**不能**补 0（补 0 会把「没测到」
        写成「测了全错」，真数据上表现为 Δ=0.00 配 CI=[+nan,+nan]）。
        正确做法是这一轮标为无效，配对比较时把「任一方无效」的轮次整轮剔除，
        并把剔除比例报出来 —— 剔除比例过高说明 case 数太少、CI 本身不可信。
        """
        # W[b, c] = 第 b 次抽样抽到 case c 的次数
        W = np.zeros((args.n_boot, len(cases)), dtype=float)
        np.add.at(W, (np.repeat(np.arange(args.n_boot), len(cases)), boot_idx.ravel()), 1.0)
        # (n_slice, n_case) @ (n_case, n_boot) -> (n_slice, n_boot)
        num = S @ W.T
        den = N @ W.T
        sl_mean = np.divide(num, den, out=np.full_like(num, np.nan), where=den > 0)
        with np.errstate(invalid="ignore"):
            valid = np.isfinite(sl_mean).any(axis=0)   # (n_boot,)
            out = np.full(args.n_boot, np.nan, dtype=float)
            if valid.any():
                out[valid] = np.nanmean(sl_mean[:, valid], axis=0)
        return out

    # 自洽性前置检查：w 全 1（即不重采样）时 bootstrap 口径必须逐字等于 [3] 的点估计。
    # 不等就说明聚合公式又和 macro_micro 分叉了，后面的 CI 一律不可信。
    ones = np.ones((1, len(cases)), dtype=float)
    for r in rows:
        S, N = mats[r["system"]]
        num0, den0 = S @ ones.T, N @ ones.T
        m0 = float(np.nanmean(np.divide(num0, den0,
                                        out=np.full_like(num0, np.nan), where=den0 > 0)))
        if abs(m0 * 100.0 - r["macro"]) > 0.005:
            P(f"  [WARN] {short_name(r['system'])}: 聚合口径与点估计不一致"
              f"（口径自校验={m0*100.0:.2f}% vs 点估计={r['macro']:.2f}%）")
    bm = {r["system"]: boot_macro(*mats[r["system"]]) for r in rows}
    P(f"  {'对比':<50}{'Δmacro':>9}{'95%CI(点)':>20}{'McNemar p':>12}")
    sig_vs_top = []
    for r in rows[1:]:
        raw = (bm[r["system"]] - bm[top["system"]]) * 100.0   # 分数 -> 百分点
        # 配对比较必须用**同一批**重采样轮次：任一方该轮无定义就整轮剔除，
        # 否则两串不同轮次相减会把「无定义」当成 0，凭空造出 ±宽度。
        paired = raw[np.isfinite(raw)]
        n_drop = int(raw.size - paired.size)
        if paired.size == 0:
            P(f"  {short_name(r['system']):<40} 无有效重采样轮次，无法给 CI"
              f"（{n_drop}/{raw.size} 轮无定义）")
            sig_vs_top.append((r["system"], False, r["macro"] - top["macro"],
                               float("nan"), float("nan"), float("nan")))
            continue
        d = paired
        lo, hi = np.percentile(d, [2.5, 97.5])
        extra = (f"  [丢弃 {n_drop}/{raw.size} 轮无定义重采样]" if n_drop else "")
        if n_drop and n_drop > 0.5 * raw.size:
            P(f"  [WARN] {short_name(r['system'])}: {n_drop}/{raw.size} 轮重采样无定义"
              f"（该系统只覆盖少数 case），CI 不可信。")
        # McNemar 是**配对**检验，必须按 item_id 对齐，不能按数组下标 ——
        # 问句档各系统的条目数并不相同（实测 13062 vs 13007），
        # 按下标对齐会把不同的题配成一对，p 值变成噪声。
        ids_r = r.get("item_id")
        ids_t = top.get("item_id")
        if ids_r is not None and ids_t is not None:
            tmp_r = pd.DataFrame({"i": np.asarray(ids_r), "h": np.asarray(r["hit"], float)})
            tmp_t = pd.DataFrame({"i": np.asarray(ids_t), "h": np.asarray(top["hit"], float)})
            j = tmp_r.merge(tmp_t, on="i", suffixes=("_r", "_t"))
            M1, M2 = j["h_r"].to_numpy(), j["h_t"].to_numpy()
        else:
            M1, M2 = np.asarray(r["hit"], float), np.asarray(top["hit"], float)
        b = int(np.sum((M1 == 1) & (M2 == 0)))
        c_ = int(np.sum((M1 == 0) & (M2 == 1)))
        p = mcnemar_exact(b, c_)
        tie = (lo <= 0 <= hi) if np.isfinite(lo) and np.isfinite(hi) else True
        sig_vs_top.append((r["system"], not tie, r["macro"] - top["macro"], lo, hi, p))
        P(f"  {short_name(r['system']+' vs '+top['system']):<50}{r['macro']-top['macro']:>9.2f}"
          f"{f'[{lo:+.2f},{hi:+.2f}]':>20}{p:>12.4f}{'   平局' if tie else '   显著'}{extra}")
    # 自洽性守卫：点估计必须落在自己的 CI 内，不在就是聚合口径错了
    for name, _, delta, lo, hi, _p in sig_vs_top:
        if np.isfinite(lo) and np.isfinite(hi) and not (lo - 0.51 <= delta <= hi + 0.51):
            P(f"  [WARN] {name}: Δ={delta:+.2f} 落在 95%CI [{lo:+.2f},{hi:+.2f}] 之外，"
              f"点估计与 CI 口径不一致，结果不可用。")
    n_tie = sum(1 for x in sig_vs_top if not x[1])
    P(f"  => 对榜首 {n_tie}/{len(sig_vs_top)} 组是统计平局"
      f"（{len(sig_vs_top)-n_tie} 组可区分）")

    # ---- 4b. margin 的 CI（榜首 − 地板）
    #
    # 为什么必须单独做：[4] 的配对 bootstrap 只比较**系统彼此**，从来不给
    # margin 自己的区间。可 margin 的符号决定判决 —— READABLE/MARGINAL/UNREADABLE
    # 的分界就在它过不过 0 —— 而判决段自己写着「只报榜首名次、不报 CI 是误导」。
    # 少这一段，判决就建立在一个没有不确定度的点估计上。
    #
    # 两侧必须用**同一批**重采样轮次：地板是若干生成器 c^- 的 max，榜首是单个
    # system 的 macro，各自重采再相减会把两串不同轮次的抽样噪声算进去。
    # 地板那侧同样先聚成 (slice, case) 的命中和/条数，与 slice_case_cells 同口径。
    margin_ci = None
    if args.loo and floor_u_rows and loo_domain:
        P(f"\n[4b] margin 的配对 bootstrap（{args.n_boot} 次，与 [4] 同一批 case 抽样）")
        top_cell = slice_case_cells(top)

        def cells_from_triple(trip):
            tmp = pd.DataFrame({"s": np.asarray(trip["slice"]),
                                "c": np.asarray(trip["case"]),
                                "h": np.asarray(trip["hit"], dtype=float)})
            g = tmp.groupby(["s", "c"], sort=True)["h"].agg(["sum", "count"])
            S = np.zeros((len(slice_levels), len(cases)))
            N = np.zeros_like(S)
            for (sname, cname), row in g.iterrows():
                if sname in slice_index and cname in case_index:
                    S[slice_index[sname], case_index[cname]] = float(row["sum"])
                    N[slice_index[sname], case_index[cname]] = float(row["count"])
            return S, N

        floor_mats = {j: cells_from_triple(tr) for j, tr in floor_u_rows.items()}
        boot_floor = {j: boot_macro(*m) for j, m in floor_mats.items()}
        btop = boot_macro(*top_cell)
        # 判决取 max over generators，所以每一轮也要先对生成器取 max 再相减。
        # （若改成对每个生成器各给一条 margin，读者会以为存在 m 个并列判决，
        #   而 eq:loo 只承认那一个。）
        stack = np.vstack([boot_floor[j] for j in sorted(floor_mats)])   # (m, n_boot)
        with np.errstate(invalid="ignore"):
            per_boot_floor = np.nanmax(stack, axis=0)
        margin_b = (btop - per_boot_floor) * 100.0
        ok_b = np.isfinite(margin_b)
        if ok_b.any():
            mb = margin_b[ok_b]
            lo_m, hi_m = np.percentile(mb, [2.5, 97.5])
            n_drop_b = int(margin_b.size - mb.size)
            crosses0 = bool(lo_m <= 0 <= hi_m)
            margin_ci = {
                "lo95": round(float(lo_m), 4), "hi95": round(float(hi_m), 4),
                "n_valid_rounds": int(mb.size), "n_dropped_rounds": n_drop_b,
                "crosses_zero": crosses0,
                "n_boot": int(args.n_boot), "seed": 20261001,
                "unit": "points",
            }
            P(f"  margin 点估计 = {top['macro'] - ceiling:+.2f} 点"
              f"   95%CI = [{lo_m:+.2f}, {hi_m:+.2f}]")
            if n_drop_b:
                P(f"  [丢弃 {n_drop_b}/{margin_b.size} 轮无定义重采样]")
            if crosses0:
                P(f"  => CI 跨 0：'榜首越过地板' 这一结论在这套抽样下并不稳健，"
                  f"判决应按可下结论的**下界**（{lo_m:+.2f} 点）解读，而不是点估计。")
        else:
            P("  [WARN] margin 无有效重采样轮次，无法给 CI。")

    # ---- 5. 结论
    P("\n[5] 结论")

    # 判决守卫：m<3 时 c^- 退化成「另一个生成器的答案」，量到的是生成器之间的
    # 一致率，不是 c 的自复现率。在 m=2 上按一致率给 READABLE/UNREADABLE，等于
    # 拿「两个 judge 恰好同意得够多/不够多」冒充「榜首能否被这把尺子读出来」。
    # 实测两个 judge 在 m=2 下 loo_macro 逐位相同，max_over_generators 也是空转，
    # 所以这个量连「每个生成器各自的地板」都不是。故此处 fail-closed。
    loo_degenerate_for_verdict = (loo_maps is not None
                                  and len(gold.judges) < MIN_LOO_GENERATORS)

    # 同域闸：floor 与榜单的**实计分题集**必须是同一个集合，否则 [5] 的 margin 是
    # 两个分母相减。此前只把 loo_domain 的长度写进 leaderboard_domain_size，
    # 于是平票口径 unmeasured 下 JSON 报「榜单域 = 1520」而榜首行 n=1084，
    # 论文 §3.1 自己立的同分母纪律在自己的上报字段上被打破。这里按实计分数
    # 判，不按候选题域判 —— 候选域里那些没有金标的题本来就进不了任何分子。
    lb_scored_uniform = len({r["n"] for r in rows}) == 1
    lb_scored = int(rows[0]["n"]) if rows else 0
    floor_domain_n = len(loo_domain) if loo_domain else len(gold_map)
    # 2026-10-10 加固：判据从「计数相等」换成「成员相等」。
    # 计数判据是弱一档的实现 —— 榜首在一批题上得分、地板在另一批**同样多**的题上
    # 算出来时，计数判会放行，而 margin 仍然是两个分母相减。论文把这条写成
    # 「必须测在同一批题上」（集合语义），仪器就得真的按集合判。
    # 可达性（2026-10-11 现读 [2] 段：`sub_u = sub[sub["item_id"].isin(loo_domain)]`）：
    # 每个 system 的实计分集都先被限制进 U，所以 scored_set ⊆ U，于是
    # 「大小相等」在这条路径上蕴含「成员相等」—— 两判据对**任何**现有路径的输入
    # 都同结论（不止本线四份运行）。成员判据买到的是：那道 `.isin(loo_domain)`
    # 哪天被去掉，闸仍然拦得住。这条可达性就是变异体 M27（把判据退回计数比较）
    # 在端到端套件上不可能被抓到的原因 —— 它是结构等价体，不是没写完的测试；
    # 判它的方法在 tests/test_revision_round4.py 的单元断言里（直接喂 rows）。
    _floor_set = set(loo_domain) if loo_domain else set(gold_map)
    domain_membership_equal = domain_membership_ok(rows, _floor_set)
    # 哪些 system 不在地板题集上：成员判据为假时必须点名，否则报告里会出现
    # 「榜首题集摘要 == 地板题集摘要」而 `domain_membership_equal` 为假这种
    # 自相矛盾的上报（榜首同域、别的 system 不同域时就会撞上）。
    off_domain_systems = [r["system"] for r in rows if set(r.get("scored_set") or set()) != _floor_set]
    not_same_domain = bool(loo_domain) and not domain_membership_equal

    if not_same_domain:
        verdict = "UNDECIDABLE_DOMAIN_MISMATCH"
        P("  VERDICT = UNDECIDABLE_DOMAIN_MISMATCH")
        P(f"    地板在 {floor_domain_n} 题上算，榜首在 {lb_scored} 题上算："
          "两者不是同一个分母，margin 无意义。")
        # 诊断跨**所有**行聚合，不看榜首一行：只看 rows[0] 会印出「仅榜首有 0 题、
        # 仅地板有 0 题」这种自相矛盾的话（榜首恰好同域，而另一个系统不同域）。
        # 2026-10-11 删掉了此处一句「计数相同而成员不同」的括注：它的触发条件要求
        # 所有行大小都等于 |U| 而成员不同，而 scored_set ⊆ U（见上面可达性注），
        # 所以那一支构造上不可达；留着会让下一轮又花时间去证明它为什么永不出现。
        _only_lb: set = set(); _only_fl: set = set()
        for r in rows:
            _ss = set(r.get("scored_set") or set())
            _only_lb |= (_ss - _floor_set)
            _only_fl |= (_floor_set - _ss)
        if _only_lb or _only_fl:
            P(f"    成员差异：仅榜单侧有 {len(_only_lb)} 题、仅地板侧有 {len(_only_fl)} 题")
        if off_domain_systems:
            P(f"    不在地板题集上的 system：{'、'.join(off_domain_systems)}"
              "（判据是题集成员相等，不是题数相等）")
        if not lb_scored_uniform:
            P(f"    且各 system 的计分题数不一致（{sorted({r['n'] for r in rows})}）"
              " —— 连榜单内部都不是同一个分母。")
        P("    请改用 --tie-rule 让两种口径的分母一致，或在论文里同时报出两侧分母。")
    elif loo_degenerate_for_verdict:
        verdict = "UNDECIDABLE_FLOOR_DEGENERATE"
        P("  VERDICT = UNDECIDABLE_FLOOR_DEGENERATE")
        P(f"    留一法地板在 m={len(gold.judges)} < {MIN_LOO_GENERATORS} 个生成器下退化："
          "剔除生成器 g 自己那一票后只剩另一个生成器，量到的是生成器之间的**一致率**，"
          "不是金标生成过程的自复现率。")
        P(f"    该地板 = {ceiling_loo:.2f}%（各生成器同值，max 规则空转）；榜首 "
          f"{top['macro']:.2f}%，点差 {top['macro'] - ceiling_loo:+.2f} 点。")
        P("    我们不在这个量上判 READABLE / UNREADABLE / MARGINAL：一致率高只说明"
          "两个生成器彼此投合，不说明榜首是否强于生成该金标的过程。"
          f"要判决需至少 {MIN_LOO_GENERATORS} 个生成器。")
        if margin_ci:
            P(f"    供参考（不作判决依据）：margin 95%CI = "
              f"[{margin_ci['lo95']:+.2f}, {margin_ci['hi95']:+.2f}]")
    elif (ceiling is None or not np.isfinite(ceiling)
          or top["macro"] is None or not np.isfinite(top["macro"])):
        # 地板没量到就**不许**顺着 if/elif 的 else 掉进 READABLE。
        # 10-12 实测：顶票并列的题被剔出金标后，公共留一题域只剩没有金标的行，
        # ceiling 变成 nan；`nan > x` 与 `x - nan < 2.0` 都是 False，
        # 于是旧代码打印 "VERDICT = READABLE（榜首超出下限 nan 点）" ——
        # 一个"什么都没测到"的运行在判决链末端长得像最好的那一档。
        verdict = "UNDECIDABLE_NO_READING"
        P("  VERDICT = UNDECIDABLE_NO_READING")
        # 两侧都必须有读数。10-12 实测这条臂最初只挡了地板一侧：
        # 夹具 floor_nan.csv 里地板是 0.00%（由 n=1 的单票支撑算出）、榜首是 nan，
        # `nan > x` 与 `x - nan < 2.0` 双双为 False，旧代码照样打印
        # "VERDICT = READABLE（榜首超出下限 nan 点）"。
        P(f"    地板 = {ceiling}，榜首 = {top['macro']}：两侧任一不是数，"
          "就不是『跨过了下限』也不是『没跨过』，而是这把尺子本次没有读数。"
          "常见成因：顶票并列的题按 unmeasured 全部不进金标，剩下的题不足以定义 c^-，"
          "或系统行全部落在无金标题上（覆盖 0 行）。")
    elif ceiling > top["macro"] + 1e-9:
        verdict = "UNREADABLE"
        P("  VERDICT = UNREADABLE")
        P(f"    噪声下限 {ceiling:.2f}% > 榜首 {top['macro']:.2f}%（差 {ceiling-top['macro']:.2f} 点）")
        P("    这把尺子量不出榜首系统的能力：金标由 judge 自己参与生成，"
          "judge 对这把金标的复现率就高于所有参赛系统的得分，"
          "因此分数高低首先反映「与金标生成方的对齐程度」，不是能力。")
        if n_tie < len(sig_vs_top):
            P(f"    注意别把两件事混为一谈：[4] 的 case 抽样波动仍能区分 {len(sig_vs_top)-n_tie}"
              f"/{len(sig_vs_top)} 组，但那只是「在这把有偏金标上彼此可分」，"
              "不能当成能力差 —— 分母本身不可信。")
    elif top["macro"] - ceiling <= 1e-9:
        # 「等于地板」不是勉强越过地板。2026-10-12 修：判平票按顶票唯一持有者算之后，
        # m=25 四档的地板精确落在榜首自己身上（最好的那个生成器剔掉自己一票后
        # 金标几乎不变 ⇒ 它的留一自复现 = 它的榜面分），于是 max-over-generators
        # 的下限就等于榜首。旧链里 `ceiling > top + 1e-9` 为假就一路掉进
        # `top - ceiling < 2.0` ⇒ 打印 MARGINAL，而 §4 写的规则是严格不等式
        # max_s acc_c(s) > floor_c + δ：margin=0 连"越过"都没发生。
        verdict = "UNREADABLE"
        P("  VERDICT = UNREADABLE")
        P(f"    榜首 {top['macro']:.4f}% 与噪声下限 {ceiling:.4f}% 相等（差 {top['macro']-ceiling:+.2e} 点）："
          "严格判据 max_s acc > floor + δ 没有被越过哪怕一点点。")
        P(f"    结构性成因：榜首本身就是参与造金标的 {len(gold.judges)} 个生成器之一，"
          f"剔掉它那一票后其余 {len(gold.judges) - 1} 票的顶票常常不变 ⇒ 它的留一自复现"
          "就是它的榜面分，于是『必须跨过所有生成器中最高那个下限』在这类语料上"
          "等于『跨过自己』。")
    elif top["macro"] - ceiling < 2.0:
        verdict = "MARGINAL"
        P("  VERDICT = MARGINAL")
        P(f"    噪声下限 {ceiling:.2f}% 距榜首 {top['macro']:.2f}% 仅 {top['macro']-ceiling:.2f} 点")
        P("    榜首勉强越过下限，但它与下限之间的余量小于常规波动；只报榜首名次、不报 CI 是误导。")
    else:
        verdict = "READABLE"
        P(f"  VERDICT = READABLE（榜首超出下限 {top['macro']-ceiling:.2f} 点）")
        if margin_ci and margin_ci["crosses_zero"]:
            P(f"    但 margin 的 95%CI [{margin_ci['lo95']:+.2f}, {margin_ci['hi95']:+.2f}]"
              " 跨 0：点估计为正不等于'榜首确实越过地板'稳健成立。")
        P("    注意：这只说明榜首没被这把尺子挡住，仍须报 CI、macro/micro 两口径、"
          "以及与第二名的配对检验。")
    if spread_macro < 5.0:
        P(f"  [附] 全榜跨度仅 {spread_macro:.2f} 点，且 {n_tie}/{len(sig_vs_top)} 组对榜首平局"
          f" -> 报『第 N 名』不如报『与榜首不可区分的一组』。")

    # ---- 6. 校准
    cal = {}
    if have_prob:
        P("\n[6] 校准（system 自报概率 vs 是否命中金标）")
        for r in rows:
            sub = sdf[sdf["actor"] == r["system"]]
            hit = agreement(sub, gold_map)
            pr = sub["answer_prob"].to_numpy(dtype=float)
            m = np.isfinite(pr)
            if not m.any():
                continue
            c = calibration(pr[m], np.asarray(hit, dtype=float)[m], args.bins)
            if c["n"] == 0:
                continue
            cal[r["system"]] = c
            direction = "高估" if c["mean_conf"] > c["acc"] else "低估"
            P(f"  {short_name(r['system']):<40} ECE={c['ECE']:.4f}  Brier={c['Brier']:.4f}  "
              f"conf={c['mean_conf']:.4f} vs acc={c['acc']:.4f}  ({direction}, n={c['n']})")
        if not cal:
            P("  [WARN] system 行没有可用的 answer_prob。")

    out = {
        "gold_method": method,
        "n_items": int(df["item_id"].nunique()),
        "judges": gold.judges,
        "ceiling_inclusive_macro": round(ceiling_incl, 4),
        "ceiling_inclusive_macro_min": round(min(incl), 4),
        "ceiling_loo_macro": (round(ceiling_loo, 4) if ceiling_loo is not None else None),
        "ceiling_loo_macro_min": (round(min(loo_v), 4) if loo_v else None),
        # max 是判决用的数（论文 §Threat Model：a leader must clear all of them），
        # min 只是敏感性分析的对照。旧代码两者都取 min，等于把「最容易跨过的那个
        # 生成器」当门槛，方向与论文相反。
        "ceiling_rule": "max_over_generators",
        "floor_basis": ("judge_gold_leave_one_out" if ceiling_loo is not None
                        else "judge_gold_inclusive"),
        # 平票口径与规模。平票题的「金标」在 unmeasured 下根本不存在，所以地板和
        # 榜单的分母都比语料总题数小；不给这两个字段，下游会把缩小后的分母
        # 误当成「金标覆盖率 100%」。
        "gold_tie_rule": gold.tie_rule,
        "gold_tie_items": len(gold.tie_items),
        # 加权口径的浮点恰等题数：判据本身仍是"顶票按 (值, 标签) 取 max"，
        # 也就是这些题的金标由标签顺序落定。这一口径在正文里已被降级
        # （m=2 时它是符号裁决，不是判官准确率），所以这里**只登记不改判**，
        # 但"没量过"不能继续成立 —— 实测 jev_votes_question 有 19 题。
        "gold_mean_prob_tie_items": len(getattr(gold, "mean_prob_ties", {}) or {}),
        "gold_tie_fraction_of_items": (
            round(len(gold.tie_items) / max(1, int(df["item_id"].nunique())), 6)
        ),
        # floor 与 leaderboard 的公共题域大小：两者必须相等才可比。
        "loo_domain_size": (len(loo_domain) if loo_domain else None),
        "leaderboard_domain_size": (len(loo_domain) if loo_domain
                                    else int(df["item_id"].nunique())),
        # 上一个字段是**候选**题域（lb_domain 过滤后的 item 数），不是**实计分**数。
        # 两者只有在每个 system 的每个 item 都有金标时才相等；平票口径为
        # unmeasured 时 loo_domain 里仍有 436 道无金标的平票题，于是
        # leaderboard_domain_size=1520 而榜首行 n=1084 —— 同一份 JSON 里
        # 两个数字互相矛盾，论文「同分母」纪律被自己的上报字段破坏。
        # 这三个字段必须一起读：
        #   leaderboard_candidate_items  过滤后进入榜单的题数
        #   leaderboard_scored_items     榜首（=全部 system 共有的）实计分题数
        #   same_domain_as_floor         两者是否真同域；False 时判决不可比
        "leaderboard_candidate_items": (
            len(lb_domain) if loo_domain else int(df["item_id"].nunique())),
        "leaderboard_scored_items": int(rows[0]["n"]) if rows else 0,
        "leaderboard_scored_items_uniform": len(
            {r["n"] for r in rows}) == 1 if rows else True,
        "same_domain_as_floor": domain_membership_equal,
        # 旧字段沿用旧语义（计数判据），这样「加固前后结论是否一致」是可查的，
        # 而不是被新语义悄悄覆盖：两者不等即说明存在「同大小不同成员」的分母。
        "same_domain_as_floor_by_count": (
            bool(loo_domain) and len(rows) > 0
            and all(r["n"] == len(loo_domain) for r in rows)),
        "domain_membership_equal": domain_membership_equal,
        # 为假时点名是哪几行不在地板题集上 —— 只有摘要会把「榜首同域、另一行不同域」
        # 报成自相矛盾的两个数。
        "domain_membership_off_systems": list(off_domain_systems),
        "floor_domain_digest": _digest(_floor_set),
        # 榜首（rows[0]）那一行的实计分集摘要；各 system 的摘要一起给出，
        # 这样 `domain_membership_equal` 为假时读者能看出差在谁身上。
        "leaderboard_scored_digest": _digest(rows[0].get("scored_set") or set()) if rows else "",
        "scored_digest_by_system": {
            r["system"]: _digest(r.get("scored_set") or set()) for r in rows},
        # m=2 时 c^- 退化成「另一个生成器的答案」：这个量是生成器之间的一致率，
        # 不是 c 的自复现率。数值可用，解释不同 —— 必须让下游能读到这件事。
        "loo_generators": len(gold.judges),
        # m=2 时两个 judge 的真 LOO 必然相等：命中集都是「两 judge 都投了非空且一致」
        # 的题集合，与是谁无关。这是构造决定的恒等式，不是巧合，因此 loo_per_generator
        # 在 m=2 下刻意**不**给 min/max 两个值 —— 给出会让人误以为存在可区分的两个下限。
        "loo_measure": (LOO_LABEL_SELF if len(gold.judges) >= MIN_LOO_GENERATORS
                        else LOO_LABEL_DEGENERATE),
        "loo_min_generators_for_self_reproduction": MIN_LOO_GENERATORS,
        "loo_degenerate_identical_across_generators": len(gold.judges) == 2,
        # 原始精度那几列只在内存里用于判决，不进载体：载体的字段表要被
        # make_m25_summary / 台账 field 绑定按名寻址，多一排 `_` 前缀会让下一位
        # 以为它们是可引用的读数。
        "floor_per_generator": [{k: v for k, v in r.items() if not k.startswith("_")}
                                for r in floor_rows],
        "judge_macro_gap": round(max(incl) - min(incl), 4),
        # 金标覆盖率：系统作答里有多少行所在 item 真的有金标。没被计分的行
        # 是「没测到」，不是「全错」，所以这个数是分母的定义，不能只藏在日志里。
        "gold_coverage": _gold_coverage(df, sdf, gold_map),
        "leaderboard": [
            {"system": r["system"], "macro": round(r["macro"], 4),
             "micro": round(r["micro"], 4), "n": r["n"],
             "n_rows": r["n_rows"], "n_items_unscored": r["n_items_unscored"]}
            for r in rows
        ],
        "ties_vs_top": n_tie,
        "compared": len(sig_vs_top),
        "verdict": verdict,
        "margin_vs_floor": round(top["macro"] - ceiling, 4),
        "margin_ci": margin_ci,
        "calibration": cal,
    }
    # --json 必须在 main 里落盘，否则 argparse 声明了这个开关却什么都不写——
    # 调用方（门禁）会一直读到「文件不存在」而永远 SKIP，门形同虚设。
    if getattr(args, "json", None):
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, ensure_ascii=False)
        P(f"\n[JSON] -> {args.json}")
    return out


if __name__ == "__main__":
    raise SystemExit(main())