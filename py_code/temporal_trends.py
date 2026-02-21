"""
Analyze temporal patterns of SDL/AI/Robotics research adoption (2004-2025)
Goal: Identify when research picked up to determine optimal analysis start year
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")
DATA_FILE = PROJECT_DIR / "data" / "yearly_data/test" / "regression_dataset_3yr_rolling.csv"
OUTPUT_DIR = PROJECT_DIR / "data" / "temporal_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Set plot style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# ============================================================================
# LOAD DATA
# ============================================================================

print("Loading data...")
df = pd.read_csv(DATA_FILE, low_memory=False)
print(f"Total papers: {len(df):,}")
print(f"Year range: {df['publication_year'].min()}-{df['publication_year'].max()}")

# ============================================================================
# 1. ANNUAL COUNTS (MAIN FIGURE - LIKE FIGURE 1)
# ============================================================================

print("\n" + "="*80)
print("CREATING TEMPORAL TREND FIGURES")
print("="*80)

# Aggregate by year
yearly_counts = df.groupby('publication_year').agg({
    'article_id': 'count',
    'SDL_Brown': 'sum',
    'SDL_Tomet': 'sum',
    'SDL_Filtered_Tom': 'sum',
    'sdl_keyword_measure': 'sum',
    'high_automation': 'sum',
    'AI_Paper': 'sum',
    'Robotics_Paper': 'sum'
}).reset_index()

yearly_counts.columns = ['Year', 'Total', 'SDL_Brown', 'SDL_Tomet', 
                         'SDL_Filtered_Tom', 'SDL_Keyword', 'High_Auto',
                         'AI', 'Robotics']

# Calculate union SDL
yearly_counts['SDL_Any'] = yearly_counts[['SDL_Brown', 'SDL_Tomet']].max(axis=1)

# Save summary
yearly_counts.to_csv(OUTPUT_DIR / "yearly_counts.csv", index=False)
print(f"\n✓ Saved yearly counts to: {OUTPUT_DIR / 'yearly_counts.csv'}")

# ============================================================================
# FIGURE 1: ABSOLUTE COUNTS (Extended from 2004) - SIMPLIFIED
# ============================================================================

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# Panel A: SDL measures (ONLY Brown and Tomet)
ax1.plot(yearly_counts['Year'], yearly_counts['SDL_Tomet'], 
         marker='s', linewidth=2, label='SDL Tomet', color='#3498db')
ax1.plot(yearly_counts['Year'], yearly_counts['SDL_Brown'], 
         marker='^', linewidth=2, label='SDL Brown', color='#9b59b6')

ax1.axvline(x=2007, color='gray', linestyle='--', alpha=0.5, label='2007 (First full 3yr window)')
ax1.axvline(x=2012, color='gray', linestyle=':', alpha=0.5, label='2012 (Original start)')
ax1.set_xlabel('Publication Year', fontsize=12)
ax1.set_ylabel('Number of Papers', fontsize=12)
ax1.set_title('Panel A: SDL Research Over Time (2004-2025)', fontsize=14, fontweight='bold')
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)

# Panel B: AI and Robotics
ax2.plot(yearly_counts['Year'], yearly_counts['AI'], 
         marker='o', linewidth=2, label='AI Papers', color='#2ecc71')
ax2.plot(yearly_counts['Year'], yearly_counts['Robotics'], 
         marker='s', linewidth=2, label='Robotics Papers', color='#e67e22')

ax2.axvline(x=2007, color='gray', linestyle='--', alpha=0.5, label='2007 (First full 3yr window)')
ax2.axvline(x=2012, color='gray', linestyle=':', alpha=0.5, label='2012 (Original start)')
ax2.set_xlabel('Publication Year', fontsize=12)
ax2.set_ylabel('Number of Papers', fontsize=12)
ax2.set_title('Panel B: AI and Robotics Research Over Time (2004-2025)', fontsize=14, fontweight='bold')
ax2.legend(loc='upper left', fontsize=10)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'figure1_extended_absolute_counts.png', dpi=300, bbox_inches='tight')
plt.close()

print(f"✓ Saved Figure 1 (Absolute Counts): {OUTPUT_DIR / 'figure1_extended_absolute_counts.png'}")

# ============================================================================
# FIGURE 2: SHARES/PERCENTAGES (Relative to total)
# ============================================================================

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# Calculate shares
yearly_counts['SDL_Share'] = (yearly_counts['SDL_Any'] / yearly_counts['Total']) * 100
yearly_counts['SDL_Tomet_Share'] = (yearly_counts['SDL_Tomet'] / yearly_counts['Total']) * 100
yearly_counts['SDL_Brown_Share'] = (yearly_counts['SDL_Brown'] / yearly_counts['Total']) * 100
yearly_counts['AI_Share'] = (yearly_counts['AI'] / yearly_counts['Total']) * 100
yearly_counts['Robotics_Share'] = (yearly_counts['Robotics'] / yearly_counts['Total']) * 100

# Panel A: SDL shares
ax1.plot(yearly_counts['Year'], yearly_counts['SDL_Share'], 
         marker='o', linewidth=2, label='SDL (Any)', color='#e74c3c')
ax1.plot(yearly_counts['Year'], yearly_counts['SDL_Tomet_Share'], 
         marker='s', linewidth=1.5, label='SDL Tomet', color='#3498db', alpha=0.7)
ax1.plot(yearly_counts['Year'], yearly_counts['SDL_Brown_Share'], 
         marker='^', linewidth=1.5, label='SDL Brown', color='#9b59b6', alpha=0.7)

ax1.axvline(x=2007, color='gray', linestyle='--', alpha=0.5)
ax1.axvline(x=2012, color='gray', linestyle=':', alpha=0.5)
ax1.set_xlabel('Publication Year', fontsize=12)
ax1.set_ylabel('Percentage of Total Papers (%)', fontsize=12)
ax1.set_title('Panel A: SDL Research Share Over Time', fontsize=14, fontweight='bold')
ax1.legend(loc='upper left', fontsize=9)
ax1.grid(True, alpha=0.3)

# Panel B: AI/Robotics shares
ax2.plot(yearly_counts['Year'], yearly_counts['AI_Share'], 
         marker='o', linewidth=2, label='AI Papers', color='#2ecc71')
ax2.plot(yearly_counts['Year'], yearly_counts['Robotics_Share'], 
         marker='s', linewidth=2, label='Robotics Papers', color='#e67e22')

ax2.axvline(x=2007, color='gray', linestyle='--', alpha=0.5)
ax2.axvline(x=2012, color='gray', linestyle=':', alpha=0.5)
ax2.set_xlabel('Publication Year', fontsize=12)
ax2.set_ylabel('Percentage of Total Papers (%)', fontsize=12)
ax2.set_title('Panel B: AI and Robotics Share Over Time', fontsize=14, fontweight='bold')
ax2.legend(loc='upper left', fontsize=9)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'figure2_shares_over_time.png', dpi=300, bbox_inches='tight')
plt.close()

print(f"✓ Saved Figure 2 (Shares): {OUTPUT_DIR / 'figure2_shares_over_time.png'}")

# ============================================================================
# FIGURE 3: YEAR-OVER-YEAR GROWTH RATES (S-CURVE IDENTIFICATION)
# ============================================================================

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# Calculate year-over-year percent change
yearly_counts['SDL_YoY'] = yearly_counts['SDL_Any'].pct_change() * 100
yearly_counts['AI_YoY'] = yearly_counts['AI'].pct_change() * 100
yearly_counts['Robotics_YoY'] = yearly_counts['Robotics'].pct_change() * 100

# Panel A: SDL growth rate
ax1.bar(yearly_counts['Year'], yearly_counts['SDL_YoY'], 
        color='#e74c3c', alpha=0.7, label='SDL YoY Growth (%)')
ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax1.axvline(x=2007, color='gray', linestyle='--', alpha=0.5)
ax1.axvline(x=2012, color='gray', linestyle=':', alpha=0.5)
ax1.set_xlabel('Publication Year', fontsize=12)
ax1.set_ylabel('Year-over-Year Growth (%)', fontsize=12)
ax1.set_title('Panel A: SDL Paper Growth Rate (Identifying Inflection Points)', 
              fontsize=14, fontweight='bold')
ax1.legend(fontsize=9)
ax1.grid(True, alpha=0.3, axis='y')

# Panel B: AI/Robotics growth rates
width = 0.35
years = yearly_counts['Year'].values
x = np.arange(len(years))

ax2.bar(x - width/2, yearly_counts['AI_YoY'], width, 
        label='AI YoY Growth', color='#2ecc71', alpha=0.7)
ax2.bar(x + width/2, yearly_counts['Robotics_YoY'], width,
        label='Robotics YoY Growth', color='#e67e22', alpha=0.7)

ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax2.set_xlabel('Publication Year', fontsize=12)
ax2.set_ylabel('Year-over-Year Growth (%)', fontsize=12)
ax2.set_title('Panel B: AI and Robotics Growth Rates', fontsize=14, fontweight='bold')
ax2.set_xticks(x[::2])  # Show every other year
ax2.set_xticklabels(years[::2], rotation=45)
ax2.legend(fontsize=9)
ax2.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'figure3_growth_rates.png', dpi=300, bbox_inches='tight')
plt.close()

print(f"✓ Saved Figure 3 (Growth Rates): {OUTPUT_DIR / 'figure3_growth_rates.png'}")

# ============================================================================
# FIGURE 4: CUMULATIVE COUNTS (S-CURVE VISUALIZATION)
# ============================================================================

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Calculate cumulative counts
yearly_counts['SDL_Cumulative'] = yearly_counts['SDL_Any'].cumsum()
yearly_counts['AI_Cumulative'] = yearly_counts['AI'].cumsum()
yearly_counts['Robotics_Cumulative'] = yearly_counts['Robotics'].cumsum()

# Panel A: SDL
ax1.plot(yearly_counts['Year'], yearly_counts['SDL_Cumulative'], 
         marker='o', linewidth=2.5, color='#e74c3c')
ax1.axvline(x=2007, color='gray', linestyle='--', alpha=0.5, label='2007')
ax1.axvline(x=2012, color='gray', linestyle=':', alpha=0.5, label='2012')
ax1.set_xlabel('Publication Year', fontsize=12)
ax1.set_ylabel('Cumulative Papers', fontsize=12)
ax1.set_title('Panel A: Cumulative SDL Papers (S-Curve)', fontsize=14, fontweight='bold')
ax1.legend(fontsize=9)
ax1.grid(True, alpha=0.3)

# Panel B: AI and Robotics
ax2.plot(yearly_counts['Year'], yearly_counts['AI_Cumulative'], 
         marker='o', linewidth=2.5, color='#2ecc71', label='AI (Cumulative)')
ax2.plot(yearly_counts['Year'], yearly_counts['Robotics_Cumulative'], 
         marker='s', linewidth=2.5, color='#e67e22', label='Robotics (Cumulative)')
ax2.axvline(x=2007, color='gray', linestyle='--', alpha=0.5)
ax2.axvline(x=2012, color='gray', linestyle=':', alpha=0.5)
ax2.set_xlabel('Publication Year', fontsize=12)
ax2.set_ylabel('Cumulative Papers', fontsize=12)
ax2.set_title('Panel B: Cumulative AI and Robotics Papers', fontsize=14, fontweight='bold')
ax2.legend(fontsize=9)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'figure4_cumulative_scurve.png', dpi=300, bbox_inches='tight')
plt.close()

print(f"✓ Saved Figure 4 (S-Curves): {OUTPUT_DIR / 'figure4_cumulative_scurve.png'}")

# ============================================================================
# STATISTICAL ANALYSIS: IDENTIFY INFLECTION POINTS
# ============================================================================

print("\n" + "="*80)
print("STATISTICAL ANALYSIS: INFLECTION POINT DETECTION")
print("="*80)

def detect_inflection(years, values, technology_name):
    """Detect inflection point using second derivative"""
    
    # Calculate first and second derivatives
    first_deriv = np.gradient(values)
    second_deriv = np.gradient(first_deriv)
    
    # Find year where second derivative is maximum (steepest acceleration)
    inflection_idx = np.argmax(second_deriv)
    inflection_year = years.iloc[inflection_idx]
    
    # Calculate average growth before and after inflection
    before_mask = years < inflection_year
    after_mask = years >= inflection_year
    
    avg_before = values[before_mask].mean() if before_mask.sum() > 0 else 0
    avg_after = values[after_mask].mean() if after_mask.sum() > 0 else 0
    
    return {
        'technology': technology_name,
        'inflection_year': inflection_year,
        'avg_count_before': avg_before,
        'avg_count_after': avg_after,
        'growth_rate_change': avg_after - avg_before
    }

# Analyze each technology
results = []
results.append(detect_inflection(yearly_counts['Year'], yearly_counts['SDL_Any'], 'SDL'))
results.append(detect_inflection(yearly_counts['Year'], yearly_counts['AI'], 'AI'))
results.append(detect_inflection(yearly_counts['Year'], yearly_counts['Robotics'], 'Robotics'))

inflection_df = pd.DataFrame(results)
inflection_df.to_csv(OUTPUT_DIR / 'inflection_points.csv', index=False)

print("\nInflection Point Analysis:")
print(inflection_df.to_string(index=False))

# ============================================================================
# PERIOD COMPARISON: 2004-2007 vs 2008-2012 vs 2013-2025
# ============================================================================

print("\n" + "="*80)
print("PERIOD COMPARISON ANALYSIS")
print("="*80)

periods = {
    'Very Early (2004-2007)': (2004, 2007),
    'Early (2008-2012)': (2008, 2012),
    'Growth (2013-2018)': (2013, 2018),
    'Recent (2019-2025)': (2019, 2025)
}

period_stats = []

for period_name, (start, end) in periods.items():
    period_data = yearly_counts[(yearly_counts['Year'] >= start) & (yearly_counts['Year'] <= end)]
    
    period_stats.append({
        'Period': period_name,
        'Years': f"{start}-{end}",
        'Avg_SDL': period_data['SDL_Any'].mean(),
        'Avg_AI': period_data['AI'].mean(),
        'Avg_Robotics': period_data['Robotics'].mean(),
        'Total_Papers': period_data['Total'].sum(),
        'SDL_Share_%': (period_data['SDL_Any'].sum() / period_data['Total'].sum()) * 100,
        'AI_Share_%': (period_data['AI'].sum() / period_data['Total'].sum()) * 100,
        'Robotics_Share_%': (period_data['Robotics'].sum() / period_data['Total'].sum()) * 100
    })

period_comparison = pd.DataFrame(period_stats)
period_comparison.to_csv(OUTPUT_DIR / 'period_comparison.csv', index=False)

print("\nPeriod Comparison:")
print(period_comparison.to_string(index=False))

# ============================================================================
# SUMMARY REPORT
# ============================================================================

print("\n" + "="*80)
print("GENERATING SUMMARY REPORT")
print("="*80)

with open(OUTPUT_DIR / 'summary_report.txt', 'w') as f:
    f.write("="*80 + "\n")
    f.write("TEMPORAL ANALYSIS SUMMARY: SDL/AI/ROBOTICS ADOPTION (2004-2025)\n")
    f.write("="*80 + "\n\n")
    
    f.write("RESEARCH QUESTION:\n")
    f.write("When did SDL/AI/Robotics research pick up? Where on the S-curve are we?\n\n")
    
    f.write("="*80 + "\n")
    f.write("KEY FINDINGS:\n")
    f.write("="*80 + "\n\n")
    
    f.write("1. PRE-PERIOD (2004-2012):\n")
    pre_2012 = yearly_counts[yearly_counts['Year'] <= 2012]
    f.write(f"   - Average SDL papers/year: {pre_2012['SDL_Any'].mean():.1f}\n")
    f.write(f"   - Average AI papers/year: {pre_2012['AI'].mean():.1f}\n")
    f.write(f"   - Average Robotics papers/year: {pre_2012['Robotics'].mean():.1f}\n")
    f.write(f"   - SDL Share: {(pre_2012['SDL_Any'].sum() / pre_2012['Total'].sum())*100:.3f}%\n\n")
    
    f.write("2. INFLECTION POINTS (Maximum Acceleration):\n")
    for _, row in inflection_df.iterrows():
        f.write(f"   - {row['technology']}: {int(row['inflection_year'])}\n")
    f.write("\n")
    
    f.write("3. RECENT PERIOD (2019-2025):\n")
    recent = yearly_counts[yearly_counts['Year'] >= 2019]
    f.write(f"   - Average SDL papers/year: {recent['SDL_Any'].mean():.1f}\n")
    f.write(f"   - Average AI papers/year: {recent['AI'].mean():.1f}\n")
    f.write(f"   - Average Robotics papers/year: {recent['Robotics'].mean():.1f}\n")
    f.write(f"   - SDL Share: {(recent['SDL_Any'].sum() / recent['Total'].sum())*100:.3f}%\n\n")
    
    f.write("="*80 + "\n")
    f.write("RECOMMENDATIONS FOR ANALYSIS START YEAR:\n")
    f.write("="*80 + "\n\n")
    
    # Calculate early period flatness
    very_early = yearly_counts[yearly_counts['Year'] <= 2007]
    early_std = very_early['SDL_Any'].std()
    
    f.write(f"Option 1: Start in 2007 (First year with full 3-year backward window)\n")
    f.write(f"   - Pro: Maximum data retention\n")
    f.write(f"   - Pro: Captures very flat pre-period (SDL std dev 2004-2007: {early_std:.2f})\n")
    f.write(f"   - Con: 2004 has no backward-looking data (0 prior years)\n\n")
    
    f.write(f"Option 2: Start in 2010 (Suggested by professors)\n")
    f.write(f"   - Pro: All years have at least some backward-looking data\n")
    f.write(f"   - Pro: Still captures pre-takeoff period\n")
    f.write(f"   - Con: Loses 2004-2009 observations\n\n")
    
    f.write("="*80 + "\n")
    f.write("PERIOD COMPARISON TABLE:\n")
    f.write("="*80 + "\n\n")
    f.write(period_comparison.to_string(index=False))
    f.write("\n\n")
    
    f.write("="*80 + "\n")
    f.write("FILES GENERATED:\n")
    f.write("="*80 + "\n")
    f.write("1. figure1_extended_absolute_counts.png - Main temporal trends (like Figure 1)\n")
    f.write("2. figure2_shares_over_time.png - Percentage shares over time\n")
    f.write("3. figure3_growth_rates.png - Year-over-year growth rates\n")
    f.write("4. figure4_cumulative_scurve.png - S-curve visualization\n")
    f.write("5. yearly_counts.csv - Raw data by year\n")
    f.write("6. inflection_points.csv - Statistical inflection analysis\n")
    f.write("7. period_comparison.csv - Period-by-period comparison\n")

print(f"\n✓ Saved summary report: {OUTPUT_DIR / 'summary_report.txt'}")

print("\n" + "="*80)
print("ANALYSIS COMPLETE!")
print("="*80)
print(f"\nAll outputs saved to: {OUTPUT_DIR}")
print("\nKey files to share with professors:")
print("  1. figure1_extended_absolute_counts.png (Main result)")
print("  2. summary_report.txt (Written summary)")