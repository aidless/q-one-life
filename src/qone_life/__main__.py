"""以模块方式（python -m qone_life）运行命令行入口。"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
