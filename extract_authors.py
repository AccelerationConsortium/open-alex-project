import pandas as pd
import json
import os
import csv
from collections import defaultdict

# =============================================================================
# CONFIGURATION
# =============================================================================
DATA_DIR = "data/fields"
OUTPUT_FILE = "data/authors_top_field_topic.csv"
CHUNK_SIZE = 1000000

FIELDS = {
    'chemistry': 'chemistry',
    'materials_science': 'material_science',
    'engineering': 'engineering',
    'computer_science': 'computer_science'
}

# =============================================================================
# AUTHOR ANALYSIS
# =============================================================================

def analyze_authors():
    """
    Extract all unique authors and calculate their top field and topic
    in a single pass through the data. Most optimized approach.
    """
    print("="*60)
    print("ANALYZING AUTHORS - EXTRACTING AND CALCULATING STATS")
    print("="*60 + "\n")
    
    # Build author stats as we go - no pre-loading needed
    author_stats = defaultdict(lambda: {
        'name': '',
        'field_counts': defaultdict(int), 
        'topic_counts': defaultdict(int)
    })
    
    # Single pass through all TSV files
    for field_name, field_dir in FIELDS.items():
        print(f"Processing {field_name.upper()}...")
        papers_processed = 0
        
        for year in range(2012, 2026):
            file_path = os.path.join(DATA_DIR, field_dir, f"{field_name}_{year}.tsv")
            
            if not os.path.exists(file_path):
                continue
            
            year_papers = 0
            
            try:
                for chunk in pd.read_csv(file_path, sep='\t', 
                                        usecols=['raw_data'],
                                        chunksize=CHUNK_SIZE):
                    
                    for idx in chunk.index:
                        raw_data = chunk.at[idx, 'raw_data']
                        
                        if pd.notna(raw_data):
                            try:
                                data = json.loads(raw_data)
                                
                                # Get topic
                                primary_topic = data.get('primary_topic', {})
                                topic_name = primary_topic.get('display_name', 'Unknown')
                                
                                # Get authors
                                authorships = data.get('authorships', [])
                                
                                for authorship in authorships:
                                    author = authorship.get('author', {})
                                    author_id = author.get('id', '').replace('https://openalex.org/', '')
                                    author_name = author.get('display_name', '')
                                    
                                    if author_id:
                                        # Store name if not stored
                                        if not author_stats[author_id]['name']:
                                            author_stats[author_id]['name'] = author_name
                                        
                                        # Increment counts
                                        author_stats[author_id]['field_counts'][field_name] += 1
                                        if topic_name:
                                            author_stats[author_id]['topic_counts'][topic_name] += 1
                                
                                year_papers += 1
                            except:
                                continue
            except Exception as e:
                print(f"  Error processing {year}: {e}")
                continue
            
            papers_processed += year_papers
            print(f"  {year}: {year_papers:,} papers")
        
        print(f"  {field_name} complete: {papers_processed:,} papers\n")
    
    # Build final dataframe
    print("="*60)
    print("BUILDING FINAL CSV WITH TOP FIELD AND TOPIC")
    print("="*60 + "\n")
    
    rows = []
    for author_id, stats in author_stats.items():
        # Top field
        if stats['field_counts']:
            top_field = max(stats['field_counts'].items(), key=lambda x: x[1])
            top_field_name = top_field[0]
            top_field_count = top_field[1]
        else:
            top_field_name = 'Unknown'
            top_field_count = 0
        
        # Top topic
        if stats['topic_counts']:
            top_topic = max(stats['topic_counts'].items(), key=lambda x: x[1])
            top_topic_name = top_topic[0]
            top_topic_count = top_topic[1]
        else:
            top_topic_name = 'Unknown'
            top_topic_count = 0
        
        # Total papers
        total_papers = sum(stats['field_counts'].values())
        
        rows.append({
            'author_id': author_id,
            'author_name': stats['name'],
            'total_papers': total_papers,
            'top_field': top_field_name,
            'top_field_paper_count': top_field_count,
            'top_topic': top_topic_name,
            'top_topic_paper_count': top_topic_count
        })
    
    # Create dataframe and sort by total papers
    authors_df = pd.DataFrame(rows)
    authors_df = authors_df.sort_values('total_papers', ascending=False)
    
    # Save
    print("="*60)
    print("SAVING TO CSV")
    print("="*60 + "\n")
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    authors_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(authors_df):,} authors to {OUTPUT_FILE}\n")
    
    # Sample
    print("Sample of top authors:")
    print(authors_df.head(10).to_string(index=False))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total unique authors: {len(authors_df):,}")
    
    field_counts = authors_df['top_field'].value_counts()
    print("\nAuthors by top field:")
    for field, count in field_counts.items():
        print(f"  {field}: {count:,}")
    
    avg_papers = authors_df['total_papers'].mean()
    print(f"\nAverage papers per author: {avg_papers:.2f}")
    print("="*60 + "\n")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    analyze_authors()
    print("✓ Analysis complete!")