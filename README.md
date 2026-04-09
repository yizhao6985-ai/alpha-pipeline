# quant-data-foundry

专注于 A 股市场数据获取的数据处理项目。

## 快速开始

```bash
# 1. 初始化（创建环境 + 配置模板）
make setup

# 2. 编辑 .env 填入 Tushare Token
# TUSHARE_TOKEN=your_tushare_token_here

# 3. 激活环境
conda activate quant-data-foundry

# 4. 获取演示数据（2只股票）
make fetch-demo
```

## 项目结构

```
quant-data-foundry/
├── scripts/                   # 脚本入口
│   ├── fetch_market_data.py          # 主数据获取脚本
│   ├── fetchers/                     # 数据获取模块
│   │   ├── base.py                   # 基础工具
│   │   ├── stock.py                  # 股票数据
│   │   ├── company.py                # 公司数据
│   │   ├── index.py                  # 指数数据
│   │   ├── market.py                 # 市场数据
│   │   └── quote.py                  # 行情数据
├── data/                      # 原始数据输出目录
├── Makefile                   # 快捷命令
├── environment.yml            # Conda 环境配置
└── .env.example               # 环境变量模板
```

## 常用命令

### Makefile 快捷命令

```bash
make help              # 显示所有命令
make setup             # 初始化环境和配置
make fetch             # 获取所有数据（所有主板股票）
make fetch-quick       # 快速获取基础数据
make fetch-demo        # 获取演示数据（2只股票）
make fetch-stocks      # 获取指定股票
make lint              # 代码检查
```

### 示例

```bash
# 快速获取基础数据（股票列表、指数、日历等）
make fetch-quick

# 获取指定股票数据
make fetch-stocks CODES=600000.SH,000001.SZ

# 获取所有主板股票数据（耗时较长）
make fetch

# 直接运行脚本
python scripts/fetch_market_data.py --ts-codes 600000.SH,000001.SZ
```

详细说明请参考 `AGENTS.md`。
