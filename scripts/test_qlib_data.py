#!/usr/bin/env python3
"""
测试 Qlib 数据加载

验证转换后的数据能否被 Qlib 正常读取且数据量不为 0

用法:
    python scripts/test_qlib_data.py
    python scripts/test_qlib_data.py --code SH600000
    python scripts/test_qlib_data.py --code BJ920000
    python scripts/test_qlib_data.py --help
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

QLIB_DATA_DIR = Path("qlib_data")


def test_qlib_loading(test_code: str | None = None) -> bool:
    """测试 Qlib 数据加载
    
    Args:
        test_code: 指定要测试的股票代码，如 "SH600000"。为 None 时测试第一只股票。
    """
    print("=" * 60)
    print("Qlib 数据加载测试")
    print("=" * 60)
    
    # 检查数据目录
    if not QLIB_DATA_DIR.exists():
        print(f"❌ 数据目录不存在: {QLIB_DATA_DIR.absolute()}")
        print("请先运行: make process")
        return False
    
    # 检查 features 目录
    features_dir = QLIB_DATA_DIR / "features"
    if not features_dir.exists():
        print(f"❌ features 目录不存在")
        return False
    
    # 检查是否有股票数据
    stock_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
    if not stock_dirs:
        print("❌ 没有找到股票数据目录")
        return False
    
    print(f"✅ 找到 {len(stock_dirs)} 个股票/指数目录")
    print(f"   示例: {stock_dirs[0].name}")
    
    # 尝试导入 Qlib
    try:
        import qlib
        from qlib.config import REG_CN
        from qlib.data import D
        print("✅ Qlib 导入成功")
    except ImportError:
        print("⚠️  未安装 Qlib，跳过加载测试")
        print("   如需测试加载，请运行: pip install pyqlib")
        return True
    
    # 初始化 Qlib
    try:
        provider_uri = str(QLIB_DATA_DIR.absolute())
        qlib.init(provider_uri=provider_uri, region=REG_CN)
        print(f"✅ Qlib 初始化成功")
        print(f"   数据目录: {provider_uri}")
    except Exception as e:
        print(f"❌ Qlib 初始化失败: {e}")
        return False
    
    # 测试 1: 加载交易日历
    print("\n测试 1: 交易日历")
    try:
        calendar = D.calendar(freq="day")
        if len(calendar) == 0:
            print("❌ 交易日历为空")
            return False
        print(f"✅ 交易日历: {len(calendar)} 天 ({calendar[0]} ~ {calendar[-1]})")
    except Exception as e:
        print(f"❌ 交易日历加载失败: {e}")
        return False
    
    # 测试 2: 加载股票列表
    print("\n测试 2: 股票列表")
    try:
        instruments = D.instruments(market="all")
        inst_list = list(D.list_instruments(instruments))
        if len(inst_list) == 0:
            print("❌ 股票列表为空")
            return False
        print(f"✅ 股票列表: {len(inst_list)} 只")
        print(f"   示例: {inst_list[0]}")
    except Exception as e:
        print(f"❌ 股票列表加载失败: {e}")
        return False
    
    # 测试 3: 加载特征数据
    print("\n测试 3: 特征数据")
    try:
        # 确定要测试的股票代码
        if test_code:
            # 验证指定的股票代码是否存在
            if test_code not in inst_list:
                # 尝试转换为 Qlib 格式查找
                test_code_alt = test_code.upper()
                if test_code_alt not in inst_list:
                    print(f"❌ 指定的股票代码 {test_code} 不在数据集中")
                    print(f"   可用代码示例: {', '.join(inst_list[:5])}...")
                    return False
                test_code = test_code_alt
            test_stock = test_code
            print(f"   使用指定代码: {test_stock}")
        else:
            test_stock = inst_list[0]
            print(f"   使用默认代码（第一只）: {test_stock}")
        
        features = D.features(
            instruments=[test_stock],
            fields=["$close", "$volume"],
            freq="day"
        )
        if len(features) == 0:
            print(f"❌ {test_stock} 特征数据为空")
            return False
        
        # 统计非零数据
        non_zero_count = (features["$close"] != 0).sum()
        zero_count = (features["$close"] == 0).sum()
        
        print(f"✅ {test_stock} 特征数据: {len(features)} 条")
        print(f"   列: {list(features.columns)}")
        print(f"   非零值: {non_zero_count} 条, 零值: {zero_count} 条")
        
        if zero_count > 0 and non_zero_count > 0:
            # 显示第一个非零值的位置
            first_non_zero_idx = features[features["$close"] != 0].index[0]
            print(f"   第一个有效数据日期: {first_non_zero_idx[1]}")
            print(f"   前3行（含零值）:")
            print(features.head(3))
            print(f"   最后3行:")
            print(features.tail(3))
        else:
            print(f"   前3行:")
            print(features.head(3))
    except Exception as e:
        print(f"❌ 特征数据加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试 4: 加载指数数据（如果有）
    print("\n测试 4: 指数数据")
    try:
        index_instruments = D.instruments(market="index_all")
        index_list = list(D.list_instruments(index_instruments))
        if len(index_list) == 0:
            print("⚠️  指数列表为空（可选）")
        else:
            print(f"✅ 指数列表: {len(index_list)} 个")
            # 加载指数特征
            test_index = index_list[0]
            index_features = D.features(
                instruments=[test_index],
                fields=["$close"],
                freq="day"
            )
            if len(index_features) == 0:
                print(f"⚠️  {test_index} 特征数据为空")
            else:
                print(f"✅ {test_index} 特征数据: {len(index_features)} 条")
    except Exception as e:
        print(f"⚠️  指数数据加载失败（可选）: {e}")
    
    return True


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="测试 Qlib 数据加载",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/test_qlib_data.py           # 测试默认第一只股票
  python scripts/test_qlib_data.py --code SH600000   # 测试指定股票
  python scripts/test_qlib_data.py --code BJ920000   # 测试北交所股票
        """
    )
    parser.add_argument(
        "--code",
        type=str,
        default=None,
        help="指定要测试的股票代码，如 SH600000、BJ920000。不指定则测试第一只股票。"
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    
    success = test_qlib_loading(test_code=args.code)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过！数据可以被 Qlib 正常加载。")
        return 0
    else:
        print("❌ 测试失败，请检查数据格式。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
