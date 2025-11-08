"""
Code to extract and restructure author data.
Trying to get number of affiliations (institutions linked to) for each author
"""
import pandas as pd
import json
import os
from collections import defaultdict

# Configuration
DATA_DIRS = {
    'chemistry': '../data/fields/chemistry',
    'materials_science': '../data/fields/material_science',
    'engineering': '../data/fields/engineering',
    'computer_science': '../data/fields/computer_science'
}
OUTPUT_FILE = '../data/author_affiliations.csv'
EDA_OUTPUT_FILE = '../data/author_affiliations_eda.csv'
YEARS = range(2012, 2026)
CHUNK_SIZE = 500000

def extract_author_affiliations():
    """Extract unique affiliation count for each author across all fields"""
    
    print("\n" + "="*70)
    print("EXTRACTING AUTHOR AFFILIATIONS")
    print("="*70 + "\n")
    
    author_data = defaultdict(lambda: {'name': None, 'institutions': set()})
    
    for field_name, directory in DATA_DIRS.items():
        print(f"Processing {field_name}...")
        
        for year in YEARS:
            if field_name == 'materials_science':
                filename = f"materials_science_{year}.tsv"
            else:
                filename = f"{field_name}_{year}.tsv"
            
            file_path = os.path.join(directory, filename)
            
            if not os.path.exists(file_path):
                continue
            
            for chunk in pd.read_csv(file_path, sep='\t', usecols=['raw_data'], 
                                    chunksize=CHUNK_SIZE):
                
                for idx in chunk.index:
                    raw_data = chunk.at[idx, 'raw_data']
                    
                    if pd.isna(raw_data):
                        continue
                    
                    try:
                        paper_data = json.loads(raw_data)
                        authorships = paper_data.get('authorships', [])
                        
                        for authorship in authorships:
                            author = authorship.get('author', {})
                            author_id = author.get('id', '').replace('https://openalex.org/', '')
                            
                            if not author_id:
                                continue
                            
                            if author_data[author_id]['name'] is None:
                                author_data[author_id]['name'] = author.get('display_name', 'Unknown')
                            
                            institutions = authorship.get('institutions', [])
                            for inst in institutions:
                                inst_id = inst.get('id', '').replace('https://openalex.org/', '')
                                if inst_id:
                                    author_data[author_id]['institutions'].add(inst_id)
                    
                    except:
                        continue
            
            print(f"  {year} complete")
    
    print(f"\nUnique authors found: {len(author_data):,}")
    print("Converting to DataFrame...")
    
    authors_list = []
    for author_id, data in author_data.items():
        authors_list.append({
            'author_id': author_id,
            'author_name': data['name'],
            'affiliation_count': len(data['institutions'])
        })
    
    df = pd.DataFrame(authors_list)
    df = df.sort_values('affiliation_count', ascending=False)
    
    print(f"Saving to {OUTPUT_FILE}...")
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Total authors saved: {len(df):,}\n")
    
    return df

def analyze_author_affiliations(csv_file):
    """Perform EDA on author affiliation data from CSV file"""
    
    print("\n" + "="*70)
    print("AUTHOR AFFILIATION EDA")
    print("="*70 + "\n")
    
    print(f"Loading data from {csv_file}...")
    df = pd.read_csv(csv_file)
    
    # Basic statistics
    print("\nBasic Statistics:")
    print(f"  Total authors: {len(df):,}")
    print(f"  Mean affiliations: {df['affiliation_count'].mean():.2f}")
    print(f"  Median affiliations: {df['affiliation_count'].median():.0f}")
    print(f"  Std deviation: {df['affiliation_count'].std():.2f}")
    print(f"  Min affiliations: {df['affiliation_count'].min()}")
    print(f"  Max affiliations: {df['affiliation_count'].max()}")
    
    # Distribution
    print(f"\nAffiliation Distribution:")
    print(f"  1 affiliation: {(df['affiliation_count'] == 1).sum():,} ({(df['affiliation_count'] == 1).sum()/len(df)*100:.1f}%)")
    print(f"  2-5 affiliations: {((df['affiliation_count'] >= 2) & (df['affiliation_count'] <= 5)).sum():,} ({((df['affiliation_count'] >= 2) & (df['affiliation_count'] <= 5)).sum()/len(df)*100:.1f}%)")
    print(f"  6-10 affiliations: {((df['affiliation_count'] >= 6) & (df['affiliation_count'] <= 10)).sum():,} ({((df['affiliation_count'] >= 6) & (df['affiliation_count'] <= 10)).sum()/len(df)*100:.1f}%)")
    print(f"  >10 affiliations: {(df['affiliation_count'] > 10).sum():,} ({(df['affiliation_count'] > 10).sum()/len(df)*100:.1f}%)")
    
    # Percentiles
    print(f"\nPercentiles:")
    for p in [25, 50, 75, 90, 95, 99]:
        print(f"  {p}th percentile: {df['affiliation_count'].quantile(p/100):.0f}")
    
    # Create EDA summary dataframe with examples
    eda_results = []
    
    # Top 20 authors
    top_20 = df.head(20).copy()
    top_20['category'] = 'top_20'
    eda_results.append(top_20)
    
    # Outliers (>99th percentile)
    threshold = df['affiliation_count'].quantile(0.99)
    outliers = df[df['affiliation_count'] > threshold].copy()
    outliers['category'] = 'outlier'
    eda_results.append(outliers)
    
    # Median examples (around 50th percentile)
    median_val = df['affiliation_count'].median()
    median_examples = df[df['affiliation_count'] == median_val].head(10).copy()
    median_examples['category'] = 'median_example'
    eda_results.append(median_examples)
    
    # Random sample from middle range (25th-75th percentile)
    q25 = df['affiliation_count'].quantile(0.25)
    q75 = df['affiliation_count'].quantile(0.75)
    middle_range = df[(df['affiliation_count'] >= q25) & (df['affiliation_count'] <= q75)]
    random_middle = middle_range.sample(n=min(20, len(middle_range)), random_state=42).copy()
    random_middle['category'] = 'random_middle'
    eda_results.append(random_middle)
    
    # Single affiliation examples
    single_aff = df[df['affiliation_count'] == 1].head(10).copy()
    single_aff['category'] = 'single_affiliation'
    eda_results.append(single_aff)
    
    # Combine all
    eda_df = pd.concat(eda_results, ignore_index=True)
    
    # Add summary statistics as separate rows
    summary_stats = pd.DataFrame({
        'author_id': ['STAT', 'STAT', 'STAT', 'STAT', 'STAT', 'STAT'],
        'author_name': ['Total Authors', 'Mean', 'Median', 'Std Dev', 'Min', 'Max'],
        'affiliation_count': [len(df), df['affiliation_count'].mean(), df['affiliation_count'].median(),
                              df['affiliation_count'].std(), df['affiliation_count'].min(), df['affiliation_count'].max()],
        'category': ['summary', 'summary', 'summary', 'summary', 'summary', 'summary']
    })
    
    eda_df = pd.concat([summary_stats, eda_df], ignore_index=True)
    
    print(f"\nSaving EDA results to {EDA_OUTPUT_FILE}...")
    eda_df.to_csv(EDA_OUTPUT_FILE, index=False)
    
    print(f"\nEDA Summary:")
    print(f"  Top 20 authors: {len(top_20)}")
    print(f"  Outliers (>{threshold:.0f} affiliations): {len(outliers)}")
    print(f"  Median examples: {len(median_examples)}")
    print(f"  Random middle samples: {len(random_middle)}")
    print(f"  Single affiliation examples: {len(single_aff)}")
    print(f"  Total rows in EDA file: {len(eda_df)}")
    print("\nEDA complete\n")

if __name__ == "__main__":
    # df = extract_author_affiliations()
    # file_path = '../data/fields/chemistry/chemistry_2012.tsv'
    # chunk = pd.read_csv(file_path, sep='\t', nrows=1)
    # print(chunk.columns.tolist())
    analyze_author_affiliations(OUTPUT_FILE)
