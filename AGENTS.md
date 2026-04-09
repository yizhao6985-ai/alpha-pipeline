# quant-data-foundry

专注于 A 股市场数据获取的数据处理项目。

## 项目概述

本项目用于从 Tushare 获取 A 股市场数据并保存为 CSV 格式。

## 技术栈

- **Python**: >= 3.12
- **环境管理**: Conda (`environment.yml`)
- **数据获取**: Tushare API
- **数据处理**: pandas
- **依赖管理**: pip (内置于 conda 环境)

主要依赖包：
- `tushare` - A 股数据源
- `pandas` - 数据处理
- `python-dotenv` - 环境变量管理
- `tqdm` - 进度条显示
- `concurrent.futures` - 并发下载（Python 内置）

## 项目结构

```
quant-data-foundry/
├── scripts/                   # 脚本入口
│   ├── fetch_market_data.py          # 主数据获取脚本
│   ├── fetchers/                     # 数据获取模块
│   │   ├── __init__.py
│   │   ├── base.py                   # 基础工具（Tushare客户端、文件操作）
│   │   ├── stock.py                  # 股票相关数据（股票列表、ST）
│   │   ├── company.py                # 公司相关数据（公司信息、财报）
│   │   ├── index.py                  # 指数相关数据（指数信息、成分权重）
│   │   ├── market.py                 # 市场相关数据（交易日历）
│   │   └── quote.py                  # 行情数据（日线、指标、复权因子）
│   └── process_to_qlib.py            # 数据处理脚本（生成 Qlib 格式）
├── data/                      # 原始数据输出目录（gitignored）
├── environment.yml            # Conda 环境配置
├── .env.example               # 环境变量模板
├── README.md                  # 项目说明
└── AGENTS.md                  # 本文件
```

## 安装与配置

### 快速开始（推荐）

```bash
# 1. 完整初始化（创建环境 + 配置模板）
make setup

# 2. 编辑 .env 文件填入 Tushare Token
# TUSHARE_TOKEN=your_tushare_token_here

# 3. 激活环境并开始使用
conda activate quant-data-foundry
make fetch-demo
```

### 手动安装

#### 1. 创建 Conda 环境

```bash
conda env create -f environment.yml
conda activate quant-data-foundry
```

#### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 Tushare Token
# TUSHARE_TOKEN=your_tushare_token_here
```

## 使用说明

### Makefile 快捷命令

推荐使用 `make` 命令来执行常用操作：

| 命令 | 说明 |
|------|------|
| `make help` | 显示所有可用命令 |
| `make setup` | 完整初始化（创建环境 + 配置模板） |
| `make fetch` | 获取所有市场数据（所有主板股票） |
| `make fetch-quick` | 快速获取基础数据（跳过财报和行情） |
| `make fetch-demo` | 获取演示数据（2只股票） |
| `make fetch-stocks CODES=xxx` | 获取指定股票 |

| `make clean` | 清理行情和财报数据 |
| `make lint` | 代码语法检查 |
| `make process` | 处理数据生成 Qlib 格式 |

### 常用示例

```bash
# 快速获取基础数据（推荐首次使用）
make fetch-quick

# 获取演示数据（2只股票，用于测试）
make fetch-demo

# 获取指定股票数据
make fetch-stocks CODES=600000.SH,000001.SZ

# 获取所有主板股票（耗时较长）
make fetch
```

### 直接运行脚本

| 脚本 | 用途 | 示例 |
|------|------|------|
| `fetch_market_data.py` | 获取市场数据 | `python scripts/fetch_market_data.py` |
| `process_to_qlib.py` | 处理数据生成 Qlib 格式 | `python scripts/process_to_qlib.py` |

### 数据获取脚本参数

```bash
python scripts/fetch_market_data.py --help
```

主要参数：
- `--output-dir`: 输出根目录，默认 "data"
- `--start-date`: 开始日期，默认 "20180101"
- `--end-date`: 结束日期，默认为今天
- `--ts-codes`: 股票代码列表，逗号分隔。不传则自动获取全部A股
- `--market`: 指定市场类型（主板/创业板/科创板/北交所），默认获取所有A股
- `--index-codes`: 指数代码列表，逗号分隔，默认 "000985.CSI,000903.SH,399300.SZ,000905.SH,000852.SH"（中证全指、中证100、沪深300、中证500、中证1000）
- `--workers`: 并发下载线程数，默认 8（根据 Tushare 积分调整）
- `--skip-stock-list`: 跳过股票列表获取
- `--skip-st`: 跳过 ST 股票列表
- `--skip-index-basic`: 跳过指数基础信息
- `--skip-index-weight`: 跳过指数成分权重
- `--skip-calendar`: 跳过交易日历
- `--skip-qfq-daily`: 跳过日线行情
- `--skip-daily-basic`: 跳过每日指标
- `--skip-cyq`: 跳过每日筹码及胜率
- `--skip-financial`: 跳过财务报表

### 数据获取示例

```bash
# 获取中证全指成分股数据（默认）
python scripts/fetch_market_data.py

# 处理数据生成 Qlib 格式（排除 ST 股票）
python scripts/process_to_qlib.py

# 只获取指定股票
python scripts/fetch_market_data.py --ts-codes 600000.SH,000001.SZ

# 指定指数代码（默认已包含中证全指、中证100、沪深300、中证500、中证1000）
python scripts/fetch_market_data.py --index-codes 399300.SZ,000001.SH

# 跳过某些数据类型
python scripts/fetch_market_data.py --skip-financial

# 指定日期范围
python scripts/fetch_market_data.py --start-date 20240101 --end-date 20241231
```

### 数据输出目录结构

数据按日期组织在 `data/YYYYMMDD/` 下：

```
data/YYYYMMDD/
├── company/                    # 公司基本信息 ({ts_code}.csv)
└── financial/                  # 财务报表
    ├── balancesheet/           # 资产负债表 ({ts_code}.csv)
    ├── income/                 # 利润表 ({ts_code}.csv)
    └── cashflow/               # 现金流量表 ({ts_code}.csv)
├── index/
│   ├── index_basic/            # 指数基础信息 ({market}_{category}.csv)
│   └── index_weight/           # 指数成分权重 ({index_code}.csv)
├── calendar/
│   └── trade_calendar.csv      # 交易日历
├── stock/
│   ├── stock_list.csv          # 股票列表（中证全指成分股）
│   └── st_stock_list.csv       # ST 股票列表
├── index/
│   ├── index_basic/            # 指数基础信息
│   └── index_weight/           # 指数成分权重 ({index_code}.csv)
└── quote/
    ├── qfq/                    # 前复权日线行情 ({ts_code}.csv)
    ├── basic/                  # 每日指标 ({ts_code}.csv)
    └── cyq/                    # 每日筹码及胜率 ({ts_code}.csv)
```

## 模块说明

### fetchers/base.py
基础工具函数：
- `get_tushare_pro()` - 获取 Tushare API 客户端
- `save_csv(df, path)` - 保存 DataFrame 为 CSV
- `file_exists_and_not_empty(path)` - 检查文件是否存在

### fetchers/stock.py
股票相关数据：
- `fetch_stock_list(output_dir, today_ymd)` - 股票列表
- `get_all_stock_codes()` - 获取所有主板股票代码
- `fetch_stock_hsgt(...)` - 沪深港通股票列表
- `fetch_stock_st(...)` - ST 股票列表

### fetchers/company.py
公司相关数据：
- `fetch_company_basic_info(...)` - 公司基本信息（指定股票列表）
- `fetch_financial_statements(...)` - 财务报表

### fetchers/index.py
指数相关数据：
- `fetch_index_basic(...)` - 指数基础信息
- `fetch_index_weight(...)` - 指数成分权重

### fetchers/market.py
市场相关数据：
- `fetch_trade_calendar(...)` - 交易日历

### fetchers/quote.py
行情数据：
- `fetch_qfq_daily(...)` - 前复权日线
- `fetch_daily_basic(...)` - 每日指标

### process_to_qlib.py
数据处理脚本，将原始数据转换为 Qlib 格式：
- 排除 ST 股票
- 合并行情数据和每日指标
- 生成 `qlib_data.csv` - 主数据文件
- 生成 `instruments.txt` - 股票列表及时间范围
- 生成 `calendars.txt` - 交易日历

参数：
- `--data-dir`: 原始数据目录，默认 "data"
- `--date`: 数据日期，默认使用最新日期
- `--output-dir`: 输出目录，默认 "qlib_data"
- `--output-file`: 输出文件名，默认 "qlib_data.csv"

使用示例：
```bash
# 使用最新数据日期
python scripts/process_to_qlib.py

# 指定数据日期
python scripts/process_to_qlib.py --date 20260408

# 指定输出目录
python scripts/process_to_qlib.py --output-dir my_qlib_data
```

输出文件结构：
```
qlib_data/
├── qlib_data.csv       # 主数据文件（合并后的行情+指标）
├── instruments.txt     # 股票列表（symbol\tstart_date\tend_date）
└── calendars.txt       # 交易日历（日期列表）
```

CSV 列说明：
- 基础列：`date`, `symbol`, `open`, `high`, `low`, `close`, `volume`, `money`
- 指标列：`turnover_rate`, `pe`, `pe_ttm`, `pb`, `ps`, `total_mv`, `circ_mv` 等

## 代码风格

- **Python 版本**: 3.12+
- **类型注解**: 使用 `from __future__ import annotations`，全面使用类型注解
- **字符串引号**: 代码中使用双引号，文档中使用中文
- **命名规范**: 
  - 函数/变量: 小写下划线 (`fetch_stock_list`)
  - 常量: 大写下划线 (`DEFAULT_FETCH_START_DATE`)

## 注意事项

1. **API 限制**: 
   - 5分钟线数据 (`qfq_5min`) 当前因上游 API 限制已停用
   - Tushare 需要积分权限才能访问部分数据
   - 获取全部主板股票可能需要较长时间和较多 API 积分

2. **环境变量**: 
   - `TUSHARE_TOKEN` 必须配置才能使用数据获取功能
   - 使用 `python-dotenv` 从 `.env` 文件加载

3. **数据增量更新**:
   - 脚本会检查已有数据文件，存在的会跳过
   - 如需重新获取，需手动删除对应目录

4. **编码**: 所有 CSV 输出使用 UTF-8 with BOM (`utf-8-sig`)，便于 Excel 打开

## 扩展指南

### 添加新的数据类型

在 `scripts/fetchers/` 下创建新模块或编辑现有模块：

1. 添加新的数据获取函数（参考现有函数结构）
2. 在 `__init__.py` 中导出
3. 在 `fetch_market_data.py` 中调用

示例（添加到我的数据模块）：
```python
# scripts/fetchers/mydata.py
from .base import get_tushare_pro, save_csv, file_exists_and_not_empty

def fetch_my_data(output_dir: Path, today_ymd: str) -> None:
    pro = get_tushare_pro()
    path = output_dir / today_ymd / "my_data" / f"my_data_{today_ymd}.csv"
    if file_exists_and_not_empty(path):
        return
    df = pro.query("my_api", ...)
    save_csv(df, path)
```
