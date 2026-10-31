"""桌面 sidecar 进程入口：直接转发到 qone_life.sidecar.main。"""

from qone_life.sidecar import main

if __name__ == "__main__":
    raise SystemExit(main())
