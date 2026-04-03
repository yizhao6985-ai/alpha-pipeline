# quant-data-foundry Makefile
# 用于简化数据获取任务的常用命令

.PHONY: help env install fetch fetch-quick clean lint

# 默认目标
help:
	@echo "quant-data-foundry 常用命令"
	@echo ""
	@echo "  make env          - 创建 conda 环境"
	@echo "  make install      - 安装/更新依赖"
	@echo "  make fetch        - 获取所有市场数据（所有主板股票）"
	@echo "  make fetch-quick  - 快速获取（跳过财报和行情）"
	@echo "  make fetch-demo   - 获取演示数据（2只股票）"
	@echo "  make setup        - 完整初始化（创建环境 + 配置模板）"
	@echo "  make clean        - 清理数据目录"
	@echo "  make lint         - 代码语法检查"
	@echo ""
	@echo "环境变量:"
	@echo "  TUSHARE_TOKEN     - Tushare API Token（必需）"

# 创建 conda 环境
env:
	conda env create -f environment.yml || conda env update -f environment.yml
	@echo "环境创建完成，运行: conda activate quant-data-foundry"

# 安装/更新依赖
install:
	conda env update -f environment.yml

# 完整初始化
setup: env
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "已创建 .env 文件，请编辑填入 TUSHARE_TOKEN"; \
	else \
		echo ".env 文件已存在"; \
	fi

# 获取所有市场数据（完整模式）
fetch:
	python scripts/fetch_market_data.py

# 快速获取（跳过财报和个股行情，只获取基础数据）
fetch-quick:
	python scripts/fetch_market_data.py \
		--skip-qfq-daily \
		--skip-daily-basic \
		--skip-adj-factor \
		--skip-financial

# 演示模式（只获取2只股票的完整数据）
fetch-demo:
	python scripts/fetch_market_data.py \
		--ts-codes 600000.SH,000001.SZ \
		--index-codes 399300.SZ

# 获取指定股票
fetch-stocks:
	@echo "用法: make fetch-stocks CODES=600000.SH,000001.SZ"
	@if [ -z "$(CODES)" ]; then \
		echo "错误: 请指定 CODES 参数"; \
		exit 1; \
	fi
	python scripts/fetch_market_data.py --ts-codes $(CODES)

# 只获取基础数据（股票列表、指数、日历等）
fetch-base:
	python scripts/fetch_market_data.py \
		--skip-qfq-daily \
		--skip-daily-basic \
		--skip-adj-factor \
		--skip-financial

# 只获取行情数据（需要已配置股票代码）
fetch-quotes:
	python scripts/fetch_market_data.py \
		--skip-stock-list \
		--skip-hsgt \
		--skip-st \
		--skip-company \
		--skip-index-basic \
		--skip-index-weight \
		--skip-calendar

# 清理数据目录
clean:
	@echo "清理数据目录..."
	@rm -rf data/*/quote/*
	@rm -rf data/*/company/financial/*
	@echo "已清理行情和财报数据"
	@echo "提示: 使用 'make clean-all' 清理所有数据"

# 清理所有数据（谨慎使用）
clean-all:
	@echo "警告: 这将删除所有下载的数据!"
	@read -p "确认继续? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@rm -rf data/
	@echo "已清理所有数据"

# 代码语法检查
lint:
	@echo "检查 Python 语法..."
	@python -m py_compile scripts/*.py scripts/fetchers/*.py
	@echo "语法检查通过"

# 显示项目信息
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
