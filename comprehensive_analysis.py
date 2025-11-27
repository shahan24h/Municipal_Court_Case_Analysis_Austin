import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
import json

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
plt.rcParams['figure.figsize'] = (14, 8)


def load_clean_data():
    """Load and clean the court case data"""
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
    df['Weekday'] = df['Offense Date'].dt.weekday
    df['Day'] = df['Offense Date'].dt.day

    # Parse time properly
    df['Hour'] = pd.to_datetime(df['Offense Time'], format='%H:%M:%S', errors='coerce').dt.hour

    # Create useful flags
    df['Has_Demographics'] = ~(df['Race'].isnull() | df['Defendant Gender'].isnull())
    df['Is_School_Zone'] = df['School Zone'] == True
    df['Is_Active'] = df['Case Closed'] == 'ACT'
    df['Is_Parking'] = df['Offense Case Type'] == 'PK'
    df['Is_Traffic'] = df['Offense Case Type'] == 'TR'

    return df


def get_mode_safe(x):
    """Safely get mode, handling empty series"""
    if len(x) == 0:
        return None
    mode_vals = x.mode()
    return mode_vals.iloc[0] if len(mode_vals) > 0 else None


def temporal_analysis(df):
    """Analyze temporal patterns"""
    print("\n" + "=" * 80)
    print("⏰ TEMPORAL PATTERN ANALYSIS")
    print("=" * 80)

    # Daily pattern
    print("\n📅 CASES BY DAY OF WEEK")
    print("-" * 80)
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily_cases = df['Day of Week'].value_counts().reindex(day_order)
    for day, count in daily_cases.items():
        pct = (count / len(df)) * 100
        bar = '█' * int(pct)
        print(f"{day:10s}: {count:5,} ({pct:5.1f}%) {bar}")

    # Hourly pattern (for cases with time data)
    print("\n🕐 PEAK ENFORCEMENT HOURS (Top 10)")
    print("-" * 80)
    hourly_cases = df['Hour'].value_counts().sort_index().head(10)
    for hour, count in hourly_cases.items():
        if pd.notna(hour):
            print(f"{int(hour):02d}:00 - {count:,} cases")

    # Day of month pattern
    print("\n📆 CASES BY DAY OF MONTH")
    print("-" * 80)
    daily_dist = df['Day'].value_counts().sort_index()
    for day, count in daily_dist.head(10).items():
        print(f"Day {day:2d}: {count:,} cases")

    # Create visualizations
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 1. Cases by Day of Week
    daily_cases.plot(kind='bar', ax=axes[0, 0], color='steelblue')
    axes[0, 0].set_title('Cases by Day of Week', fontsize=14, fontweight='bold')
    axes[0, 0].set_xlabel('Day of Week')
    axes[0, 0].set_ylabel('Number of Cases')
    axes[0, 0].tick_params(axis='x', rotation=45)

    # 2. Cases by Day of Month
    daily_dist.plot(kind='line', marker='o', ax=axes[0, 1], color='darkgreen')
    axes[0, 1].set_title('Cases by Day of Month (October 2025)', fontsize=14, fontweight='bold')
    axes[0, 1].set_xlabel('Day of Month')
    axes[0, 1].set_ylabel('Number of Cases')
    axes[0, 1].grid(True, alpha=0.3)

    # 3. Case Type Distribution
    df['Offense Case Type'].value_counts().plot(kind='pie', ax=axes[1, 0], autopct='%1.1f%%')
    axes[1, 0].set_title('Case Type Distribution', fontsize=14, fontweight='bold')
    axes[1, 0].set_ylabel('')

    # 4. Active vs Closed Cases
    status_data = df['Case Closed'].value_counts()
    status_data.plot(kind='bar', ax=axes[1, 1], color=['coral', 'lightgreen'])
    axes[1, 1].set_title('Case Status Distribution', fontsize=14, fontweight='bold')
    axes[1, 1].set_xlabel('Status')
    axes[1, 1].set_ylabel('Number of Cases')
    axes[1, 1].tick_params(axis='x', rotation=0)

    plt.tight_layout()
    plt.savefig(VIZ_PATH / 'temporal_analysis.png', dpi=300, bbox_inches='tight')
    print(f"\n✓ Visualization saved: temporal_analysis.png")
    plt.close()


def geographic_analysis(df):
    """Analyze geographic patterns"""
    print("\n" + "=" * 80)
    print("📍 GEOGRAPHIC PATTERN ANALYSIS")
    print("=" * 80)

    print("\n🗺️ TOP 20 ENFORCEMENT LOCATIONS")
    print("-" * 80)
    top_streets = df['Offense Street Name'].value_counts().head(20)
    for i, (street, count) in enumerate(top_streets.items(), 1):
        pct = (count / len(df)) * 100
        print(f"{i:2d}. {street:50s}: {count:5,} ({pct:4.1f}%)")

    # Save detailed location data - FIXED
    location_report = df.groupby('Offense Street Name').agg({
        'sid': 'count',
        'Offense Case Type': get_mode_safe,
        'Is_Active': 'sum',
        'Agency': get_mode_safe
    }).rename(columns={'sid': 'Total_Cases', 'Is_Active': 'Active_Cases'})

    location_report = location_report.sort_values('Total_Cases', ascending=False)
    location_report.to_csv(OUTPUT_PATH / 'location_hotspots.csv')
    print(f"\n✓ Location analysis saved: location_hotspots.csv")


def charge_analysis(df):
    """Analyze violation charges"""
    print("\n" + "=" * 80)
    print("⚖️ VIOLATION CHARGE ANALYSIS")
    print("=" * 80)

    print("\n🚨 TOP 15 VIOLATION TYPES")
    print("-" * 80)
    top_charges = df['Offense Charge Description'].value_counts().head(15)
    for i, (charge, count) in enumerate(top_charges.items(), 1):
        pct = (count / len(df)) * 100
        print(f"{i:2d}. {charge:60s}: {count:5,} ({pct:4.1f}%)")

    # Charge by case type
    print("\n📊 CHARGE DISTRIBUTION BY CASE TYPE")
    print("-" * 80)
    for case_type in df['Offense Case Type'].unique():
        if pd.notna(case_type):
            type_df = df[df['Offense Case Type'] == case_type]
            print(f"\n{case_type} Cases: {len(type_df):,}")
            top_3 = type_df['Offense Charge Description'].value_counts().head(3)
            for charge, count in top_3.items():
                print(f"  - {charge}: {count:,}")

    # Save charge analysis
    charge_report = df.groupby(['Offense Case Type', 'Offense Charge Description']).agg({
        'sid': 'count',
        'Is_Active': 'sum'
    }).rename(columns={'sid': 'Total_Cases', 'Is_Active': 'Active_Cases'})
    charge_report = charge_report.sort_values('Total_Cases', ascending=False)
    charge_report.to_csv(OUTPUT_PATH / 'charge_analysis.csv')
    print(f"\n✓ Charge analysis saved: charge_analysis.csv")


def demographic_analysis(df):
    """Analyze demographic patterns (limited by missing data)"""
    print("\n" + "=" * 80)
    print("👥 DEMOGRAPHIC ANALYSIS (Limited Data)")
    print("=" * 80)

    # Filter to cases with demographic data
    demo_df = df[df['Has_Demographics']].copy()

    print(f"\nCases with demographic data: {len(demo_df):,} ({len(demo_df) / len(df) * 100:.1f}%)")

    if len(demo_df) > 0:
        print("\n🎭 RACE DISTRIBUTION (Available Data Only)")
        print("-" * 80)
        race_dist = demo_df['Race'].value_counts()
        for race, count in race_dist.items():
            pct = (count / len(demo_df)) * 100
            print(f"{race:20s}: {count:5,} ({pct:5.1f}%)")

        print("\n⚥ GENDER DISTRIBUTION (Available Data Only)")
        print("-" * 80)
        gender_dist = demo_df['Defendant Gender'].value_counts()
        for gender, count in gender_dist.items():
            pct = (count / len(demo_df)) * 100
            print(f"{gender:10s}: {count:5,} ({pct:5.1f}%)")

        # Demographics by case type
        print("\n📈 DEMOGRAPHICS BY CASE TYPE")
        print("-" * 80)
        demo_by_type = pd.crosstab(demo_df['Offense Case Type'], demo_df['Race'])
        print(demo_by_type)

        # Save demographic analysis
        demo_by_type.to_csv(OUTPUT_PATH / 'demographics_by_case_type.csv')
        print(f"\n✓ Demographic analysis saved: demographics_by_case_type.csv")
    else:
        print("⚠️ Insufficient demographic data for analysis")


def agency_performance_analysis(df):
    """Analyze agency enforcement patterns"""
    print("\n" + "=" * 80)
    print("🏛️ AGENCY ENFORCEMENT ANALYSIS")
    print("=" * 80)

    agency_stats = df.groupby('Agency').agg({
        'sid': 'count',
        'Is_Active': ['sum', 'mean'],
        'Is_School_Zone': 'sum',
        'Offense Case Type': get_mode_safe
    }).round(3)

    agency_stats.columns = ['Total_Cases', 'Active_Cases', 'Active_Rate', 'School_Zone_Cases', 'Primary_Case_Type']
    agency_stats = agency_stats.sort_values('Total_Cases', ascending=False)

    print("\nAGENCY PERFORMANCE METRICS")
    print("-" * 80)
    print(agency_stats.to_string())

    agency_stats.to_csv(OUTPUT_PATH / 'agency_performance.csv')
    print(f"\n✓ Agency analysis saved: agency_performance.csv")


def policy_recommendations(df):
    """Generate policy recommendations"""
    print("\n" + "=" * 80)
    print("💡 POLICY RECOMMENDATIONS")
    print("=" * 80)

    recommendations = []

    # Recommendation 1: Data Collection
    if df['Race'].isnull().mean() > 0.5:
        recommendations.append({
            'Priority': 'HIGH',
            'Category': 'Data Quality',
            'Issue': f'{df["Race"].isnull().mean() * 100:.1f}% missing demographic data',
            'Recommendation': 'Mandate demographic data collection for all case types to enable equity analysis',
            'Impact': 'Enable bias detection and ensure equitable enforcement'
        })

    # Recommendation 2: Active Case Backlog
    active_rate = df['Is_Active'].mean()
    if active_rate > 0.6:
        recommendations.append({
            'Priority': 'HIGH',
            'Category': 'Case Management',
            'Issue': f'{active_rate * 100:.1f}% of cases remain active',
            'Recommendation': 'Review case processing procedures and staffing levels',
            'Impact': f'Resolve {df["Is_Active"].sum():,} pending cases faster'
        })

    # Recommendation 3: Parking Enforcement
    parking_pct = df['Is_Parking'].mean()
    if parking_pct > 0.8:
        recommendations.append({
            'Priority': 'MEDIUM',
            'Category': 'Resource Allocation',
            'Issue': f'{parking_pct * 100:.1f}% of cases are parking violations',
            'Recommendation': 'Consider alternative resolution mechanisms (online payment, warning programs)',
            'Impact': 'Reduce court burden, improve citizen experience'
        })

    # Recommendation 4: School Zone Safety
    if df['Is_School_Zone'].sum() > 0:
        recommendations.append({
            'Priority': 'MEDIUM',
            'Category': 'Public Safety',
            'Issue': f'{df["Is_School_Zone"].sum():,} school zone violations',
            'Recommendation': 'Enhance school zone enforcement and education campaigns',
            'Impact': 'Improve child safety near schools'
        })

    # Recommendation 5: Weekend Enforcement
    weekend_cases = df[df['Day of Week'].isin(['Saturday', 'Sunday'])].shape[0]
    weekend_pct = weekend_cases / len(df)
    if weekend_pct < 0.2:
        recommendations.append({
            'Priority': 'LOW',
            'Category': 'Enforcement Strategy',
            'Issue': f'Only {weekend_pct * 100:.1f}% of enforcement occurs on weekends',
            'Recommendation': 'Evaluate if weekend enforcement levels match violation patterns',
            'Impact': 'Optimize resource allocation across all days'
        })

    print("\n📋 RECOMMENDED ACTIONS")
    print("-" * 80)
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. [{rec['Priority']}] {rec['Category']}")
        print(f"   Issue: {rec['Issue']}")
        print(f"   Action: {rec['Recommendation']}")
        print(f"   Impact: {rec['Impact']}")

    # Save recommendations
    rec_df = pd.DataFrame(recommendations)
    rec_df.to_csv(OUTPUT_PATH / 'policy_recommendations.csv', index=False)
    print(f"\n✓ Recommendations saved: policy_recommendations.csv")


if __name__ == "__main__":
    print("=" * 80)
    print("COMPREHENSIVE POLICY ANALYSIS - MUNICIPAL COURT CASES")
    print("=" * 80)

    df = load_clean_data()

    temporal_analysis(df)
    geographic_analysis(df)
    charge_analysis(df)
    demographic_analysis(df)
    agency_performance_analysis(df)
    policy_recommendations(df)

    print("\n" + "=" * 80)
    print("✅ COMPREHENSIVE ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nGenerated Files:")
    print("  📊 Visualizations:")
    print("     - visualizations/temporal_analysis.png")
    print("  📁 Data Files:")
    print("     - output/location_hotspots.csv")
    print("     - output/charge_analysis.csv")
    print("     - output/agency_performance.csv")
    print("     - output/demographics_by_case_type.csv")
    print("     - output/policy_recommendations.csv")
    print("=" * 80)