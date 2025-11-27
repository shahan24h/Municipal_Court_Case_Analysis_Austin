import pandas as pd
import json
from pathlib import Path

# Set up paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "case_loads.json"
OUTPUT_PATH = PROJECT_ROOT / "output"


def load_data():
    """Load and properly parse the nested JSON data with column names"""
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    print(f"Raw data type: {type(raw_data)}")

    # Handle different JSON structures
    if isinstance(raw_data, list):
        # Check if it's the wrapped format
        if len(raw_data) > 0 and isinstance(raw_data[0], dict) and 'data' in raw_data[0]:
            case_records = raw_data[0]['data']
            column_names = [col['name'] for col in raw_data[0]['meta']['view']['columns']]
        else:
            case_records = raw_data
            column_names = None
    elif isinstance(raw_data, dict):
        if 'data' in raw_data:
            case_records = raw_data['data']
            if 'meta' in raw_data and 'view' in raw_data['meta']:
                column_names = [col['name'] for col in raw_data['meta']['view']['columns']]
            else:
                column_names = None
        else:
            case_records = [raw_data]
            column_names = None
    else:
        case_records = raw_data
        column_names = None

    print(f"Case records type: {type(case_records)}")
    print(f"Number of records: {len(case_records) if case_records else 0}")

    # Convert to DataFrame
    df = pd.DataFrame(case_records)

    # Rename columns if we found metadata
    if column_names and len(column_names) == len(df.columns):
        df.columns = column_names
        print(f"✓ Applied {len(column_names)} column names from metadata")
    else:
        print(f"! Using default column indices (0-{len(df.columns) - 1})")

    return df


def data_quality_check(df):
    """Analyze data quality"""
    print("\n" + "=" * 60)
    print("DATA QUALITY ASSESSMENT")
    print("=" * 60)

    for col in df.columns:
        null_count = df[col].isnull().sum()
        null_pct = (null_count / len(df)) * 100
        unique_count = df[col].nunique()

        print(f"\n{col}:")
        print(f"  Missing: {null_count:,} ({null_pct:.1f}%)")
        print(f"  Unique values: {unique_count:,}")

        # Show sample values for categorical fields
        if null_pct < 50 and unique_count <= 20:
            print(f"  Top values:")
            for val, count in df[col].value_counts().head(5).items():
                print(f"    {val}: {count:,}")


def initial_exploration(df):
    """Perform initial data exploration"""
    print("\n" + "=" * 60)
    print("MUNICIPAL COURT CASES - DATASET OVERVIEW")
    print("=" * 60)
    print(f"\nTotal Case Records: {len(df):,}")
    print(f"Total Fields: {len(df.columns)}")

    print(f"\nColumn Names:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")

    print(f"\n" + "=" * 60)
    print("SAMPLE CASE RECORD")
    print("=" * 60)
    for col in df.columns:
        value = df[col].iloc[0]
        print(f"{col:35s}: {value}")

    return df


if __name__ == "__main__":
    print("Loading Municipal Court Case data...\n")
    df = load_data()
    df = initial_exploration(df)
    data_quality_check(df)

    # Save outputs
    OUTPUT_PATH.mkdir(exist_ok=True)
    df.to_csv(OUTPUT_PATH / "cases_full.csv", index=False)
    df.head(500).to_csv(OUTPUT_PATH / "cases_sample_500.csv", index=False)

    # Save column info
    with open(OUTPUT_PATH / "column_info.txt", 'w') as f:
        f.write("COLUMN INFORMATION\n")
        f.write("=" * 60 + "\n\n")
        for i, col in enumerate(df.columns, 1):
            f.write(f"{i:2d}. {col}\n")
            f.write(f"    Type: {df[col].dtype}\n")
            f.write(f"    Non-null: {df[col].count():,} / {len(df):,}\n")
            f.write(f"    Unique: {df[col].nunique():,}\n")
            f.write("\n")

    print(f"\n{'=' * 60}")
    print(f"✓ Output files saved to: {OUTPUT_PATH}")
    print(f"  - cases_full.csv (all {len(df):,} cases)")
    print(f"  - cases_sample_500.csv (first 500 cases)")
    print(f"  - column_info.txt (field descriptions)")
    print(f"{'=' * 60}")