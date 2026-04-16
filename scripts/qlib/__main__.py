"""Qlib 侧统一 CLI 入口。

::

    python -m scripts.qlib run_backtest --output-dir qlib_runs/plots
    python -m scripts.qlib search_topk --topks 1,3,5
    python -m scripts.qlib sweep_tail_features --tail-min-pct 0 --tail-max-pct 30 --tail-step-pct 5

也可直接 ``python -m scripts.qlib.run_backtest`` 等；根目录 ``scripts/run_backtest.py`` 为薄转发。
"""
from __future__ import annotations

import importlib
import sys

_COMMANDS: dict[str, str] = {
    "run_backtest": "scripts.qlib.run_backtest",
    "search_topk": "scripts.qlib.search_topk",
    "sweep_tail_features": "scripts.qlib.sweep_tail_features",
}


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__ or "")
        print("子命令:", ", ".join(sorted(_COMMANDS)))
        return 1 if not args else 0
    cmd = args[0]
    if cmd not in _COMMANDS:
        print(f"未知子命令: {cmd!r}。可用: {', '.join(sorted(_COMMANDS))}")
        return 1
    mod = importlib.import_module(_COMMANDS[cmd])
    sys.argv = [f"scripts.qlib {cmd}", *args[1:]]
    return int(mod.main())


if __name__ == "__main__":
    raise SystemExit(main())
