# alpha-pipeline

本地研究用仓库：**不发布 pip 包**。在仓库根设 `PYTHONPATH=.`（`Makefile` 已 `export`），用 `python -m scripts…` 跑流程。Python **3.12**，依赖见 `environment.yml`（conda + pip：`tushare`、`pyqlib` 等）。

## 快速开始

```bash
# 1. 初始化（创建/更新 conda 环境 + 从模板生成 .env）
make setup

# 2. 编辑 .env 填入 Tushare Token
# TUSHARE_TOKEN=your_tushare_token_here

# 3. 激活环境
conda activate alpha-pipeline

# 4. 拉取市场数据（需 Token）
make fetch
```

## 目录（同级含义清晰）

```
alpha-pipeline/
├── scripts/
│   ├── tushare/              # Tushare 拉数 → data/（含 fetchers/）
│   ├── build_qlib/           # 原始 CSV → qlib_data/ bin（to_qlib、dump_bin）
│   ├── verify_qlib/          # 转换结果自检（verify_bin）
│   ├── qlib/                 # Qlib：__main__.py 统一入口 + run_backtest / search_topk / sweep_tail_features
│   │   ├── backtest/         # 回测流水线、绘图、配置
│   │   ├── handler/          # 特征与标签（features/ 等）
│   │   ├── model/            # 训练相关
│   │   ├── strategy/         # 策略（如 overnight_topk）
│   │   ├── dataset/          # 数据集构造
│   │   └── runtime/          # Qlib 初始化、provider、可选 mlflow
│   ├── fetch_market_data.py
│   ├── process_to_qlib.py
│   ├── test_qlib_data.py
│   ├── run_backtest.py       # → qlib.run_backtest（薄转发）
│   ├── search_topk.py
│   └── sweep_tail_features.py
├── notebooks/
├── data/                     # 行情等原始/中间数据（gitignore）
├── qlib_data/                # Qlib bin 输出目录
├── qlib_runs/                # 回测输出（如 plots，视运行参数而定）
├── Makefile
├── environment.yml
└── .env.example
```

**Qlib 命令推荐**：`python -m scripts.qlib run_backtest`、`search_topk`、`sweep_tail_features`（见 `python -m scripts.qlib -h`）。

`scripts/qlib/` 内实现按子模块 `import`（如 `from scripts.qlib.handler import …`），**没有**星号聚合导出。

不用 `make` 时，在仓库根：`export PYTHONPATH="$(pwd)"`。

## 常用命令

```bash
make help           # 列出所有目标与说明
make env            # 创建/更新 conda 环境
make activate       # 打印激活命令提示
make install        # conda env update（同步依赖）
make setup          # env + 若无则复制 .env.example → .env
make fetch          # → python -m scripts.tushare.fetch_market
make process        # → python -m scripts.build_qlib.to_qlib（可选 WORKERS=8）
make test           # → python -m scripts.verify_qlib.verify_bin
make backtest       # → python -m scripts.qlib run_backtest --output-dir qlib_runs/plots
make lint           # → python -m compileall scripts
make clean          # 清理 data 下行情与财报缓存
make clean-all      # 交互确认后删除整个 data/（慎用）
make info           # 打印路径、Python 版本、数据目录与 .env 中 Token 配置提示
```

其它：`python -m scripts.qlib search_topk`、`python -m scripts.qlib sweep_tail_features`（或直接 `-m scripts.qlib.search_topk`）。

更多见 `make help` 与各子命令 `--help`。