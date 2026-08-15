

import argparse
import os

import pandas as pd

# 默认读取的文件（国家级双边流向数据）
DEFAULT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data_input",
    "2026_V2",
    "openalex_scholarlymigration_country_flows_gender_and_field.parquet",
)


def summarize(df: pd.DataFrame) -> None:
    """打印数据的基本结构与统计信息。"""
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    print(f"形状 (行, 列): {df.shape}")
    print("\n列名与类型:")
    print(df.dtypes)

    print("\n前 8 行:")
    print(df.head(8))

    print("\n数值列描述统计:")
    print(df.describe())

    # 对分类列展示唯一值（唯一值较少时）
    print("\n分类列唯一值 (<=30 个时展示):")
    for col in df.select_dtypes(include=["object"]).columns:
        uniques = df[col].unique()
        if len(uniques) <= 30:
            print(f"  {col} ({len(uniques)}): {sorted(uniques)}")
        else:
            print(f"  {col}: {len(uniques)} 个唯一值")


def main() -> None:
    parser = argparse.ArgumentParser(description="读取 scholarly migration parquet 文件")
    parser.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_FILE,
        help="parquet 文件路径（默认: 国家级双边流向数据）",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="将读取的数据导出为同名 csv 文件",
    )
    args = parser.parse_args()

    if not os.path.exists(args.path):
        raise FileNotFoundError(f"找不到文件: {args.path}")

    print(f"读取: {args.path}\n")
    df = pd.read_parquet(args.path)
    summarize(df)

    if args.csv:
        out = os.path.splitext(args.path)[0] + ".csv"
        df.to_csv(out, index=False)
        print(f"\n已导出 csv: {out}")


if __name__ == "__main__":
    main()
