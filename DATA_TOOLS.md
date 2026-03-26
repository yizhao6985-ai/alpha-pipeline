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

## 2) 按日期生成 Qlib 基础文件

脚本：`scripts/csv_to_qlib_bin.py`

当前脚本用于从 `data/<日期>/` 生成 Qlib 的基础文本文件（不再生成 `.bin`）：

- `qlib_data/<日期>/calendars/day.txt`
- `qlib_data/<日期>/calendars/day_future.txt`
- `qlib_data/<日期>/instruments/all.txt`
- `qlib_data/<日期>/instruments/csi1000.txt`

示例：

```bash
python scripts/csv_to_qlib_bin.py 20260324
```

可选参数：

- `--data-root`：原始数据根目录（默认 `data`）
- `--output-root`：Qlib 输出根目录（默认 `qlib_data`）
