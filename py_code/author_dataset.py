# # # # """
# # # # Build comprehensive author-level dataset from paper TSV files
# # # # Optimized for HPC with two-phase processing

# # # # Phase 1: Accumulate raw data for each author across all papers
# # # # Phase 2: Aggregate accumulated data into final metrics
# # # # """
# import pandas as pd
# import json
# from collections import Counter
# import numpy as np
# from pathlib import Path
# import sys
# import os
# import traceback

# # ============================================================================
# # CONFIGURATION
# # ============================================================================

# PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# # FIXED: Correct paths based on actual data structure
# FIELDS = {
#     'chemistry': PROJECT_DIR / "data/fields" / "chemistry",
#     'materials_science': PROJECT_DIR / "data/fields" / "material_science", 
#     'engineering': PROJECT_DIR / "data/fields" / "engineering",
#     'computer_science': PROJECT_DIR / "data/fields" / "computer_science"
# }

# OUTPUT_DIR = PROJECT_DIR / "data" / "test"
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# csv_file = OUTPUT_DIR / "author_metrics11.csv"
# output_file_eda = OUTPUT_DIR / "author_metrics11_eda.txt"

# YEARS = range(2012, 2026)
# CHUNK_SIZE = 500000  # Process in chunks to manage memory

# # ============================================================================
# # EXTRACTION FUNCTIONS
# # ============================================================================

# def parse_authorships(raw_data_json):
#     """Extract authorship information from raw_data JSON"""
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
#     """Extract primary topic from raw_data"""
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
#     """Extract journal name from raw_data"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return None
    
#     try:
#         data = json.loads(raw_data_json)
#         journal = data.get('primary_location', {}).get('source', {}).get('display_name')
#         return journal
#     except:
#         return None


# def parse_corresponding_author_ids(raw_data_json):
#     """Extract corresponding author IDs from raw_data"""
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


# def parse_cited_by_count(raw_data_json):
#     """Extract cited_by_count from raw_data"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return 0
    
#     try:
#         data = json.loads(raw_data_json)
#         cited_by_count = data.get('cited_by_count', 0)
#         return cited_by_count if cited_by_count else 0
#     except:
#         return 0


# # ============================================================================
# # AUTHOR DATA STRUCTURE FACTORY
# # ============================================================================

# def create_author_entry():
#     """Factory function to create new author data entry"""
#     return {
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
#     }


# # ============================================================================
# # PHASE 1: ACCUMULATION (SEQUENTIAL)
# # ============================================================================

# def process_field_accumulation(field_name, field_dir, all_author_data):
#     """
#     Phase 1: Accumulate raw data for each author in a single field
#     Processes field sequentially and adds to global author_data dictionary
#     """
    
#     print(f"\n{'='*70}", flush=True)
#     print(f"PROCESSING: {field_name.upper()}", flush=True)
#     print(f"Directory: {field_dir}", flush=True)
#     print(f"{'='*70}", flush=True)
    
#     # Verify directory exists
#     if not field_dir.exists():
#         print(f"ERROR: Directory does not exist: {field_dir}", flush=True)
#         return 0, 0
    
#     total_papers = 0
#     total_errors = 0
    
#     for year in YEARS:
#         # Check multiple possible filename patterns
#         possible_files = [
#             field_dir / f"{field_name}_{year}.tsv",
#             field_dir / f"{field_name.replace('_', '')}_{year}.tsv",
#         ]
        
#         tsv_file = None
#         for possible_file in possible_files:
#             if possible_file.exists():
#                 tsv_file = possible_file
#                 break
        
#         if not tsv_file:
#             continue  # Skip silently if file doesn't exist
        
#         print(f"  {year}: {tsv_file.name}...", end=' ', flush=True)
        
#         papers_in_year = 0
#         errors_in_year = 0
        
#         try:
#             # First check if file is readable and get columns
#             try:
#                 sample = pd.read_csv(tsv_file, sep='\t', nrows=5)
#                 available_cols = set(sample.columns)
#             except Exception as e:
#                 print(f"✗ Cannot read file: {e}", flush=True)
#                 continue
            
#             # Determine which columns to read
#             required = ['raw_data', 'SDL', 'AI_Paper', 'Robotics_Paper']
#             columns_to_read = [col for col in required if col in available_cols]
            
#             if 'raw_data' not in columns_to_read:
#                 print(f"✗ Missing raw_data column", flush=True)
#                 continue
            
#             # Read in chunks
#             chunk_num = 0
#             for chunk in pd.read_csv(tsv_file, sep='\t', usecols=columns_to_read,
#                                     chunksize=CHUNK_SIZE, low_memory=False,
#                                     on_bad_lines='skip'):  # Skip malformed lines
                
#                 chunk_num += 1
                
#                 for idx, row in chunk.iterrows():
#                     try:
#                         # Parse authorships
#                         authorships = parse_authorships(row.get('raw_data'))
                        
#                         if not authorships:
#                             continue
                        
#                         # Extract paper-level info
#                         citations = parse_cited_by_count(row.get('raw_data'))
#                         is_sdl = row.get('SDL', 0) == 1
#                         is_ai = row.get('AI_Paper', 0) == 1
#                         is_robotics = row.get('Robotics_Paper', 0) == 1
                        
#                         topic = parse_primary_topic(row.get('raw_data'))
#                         journal = parse_journal(row.get('raw_data'))
#                         corresponding_ids = parse_corresponding_author_ids(row.get('raw_data'))
                        
#                         # Process each author
#                         for authorship in authorships:
#                             author_id = authorship['author_id']
                            
#                             # Initialize author entry if new
#                             if author_id not in all_author_data:
#                                 all_author_data[author_id] = create_author_entry()
                            
#                             data = all_author_data[author_id]
                            
#                             # Accumulate data
#                             data['names'].append(authorship['author_name'])
#                             data['citations_list'].append(citations)
#                             data['citation_sum'] += citations
#                             data['fields'].append(field_name)
                            
#                             if topic:
#                                 data['topics'].append(topic)
#                             if journal:
#                                 data['journals'].append(journal)
                            
#                             data['affiliations'].update(authorship['institutions'])
#                             data['paper_count'] += 1
                            
#                             if authorship['is_first']:
#                                 data['first_author_count'] += 1
#                             if authorship['is_last']:
#                                 data['last_author_count'] += 1
#                             if author_id in corresponding_ids:
#                                 data['corresponding_author_count'] += 1
                            
#                             if is_sdl:
#                                 data['sdl_count'] += 1
#                             if is_ai:
#                                 data['ai_count'] += 1
#                             if is_robotics:
#                                 data['robotics_count'] += 1
                        
#                         papers_in_year += 1
#                         total_papers += 1
                    
#                     except Exception as e:
#                         errors_in_year += 1
#                         total_errors += 1
#                         if errors_in_year <= 5:  # Only print first 5 errors per year
#                             print(f"\n  Row error: {str(e)[:100]}", flush=True)
                
#                 # Progress within year
#                 if chunk_num % 10 == 0:
#                     print(f".", end='', flush=True)
            
#             print(f" ✓ {papers_in_year:,} papers", flush=True)
        
#         except Exception as e:
#             print(f" ✗ File error: {str(e)[:200]}", flush=True)
#             traceback.print_exc()
#             continue
    
#     print(f"{field_name} COMPLETE:", flush=True)
#     print(f"  Papers processed: {total_papers:,}", flush=True)
#     print(f"  Errors: {total_errors:,}", flush=True)
    
#     return total_papers, total_errors


# # ============================================================================
# # PHASE 2: AGGREGATION
# # ============================================================================

# def aggregate_author_metrics(all_author_data):
#     """Phase 2: Convert accumulated data into final metrics"""
    
#     print(f"\n{'='*70}")
#     print("PHASE 2: Computing final metrics")
#     print(f"{'='*70}")
#     print(f"Processing {len(all_author_data):,} unique authors...")
    
#     rows = []
    
#     for idx, (author_id, data) in enumerate(all_author_data.items()):
#         if (idx + 1) % 100000 == 0:
#             print(f"  {idx + 1:,} authors processed...", flush=True)
        
#         # Most common name
#         author_name = Counter(data['names']).most_common(1)[0][0] if data['names'] else ''
        
#         # Counts
#         total_papers = data['paper_count']
#         first_author_papers = data['first_author_count']
#         last_author_papers = data['last_author_count']
#         corresponding_author_papers = data['corresponding_author_count']
        
#         # Citations
#         total_citations = data['citation_sum']
#         avg_citations = np.mean(data['citations_list']) if data['citations_list'] else 0
        
#         # Field
#         if data['fields']:
#             field_counter = Counter(data['fields'])
#             top_field_name, top_field_count = field_counter.most_common(1)[0]
#             num_unique_fields = len(field_counter)
#         else:
#             top_field_name, top_field_count, num_unique_fields = '', 0, 0
        
#         # Topic
#         if data['topics']:
#             topic_counter = Counter(data['topics'])
#             top_topic_name, top_topic_count = topic_counter.most_common(1)[0]
#             num_unique_topics = len(topic_counter)
#         else:
#             top_topic_name, top_topic_count, num_unique_topics = '', 0, 0
        
#         # Journal
#         if data['journals']:
#             journal_counter = Counter(data['journals'])
#             top_journal_name, top_journal_count = journal_counter.most_common(1)[0]
#             num_unique_journals = len(journal_counter)
#         else:
#             top_journal_name, top_journal_count, num_unique_journals = '', 0, 0
        
#         # Affiliations
#         num_affiliations = len(data['affiliations'])
#         top_affiliation = list(data['affiliations'])[0] if data['affiliations'] else ''
        
#         rows.append({
#             'author_id': author_id,
#             'author_name': author_name,
#             'total_papers': total_papers,
#             'first_author_papers': first_author_papers,
#             'last_author_papers': last_author_papers,
#             'corresponding_author_papers': corresponding_author_papers,
#             'total_citations': int(total_citations),
#             'avg_citations_per_paper': round(avg_citations, 2),
#             'top_field': top_field_name,
#             'top_field_paper_count': top_field_count,
#             'num_unique_fields': num_unique_fields,
#             'top_topic': top_topic_name,
#             'top_topic_paper_count': top_topic_count,
#             'num_unique_topics': num_unique_topics,
#             'top_journal': top_journal_name,
#             'top_journal_paper_count': top_journal_count,
#             'num_unique_journals': num_unique_journals,
#             'num_affiliations': num_affiliations,
#             'top_affiliation': top_affiliation,
#             'sdl_papers': data['sdl_count'],
#             'ai_papers': data['ai_count'],
#             'robotics_papers': data['robotics_count']
#         })
    
#     return pd.DataFrame(rows)



# def perform_eda_and_save(csv_file_path, output_file_path=None):
#     """
#     Perform comprehensive EDA on author dataset and save results to file
    
#     Args:
#         csv_file_path: Path to author_metrics.csv
#         output_file_path: Path to save EDA report (optional, defaults to same dir as csv)
#     """
#     import pandas as pd
#     import numpy as np
#     from pathlib import Path
#     from datetime import datetime
    
#     print(f"\n{'='*70}")
#     print("EXPLORATORY DATA ANALYSIS - AUTHOR DATASET")
#     print(f"{'='*70}\n")
    
#     # Load data
#     print(f"Loading data from: {csv_file_path}")
#     df = pd.read_csv(csv_file_path)
    
#     # Set output file path
#     if output_file_path is None:
#         csv_path = Path(csv_file_path)
#         output_file_path = csv_path.parent / f"author_dataset_EDA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
#     print(f"Saving EDA report to: {output_file_path}\n")
    
#     # Open file for writing
#     with open(output_file_path, 'w', encoding='utf-8') as f:
        
#         # Header
#         f.write("="*80 + "\n")
#         f.write("EXPLORATORY DATA ANALYSIS - AUTHOR DATASET\n")
#         f.write("="*80 + "\n")
#         f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
#         f.write(f"Source file: {csv_file_path}\n")
#         f.write("="*80 + "\n\n")
        
#         # ====================================================================
#         # 1. BASIC DATASET INFO
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("1. DATASET OVERVIEW\n")
#         f.write("="*80 + "\n\n")
        
#         f.write(f"Total authors: {len(df):,}\n")
#         f.write(f"Total columns: {len(df.columns)}\n")
#         f.write(f"Memory usage: {df.memory_usage(deep=True).sum() / 1e6:.2f} MB\n\n")
        
#         f.write("Columns:\n")
#         for i, col in enumerate(df.columns, 1):
#             f.write(f"  {i:2d}. {col}\n")
#         f.write("\n")
        
#         # ====================================================================
#         # 2. MISSING VALUES ANALYSIS
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("2. MISSING VALUES ANALYSIS\n")
#         f.write("="*80 + "\n\n")
        
#         missing = df.isnull().sum()
#         missing_pct = (missing / len(df) * 100).round(2)
        
#         if missing.sum() == 0:
#             f.write("✓ No missing values found!\n\n")
#         else:
#             f.write("Columns with missing values:\n")
#             for col in missing[missing > 0].index:
#                 f.write(f"  {col}: {missing[col]:,} ({missing_pct[col]:.2f}%)\n")
#             f.write("\n")
        
#         # Empty string check for key columns
#         f.write("Empty string check:\n")
#         empty_checks = {
#             'author_name': (df['author_name'] == '').sum(),
#             'top_field': (df['top_field'] == '').sum(),
#             'top_topic': (df['top_topic'] == '').sum(),
#             'top_journal': (df['top_journal'] == '').sum()
#         }
#         for col, count in empty_checks.items():
#             if count > 0:
#                 f.write(f"  {col}: {count:,} ({count/len(df)*100:.2f}%)\n")
#         f.write("\n")
        
#         # ====================================================================
#         # 3. PUBLICATION COUNTS STATISTICS
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("3. PUBLICATION COUNTS STATISTICS\n")
#         f.write("="*80 + "\n\n")
        
#         pub_cols = ['total_papers', 'first_author_papers', 'last_author_papers', 
#                     'corresponding_author_papers', 'sdl_papers', 'ai_papers', 'robotics_papers']
        
#         f.write(df[pub_cols].describe().to_string())
#         f.write("\n\n")
        
#         # Distribution breakdowns
#         f.write("Publication count distributions:\n\n")
        
#         for col in ['total_papers', 'first_author_papers', 'last_author_papers']:
#             f.write(f"{col}:\n")
#             bins = [1, 2, 5, 10, 20, 50, 100, 500, 1000, np.inf]
#             labels = ['1', '2-4', '5-9', '10-19', '20-49', '50-99', '100-499', '500-999', '1000+']
            
#             try:
#                 dist = pd.cut(df[col], bins=bins, labels=labels, right=False)
#                 counts = dist.value_counts().sort_index()
#                 for label, count in counts.items():
#                     pct = count / len(df) * 100
#                     f.write(f"  {label:10s}: {count:8,} ({pct:5.2f}%)\n")
#             except Exception as e:
#                 f.write(f"  Error creating distribution: {e}\n")
            
#             f.write("\n")
        
#         # ====================================================================
#         # 4. CITATION STATISTICS
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("4. CITATION STATISTICS\n")
#         f.write("="*80 + "\n\n")
        
#         cite_cols = ['total_citations', 'avg_citations_per_paper']
#         f.write(df[cite_cols].describe().to_string())
#         f.write("\n\n")
        
#         # Highly cited authors
#         f.write("Citation milestones:\n")
#         f.write(f"  Authors with 0 citations: {(df['total_citations'] == 0).sum():,}\n")
#         f.write(f"  Authors with 100+ citations: {(df['total_citations'] >= 100).sum():,}\n")
#         f.write(f"  Authors with 1,000+ citations: {(df['total_citations'] >= 1000).sum():,}\n")
#         f.write(f"  Authors with 10,000+ citations: {(df['total_citations'] >= 10000).sum():,}\n")
#         f.write(f"  Authors with 100,000+ citations: {(df['total_citations'] >= 100000).sum():,}\n")
#         f.write("\n")
        
#         # ====================================================================
#         # 5. FIELD DISTRIBUTION
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("5. FIELD DISTRIBUTION\n")
#         f.write("="*80 + "\n\n")
        
#         field_counts = df['top_field'].value_counts()
#         f.write("Authors by top field:\n")
#         for field, count in field_counts.items():
#             pct = count / len(df) * 100
#             f.write(f"  {field:25s}: {count:8,} ({pct:5.2f}%)\n")
#         f.write("\n")
        
#         # Multi-field authors
#         f.write("Multi-field activity:\n")
#         multi_field_dist = df['num_unique_fields'].value_counts().sort_index()
#         for num_fields, count in multi_field_dist.items():
#             pct = count / len(df) * 100
#             f.write(f"  {num_fields} fields: {count:8,} ({pct:5.2f}%)\n")
#         f.write("\n")
        
#         # ====================================================================
#         # 6. TOP AUTHORS
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("6. TOP AUTHORS\n")
#         f.write("="*80 + "\n\n")
        
#         # Top by total papers
#         f.write("Top 20 authors by total papers:\n")
#         f.write("-" * 80 + "\n")
#         top_papers = df.nlargest(20, 'total_papers')[
#             ['author_name', 'total_papers', 'total_citations', 'top_field', 'top_topic', 'sdl_papers']
#         ]
#         f.write(top_papers.to_string(index=False, max_colwidth=30))
#         f.write("\n\n")
        
#         # Top by citations
#         f.write("Top 20 authors by total citations:\n")
#         f.write("-" * 80 + "\n")
#         top_cites = df.nlargest(20, 'total_citations')[
#             ['author_name', 'total_papers', 'total_citations', 'avg_citations_per_paper', 'top_field']
#         ]
#         f.write(top_cites.to_string(index=False, max_colwidth=30))
#         f.write("\n\n")
        
#         # Top by average citations (min 10 papers to avoid noise)
#         f.write("Top 20 authors by avg citations per paper (min 10 papers):\n")
#         f.write("-" * 80 + "\n")
#         top_avg = df[df['total_papers'] >= 10].nlargest(20, 'avg_citations_per_paper')[
#             ['author_name', 'total_papers', 'total_citations', 'avg_citations_per_paper', 'top_field']
#         ]
#         f.write(top_avg.to_string(index=False, max_colwidth=30))
#         f.write("\n\n")
        
#         # ====================================================================
#         # 7. SDL/AI/ROBOTICS ANALYSIS
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("7. SDL/AI/ROBOTICS INVOLVEMENT\n")
#         f.write("="*80 + "\n\n")
        
#         f.write("Authors with SDL/AI/Robotics papers:\n")
#         f.write(f"  Authors with ≥1 SDL paper: {(df['sdl_papers'] > 0).sum():,}\n")
#         f.write(f"  Authors with ≥5 SDL papers: {(df['sdl_papers'] >= 5).sum():,}\n")
#         f.write(f"  Authors with ≥10 SDL papers: {(df['sdl_papers'] >= 10).sum():,}\n\n")
        
#         f.write(f"  Authors with ≥1 AI paper: {(df['ai_papers'] > 0).sum():,}\n")
#         f.write(f"  Authors with ≥10 AI papers: {(df['ai_papers'] >= 10).sum():,}\n\n")
        
#         f.write(f"  Authors with ≥1 Robotics paper: {(df['robotics_papers'] > 0).sum():,}\n")
#         f.write(f"  Authors with ≥10 Robotics papers: {(df['robotics_papers'] >= 10).sum():,}\n\n")
        
#         # Top SDL authors
#         if (df['sdl_papers'] > 0).sum() > 0:
#             f.write("Top 20 SDL authors:\n")
#             f.write("-" * 80 + "\n")
#             top_sdl = df[df['sdl_papers'] > 0].nlargest(20, 'sdl_papers')[
#                 ['author_name', 'total_papers', 'sdl_papers', 'ai_papers', 'robotics_papers', 'top_field']
#             ]
#             f.write(top_sdl.to_string(index=False, max_colwidth=30))
#             f.write("\n\n")
        
#         # ====================================================================
#         # 8. TOPIC ANALYSIS
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("8. TOPIC ANALYSIS\n")
#         f.write("="*80 + "\n\n")
        
#         # Top topics
#         f.write("Top 30 research topics by author count:\n")
#         topic_counts = df['top_topic'].value_counts().head(30)
#         for i, (topic, count) in enumerate(topic_counts.items(), 1):
#             pct = count / len(df) * 100
#             f.write(f"  {i:2d}. {topic[:50]:50s}: {count:6,} ({pct:4.2f}%)\n")
#         f.write("\n")
        
#         # Topic diversity
#         f.write("Topic diversity:\n")
#         f.write(f"  Unique topics in dataset: {df['top_topic'].nunique():,}\n")
#         f.write(f"  Avg topics per author: {df['num_unique_topics'].mean():.2f}\n")
#         f.write(f"  Max topics by single author: {df['num_unique_topics'].max()}\n\n")
        
#         # ====================================================================
#         # 9. JOURNAL ANALYSIS
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("9. JOURNAL ANALYSIS\n")
#         f.write("="*80 + "\n\n")
        
#         # Top journals
#         f.write("Top 30 journals by author count:\n")
#         journal_counts = df['top_journal'].value_counts().head(30)
#         for i, (journal, count) in enumerate(journal_counts.items(), 1):
#             pct = count / len(df) * 100
#             f.write(f"  {i:2d}. {journal[:50]:50s}: {count:6,} ({pct:4.2f}%)\n")
#         f.write("\n")
        
#         f.write("Journal diversity:\n")
#         f.write(f"  Unique journals in dataset: {df['top_journal'].nunique():,}\n")
#         f.write(f"  Avg journals per author: {df['num_unique_journals'].mean():.2f}\n")
#         f.write(f"  Max journals by single author: {df['num_unique_journals'].max()}\n\n")
        
#         # ====================================================================
#         # 10. AUTHORSHIP POSITION ANALYSIS
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("10. AUTHORSHIP POSITION ANALYSIS\n")
#         f.write("="*80 + "\n\n")
        
#         # First author stats
#         f.write("First authorship:\n")
#         f.write(f"  Authors who were NEVER first author: {(df['first_author_papers'] == 0).sum():,}\n")
#         f.write(f"  Authors who were ALWAYS first author: {(df['first_author_papers'] == df['total_papers']).sum():,}\n")
#         f.write(f"  Avg first author papers: {df['first_author_papers'].mean():.2f}\n\n")
        
#         # Last author stats
#         f.write("Last authorship:\n")
#         f.write(f"  Authors who were NEVER last author: {(df['last_author_papers'] == 0).sum():,}\n")
#         f.write(f"  Authors who were ALWAYS last author: {(df['last_author_papers'] == df['total_papers']).sum():,}\n")
#         f.write(f"  Avg last author papers: {df['last_author_papers'].mean():.2f}\n\n")
        
#         # Corresponding author stats
#         f.write("Corresponding authorship:\n")
#         f.write(f"  Authors who were NEVER corresponding: {(df['corresponding_author_papers'] == 0).sum():,}\n")
#         f.write(f"  Authors corresponding on all papers: {(df['corresponding_author_papers'] == df['total_papers']).sum():,}\n")
#         f.write(f"  Avg corresponding papers: {df['corresponding_author_papers'].mean():.2f}\n\n")
        
#         # ====================================================================
#         # 11. DATA QUALITY CHECKS / ANOMALIES
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("11. DATA QUALITY CHECKS & ANOMALIES\n")
#         f.write("="*80 + "\n\n")
        
#         # Check for impossible values
#         f.write("ANOMALY CHECKS:\n\n")
        
#         # First + Last > Total (should be 0 for multi-author papers)
#         anomaly1 = df[(df['first_author_papers'] + df['last_author_papers']) > df['total_papers']]
#         f.write(f"1. Authors where (first + last) > total papers: {len(anomaly1):,}\n")
#         if len(anomaly1) > 0:
#             f.write("   NOTE: This should only happen for single-author papers!\n")
#             single_author = anomaly1[anomaly1['total_papers'] == anomaly1['first_author_papers']]
#             f.write(f"   Single-author cases: {len(single_author):,}\n")
#             f.write(f"   ACTUAL ANOMALIES: {len(anomaly1) - len(single_author):,}\n")
#         f.write("\n")
        
#         # Negative values (should be 0)
#         f.write("2. Negative value check:\n")
#         for col in df.select_dtypes(include=[np.number]).columns:
#             negative_count = (df[col] < 0).sum()
#             if negative_count > 0:
#                 f.write(f"   ✗ {col}: {negative_count:,} negative values!\n")
#         f.write("   ✓ No negative values found\n\n")
        
#         # Authors with citations but no papers (should be 0)
#         anomaly3 = df[(df['total_citations'] > 0) & (df['total_papers'] == 0)]
#         f.write(f"3. Authors with citations but no papers: {len(anomaly3):,}\n\n")
        
#         # Authors with papers but no citations
#         anomaly4 = df[(df['total_papers'] > 0) & (df['total_citations'] == 0)]
#         f.write(f"4. Authors with papers but ZERO citations: {len(anomaly4):,} ({len(anomaly4)/len(df)*100:.2f}%)\n")
#         if len(anomaly4) > 0:
#             f.write(f"   This includes papers that are very recent or not yet cited\n")
#         f.write("\n")
        
#         # Very high average citations (potential data issues)
#         anomaly5 = df[df['avg_citations_per_paper'] > 1000]
#         f.write(f"5. Authors with avg >1000 citations per paper: {len(anomaly5):,}\n")
#         if len(anomaly5) > 0:
#             f.write("   Top cases:\n")
#             for _, row in anomaly5.nlargest(5, 'avg_citations_per_paper').iterrows():
#                 f.write(f"   - {row['author_name'][:30]:30s}: {row['avg_citations_per_paper']:8.1f} avg ({row['total_papers']} papers)\n")
#         f.write("\n")
        
#         # Corresponding author rate
#         f.write("6. Corresponding author anomalies:\n")
#         corr_rate = df['corresponding_author_papers'] / df['total_papers']
#         anomaly6 = df[corr_rate > 1.0]
#         f.write(f"   Authors where corresponding > total papers: {len(anomaly6):,}\n")
#         f.write(f"   (Note: This can happen if multiple corresponding authors per paper)\n\n")
        
#         # ====================================================================
#         # 12. AFFILIATION ANALYSIS
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("12. AFFILIATION ANALYSIS\n")
#         f.write("="*80 + "\n\n")
        
#         f.write("Affiliation statistics:\n")
#         f.write(f"  Avg affiliations per author: {df['num_affiliations'].mean():.2f}\n")
#         f.write(f"  Median affiliations: {df['num_affiliations'].median():.0f}\n")
#         f.write(f"  Max affiliations by single author: {df['num_affiliations'].max()}\n\n")
        
#         f.write("Affiliation distribution:\n")
#         aff_bins = [0, 1, 2, 5, 10, 20, 50, np.inf]
#         aff_labels = ['0', '1', '2-4', '5-9', '10-19', '20-49', '50+']
#         aff_dist = pd.cut(df['num_affiliations'], bins=aff_bins, labels=aff_labels, right=False)
#         aff_counts = aff_dist.value_counts().sort_index()
#         for label, count in aff_counts.items():
#             pct = count / len(df) * 100
#             f.write(f"  {label:6s}: {count:8,} ({pct:5.2f}%)\n")
#         f.write("\n")
        
#         # ====================================================================
#         # 13. INTERESTING PATTERNS
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("13. INTERESTING PATTERNS\n")
#         f.write("="*80 + "\n\n")
        
#         # Prolific but uncited
#         f.write("Prolific but uncited authors (>50 papers, 0 citations):\n")
#         prolific_uncited = df[(df['total_papers'] > 50) & (df['total_citations'] == 0)]
#         f.write(f"  Count: {len(prolific_uncited):,}\n")
#         if len(prolific_uncited) > 0:
#             f.write("  Top cases:\n")
#             for _, row in prolific_uncited.nlargest(5, 'total_papers').iterrows():
#                 f.write(f"  - {row['author_name'][:40]:40s}: {row['total_papers']:4d} papers\n")
#         f.write("\n")
        
#         # Highly cited with few papers
#         f.write("Highly efficient authors (>1000 citations, <10 papers):\n")
#         efficient = df[(df['total_citations'] > 1000) & (df['total_papers'] < 10)]
#         f.write(f"  Count: {len(efficient):,}\n")
#         if len(efficient) > 0:
#             f.write("  Top cases:\n")
#             for _, row in efficient.nlargest(5, 'avg_citations_per_paper').iterrows():
#                 f.write(f"  - {row['author_name'][:40]:40s}: {row['total_citations']:6,} cites in {row['total_papers']} papers (avg: {row['avg_citations_per_paper']:.0f})\n")
#         f.write("\n")
        
#         # Cross-field superstars
#         f.write("Cross-field researchers (4 fields, >100 papers):\n")
#         cross_field = df[(df['num_unique_fields'] == 4) & (df['total_papers'] > 100)]
#         f.write(f"  Count: {len(cross_field):,}\n")
#         if len(cross_field) > 0:
#             f.write("  Examples:\n")
#             for _, row in cross_field.nlargest(5, 'total_papers').iterrows():
#                 f.write(f"  - {row['author_name'][:40]:40s}: {row['total_papers']:4d} papers across all 4 fields\n")
#         f.write("\n")
        
#         # ====================================================================
#         # FOOTER
#         # ====================================================================
        
#         f.write("="*80 + "\n")
#         f.write("END OF REPORT\n")
#         f.write("="*80 + "\n")
    
#     print(f"✓ EDA report saved to: {output_file_path}")
#     print(f"  File size: {Path(output_file_path).stat().st_size / 1024:.1f} KB")
    
#     # Also print some quick stats to console
#     print(f"\nQUICK SUMMARY:")
#     print(f"  Total authors: {len(df):,}")
#     print(f"  Authors with SDL papers: {(df['sdl_papers'] > 0).sum():,}")
#     print(f"  Most prolific author: {df.loc[df['total_papers'].idxmax(), 'author_name']} ({df['total_papers'].max()} papers)")
#     print(f"  Most cited author: {df.loc[df['total_citations'].idxmax(), 'author_name']} ({df['total_citations'].max():,} citations)")
    
#     return output_file_path

# # ============================================================================
# # MAIN EXECUTION
# # ============================================================================

# def main():
#     print("="*70)
#     print("BUILDING AUTHOR-LEVEL DATASET (SEQUENTIAL VERSION)")
#     print("="*70)
#     print(f"\nConfiguration:")
#     print(f"  Project dir: {PROJECT_DIR}")
#     print(f"  Output dir: {OUTPUT_DIR}")
#     print(f"  Years: {min(YEARS)}-{max(YEARS)-1}")
#     print(f"  Chunk size: {CHUNK_SIZE:,}")
#     print(f"  Processing: SEQUENTIAL (one field at a time)")
    
#     # Verify field directories
#     print(f"\nVerifying field directories:")
#     fields_to_process = []
#     for name, path in FIELDS.items():
#         exists = path.exists()
#         status = "✓" if exists else "✗"
#         print(f"  {status} {name}: {path}")
#         if exists:
#             fields_to_process.append((name, path))
    
#     if not fields_to_process:
#         print("\n✗ ERROR: No valid field directories found!")
#         return 1
    
#     print(f"\nWill process {len(fields_to_process)} fields sequentially...")
    
#     # ========================================================================
#     # PHASE 1: Sequential accumulation
#     # ========================================================================
    
#     # Initialize global author data dictionary
#     all_author_data = {}
    
#     total_papers_all = 0
#     total_errors_all = 0
    
#     # Process each field one at a time
#     for field_name, field_dir in fields_to_process:
#         papers, errors = process_field_accumulation(field_name, field_dir, all_author_data)
#         total_papers_all += papers
#         total_errors_all += errors
        
#         # Show running totals
#         print(f"  Running totals: {len(all_author_data):,} unique authors across {total_papers_all:,} papers")
    
#     # ========================================================================
#     # Summary after all fields processed
#     # ========================================================================
    
#     print(f"\n{'='*70}")
#     print("ALL FIELDS PROCESSED")
#     print(f"{'='*70}")
#     print(f"  Total papers: {total_papers_all:,}")
#     print(f"  Total errors: {total_errors_all:,}")
#     print(f"  Unique authors: {len(all_author_data):,}")
    
#     # ========================================================================
#     # PHASE 2: Aggregation
#     # ========================================================================
    
#     df_authors = aggregate_author_metrics(all_author_data)
    
#     # ========================================================================
#     # Save output
#     # ========================================================================
    
#     output_file = OUTPUT_DIR / "author_metrics.csv"
#     print(f"\n{'='*70}")
#     print("SAVING OUTPUT")
#     print(f"{'='*70}")
    
#     df_authors.to_csv(output_file, index=False)
    
#     file_size_mb = output_file.stat().st_size / (1024 * 1024)
#     print(f"  File: {output_file}")
#     print(f"  Size: {file_size_mb:.1f} MB")
#     print(f"  Rows: {len(df_authors):,}")
#     print(f"  Columns: {len(df_authors.columns)}")
    
#     # Summary stats
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
    
#     return 0

# if __name__ == "__main__":
#     main()
#     # perform_eda_and_save(csv_file, output_file_eda)

# """
# Build comprehensive author-level dataset from paper TSV files
# Optimized for HPC with multiprocessing

# Phase 1: Process each field in parallel, accumulating author data
# Phase 2: Merge field results and aggregate into final metrics
# """
# import pandas as pd
# import json
# from collections import Counter
# import numpy as np
# from pathlib import Path
# import multiprocessing as mp

# # ============================================================================
# # CONFIGURATION
# # ============================================================================

# PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# FIELDS = {
#     'chemistry': PROJECT_DIR / "data/fields" / "chemistry",
#     'materials_science': PROJECT_DIR / "data/fields" / "materials_science",  # FIXED: was material_science
#     'engineering': PROJECT_DIR / "data/fields" / "engineering",
#     'computer_science': PROJECT_DIR / "data/fields" / "computer_science"
# }

# OUTPUT_DIR = PROJECT_DIR / "data" / "author/test"
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# OUTPUT_FILE = OUTPUT_DIR / "author_metrics.csv"

# YEARS = range(2012, 2026)
# CHUNK_SIZE = 500000
# NUM_CORES = 8  # Adjust based on your SLURM allocation

# # ============================================================================
# # EXTRACTION FUNCTIONS
# # ============================================================================

# def parse_authorships(raw_data_json):
#     """Extract authorship information from raw_data JSON"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return []
    
#     try:
#         data = json.loads(raw_data_json)
#         authorships = data.get('authorships', [])
        
#         result = []
#         num_authors = len(authorships)
        
#         for idx, authorship in enumerate(authorships):
#             author = authorship.get('author', {})
#             author_id = author.get('id', '').replace('https://openalex.org/', '')
            
#             if not author_id:
#                 continue
            
#             institutions = []
#             for inst in authorship.get('institutions', []):
#                 inst_id = inst.get('id', '').replace('https://openalex.org/', '')
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
#     except:
#         return []


# def parse_primary_topic(raw_data_json):
#     """Extract primary topic from raw_data"""
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
#     """Extract journal name from raw_data"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return None
#     try:
#         data = json.loads(raw_data_json)
#         return data.get('primary_location', {}).get('source', {}).get('display_name')
#     except:
#         return None


# def parse_corresponding_author_ids(raw_data_json):
#     """Extract corresponding author IDs from raw_data"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return []
#     try:
#         data = json.loads(raw_data_json)
#         corresponding_ids = data.get('corresponding_author_ids', [])
#         return [aid.replace('https://openalex.org/', '') for aid in corresponding_ids if aid]
#     except:
#         return []


# def parse_cited_by_count(raw_data_json):
#     """Extract cited_by_count from raw_data"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return 0
#     try:
#         data = json.loads(raw_data_json)
#         cited_by_count = data.get('cited_by_count', 0)
#         return cited_by_count if cited_by_count else 0
#     except:
#         return 0


# # ============================================================================
# # AUTHOR DATA STRUCTURE
# # ============================================================================

# def create_author_entry():
#     """Factory function to create new author data entry"""
#     return {
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
#     }


# # ============================================================================
# # SINGLE YEAR PROCESSING (FOR MULTIPROCESSING)
# # ============================================================================

# def process_single_year_file(args):
#     """
#     Process a single year file for a given field
#     Returns dictionary of author data for that year/field
#     """
#     field_name, field_dir, year = args
    
#     # Find the file
#     possible_files = [
#         field_dir / f"{field_name}_{year}.tsv",
#         field_dir / f"{field_name.replace('_', '')}_{year}.tsv",
#     ]
    
#     tsv_file = None
#     for pf in possible_files:
#         if pf.exists():
#             tsv_file = pf
#             break
    
#     if not tsv_file:
#         return {}
    
#     # Process file
#     author_data = {}
#     papers_processed = 0
    
#     try:
#         # Check columns
#         sample = pd.read_csv(tsv_file, sep='\t', nrows=5)
#         available_cols = set(sample.columns)
        
#         required = ['raw_data', 'SDL', 'AI_Paper', 'Robotics_Paper']
#         columns_to_read = [col for col in required if col in available_cols]
        
#         if 'raw_data' not in columns_to_read:
#             return {}
        
#         # Read in chunks
#         for chunk in pd.read_csv(tsv_file, sep='\t', usecols=columns_to_read,
#                                 chunksize=CHUNK_SIZE, low_memory=False,
#                                 on_bad_lines='skip'):
            
#             for _, row in chunk.iterrows():
#                 try:
#                     authorships = parse_authorships(row.get('raw_data'))
#                     if not authorships:
#                         continue
                    
#                     citations = parse_cited_by_count(row.get('raw_data'))
#                     is_sdl = row.get('SDL', 0) == 1
#                     is_ai = row.get('AI_Paper', 0) == 1
#                     is_robotics = row.get('Robotics_Paper', 0) == 1
                    
#                     topic = parse_primary_topic(row.get('raw_data'))
#                     journal = parse_journal(row.get('raw_data'))
#                     corresponding_ids = parse_corresponding_author_ids(row.get('raw_data'))
                    
#                     for authorship in authorships:
#                         author_id = authorship['author_id']
                        
#                         if author_id not in author_data:
#                             author_data[author_id] = create_author_entry()
                        
#                         data = author_data[author_id]
                        
#                         data['names'].append(authorship['author_name'])
#                         data['citations_list'].append(citations)
#                         data['citation_sum'] += citations
#                         data['fields'].append(field_name)
                        
#                         if topic:
#                             data['topics'].append(topic)
#                         if journal:
#                             data['journals'].append(journal)
                        
#                         data['affiliations'].update(authorship['institutions'])
#                         data['paper_count'] += 1
                        
#                         if authorship['is_first']:
#                             data['first_author_count'] += 1
#                         if authorship['is_last']:
#                             data['last_author_count'] += 1
#                         if author_id in corresponding_ids:
#                             data['corresponding_author_count'] += 1
                        
#                         if is_sdl:
#                             data['sdl_count'] += 1
#                         if is_ai:
#                             data['ai_count'] += 1
#                         if is_robotics:
#                             data['robotics_count'] += 1
                    
#                     papers_processed += 1
                
#                 except:
#                     continue
    
#     except:
#         pass
    
#     return author_data


# # ============================================================================
# # MERGE DICTIONARIES
# # ============================================================================

# def merge_author_dicts(dict1, dict2):
#     """Merge two author data dictionaries"""
#     for author_id, data2 in dict2.items():
#         if author_id not in dict1:
#             dict1[author_id] = data2
#         else:
#             data1 = dict1[author_id]
#             data1['names'].extend(data2['names'])
#             data1['citations_list'].extend(data2['citations_list'])
#             data1['fields'].extend(data2['fields'])
#             data1['topics'].extend(data2['topics'])
#             data1['journals'].extend(data2['journals'])
#             data1['affiliations'].update(data2['affiliations'])
#             data1['paper_count'] += data2['paper_count']
#             data1['first_author_count'] += data2['first_author_count']
#             data1['last_author_count'] += data2['last_author_count']
#             data1['corresponding_author_count'] += data2['corresponding_author_count']
#             data1['citation_sum'] += data2['citation_sum']
#             data1['sdl_count'] += data2['sdl_count']
#             data1['ai_count'] += data2['ai_count']
#             data1['robotics_count'] += data2['robotics_count']
    
#     return dict1


# # ============================================================================
# # AGGREGATION
# # ============================================================================

# def aggregate_author_metrics(all_author_data):
#     """Convert accumulated data into final metrics"""
    
#     print(f"\nComputing final metrics for {len(all_author_data):,} authors...")
    
#     rows = []
    
#     for idx, (author_id, data) in enumerate(all_author_data.items()):
#         if (idx + 1) % 100000 == 0:
#             print(f"  {idx + 1:,} authors processed...", flush=True)
        
#         author_name = Counter(data['names']).most_common(1)[0][0] if data['names'] else ''
        
#         total_papers = data['paper_count']
#         first_author_papers = data['first_author_count']
#         last_author_papers = data['last_author_count']
#         corresponding_author_papers = data['corresponding_author_count']
        
#         total_citations = data['citation_sum']
#         avg_citations = np.mean(data['citations_list']) if data['citations_list'] else 0
        
#         if data['fields']:
#             field_counter = Counter(data['fields'])
#             top_field_name, top_field_count = field_counter.most_common(1)[0]
#             num_unique_fields = len(field_counter)
#         else:
#             top_field_name, top_field_count, num_unique_fields = '', 0, 0
        
#         if data['topics']:
#             topic_counter = Counter(data['topics'])
#             top_topic_name, top_topic_count = topic_counter.most_common(1)[0]
#             num_unique_topics = len(topic_counter)
#         else:
#             top_topic_name, top_topic_count, num_unique_topics = '', 0, 0
        
#         if data['journals']:
#             journal_counter = Counter(data['journals'])
#             top_journal_name, top_journal_count = journal_counter.most_common(1)[0]
#             num_unique_journals = len(journal_counter)
#         else:
#             top_journal_name, top_journal_count, num_unique_journals = '', 0, 0
        
#         num_affiliations = len(data['affiliations'])
#         top_affiliation = list(data['affiliations'])[0] if data['affiliations'] else ''
        
#         rows.append({
#             'author_id': author_id,
#             'author_name': author_name,
#             'total_papers': total_papers,
#             'first_author_papers': first_author_papers,
#             'last_author_papers': last_author_papers,
#             'corresponding_author_papers': corresponding_author_papers,
#             'total_citations': int(total_citations),
#             'avg_citations_per_paper': round(avg_citations, 2),
#             'top_field': top_field_name,
#             'top_field_paper_count': top_field_count,
#             'num_unique_fields': num_unique_fields,
#             'top_topic': top_topic_name,
#             'top_topic_paper_count': top_topic_count,
#             'num_unique_topics': num_unique_topics,
#             'top_journal': top_journal_name,
#             'top_journal_paper_count': top_journal_count,
#             'num_unique_journals': num_unique_journals,
#             'num_affiliations': num_affiliations,
#             'top_affiliation': top_affiliation,
#             'sdl_papers': data['sdl_count'],
#             'ai_papers': data['ai_count'],
#             'robotics_papers': data['robotics_count']
#         })
    
#     return pd.DataFrame(rows)


# # ============================================================================
# # MAIN EXECUTION
# # ============================================================================

# def main():
#     print("="*70)
#     print("BUILDING AUTHOR-LEVEL DATASET (MULTIPROCESSING)")
#     print("="*70)
#     print(f"\nConfiguration:")
#     print(f"  Project dir: {PROJECT_DIR}")
#     print(f"  Output dir: {OUTPUT_DIR}")
#     print(f"  Years: {min(YEARS)}-{max(YEARS)-1}")
#     print(f"  Chunk size: {CHUNK_SIZE:,}")
#     print(f"  CPU cores: {NUM_CORES}")
    
#     # Verify field directories
#     print(f"\nVerifying field directories:")
#     fields_to_process = []
#     for name, path in FIELDS.items():
#         exists = path.exists()
#         status = "✓" if exists else "✗"
#         print(f"  {status} {name}: {path}")
#         if exists:
#             fields_to_process.append((name, path))
    
#     if not fields_to_process:
#         print("\n✗ ERROR: No valid field directories found!")
#         return 1
    
#     # ========================================================================
#     # PHASE 1: Parallel processing by year/field
#     # ========================================================================
    
#     print(f"\n{'='*70}")
#     print("PHASE 1: Processing all year/field combinations in parallel")
#     print(f"{'='*70}")
    
#     # Create list of all (field_name, field_dir, year) combinations
#     tasks = []
#     for field_name, field_dir in fields_to_process:
#         for year in YEARS:
#             tasks.append((field_name, field_dir, year))
    
#     print(f"Total tasks: {len(tasks)}")
#     print(f"Processing with {NUM_CORES} cores...")
    
#     # Process in parallel
#     with mp.Pool(NUM_CORES) as pool:
#         results = pool.map(process_single_year_file, tasks)
    
#     print(f"\n✓ Parallel processing complete")
    
#     # ========================================================================
#     # PHASE 2: Merge all results
#     # ========================================================================
    
#     print(f"\n{'='*70}")
#     print("PHASE 2: Merging results")
#     print(f"{'='*70}")
    
#     all_author_data = {}
    
#     for i, result_dict in enumerate(results):
#         if result_dict:  # Skip empty results
#             all_author_data = merge_author_dicts(all_author_data, result_dict)
#             if (i + 1) % 10 == 0:
#                 print(f"  Merged {i+1}/{len(results)} results... ({len(all_author_data):,} unique authors)", flush=True)
    
#     print(f"\n✓ Merge complete: {len(all_author_data):,} unique authors")
    
#     # ========================================================================
#     # PHASE 3: Aggregation
#     # ========================================================================
    
#     print(f"\n{'='*70}")
#     print("PHASE 3: Computing final metrics")
#     print(f"{'='*70}")
    
#     df_authors = aggregate_author_metrics(all_author_data)
    
#     # ========================================================================
#     # Save output
#     # ========================================================================
    
#     print(f"\n{'='*70}")
#     print("SAVING OUTPUT")
#     print(f"{'='*70}")
    
#     df_authors.to_csv(OUTPUT_FILE, index=False)
    
#     file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
#     print(f"  File: {OUTPUT_FILE}")
#     print(f"  Size: {file_size_mb:.1f} MB")
#     print(f"  Rows: {len(df_authors):,}")
#     print(f"  Columns: {len(df_authors.columns)}")
    
#     # Summary stats
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
#     print(f"Output: {OUTPUT_FILE}\n")
    
#     return 0


# if __name__ == "__main__":
#     main()

# """
# Build comprehensive author-level dataset from paper TSV files
# Optimized for HPC with multiprocessing
# """
# import pandas as pd
# import json
# from collections import Counter
# import numpy as np
# from pathlib import Path
# import multiprocessing as mp
# import ast

# # ============================================================================
# # CONFIGURATION
# # ============================================================================

# PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# FIELDS = {
#     'chemistry': PROJECT_DIR / "data/fields" / "chemistry",
#     'materials_science': PROJECT_DIR / "data/fields" / "materials_science",
#     'engineering': PROJECT_DIR / "data/fields" / "engineering",
#     'computer_science': PROJECT_DIR / "data/fields" / "computer_science"
# }

# # Path to Keywords
# CS_KEYWORDS_FILE = PROJECT_DIR / "data/lasso_regression" / "cs_keywords_shortlisted.txt"

# OUTPUT_DIR = PROJECT_DIR / "data" / "author/test"
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# OUTPUT_FILE = OUTPUT_DIR / "author_metrics.csv"

# YEARS = range(2012, 2026)
# CHUNK_SIZE = 500000
# NUM_CORES = 8 

# # ============================================================================
# # HELPER FUNCTIONS (CS Keyword Matching)
# # ============================================================================

# def load_cs_keywords(file_path):
#     """Load CS keywords from text file"""
#     if not file_path.exists():
#         return set()
#     with open(file_path, 'r', encoding='utf-8') as f:
#         keywords = set(line.strip().lower() for line in f 
#                       if line.strip() and not line.strip().startswith('#'))
#     return keywords

# def check_cs_keyword_match(primary_topic, all_topics, title, abstract, cs_keywords_set):
#     """
#     Check if at least 2 different CS keywords match.
#     Returns True if match found.
#     """
#     if not cs_keywords_set:
#         return False
        
#     matched_keywords = set()
    
#     # Check primary topic
#     if primary_topic:
#         primary_lower = primary_topic.lower()
#         for keyword in cs_keywords_set:
#             if keyword in primary_lower:
#                 matched_keywords.add(keyword)
#                 if len(matched_keywords) >= 2: return True
    
#     # Check all topics (list of strings)
#     if all_topics:
#         for t in all_topics:
#             t_lower = t.lower()
#             for keyword in cs_keywords_set:
#                 if keyword in t_lower:
#                     matched_keywords.add(keyword)
#                     if len(matched_keywords) >= 2: return True
    
#     # Check title
#     if title and isinstance(title, str):
#         title_lower = title.lower()
#         for keyword in cs_keywords_set:
#             if keyword in title_lower:
#                 matched_keywords.add(keyword)
#                 if len(matched_keywords) >= 2: return True
    
#     # Check abstract
#     if abstract and isinstance(abstract, str):
#         abstract_lower = abstract.lower()
#         for keyword in cs_keywords_set:
#             if keyword in abstract_lower:
#                 matched_keywords.add(keyword)
#                 if len(matched_keywords) >= 2: return True
    
#     return len(matched_keywords) >= 2

# # ============================================================================
# # EXTRACTION FUNCTIONS
# # ============================================================================

# def parse_authorships(raw_data_json):
#     """Extract authorship information from raw_data JSON"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return []
#     try:
#         data = json.loads(raw_data_json)
#         authorships = data.get('authorships', [])
#         result = []
#         num_authors = len(authorships)
#         for idx, authorship in enumerate(authorships):
#             author = authorship.get('author', {})
#             author_id = author.get('id', '').replace('https://openalex.org/', '')
#             if not author_id: continue
            
#             institutions = []
#             for inst in authorship.get('institutions', []):
#                 inst_id = inst.get('id', '').replace('https://openalex.org/', '')
#                 if inst_id: institutions.append(inst_id)
            
#             result.append({
#                 'author_id': author_id,
#                 'author_name': author.get('display_name', ''),
#                 'position': idx,
#                 'is_first': (idx == 0),
#                 'is_last': (idx == num_authors - 1),
#                 'institutions': institutions
#             })
#         return result
#     except:
#         return []

# def parse_metadata_for_cs(raw_data_json):
#     """Extract metadata needed for CS checking (topics, title, abstract)"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return None, [], None, None
#     try:
#         data = json.loads(raw_data_json)
        
#         # Topics
#         topics = data.get('topics', [])
#         primary_topic = topics[0].get('display_name') if topics else None
#         all_topics = [t.get('display_name') for t in topics if t.get('display_name')]
        
#         title = data.get('title', '')
        
#         # Reconstruct Abstract
#         abstract_text = None
#         abstract_inverted = data.get('abstract_inverted_index')
#         if abstract_inverted:
#             word_positions = []
#             for word, positions in abstract_inverted.items():
#                 for pos in positions:
#                     word_positions.append((pos, word))
#             word_positions.sort(key=lambda x: x[0])
#             abstract_text = ' '.join([word for pos, word in word_positions])
            
#         return primary_topic, all_topics, title, abstract_text
#     except:
#         return None, [], None, None

# def parse_journal(raw_data_json):
#     if pd.isna(raw_data_json) or raw_data_json == '': return None
#     try:
#         data = json.loads(raw_data_json)
#         return data.get('primary_location', {}).get('source', {}).get('display_name')
#     except: return None

# def parse_corresponding_author_ids(raw_data_json):
#     if pd.isna(raw_data_json) or raw_data_json == '': return []
#     try:
#         data = json.loads(raw_data_json)
#         return [aid.replace('https://openalex.org/', '') for aid in data.get('corresponding_author_ids', []) if aid]
#     except: return []

# def parse_cited_by_count(raw_data_json):
#     if pd.isna(raw_data_json) or raw_data_json == '': return 0
#     try:
#         data = json.loads(raw_data_json)
#         return data.get('cited_by_count', 0) or 0
#     except: return 0

# # ============================================================================
# # AUTHOR DATA STRUCTURE
# # ============================================================================

# def create_author_entry():
#     return {
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
#         'robotics_count': 0,
#         'has_cs_exp': False,
        
#         # TEAM SIZE ACCUMULATORS
#         'team_size_sum': 0,             # For overall avg
#         'team_size_sum_last_author': 0, # For managerial avg
#         'team_size_sum_sdl': 0          # For SDL-specific avg
#     }

# # ============================================================================
# # SINGLE YEAR PROCESSING
# # ============================================================================

# def process_single_year_file(args):
#     """Process a single year file for a given field"""
#     field_name, field_dir, year = args
    
#     # Locate file
#     possible_files = [
#         field_dir / f"{field_name}_{year}.tsv",
#         field_dir / f"{field_name.replace('_', '')}_{year}.tsv",
#     ]
#     tsv_file = next((f for f in possible_files if f.exists()), None)
    
#     if not tsv_file: return {}
    
#     # Load CS Keywords (once per process)
#     cs_keywords = load_cs_keywords(CS_KEYWORDS_FILE)
    
#     author_data = {}
    
#     try:
#         # Check available columns
#         sample = pd.read_csv(tsv_file, sep='\t', nrows=5)
#         available_cols = set(sample.columns)
#         # Added 'author_count'
#         required = ['raw_data', 'SDL', 'AI_Paper', 'Robotics_Paper', 'author_count']
#         columns_to_read = [col for col in required if col in available_cols]
        
#         if 'raw_data' not in columns_to_read: return {}
        
#         for chunk in pd.read_csv(tsv_file, sep='\t', usecols=columns_to_read,
#                                 chunksize=CHUNK_SIZE, low_memory=False,
#                                 on_bad_lines='skip'):
            
#             for _, row in chunk.iterrows():
#                 try:
#                     raw = row.get('raw_data')
#                     authorships = parse_authorships(raw)
#                     if not authorships: continue
                    
#                     # Metadata Extraction
#                     citations = parse_cited_by_count(raw)
#                     is_sdl = row.get('SDL', 0) == 1
#                     is_ai = row.get('AI_Paper', 0) == 1
#                     is_robotics = row.get('Robotics_Paper', 0) == 1
                    
#                     # Extract Team Size 
#                     team_size = row.get('author_count', 0)
#                     if pd.isna(team_size): team_size = 0
                    
#                     # Topic/Journal for existing metrics
#                     primary_topic, all_topics, title, abstract = parse_metadata_for_cs(raw)
#                     journal = parse_journal(raw)
#                     corresponding_ids = parse_corresponding_author_ids(raw)
                    
#                     # Check CS Experience
#                     is_cs_paper = False
#                     if field_name == 'computer_science':
#                         is_cs_paper = True
#                     else:
#                         is_cs_paper = check_cs_keyword_match(primary_topic, all_topics, title, abstract, cs_keywords)
                    
#                     for authorship in authorships:
#                         author_id = authorship['author_id']
#                         if author_id not in author_data:
#                             author_data[author_id] = create_author_entry()
                        
#                         data = author_data[author_id]
                        
#                         # Accumulate Basic Data
#                         data['names'].append(authorship['author_name'])
#                         data['citations_list'].append(citations)
#                         data['citation_sum'] += citations
#                         data['fields'].append(field_name)
                        
#                         if primary_topic: data['topics'].append(primary_topic)
#                         if journal: data['journals'].append(journal)
#                         data['affiliations'].update(authorship['institutions'])
                        
#                         data['paper_count'] += 1
#                         if authorship['is_first']: data['first_author_count'] += 1
#                         if authorship['is_last']: data['last_author_count'] += 1
#                         if author_id in corresponding_ids: data['corresponding_author_count'] += 1
                        
#                         if is_sdl: data['sdl_count'] += 1
#                         if is_ai: data['ai_count'] += 1
#                         if is_robotics: data['robotics_count'] += 1
                        
#                         if is_cs_paper: data['has_cs_exp'] = True

#                         # --- TEAM SIZE ACCUMULATION ---
#                         # 1. Overall Team Size Sum
#                         data['team_size_sum'] += team_size
                        
#                         # 2. Team Size as Last Author (Managerial Proxy)
#                         if authorship['is_last']:
#                             data['team_size_sum_last_author'] += team_size
                            
#                         # 3. Team Size on SDL Papers (Context Proxy)
#                         if is_sdl:
#                             data['team_size_sum_sdl'] += team_size
                            
#                 except: continue
#     except: pass
    
#     return author_data

# # ============================================================================
# # MERGE DICTIONARIES
# # ============================================================================

# def merge_author_dicts(dict1, dict2):
#     """Merge two author data dictionaries"""
#     for author_id, data2 in dict2.items():
#         if author_id not in dict1:
#             dict1[author_id] = data2
#         else:
#             data1 = dict1[author_id]
#             data1['names'].extend(data2['names'])
#             data1['citations_list'].extend(data2['citations_list'])
#             data1['fields'].extend(data2['fields'])
#             data1['topics'].extend(data2['topics'])
#             data1['journals'].extend(data2['journals'])
#             data1['affiliations'].update(data2['affiliations'])
            
#             data1['paper_count'] += data2['paper_count']
#             data1['first_author_count'] += data2['first_author_count']
#             data1['last_author_count'] += data2['last_author_count']
#             data1['corresponding_author_count'] += data2['corresponding_author_count']
#             data1['citation_sum'] += data2['citation_sum']
#             data1['sdl_count'] += data2['sdl_count']
#             data1['ai_count'] += data2['ai_count']
#             data1['robotics_count'] += data2['robotics_count']
            
#             if data2['has_cs_exp']: data1['has_cs_exp'] = True
            
#             # Merge Team Size Accumulators
#             data1['team_size_sum'] += data2['team_size_sum']
#             data1['team_size_sum_last_author'] += data2['team_size_sum_last_author']
#             data1['team_size_sum_sdl'] += data2['team_size_sum_sdl']
                
#     return dict1

# # ============================================================================
# # AGGREGATION
# # ============================================================================

# def aggregate_author_metrics(all_author_data):
#     """Convert accumulated data into final metrics"""
    
#     print(f"\nComputing final metrics for {len(all_author_data):,} authors...")
    
#     rows = []
    
#     for idx, (author_id, data) in enumerate(all_author_data.items()):
#         if (idx + 1) % 100000 == 0:
#             print(f"  {idx + 1:,} authors processed...", flush=True)
        
#         # Basic Stats
#         author_name = Counter(data['names']).most_common(1)[0][0] if data['names'] else ''
#         total_papers = data['paper_count']
        
#         # --- TEAM SIZE CALCULATIONS ---
        
#         # 1. Avg Team Size (Overall)
#         avg_team_size = 0
#         if total_papers > 0:
#             avg_team_size = data['team_size_sum'] / total_papers
            
#         # 2. Avg Team Size (Last Author)
#         avg_team_size_last = 0
#         last_papers = data['last_author_count']
#         if last_papers > 0:
#             avg_team_size_last = data['team_size_sum_last_author'] / last_papers
            
#         # 3. Avg Team Size (SDL)
#         avg_team_size_sdl = 0
#         sdl_papers = data['sdl_count']
#         if sdl_papers > 0:
#             avg_team_size_sdl = data['team_size_sum_sdl'] / sdl_papers

#         # Field Analysis
#         field_counter = Counter(data['fields'])
        
#         # Top Field
#         if data['fields']:
#             top_field_name, top_field_count = field_counter.most_common(1)[0]
#             num_unique_fields = len(field_counter)
#         else:
#             top_field_name, top_field_count, num_unique_fields = '', 0, 0
            
#         # Field Dict
#         field_counts_str = str(dict(field_counter))
        
#         # Author Profile
#         core_fields = []
#         for field, count in field_counter.items():
#             if count >= 2 and (count / total_papers) > 0.10:
#                 core_fields.append(field)
        
#         core_fields.sort()
        
#         if len(core_fields) == 0:
#             author_profile = f"{top_field_name}_Only" if top_field_name else "Unknown"
#         elif len(core_fields) == 1:
#             author_profile = f"{core_fields[0]}_Only"
#         elif len(core_fields) == 2:
#             author_profile = "+".join(core_fields)
#         else:
#             author_profile = "Generalist"
            
#         # Top Topic
#         if data['topics']:
#             topic_counter = Counter(data['topics'])
#             top_topic_name, top_topic_count = topic_counter.most_common(1)[0]
#             num_unique_topics = len(topic_counter)
#         else:
#             top_topic_name, top_topic_count, num_unique_topics = '', 0, 0
            
#         # Top Journal
#         if data['journals']:
#             journal_counter = Counter(data['journals'])
#             top_journal_name, top_journal_count = journal_counter.most_common(1)[0]
#             num_unique_journals = len(journal_counter)
#         else:
#             top_journal_name, top_journal_count, num_unique_journals = '', 0, 0

#         rows.append({
#             'author_id': author_id,
#             'author_name': author_name,
#             'total_papers': total_papers,
#             'first_author_papers': data['first_author_count'],
#             'last_author_papers': data['last_author_count'],
#             'corresponding_author_papers': data['corresponding_author_count'],
#             'total_citations': int(data['citation_sum']),
#             'avg_citations_per_paper': round(np.mean(data['citations_list']) if data['citations_list'] else 0, 2),
            
#             # --- NEW VARIABLES ---
#             'avg_team_size': round(avg_team_size, 2),
#             'avg_team_size_last_author': round(avg_team_size_last, 2),
#             'avg_team_size_sdl': round(avg_team_size_sdl, 2),
            
#             # Field Vars
#             'top_field': top_field_name,
#             'top_field_paper_count': top_field_count,
#             'num_unique_fields': num_unique_fields,
#             'field_counts': field_counts_str,
#             'author_profile': author_profile,
            
#             # CS Experience
#             'has_cs_experience': 1 if data['has_cs_exp'] else 0,
            
#             # Other Metrcis
#             'top_topic': top_topic_name,
#             'top_topic_paper_count': top_topic_count,
#             'num_unique_topics': num_unique_topics,
#             'top_journal': top_journal_name,
#             'top_journal_paper_count': top_journal_count,
#             'num_unique_journals': num_unique_journals,
#             'num_affiliations': len(data['affiliations']),
#             'top_affiliation': list(data['affiliations'])[0] if data['affiliations'] else '',
#             'sdl_papers': data['sdl_count'],
#             'ai_papers': data['ai_count'],
#             'robotics_papers': data['robotics_count']
#         })
    
#     return pd.DataFrame(rows)

# # ============================================================================
# # MAIN EXECUTION
# # ============================================================================

# def main():
#     print("="*70)
#     print("BUILDING AUTHOR-LEVEL DATASET (V3 - TEAM SIZES)")
#     print("="*70)
#     print(f"Output: {OUTPUT_FILE}")
#     print(f"Using {NUM_CORES} cores")
#     print(f"CS Keywords: {CS_KEYWORDS_FILE}")
    
#     # Check Directories
#     fields_to_process = []
#     for name, path in FIELDS.items():
#         if path.exists(): fields_to_process.append((name, path))
    
#     if not fields_to_process:
#         print("Error: No field directories found.")
#         return
        
#     # Phase 1: Parallel Processing
#     tasks = [(name, path, year) for name, path in fields_to_process for year in YEARS]
#     print(f"Processing {len(tasks)} file tasks...")
    
#     with mp.Pool(NUM_CORES) as pool:
#         results = pool.map(process_single_year_file, tasks)
        
#     # Phase 2: Merge
#     print("\nMerging results...")
#     all_author_data = {}
#     for res in results:
#         if res: all_author_data = merge_author_dicts(all_author_data, res)
        
#     # Phase 3: Aggregate
#     print("\nAggregating metrics...")
#     df = aggregate_author_metrics(all_author_data)
    
#     # Save
#     df.to_csv(OUTPUT_FILE, index=False)
#     print(f"\nSaved {len(df):,} authors to {OUTPUT_FILE}")
#     print("Columns:", list(df.columns))

# if __name__ == "__main__":
#     main()

import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")
INPUT_FILE = PROJECT_DIR / "data/author/test/author_metrics.csv"
OUTPUT_FILE = PROJECT_DIR / "data/author/test/author_eda_report.txt"

# Ensure output directory exists
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Formatting settings
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.set_option('display.float_format', '{:.2f}'.format)

# ============================================================================
# LOGGING UTILITY
# ============================================================================
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

# Redirect output to file and console
sys.stdout = Logger(OUTPUT_FILE)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_header(title):
    print("\n" + "="*80)
    print(title)
    print("="*80)

def print_dist(series, bins, labels):
    # include_lowest=True handles the first edge
    dist = pd.cut(series, bins=bins, labels=labels, include_lowest=True).value_counts().sort_index()
    for label, count in dist.items():
        print(f"  {label:<10}: {count:>9,} ({count/len(series)*100:.2f}%)")

# ============================================================================
# MAIN EDA SCRIPT
# ============================================================================

def main():
    if not INPUT_FILE.exists():
        print(f"Error: File not found at {INPUT_FILE}")
        return

    print("Loading data... (this may take a minute due to size)")
    df = pd.read_csv(INPUT_FILE)
    
    print("="*80)
    print("EXPLORATORY DATA ANALYSIS - AUTHOR DATASET (V3)")
    print("="*80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Source file: {INPUT_FILE}")
    print("="*80)

    # ============================================================================
    # 1. DATASET OVERVIEW
    # ============================================================================
    print_header("1. DATASET OVERVIEW")
    
    print(f"Total authors: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB\n")

    print("Columns:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:>2}. {col}")

    # ============================================================================
    # 2. MISSING VALUES ANALYSIS
    # ============================================================================
    print_header("2. MISSING VALUES ANALYSIS")
    
    print("Columns with missing values:")
    missing = df.isnull().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    for col, val in missing.items():
        print(f"  {col}: {val:,} ({val/len(df)*100:.2f}%)")
        
    print("\nEmpty string check:")
    obj_cols = df.select_dtypes(include=['object']).columns
    for col in obj_cols:
        empty_count = (df[col] == '').sum()
        if empty_count > 0:
            print(f"  {col}: {empty_count:,} empty strings")

    # ============================================================================
    # 3. PUBLICATION COUNTS STATISTICS
    # ============================================================================
    print_header("3. PUBLICATION COUNTS STATISTICS")

    cols = ['total_papers', 'first_author_papers', 'last_author_papers', 
            'corresponding_author_papers', 'sdl_papers', 'ai_papers', 'robotics_papers']
    cols = [c for c in cols if c in df.columns]
    print(df[cols].describe().to_string())

    print("\nPublication count distributions:")
    bins = [0, 1, 4, 9, 19, 49, 99, 499, 999, 1000000]
    labels = ['1', '2-4', '5-9', '10-19', '20-49', '50-99', '100-499', '500-999', '1000+']
    
    for col in ['total_papers', 'first_author_papers', 'last_author_papers']:
        if col in df.columns:
            print(f"\n{col}:")
            print_dist(df[col], bins, labels)

    # ============================================================================
    # 4. CITATION STATISTICS
    # ============================================================================
    print_header("4. CITATION STATISTICS")

    cit_cols = ['total_citations', 'avg_citations_per_paper']
    print(df[cit_cols].describe().to_string())

    print("\nCitation milestones:")
    print(f"  Authors with 0 citations: {len(df[df['total_citations'] == 0]):,}")
    print(f"  Authors with 100+ citations: {len(df[df['total_citations'] >= 100]):,}")
    print(f"  Authors with 1,000+ citations: {len(df[df['total_citations'] >= 1000]):,}")
    print(f"  Authors with 10,000+ citations: {len(df[df['total_citations'] >= 10000]):,}")
    print(f"  Authors with 100,000+ citations: {len(df[df['total_citations'] >= 100000]):,}")

    # ============================================================================
    # 5. FIELD DISTRIBUTION
    # ============================================================================
    print_header("5. FIELD DISTRIBUTION")

    print("Authors by top field:")
    print(df['top_field'].value_counts(dropna=False).head(5).to_string())

    print("\nMulti-field activity:")
    if 'num_unique_fields' in df.columns:
        counts = df['num_unique_fields'].value_counts().sort_index()
        for i in range(1, 5):
            val = counts.get(i, 0)
            print(f"  {i} fields: {val:,} ({val/len(df)*100:.2f}%)")

    # ============================================================================
    # 6. TOP AUTHORS
    # ============================================================================
    print_header("6. TOP AUTHORS")
    
    show_cols = ['author_name', 'total_papers', 'total_citations', 'top_field', 'top_topic', 'sdl_papers']
    show_cols = [c for c in show_cols if c in df.columns]

    print("Top 20 authors by total papers:")
    print("-" * 80)
    print(df.nlargest(20, 'total_papers')[show_cols].to_string(index=False))

    print("\nTop 20 authors by total citations:")
    print("-" * 80)
    show_cols_cit = ['author_name', 'total_papers', 'total_citations', 'avg_citations_per_paper', 'top_field']
    print(df.nlargest(20, 'total_citations')[show_cols_cit].to_string(index=False))

    print("\nTop 20 authors by avg citations per paper (min 10 papers):")
    print("-" * 80)
    mask = df['total_papers'] >= 10
    print(df[mask].nlargest(20, 'avg_citations_per_paper')[show_cols_cit].to_string(index=False))

    # ============================================================================
    # 7. SDL/AI/ROBOTICS INVOLVEMENT
    # ============================================================================
    print_header("7. SDL/AI/ROBOTICS INVOLVEMENT")

    print("Authors with SDL/AI/Robotics papers:")
    for col, name in [('sdl_papers', 'SDL'), ('ai_papers', 'AI'), ('robotics_papers', 'Robotics')]:
        if col in df.columns:
            print(f"  Authors with >=1 {name} paper: {len(df[df[col] >= 1]):,}")
            if name != 'SDL':
                print(f"  Authors with >=10 {name} papers: {len(df[df[col] >= 10]):,}")
            else:
                print(f"  Authors with >=5 {name} papers: {len(df[df[col] >= 5]):,}")
                print(f"  Authors with >=10 {name} papers: {len(df[df[col] >= 10]):,}")
        print()

    print("Top 20 SDL authors:")
    print("-" * 80)
    sdl_show = ['author_name', 'total_papers', 'sdl_papers', 'ai_papers', 'robotics_papers', 'top_field']
    sdl_show = [c for c in sdl_show if c in df.columns]
    print(df.nlargest(20, 'sdl_papers')[sdl_show].to_string(index=False))

    # ============================================================================
    # 8. TOPIC ANALYSIS
    # ============================================================================
    print_header("8. TOPIC ANALYSIS")
    
    print("Top 30 research topics by author count:")
    if 'top_topic' in df.columns:
        counts = df['top_topic'].value_counts().head(30)
        for i, (topic, count) in enumerate(counts.items(), 1):
            print(f"  {i:>2}. {topic:<50}: {count:,} ({count/len(df)*100:.2f}%)")
            
        print("\nTopic diversity:")
        print(f"  Unique topics in dataset: {df['top_topic'].nunique():,}")
        if 'num_unique_topics' in df.columns:
            print(f"  Avg topics per author: {df['num_unique_topics'].mean():.2f}")
            print(f"  Max topics by single author: {df['num_unique_topics'].max()}")

    # ============================================================================
    # 9. JOURNAL ANALYSIS
    # ============================================================================
    print_header("9. JOURNAL ANALYSIS")

    print("Top 30 journals by author count:")
    if 'top_journal' in df.columns:
        counts = df['top_journal'].value_counts().head(30)
        for i, (journal, count) in enumerate(counts.items(), 1):
            print(f"  {i:>2}. {journal:<50}: {count:,} ({count/len(df)*100:.2f}%)")

        print("\nJournal diversity:")
        print(f"  Unique journals in dataset: {df['top_journal'].nunique():,}")
        if 'num_unique_journals' in df.columns:
            print(f"  Avg journals per author: {df['num_unique_journals'].mean():.2f}")
            print(f"  Max journals by single author: {df['num_unique_journals'].max()}")

    # ============================================================================
    # 10. AUTHORSHIP POSITION ANALYSIS
    # ============================================================================
    print_header("10. AUTHORSHIP POSITION ANALYSIS")

    if 'first_author_papers' in df.columns:
        print("First authorship:")
        print(f"  Authors who were NEVER first author: {len(df[df['first_author_papers'] == 0]):,}")
        print(f"  Authors who were ALWAYS first author: {len(df[df['first_author_papers'] == df['total_papers']]):,}")
        print(f"  Avg first author papers: {df['first_author_papers'].mean():.2f}")

    if 'last_author_papers' in df.columns:
        print("\nLast authorship:")
        print(f"  Authors who were NEVER last author: {len(df[df['last_author_papers'] == 0]):,}")
        print(f"  Authors who were ALWAYS last author: {len(df[df['last_author_papers'] == df['total_papers']]):,}")
        print(f"  Avg last author papers: {df['last_author_papers'].mean():.2f}")

    if 'corresponding_author_papers' in df.columns:
        print("\nCorresponding authorship:")
        print(f"  Authors who were NEVER corresponding: {len(df[df['corresponding_author_papers'] == 0]):,}")
        print(f"  Authors corresponding on all papers: {len(df[df['corresponding_author_papers'] == df['total_papers']]):,}")
        print(f"  Avg corresponding papers: {df['corresponding_author_papers'].mean():.2f}")

    # ============================================================================
    # 11. DATA QUALITY CHECKS & ANOMALIES
    # ============================================================================
    print_header("11. DATA QUALITY CHECKS & ANOMALIES")
    print("ANOMALY CHECKS:")
    
    if 'first_author_papers' in df.columns and 'last_author_papers' in df.columns:
        anom = df[df['first_author_papers'] + df['last_author_papers'] > df['total_papers']]
        print(f"\n1. Authors where (first + last) > total papers: {len(anom):,}")
        print("   NOTE: This should only happen for single-author papers!")
        
        single_author_cases = len(df[df['total_papers'] == 1])
        print(f"   Single-author cases: {single_author_cases:,}")
        
        real_anom = anom[anom['total_papers'] > 1]
        print(f"   POTENTIAL ANOMALIES (Multi-paper authors): {len(real_anom):,}")

    num_cols = df.select_dtypes(include=[np.number]).columns
    neg_check = (df[num_cols] < 0).sum().sum()
    print(f"\n2. Negative value check:")
    if neg_check == 0:
        print("   ✓ No negative values found")
    else:
        print(f"   ✗ Found {neg_check} negative values!")

    no_papers_with_cites = len(df[(df['total_papers'] == 0) & (df['total_citations'] > 0)])
    print(f"\n3. Authors with citations but no papers: {no_papers_with_cites}")
    
    papers_no_cites = len(df[(df['total_papers'] > 0) & (df['total_citations'] == 0)])
    print(f"\n4. Authors with papers but ZERO citations: {papers_no_cites:,} ({papers_no_cites/len(df)*100:.2f}%)")

    high_avg = df[df['avg_citations_per_paper'] > 1000]
    print(f"\n5. Authors with avg >1000 citations per paper: {len(high_avg):,}")
    print("   Top cases:")
    print(high_avg.nlargest(5, 'avg_citations_per_paper')[['author_name', 'total_citations', 'total_papers']].to_string(index=False))

    # ============================================================================
    # 12. AFFILIATION ANALYSIS
    # ============================================================================
    print_header("12. AFFILIATION ANALYSIS")

    if 'num_affiliations' in df.columns:
        print("Affiliation statistics:")
        print(f"  Avg affiliations per author: {df['num_affiliations'].mean():.2f}")
        print(f"  Median affiliations: {df['num_affiliations'].median():.0f}")
        print(f"  Max affiliations by single author: {df['num_affiliations'].max()}")

        print("\nAffiliation distribution:")
        # Corrected bins handling
        bins = [-1, 0, 1, 4, 9, 19, 49, 10000]
        labels = ['0', '1', '2-4', '5-9', '10-19', '20-49', '50+']
        
        max_val = df['num_affiliations'].max()
        if max_val > bins[-1]:
            bins[-1] = max_val + 1
            
        print_dist(df['num_affiliations'], bins, labels)

    # ============================================================================
    # 13. INTERESTING PATTERNS
    # ============================================================================
    print_header("13. INTERESTING PATTERNS")

    prolific_uncited = df[(df['total_papers'] > 50) & (df['total_citations'] == 0)]
    print(f"Prolific but uncited authors (>50 papers, 0 citations):")
    print(f"  Count: {len(prolific_uncited):,}")
    if len(prolific_uncited) > 0:
        print("  Top cases:")
        print(prolific_uncited.nlargest(5, 'total_papers')[['author_name', 'total_papers']].to_string(index=False))

    efficient = df[(df['total_citations'] > 1000) & (df['total_papers'] < 10)]
    print(f"\nHighly efficient authors (>1000 citations, <10 papers):")
    print(f"  Count: {len(efficient):,}")
    if len(efficient) > 0:
        print("  Top cases:")
        print(efficient.nlargest(5, 'total_citations')[['author_name', 'total_citations', 'total_papers']].to_string(index=False))

    # ============================================================================
    # 14. NEW VARIABLES ANALYSIS (ENHANCED)
    # ============================================================================
    print_header("14. NEW VARIABLES ANALYSIS (ENHANCED)")

    # A. CS EXPERIENCE
    if 'has_cs_experience' in df.columns and 'top_field' in df.columns:
        print("A. Computer Science Experience Logic Check")
        cs_exp_count = df['has_cs_experience'].sum()
        print(f"  Total Authors with CS Exp: {cs_exp_count:,} ({cs_exp_count/len(df)*100:.2f}%)")
        
        non_cs_authors = df[df['top_field'] != 'computer_science']
        non_cs_with_exp = non_cs_authors['has_cs_experience'].sum()
        print(f"\n  Non-CS Authors (Chem/Eng/MatSci): {len(non_cs_authors):,}")
        print(f"  -> With CS Experience:            {non_cs_with_exp:,} ({non_cs_with_exp/len(non_cs_authors)*100:.2f}%)")

        print("\n  CS Experience Rate by Top Field:")
        ct = pd.crosstab(df['top_field'], df['has_cs_experience'])
        if 1 in ct.columns:
            ct['Total'] = ct.sum(axis=1)
            ct['% with CS Exp'] = (ct[1] / ct['Total'] * 100)
            print(ct.sort_values(by='% with CS Exp', ascending=False)[['Total', 1, '% with CS Exp']].to_string())

    # B. AUTHOR PROFILE
    if 'author_profile' in df.columns:
        print("\nB. Author Profile (Specialist vs. Generalist)")
        print("  Profile Distribution:")
        counts = df['author_profile'].value_counts()
        for profile, count in counts.items():
            print(f"  {profile:<30}: {count:>9,} ({count/len(df)*100:.2f}%)")
            
        print("\n  Productivity (Avg Papers) by Profile:")
        perf = df.groupby('author_profile')[['total_papers', 'total_citations']].mean()
        perf['citations_per_paper'] = perf['total_citations'] / perf['total_papers']
        print(perf.sort_values('total_papers', ascending=False).to_string(float_format="{:.1f}".format))

    # C. FIELD COUNTS
    if 'field_counts' in df.columns:
        print("\nC. Field Counts Analysis (Parsing Strings)")
        import ast
        sample_size = 10000
        valid_sample = df['field_counts'].dropna().head(sample_size)
        try:
            parsed_counts = valid_sample.apply(ast.literal_eval)
            def calc_diversity(d):
                if not d: return 0
                total = sum(d.values())
                if total == 0: return 0
                top = max(d.values())
                return 1.0 - (top / total)
            diversity_scores = parsed_counts.apply(calc_diversity)
            print(f"  Analyzed sample of {sample_size:,} authors:")
            print(f"  Avg % of papers OUTSIDE top field: {diversity_scores.mean()*100:.2f}%")
        except Exception as e:
            print(f"  ERROR parsing field_counts: {e}")

    # ============================================================================
    # 15. TEAM SIZE ANALYSIS (NEW)
    # ============================================================================
    print_header("15. TEAM SIZE ANALYSIS (NEW VARIABLES)")
    
    # 1. Variable check
    team_vars = ['avg_team_size', 'avg_team_size_last_author', 'avg_team_size_sdl']
    available_vars = [v for v in team_vars if v in df.columns]
    
    if not available_vars:
        print("  NOTE: Team size variables not found in dataset.")
    else:
        # 2. Descriptive Stats
        print("Descriptive Statistics:")
        print(df[available_vars].describe().to_string())
        
        # 3. Distribution of Overall Team Size
        if 'avg_team_size' in df.columns:
            print("\nDistribution of Overall Avg Team Size:")
            # Bins suitable for team sizes: 1, 2-3, 4-6, 7-10, 11-20, 20+
            # Using -0.001 to catch 0 if any, though team size >= 1 usually
            bins = [0, 1, 3, 6, 10, 20, 10000]
            labels = ['1', '2-3', '4-6', '7-10', '11-20', '20+']
            
            # Handle max
            max_val = df['avg_team_size'].max()
            if max_val > bins[-1]: bins[-1] = max_val + 1
            
            print_dist(df['avg_team_size'], bins, labels)
            
        # 4. Managerial Hypothesis Check (Last Author vs Overall)
        # Hypothesis: Do they supervise larger teams than they participate in?
        if 'avg_team_size_last_author' in df.columns and 'avg_team_size' in df.columns:
            print("\nManagerial Proxy Check (Last Author vs Overall):")
            
            # Filter for authors who have actually been a last author
            last_authors = df[df['last_author_papers'] > 0].copy()
            print(f"  Authors with >0 last author papers: {len(last_authors):,}")
            
            last_authors['managerial_diff'] = last_authors['avg_team_size_last_author'] - last_authors['avg_team_size']
            
            print(f"  Avg Overall Team Size:      {last_authors['avg_team_size'].mean():.2f}")
            print(f"  Avg Last-Author Team Size:  {last_authors['avg_team_size_last_author'].mean():.2f}")
            print(f"  Avg Difference (Last-Over): {last_authors['managerial_diff'].mean():.2f}")
            
            pos_diff = (last_authors['managerial_diff'] > 0).sum()
            print(f"  Authors supervising LARGER teams than avg: {pos_diff:,} ({pos_diff/len(last_authors)*100:.1f}%)")

        # 5. SDL Context Check
        # Hypothesis: Are SDL teams larger?
        if 'avg_team_size_sdl' in df.columns and 'avg_team_size' in df.columns:
            print("\nSDL Context Check (SDL vs Overall):")
            
            sdl_authors = df[df['sdl_papers'] > 0].copy()
            print(f"  Authors with >0 SDL papers: {len(sdl_authors):,}")
            
            sdl_authors['sdl_diff'] = sdl_authors['avg_team_size_sdl'] - sdl_authors['avg_team_size']
            
            print(f"  Avg Overall Team Size:      {sdl_authors['avg_team_size'].mean():.2f}")
            print(f"  Avg SDL Team Size:          {sdl_authors['avg_team_size_sdl'].mean():.2f}")
            print(f"  Avg Difference (SDL-Over):  {sdl_authors['sdl_diff'].mean():.2f}")
            
            pos_diff = (sdl_authors['sdl_diff'] > 0).sum()
            print(f"  Authors with LARGER SDL teams than avg: {pos_diff:,} ({pos_diff/len(sdl_authors)*100:.1f}%)")

    print("\n" + "="*80)
    print("END OF REPORT")
    print("="*80)

if __name__ == "__main__":
    main()