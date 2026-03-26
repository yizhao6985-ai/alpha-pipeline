# quant-data-foundry

专注于市场数据获取、清洗和 Qlib 结构化准备的数据处理项目。

## 项目结构

```
quant-data-foundry/
├── src/data_fetch/            # 数据获取与落盘逻辑
├── src/data_tools/            # 数据转换与 Qlib 元数据构建
├── scripts/                   # 脚本入口
├── data/                      # 原始/中间数据输出目录
├── qlib_data/                 # Qlib 格式相关输出
├── runtime/                   # 运行时目标配置
├── tests/                     # 测试
├── pyproject.toml             # 项目与工具配置
├── requirements.txt           # 运行依赖
└── requirements-dev.txt       # 开发依赖
```

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## 使用说明

所有使用说明统一放在根目录 Markdown 文件：

- 数据抓取与目录规则：`DATA_FETCH.md`
- `csv/xls` 和 Qlib 辅助脚本说明：`DATA_TOOLS.md`

常用命令：

```bash
python scripts/fetch_market_data.py --help
python scripts/generate_runtime_targets.py --help
python scripts/csv_to_qlib_bin.py --help
python scripts/xls_to_csv.py --help
```

## 环境变量

使用 `tushare` 前请先配置 `.env`：

```bash
cp .env.example .env
```

并填写：

```bash
TUSHARE_TOKEN=your_tushare_token_here
```
