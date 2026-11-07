#!/usr/bin/env python3
"""把 JudgeSense 的「25 个判官 × 4 任务」拼成 m≥3 的模型金标长表。

为什么要有这个脚本（2026-10-12，三方独立评审的 C1）：
评审三人各自提出同一件事——留一地板从未在它为之成立的 **m ≥ 3** 区间上跑过真实语料，
现稿里唯一的非拒绝判决是合成自测（§6 的 case 8）。这条不是措辞能解决的：
要么补一支真语料的 m≥3 判决，要么把标题/摘要/结论收窄。

盘上其实已经有这支语料，只是**从没按这个口径用过**：
`examples/judgesense_<task>.csv` 是 role=system 的 25 个判官榜单，
`examples/judgesense_<task>_judges.csv` 是同一批 25 个 actor 的 role=judge 投票。
现稿 §5.4 用 `--gold-file`（人工外部金标）跑它 ⇒ 金标不是模型产的 ⇒ 留一地板无定义，
只能报「弃权」。而**把金标改成这 25 个模型自己的多数投票**（`--gold majority`），
m 就从 2 跳到 25：地板第一次成为真正的「金标生成过程的自复现率」。
（2026-10-15 更正第二轮评审 R2-M1：这里原来写的「δ=2.0 也第一次有东西可比」是错的。
在金标由被排名的这批模型自己产出、且两侧同域的构造上，floor 恒等于榜首，
margin ≡ 0 是恒等式而不是读数，δ 在这一档**永远不会**bind —— 见正文 §4 Proposition 4。）

合成的表是逐字拼接，不做任何改写：judge 行进金标构造，system 行进榜单。
两者的 actor 集合**本来就相同**（25/25），这正是本论文标题所指的情形
（"they could compete in the ranking they defined"），也是 §8 第 2 条局限
（自评让地板偏乐观）必须随结果一起披露的原因。

用法：
    python3 make_m25_votes.py --out-dir /tmp/m25 [--task factuality]
打印每张表的 sha256 与行/actor/item 计数；这些数会进日志，
好让「判决来自哪份字节」可接回（本线 10-11 为这件事写过两条纪律）。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = ("factuality", "coherence", "relevance", "preference")


def build(task: str, out_dir: str, examples: str) -> dict:
    """judges(role=judge) + systems(role=system) 逐字拼接，返回这张表的读数。"""
    sys_p = os.path.join(examples, f"judgesense_{task}.csv")
    jd_p = os.path.join(examples, f"judgesense_{task}_judges.csv")
    for p in (sys_p, jd_p):
        if not os.path.exists(p):
            raise SystemExit(f"FATAL 缺输入文件：{p}")
    s = pd.read_csv(sys_p, dtype=str)
    j = pd.read_csv(jd_p, dtype=str)
    if set(s.columns) != set(j.columns):
        raise SystemExit(f"FATAL {task} 两张表的列不一致：{list(s.columns)} vs {list(j.columns)}")
    # 前提必须为真，否则这份构造就不是「25 个模型自己造金标、自己上榜」
    if set(j["role"]) != {"judge"} or set(s["role"]) != {"system"}:
        raise SystemExit(f"FATAL {task} 的 role 不是预期的单角色表："
                         f"judge 表 {sorted(set(j['role']))} / system 表 {sorted(set(s['role']))}")
    if set(j["actor"]) != set(s["actor"]):
        raise SystemExit(f"FATAL {task} 的金标生成方与榜单参赛者不是同一批 actor："
                         f"仅 judge {sorted(set(j['actor']) - set(s['actor']))[:3]} / "
                         f"仅 system {sorted(set(s['actor']) - set(j['actor']))[:3]}")
    # Proposition 4 的第三条前提：某个 actor 在这一题上的**选票**就是它自己对这一题的
    # **答案**。这条不成立时「留一自复现 = 它的榜面分」就不是恒等式而是巧合，而 §4 把它
    # 写成了「构造保证」——所以构造这一步必须拒绝写出不满足它的表，而不是让正文去相信。
    # 2026-10-15 加：此前这里只比 actor 集合，那句话没有闸门兜着。
    dup_j = int(j.duplicated(subset=["actor", "item_id"]).sum())
    dup_s = int(s.duplicated(subset=["actor", "item_id"]).sum())
    if dup_j or dup_s:
        raise SystemExit(f"FATAL {task} 的 (actor,item_id) 不唯一（judge {dup_j} / system {dup_s} 行重复），"
                         "选票与答案无法一一配对，前提不可判")
    p = j[["actor", "item_id", "answer"]].merge(
        s[["actor", "item_id", "answer"]], on=["actor", "item_id"], suffixes=("_ballot", "_answer"))
    if p.empty:
        raise SystemExit(f"FATAL {task} 的选票表与答案表没有任何 (actor,item_id) 交集，前提不可判")
    diff = p.loc[p.answer_ballot != p.answer_answer]
    if len(diff):
        head = diff.head(3).to_dict("records")
        raise SystemExit(f"FATAL {task}: {len(diff)}/{len(p)} 对的选票与该 actor 自己的答案不同 "
                         f"（样例 {head}）。这不是「金标由被排名的模型产出」那一档构造，"
                         "§4 Proposition 4 的前提不成立，拒写拼接表")
    m = pd.concat([j, s], ignore_index=True)[list(s.columns)]
    out = os.path.join(out_dir, f"judgesense_{task}_m25.csv")
    m.to_csv(out, index=False)
    return {
        "task": task,
        "path": out,
        "sha256": hashlib.sha256(open(out, "rb").read()).hexdigest(),
        "rows": int(len(m)),
        "rows_judge": int(len(j)),
        "rows_system": int(len(s)),
        "n_generators": int(m.loc[m["role"] == "judge", "actor"].nunique()),
        "n_systems": int(m.loc[m["role"] == "system", "actor"].nunique()),
        "n_items": int(m["item_id"].nunique()),
        "self_grading_overlap": int(len(set(j["actor"]) & set(s["actor"]))),
        # Proposition 4 前提的回执：配了对的 (actor,item) 全部逐字相同才走到这里。
        "ballot_answer_pairs": int(len(p)),
        "ballot_equals_answer_pairs": int(len(p) - len(diff)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True,
                    help="拼接表写到哪（建议 scratch；这份表是派生物，不进库）")
    ap.add_argument("--examples", default=os.path.join(HERE, "examples"))
    ap.add_argument("--task", default="all", choices=("all",) + TASKS)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    tasks = TASKS if args.task == "all" else (args.task,)
    print(f"# make_m25_votes.py -> {args.out_dir}")
    for t in tasks:
        r = build(t, args.out_dir, args.examples)
        print(f"  {t:11s} rows={r['rows']:6d} (judge {r['rows_judge']} + system {r['rows_system']}) "
              f"generators={r['n_generators']} items={r['n_items']} "
              f"overlap={r['self_grading_overlap']}/{r['n_systems']} "
              f"ballot==answer {r['ballot_equals_answer_pairs']}/{r['ballot_answer_pairs']} "
              f"sha256={r['sha256'][:16]}")
    print("# 说明：judge 表与 system 表的 actor 集合相同 ⇒ 金标由被排名的这批模型自己产出，"
          "地板是它们的自复现率；§8 第 2 条（自评让地板偏乐观）必须随结果披露。")
    print("# ballot==answer 是 §4 Proposition 4 的第三条前提（每个 actor 的选票就是它自己的答案），"
          "build() 里不满足即 FATAL 退出、不写表，所以这一列的分子等于分母不是巧合而是被这一步强制的。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
