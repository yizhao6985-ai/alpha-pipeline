# 数据处理工具脚本

## 1) XLS 转 CSV

脚本：`scripts/xls_to_csv.py`

```bash
python scripts/xls_to_csv.py data/download/000852cons.xls
```

可选参数：

- `--output-csv`：指定输出路径
- `--sheet-name`：指定工作表名
- `--sheet-index`：指定工作表索引（默认 0）

## 2) 目标特征行情生成

脚本：`scripts/build_target_quote_from_tushare.py`

用于从 `qfq_daily/adj_factor` 生成目标特征行情 CSV（输出到 `qlib_data/<日期>/feature`）。

示例：

```bash
python scripts/build_target_quote_from_tushare.py \
  --qfq-dir data/20260326/quote/qfq_daily \
  --adj-dir data/20260326/quote/adj_factor
```
