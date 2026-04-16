# alpha-pipeline

本地研究用仓库：**不发布 pip 包**。在仓库根设 `PYTHONPATH=.`（`Makefile` 已 `export`），用 `python -m scripts…` 跑流程。

## 快速开始

```bash
# 1. 初始化（创建环境 + 配置模板）
make setup

# 2. 编辑 .env 填入 Tushare Token
# TUSHARE_TOKEN=your_tushare_token_here

# 3. 激活环境
conda activate alpha-pipeline

# 4. 获取演示数据（2只股票）
make fetch-demo
```

## 目录（同级含义清晰）

```
alpha-pipeline/
├── scripts/
│   ├── tushare/              # Tushare 拉数 → data/
│   ├── build_qlib/           # 原始 CSV → qlib_data/ bin（仅转换）
│   ├── verify_qlib/          # 转换结果自检（如 verify_bin）
│   ├── qlib/                 # Qlib：__main__.py 统一入口 + run_backtest/search_topk/sweep_tail_features + 实现子包
│   ├── fetch_market_data.py
│   ├── process_to_qlib.py
│   ├── test_qlib_data.py
│   ├── run_backtest.py       # → qlib.run_backtest（薄转发）
│   ├── search_topk.py
│   └── sweep_tail_features.py
├── notebooks/
├── data/
├── qlib_data/
├── Makefile
├── environment.yml
└── .env.example
```

**Qlib 命令推荐**：`python -m scripts.qlib run_backtest`、`search_topk`、`sweep_tail_features`（见 `python -m scripts.qlib -h`）。

`scripts/qlib/` 内实现按子模块 `import`（如 `from scripts.qlib.handler import …`），**没有**星号聚合导出。

不用 `make` 时，在仓库根：`export PYTHONPATH="$(pwd)"`。

## 常用命令

```bash
make help
make fetch          # → python -m scripts.tushare.fetch_market
make process        # → python -m scripts.build_qlib.to_qlib
make test           # → python -m scripts.verify_qlib.verify_bin
make backtest       # → python -m scripts.qlib run_backtest
```

其它：`python -m scripts.qlib search_topk`、`python -m scripts.qlib sweep_tail_features`（或直接 `-m scripts.qlib.search_topk`）。

更多见 `make help` 与各模块 `--help`。
