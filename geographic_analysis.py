import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
from collections import Counter

# Set up paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "case_loads.json"
OUTPUT_PATH = PROJECT_ROOT / "output"
VIZ_PATH = PROJECT_ROOT / "visualizations"

OUTPUT_PATH.mkdir(exist_ok=True)
VIZ_PATH.mkdir(exist_ok=True)


def load_clean_data():
    """Load and clean the court case data"""
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    case_records = raw_data['data']
    column_names = [col['name'] for col in raw_data['meta']['view']['columns']]
    df = pd.DataFrame(case_records, columns=column_names)

    df['Offense Date'] = pd.to_datetime(df['Offense Date'])
    df['Is_Parking'] = df['Offense Case Type'] == 'PK'
    df['Is_Traffic'] = df['Offense Case Type'] == 'TR'
    df['Is_Active'] = df['Case Closed'] == 'ACT'

    return df


def extract_street_patterns(df):
    """Analyze and group streets by patterns"""
    print("=" * 80)
    print("📍 STREET-LEVEL GEOGRAPHIC ANALYSIS")
    print("=" * 80)

    # Clean and standardize street names
    df['Street_Clean'] = df['Offense Street Name'].str.upper().str.strip()

    # Extract street base names (remove numbers)
    df['Street_Base'] = df['Street_Clean'].str.extract(r'(\d+\s+)?([A-Z\s]+)', expand=False)[1]
    df['Street_Base'] = df['Street_Base'].str.strip()

    # Group by major corridors
    print("\n🛣️  TOP CORRIDORS (Aggregated by street name)")
    print("-" * 80)

    corridor_counts = df['Street_Base'].value_counts().head(20)
    for i, (corridor, count) in enumerate(corridor_counts.items(), 1):
        pct = (count / len(df)) * 100
        total_on_street = len(df[df['Street_Base'] == corridor])
        print(f"{i:2d}. {corridor:40s}: {count:5,} locations ({pct:4.1f}%)")

    return df


def analyze_major_corridors(df):
    """Detailed analysis of major enforcement corridors"""
    print("\n" + "=" * 80)
    print("🗺️  MAJOR CORRIDOR ANALYSIS")
    print("=" * 80)

    # Define major corridors
    corridors = {
        'S CONGRESS AVE': ['S CONGRESS', 'CONGRESS AVE'],
        'E 4TH ST': ['E 4TH', '4TH ST'],
        'W CESAR CHAVEZ': ['CESAR CHAVEZ', 'W CESAR'],
        'I-35': ['I-35', 'I35', 'IH35', 'IH 35'],
        'PRESIDENTIAL BLVD': ['PRESIDENTIAL'],
        'E DEAN KEETON': ['DEAN KEETON'],
        'NUECES ST': ['NUECES'],
        'ALDRICH ST': ['ALDRICH']
    }

    # Categorize each case by corridor
    def categorize_corridor(street):
        if pd.isna(street):
            return 'Other'
        street = str(street).upper()
        for corridor_name, keywords in corridors.items():
            if any(keyword in street for keyword in keywords):
                return corridor_name
        return 'Other'

    df['Corridor'] = df['Offense Street Name'].apply(categorize_corridor)

    # Analyze by corridor
    corridor_analysis = df.groupby('Corridor').agg({
        'sid': 'count',
        'Is_Parking': 'sum',
        'Is_Traffic': 'sum',
        'Is_Active': 'sum',
        'Offense Case Type': lambda x: x.mode()[0] if len(x) > 0 else None
    }).rename(columns={
        'sid': 'Total_Cases',
        'Is_Parking': 'Parking_Cases',
        'Is_Traffic': 'Traffic_Cases',
        'Is_Active': 'Active_Cases'
    })

    corridor_analysis['Active_Rate'] = (corridor_analysis['Active_Cases'] /
                                        corridor_analysis['Total_Cases'] * 100).round(1)

    corridor_analysis = corridor_analysis.sort_values('Total_Cases', ascending=False)

    print("\nCORRIDOR ENFORCEMENT SUMMARY")
    print("-" * 80)
    print(f"{'Corridor':<25} {'Total':>8} {'Parking':>8} {'Traffic':>8} {'Active%':>8}")
    print("-" * 80)

    for corridor, row in corridor_analysis.head(15).iterrows():
        print(f"{corridor:<25} {row['Total_Cases']:>8,} {row['Parking_Cases']:>8,} "
              f"{row['Traffic_Cases']:>8,} {row['Active_Rate']:>7.1f}%")

    # Save detailed corridor analysis
    corridor_analysis.to_csv(OUTPUT_PATH / 'corridor_analysis.csv')
    print(f"\n✓ Corridor analysis saved: corridor_analysis.csv")

    return df, corridor_analysis


def create_heatmap_data(df):
    """Create data for heat mapping"""
    print("\n" + "=" * 80)
    print("🔥 GENERATING HEAT MAP DATA")
    print("=" * 80)

    # Group by exact location
    location_heatmap = df.groupby('Offense Street Name').agg({
        'sid': 'count',
        'Is_Parking': 'sum',
        'Is_Traffic': 'sum',
        'Offense Case Type': lambda x: ', '.join(x.value_counts().head(3).index.tolist())
    }).rename(columns={
        'sid': 'Case_Count',
        'Is_Parking': 'Parking_Count',
        'Is_Traffic': 'Traffic_Count',
        'Offense Case Type': 'Top_Case_Types'
    })

    location_heatmap = location_heatmap.sort_values('Case_Count', ascending=False)

    # Categorize intensity
    location_heatmap['Intensity'] = pd.cut(
        location_heatmap['Case_Count'],
        bins=[0, 10, 50, 100, 500],
        labels=['Low', 'Medium', 'High', 'Critical']
    )

    print("\nENFORCEMENT INTENSITY DISTRIBUTION")
    print("-" * 80)
    intensity_dist = location_heatmap['Intensity'].value_counts().sort_index()
    for intensity, count in intensity_dist.items():
        pct = (count / len(location_heatmap)) * 100
        print(f"{intensity:10s}: {count:4,} locations ({pct:5.1f}%)")

    # Save heat map data
    location_heatmap.to_csv(OUTPUT_PATH / 'location_heatmap_data.csv')
    print(f"\n✓ Heat map data saved: location_heatmap_data.csv")

    # High-intensity locations
    print("\n🚨 CRITICAL ENFORCEMENT ZONES (100+ cases)")
    print("-" * 80)
    critical_zones = location_heatmap[location_heatmap['Case_Count'] >= 100]
    for location, row in critical_zones.head(20).iterrows():
        print(f"{location:50s}: {row['Case_Count']:4,} cases")

    return location_heatmap


def analyze_district_patterns(df):
    """Analyze patterns by district/area"""
    print("\n" + "=" * 80)
    print("🏙️  DISTRICT/AREA ANALYSIS")
    print("=" * 80)

    # Identify areas by keywords in street names
    def categorize_area(street):
        if pd.isna(street):
            return 'Unknown'
        street = str(street).upper()

        # Downtown
        if any(x in street for x in ['CONGRESS', 'COLORADO', 'BRAZOS', 'LAVACA', 'SAN JACINTO', 'TRINITY']):
            return 'Downtown'
        # University area
        elif any(x in street for x in ['DEAN KEETON', 'GUADALUPE', 'NUECES', 'RIO GRANDE']):
            return 'University/Campus'
        # Airport
        elif any(x in street for x in ['PRESIDENTIAL', 'BERGSTROM', 'AIRPORT']):
            return 'Airport Area'
        # East Austin
        elif any(x in street for x in ['E 7TH', 'E 6TH', 'E 5TH', 'CESAR CHAVEZ', 'HOLLY']):
            return 'East Austin'
        # South Austin
        elif any(x in street for x in ['S CONGRESS', 'S LAMAR', 'S 1ST', 'OLTORF']):
            return 'South Austin'
        # North Austin
        elif any(x in street for x in ['N LAMAR', 'BURNET', 'ANDERSON']):
            return 'North Austin'
        # West Austin
        elif any(x in street for x in ['MOPAC', 'WEST GATE']):
            return 'West Austin'
        else:
            return 'Other'

    df['Area'] = df['Offense Street Name'].apply(categorize_area)

    area_analysis = df.groupby('Area').agg({
        'sid': 'count',
        'Is_Parking': ['sum', 'mean'],
        'Is_Traffic': ['sum', 'mean'],
        'Is_Active': 'mean'
    }).round(3)

    area_analysis.columns = ['Total_Cases', 'Parking_Count', 'Parking_Rate',
                             'Traffic_Count', 'Traffic_Rate', 'Active_Rate']
    area_analysis = area_analysis.sort_values('Total_Cases', ascending=False)

    print("\nAREA ENFORCEMENT SUMMARY")
    print("-" * 80)
    print(area_analysis)

    # Save area analysis
    area_analysis.to_csv(OUTPUT_PATH / 'area_analysis.csv')
    print(f"\n✓ Area analysis saved: area_analysis.csv")

    return df, area_analysis


def create_geographic_visualizations(df, corridor_analysis, area_analysis):
    """Create geographic visualizations"""
    print("\n" + "=" * 80)
    print("📊 CREATING GEOGRAPHIC VISUALIZATIONS")
    print("=" * 80)

    fig, axes = plt.subplots(2, 2, figsize=(18, 12))

    # 1. Top Corridors
    ax1 = axes[0, 0]
    top_corridors = corridor_analysis.head(10)
    ax1.barh(range(len(top_corridors)), top_corridors['Total_Cases'], color='steelblue')
    ax1.set_yticks(range(len(top_corridors)))
    ax1.set_yticklabels(top_corridors.index, fontsize=9)
    ax1.set_xlabel('Number of Cases', fontweight='bold')
    ax1.set_title('Top 10 Enforcement Corridors', fontweight='bold', fontsize=12)
    ax1.invert_yaxis()
    for i, v in enumerate(top_corridors['Total_Cases']):
        ax1.text(v + 20, i, f'{v:,}', va='center', fontsize=9)

    # 2. Area Distribution
    ax2 = axes[0, 1]
    area_cases = area_analysis['Total_Cases'].sort_values(ascending=False).head(8)
    colors = plt.cm.Set3(range(len(area_cases)))
    ax2.pie(area_cases.values, labels=area_cases.index, autopct='%1.1f%%',
            colors=colors, startangle=90)
    ax2.set_title('Cases by Area', fontweight='bold', fontsize=12)

    # 3. Parking vs Traffic by Corridor
    ax3 = axes[1, 0]
    top_5_corridors = corridor_analysis.head(5)
    x = range(len(top_5_corridors))
    width = 0.35
    ax3.bar([i - width / 2 for i in x], top_5_corridors['Parking_Cases'],
            width, label='Parking', color='orange')
    ax3.bar([i + width / 2 for i in x], top_5_corridors['Traffic_Cases'],
            width, label='Traffic', color='blue')
    ax3.set_xticks(x)
    ax3.set_xticklabels([c[:15] for c in top_5_corridors.index], rotation=45, ha='right')
    ax3.set_ylabel('Number of Cases', fontweight='bold')
    ax3.set_title('Case Types by Top 5 Corridors', fontweight='bold', fontsize=12)
    ax3.legend()

    # 4. Location Concentration
    ax4 = axes[1, 1]
    location_counts = df['Offense Street Name'].value_counts()
    concentration_bins = [0, 10, 25, 50, 100, 500]
    concentration_labels = ['1-10', '11-25', '26-50', '51-100', '100+']
    location_distribution = pd.cut(location_counts, bins=concentration_bins,
                                   labels=concentration_labels).value_counts().sort_index()

    ax4.bar(range(len(location_distribution)), location_distribution.values, color='darkgreen')
    ax4.set_xticks(range(len(location_distribution)))
    ax4.set_xticklabels(location_distribution.index)
    ax4.set_xlabel('Cases per Location', fontweight='bold')
    ax4.set_ylabel('Number of Locations', fontweight='bold')
    ax4.set_title('Enforcement Concentration Pattern', fontweight='bold', fontsize=12)
    for i, v in enumerate(location_distribution.values):
        ax4.text(i, v + 5, str(v), ha='center', fontweight='bold')

    plt.suptitle('GEOGRAPHIC ENFORCEMENT ANALYSIS - OCTOBER 2025',
                 fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(VIZ_PATH / 'geographic_analysis.png', dpi=300, bbox_inches='tight')
    print(f"✓ Geographic visualization saved: geographic_analysis.png")
    plt.close()


def generate_geocoding_template(df):
    """Generate template for geocoding"""
    print("\n" + "=" * 80)
    print("🗺️  GENERATING GEOCODING TEMPLATE")
    print("=" * 80)

    # Get unique locations with counts
    location_summary = df.groupby('Offense Street Name').agg({
        'sid': 'count',
        'Offense Case Type': lambda x: x.mode()[0] if len(x) > 0 else None
    }).rename(columns={'sid': 'Case_Count'})

    location_summary = location_summary.sort_values('Case_Count', ascending=False)

    # Add city and state for geocoding
    location_summary['Full_Address'] = location_summary.index + ', Austin, TX'
    location_summary['Latitude'] = ''
    location_summary['Longitude'] = ''
    location_summary['Geocoded'] = False

    # Save template
    location_summary.to_csv(OUTPUT_PATH / 'locations_for_geocoding.csv')

    print(f"\n✓ Geocoding template created: locations_for_geocoding.csv")
    print(f"  Total unique locations: {len(location_summary):,}")
    print(f"\n  Next steps:")
    print(f"  1. Use Google Maps API, OpenStreetMap, or manual geocoding")
    print(f"  2. Fill in Latitude and Longitude columns")
    print(f"  3. Import back for heat map visualization")
    print(f"  4. Suggested tools: geopy, googlemaps Python packages")


if __name__ == "__main__":
    print("=" * 80)
    print("GEOGRAPHIC ANALYSIS - MUNICIPAL COURT CASES")
    print("=" * 80)
    print()

    df = load_clean_data()

    # Street pattern analysis
    df = extract_street_patterns(df)

    # Major corridor analysis
    df, corridor_analysis = analyze_major_corridors(df)

    # Heat map data
    location_heatmap = create_heatmap_data(df)

    # District/area analysis
    df, area_analysis = analyze_district_patterns(df)

    # Create visualizations
    create_geographic_visualizations(df, corridor_analysis, area_analysis)

    # Generate geocoding template
    generate_geocoding_template(df)

    print("\n" + "=" * 80)
    print("✅ GEOGRAPHIC ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nGenerated Files:")
    print("  📁 Data:")
    print("     - output/corridor_analysis.csv")
    print("     - output/area_analysis.csv")
    print("     - output/location_heatmap_data.csv")
    print("     - output/locations_for_geocoding.csv (for mapping)")
    print("  📊 Visualizations:")
    print("     - visualizations/geographic_analysis.png")
    print("=" * 80)