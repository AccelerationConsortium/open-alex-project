# """
# Build Author Diversity Profiles - ALL AUTHORS
# For all authors in the 490K filtered regression dataset, extract field/topic/journal distributions
# and CS experience based on the comp_sci_experience_paper variable.
# """

# import pandas as pd
# import json
# from pathlib import Path
# from collections import defaultdict, Counter

# # ============================================
# # CONFIGURATION
# # ============================================
# PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# # Input file - USE FILTERED DATASET
# REGRESSION_DATA = PROJECT_DIR / "data" / "regression/test" / "regression_dataset_filtered.csv"

# # Output file
# OUTPUT_FILE = PROJECT_DIR / "data" / "author/test" / "all_authors_diversity.csv"

# # Chunk size for reading
# CHUNK_SIZE = 500000

# # ============================================
# # BUILD AUTHOR PROFILES
# # ============================================

# def build_author_profiles():
#     """
#     Build author profiles from filtered regression dataset.
#     For ALL authors (first, last, corresponding), track counts of fields, topics, and journals.
    
#     CS Experience: Author has CS experience if they authored 1+ papers where comp_sci_experience_paper = 1
#     """
#     print("\n" + "="*60)
#     print("BUILDING AUTHOR PROFILES (ALL AUTHORS)")
#     print("="*60)
#     print("Dataset: Pre-filtered 490K (SDL venue matched)")
#     print("CS Experience Logic: 1+ papers with CS keywords")
    
#     # Dictionary to store author profiles
#     author_profiles = defaultdict(lambda: {
#         'fields': Counter(),
#         'topics': Counter(),
#         'journals': Counter(),
#         'has_cs_experience': False
#     })
    
#     total_papers = 0
#     valid_papers = 0
    
#     print("\nProcessing chunks...")
    
#     for chunk_num, chunk in enumerate(pd.read_csv(
#         REGRESSION_DATA,
#         sep=',',
#         chunksize=CHUNK_SIZE,
#         usecols=['journal', 'primary_topic', 'first_author_id', 'last_author_id', 
#                 'corresponding_author_id', 'field', 'author_count', 'publication_year', 
#                 'comp_sci_experience_paper']
#     ), start=1):
        
#         total_papers += len(chunk)
        
#         # Remove papers with missing critical values
#         chunk = chunk.dropna(subset=['author_count', 'publication_year', 'field'])
#         valid_papers += len(chunk)
        
#         # Process each paper
#         for _, row in chunk.iterrows():
#             # Collect ALL author IDs for this paper
#             author_ids = []
            
#             if pd.notna(row['last_author_id']):
#                 author_ids.append(row['last_author_id'])
                
#             if pd.notna(row['first_author_id']):
#                 author_ids.append(row['first_author_id'])

#             if pd.notna(row['corresponding_author_id']):
#                 author_ids.append(row['corresponding_author_id'])

#             # Skip if no authors
#             if not author_ids:
#                 continue
            
#             # Update profile for each author
#             for author_id in author_ids:
#                 # Update field, topic, journal counts
#                 if pd.notna(row['field']):
#                     author_profiles[author_id]['fields'][row['field']] += 1
                
#                 if pd.notna(row['primary_topic']):
#                     author_profiles[author_id]['topics'][row['primary_topic']] += 1
                
#                 if pd.notna(row['journal']):
#                     author_profiles[author_id]['journals'][row['journal']] += 1
                
#                 # Update CS experience
#                 if row['comp_sci_experience_paper'] == 1:
#                     author_profiles[author_id]['has_cs_experience'] = True
        
#         # Progress update
#         if chunk_num % 5 == 0:
#             print(f"  Chunk {chunk_num}: {valid_papers:,} papers processed, {len(author_profiles):,} unique authors...")
    
#     print(f"\n✓ Finished processing")
#     print(f"  Total papers in dataset: {total_papers:,}")
#     print(f"  Papers with valid data: {valid_papers:,}")
#     print(f"  Unique authors: {len(author_profiles):,}")
    
#     return author_profiles

# # ============================================
# # SAVE RESULTS
# # ============================================

# def save_author_profiles(author_profiles):
#     """Convert author profiles to DataFrame and save."""
#     print("\n" + "="*60)
#     print("SAVING AUTHOR PROFILES")
#     print("="*60)
    
#     results = []
    
#     for author_id, profile in author_profiles.items():
#         # Calculate totals
#         total_papers = sum(profile['fields'].values())
        
#         # Get top field, topic, and journal (most common)
#         top_field = profile['fields'].most_common(1)[0][0] if profile['fields'] else None
#         top_topic = profile['topics'].most_common(1)[0][0] if profile['topics'] else None
#         top_journal = profile['journals'].most_common(1)[0][0] if profile['journals'] else None
        
#         # Convert counters to JSON strings
#         result = {
#             'author_id': author_id,
#             'total_papers': total_papers,
#             'top_field': top_field,
#             'top_topic': top_topic,
#             'top_journal': top_journal,
#             'has_cs_experience': int(profile['has_cs_experience']),
#             'field_counts': json.dumps(dict(profile['fields'])),
#             'topic_counts': json.dumps(dict(profile['topics'])),
#             'journal_counts': json.dumps(dict(profile['journals'])),
#             'num_unique_fields': len(profile['fields']),
#             'num_unique_topics': len(profile['topics']),
#             'num_unique_journals': len(profile['journals'])
#         }
#         results.append(result)
    
#     # Create DataFrame
#     df = pd.DataFrame(results)
    
#     # Sort by total papers (descending)
#     df = df.sort_values('total_papers', ascending=False)
    
#     # Save to CSV
#     df.to_csv(OUTPUT_FILE, index=False)
    
#     print(f"✓ Saved {len(df):,} author profiles to {OUTPUT_FILE}")
    
#     # Print summary statistics
#     print("\n" + "="*60)
#     print("SUMMARY STATISTICS")
#     print("="*60)
#     print(f"Total authors: {len(df):,}")
#     print(f"\nPapers per author:")
#     print(f"  Mean: {df['total_papers'].mean():.1f}")
#     print(f"  Median: {df['total_papers'].median():.0f}")
#     print(f"  Min: {df['total_papers'].min()}")
#     print(f"  Max: {df['total_papers'].max()}")
    
#     print(f"\nCS Experience:")
#     cs_count = df['has_cs_experience'].sum()
#     print(f"  Authors with CS experience: {cs_count:,} ({cs_count/len(df)*100:.2f}%)")
#     print(f"  Authors without CS experience: {len(df)-cs_count:,} ({(len(df)-cs_count)/len(df)*100:.2f}%)")
    
#     print(f"\nField diversity:")
#     print(f"  Mean unique fields: {df['num_unique_fields'].mean():.2f}")
#     print(f"  Max unique fields: {df['num_unique_fields'].max()}")
    
#     print(f"\nTopic diversity:")
#     print(f"  Mean unique topics: {df['num_unique_topics'].mean():.1f}")
#     print(f"  Max unique topics: {df['num_unique_topics'].max()}")
    
#     print(f"\nJournal diversity:")
#     print(f"  Mean unique journals: {df['num_unique_journals'].mean():.1f}")
#     print(f"  Max unique journals: {df['num_unique_journals'].max()}")
    
#     print("="*60)

# # ============================================
# # MAIN
# # ============================================

# def main():
#     print("="*60)
#     print("BUILDING AUTHOR DIVERSITY PROFILES - ALL AUTHORS")
#     print("="*60)
    
#     # Check if input file exists
#     if not Path(REGRESSION_DATA).exists():
#         print(f"\n❌ ERROR: Regression dataset not found at {REGRESSION_DATA}")
#         return
    
#     print(f"\n📂 Reading from: {REGRESSION_DATA}")
#     print(f"📝 Output to: {OUTPUT_FILE}")
    
#     # Build author profiles
#     author_profiles = build_author_profiles()
    
#     # Save results
#     save_author_profiles(author_profiles)
    
#     print(f"\n✅ Complete! Output saved to: {OUTPUT_FILE}")

# if __name__ == "__main__":
#     main()


"""
Perform EDA on author diversity dataset and save to text file
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# Toggle between all authors and last authors
INPUT_FILE = PROJECT_DIR / "data" / "author/test" / "all_authors_diversity.csv"
# INPUT_FILE = PROJECT_DIR / "data" / "author/test" / "last_authors_diversity.csv"

OUTPUT_FILE = INPUT_FILE.parent / f"{INPUT_FILE.stem}_eda.txt"

# ============================================================================
# MAIN EDA FUNCTION
# ============================================================================

def run_eda():
    """Run comprehensive EDA and save to file"""
    
    print(f"Loading data from: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)
    
    print(f"Saving EDA report to: {OUTPUT_FILE}\n")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        
        # Header
        f.write("="*80 + "\n")
        f.write("EXPLORATORY DATA ANALYSIS - AUTHOR DIVERSITY DATASET\n")
        f.write("="*80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Source file: {INPUT_FILE}\n")
        f.write("="*80 + "\n\n")
        
        # ====================================================================
        # 1. DATASET OVERVIEW
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("1. DATASET OVERVIEW\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Total authors: {len(df):,}\n")
        f.write(f"Total columns: {len(df.columns)}\n")
        f.write(f"Memory usage: {df.memory_usage(deep=True).sum() / 1e6:.2f} MB\n\n")
        
        f.write("Columns:\n")
        for i, col in enumerate(df.columns, 1):
            f.write(f"  {i:2d}. {col}\n")
        f.write("\n")
        
        # ====================================================================
        # 2. MISSING VALUES
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("2. MISSING VALUES ANALYSIS\n")
        f.write("="*80 + "\n\n")
        
        missing = df.isnull().sum()
        
        if missing.sum() == 0:
            f.write("✓ No missing values found\n\n")
        else:
            for col in missing[missing > 0].index:
                pct = missing[col] / len(df) * 100
                f.write(f"  {col}: {missing[col]:,} ({pct:.2f}%)\n")
            f.write("\n")
        
        # ====================================================================
        # 3. PUBLICATION COUNTS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("3. PUBLICATION COUNTS STATISTICS\n")
        f.write("="*80 + "\n\n")
        
        f.write(df['total_papers'].describe().to_string())
        f.write("\n\n")
        
        f.write("Publication count distribution:\n\n")
        bins = [1, 2, 5, 10, 20, 50, 100, 500, np.inf]
        labels = ['1', '2-4', '5-9', '10-19', '20-49', '50-99', '100-499', '500+']
        dist = pd.cut(df['total_papers'], bins=bins, labels=labels, right=False)
        counts = dist.value_counts().sort_index()
        for label, count in counts.items():
            pct = count / len(df) * 100
            f.write(f"  {label:10s}: {count:8,} ({pct:5.2f}%)\n")
        f.write("\n")
        
        # ====================================================================
        # 4. FIELD DIVERSITY
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("4. FIELD DIVERSITY ANALYSIS\n")
        f.write("="*80 + "\n\n")
        
        f.write("Field diversity statistics:\n")
        f.write(df['num_unique_fields'].describe().to_string())
        f.write("\n\n")
        
        f.write("Distribution of unique fields per author:\n")
        field_dist = df['num_unique_fields'].value_counts().sort_index()
        for num_fields, count in field_dist.items():
            pct = count / len(df) * 100
            f.write(f"  {int(num_fields)} field(s): {count:8,} ({pct:5.2f}%)\n")
        f.write("\n\n")
        
        f.write("Top fields (by author count):\n")
        field_counts = df['top_field'].value_counts()
        for i, (field, count) in enumerate(field_counts.items(), 1):
            pct = count / len(df) * 100
            f.write(f"  {i:2d}. {field:40s}: {count:8,} ({pct:5.2f}%)\n")
        f.write("\n")
        
        # ====================================================================
        # 5. TOPIC DIVERSITY
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("5. TOPIC DIVERSITY ANALYSIS\n")
        f.write("="*80 + "\n\n")
        
        f.write("Topic diversity statistics:\n")
        f.write(df['num_unique_topics'].describe().to_string())
        f.write("\n\n")
        
        f.write("Distribution of unique topics per author:\n")
        bins_topics = [1, 2, 5, 10, 20, 50, 100, np.inf]
        labels_topics = ['1', '2-4', '5-9', '10-19', '20-49', '50-99', '100+']
        topic_dist = pd.cut(df['num_unique_topics'], bins=bins_topics, labels=labels_topics, right=False)
        topic_counts = topic_dist.value_counts().sort_index()
        for label, count in topic_counts.items():
            pct = count / len(df) * 100
            f.write(f"  {label:10s}: {count:8,} ({pct:5.2f}%)\n")
        f.write("\n\n")
        
        # Count topics across all authors
        all_topics = []
        for topics_json in df['topic_counts']:
            topics_dict = json.loads(topics_json)
            all_topics.extend(topics_dict.keys())
        
        topic_counter = pd.Series(all_topics).value_counts().head(30)
        f.write("Top 30 research topics (by author count):\n")
        for i, (topic, count) in enumerate(topic_counter.items(), 1):
            pct = count / len(df) * 100
            f.write(f"  {i:2d}. {topic[:60]:60s}: {count:6,} ({pct:4.2f}%)\n")
        f.write("\n")
        
        # ====================================================================
        # 6. JOURNAL DIVERSITY
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("6. JOURNAL DIVERSITY ANALYSIS\n")
        f.write("="*80 + "\n\n")
        
        f.write("Journal diversity statistics:\n")
        f.write(df['num_unique_journals'].describe().to_string())
        f.write("\n\n")
        
        f.write("Distribution of unique journals per author:\n")
        bins_journals = [1, 2, 5, 10, 20, 50, 100, np.inf]
        labels_journals = ['1', '2-4', '5-9', '10-19', '20-49', '50-99', '100+']
        journal_dist = pd.cut(df['num_unique_journals'], bins=bins_journals, labels=labels_journals, right=False)
        journal_counts = journal_dist.value_counts().sort_index()
        for label, count in journal_counts.items():
            pct = count / len(df) * 100
            f.write(f"  {label:10s}: {count:8,} ({pct:5.2f}%)\n")
        f.write("\n\n")
        
        # Count journals across all authors
        all_journals = []
        for journals_json in df['journal_counts']:
            journals_dict = json.loads(journals_json)
            all_journals.extend(journals_dict.keys())
        
        journal_counter = pd.Series(all_journals).value_counts().head(30)
        f.write("Top 30 journals (by author count):\n")
        for i, (journal, count) in enumerate(journal_counter.items(), 1):
            pct = count / len(df) * 100
            f.write(f"  {i:2d}. {journal[:60]:60s}: {count:6,} ({pct:4.2f}%)\n")
        f.write("\n")
        
        # ====================================================================
        # 6B. CS EXPERIENCE
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("6B. CS EXPERIENCE ANALYSIS\n")
        f.write("="*80 + "\n\n")
        
        cs_count = df['has_cs_experience'].sum()
        no_cs = len(df) - cs_count
        f.write(f"Authors with CS experience: {cs_count:,} ({cs_count/len(df)*100:.2f}%)\n")
        f.write(f"Authors without CS experience: {no_cs:,} ({no_cs/len(df)*100:.2f}%)\n\n")
        
        f.write("CS experience by top field:\n")
        for field in df['top_field'].unique():
            field_df = df[df['top_field'] == field]
            field_cs = field_df['has_cs_experience'].sum()
            f.write(f"  {field:40s}: {field_cs:6,} / {len(field_df):6,} ({field_cs/len(field_df)*100:.2f}%)\n")
        f.write("\n")
        
        f.write("Average publications by CS experience:\n")
        f.write(f"  With CS experience: {df[df['has_cs_experience']==1]['total_papers'].mean():.2f}\n")
        f.write(f"  Without CS experience: {df[df['has_cs_experience']==0]['total_papers'].mean():.2f}\n\n")
        
        f.write("Average diversity by CS experience:\n")
        f.write(f"  With CS experience:\n")
        f.write(f"    Avg unique fields: {df[df['has_cs_experience']==1]['num_unique_fields'].mean():.2f}\n")
        f.write(f"    Avg unique topics: {df[df['has_cs_experience']==1]['num_unique_topics'].mean():.2f}\n")
        f.write(f"    Avg unique journals: {df[df['has_cs_experience']==1]['num_unique_journals'].mean():.2f}\n")
        f.write(f"  Without CS experience:\n")
        f.write(f"    Avg unique fields: {df[df['has_cs_experience']==0]['num_unique_fields'].mean():.2f}\n")
        f.write(f"    Avg unique topics: {df[df['has_cs_experience']==0]['num_unique_topics'].mean():.2f}\n")
        f.write(f"    Avg unique journals: {df[df['has_cs_experience']==0]['num_unique_journals'].mean():.2f}\n\n")
        
        # ====================================================================
        # 7. TOP AUTHORS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("7. TOP AUTHORS BY PUBLICATION COUNT\n")
        f.write("="*80 + "\n\n")
        
        f.write("Top 50 authors by total papers in SDL venues:\n")
        f.write("-"*80 + "\n")
        f.write(f"{'author_id':<20} {'papers':>6}  {'fields':>6} {'topics':>6} {'journals':>8} {'cs_exp':>6} {'top_field':<20}\n")
        f.write("-"*80 + "\n")
        
        top_50 = df.nlargest(50, 'total_papers')
        for _, row in top_50.iterrows():
            f.write(f"{row['author_id']:<20} {row['total_papers']:>6} {row['num_unique_fields']:>6} "
                   f"{row['num_unique_topics']:>6} {row['num_unique_journals']:>8} "
                   f"{row['has_cs_experience']:>6} {row['top_field']:<20}\n")
        f.write("\n")
        
        # ====================================================================
        # 8. DIVERSITY PATTERNS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("8. DIVERSITY PATTERNS\n")
        f.write("="*80 + "\n\n")
        
        # Most diverse authors
        max_fields = df['num_unique_fields'].max()
        diverse = df[df['num_unique_fields'] == max_fields].nlargest(20, 'total_papers')
        f.write(f"Highly diverse authors (top 20 by field diversity):\n")
        f.write("-"*80 + "\n")
        for _, row in diverse.iterrows():
            f.write(f"{row['author_id']:<20} - {row['num_unique_fields']} fields, "
                   f"{row['num_unique_topics']} topics, {row['total_papers']} papers, "
                   f"CS exp: {row['has_cs_experience']}\n")
        f.write("\n\n")
        
        # Highly specialized authors
        specialized = df[(df['num_unique_fields'] == 1) & (df['total_papers'] > 20)].nlargest(20, 'total_papers')
        f.write("Highly specialized authors (>20 papers, 1 field only):\n")
        f.write("-"*80 + "\n")
        for _, row in specialized.iterrows():
            f.write(f"{row['author_id']:<20} - {row['total_papers']} papers, "
                   f"Field: {row['top_field']}, {row['num_unique_topics']} topics, "
                   f"CS exp: {row['has_cs_experience']}\n")
        f.write("\n")
        
        # ====================================================================
        # 9. TOP FIELD/TOPIC/JOURNAL DISTRIBUTION
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("9. TOP FIELD/TOPIC/JOURNAL DISTRIBUTION\n")
        f.write("="*80 + "\n\n")
        
        f.write("Distribution of authors by top field:\n")
        for field, count in df['top_field'].value_counts().items():
            pct = count / len(df) * 100
            f.write(f"  {field:40s}: {count:8,} ({pct:5.2f}%)\n")
        f.write("\n\n")
        
        f.write("Top 20 most common 'top topics':\n")
        topic_counts = df['top_topic'].value_counts().head(20)
        for i, (topic, count) in enumerate(topic_counts.items(), 1):
            pct = count / len(df) * 100
            f.write(f"  {i:2d}. {topic[:60]:60s}: {count:6,} ({pct:4.2f}%)\n")
        f.write("\n\n")
        
        f.write("Top 20 most common 'top journals':\n")
        journal_counts = df['top_journal'].value_counts().head(20)
        for i, (journal, count) in enumerate(journal_counts.items(), 1):
            pct = count / len(df) * 100
            f.write(f"  {i:2d}. {journal[:60]:60s}: {count:6,} ({pct:4.2f}%)\n")
        f.write("\n")
        
        # ====================================================================
        # 10. CORRELATION ANALYSIS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("10. CORRELATION ANALYSIS\n")
        f.write("="*80 + "\n\n")
        
        corr_cols = ['total_papers', 'num_unique_fields', 'num_unique_topics', 
                     'num_unique_journals', 'has_cs_experience']
        corr_matrix = df[corr_cols].corr()
        
        f.write("Correlation matrix:\n\n")
        f.write(corr_matrix.to_string())
        f.write("\n\n")
        
        f.write("Key insights:\n")
        f.write(f"  - Papers vs Fields correlation: {corr_matrix.loc['total_papers', 'num_unique_fields']:.3f}\n")
        f.write(f"  - Papers vs Topics correlation: {corr_matrix.loc['total_papers', 'num_unique_topics']:.3f}\n")
        f.write(f"  - Papers vs Journals correlation: {corr_matrix.loc['total_papers', 'num_unique_journals']:.3f}\n")
        f.write(f"  - Papers vs CS Experience correlation: {corr_matrix.loc['total_papers', 'has_cs_experience']:.3f}\n\n")
        
        # ====================================================================
        # 11. DATA QUALITY CHECKS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("11. DATA QUALITY CHECKS\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Authors with 0 papers: {(df['total_papers'] == 0).sum()}\n\n")
        
        f.write("Anomalies:\n")
        f.write(f"  - Authors with more unique fields than papers: {(df['num_unique_fields'] > df['total_papers']).sum()}\n")
        f.write(f"  - Authors with more unique topics than papers: {(df['num_unique_topics'] > df['total_papers']).sum()}\n")
        f.write(f"  - Authors with more unique journals than papers: {(df['num_unique_journals'] > df['total_papers']).sum()}\n\n")
        
        # Check empty dictionaries
        empty_fields = 0
        empty_topics = 0
        empty_journals = 0
        for _, row in df.iterrows():
            if json.loads(row['field_counts']) == {}:
                empty_fields += 1
            if json.loads(row['topic_counts']) == {}:
                empty_topics += 1
            if json.loads(row['journal_counts']) == {}:
                empty_journals += 1
        
        f.write("Empty count dictionaries:\n")
        f.write(f"  - Authors with empty field_counts: {empty_fields}\n")
        f.write(f"  - Authors with empty topic_counts: {empty_topics}\n")
        f.write(f"  - Authors with empty journal_counts: {empty_journals}\n\n")
        
        # ====================================================================
        # 12. SUMMARY STATISTICS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("12. SUMMARY STATISTICS\n")
        f.write("="*80 + "\n\n")
        
        # Get unique counts
        unique_fields = set()
        unique_topics = set()
        unique_journals = set()
        
        for _, row in df.iterrows():
            unique_fields.update(json.loads(row['field_counts']).keys())
            unique_topics.update(json.loads(row['topic_counts']).keys())
            unique_journals.update(json.loads(row['journal_counts']).keys())
        
        f.write(f"Total unique authors: {len(df):,}\n")
        f.write(f"Total unique fields: {len(unique_fields)}\n")
        f.write(f"Total unique topics: {len(unique_topics)}\n")
        f.write(f"Total unique journals: {len(unique_journals)}\n\n")
        
        f.write(f"Average papers per author: {df['total_papers'].mean():.2f}\n")
        f.write(f"Median papers per author: {df['total_papers'].median():.0f}\n")
        f.write(f"Average fields per author: {df['num_unique_fields'].mean():.2f}\n")
        f.write(f"Average topics per author: {df['num_unique_topics'].mean():.2f}\n")
        f.write(f"Average journals per author: {df['num_unique_journals'].mean():.2f}\n")
        f.write(f"Authors with CS experience: {df['has_cs_experience'].sum():,} ({df['has_cs_experience'].sum()/len(df)*100:.2f}%)\n\n")
        
        # Footer
        f.write("="*80 + "\n")
        f.write("END OF REPORT\n")
        f.write("="*80 + "\n")
    
    print(f"✓ EDA report saved to: {OUTPUT_FILE}")
    print(f"  File size: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    run_eda()