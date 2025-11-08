# """
# Build comprehensive author-level dataset from paper TSV files
# Optimized for HPC with two-phase processing

# Phase 1: Accumulate raw data for each author across all papers
# Phase 2: Aggregate accumulated data into final metrics
# """

# import pandas as pd
# import json
# from collections import defaultdict, Counter
# import numpy as np
# from pathlib import Path

# # ============================================================================
# # CONFIGURATION
# # ============================================================================

# PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")
# DATA_DIR = PROJECT_DIR / "data/fields"
# OUTPUT_DIR = PROJECT_DIR / "data" 
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# # Fields to process
# FIELDS = {
#     'chemistry': DATA_DIR / "chemistry",
#     'materials_science': DATA_DIR / "material_science", 
#     'engineering': DATA_DIR / "engineering_redownload",
#     'computer_science': DATA_DIR / "computer_science"
# }

# YEARS = range(2012, 2026)
# CHUNK_SIZE = 500000  # Process in chunks to manage memory

# # ============================================================================
# # EXTRACTION FUNCTIONS
# # ============================================================================

# def parse_authorships(raw_data_json):
#     """
#     Extract authorship information from raw_data JSON
    
#     Returns list of dicts with:
#     - author_id: OpenAlex ID (cleaned)
#     - author_name: Display name
#     - position: Index in authorship list (0=first, last=last author)
#     - institutions: List of institution IDs for this author
#     """
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return []
    
#     try:
#         data = json.loads(raw_data_json)
#         authorships = data.get('authorships', [])
        
#         result = []
#         num_authors = len(authorships)
        
#         for idx, authorship in enumerate(authorships):
#             author = authorship.get('author', {})
            
#             # Extract author ID and clean it
#             author_id = author.get('id', '')
#             author_id = author_id.replace('https://openalex.org/', '')
            
#             if not author_id:
#                 continue
            
#             # Get institutions for this author on this paper
#             institutions = []
#             for inst in authorship.get('institutions', []):
#                 inst_id = inst.get('id', '')
#                 inst_id = inst_id.replace('https://openalex.org/', '')
#                 if inst_id:
#                     institutions.append(inst_id)
            
#             result.append({
#                 'author_id': author_id,
#                 'author_name': author.get('display_name', ''),
#                 'position': idx,
#                 'is_first': (idx == 0),
#                 'is_last': (idx == num_authors - 1),
#                 'institutions': institutions
#             })
        
#         return result
    
#     except Exception as e:
#         return []


# def parse_primary_topic(raw_data_json):
#     """
#     Extract primary topic from raw_data
#     Primary topic is the first topic in the topics list
    
#     Returns: topic display_name or None
#     """
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return None
    
#     try:
#         data = json.loads(raw_data_json)
#         topics = data.get('topics', [])
#         if topics and len(topics) > 0:
#             return topics[0].get('display_name', None)
#     except:
#         pass
    
#     return None


# def parse_journal(raw_data_json):
#     """
#     Extract journal name from raw_data
#     Journal is in primary_location -> source -> display_name
    
#     Returns: journal name or None
#     """
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return None
    
#     try:
#         data = json.loads(raw_data_json)
#         journal = data.get('primary_location', {}).get('source', {}).get('display_name')
#         return journal
#     except:
#         return None


# def parse_corresponding_author_ids(raw_data_json):
#     """
#     Extract corresponding author IDs from raw_data
#     This is a paper-level field, more reliable than authorship-level is_corresponding
    
#     Returns: list of author IDs (cleaned) or empty list
#     """
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return []
    
#     try:
#         data = json.loads(raw_data_json)
#         corresponding_ids = data.get('corresponding_author_ids', [])
        
#         # Clean the IDs (remove URL prefix)
#         cleaned_ids = []
#         for author_id in corresponding_ids:
#             if author_id:
#                 cleaned_id = author_id.replace('https://openalex.org/', '')
#                 cleaned_ids.append(cleaned_id)
        
#         return cleaned_ids
    
#     except:
#         return []


# # ============================================================================
# # PHASE 1: ACCUMULATION
# # ============================================================================

# def process_field_accumulation(field_name, field_dir):
#     """
#     Phase 1: Accumulate raw data for each author
    
#     Goes through all papers in a field and accumulates:
#     - Lists of values (names, topics, journals, citations, etc.)
#     - Counters (total papers, first author papers, etc.)
#     - Sets (unique affiliations)
    
#     Returns: dict of author_id -> accumulated data
#     """
    
#     print(f"\n{'='*70}")
#     print(f"PHASE 1: Accumulating data from {field_name.upper()}")
#     print(f"{'='*70}")
    
#     # Initialize author data structure
#     # Using defaultdict with lambda to auto-create structure for new authors
#     author_data = defaultdict(lambda: {
#         # Lists to accumulate values across papers
#         'names': [],              # All name variants
#         'citations_list': [],     # Citation count for each paper
#         'fields': [],             # Field for each paper
#         'topics': [],             # Topic for each paper
#         'journals': [],           # Journal for each paper
        
#         # Sets for unique values
#         'affiliations': set(),    # Unique institution IDs
        
#         # Counters
#         'paper_count': 0,
#         'first_author_count': 0,
#         'last_author_count': 0,
#         'corresponding_author_count': 0,
#         'citation_sum': 0,
        
#         # SDL/AI/Robotics counts
#         'sdl_count': 0,
#         'ai_count': 0,
#         'robotics_count': 0
#     })
    
#     total_papers = 0
    
#     for year in YEARS:
#         tsv_file = field_dir / f"{field_name}_{year}.tsv"
        
#         if not tsv_file.exists():
#             print(f"  ⚠️  Skipping {year}: file not found")
#             continue
        
#         print(f"  Processing {year}...", end=' ', flush=True)
        
#         # Columns we need from TSV
#         columns = [
#             'raw_data',           # For parsing authorships, topics, journal
#             'author_count',       # Team size
#             'SDL',                # SDL paper flag
#             'AI_Paper',           # AI paper flag
#             'Robotics_Paper',     # Robotics paper flag
#             'cited_by_count'      # Citations
#         ]
        
#         chunks_processed = 0
#         papers_in_year = 0
        
#         try:
#             # Read in chunks to manage memory
#             for chunk in pd.read_csv(tsv_file, sep='\t', usecols=columns, 
#                                     chunksize=CHUNK_SIZE, low_memory=False):
                
#                 for _, row in chunk.iterrows():
#                     # Parse authorships from raw_data
#                     authorships = parse_authorships(row['raw_data'])
                    
#                     if not authorships:
#                         continue
                    
#                     # Extract paper-level information
#                     citations = row.get('cited_by_count', 0) or 0
#                     is_sdl = row.get('SDL', 0) == 1
#                     is_ai = row.get('AI_Paper', 0) == 1
#                     is_robotics = row.get('Robotics_Paper', 0) == 1
                    
#                     # Parse topic and journal from raw_data
#                     topic = parse_primary_topic(row['raw_data'])
#                     journal = parse_journal(row['raw_data'])
                    
#                     # Parse corresponding author IDs (paper-level)
#                     corresponding_author_ids = parse_corresponding_author_ids(row['raw_data'])
                    
#                     # Process each author on this paper
#                     for authorship in authorships:
#                         author_id = authorship['author_id']
                        
#                         # Get this author's accumulated data
#                         data = author_data[author_id]
                        
#                         # Accumulate name (to find most common later)
#                         data['names'].append(authorship['author_name'])
                        
#                         # Accumulate citation data
#                         data['citations_list'].append(citations)
#                         data['citation_sum'] += citations
                        
#                         # Accumulate field/topic/journal
#                         data['fields'].append(field_name)
#                         if topic:
#                             data['topics'].append(topic)
#                         if journal:
#                             data['journals'].append(journal)
                        
#                         # Accumulate affiliations (using set for uniqueness)
#                         data['affiliations'].update(authorship['institutions'])
                        
#                         # Update counters
#                         data['paper_count'] += 1
                        
#                         if authorship['is_first']:
#                             data['first_author_count'] += 1
                        
#                         if authorship['is_last']:
#                             data['last_author_count'] += 1
                        
#                         # Check if this author is in corresponding_author_ids list
#                         if author_id in corresponding_author_ids:
#                             data['corresponding_author_count'] += 1
                        
#                         # SDL/AI/Robotics counters
#                         if is_sdl:
#                             data['sdl_count'] += 1
#                         if is_ai:
#                             data['ai_count'] += 1
#                         if is_robotics:
#                             data['robotics_count'] += 1
                    
#                     papers_in_year += 1
#                     total_papers += 1
                
#                 chunks_processed += 1
#                 if chunks_processed % 10 == 0:
#                     print(f"{chunks_processed * CHUNK_SIZE:,} rows...", end=' ', flush=True)
            
#             print(f"✓ {papers_in_year:,} papers")
        
#         except Exception as e:
#             print(f"✗ Error: {e}")
#             continue
    
#     print(f"  Total papers: {total_papers:,}")
#     print(f"  Unique authors: {len(author_data):,}")
    
#     return author_data


# # ============================================================================
# # PHASE 2: AGGREGATION
# # ============================================================================

# def aggregate_author_metrics(author_data):
#     """
#     Phase 2: Convert accumulated data into final metrics
    
#     Takes the accumulated lists/counters and computes:
#     - Most common values (name, top field, top topic, top journal)
#     - Averages (avg citations)
#     - Counts (unique fields, topics, journals, affiliations)
    
#     Returns: DataFrame with one row per author
#     """
    
#     print(f"\n{'='*70}")
#     print("PHASE 2: Computing final metrics")
#     print(f"{'='*70}")
#     print(f"Processing {len(author_data):,} unique authors...")
    
#     rows = []
    
#     for author_id, data in author_data.items():
        
#         # ====================================================================
#         # CORE IDENTITY
#         # ====================================================================
        
#         # Most common name (in case of name variants)
#         if data['names']:
#             # Counter finds most common element
#             author_name = Counter(data['names']).most_common(1)[0][0]
#         else:
#             author_name = ''
        
#         # ====================================================================
#         # PUBLICATION COUNTS
#         # ====================================================================
        
#         total_papers = data['paper_count']
#         first_author_papers = data['first_author_count']
#         last_author_papers = data['last_author_count']
#         corresponding_author_papers = data['corresponding_author_count']
        
#         # ====================================================================
#         # CITATION METRICS
#         # ====================================================================
        
#         total_citations = data['citation_sum']
        
#         # Average citations per paper
#         if data['citations_list']:
#             avg_citations = np.mean(data['citations_list'])
#         else:
#             avg_citations = 0
        
#         # ====================================================================
#         # FIELD ANALYSIS
#         # ====================================================================
        
#         if data['fields']:
#             # Find most common field
#             field_counter = Counter(data['fields'])
#             top_field_name, top_field_count = field_counter.most_common(1)[0]
#             num_unique_fields = len(field_counter)
#         else:
#             top_field_name, top_field_count, num_unique_fields = '', 0, 0
        
#         # ====================================================================
#         # TOPIC ANALYSIS
#         # ====================================================================
        
#         if data['topics']:
#             topic_counter = Counter(data['topics'])
#             top_topic_name, top_topic_count = topic_counter.most_common(1)[0]
#             num_unique_topics = len(topic_counter)
#         else:
#             top_topic_name, top_topic_count, num_unique_topics = '', 0, 0
        
#         # ====================================================================
#         # JOURNAL ANALYSIS
#         # ====================================================================
        
#         if data['journals']:
#             journal_counter = Counter(data['journals'])
#             top_journal_name, top_journal_count = journal_counter.most_common(1)[0]
#             num_unique_journals = len(journal_counter)
#         else:
#             top_journal_name, top_journal_count, num_unique_journals = '', 0, 0
        
#         # ====================================================================
#         # AFFILIATION ANALYSIS
#         # ====================================================================
        
#         num_affiliations = len(data['affiliations'])
        
#         # For top_affiliation, we'd need to track counts per institution
#         # For now, just take the first one as a placeholder
#         if data['affiliations']:
#             top_affiliation = list(data['affiliations'])[0]
#         else:
#             top_affiliation = ''
        
#         # ====================================================================
#         # SDL/AI/ROBOTICS COUNTS
#         # ====================================================================
        
#         sdl_papers = data['sdl_count']
#         ai_papers = data['ai_count']
#         robotics_papers = data['robotics_count']
        
#         # ====================================================================
#         # CREATE ROW
#         # ====================================================================
        
#         rows.append({
#             # Core identity
#             'author_id': author_id,
#             'author_name': author_name,
            
#             # Publication counts
#             'total_papers': total_papers,
#             'first_author_papers': first_author_papers,
#             'last_author_papers': last_author_papers,
#             'corresponding_author_papers': corresponding_author_papers,
            
#             # Citation metrics
#             'total_citations': int(total_citations),
#             'avg_citations_per_paper': round(avg_citations, 2),
            
#             # Field analysis
#             'top_field': top_field_name,
#             'top_field_paper_count': top_field_count,
#             'num_unique_fields': num_unique_fields,
            
#             # Topic analysis
#             'top_topic': top_topic_name,
#             'top_topic_paper_count': top_topic_count,
#             'num_unique_topics': num_unique_topics,
            
#             # Journal analysis
#             'top_journal': top_journal_name,
#             'top_journal_paper_count': top_journal_count,
#             'num_unique_journals': num_unique_journals,
            
#             # Affiliation
#             'num_affiliations': num_affiliations,
#             'top_affiliation': top_affiliation,
            
#             # SDL-specific
#             'sdl_papers': sdl_papers,
#             'ai_papers': ai_papers,
#             'robotics_papers': robotics_papers
#         })
    
#     print(f"  Created {len(rows):,} author records")
    
#     return pd.DataFrame(rows)


# # ============================================================================
# # MAIN EXECUTION
# # ============================================================================

# def main():
#     print("="*70)
#     print("BUILDING AUTHOR-LEVEL DATASET")
#     print("="*70)
#     print(f"\nProcessing {len(FIELDS)} fields: {', '.join(FIELDS.keys())}")
#     print(f"Years: {min(YEARS)}-{max(YEARS)-1}")
#     print(f"Output directory: {OUTPUT_DIR}\n")
    
#     # ========================================================================
#     # PHASE 1: Accumulate data from each field
#     # ========================================================================
    
#     # Initialize global author data dictionary
#     all_author_data = defaultdict(lambda: {
#         'names': [],
#         'citations_list': [],
#         'fields': [],
#         'topics': [],
#         'journals': [],
#         'affiliations': set(),
#         'paper_count': 0,
#         'first_author_count': 0,
#         'last_author_count': 0,
#         'corresponding_author_count': 0,
#         'citation_sum': 0,
#         'sdl_count': 0,
#         'ai_count': 0,
#         'robotics_count': 0
#     })
    
#     # Process each field
#     for field_name, field_dir in FIELDS.items():
#         if not field_dir.exists():
#             print(f"\n⚠️  Skipping {field_name}: directory not found")
#             continue
        
#         # Accumulate data for this field
#         field_author_data = process_field_accumulation(field_name, field_dir)
        
#         # Merge into global author data
#         print(f"  Merging {len(field_author_data):,} authors into global dataset...")
        
#         for author_id, data in field_author_data.items():
#             global_data = all_author_data[author_id]
            
#             # Merge lists
#             global_data['names'].extend(data['names'])
#             global_data['citations_list'].extend(data['citations_list'])
#             global_data['fields'].extend(data['fields'])
#             global_data['topics'].extend(data['topics'])
#             global_data['journals'].extend(data['journals'])
            
#             # Merge set
#             global_data['affiliations'].update(data['affiliations'])
            
#             # Add counters
#             global_data['paper_count'] += data['paper_count']
#             global_data['first_author_count'] += data['first_author_count']
#             global_data['last_author_count'] += data['last_author_count']
#             global_data['corresponding_author_count'] += data['corresponding_author_count']
#             global_data['citation_sum'] += data['citation_sum']
#             global_data['sdl_count'] += data['sdl_count']
#             global_data['ai_count'] += data['ai_count']
#             global_data['robotics_count'] += data['robotics_count']
        
#         print(f"  Global total: {len(all_author_data):,} unique authors")
    
#     # ========================================================================
#     # PHASE 2: Aggregate into final metrics
#     # ========================================================================
    
#     df_authors = aggregate_author_metrics(all_author_data)
    
#     # ========================================================================
#     # SAVE OUTPUT
#     # ========================================================================
    
#     output_file = OUTPUT_DIR / "author_metrics.csv"
#     print(f"\n{'='*70}")
#     print("SAVING OUTPUT")
#     print(f"{'='*70}")
#     print(f"File: {output_file}")
    
#     df_authors.to_csv(output_file, index=False)
    
#     file_size_mb = output_file.stat().st_size / (1024 * 1024)
#     print(f"Size: {file_size_mb:.1f} MB")
#     print(f"Rows: {len(df_authors):,}")
#     print(f"Columns: {len(df_authors.columns)}")
    
#     # ========================================================================
#     # SUMMARY STATISTICS
#     # ========================================================================
    
#     print(f"\n{'='*70}")
#     print("SUMMARY STATISTICS")
#     print(f"{'='*70}")
#     print(df_authors[['total_papers', 'total_citations', 
#                      'first_author_papers', 'last_author_papers']].describe())
    
#     print(f"\n{'='*70}")
#     print("TOP 10 AUTHORS BY TOTAL PAPERS")
#     print(f"{'='*70}")
#     top_authors = df_authors.nlargest(10, 'total_papers')[
#         ['author_name', 'total_papers', 'total_citations', 'top_field', 'top_topic']
#     ]
#     print(top_authors.to_string(index=False))
    
#     print(f"\n{'='*70}")
#     print("✅ COMPLETE!")
#     print(f"{'='*70}")
#     print(f"Output: {output_file}\n")


# if __name__ == "__main__":
#     main()
"""
Build comprehensive author-level dataset from paper TSV files
OPTIMIZED FOR HPC with multiprocessing parallelization across fields

Phase 1: Accumulate raw data for each author (PARALLELIZED BY FIELD)
Phase 2: Aggregate accumulated data into final metrics
"""

import pandas as pd
import json
from collections import defaultdict, Counter
import numpy as np
from pathlib import Path
from multiprocessing import Pool, cpu_count
import sys
import os

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")
DATA_DIR = PROJECT_DIR / "data/fields"
OUTPUT_DIR = PROJECT_DIR / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Fields to process
FIELDS = {
    'chemistry': DATA_DIR / "chemistry",
    'materials_science': DATA_DIR / "material_science", 
    'engineering': DATA_DIR / "engineering_redownload",
    'computer_science': DATA_DIR / "computer_science"
}

YEARS = range(2012, 2026)
CHUNK_SIZE = 500000 # Process in chunks to manage memory

# Multiprocessing configuration
NUM_PROCESSES = None  # None = use all available CPUs

# ============================================================================
# EXTRACTION FUNCTIONS
# ============================================================================

def parse_authorships(raw_data_json):
    """
    Extract authorship information from raw_data JSON
    
    Returns list of dicts with:
    - author_id: OpenAlex ID (cleaned)
    - author_name: Display name
    - position: Index in authorship list (0=first, last=last author)
    - institutions: List of institution IDs for this author
    """
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
    """
    Extract primary topic from raw_data
    Primary topic is the first topic in the topics list
    
    Returns: topic display_name or None
    """
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
    """
    Extract journal name from raw_data
    Journal is in primary_location -> source -> display_name
    
    Returns: journal name or None
    """
    if pd.isna(raw_data_json) or raw_data_json == '':
        return None
    
    try:
        data = json.loads(raw_data_json)
        journal = data.get('primary_location', {}).get('source', {}).get('display_name')
        return journal
    except:
        return None


def parse_corresponding_author_ids(raw_data_json):
    """
    Extract corresponding author IDs from raw_data
    This is a paper-level field, more reliable than authorship-level is_corresponding
    
    Returns: list of author IDs (cleaned) or empty list
    """
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
    """
    Extract cited_by_count from raw_data
    
    Returns: citation count (int) or 0
    """
    if pd.isna(raw_data_json) or raw_data_json == '':
        return 0
    
    try:
        data = json.loads(raw_data_json)
        cited_by_count = data.get('cited_by_count', 0)
        return cited_by_count if cited_by_count else 0
    except:
        return 0


# ============================================================================
# PHASE 1: ACCUMULATION (PARALLELIZED)
# ============================================================================

def process_field_accumulation(field_tuple):
    """
    Phase 1: Accumulate raw data for each author in a single field
    This function is called in parallel for each field
    
    Args:
        field_tuple: (field_name, field_dir) tuple
    
    Returns: 
        dict of author_id -> accumulated data for this field
    """
    
    field_name, field_dir = field_tuple
    
    print(f"\n{'='*70}", flush=True)
    print(f"PHASE 1: Processing {field_name.upper()} (PID: {os.getpid()})", flush=True)
    print(f"{'='*70}", flush=True)
    
    # Initialize author data structure for this field
    author_data = defaultdict(lambda: {
        # Lists to accumulate values across papers
        'names': [],
        'citations_list': [],
        'fields': [],
        'topics': [],
        'journals': [],
        
        # Sets for unique values
        'affiliations': set(),
        
        # Counters
        'paper_count': 0,
        'first_author_count': 0,
        'last_author_count': 0,
        'corresponding_author_count': 0,
        'citation_sum': 0,
        
        # SDL/AI/Robotics counts
        'sdl_count': 0,
        'ai_count': 0,
        'robotics_count': 0
    })
    
    total_papers = 0
    
    for year in YEARS:
        tsv_file = field_dir / f"{field_name}_{year}.tsv"
        
        if not tsv_file.exists():
            print(f"  ⚠️  Skipping {year}: file not found", flush=True)
            continue
        
        print(f"  Processing {year}...", end=' ', flush=True)
        
        # Columns we need from TSV
        # Note: cited_by_count might not exist in all files
        required_columns = [
            'raw_data',
            'author_count',
            'SDL',
            'AI_Paper',
            'Robotics_Paper'
        ]
        
        # Try to determine which columns actually exist
        try:
            sample_df = pd.read_csv(tsv_file, sep='\t', nrows=1)
            available_columns = sample_df.columns.tolist()
            
            # Check for citation column variants
            citation_col = None
            for col in ['cited_by_count', 'citation_count', 'citations']:
                if col in available_columns:
                    citation_col = col
                    break
            
            columns_to_read = required_columns.copy()
            if citation_col:
                columns_to_read.append(citation_col)
            
            # Filter to only columns that exist
            columns_to_read = [col for col in columns_to_read if col in available_columns]
            
        except Exception as e:
            print(f"✗ Error reading file structure: {e}", flush=True)
            continue
        
        chunks_processed = 0
        papers_in_year = 0
        
        try:
            # Read in chunks to manage memory
            for chunk in pd.read_csv(tsv_file, sep='\t', usecols=columns_to_read, 
                                    chunksize=CHUNK_SIZE, low_memory=False):
                
                for _, row in chunk.iterrows():
                    # Parse authorships from raw_data
                    authorships = parse_authorships(row['raw_data'])
                    
                    if not authorships:
                        continue
                    
                    # Extract paper-level information
                    # Handle citations - use 0 if column doesn't exist
                    if citation_col and citation_col in row:
                        citations = row.get(citation_col, 0) or 0
                    else:
                        citations = 0
                    
                    is_sdl = row.get('SDL', 0) == 1
                    is_ai = row.get('AI_Paper', 0) == 1
                    is_robotics = row.get('Robotics_Paper', 0) == 1
                    
                    # Parse topic and journal from raw_data
                    topic = parse_primary_topic(row['raw_data'])
                    journal = parse_journal(row['raw_data'])
                    
                    # Parse corresponding author IDs (paper-level)
                    corresponding_author_ids = parse_corresponding_author_ids(row['raw_data'])
                    
                    # Process each author on this paper
                    for authorship in authorships:
                        author_id = authorship['author_id']
                        
                        # Get this author's accumulated data
                        data = author_data[author_id]
                        
                        # Accumulate name
                        data['names'].append(authorship['author_name'])
                        
                        # Accumulate citation data
                        data['citations_list'].append(citations)
                        data['citation_sum'] += citations
                        
                        # Accumulate field/topic/journal
                        data['fields'].append(field_name)
                        if topic:
                            data['topics'].append(topic)
                        if journal:
                            data['journals'].append(journal)
                        
                        # Accumulate affiliations
                        data['affiliations'].update(authorship['institutions'])
                        
                        # Update counters
                        data['paper_count'] += 1
                        
                        if authorship['is_first']:
                            data['first_author_count'] += 1
                        
                        if authorship['is_last']:
                            data['last_author_count'] += 1
                        
                        # Check if this author is in corresponding_author_ids list
                        if author_id in corresponding_author_ids:
                            data['corresponding_author_count'] += 1
                        
                        # SDL/AI/Robotics counters
                        if is_sdl:
                            data['sdl_count'] += 1
                        if is_ai:
                            data['ai_count'] += 1
                        if is_robotics:
                            data['robotics_count'] += 1
                    
                    papers_in_year += 1
                    total_papers += 1
                
                chunks_processed += 1
                if chunks_processed % 10 == 0:
                    print(f"{chunks_processed * CHUNK_SIZE:,} rows...", end=' ', flush=True)
            
            print(f"✓ {papers_in_year:,} papers", flush=True)
        
        except Exception as e:
            print(f"✗ Error: {e}", flush=True)
            continue
    
    print(f"  {field_name} COMPLETE: {total_papers:,} papers, {len(author_data):,} authors", flush=True)
    
    return (field_name, author_data)


# ============================================================================
# HELPER: MERGE AUTHOR DATA
# ============================================================================

def merge_author_data_dicts(dict1, dict2):
    """
    Merge two author data dictionaries
    Used to combine results from different fields
    """
    for author_id, data in dict2.items():
        global_data = dict1[author_id]
        
        # Merge lists
        global_data['names'].extend(data['names'])
        global_data['citations_list'].extend(data['citations_list'])
        global_data['fields'].extend(data['fields'])
        global_data['topics'].extend(data['topics'])
        global_data['journals'].extend(data['journals'])
        
        # Merge set
        global_data['affiliations'].update(data['affiliations'])
        
        # Add counters
        global_data['paper_count'] += data['paper_count']
        global_data['first_author_count'] += data['first_author_count']
        global_data['last_author_count'] += data['last_author_count']
        global_data['corresponding_author_count'] += data['corresponding_author_count']
        global_data['citation_sum'] += data['citation_sum']
        global_data['sdl_count'] += data['sdl_count']
        global_data['ai_count'] += data['ai_count']
        global_data['robotics_count'] += data['robotics_count']


# ============================================================================
# PHASE 2: AGGREGATION
# ============================================================================

def aggregate_author_metrics(author_data):
    """
    Phase 2: Convert accumulated data into final metrics
    """
    
    print(f"\n{'='*70}")
    print("PHASE 2: Computing final metrics")
    print(f"{'='*70}")
    print(f"Processing {len(author_data):,} unique authors...")
    
    rows = []
    
    for idx, (author_id, data) in enumerate(author_data.items()):
        # Progress indicator
        if (idx + 1) % 100000 == 0:
            print(f"  Processed {idx + 1:,} authors...", flush=True)
        
        # Core identity
        if data['names']:
            author_name = Counter(data['names']).most_common(1)[0][0]
        else:
            author_name = ''
        
        # Publication counts
        total_papers = data['paper_count']
        first_author_papers = data['first_author_count']
        last_author_papers = data['last_author_count']
        corresponding_author_papers = data['corresponding_author_count']
        
        # Citation metrics
        total_citations = data['citation_sum']
        avg_citations = np.mean(data['citations_list']) if data['citations_list'] else 0
        
        # Field analysis
        if data['fields']:
            field_counter = Counter(data['fields'])
            top_field_name, top_field_count = field_counter.most_common(1)[0]
            num_unique_fields = len(field_counter)
        else:
            top_field_name, top_field_count, num_unique_fields = '', 0, 0
        
        # Topic analysis
        if data['topics']:
            topic_counter = Counter(data['topics'])
            top_topic_name, top_topic_count = topic_counter.most_common(1)[0]
            num_unique_topics = len(topic_counter)
        else:
            top_topic_name, top_topic_count, num_unique_topics = '', 0, 0
        
        # Journal analysis
        if data['journals']:
            journal_counter = Counter(data['journals'])
            top_journal_name, top_journal_count = journal_counter.most_common(1)[0]
            num_unique_journals = len(journal_counter)
        else:
            top_journal_name, top_journal_count, num_unique_journals = '', 0, 0
        
        # Affiliation analysis
        num_affiliations = len(data['affiliations'])
        top_affiliation = list(data['affiliations'])[0] if data['affiliations'] else ''
        
        # SDL/AI/Robotics counts
        sdl_papers = data['sdl_count']
        ai_papers = data['ai_count']
        robotics_papers = data['robotics_count']
        
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
            'sdl_papers': sdl_papers,
            'ai_papers': ai_papers,
            'robotics_papers': robotics_papers
        })
    
    print(f"  Created {len(rows):,} author records")
    
    return pd.DataFrame(rows)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("="*70)
    print("BUILDING AUTHOR-LEVEL DATASET (PARALLEL VERSION)")
    print("="*70)
    print(f"\nProcessing {len(FIELDS)} fields: {', '.join(FIELDS.keys())}")
    print(f"Years: {min(YEARS)}-{max(YEARS)-1}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Determine number of processes
    num_processes = NUM_PROCESSES if NUM_PROCESSES else cpu_count()
    print(f"Parallel processing: {num_processes} processes")
    print(f"Chunk size: {CHUNK_SIZE:,} rows\n")
    
    # ========================================================================
    # PHASE 1: Accumulate data from each field IN PARALLEL
    # ========================================================================
    
    print("="*70)
    print("PHASE 1: PARALLEL FIELD PROCESSING")
    print("="*70)
    print("Processing fields in parallel...\n")
    
    # Filter to only existing field directories
    fields_to_process = [(name, path) for name, path in FIELDS.items() if path.exists()]
    
    if not fields_to_process:
        print("ERROR: No field directories found!")
        return
    
    print(f"Fields to process: {len(fields_to_process)}")
    for name, path in fields_to_process:
        print(f"  - {name}: {path}")
    print()
    
    # Process fields in parallel
    with Pool(processes=min(num_processes, len(fields_to_process))) as pool:
        results = pool.map(process_field_accumulation, fields_to_process)
    
    print("\n" + "="*70)
    print("MERGING FIELD RESULTS")
    print("="*70)
    
    # Initialize global author data dictionary
    all_author_data = defaultdict(lambda: {
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
    })
    
    # Merge results from each field
    for field_name, field_author_data in results:
        print(f"  Merging {field_name}: {len(field_author_data):,} authors")
        merge_author_data_dicts(all_author_data, field_author_data)
    
    print(f"\n  Global total: {len(all_author_data):,} unique authors")
    
    # ========================================================================
    # PHASE 2: Aggregate into final metrics
    # ========================================================================
    
    df_authors = aggregate_author_metrics(all_author_data)
    
    # ========================================================================
    # SAVE OUTPUT
    # ========================================================================
    
    output_file = OUTPUT_DIR / "author_metrics.csv"
    print(f"\n{'='*70}")
    print("SAVING OUTPUT")
    print(f"{'='*70}")
    print(f"File: {output_file}")
    
    df_authors.to_csv(output_file, index=False)
    
    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"Size: {file_size_mb:.1f} MB")
    print(f"Rows: {len(df_authors):,}")
    print(f"Columns: {len(df_authors.columns)}")
    
    # ========================================================================
    # SUMMARY STATISTICS
    # ========================================================================
    
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


if __name__ == "__main__":
    main()