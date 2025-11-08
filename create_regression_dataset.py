import pandas as pd
import json
import os

# ============================================================================
# CONFIGURATION
# ============================================================================

AUTHOR_METRICS_FILE = "data/authors_top_field_topic_affiliation_citation.csv"
# OUTPUT_FILE = "regression_dataset.csv"

FIELDS = [
    ("Chemistry", "data/fields/chemistry", "chemistry"),
    ("Materials Science", "data/fields/material_science", "materials_science"),
    ("Engineering", "data/fields/engineering", "engineering"),
    ("Computer Science", "data/fields/computer_science", "computer_science")
]

START_YEAR = 2012
END_YEAR = 2025

# ============================================================================
# EXTRACTION FUNCTIONS
# ============================================================================

def extract_paper_data(raw_data_json):
    """
    Extract first_author_id, last_author_id, num_affiliations, primary_topic in ONE pass.
    """
    if pd.isna(raw_data_json) or raw_data_json == '':
        return None, None, None, None
    
    try:
        data = json.loads(raw_data_json)
        authorships = data.get('authorships', [])
        
        if not authorships:
            return None, None, None, None
        
        # First author
        first_id = authorships[0].get('author', {}).get('id', '')
        first_id = first_id.replace('https://openalex.org/', '') if first_id else None
        
        # Last author
        last_id = authorships[-1].get('author', {}).get('id', '')
        last_id = last_id.replace('https://openalex.org/', '') if last_id else None
        
        # Count unique affiliations
        institutions = set()
        for authorship in authorships:
            for inst in authorship.get('institutions', []):
                inst_id = inst.get('id')
                if inst_id:
                    institutions.add(inst_id)
        
        num_affiliations = len(institutions) if institutions else None
        
        # Get primary topic
        primary_topic = data.get('primary_topic', {})
        topic_name = primary_topic.get('display_name', None) if primary_topic else None
        
        return first_id, last_id, num_affiliations, topic_name
        
    except Exception as e:
        return None, None, None, None


def load_author_metrics(filepath):
    """Load and index author metrics for fast lookup"""
    print(f"📊 Loading author metrics from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"   Loaded {len(df):,} authors")
    
    # Index by author_id for O(1) lookup
    df.set_index('author_id', inplace=True)
    return df


def process_year_field(year, field_name, field_folder, field_prefix, author_metrics):
    """
    Process all papers for one year-field combination.
    Returns DataFrame with all regression variables.
    """
    input_file = os.path.join(field_folder, f"{field_prefix}_{year}.tsv")
    
    if not os.path.exists(input_file):
        return None
    
    print(f"  Reading {field_prefix}_{year}.tsv...")
    
    try:
        # Read file - note your actual column names
        df = pd.read_csv(
            input_file,
            sep='\t',
            encoding='utf-8',
            usecols=['article_id', 'author_count', 'journal', 'publication_year', 
                    'raw_data', 'SDL'],
            on_bad_lines='skip'
        )
        
        print(f"  Loaded {len(df):,} papers")
        
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return None
    
    print(f"  Extracting author data and topic...")
    
    # Extract all data in one vectorized operation
    df[['first_author_id', 'last_author_id', 'num_paper_affiliations', 'primary_topic']] = \
        df['raw_data'].apply(lambda x: pd.Series(extract_paper_data(x)))
    
    # Drop raw_data to free memory
    df.drop('raw_data', axis=1, inplace=True)
    
    print(f"  Merging author metrics...")
    
    # Join with author metrics (FAST with indexed DataFrame)
    df = df.join(
        author_metrics[['total_papers', 'total_citations']],
        on='first_author_id',
        how='left'
    ).rename(columns={
        'total_papers': 'first_author_papers',
        'total_citations': 'first_author_citations'
    })
    
    df = df.join(
        author_metrics[['total_papers', 'total_citations']],
        on='last_author_id',
        how='left',
        rsuffix='_last'
    ).rename(columns={
        'total_papers_last': 'last_author_papers',
        'total_citations_last': 'last_author_citations'
    })
    
    # Add field identifier
    df['field'] = field_name
    
    print(f"  ✅ Processed: {len(df):,} papers")
    
    return df


def create_regression_dataset(author_metrics_file, fields, start_year, end_year, output_file):
    """
    Main pipeline: load author metrics, process all years/fields, combine and save.
    """
    # Load author metrics once
    author_metrics = load_author_metrics(author_metrics_file)
    
    # Process all year-field combinations
    all_dataframes = []
    total_papers = 0
    
    for year in range(start_year, end_year + 1):
        print(f"\n{'─'*70}")
        print(f"📅 Year {year}")
        print('─'*70)
        
        for field_name, folder, prefix in fields:
            df = process_year_field(year, field_name, folder, prefix, author_metrics)
            
            if df is not None:
                all_dataframes.append(df)
                total_papers += len(df)
                print(f"  → {field_name}: {len(df):,} papers")
            else:
                print(f"  → {field_name}: Not found")
        
        print(f"\n  Running total: {total_papers:,} papers")
    
    # Combine all data
    print(f"\n{'='*70}")
    print("📦 Combining all data...")
    print('='*70)
    
    if not all_dataframes:
        print("❌ No data to combine!")
        return None
    
    final_df = pd.concat(all_dataframes, ignore_index=True)
    
    print(f"✅ Combined: {len(final_df):,} papers")
    
    # Save
    print(f"\n💾 Saving to: {output_file}")
    final_df.to_csv(output_file, index=False)
    print(f"✅ Saved successfully")
    
    return final_df


def print_summary(df):
    """Print summary statistics of the dataset"""
    print(f"\n{'='*70}")
    print("📊 DATASET SUMMARY")
    print('='*70)
    
    print(f"\n📄 Total papers: {len(df):,}")
    
    print(f"\n📋 Columns ({len(df.columns)}):")
    for col in df.columns:
        print(f"   • {col}")
    
    print(f"\n🔍 Missing values:")
    missing = df.isnull().sum()
    missing_sorted = missing[missing > 0].sort_values(ascending=False)
    
    if len(missing_sorted) > 0:
        for col, count in missing_sorted.items():
            pct = (count / len(df)) * 100
            print(f"   • {col}: {count:,} ({pct:.1f}%)")
    else:
        print("   ✅ No missing values!")
    
    print(f"\n📈 Continuous variables:")
    stats_cols = ['author_count', 'num_paper_affiliations', 
                  'first_author_papers', 'first_author_citations',
                  'last_author_papers', 'last_author_citations']
    
    # Only include columns that exist
    existing_stats_cols = [col for col in stats_cols if col in df.columns]
    print(df[existing_stats_cols].describe())
    
    print(f"\n📊 Papers by field:")
    print(df['field'].value_counts())
    
    print(f"\n📊 SDL vs Non-SDL:")
    sdl_counts = df['SDL'].value_counts()
    for sdl_status, count in sdl_counts.items():
        label = "SDL" if sdl_status == 1 else "Non-SDL"
        pct = (count / len(df)) * 100
        print(f"   {label}: {count:,} ({pct:.1f}%)")
    
    print(f"\n📊 Top 10 journals:")
    print(df['journal'].value_counts().head(10))
    
    print(f"\n📊 Top 10 topics:")
    print(df['primary_topic'].value_counts().head(10))
    
    print(f"\n{'='*70}")

def sample_rows(csv_file, n=5):
    """Print n random rows from CSV"""
    df = pd.read_csv(csv_file, low_memory=False)


    print(df.sample(n=n))
# ============================================================================
# cleaning DATASET
# ============================================================================

INPUT_FILE = "data/regression/regression_dataset.csv"
OUTPUT_FILE = "data/regression/regression_dataset_clean.csv"

# Cleaning thresholds
MIN_JOURNAL_PAPERS = 10
MIN_TOPIC_PAPERS = 10
TEAM_SIZE_PERCENTILE = 0.99  # Remove top 1% outliers
def clean_regression_data():
    """Quick cleaning without last author requirements"""
    
    print("="*70)
    print("CLEANING REGRESSION DATASET (NO LAST AUTHOR)")
    print("="*70)
    
    # Load
    print(f"\n📂 Loading: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, low_memory=False)
    initial_size = len(df)
    print(f"   Initial: {initial_size:,} rows")
    
    # Filter - only what's needed
    print(f"\n🔍 Filtering...")
    
    mask = (
        df['author_count'].notna() &
        df['journal'].notna() &
        df['num_paper_affiliations'].notna() &
        df['primary_topic'].notna() &
        df['first_author_papers'].notna() &
        df['first_author_citations'].notna()
    )
    
    df = df[mask].copy()
    print(f"   After missing: {len(df):,} rows")
    df['author_count'] = pd.to_numeric(df['author_count'], errors='coerce')
    df = df.dropna(subset=['author_count'])

    # Remove outliers
    cutoff = df['author_count'].quantile(TEAM_SIZE_PERCENTILE)
    df = df[df['author_count'] <= cutoff]
    print(f"   After outliers: {len(df):,} rows")
    
    # Filter journals
    journal_counts = df['journal'].value_counts()
    valid_journals = journal_counts[journal_counts >= MIN_JOURNAL_PAPERS].index
    df = df[df['journal'].isin(valid_journals)]
    print(f"   After journals: {len(df):,} rows")
    
    # Filter topics
    topic_counts = df['primary_topic'].value_counts()
    valid_topics = topic_counts[topic_counts >= MIN_TOPIC_PAPERS].index
    df = df[df['primary_topic'].isin(valid_topics)]
    print(f"   After topics: {len(df):,} rows")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"Final: {len(df):,} rows ({(len(df)/initial_size)*100:.1f}% kept)")
    print(f"Journals: {df['journal'].nunique():,}")
    print(f"Topics: {df['primary_topic'].nunique():,}")
    print(f"{'='*70}")
    
    # Save
    print(f"\n💾 Saving: {OUTPUT_FILE}")
    df.to_csv(OUTPUT_FILE, index=False)
    print("✅ Done!")
    
    return df


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # CSV_FILE = "data/regression/regression_dataset.csv"
    
    # # Option 1: Random sample
    # print("\n" + "="*70)
    # print("OPTION 1: RANDOM SAMPLE")
    # print("="*70)
    # sample_rows(CSV_FILE, n=10)
    # print("="*70)
    # print("CREATING REGRESSION DATASET")
    # print("="*70)
    
    # # Create the dataset
    # df = create_regression_dataset(
    #     AUTHOR_METRICS_FILE,
    #     FIELDS,
    #     START_YEAR,
    #     END_YEAR,
    #     OUTPUT_FILE
    # )
    
    # if df is not None:
        # Print summary
        # print_summary(df)
        
        # print(f"\n{'='*70}")
        # print("✅ COMPLETE!")
        # print(f"💾 File: {OUTPUT_FILE}")
        # print(f"📊 Rows: {len(df):,}")
        # print(f"📋 Columns: {len(df.columns)}")
        # print('='*70)


    # else:
    #     print("\n❌ Failed to create dataset")
        df_clean = clean_regression_data()
