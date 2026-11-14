# --- acceptance_backfill (EVAL_ACCEPTANCE_STANDARD.md P4) ---
# 证据来源: .github/workflows/checks.yml
# 命令逐字取自该来源，未增删任何参数。
# 归一: python → python3（本机无 python 别名，实测 Error 127）
# 归一: 补解释器前缀。CI 在测试前 `python -m pip install -r requirements.txt` +
#   `python -m pip install . pytest`（pyproject 里 q-one-core[adaptive]、q-one-agent
#   走 git 依赖），本机系统 python 是 PEP-668 外部管理环境，缺 qone_life / qone_core /
#   qone_agent / portalocker，38 个测试文件在收集阶段就 ModuleNotFoundError（不是测试失败）。
#   已有现成环境 ~/.cache/qone-life-venv（editable 指向本仓 src，含上述依赖）；
#   eval 在该解释器存在时用它，否则回退 python3（等价于 CI 装完依赖后的裸命令）。
QONE_LIFE_PY := $(firstword $(wildcard $(HOME)/.cache/qone-life-venv/bin/python) python3)

.PHONY: eval

eval:
	$(QONE_LIFE_PY) -m pytest -q
