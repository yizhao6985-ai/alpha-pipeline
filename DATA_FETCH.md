# 数据抓取说明

## 入口脚本

统一使用：

```bash
python scripts/fetch_market_data.py --help
```

## 常用命令

抓取默认数据：

```bash
python scripts/fetch_market_data.py
```

生成 runtime 目标文件：

```bash
python scripts/generate_runtime_targets.py
```

手动指定公司和指数：

```bash
python scripts/generate_runtime_targets.py \
  --ts-code 600000.SH \
  --ts-code 000001.SZ \
  --index-code 399300.SZ,000001.SH
```

## 参数说明

- `--output-dir`：输出根目录，默认 `data`
- `--skip-financial`：跳过公司财报抓取
- `--skip-qfq-daily`：跳过 A 股前复权日线行情抓取
- `--skip-qfq-5min`：跳过 A 股前复权 5 分钟行情抓取
- `--skip-daily-basic`：跳过 A 股每日指标抓取

## Runtime 配置

默认读取 `runtime/targets.json`，示例：

```json
{
  "ts_codes": ["600000.SH", "000001.SZ"],
  "index_codes": ["399300.SZ", "000001.SH"],
  "index_basic_markets": ["CSI", "SSE", "SZSE"],
  "stock_index_basic_categories": [
    "主题指数",
    "规模指数",
    "策略指数",
    "风格指数",
    "综合指数",
    "行业指数"
  ]
}
```

## 数据输出目录

- `data/YYYYMMDD/company/company_basic_info`
- `data/YYYYMMDD/company/financial`
- `data/YYYYMMDD/index/index_basic`
- `data/YYYYMMDD/index/index_weight`
- `data/YYYYMMDD/calendar/calendar`
- `data/YYYYMMDD/stock/hsgt_stock_list`
- `data/YYYYMMDD/stock/stock_list`
- `data/YYYYMMDD/stock/st_stock_list`
- `data/YYYYMMDD/quote/qfq_daily`
- `data/YYYYMMDD/quote/qfq_5min`
- `data/YYYYMMDD/quote/daily_basic`
