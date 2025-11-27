import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime

# Set up paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "case_loads.json"
OUTPUT_PATH = PROJECT_ROOT / "output"
VIZ_PATH = PROJECT_ROOT / "visualizations"

# Create directories
OUTPUT_PATH.mkdir(exist_ok=True)
VIZ_PATH.mkdir(exist_ok=True)

# Set visualization style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)


def load_clean_data():
    """Load and clean the court case data"""
    import json

    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    case_records = raw_data['data']
    column_names = [col['name'] for col in raw_data['meta']['view']['columns']]
    df = pd.DataFrame(case_records, columns=column_names)

    # Data cleaning
    df['Offense Date'] = pd.to_datetime(df['Offense Date'])
    df['Year'] = df['Offense Date'].dt.year
    df['Month'] = df['Offense Date'].dt.month
    df['Month Name'] = df['Offense Date'].dt.strftime('%B')
    df['Day of Week'] = df['Offense Date'].dt.day_name()
    df['Hour'] = pd.to_datetime(df['Offense Time'], format='%H:%M:%S', errors='coerce').dt.hour

    # Create useful flags
    df['Has_Demographics'] = ~(df['Race'].isnull() | df['Defendant Gender'].isnull())
    df['Is_School_Zone'] = df['School Zone'] == True
    df['Is_Active'] = df['Case Closed'] == 'ACT'

    return df


def policy_analysis_overview(df):
    """Generate executive summary for policy makers"""
    print("=" * 80)
    print("MUNICIPAL COURT POLICY ANALYSIS - FISCAL YEAR 2026")
    print("=" * 80)

    print("\n📊 EXECUTIVE SUMMARY")
    print("-" * 80)
    print(f"Total Cases Filed: {len(df):,}")
    print(
        f"Date Range: {df['Offense Date'].min().strftime('%B %d, %Y')} to {df['Offense Date'].max().strftime('%B %d, %Y')}")
    print(f"Active Cases: {df['Is_Active'].sum():,} ({df['Is_Active'].mean() * 100:.1f}%)")
    print(f"Closed Cases: {(~df['Is_Active']).sum():,} ({(~df['Is_Active']).mean() * 100:.1f}%)")

    print("\n🎯 CASE TYPE DISTRIBUTION")
    print("-" * 80)
    case_type_dist = df['Offense Case Type'].value_counts()
    for case_type, count in case_type_dist.items():
        pct = (count / len(df)) * 100
        print(f"{case_type:4s}: {count:6,} cases ({pct:5.1f}%)")

    print("\n🏢 ENFORCEMENT AGENCIES")
    print("-" * 80)
    agency_dist = df['Agency'].value_counts()
    for agency, count in agency_dist.head(5).items():
        pct = (count / len(df)) * 100
        print(f"{agency:50s}: {count:6,} ({pct:5.1f}%)")

    print("\n⚠️ DATA QUALITY CONCERNS")
    print("-" * 80)
    print(f"Missing Race Data: {df['Race'].isnull().sum():,} cases ({df['Race'].isnull().mean() * 100:.1f}%)")
    print(
        f"Missing Gender Data: {df['Defendant Gender'].isnull().sum():,} cases ({df['Defendant Gender'].isnull().mean() * 100:.1f}%)")
    print(f"  → Policy Impact: Cannot assess equity/bias in {df['Race'].isnull().mean() * 100:.1f}% of cases")

    print("\n🎓 SCHOOL ZONE VIOLATIONS")
    print("-" * 80)
    school_zone_cases = df['Is_School_Zone'].sum()
    print(f"School Zone Cases: {school_zone_cases:,} ({df['Is_School_Zone'].mean() * 100:.1f}%)")

    return df


def save_policy_report(df):
    """Save comprehensive policy report"""
    report_path = OUTPUT_PATH / "policy_analysis_report.txt"

    with open(report_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("MUNICIPAL COURT POLICY ANALYSIS REPORT\n")
        f.write("FISCAL YEAR 2026\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Cases Analyzed: {len(df):,}\n")
        f.write(f"Date Range: {df['Offense Date'].min()} to {df['Offense Date'].max()}\n\n")

        f.write("POLICY FINDINGS AND RECOMMENDATIONS:\n")
        f.write("-" * 80 + "\n\n")

        # Finding 1: Data Quality
        f.write("1. DATA COLLECTION GAPS\n")
        f.write(f"   - {df['Race'].isnull().mean() * 100:.1f}% of cases missing demographic data\n")
        f.write("   - Recommendation: Mandate demographic data collection for equity analysis\n\n")

        # Finding 2: Case Load by Type
        f.write("2. CASE TYPE DISTRIBUTION\n")
        for case_type, count in df['Offense Case Type'].value_counts().items():
            f.write(f"   - {case_type}: {count:,} cases ({count / len(df) * 100:.1f}%)\n")
        f.write("\n")

        # Finding 3: Active vs Closed
        active_rate = df['Is_Active'].mean() * 100
        f.write(f"3. CASE RESOLUTION RATE\n")
        f.write(f"   - Active Cases: {active_rate:.1f}%\n")
        f.write(f"   - Closed Cases: {100 - active_rate:.1f}%\n")
        f.write(f"   - Recommendation: Review case processing efficiency\n\n")

    print(f"\n✓ Policy report saved to: {report_path}")


if __name__ == "__main__":
    print("Loading and analyzing Municipal Court data...\n")

    df = load_clean_data()
    df = policy_analysis_overview(df)
    save_policy_report(df)

    print("\n" + "=" * 80)
    print("✓ ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nNext Steps:")
    print("  1. Review policy_analysis_report.txt")
    print("  2. Run detailed analysis on specific case types")
    print("  3. Analyze temporal patterns")
    print("  4. Examine geographic distribution")
    print("=" * 80)