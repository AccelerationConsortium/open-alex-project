# import json, pandas as pd
# import numpy as np
# from pathlib import Path
# import sys
# from multiprocessing import Pool, cpu_count

# # ============================================================================
# # CONFIGURATION
# # ============================================================================

# PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# FIELDS = {
#     'chemistry': PROJECT_DIR / "data/fields" / "chemistry",
#     'materials_science': PROJECT_DIR / "data/fields" / "material_science", 
#     'engineering': PROJECT_DIR / "data/fields" / "engineering",
#     'computer_science': PROJECT_DIR / "data/fields" / "computer_science"
# }

# # UPDATED: Use yearly author metrics file
# AUTHOR_METRICS_FILE = PROJECT_DIR / "data" / "yearly_data" / "author_metrics_yearly.csv"
# CS_KEYWORDS_FILE = PROJECT_DIR / "data/lasso_regression" / "cs_keywords_shortlisted.txt"  # Computer science keywords file

# # --- SDL FILTER CONFIGURATION ---
# SDL_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_journals.txt"
# SDL_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_primary_topics.txt"

# FILTER_CONFIG = {
#     'use_journal_filter': True,
#     'use_topic_filter': True,
# }
# # -----------------------------------------------------------

# OUTPUT_DIR = PROJECT_DIR / "data" / "yearly"
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# YEARS = range(2012, 2026)
# CHUNK_SIZE = 50000

# # ============================================================================
# # HELPER FUNCTIONS
# # ============================================================================

# def load_cs_keywords(file_path):
#     """Load CS keywords from text file into a set for fast lookup, skip commented lines"""
#     with open(file_path, 'r', encoding='utf-8') as f:
#         keywords = set(line.strip().lower() for line in f 
#                       if line.strip() and not line.strip().startswith('#'))
#     return keywords


# def check_cs_keyword_match(primary_topic, all_topics_str, title, abstract, cs_keywords_set):
#     """
#     Check if at least 2 different CS keywords match in topics, title, or abstract.
#     Returns 1 if >= 2 different keywords found, 0 otherwise.
#     """
#     matched_keywords = set()
    
#     # Check primary topic
#     if primary_topic:
#         primary_lower = primary_topic.lower()
#         for keyword in cs_keywords_set:
#             if keyword in primary_lower:
#                 matched_keywords.add(keyword)
#                 if len(matched_keywords) >= 2:
#                     return 1
    
#     # Check all topics
#     if all_topics_str:
#         all_topics_lower = all_topics_str.lower()
#         for keyword in cs_keywords_set:
#             if keyword in all_topics_lower:
#                 matched_keywords.add(keyword)
#                 if len(matched_keywords) >= 2:
#                     return 1
    
#     # Check title
#     if title and isinstance(title, str):
#         title_lower = title.lower()
#         for keyword in cs_keywords_set:
#             if keyword in title_lower:
#                 matched_keywords.add(keyword)
#                 if len(matched_keywords) >= 2:
#                     return 1
    
#     # Check abstract
#     if abstract and isinstance(abstract, str):
#         abstract_lower = abstract.lower()
#         for keyword in cs_keywords_set:
#             if keyword in abstract_lower:
#                 matched_keywords.add(keyword)
#                 if len(matched_keywords) >= 2:
#                     return 1
    
#     # Return 1 if at least 2 different keywords matched, 0 otherwise
#     return 1 if len(matched_keywords) >= 2 else 0


# def clean_author_id(author_id):
#     """Remove URL prefix from author ID for lookup"""
#     if pd.isna(author_id) or author_id == '':
#         return None
#     return str(author_id).replace('https://openalex.org/', '')


# def parse_authorships(raw_data_json):
#     """Extract first and last author IDs from raw_data"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return None, None
    
#     try:
#         data = json.loads(raw_data_json)
#         authorships = data.get('authorships', [])
        
#         if not authorships:
#             return None, None
        
#         first_author_id = clean_author_id(authorships[0].get('author', {}).get('id'))
#         last_author_id = clean_author_id(authorships[-1].get('author', {}).get('id'))
        
#         return first_author_id, last_author_id
    
#     except:
#         return None, None


# def parse_corresponding_authors(raw_data_json):
#     """Extract corresponding author IDs and select primary one"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return None, []
    
#     try:
#         data = json.loads(raw_data_json)
#         corr_ids = data.get('corresponding_author_ids', [])
        
#         if not corr_ids:
#             return None, []
        
#         # Clean IDs
#         cleaned_ids = [clean_author_id(aid) for aid in corr_ids if aid]
        
#         # Primary corresponding = first one in list
#         primary_corr = cleaned_ids[0] if cleaned_ids else None
        
#         return primary_corr, cleaned_ids
    
#     except:
#         return None, []


# def parse_paper_metadata(raw_data_json):
#     """Extract topics (primary + all), journal, citations, affiliations count, publication date, abstract"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return None, None, None, 0, 0, None, None
    
#     try:
#         data = json.loads(raw_data_json)
        
#         # Topics - get ALL topics
#         topics = data.get('topics', [])
#         primary_topic = topics[0].get('display_name') if topics else None
        
#         # Extract all topic names as a list
#         all_topics = [t.get('display_name') for t in topics if t.get('display_name')]
#         # Convert to pipe-separated string for CSV storage
#         all_topics_str = '|'.join(all_topics) if all_topics else None
        
#         # Journal
#         journal = data.get('primary_location', {}).get('source', {}).get('display_name')
        
#         # Citations
#         cited_by_count = data.get('cited_by_count', 0) or 0
        
#         # Publication date
#         publication_date = data.get('publication_date')
        
#         # Abstract - convert from inverted index to paragraph form
#         abstract_text = None
#         abstract_inverted = data.get('abstract_inverted_index')
#         if abstract_inverted:
#             # Inverted index format: {"word": [position1, position2, ...]}
#             # Need to reconstruct the original text
#             word_positions = []
#             for word, positions in abstract_inverted.items():
#                 for pos in positions:
#                     word_positions.append((pos, word))
            
#             # Sort by position and join words
#             word_positions.sort(key=lambda x: x[0])
#             abstract_text = ' '.join([word for pos, word in word_positions])
        
#         # Count unique affiliations
#         authorships = data.get('authorships', [])
#         all_institutions = set()
#         for authorship in authorships:
#             for inst in authorship.get('institutions', []):
#                 inst_id = inst.get('id')
#                 if inst_id:
#                     all_institutions.add(inst_id)
        
#         num_paper_affiliations = len(all_institutions)
        
#         return primary_topic, all_topics_str, journal, cited_by_count, num_paper_affiliations, publication_date, abstract_text
    
#     except:
#         return None, None, None, 0, 0, None, None


# def get_corresponding_position(first_id, last_id, corr_id, corr_ids_list):
#     """Determine position of corresponding author"""
#     if not corr_id:
#         return 'missing'
    
#     if first_id == last_id:  # Single author
#         return 'only'
    
#     # Check if first or last
#     is_first = (corr_id == first_id)
#     is_last = (corr_id == last_id)
    
#     if is_first and is_last:
#         return 'both'
#     elif is_first:
#         return 'first'
#     elif is_last:
#         return 'last'
#     else:
#         return 'middle'


# # ============================================================================
# # PARALLEL PROCESSING FUNCTION (YEAR-LEVEL)
# # ============================================================================
# def process_field_year(args):
#     """Process a single (field, year) combination - designed to run in parallel"""
#     field_name, field_dir, year, author_metrics_path, cs_keywords_path = args
    
#     tsv_file = field_dir / f"{field_name}_{year}.tsv"
    
#     if not tsv_file.exists():
#         return field_name, year, [], 0, 0
    
#     # Load YEARLY author metrics (each process gets its own copy)
#     # Key change: we now have (author_id, year) as the index
#     author_df = pd.read_csv(author_metrics_path)
#     # Create multi-index for fast lookup by (author_id, year)
#     author_df = author_df.set_index(['author_id', 'year'])
    
#     # Load CS keywords (each process gets its own copy)
#     cs_keywords = load_cs_keywords(cs_keywords_path)
    
#     papers = []
#     total = 0
#     skipped = 0
    
#     try:
#         # Read in chunks
#         for chunk in pd.read_csv(
#             tsv_file, 
#             sep='\t',
#             usecols=['article_id', 'doi', 'title', 
#                      'publication_year', 'author_count', 'SDL', 
#                      'AI_Paper', 'Robotics_Paper', 'raw_data'],
#             chunksize=CHUNK_SIZE,
#             low_memory=False,
#             on_bad_lines='skip'
#         ):
            
#             for _, row in chunk.iterrows():
                
#                 try:
#                     # Get publication year for this paper
#                     pub_year = row['publication_year']
                    
#                     # Parse authorships
#                     first_author_id, last_author_id = parse_authorships(row['raw_data'])
                    
#                     if not first_author_id or not last_author_id:
#                         skipped += 1
#                         continue
                    
#                     # Parse corresponding authors
#                     primary_corr_id, all_corr_ids = parse_corresponding_authors(row['raw_data'])
                    
#                     # Parse paper metadata (INCLUDES ABSTRACT)
#                     primary_topic, all_topics_str, journal, cited_by_count, num_affiliations, publication_date, abstract = \
#                         parse_paper_metadata(row['raw_data'])
                    
#                     # Get title from row
#                     title = row.get('title', '')
                    
#                     # Determine CS experience for paper using KEYWORD MATCHING
#                     if field_name == 'computer_science':
#                         comp_sci_experience_paper = 1
#                     else:
#                         # Check if at least 2 different keywords match in topics/title/abstract
#                         comp_sci_experience_paper = check_cs_keyword_match(
#                             primary_topic, all_topics_str, title, abstract, cs_keywords
#                         )
                    
#                     # ============================================================
#                     # KEY CHANGE: Look up author metrics for THIS SPECIFIC YEAR
#                     # ============================================================
                    
#                     # Get first author metrics (cumulative up to pub_year)
#                     if (first_author_id, pub_year) in author_df.index:
#                         first_author = author_df.loc[(first_author_id, pub_year)]
#                         first_papers = first_author['total_papers_to_date']
#                         first_citations = first_author['total_citations_to_date']
#                         first_sdl_exp = first_author['sdl_papers_to_date']
#                         first_field = first_author['top_field_to_date']
#                     else:
#                         # If author not in metrics for this year, use zeros
#                         first_papers = 0
#                         first_citations = 0
#                         first_sdl_exp = 0
#                         first_field = ''
                    
#                     # Get last author metrics (cumulative up to pub_year)
#                     if (last_author_id, pub_year) in author_df.index:
#                         last_author = author_df.loc[(last_author_id, pub_year)]
#                         last_papers = last_author['total_papers_to_date']
#                         last_citations = last_author['total_citations_to_date']
#                         last_sdl_exp = last_author['sdl_papers_to_date']
#                         last_field = last_author['top_field_to_date']
#                     else:
#                         last_papers = 0
#                         last_citations = 0
#                         last_sdl_exp = 0
#                         last_field = ''
                    
#                     # Get corresponding author metrics (cumulative up to pub_year)
#                     if primary_corr_id and (primary_corr_id, pub_year) in author_df.index:
#                         corr_author = author_df.loc[(primary_corr_id, pub_year)]
#                         corr_papers = corr_author['total_papers_to_date']
#                         corr_citations = corr_author['total_citations_to_date']
#                         corr_sdl_exp = corr_author['sdl_papers_to_date']
#                     else:
#                         corr_papers = 0
#                         corr_citations = 0
#                         corr_sdl_exp = 0
                    
#                     # Determine corresponding position
#                     corr_position = get_corresponding_position(
#                         first_author_id, last_author_id, primary_corr_id, all_corr_ids
#                     )
                    
#                     # Check if first/last is corresponding
#                     first_is_corr = 1 if first_author_id in all_corr_ids else 0
#                     last_is_corr = 1 if last_author_id in all_corr_ids else 0
                    
#                     # Create paper record
#                     paper_record = {
#                         # Identifiers
#                         'article_id': row['article_id'],
#                         'doi': row.get('doi', ''),
#                         'title': title,
#                         'abstract': abstract or '',
#                         'publication_year': row['publication_year'],
#                         'publication_date': publication_date or '',
                        
#                         # Dependent variable
#                         'author_count': row['author_count'],
                        
#                         # Treatment variables
#                         'SDL': row['SDL'],
#                         'AI_Paper': row.get('AI_Paper', 0),
#                         'Robotics_Paper': row.get('Robotics_Paper', 0),
                        
#                         # Paper-level controls
#                         'num_paper_affiliations': num_affiliations,
#                         'primary_topic': primary_topic or 'MISSING',
#                         'all_topics': all_topics_str or '',
#                         'journal': journal or 'MISSING',
#                         'cited_by_count': cited_by_count,
#                         'field': field_name,
#                         'comp_sci_experience_paper': comp_sci_experience_paper,
                        
#                         # First author metrics (CUMULATIVE TO DATE)
#                         'first_author_id': first_author_id,
#                         'first_author_papers': first_papers,
#                         'first_author_citations': first_citations,
#                         'first_author_sdl_experience': first_sdl_exp,
#                         'first_author_is_corresponding': first_is_corr,
#                         'first_author_field': first_field,
                        
#                         # Last author metrics (CUMULATIVE TO DATE)
#                         'last_author_id': last_author_id,
#                         'last_author_papers': last_papers,
#                         'last_author_citations': last_citations,
#                         'last_author_sdl_experience': last_sdl_exp,
#                         'last_author_is_corresponding': last_is_corr,
#                         'last_author_field': last_field,
                        
#                         # Corresponding author metrics (CUMULATIVE TO DATE)
#                         'corresponding_author_id': primary_corr_id or '',
#                         'corresponding_author_papers': corr_papers,
#                         'corresponding_author_citations': corr_citations,
#                         'corresponding_author_sdl_experience': corr_sdl_exp,
#                         'corresponding_position': corr_position,
#                         'num_corresponding_authors': len(all_corr_ids)
#                     }
                    
#                     papers.append(paper_record)
#                     total += 1
                    
#                 except Exception as e:
#                     skipped += 1
        
#     except Exception as e:
#         pass
    
#     return field_name, year, papers, total, skipped

# # ============================================================================
# # MAIN PROCESSING
# # ============================================================================

# def load_sdl_venues():
#     """Load SDL journals and topics for filtering"""
#     sdl_journals = set()
#     sdl_topics = set()
    
#     print("\n--- Loading SDL Venue Lists ---")
    
#     if FILTER_CONFIG['use_journal_filter'] and SDL_JOURNALS_FILE.exists():
#         with open(SDL_JOURNALS_FILE, 'r') as f:
#             sdl_journals = {line.strip() for line in f if line.strip()}
#         print(f"✓ Loaded {len(sdl_journals)} SDL journals.")
#     elif FILTER_CONFIG['use_journal_filter']:
#         print(f"❌ ERROR: SDL journals file not found: {SDL_JOURNALS_FILE}")
    
#     if FILTER_CONFIG['use_topic_filter'] and SDL_TOPICS_FILE.exists():
#         with open(SDL_TOPICS_FILE, 'r') as f:
#             sdl_topics = {line.strip() for line in f if line.strip()}
#         print(f"✓ Loaded {len(sdl_topics)} SDL topics.")
#     elif FILTER_CONFIG['use_topic_filter']:
#         print(f"❌ ERROR: SDL topics file not found: {SDL_TOPICS_FILE}")

#     return sdl_journals, sdl_topics


# def build_regression_dataset():
#     """Build complete regression dataset using parallel processing (year-level)"""
    
#     print("="*80)
#     print("BUILDING FILTERED REGRESSION DATASET WITH YEARLY AUTHOR METRICS")
#     print("="*80)
#     print(f"\nOutput directory: {OUTPUT_DIR}")
#     print(f"Years: {min(YEARS)}-{max(YEARS)-1}")
#     print(f"Fields: {len(FIELDS)}")
#     print(f"Filtering: SDL journals AND topics (matched venue design)")
#     print(f"CPU cores available: {cpu_count()}")
#     print(f"Using up to 20 parallel processes\n")
    
#     # ========================================================================
#     # STEP 1: Verify files exist
#     # ========================================================================
    
#     print("="*80)
#     print("STEP 1: Verifying required files")
#     print("="*80)
    
#     if not AUTHOR_METRICS_FILE.exists():
#         print(f"❌ ERROR: Author metrics file not found: {AUTHOR_METRICS_FILE}")
#         sys.exit(1)
#     print(f"✓ Found: {AUTHOR_METRICS_FILE}")
    
#     if not CS_KEYWORDS_FILE.exists():
#         print(f"❌ ERROR: CS keywords file not found: {CS_KEYWORDS_FILE}")
#         sys.exit(1)
#     print(f"✓ Found: {CS_KEYWORDS_FILE}")
    
#     # Load and display CS keywords count
#     cs_keywords = load_cs_keywords(CS_KEYWORDS_FILE)
#     print(f"✓ Loaded {len(cs_keywords)} CS keywords\n")
    
#     # Load SDL venue lists for filtering
#     sdl_journals, sdl_topics = load_sdl_venues()
    
#     # ========================================================================
#     # STEP 2: Build task list (field, year combinations)
#     # ========================================================================
    
#     print("="*80)
#     print("STEP 2: Building task list")
#     print("="*80)
    
#     tasks = []
#     for field_name, field_dir in FIELDS.items():
#         if not field_dir.exists():
#             print(f"  ✗ {field_name}: directory not found")
#             continue
        
#         print(f"  ✓ {field_name}: {field_dir}")
#         for year in YEARS:
#             tasks.append((field_name, field_dir, year, AUTHOR_METRICS_FILE, CS_KEYWORDS_FILE))
    
#     print(f"\n✓ {len(tasks)} tasks ready (field × year combinations)\n")
    
#     # ========================================================================
#     # STEP 3: Process tasks in parallel
#     # ========================================================================
    
#     print("="*80)
#     print("STEP 3: Processing tasks in parallel")
#     print("="*80)
#     print("Progress will be displayed as tasks complete...\n")
    
#     num_processes = min(20, len(tasks), cpu_count())
    
#     with Pool(processes=num_processes) as pool:
#         results = pool.map(process_field_year, tasks)
    
#     # ========================================================================
#     # STEP 4: Combine results
#     # ========================================================================
    
#     print(f"\n{'='*80}")
#     print("STEP 4: Combining results")
#     print("="*80)
    
#     all_papers = []
#     total_papers = 0
#     total_skipped = 0
    
#     # Group by field for summary
#     field_summary = {}
    
#     for field_name, year, papers, total, skipped in results:
#         all_papers.extend(papers)
#         total_papers += total
#         total_skipped += skipped
        
#         if field_name not in field_summary:
#             field_summary[field_name] = {'papers': 0, 'skipped': 0}
#         field_summary[field_name]['papers'] += total
#         field_summary[field_name]['skipped'] += skipped
    
#     for field_name, stats in field_summary.items():
#         print(f"  {field_name}: {stats['papers']:,} papers ({stats['skipped']:,} skipped)")
    
#     print(f"\nTOTAL: {total_papers:,} papers ({total_skipped:,} skipped)\n")
    
#     # ========================================================================
#     # STEP 5: Create DataFrame and apply transformations
#     # ========================================================================
    
#     print("="*80)
#     print("STEP 5: Creating DataFrame and transformations")
#     print("="*80)
    
#     df = pd.DataFrame(all_papers)
#     print(f"  DataFrame shape: {df.shape}")
    
#     # Apply asinh transformations
#     print("  Applying transformations...")
#     df['asinh_first_author_papers'] = np.arcsinh(df['first_author_papers'].astype(float))
#     df['asinh_first_author_citations'] = np.arcsinh(df['first_author_citations'].astype(float))
#     df['asinh_last_author_papers'] = np.arcsinh(df['last_author_papers'].astype(float))
#     df['asinh_last_author_citations'] = np.arcsinh(df['last_author_citations'].astype(float))
#     df['asinh_corresponding_papers'] = np.arcsinh(df['corresponding_author_papers'].astype(float))
#     df['asinh_corresponding_citations'] = np.arcsinh(df['corresponding_author_citations'].astype(float))
#     df['asinh_paper_citations'] = np.arcsinh(df['cited_by_count'].astype(float))
    
#     # Log transform (handle zeros by filtering or using log1p)
#     df['log_author_count'] = np.log(df['author_count'].astype(float).replace(0, np.nan))
    
#     print("  ✓ Transformations complete\n")
    
#     # ========================================================================
#     # STEP 6: Apply Regression Filters and Save Filtered Dataset
#     # ========================================================================
    
#     print(f"\n{'='*80}")
#     print("STEP 6: Applying Regression Filters and Saving Filtered Dataset")
#     print("="*80)
    
#     df_filtered = df.copy()
#     initial_count = len(df_filtered)
    
#     # --- Filter 1 & 2: SDL Venue Filters ---
#     print(f"  Applying venue filters (Journals={FILTER_CONFIG['use_journal_filter']}, Topics={FILTER_CONFIG['use_topic_filter']})...")
    
#     mask = pd.Series(True, index=df_filtered.index)
    
#     if FILTER_CONFIG['use_journal_filter'] and len(sdl_journals) > 0:
#         mask &= df_filtered['journal'].isin(sdl_journals)
    
#     if FILTER_CONFIG['use_topic_filter'] and len(sdl_topics) > 0:
#         mask &= df_filtered['primary_topic'].isin(sdl_topics)
    
#     df_filtered = df_filtered[mask].copy()
    
#     print(f"  Rows after venue filtering: {len(df_filtered):,}")
    
#     # --- Filter 3: Remove Missing Key Regression Variables ---
#     key_vars = ['author_count', 'publication_year', 'field', 'asinh_first_author_papers', 'asinh_last_author_papers']
    
#     pre_dropna_count = len(df_filtered)
#     df_filtered = df_filtered.dropna(subset=key_vars)
#     removed_missing = pre_dropna_count - len(df_filtered)
    
#     print(f"  Removed {removed_missing:,} rows with missing key regression variables.")
#     print(f"  Final filtered rows: {len(df_filtered):,}")
    
#     # Save as CSV
#     csv_file_filtered = OUTPUT_DIR / "regression_dataset_filtered_yearly_with_abstract.csv"
#     print(f"\nSaving FILTERED dataset: {csv_file_filtered}")
#     df_filtered.to_csv(csv_file_filtered, index=False)
#     csv_size_filtered = csv_file_filtered.stat().st_size / (1024 * 1024)
#     print(f"  Size: {csv_size_filtered:.1f} MB")
    
#     # ========================================================================
#     # STEP 7: Summary statistics
#     # ========================================================================
    
#     print(f"\n{'='*80}")
#     print("SUMMARY STATISTICS - FILTERED DATASET")
#     print("="*80)
    
#     print(f"\nTotal papers: {len(df_filtered):,}")
#     print(f"  SDL papers: {df_filtered['SDL'].sum():,}")
#     print(f"  Non-SDL papers: {(df_filtered['SDL'] == 0).sum():,}")
#     print(f"  CS Experience papers (KEYWORD MATCHING): {df_filtered['comp_sci_experience_paper'].sum():,}")
    
#     # Check abstracts in filtered dataset
#     filtered_with_abstract = df_filtered['abstract'].notna().sum()
#     print(f"  Papers with abstracts: {filtered_with_abstract:,} ({filtered_with_abstract/len(df_filtered)*100:.1f}%)")
    
#     print(f"\nPapers by field:")
#     print(df_filtered['field'].value_counts().to_string())
    
#     print(f"\nCS Experience by field:")
#     print(df_filtered.groupby('field')['comp_sci_experience_paper'].agg(['sum', 'count', 'mean']).to_string())
    
#     print(f"\nPapers by year:")
#     print(df_filtered['publication_year'].value_counts().sort_index().to_string())
    
#     print(f"\nAuthor metrics summary (first authors):")
#     print(df_filtered[['first_author_papers', 'first_author_citations', 'first_author_sdl_experience']].describe().to_string())
    
#     print(f"\nAuthor metrics summary (last authors):")
#     print(df_filtered[['last_author_papers', 'last_author_citations', 'last_author_sdl_experience']].describe().to_string())
    
#     print(f"\n{'='*80}")
#     print("✅ COMPLETE!")
#     print("="*80)
#     print(f"\nOutput file:")
#     print(f"  {csv_file_filtered}")
#     print(f"  Size: {csv_size_filtered:.1f} MB\n")
    
#     return df_filtered


# # ============================================================================
# # MAIN EXECUTION
# # ============================================================================

# if __name__ == "__main__":
#     df_final = build_regression_dataset()
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")
REGRESSION_FILE = PROJECT_DIR / "data/yearly_data/test" / "regression_dataset_filtered_yearly_with_abstract.csv"
OUTPUT_FILE = PROJECT_DIR / "data/yearly_data/test" / "eda_regression_yearly_report.txt"

REPORT_WIDTH = 80
SEPARATOR = "=" * REPORT_WIDTH

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_section(title):
    """Print formatted section header"""
    print(f"\n{SEPARATOR}")
    print(title)
    print(SEPARATOR)

def safe_percentage(numerator, denominator):
    """Calculate percentage safely"""
    if denominator == 0:
        return 0.0
    return 100 * numerator / denominator

# ============================================================================
# MAIN EDA FUNCTION
# ============================================================================

def generate_yearly_regression_eda(df):
    """Generate comprehensive EDA report for yearly regression dataset"""
    
    # ========================================================================
    # HEADER
    # ========================================================================
    
    print(SEPARATOR)
    print("EXPLORATORY DATA ANALYSIS - YEARLY REGRESSION DATASET")
    print(SEPARATOR)
    print(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Source file: {REGRESSION_FILE}")
    print(SEPARATOR)
    
    # ========================================================================
    # DATASET OVERVIEW
    # ========================================================================
    
    print_section("DATASET OVERVIEW")
    
    print("\nSample: SDL VENUE MATCHED PAPERS WITH YEARLY AUTHOR METRICS")
    print("Filtering: Papers in SDL journals AND topics")
    print("Author Metrics: CUMULATIVE TO PUBLICATION YEAR\n")
    
    print(f"Total papers: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    print(f"Memory usage: {memory_mb:.2f} MB")
    
    print("\nColumns:")
    for i, col in enumerate(df.columns, 1):
        print(f"   {i:2}. {col}")
    
    # ========================================================================
    # 1B. ABSTRACT ANALYSIS
    # ========================================================================
    
    print_section("1B. ABSTRACT ANALYSIS")
    
    has_abstract = df['abstract'].notna() & (df['abstract'] != '')
    abstract_count = has_abstract.sum()
    
    print(f"\nPapers with abstracts: {abstract_count:,} ({safe_percentage(abstract_count, len(df)):.2f}%)")
    print(f"Papers without abstracts: {(~has_abstract).sum():,} ({safe_percentage((~has_abstract).sum(), len(df)):.2f}%)")
    
    if abstract_count > 0:
        abstract_lengths = df.loc[has_abstract, 'abstract'].str.len()
        print(f"\nAbstract length statistics (characters):")
        print(f"  Mean: {abstract_lengths.mean():.0f}")
        print(f"  Median: {abstract_lengths.median():.0f}")
        print(f"  Min: {abstract_lengths.min():.0f}")
        print(f"  Max: {abstract_lengths.max():.0f}")
        
        abstract_words = df.loc[has_abstract, 'abstract'].str.split().str.len()
        print(f"\nAbstract word count:")
        print(f"  Mean: {abstract_words.mean():.0f}")
        print(f"  Median: {abstract_words.median():.0f}")
        print(f"  Min: {abstract_words.min():.0f}")
        print(f"  Max: {abstract_words.max():.0f}")
    
    print(f"\nAbstracts by field:")
    for field in df['field'].unique():
        field_total = (df['field'] == field).sum()
        field_abstract = ((df['field'] == field) & has_abstract).sum()
        print(f"  {field:<20}: {field_abstract:,} / {field_total:,} ({safe_percentage(field_abstract, field_total):.2f}%)")
    
    sdl_with_abstract = ((df['SDL'] == 1) & has_abstract).sum()
    sdl_total = (df['SDL'] == 1).sum()
    print(f"\nSDL papers with abstracts: {sdl_with_abstract} / {sdl_total} ({safe_percentage(sdl_with_abstract, sdl_total):.2f}%)")
    
    # ========================================================================
    # 2. MISSING VALUES ANALYSIS
    # ========================================================================
    
    print_section("2. MISSING VALUES ANALYSIS")
    
    missing = df.isnull().sum()
    missing_cols = missing[missing > 0].sort_values(ascending=False)
    
    if len(missing_cols) > 0:
        print("\nColumns with missing values:")
        for col, count in missing_cols.items():
            pct = safe_percentage(count, len(df))
            print(f"  {col}: {count:,} ({pct:.2f}%)")
    else:
        print("\n✓ No missing values found")
    
    # ========================================================================
    # 3. DEPENDENT VARIABLE - TEAM SIZE
    # ========================================================================
    
    print_section("3. DEPENDENT VARIABLE - TEAM SIZE (author_count)")
    
    print(f"\n{df['author_count'].describe().to_string()}")
    
    print("\nTeam size distribution:")
    bins = [
        (df['author_count'] == 1, "1"),
        (df['author_count'] == 2, "2"),
        (df['author_count'] == 3, "3"),
        (df['author_count'] == 4, "4"),
        ((df['author_count'] >= 5) & (df['author_count'] <= 9), "5-9"),
        ((df['author_count'] >= 10) & (df['author_count'] <= 19), "10-19"),
        ((df['author_count'] >= 20) & (df['author_count'] <= 49), "20-49"),
        ((df['author_count'] >= 50) & (df['author_count'] <= 99), "50-99"),
        (df['author_count'] >= 100, "100+")
    ]
    
    for condition, label in bins:
        count = condition.sum()
        pct = safe_percentage(count, len(df))
        print(f"  {label:<8}: {count:,} ({pct:.2f}%)")
    
    # ========================================================================
    # 4. TREATMENT VARIABLES
    # ========================================================================
    
    print_section("4. TREATMENT VARIABLES")
    
    sdl_count = (df['SDL'] == 1).sum()
    ai_count = (df['AI_Paper'] == 1).sum()
    robotics_count = (df['Robotics_Paper'] == 1).sum()
    
    print(f"\nSDL papers: {sdl_count:,} ({safe_percentage(sdl_count, len(df)):.2f}%)")
    print(f"AI papers: {ai_count:,} ({safe_percentage(ai_count, len(df)):.2f}%)")
    print(f"Robotics papers: {robotics_count:,} ({safe_percentage(robotics_count, len(df)):.2f}%)")
    
    print("\nOverlap analysis:")
    sdl_only = ((df['SDL'] == 1) & (df['AI_Paper'] == 0) & (df['Robotics_Paper'] == 0)).sum()
    sdl_ai = ((df['SDL'] == 1) & (df['AI_Paper'] == 1) & (df['Robotics_Paper'] == 0)).sum()
    sdl_robotics = ((df['SDL'] == 1) & (df['AI_Paper'] == 0) & (df['Robotics_Paper'] == 1)).sum()
    sdl_both = ((df['SDL'] == 1) & (df['AI_Paper'] == 1) & (df['Robotics_Paper'] == 1)).sum()
    
    print(f"  SDL only: {sdl_only}")
    print(f"  SDL + AI: {sdl_ai}")
    print(f"  SDL + Robotics: {sdl_robotics}")
    print(f"  SDL + AI + Robotics: {sdl_both}")
    
    print("\nAverage team size by treatment:")
    print(f"  SDL papers: {df[df['SDL'] == 1]['author_count'].mean():.2f}")
    print(f"  Non-SDL papers: {df[df['SDL'] == 0]['author_count'].mean():.2f}")
    print(f"  AI papers: {df[df['AI_Paper'] == 1]['author_count'].mean():.2f}")
    print(f"  Robotics papers: {df[df['Robotics_Paper'] == 1]['author_count'].mean():.2f}")
    
    # ========================================================================
    # 5. FIELD DISTRIBUTION
    # ========================================================================
    
    print_section("5. FIELD DISTRIBUTION")
    
    field_counts = df['field'].value_counts()
    print()
    for field, count in field_counts.items():
        pct = safe_percentage(count, len(df))
        print(f"  {field:<20}: {count:,} ({pct:.2f}%)")
    
    print("\nSDL papers by field:")
    for field in df['field'].unique():
        count = ((df['field'] == field) & (df['SDL'] == 1)).sum()
        print(f"  {field:<20}: {count}")
    
    # ========================================================================
    # 5B. CS EXPERIENCE ANALYSIS
    # ========================================================================
    
    print_section("5B. CS EXPERIENCE ANALYSIS (KEYWORD MATCHING)")
    
    print("\nCS Experience Logic: CS field = 1, Others = 1 if 2+ different keywords in topics/title/abstract")
    
    cs_exp_count = (df['comp_sci_experience_paper'] == 1).sum()
    no_cs_exp = (df['comp_sci_experience_paper'] == 0).sum()
    
    print(f"\nPapers with CS experience: {cs_exp_count:,} ({safe_percentage(cs_exp_count, len(df)):.2f}%)")
    print(f"Papers without CS experience: {no_cs_exp:,} ({safe_percentage(no_cs_exp, len(df)):.2f}%)")
    
    print("\nCS experience by field:")
    for field in df['field'].unique():
        field_total = (df['field'] == field).sum()
        field_cs = ((df['field'] == field) & (df['comp_sci_experience_paper'] == 1)).sum()
        print(f"  {field:<20}: {field_cs:,} / {field_total:,} ({safe_percentage(field_cs, field_total):.2f}%)")
    
    non_cs_fields = df[df['field'] != 'computer_science']
    non_cs_total = len(non_cs_fields)
    non_cs_with_keywords = (non_cs_fields['comp_sci_experience_paper'] == 1).sum()
    
    print(f"\nCS experience in non-CS fields:")
    print(f"  Total non-CS papers: {non_cs_total:,}")
    print(f"  Non-CS papers with CS keywords: {non_cs_with_keywords:,} ({safe_percentage(non_cs_with_keywords, non_cs_total):.2f}%)")
    
    print("\nAverage team size by CS experience:")
    print(f"  With CS experience: {df[df['comp_sci_experience_paper'] == 1]['author_count'].mean():.2f}")
    print(f"  Without CS experience: {df[df['comp_sci_experience_paper'] == 0]['author_count'].mean():.2f}")
    
    sdl_with_cs = ((df['SDL'] == 1) & (df['comp_sci_experience_paper'] == 1)).sum()
    sdl_without_cs = ((df['SDL'] == 1) & (df['comp_sci_experience_paper'] == 0)).sum()
    
    print("\nSDL papers and CS experience:")
    print(f"  SDL with CS experience: {sdl_with_cs} ({safe_percentage(sdl_with_cs, sdl_total):.2f}%)")
    print(f"  SDL without CS experience: {sdl_without_cs} ({safe_percentage(sdl_without_cs, sdl_total):.2f}%)")
    
    # ========================================================================
    # 6. TEMPORAL DISTRIBUTION
    # ========================================================================
    
    print_section("6. TEMPORAL DISTRIBUTION")
    
    print("\nPapers by year:")
    year_counts = df['publication_year'].value_counts().sort_index()
    for year, count in year_counts.items():
        sdl_year = ((df['publication_year'] == year) & (df['SDL'] == 1)).sum()
        print(f"  {year}: {count:,} papers ({sdl_year} SDL)")
    
    # ========================================================================
    # 7. AUTHOR METRICS STATISTICS (YEARLY/CUMULATIVE)
    # ========================================================================
    
    print_section("7. AUTHOR METRICS STATISTICS (CUMULATIVE TO PUBLICATION YEAR)")
    
    print("\n⚠️  IMPORTANT: These metrics are CUMULATIVE up to publication year")
    print("   - NOT career totals")
    print("   - Values increase over time for the same author")
    print("   - Papers in 2015 use metrics ≤ 2015, papers in 2020 use metrics ≤ 2020\n")
    
    first_cols = ['first_author_papers', 'first_author_citations', 'first_author_sdl_experience']
    print("First author metrics:")
    print(df[first_cols].describe().to_string())
    
    last_cols = ['last_author_papers', 'last_author_citations', 'last_author_sdl_experience']
    print("\n\nLast author metrics:")
    print(df[last_cols].describe().to_string())
    
    corr_cols = ['corresponding_author_papers', 'corresponding_author_citations', 'corresponding_author_sdl_experience']
    print("\n\nCorresponding author metrics:")
    print(df[corr_cols].describe().to_string())
    
    # ========================================================================
    # 7B. TEMPORAL VALIDATION OF AUTHOR METRICS
    # ========================================================================
    
    print_section("7B. TEMPORAL VALIDATION - AUTHOR METRICS OVER TIME")
    
    print("\nThis validates that author metrics increase over time (as expected)")
    print("Showing average metrics by publication year:\n")
    
    temporal_stats = df.groupby('publication_year').agg({
        'first_author_papers': 'mean',
        'first_author_citations': 'mean',
        'last_author_papers': 'mean',
        'last_author_citations': 'mean'
    }).round(2)
    
    print("Year    First_Papers  First_Cites  Last_Papers  Last_Cites")
    print("-" * 65)
    for year in temporal_stats.index:
        print(f"{year}    {temporal_stats.loc[year, 'first_author_papers']:>11.2f}  "
              f"{temporal_stats.loc[year, 'first_author_citations']:>11.2f}  "
              f"{temporal_stats.loc[year, 'last_author_papers']:>10.2f}  "
              f"{temporal_stats.loc[year, 'last_author_citations']:>10.2f}")
    
    print("\n✓ Metrics should generally increase over time due to cumulative nature")
    print("  (Some variation is normal due to different author cohorts each year)")
    
    # ========================================================================
    # 8. CORRESPONDING AUTHOR POSITION ANALYSIS
    # ========================================================================
    
    print_section("8. CORRESPONDING AUTHOR POSITION ANALYSIS")
    
    print("\nCorresponding author position distribution:")
    corr_pos_counts = df['corresponding_position'].value_counts()
    for pos, count in corr_pos_counts.items():
        pct = safe_percentage(count, len(df))
        print(f"  {pos:<10}: {count:,} ({pct:.2f}%)")
    
    first_is_corr = (df['first_author_is_corresponding'] == 1).sum()
    last_is_corr = (df['last_author_is_corresponding'] == 1).sum()
    both_corr = ((df['first_author_is_corresponding'] == 1) & 
                 (df['last_author_is_corresponding'] == 1)).sum()
    
    print("\nFirst/Last author as corresponding:")
    print(f"  First author is corresponding: {first_is_corr:,} ({safe_percentage(first_is_corr, len(df)):.2f}%)")
    print(f"  Last author is corresponding: {last_is_corr:,} ({safe_percentage(last_is_corr, len(df)):.2f}%)")
    print(f"  Both first and last: {both_corr:,}")
    
    # ========================================================================
    # 9. PAPER-LEVEL CONTROLS
    # ========================================================================
    
    print_section("9. PAPER-LEVEL CONTROLS")
    
    print("\nAffiliations per paper:")
    print(df['num_paper_affiliations'].describe().to_string())
    
    print("\n\nCitations per paper:")
    print(df['cited_by_count'].describe().to_string())
    
    print("\n\nTop 20 primary topics:")
    topic_counts = df['primary_topic'].value_counts().head(20)
    for i, (topic, count) in enumerate(topic_counts.items(), 1):
        pct = safe_percentage(count, len(df))
        print(f"   {i:2}. {topic:<60}: {count:,} ({pct:.2f}%)")
    
    print("\n\nTop 20 journals:")
    journal_counts = df['journal'].value_counts().head(20)
    for i, (journal, count) in enumerate(journal_counts.items(), 1):
        pct = safe_percentage(count, len(df))
        print(f"   {i:2}. {journal:<60}: {count:,} ({pct:.2f}%)")
    
    print("\n\nUnique venues in sample:")
    print(f"  Unique journals: {df['journal'].nunique()}")
    print(f"  Unique primary topics: {df['primary_topic'].nunique()}")
    
    # ========================================================================
    # 10. ALL TOPICS ANALYSIS
    # ========================================================================
    
    print_section("10. ALL TOPICS ANALYSIS")
    
    # Count topics per paper
    topics_per_paper = df['all_topics'].str.split('|').str.len()
    
    print("\nTopics per paper statistics:")
    print(topics_per_paper.describe().to_string())
    
    print("\nDistribution of number of topics:")
    topic_dist = topics_per_paper.value_counts().sort_index()
    for num_topics, count in topic_dist.items():
        print(f"  {num_topics} topics: {count:,} papers")
    
    # Flatten all topics
    all_topics_list = []
    for topics_str in df['all_topics'].dropna():
        all_topics_list.extend(topics_str.split('|'))
    
    from collections import Counter
    topic_counter = Counter(all_topics_list)
    
    print("\n\nTop 20 topics (across all positions):")
    for i, (topic, count) in enumerate(topic_counter.most_common(20), 1):
        print(f"   {i:2}. {topic:<60}: {count:,}")
    
    if sdl_total > 0:
        sdl_topics = df[df['SDL'] == 1]['all_topics'].str.split('|').str.len()
        print("\nSDL papers - topics per paper:")
        print(f"  Mean: {sdl_topics.mean():.2f}")
        print(f"  Median: {sdl_topics.median():.0f}")
        print(f"  Max: {sdl_topics.max():.0f}")
    
    # ========================================================================
    # 11. TRANSFORMED VARIABLES
    # ========================================================================
    
    print_section("11. TRANSFORMED VARIABLES")
    
    print("\nTransformed variable statistics:\n")
    
    transform_cols = [
        'asinh_first_author_papers',
        'asinh_first_author_citations',
        'asinh_last_author_papers',
        'asinh_last_author_citations',
        'asinh_corresponding_papers',
        'asinh_corresponding_citations',
        'asinh_paper_citations',
        'log_author_count'
    ]
    
    for col in transform_cols:
        if col in df.columns:
            stats = df[col].describe()
            missing = df[col].isnull().sum()
            print(f"{col}:")
            print(f"  Mean: {stats['mean']:.4f}, Std: {stats['std']:.4f}")
            print(f"  Min: {stats['min']:.4f}, Max: {stats['max']:.4f}")
            print(f"  Missing: {missing}\n")
    
    # ========================================================================
    # 12. DATA QUALITY CHECKS
    # ========================================================================
    
    print_section("12. DATA QUALITY CHECKS & ANOMALIES")
    
    print("\nANOMALY CHECKS:\n")
    
    # 1. Papers with ≤0 authors
    zero_authors = (df['author_count'] <= 0).sum()
    print(f"1. Papers with ≤0 authors: {zero_authors}")
    
    # 2. Papers with missing author metrics
    print(f"\n2. Papers with missing author metrics:")
    first_zero = (df['first_author_papers'] == 0).sum()
    last_zero = (df['last_author_papers'] == 0).sum()
    corr_zero = (df['corresponding_author_papers'] == 0).sum()
    print(f"   First author papers = 0: {first_zero:,}")
    print(f"   Last author papers = 0: {last_zero:,}")
    print(f"   Corresponding author papers = 0: {corr_zero:,}")
    
    # 3. Papers with >100 authors
    huge_teams = (df['author_count'] > 100).sum()
    print(f"\n3. Papers with >100 authors: {huge_teams}")
    
    # 4. SDL papers where neither first nor last has SDL experience
    if sdl_total > 0:
        sdl_no_exp = ((df['SDL'] == 1) & 
                      (df['first_author_sdl_experience'] == 0) & 
                      (df['last_author_sdl_experience'] == 0)).sum()
        print(f"\n4. SDL papers where NEITHER first nor last author has SDL experience: {sdl_no_exp} ({safe_percentage(sdl_no_exp, sdl_total):.1f}%)")
    
    # 5. Papers with 0 affiliations
    zero_aff = (df['num_paper_affiliations'] == 0).sum()
    print(f"\n5. Papers with 0 affiliations: {zero_aff:,} ({safe_percentage(zero_aff, len(df)):.2f}%)")
    
    # 6. Papers with 0 citations
    zero_cites = (df['cited_by_count'] == 0).sum()
    print(f"\n6. Papers with 0 citations: {zero_cites:,} ({safe_percentage(zero_cites, len(df)):.2f}%)")
    print(f"   (This is normal for recent papers)")
    
    # ========================================================================
    # 13. SDL PAPER DEEP DIVE
    # ========================================================================
    
    print_section("13. SDL PAPER DEEP DIVE")
    
    sdl_papers = df[df['SDL'] == 1]
    
    print(f"\nTotal SDL papers: {len(sdl_papers)}")
    
    print("\nSDL papers by field:")
    for field in df['field'].unique():
        count = (sdl_papers['field'] == field).sum()
        print(f"  {field:<20}: {count}")
    
    print("\nSDL papers by year:")
    sdl_by_year = sdl_papers['publication_year'].value_counts().sort_index()
    for year, count in sdl_by_year.items():
        print(f"  {year}: {count}")
    
    if len(sdl_papers) > 0:
        print("\nSDL paper characteristics:")
        print(f"  Avg team size: {sdl_papers['author_count'].mean():.2f} (vs {df[df['SDL']==0]['author_count'].mean():.2f} non-SDL)")
        print(f"  Avg affiliations: {sdl_papers['num_paper_affiliations'].mean():.2f} (vs {df[df['SDL']==0]['num_paper_affiliations'].mean():.2f} non-SDL)")
        print(f"  Avg citations: {sdl_papers['cited_by_count'].mean():.2f} (vs {df[df['SDL']==0]['cited_by_count'].mean():.2f} non-SDL)")
        
        print("\nSDL first author experience (cumulative to pub year):")
        print(f"  Avg first author papers: {sdl_papers['first_author_papers'].mean():.2f} (vs {df[df['SDL']==0]['first_author_papers'].mean():.2f} non-SDL)")
        print(f"  Avg first author citations: {sdl_papers['first_author_citations'].mean():.2f} (vs {df[df['SDL']==0]['first_author_citations'].mean():.2f} non-SDL)")
        print(f"  Avg first author SDL exp: {sdl_papers['first_author_sdl_experience'].mean():.2f}")
        
        sdl_with_cs_count = (sdl_papers['comp_sci_experience_paper'] == 1).sum()
        print("\nSDL and CS experience:")
        print(f"  SDL papers with CS experience: {sdl_with_cs_count} ({safe_percentage(sdl_with_cs_count, len(sdl_papers)):.2f}%)")
        
        print("\nTop 10 SDL paper topics:")
        sdl_topic_counts = sdl_papers['primary_topic'].value_counts().head(10)
        for i, (topic, count) in enumerate(sdl_topic_counts.items(), 1):
            print(f"   {i:2}. {topic}: {count}")
    
    # ========================================================================
    # 14. CORRELATION WITH TEAM SIZE
    # ========================================================================
    
    print_section("14. CORRELATION WITH TEAM SIZE")
    
    corr_cols = [
        'num_paper_affiliations',
        'comp_sci_experience_paper',
        'AI_Paper',
        'cited_by_count',
        'last_author_citations',
        'Robotics_Paper',
        'last_author_papers',
        'first_author_papers',
        'SDL',
        'first_author_citations'
    ]
    
    print("\nCorrelation with author_count (team size):")
    correlations = []
    for col in corr_cols:
        if col in df.columns:
            corr = df[['author_count', col]].corr().iloc[0, 1]
            correlations.append((col, corr))
    
    correlations.sort(key=lambda x: abs(x[1]), reverse=True)
    
    for col, corr in correlations:
        print(f"  {col:<30}:  {corr:7.4f}")
    
    # ========================================================================
    # 15. MATCHED SAMPLE CHARACTERISTICS
    # ========================================================================
    
    print_section("15. MATCHED SAMPLE CHARACTERISTICS")
    
    print("\nThis sample uses a 'matched venue' design:")
    print("  - Papers published in journals where SDL papers appear")
    print("  - Papers with topics matching SDL paper topics")
    print("  - Author metrics are CUMULATIVE to publication year (temporally accurate)")
    print("  - Provides apples-to-apples comparison of SDL vs non-SDL\n")
    
    print(f"Sample size: {len(df):,}")
    print(f"  SDL papers: {sdl_total:,}")
    print(f"  Non-SDL papers: {len(df) - sdl_total:,}")
    print(f"  SDL ratio: {safe_percentage(sdl_total, len(df)):.2f}%")
    
    print("\nComparison to full dataset:")
    print("  This sample represents papers in venues relevant to SDL research")
    print("  Controls for journal prestige and research topic by construction")
    print("  Enables causal inference about SDL effect on team size")
    print("  Uses temporally accurate author metrics (not anachronistic career totals)")
    
    # ========================================================================
    # END
    # ========================================================================
    
    print(f"\n{SEPARATOR}")
    print("END OF REPORT")
    print(SEPARATOR)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    
    if not REGRESSION_FILE.exists():
        print(f"ERROR: Regression file not found: {REGRESSION_FILE}")
        sys.exit(1)
    
    print(f"Loading data from: {REGRESSION_FILE}")
    
    try:
        df = pd.read_csv(REGRESSION_FILE, low_memory=False)
        print(f"Loaded {len(df):,} rows")
        print(f"Generating EDA report...")
        
        # Redirect output to file
        original_stdout = sys.stdout
        
        with open(OUTPUT_FILE, 'w') as f:
            sys.stdout = f
            generate_yearly_regression_eda(df)
        
        # Restore stdout
        sys.stdout = original_stdout
        
        print(f"\n✅ EDA report saved to: {OUTPUT_FILE}")
        
        # Print file size
        file_size = OUTPUT_FILE.stat().st_size / 1024
        print(f"   File size: {file_size:.1f} KB")
        
    except Exception as e:
        sys.stdout = original_stdout  # Restore stdout in case of error
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)