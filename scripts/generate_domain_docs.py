#!/usr/bin/env python3
"""从指标目录 CATALOG（唯一事实来源）生成各领域的使用文档。

为 generate_metric_specs.CATALOG 里的每个领域生成 docs/domains/<domain>.zh-CN.md，
这样文档与 examples/metric-spec.json 不会出现口径漂移。

用法：
    python3 scripts/generate_domain_docs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_metric_specs import CATALOG

DOMAIN_NAMES = {
    "health": "健康",
    "finance": "财务",
    "learning": "学习",
    "work": "工作",
    "social": "社交",
    "emotion": "情绪",
    "environment": "环境",
    "energy": "精力",
    "recovery": "恢复",
    "other": "其他",
}

DIRECTION_LABEL = {
    "higher": "越高越好",
    "lower": "越低越好",
    "target": "目标值",
}

# 每个域一句话定位（用于文档头部）
DOMAIN_INTRO = {
    "health": "身体状态、营养摄入、运动与睡眠——可观察、可记录、可打分的健康维度。",
    "finance": "支出、收入、资产与债务——每日记账到月度财务健康，方向感知打分。",
    "learning": "学科、技能、阅读与学习工具——投入与掌握度并行的能力积累维度。",
    "work": "任务、项目、会议与工具——把工作投入与产出都纳入量化。",
    "social": "关系、沟通渠道与社群——连接的质量与数量。",
    "emotion": "情绪状态、压力源与自我意象——主观感受的如实记录。",
    "environment": "空气、居住舒适、通勤与天气——外部条件的量化窗口。",
    "energy": "睡眠阶段、消耗与增益——精力从哪里来、又流向哪里。",
    "recovery": "恢复技巧、恢复指标与休息日——主动恢复的可度量维度。",
    "other": "数字生活、习惯、目标、休闲与消费——不属于上述各域的杂项量化。",
}


def _template_direction(tmpl: tuple) -> str:
    """取出模板的方向字段（模板第 4 个元素）。"""
    return tmpl[3]  # direction


def _member_target(member) -> float | None:
    """成员若是带属性的元组，返回其目标值；否则返回 None。"""
    if isinstance(member, (tuple, list)) and len(member) >= 2 and not isinstance(member[0], (int, float)):
        return member[1]
    return None


def _member_unit(member) -> str | None:
    """成员若是带属性的元组，返回其单位；否则返回 None。"""
    if isinstance(member, (tuple, list)) and len(member) >= 3 and not isinstance(member[0], (int, float)):
        return member[2]
    return None


def _member_direction(member) -> str | None:
    """成员若是带属性的元组，返回其方向；否则返回 None。"""
    if isinstance(member, (tuple, list)) and len(member) >= 4 and not isinstance(member[0], (int, float)):
        return member[3]
    return None


def build_domain_docs() -> dict[str, str]:
    """为每个领域返回 {domain: markdown}。"""
    docs: dict[str, str] = {}
    for domain, categories in CATALOG.items():
        name = DOMAIN_NAMES.get(domain, domain)
        lines: list[str] = []
        lines.append(f"# {name}域（{domain}）量化指南")
        lines.append("")
        lines.append(DOMAIN_INTRO.get(domain, ""))
        lines.append("")
        lines.append("> 本文档由 `scripts/generate_domain_docs.py` 从指标目录同源生成，与 `examples/metric-spec.json` 保持一致。")
        lines.append("")
        lines.append("## 指标总览")
        lines.append("")
        total = 0
        lines.append("| 类别 | 指标数 | 方向 | 单位 |")
        lines.append("|---|---|---|---|")
        for category_name, templates, members in categories:
            n_metrics = len(members) * len(templates)
            total += n_metrics
            # 方向/单位摘要：同一类别可能有多个模板，取首个非空值。
            directions = set()
            units = set()
            for suffix, lo, hi, direction, unit, _t, _w, _tc in templates:
                directions.add(DIRECTION_LABEL.get(direction, direction))
                if unit != "__member_unit__":
                    units.add(unit)
            dir_str = "、".join(sorted(directions))

            # 收集所有非空单位并排序；一个都没有时用破折号占位。
            unit_list = []
            for u in units:
                if u:
                    unit_list.append(u)
            unit_str = "、".join(sorted(unit_list))
            if not unit_str:
                unit_str = "—"
            lines.append(f"| {category_name} | {n_metrics} | {dir_str} | {unit_str} |")
        lines.append(f"| **合计** | **{total}** | | |")
        lines.append("")

        # 每类别一节：说明成员与打分方向
        lines.append("## 类别详解")
        lines.append("")
        for category_name, templates, members in categories:
            lines.append(f"### {category_name}")
            lines.append("")
            # 逐个模板生成一句说明文字。
            tmpl_desc = []
            for suffix, lo, hi, direction, unit, _t, _w, tc in templates:
                unit_disp = unit
                if unit == "__member_unit__":
                    unit_disp = "(成员级单位)"
                tmpl_desc.append(f"`{suffix}`：范围 {lo}–{hi}{unit_disp}，{DIRECTION_LABEL.get(direction, direction)}，建议 {tc} 次/窗口")
            lines.append("维度模板：" + "；".join(tmpl_desc) + "。")
            lines.append("")
            # 成员表格
            lines.append("| 成员 | 方向 | 单位 | 目标 |")
            lines.append("|---|---|---|---|")
            for member in members:
                m_name = member
                if isinstance(member, (tuple, list)):
                    m_name = member[0]
                m_target = _member_target(member)
                m_unit = _member_unit(member)
                m_dir = _member_direction(member)
                # 决定该成员的方向与单位（按首个模板推断）
                eff_dir = m_dir
                eff_unit = m_unit or ""
                if eff_dir is None:
                    for suffix, _lo, _hi, direction, unit, _t, _w, _tc in templates:
                        eff_dir = direction
                        if unit != "__member_unit__":
                            eff_unit = eff_unit or unit
                        break
                if eff_unit == "__member_unit__":
                    eff_unit = ""
                dir_label = DIRECTION_LABEL.get(eff_dir or "", eff_dir or "—")
                tgt = "—"
                if m_target is not None:
                    tgt = f"{m_target:g}"
                lines.append(f"| {m_name} | {dir_label} | {eff_unit or '—'} | {tgt} |")
            lines.append("")

        docs[domain] = "\n".join(lines)
    return docs


def main() -> int:
    """生成全部领域文档并写入 docs/domains 目录。"""
    docs = build_domain_docs()
    out_dir = Path(__file__).resolve().parent.parent / "docs" / "domains"
    out_dir.mkdir(parents=True, exist_ok=True)
    for domain, markdown in docs.items():
        path = out_dir / f"{domain}.zh-CN.md"
        path.write_text(markdown, encoding="utf-8")
    print(f"Wrote {len(docs)} domain docs to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
