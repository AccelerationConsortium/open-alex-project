# """
# Build comprehensive author-level dataset from paper TSV files
# Optimized for HPC with two-phase processing

# Phase 1: Accumulate raw data for each author across all papers
# Phase 2: Aggregate accumulated data into final metrics
# """
import pandas as pd
import json
from collections import Counter
import numpy as np
from pathlib import Path
import sys
import os
import traceback

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# FIXED: Correct paths based on actual data structure
FIELDS = {
    'chemistry': PROJECT_DIR / "data" / "chemistry",
    'materials_science': PROJECT_DIR / "data" / "material_science", 
    'engineering': PROJECT_DIR / "data" / "engineering_redownload",
    'computer_science': PROJECT_DIR / "data" / "computer_science"
}

OUTPUT_DIR = PROJECT_DIR / "data" / "author"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
csv_file = OUTPUT_DIR / "author_metrics.csv"
output_file_eda = OUTPUT_DIR / "author_metrics_eda.txt"

YEARS = range(2012, 2026)
CHUNK_SIZE = 50000  # Process in chunks to manage memory

# ============================================================================
# EXTRACTION FUNCTIONS
# ============================================================================

def parse_authorships(raw_data_json):
    """Extract authorship information from raw_data JSON"""
    if pd.isna(raw_data_json) or raw_data_json == '':
        return []
    
    try:
        data = json.loads(raw_data_json)
        authorships = data.get('authorships', [])
        
        result = []
        num_authors = len(authorships)
        
        for idx, authorship in enumerate(authorships):
            author = authorship.get('author', {})
            
            # Extract author ID and clean it
            author_id = author.get('id', '')
            author_id = author_id.replace('https://openalex.org/', '')
            
            if not author_id:
                continue
            
            # Get institutions for this author on this paper
            institutions = []
            for inst in authorship.get('institutions', []):
                inst_id = inst.get('id', '')
                inst_id = inst_id.replace('https://openalex.org/', '')
                if inst_id:
                    institutions.append(inst_id)
            
            result.append({
                'author_id': author_id,
                'author_name': author.get('display_name', ''),
                'position': idx,
                'is_first': (idx == 0),
                'is_last': (idx == num_authors - 1),
                'institutions': institutions
            })
        
        return result
    
    except Exception as e:
        return []


def parse_primary_topic(raw_data_json):
    """Extract primary topic from raw_data"""
    if pd.isna(raw_data_json) or raw_data_json == '':
        return None
    
    try:
        data = json.loads(raw_data_json)
        topics = data.get('topics', [])
        if topics and len(topics) > 0:
            return topics[0].get('display_name', None)
    except:
        pass
    
    return None


def parse_journal(raw_data_json):
    """Extract journal name from raw_data"""
    if pd.isna(raw_data_json) or raw_data_json == '':
        return None
    
    try:
        data = json.loads(raw_data_json)
        journal = data.get('primary_location', {}).get('source', {}).get('display_name')
        return journal
    except:
        return None


def parse_corresponding_author_ids(raw_data_json):
    """Extract corresponding author IDs from raw_data"""
    if pd.isna(raw_data_json) or raw_data_json == '':
        return []
    
    try:
        data = json.loads(raw_data_json)
        corresponding_ids = data.get('corresponding_author_ids', [])
        
        # Clean the IDs (remove URL prefix)
        cleaned_ids = []
        for author_id in corresponding_ids:
            if author_id:
                cleaned_id = author_id.replace('https://openalex.org/', '')
                cleaned_ids.append(cleaned_id)
        
        return cleaned_ids
    
    except:
        return []


def parse_cited_by_count(raw_data_json):
    """Extract cited_by_count from raw_data"""
    if pd.isna(raw_data_json) or raw_data_json == '':
        return 0
    
    try:
        data = json.loads(raw_data_json)
        cited_by_count = data.get('cited_by_count', 0)
        return cited_by_count if cited_by_count else 0
    except:
        return 0


# ============================================================================
# AUTHOR DATA STRUCTURE FACTORY
# ============================================================================

def create_author_entry():
    """Factory function to create new author data entry"""
    return {
        'names': [],
        'citations_list': [],
        'fields': [],
        'topics': [],
        'journals': [],
        'affiliations': set(),
        'paper_count': 0,
        'first_author_count': 0,
        'last_author_count': 0,
        'corresponding_author_count': 0,
        'citation_sum': 0,
        'sdl_count': 0,
        'ai_count': 0,
        'robotics_count': 0
    }


# ============================================================================
# PHASE 1: ACCUMULATION (SEQUENTIAL)
# ============================================================================

def process_field_accumulation(field_name, field_dir, all_author_data):
    """
    Phase 1: Accumulate raw data for each author in a single field
    Processes field sequentially and adds to global author_data dictionary
    """
    
    print(f"\n{'='*70}", flush=True)
    print(f"PROCESSING: {field_name.upper()}", flush=True)
    print(f"Directory: {field_dir}", flush=True)
    print(f"{'='*70}", flush=True)
    
    # Verify directory exists
    if not field_dir.exists():
        print(f"ERROR: Directory does not exist: {field_dir}", flush=True)
        return 0, 0
    
    total_papers = 0
    total_errors = 0
    
    for year in YEARS:
        # Check multiple possible filename patterns
        possible_files = [
            field_dir / f"{field_name}_{year}.tsv",
            field_dir / f"{field_name.replace('_', '')}_{year}.tsv",
        ]
        
        tsv_file = None
        for possible_file in possible_files:
            if possible_file.exists():
                tsv_file = possible_file
                break
        
        if not tsv_file:
            continue  # Skip silently if file doesn't exist
        
        print(f"  {year}: {tsv_file.name}...", end=' ', flush=True)
        
        papers_in_year = 0
        errors_in_year = 0
        
        try:
            # First check if file is readable and get columns
            try:
                sample = pd.read_csv(tsv_file, sep='\t', nrows=5)
                available_cols = set(sample.columns)
            except Exception as e:
                print(f"✗ Cannot read file: {e}", flush=True)
                continue
            
            # Determine which columns to read
            required = ['raw_data', 'SDL', 'AI_Paper', 'Robotics_Paper']
            columns_to_read = [col for col in required if col in available_cols]
            
            if 'raw_data' not in columns_to_read:
                print(f"✗ Missing raw_data column", flush=True)
                continue
            
            # Read in chunks
            chunk_num = 0
            for chunk in pd.read_csv(tsv_file, sep='\t', usecols=columns_to_read,
                                    chunksize=CHUNK_SIZE, low_memory=False,
                                    on_bad_lines='skip'):  # Skip malformed lines
                
                chunk_num += 1
                
                for idx, row in chunk.iterrows():
                    try:
                        # Parse authorships
                        authorships = parse_authorships(row.get('raw_data'))
                        
                        if not authorships:
                            continue
                        
                        # Extract paper-level info
                        citations = parse_cited_by_count(row.get('raw_data'))
                        is_sdl = row.get('SDL', 0) == 1
                        is_ai = row.get('AI_Paper', 0) == 1
                        is_robotics = row.get('Robotics_Paper', 0) == 1
                        
                        topic = parse_primary_topic(row.get('raw_data'))
                        journal = parse_journal(row.get('raw_data'))
                        corresponding_ids = parse_corresponding_author_ids(row.get('raw_data'))
                        
                        # Process each author
                        for authorship in authorships:
                            author_id = authorship['author_id']
                            
                            # Initialize author entry if new
                            if author_id not in all_author_data:
                                all_author_data[author_id] = create_author_entry()
                            
                            data = all_author_data[author_id]
                            
                            # Accumulate data
                            data['names'].append(authorship['author_name'])
                            data['citations_list'].append(citations)
                            data['citation_sum'] += citations
                            data['fields'].append(field_name)
                            
                            if topic:
                                data['topics'].append(topic)
                            if journal:
                                data['journals'].append(journal)
                            
                            data['affiliations'].update(authorship['institutions'])
                            data['paper_count'] += 1
                            
                            if authorship['is_first']:
                                data['first_author_count'] += 1
                            if authorship['is_last']:
                                data['last_author_count'] += 1
                            if author_id in corresponding_ids:
                                data['corresponding_author_count'] += 1
                            
                            if is_sdl:
                                data['sdl_count'] += 1
                            if is_ai:
                                data['ai_count'] += 1
                            if is_robotics:
                                data['robotics_count'] += 1
                        
                        papers_in_year += 1
                        total_papers += 1
                    
                    except Exception as e:
                        errors_in_year += 1
                        total_errors += 1
                        if errors_in_year <= 5:  # Only print first 5 errors per year
                            print(f"\n  Row error: {str(e)[:100]}", flush=True)
                
                # Progress within year
                if chunk_num % 10 == 0:
                    print(f".", end='', flush=True)
            
            print(f" ✓ {papers_in_year:,} papers", flush=True)
        
        except Exception as e:
            print(f" ✗ File error: {str(e)[:200]}", flush=True)
            traceback.print_exc()
            continue
    
    print(f"{field_name} COMPLETE:", flush=True)
    print(f"  Papers processed: {total_papers:,}", flush=True)
    print(f"  Errors: {total_errors:,}", flush=True)
    
    return total_papers, total_errors


# ============================================================================
# PHASE 2: AGGREGATION
# ============================================================================

def aggregate_author_metrics(all_author_data):
    """Phase 2: Convert accumulated data into final metrics"""
    
    print(f"\n{'='*70}")
    print("PHASE 2: Computing final metrics")
    print(f"{'='*70}")
    print(f"Processing {len(all_author_data):,} unique authors...")
    
    rows = []
    
    for idx, (author_id, data) in enumerate(all_author_data.items()):
        if (idx + 1) % 100000 == 0:
            print(f"  {idx + 1:,} authors processed...", flush=True)
        
        # Most common name
        author_name = Counter(data['names']).most_common(1)[0][0] if data['names'] else ''
        
        # Counts
        total_papers = data['paper_count']
        first_author_papers = data['first_author_count']
        last_author_papers = data['last_author_count']
        corresponding_author_papers = data['corresponding_author_count']
        
        # Citations
        total_citations = data['citation_sum']
        avg_citations = np.mean(data['citations_list']) if data['citations_list'] else 0
        
        # Field
        if data['fields']:
            field_counter = Counter(data['fields'])
            top_field_name, top_field_count = field_counter.most_common(1)[0]
            num_unique_fields = len(field_counter)
        else:
            top_field_name, top_field_count, num_unique_fields = '', 0, 0
        
        # Topic
        if data['topics']:
            topic_counter = Counter(data['topics'])
            top_topic_name, top_topic_count = topic_counter.most_common(1)[0]
            num_unique_topics = len(topic_counter)
        else:
            top_topic_name, top_topic_count, num_unique_topics = '', 0, 0
        
        # Journal
        if data['journals']:
            journal_counter = Counter(data['journals'])
            top_journal_name, top_journal_count = journal_counter.most_common(1)[0]
            num_unique_journals = len(journal_counter)
        else:
            top_journal_name, top_journal_count, num_unique_journals = '', 0, 0
        
        # Affiliations
        num_affiliations = len(data['affiliations'])
        top_affiliation = list(data['affiliations'])[0] if data['affiliations'] else ''
        
        rows.append({
            'author_id': author_id,
            'author_name': author_name,
            'total_papers': total_papers,
            'first_author_papers': first_author_papers,
            'last_author_papers': last_author_papers,
            'corresponding_author_papers': corresponding_author_papers,
            'total_citations': int(total_citations),
            'avg_citations_per_paper': round(avg_citations, 2),
            'top_field': top_field_name,
            'top_field_paper_count': top_field_count,
            'num_unique_fields': num_unique_fields,
            'top_topic': top_topic_name,
            'top_topic_paper_count': top_topic_count,
            'num_unique_topics': num_unique_topics,
            'top_journal': top_journal_name,
            'top_journal_paper_count': top_journal_count,
            'num_unique_journals': num_unique_journals,
            'num_affiliations': num_affiliations,
            'top_affiliation': top_affiliation,
            'sdl_papers': data['sdl_count'],
            'ai_papers': data['ai_count'],
            'robotics_papers': data['robotics_count']
        })
    
    return pd.DataFrame(rows)



def perform_eda_and_save(csv_file_path, output_file_path=None):
    """
    Perform comprehensive EDA on author dataset and save results to file
    
    Args:
        csv_file_path: Path to author_metrics.csv
        output_file_path: Path to save EDA report (optional, defaults to same dir as csv)
    """
    import pandas as pd
    import numpy as np
    from pathlib import Path
    from datetime import datetime
    
    print(f"\n{'='*70}")
    print("EXPLORATORY DATA ANALYSIS - AUTHOR DATASET")
    print(f"{'='*70}\n")
    
    # Load data
    print(f"Loading data from: {csv_file_path}")
    df = pd.read_csv(csv_file_path)
    
    # Set output file path
    if output_file_path is None:
        csv_path = Path(csv_file_path)
        output_file_path = csv_path.parent / f"author_dataset_EDA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    print(f"Saving EDA report to: {output_file_path}\n")
    
    # Open file for writing
    with open(output_file_path, 'w', encoding='utf-8') as f:
        
        # Header
        f.write("="*80 + "\n")
        f.write("EXPLORATORY DATA ANALYSIS - AUTHOR DATASET\n")
        f.write("="*80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Source file: {csv_file_path}\n")
        f.write("="*80 + "\n\n")
        
        # ====================================================================
        # 1. BASIC DATASET INFO
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
        # 2. MISSING VALUES ANALYSIS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("2. MISSING VALUES ANALYSIS\n")
        f.write("="*80 + "\n\n")
        
        missing = df.isnull().sum()
        missing_pct = (missing / len(df) * 100).round(2)
        
        if missing.sum() == 0:
            f.write("✓ No missing values found!\n\n")
        else:
            f.write("Columns with missing values:\n")
            for col in missing[missing > 0].index:
                f.write(f"  {col}: {missing[col]:,} ({missing_pct[col]:.2f}%)\n")
            f.write("\n")
        
        # Empty string check for key columns
        f.write("Empty string check:\n")
        empty_checks = {
            'author_name': (df['author_name'] == '').sum(),
            'top_field': (df['top_field'] == '').sum(),
            'top_topic': (df['top_topic'] == '').sum(),
            'top_journal': (df['top_journal'] == '').sum()
        }
        for col, count in empty_checks.items():
            if count > 0:
                f.write(f"  {col}: {count:,} ({count/len(df)*100:.2f}%)\n")
        f.write("\n")
        
        # ====================================================================
        # 3. PUBLICATION COUNTS STATISTICS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("3. PUBLICATION COUNTS STATISTICS\n")
        f.write("="*80 + "\n\n")
        
        pub_cols = ['total_papers', 'first_author_papers', 'last_author_papers', 
                    'corresponding_author_papers', 'sdl_papers', 'ai_papers', 'robotics_papers']
        
        f.write(df[pub_cols].describe().to_string())
        f.write("\n\n")
        
        # Distribution breakdowns
        f.write("Publication count distributions:\n\n")
        
        for col in ['total_papers', 'first_author_papers', 'last_author_papers']:
            f.write(f"{col}:\n")
            bins = [1, 2, 5, 10, 20, 50, 100, 500, 1000, np.inf]
            labels = ['1', '2-4', '5-9', '10-19', '20-49', '50-99', '100-499', '500-999', '1000+']
            
            try:
                dist = pd.cut(df[col], bins=bins, labels=labels, right=False)
                counts = dist.value_counts().sort_index()
                for label, count in counts.items():
                    pct = count / len(df) * 100
                    f.write(f"  {label:10s}: {count:8,} ({pct:5.2f}%)\n")
            except Exception as e:
                f.write(f"  Error creating distribution: {e}\n")
            
            f.write("\n")
        
        # ====================================================================
        # 4. CITATION STATISTICS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("4. CITATION STATISTICS\n")
        f.write("="*80 + "\n\n")
        
        cite_cols = ['total_citations', 'avg_citations_per_paper']
        f.write(df[cite_cols].describe().to_string())
        f.write("\n\n")
        
        # Highly cited authors
        f.write("Citation milestones:\n")
        f.write(f"  Authors with 0 citations: {(df['total_citations'] == 0).sum():,}\n")
        f.write(f"  Authors with 100+ citations: {(df['total_citations'] >= 100).sum():,}\n")
        f.write(f"  Authors with 1,000+ citations: {(df['total_citations'] >= 1000).sum():,}\n")
        f.write(f"  Authors with 10,000+ citations: {(df['total_citations'] >= 10000).sum():,}\n")
        f.write(f"  Authors with 100,000+ citations: {(df['total_citations'] >= 100000).sum():,}\n")
        f.write("\n")
        
        # ====================================================================
        # 5. FIELD DISTRIBUTION
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("5. FIELD DISTRIBUTION\n")
        f.write("="*80 + "\n\n")
        
        field_counts = df['top_field'].value_counts()
        f.write("Authors by top field:\n")
        for field, count in field_counts.items():
            pct = count / len(df) * 100
            f.write(f"  {field:25s}: {count:8,} ({pct:5.2f}%)\n")
        f.write("\n")
        
        # Multi-field authors
        f.write("Multi-field activity:\n")
        multi_field_dist = df['num_unique_fields'].value_counts().sort_index()
        for num_fields, count in multi_field_dist.items():
            pct = count / len(df) * 100
            f.write(f"  {num_fields} fields: {count:8,} ({pct:5.2f}%)\n")
        f.write("\n")
        
        # ====================================================================
        # 6. TOP AUTHORS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("6. TOP AUTHORS\n")
        f.write("="*80 + "\n\n")
        
        # Top by total papers
        f.write("Top 20 authors by total papers:\n")
        f.write("-" * 80 + "\n")
        top_papers = df.nlargest(20, 'total_papers')[
            ['author_name', 'total_papers', 'total_citations', 'top_field', 'top_topic', 'sdl_papers']
        ]
        f.write(top_papers.to_string(index=False, max_colwidth=30))
        f.write("\n\n")
        
        # Top by citations
        f.write("Top 20 authors by total citations:\n")
        f.write("-" * 80 + "\n")
        top_cites = df.nlargest(20, 'total_citations')[
            ['author_name', 'total_papers', 'total_citations', 'avg_citations_per_paper', 'top_field']
        ]
        f.write(top_cites.to_string(index=False, max_colwidth=30))
        f.write("\n\n")
        
        # Top by average citations (min 10 papers to avoid noise)
        f.write("Top 20 authors by avg citations per paper (min 10 papers):\n")
        f.write("-" * 80 + "\n")
        top_avg = df[df['total_papers'] >= 10].nlargest(20, 'avg_citations_per_paper')[
            ['author_name', 'total_papers', 'total_citations', 'avg_citations_per_paper', 'top_field']
        ]
        f.write(top_avg.to_string(index=False, max_colwidth=30))
        f.write("\n\n")
        
        # ====================================================================
        # 7. SDL/AI/ROBOTICS ANALYSIS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("7. SDL/AI/ROBOTICS INVOLVEMENT\n")
        f.write("="*80 + "\n\n")
        
        f.write("Authors with SDL/AI/Robotics papers:\n")
        f.write(f"  Authors with ≥1 SDL paper: {(df['sdl_papers'] > 0).sum():,}\n")
        f.write(f"  Authors with ≥5 SDL papers: {(df['sdl_papers'] >= 5).sum():,}\n")
        f.write(f"  Authors with ≥10 SDL papers: {(df['sdl_papers'] >= 10).sum():,}\n\n")
        
        f.write(f"  Authors with ≥1 AI paper: {(df['ai_papers'] > 0).sum():,}\n")
        f.write(f"  Authors with ≥10 AI papers: {(df['ai_papers'] >= 10).sum():,}\n\n")
        
        f.write(f"  Authors with ≥1 Robotics paper: {(df['robotics_papers'] > 0).sum():,}\n")
        f.write(f"  Authors with ≥10 Robotics papers: {(df['robotics_papers'] >= 10).sum():,}\n\n")
        
        # Top SDL authors
        if (df['sdl_papers'] > 0).sum() > 0:
            f.write("Top 20 SDL authors:\n")
            f.write("-" * 80 + "\n")
            top_sdl = df[df['sdl_papers'] > 0].nlargest(20, 'sdl_papers')[
                ['author_name', 'total_papers', 'sdl_papers', 'ai_papers', 'robotics_papers', 'top_field']
            ]
            f.write(top_sdl.to_string(index=False, max_colwidth=30))
            f.write("\n\n")
        
        # ====================================================================
        # 8. TOPIC ANALYSIS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("8. TOPIC ANALYSIS\n")
        f.write("="*80 + "\n\n")
        
        # Top topics
        f.write("Top 30 research topics by author count:\n")
        topic_counts = df['top_topic'].value_counts().head(30)
        for i, (topic, count) in enumerate(topic_counts.items(), 1):
            pct = count / len(df) * 100
            f.write(f"  {i:2d}. {topic[:50]:50s}: {count:6,} ({pct:4.2f}%)\n")
        f.write("\n")
        
        # Topic diversity
        f.write("Topic diversity:\n")
        f.write(f"  Unique topics in dataset: {df['top_topic'].nunique():,}\n")
        f.write(f"  Avg topics per author: {df['num_unique_topics'].mean():.2f}\n")
        f.write(f"  Max topics by single author: {df['num_unique_topics'].max()}\n\n")
        
        # ====================================================================
        # 9. JOURNAL ANALYSIS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("9. JOURNAL ANALYSIS\n")
        f.write("="*80 + "\n\n")
        
        # Top journals
        f.write("Top 30 journals by author count:\n")
        journal_counts = df['top_journal'].value_counts().head(30)
        for i, (journal, count) in enumerate(journal_counts.items(), 1):
            pct = count / len(df) * 100
            f.write(f"  {i:2d}. {journal[:50]:50s}: {count:6,} ({pct:4.2f}%)\n")
        f.write("\n")
        
        f.write("Journal diversity:\n")
        f.write(f"  Unique journals in dataset: {df['top_journal'].nunique():,}\n")
        f.write(f"  Avg journals per author: {df['num_unique_journals'].mean():.2f}\n")
        f.write(f"  Max journals by single author: {df['num_unique_journals'].max()}\n\n")
        
        # ====================================================================
        # 10. AUTHORSHIP POSITION ANALYSIS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("10. AUTHORSHIP POSITION ANALYSIS\n")
        f.write("="*80 + "\n\n")
        
        # First author stats
        f.write("First authorship:\n")
        f.write(f"  Authors who were NEVER first author: {(df['first_author_papers'] == 0).sum():,}\n")
        f.write(f"  Authors who were ALWAYS first author: {(df['first_author_papers'] == df['total_papers']).sum():,}\n")
        f.write(f"  Avg first author papers: {df['first_author_papers'].mean():.2f}\n\n")
        
        # Last author stats
        f.write("Last authorship:\n")
        f.write(f"  Authors who were NEVER last author: {(df['last_author_papers'] == 0).sum():,}\n")
        f.write(f"  Authors who were ALWAYS last author: {(df['last_author_papers'] == df['total_papers']).sum():,}\n")
        f.write(f"  Avg last author papers: {df['last_author_papers'].mean():.2f}\n\n")
        
        # Corresponding author stats
        f.write("Corresponding authorship:\n")
        f.write(f"  Authors who were NEVER corresponding: {(df['corresponding_author_papers'] == 0).sum():,}\n")
        f.write(f"  Authors corresponding on all papers: {(df['corresponding_author_papers'] == df['total_papers']).sum():,}\n")
        f.write(f"  Avg corresponding papers: {df['corresponding_author_papers'].mean():.2f}\n\n")
        
        # ====================================================================
        # 11. DATA QUALITY CHECKS / ANOMALIES
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("11. DATA QUALITY CHECKS & ANOMALIES\n")
        f.write("="*80 + "\n\n")
        
        # Check for impossible values
        f.write("ANOMALY CHECKS:\n\n")
        
        # First + Last > Total (should be 0 for multi-author papers)
        anomaly1 = df[(df['first_author_papers'] + df['last_author_papers']) > df['total_papers']]
        f.write(f"1. Authors where (first + last) > total papers: {len(anomaly1):,}\n")
        if len(anomaly1) > 0:
            f.write("   NOTE: This should only happen for single-author papers!\n")
            single_author = anomaly1[anomaly1['total_papers'] == anomaly1['first_author_papers']]
            f.write(f"   Single-author cases: {len(single_author):,}\n")
            f.write(f"   ACTUAL ANOMALIES: {len(anomaly1) - len(single_author):,}\n")
        f.write("\n")
        
        # Negative values (should be 0)
        f.write("2. Negative value check:\n")
        for col in df.select_dtypes(include=[np.number]).columns:
            negative_count = (df[col] < 0).sum()
            if negative_count > 0:
                f.write(f"   ✗ {col}: {negative_count:,} negative values!\n")
        f.write("   ✓ No negative values found\n\n")
        
        # Authors with citations but no papers (should be 0)
        anomaly3 = df[(df['total_citations'] > 0) & (df['total_papers'] == 0)]
        f.write(f"3. Authors with citations but no papers: {len(anomaly3):,}\n\n")
        
        # Authors with papers but no citations
        anomaly4 = df[(df['total_papers'] > 0) & (df['total_citations'] == 0)]
        f.write(f"4. Authors with papers but ZERO citations: {len(anomaly4):,} ({len(anomaly4)/len(df)*100:.2f}%)\n")
        if len(anomaly4) > 0:
            f.write(f"   This includes papers that are very recent or not yet cited\n")
        f.write("\n")
        
        # Very high average citations (potential data issues)
        anomaly5 = df[df['avg_citations_per_paper'] > 1000]
        f.write(f"5. Authors with avg >1000 citations per paper: {len(anomaly5):,}\n")
        if len(anomaly5) > 0:
            f.write("   Top cases:\n")
            for _, row in anomaly5.nlargest(5, 'avg_citations_per_paper').iterrows():
                f.write(f"   - {row['author_name'][:30]:30s}: {row['avg_citations_per_paper']:8.1f} avg ({row['total_papers']} papers)\n")
        f.write("\n")
        
        # Corresponding author rate
        f.write("6. Corresponding author anomalies:\n")
        corr_rate = df['corresponding_author_papers'] / df['total_papers']
        anomaly6 = df[corr_rate > 1.0]
        f.write(f"   Authors where corresponding > total papers: {len(anomaly6):,}\n")
        f.write(f"   (Note: This can happen if multiple corresponding authors per paper)\n\n")
        
        # ====================================================================
        # 12. AFFILIATION ANALYSIS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("12. AFFILIATION ANALYSIS\n")
        f.write("="*80 + "\n\n")
        
        f.write("Affiliation statistics:\n")
        f.write(f"  Avg affiliations per author: {df['num_affiliations'].mean():.2f}\n")
        f.write(f"  Median affiliations: {df['num_affiliations'].median():.0f}\n")
        f.write(f"  Max affiliations by single author: {df['num_affiliations'].max()}\n\n")
        
        f.write("Affiliation distribution:\n")
        aff_bins = [0, 1, 2, 5, 10, 20, 50, np.inf]
        aff_labels = ['0', '1', '2-4', '5-9', '10-19', '20-49', '50+']
        aff_dist = pd.cut(df['num_affiliations'], bins=aff_bins, labels=aff_labels, right=False)
        aff_counts = aff_dist.value_counts().sort_index()
        for label, count in aff_counts.items():
            pct = count / len(df) * 100
            f.write(f"  {label:6s}: {count:8,} ({pct:5.2f}%)\n")
        f.write("\n")
        
        # ====================================================================
        # 13. INTERESTING PATTERNS
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("13. INTERESTING PATTERNS\n")
        f.write("="*80 + "\n\n")
        
        # Prolific but uncited
        f.write("Prolific but uncited authors (>50 papers, 0 citations):\n")
        prolific_uncited = df[(df['total_papers'] > 50) & (df['total_citations'] == 0)]
        f.write(f"  Count: {len(prolific_uncited):,}\n")
        if len(prolific_uncited) > 0:
            f.write("  Top cases:\n")
            for _, row in prolific_uncited.nlargest(5, 'total_papers').iterrows():
                f.write(f"  - {row['author_name'][:40]:40s}: {row['total_papers']:4d} papers\n")
        f.write("\n")
        
        # Highly cited with few papers
        f.write("Highly efficient authors (>1000 citations, <10 papers):\n")
        efficient = df[(df['total_citations'] > 1000) & (df['total_papers'] < 10)]
        f.write(f"  Count: {len(efficient):,}\n")
        if len(efficient) > 0:
            f.write("  Top cases:\n")
            for _, row in efficient.nlargest(5, 'avg_citations_per_paper').iterrows():
                f.write(f"  - {row['author_name'][:40]:40s}: {row['total_citations']:6,} cites in {row['total_papers']} papers (avg: {row['avg_citations_per_paper']:.0f})\n")
        f.write("\n")
        
        # Cross-field superstars
        f.write("Cross-field researchers (4 fields, >100 papers):\n")
        cross_field = df[(df['num_unique_fields'] == 4) & (df['total_papers'] > 100)]
        f.write(f"  Count: {len(cross_field):,}\n")
        if len(cross_field) > 0:
            f.write("  Examples:\n")
            for _, row in cross_field.nlargest(5, 'total_papers').iterrows():
                f.write(f"  - {row['author_name'][:40]:40s}: {row['total_papers']:4d} papers across all 4 fields\n")
        f.write("\n")
        
        # ====================================================================
        # FOOTER
        # ====================================================================
        
        f.write("="*80 + "\n")
        f.write("END OF REPORT\n")
        f.write("="*80 + "\n")
    
    print(f"✓ EDA report saved to: {output_file_path}")
    print(f"  File size: {Path(output_file_path).stat().st_size / 1024:.1f} KB")
    
    # Also print some quick stats to console
    print(f"\nQUICK SUMMARY:")
    print(f"  Total authors: {len(df):,}")
    print(f"  Authors with SDL papers: {(df['sdl_papers'] > 0).sum():,}")
    print(f"  Most prolific author: {df.loc[df['total_papers'].idxmax(), 'author_name']} ({df['total_papers'].max()} papers)")
    print(f"  Most cited author: {df.loc[df['total_citations'].idxmax(), 'author_name']} ({df['total_citations'].max():,} citations)")
    
    return output_file_path

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("="*70)
    print("BUILDING AUTHOR-LEVEL DATASET (SEQUENTIAL VERSION)")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Project dir: {PROJECT_DIR}")
    print(f"  Output dir: {OUTPUT_DIR}")
    print(f"  Years: {min(YEARS)}-{max(YEARS)-1}")
    print(f"  Chunk size: {CHUNK_SIZE:,}")
    print(f"  Processing: SEQUENTIAL (one field at a time)")
    
    # Verify field directories
    print(f"\nVerifying field directories:")
    fields_to_process = []
    for name, path in FIELDS.items():
        exists = path.exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {name}: {path}")
        if exists:
            fields_to_process.append((name, path))
    
    if not fields_to_process:
        print("\n✗ ERROR: No valid field directories found!")
        return 1
    
    print(f"\nWill process {len(fields_to_process)} fields sequentially...")
    
    # ========================================================================
    # PHASE 1: Sequential accumulation
    # ========================================================================
    
    # Initialize global author data dictionary
    all_author_data = {}
    
    total_papers_all = 0
    total_errors_all = 0
    
    # Process each field one at a time
    for field_name, field_dir in fields_to_process:
        papers, errors = process_field_accumulation(field_name, field_dir, all_author_data)
        total_papers_all += papers
        total_errors_all += errors
        
        # Show running totals
        print(f"  Running totals: {len(all_author_data):,} unique authors across {total_papers_all:,} papers")
    
    # ========================================================================
    # Summary after all fields processed
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("ALL FIELDS PROCESSED")
    print(f"{'='*70}")
    print(f"  Total papers: {total_papers_all:,}")
    print(f"  Total errors: {total_errors_all:,}")
    print(f"  Unique authors: {len(all_author_data):,}")
    
    # ========================================================================
    # PHASE 2: Aggregation
    # ========================================================================
    
    df_authors = aggregate_author_metrics(all_author_data)
    
    # ========================================================================
    # Save output
    # ========================================================================
    
    output_file = OUTPUT_DIR / "author_metrics.csv"
    print(f"\n{'='*70}")
    print("SAVING OUTPUT")
    print(f"{'='*70}")
    
    df_authors.to_csv(output_file, index=False)
    
    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"  File: {output_file}")
    print(f"  Size: {file_size_mb:.1f} MB")
    print(f"  Rows: {len(df_authors):,}")
    print(f"  Columns: {len(df_authors.columns)}")
    
    # Summary stats
    print(f"\n{'='*70}")
    print("SUMMARY STATISTICS")
    print(f"{'='*70}")
    print(df_authors[['total_papers', 'total_citations', 
                     'first_author_papers', 'last_author_papers']].describe())
    
    print(f"\n{'='*70}")
    print("TOP 10 AUTHORS BY TOTAL PAPERS")
    print(f"{'='*70}")
    top_authors = df_authors.nlargest(10, 'total_papers')[
        ['author_name', 'total_papers', 'total_citations', 'top_field', 'top_topic']
    ]
    print(top_authors.to_string(index=False))
    
    print(f"\n{'='*70}")
    print("✅ COMPLETE!")
    print(f"{'='*70}")
    print(f"Output: {output_file}\n")
    
    return 0

if __name__ == "__main__":
    # main()
    perform_eda_and_save(csv_file, output_file_eda)

