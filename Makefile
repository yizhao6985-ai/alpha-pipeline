# quant-data-foundry Makefile

.PHONY: help env install fetch setup clean clean-all lint process test backtest activate info

help:
	@echo "quant-data-foundry 常用命令"
	@echo ""
	@echo "  make env          - 创建 conda 环境"
	@echo "  make activate     - 显示激活环境命令"
	@echo "  make install      - 安装/更新依赖"
	@echo "  make fetch        - 获取市场数据（scripts/fetch_market_data.py 默认参数）"
	@echo "  make setup        - 完整初始化（创建环境 + 配置模板）"
	@echo "  make clean        - 清理行情与财报缓存"
	@echo "  make lint         - 代码语法检查"
	@echo "  make process      - 处理数据生成 Qlib 格式（可选 WORKERS=8）"
	@echo "  make test         - 测试 Qlib 数据格式"
	@echo "  make backtest - Qlib 训练 + 回测 + 出图（qlib_runs/plots）"
	@echo ""
	@echo "环境变量:"
	@echo "  TUSHARE_TOKEN     - Tushare API Token（必需）"

env:
	conda env create -f environment.yml || conda env update -f environment.yml
	@echo "环境创建完成，运行: make activate 查看激活命令"

activate:
	@echo "请运行以下命令激活环境:"
	@echo ""
	@echo "  conda activate quant-data-foundry"
	@echo ""

install:
	conda env update -f environment.yml

setup: env
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "已创建 .env 文件，请编辑填入 TUSHARE_TOKEN"; \
	else \
		echo ".env 文件已存在"; \
	fi

fetch:
	python scripts/fetch_market_data.py

clean:
	@echo "清理数据目录..."
	@rm -rf data/*/quote/*
	@rm -rf data/*/company/financial/*
	@echo "已清理行情和财报数据"
	@echo "提示: 使用 'make clean-all' 清理所有数据"

clean-all:
	@echo "警告: 这将删除所有下载的数据!"
	@read -p "确认继续? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@rm -rf data/
	@echo "已清理所有数据"

lint:
	@echo "检查 Python 语法..."
	@python -m compileall -q scripts qlib_lab
	@echo "语法检查通过"

process:
	python scripts/process_to_qlib.py $(if $(WORKERS),--workers $(WORKERS),)

test:
	@echo "测试 Qlib 数据格式..."
	@python scripts/test_qlib_data.py

backtest:
	PYTHONPATH=$(PWD) python -m qlib_lab.run_qlib_backtest --output-dir qlib_runs/plots

info:
	@echo "项目路径: $(PWD)"
	@echo "Python 版本: $(shell python --version 2>&1)"
	@echo ""
	@echo "数据目录结构:"
	@ls -la data/ 2>/dev/null || echo "  (数据目录不存在)"
	@echo ""
	@echo "环境变量:"
	@if [ -f .env ]; then \
		echo "  .env 文件: 存在"; \
		grep "TUSHARE_TOKEN" .env | head -1 || echo "  TUSHARE_TOKEN: 未配置"; \
	else \
		echo "  .env 文件: 不存在 (运行 'make setup' 创建)"; \
	fi
