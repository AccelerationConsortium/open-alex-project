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

# AUTHOR_METRICS_FILE = PROJECT_DIR / "data" / "yearly_data/test" / "author_metrics_yearly.csv"
# CS_KEYWORDS_FILE = PROJECT_DIR / "data/lasso_regression" / "cs_keywords_shortlisted.txt"  # Computer science keywords file

# # --- SDL FILTER CONFIGURATION ---
# SDL_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_journals.txt"
# SDL_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_primary_topics.txt"

# FILTER_CONFIG = {
#     'use_journal_filter': True,
#     'use_topic_filter': True,
# }
# # -----------------------------------------------------------

# OUTPUT_DIR = PROJECT_DIR / "data" / "yearly_data/test"
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# YEARS = range(2012, 2026)
# CHUNK_SIZE = 500000

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




"""
Build regression dataset from field TSV files with 3-YEAR BACKWARD-LOOKING author metrics
- Uses author_metrics_3yr_rolling.csv (author-year metrics)
- Merges on BOTH author_id AND year
- All author metrics are now time-varying (3-year backward window)
- Separated SDL metrics (Brown, Tomet)
- High automation papers
- SDL Filtered Tom classification
- SDL VENUE FILTERING: Brown + Tomet combined journals and topics
- Multiprocessing with progress tracking
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from multiprocessing import Pool
import time

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

FIELDS = {
    'chemistry': PROJECT_DIR / "data/fields" / "chemistry",
    'materials_science': PROJECT_DIR / "data/fields" / "materials_science",
    'engineering': PROJECT_DIR / "data/fields" / "engineering",
    'computer_science': PROJECT_DIR / "data/fields" / "computer_science"
}

# CRITICAL CHANGE: Now using 3-year rolling author metrics
AUTHOR_METRICS_FILE = PROJECT_DIR / "data" / "yearly_data/test" / "author_metrics_3yr_rolling.csv"

CS_KEYWORDS_FILE = PROJECT_DIR / "data/lasso_regression" / "cs_keywords_shortlisted.txt"
SDL_KEYWORDS_FILE = PROJECT_DIR / "data" / "keywords" / "sdl_Keywords.csv"

# SDL VENUE FILTERING FILES
SDL_BROWN_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "brown_journals.csv"
SDL_TOMET_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "tom_journals.csv"
SDL_BROWN_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "brown_primary_topics.csv"
SDL_TOMET_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "tom_primary_topics.csv"

OUTPUT_DIR = PROJECT_DIR / "data" / "yearly_data/test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "regression_dataset_3yr_rolling.csv"

YEARS = range(2004, 2026)  # 2004-2025
CHUNK_SIZE = 50000
NUM_CORES = 10

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_keywords(file_path):
    """Load keywords from text or CSV file"""
    keywords = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if file_path.suffix == '.csv':
                        line = line.replace('"', '').replace("'", "")
                    keywords.add(line.lower())
    except Exception as e:
        print(f"Warning: Could not load keywords from {file_path}: {e}")
    return keywords


def load_sdl_venues(brown_journals_file, tomet_journals_file, brown_topics_file, tomet_topics_file):
    """Load SDL journals and topics from 4 separate CSV files, return union"""
    brown_journals = set()
    tomet_journals = set()
    brown_topics = set()
    tomet_topics = set()
    
    try:
        df = pd.read_csv(brown_journals_file, header=None)
        brown_journals = {str(val).strip() for val in df[0].dropna() if str(val).strip()}
        print(f"  Loaded {len(brown_journals)} Brown journals")
    except Exception as e:
        print(f"  Warning: Could not load Brown journals: {e}")
    
    try:
        df = pd.read_csv(tomet_journals_file, header=None, sep='\t', on_bad_lines='skip')
        tomet_journals = {str(val).strip() for val in df[0].dropna() if str(val).strip()}
        print(f"  Loaded {len(tomet_journals)} Tomet journals")
    except Exception as e:
        print(f"  Warning: Could not load Tomet journals: {e}")
    
    try:
        df = pd.read_csv(brown_topics_file, header=None)
        brown_topics = {str(val).strip() for val in df[0].dropna() if str(val).strip()}
        print(f"  Loaded {len(brown_topics)} Brown topics")
    except Exception as e:
        print(f"  Warning: Could not load Brown topics: {e}")
    
    try:
        df = pd.read_csv(tomet_topics_file, header=None)
        tomet_topics = {str(val).strip() for val in df[0].dropna() if str(val).strip()}
        print(f"  Loaded {len(tomet_topics)} Tomet topics")
    except Exception as e:
        print(f"  Warning: Could not load Tomet topics: {e}")
    
    all_journals = brown_journals | tomet_journals
    all_topics = brown_topics | tomet_topics
    
    print(f"\n  Combined (deduplicated):")
    print(f"    Total journals: {len(all_journals)} (Brown: {len(brown_journals)}, Tomet: {len(tomet_journals)}, Overlap: {len(brown_journals & tomet_journals)})")
    print(f"    Total topics: {len(all_topics)} (Brown: {len(brown_topics)}, Tomet: {len(tomet_topics)}, Overlap: {len(brown_topics & tomet_topics)})")
    
    return all_journals, all_topics


def count_keyword_matches(primary_topic, all_topics_str, title, abstract, keywords_set):
    """Count how many unique keywords appear in the paper metadata"""
    if not keywords_set: return 0
    matched_keywords = set()
    
    if primary_topic:
        primary_lower = primary_topic.lower()
        for keyword in keywords_set:
            if keyword in primary_lower: 
                matched_keywords.add(keyword)
    
    if all_topics_str:
        all_topics_lower = all_topics_str.lower()
        for keyword in keywords_set:
            if keyword in all_topics_lower: 
                matched_keywords.add(keyword)
    
    if title and isinstance(title, str):
        title_lower = title.lower()
        for keyword in keywords_set:
            if keyword in title_lower: 
                matched_keywords.add(keyword)
    
    if abstract and isinstance(abstract, str):
        abstract_lower = abstract.lower()
        for keyword in keywords_set:
            if keyword in abstract_lower: 
                matched_keywords.add(keyword)
    
    return len(matched_keywords)


def classify_sdl_filtered_tom(title, abstract, sdl_brown, sdl_tomet):
    """Classify paper using SDL Filtered Tom definition (only for SDL papers)"""
    if sdl_brown == 0 and sdl_tomet == 0:
        return 0
    
    if pd.isna(title): title = ""
    if pd.isna(abstract): abstract = ""
    
    title_lower = title.lower()
    abstract_lower = abstract.lower()
    
    # Category 1: Bayesian Optimization
    bayes = 0
    if "bayes" in title_lower or "bayes" in abstract_lower:
        if "optim" in title_lower or "optim" in abstract_lower:
            bayes = 1
    
    # Category 2: Closed-loop
    closedloop = 0
    closed_terms = ["closed-loop", "closed loop", "closedloop"]
    for term in closed_terms:
        if term in title_lower or term in abstract_lower:
            closedloop = 1
            break
    
    # Category 3: Process optimization
    proopt = 0
    if "process opt" in title_lower or "process opt" in abstract_lower:
        proopt = 1
    
    # Category 4: Autonomous condition optimization
    autocond = 0
    if ("auton" in title_lower and "optim" in title_lower) or \
       ("auton" in abstract_lower and "optim" in abstract_lower):
        autocond = 1
    
    # Category 5: Self-optimizing
    selfopt = 0
    selfopt_terms = ["self-opt", "self opt"]
    for term in selfopt_terms:
        if term in title_lower or term in abstract_lower:
            selfopt = 1
            break
    
    # Category 6: Self-driving
    selfdriv = 0
    selfdriv_simple = [
        "self-driv", "self driv",
        "autonomous experimentation",
        "automated exper",
        "autonomous chemi",
        "automated chemi",
        "autonomous lab",
        "automated lab",
        "autonomous synth",
        "automated synth",
        "acceleration materials platform",
        "acceleration platform",
        "high-throughput"
    ]
    
    for term in selfdriv_simple:
        if term in title_lower or term in abstract_lower:
            selfdriv = 1
            break
    
    if not selfdriv:
        if ("autonomous disc" in title_lower and "discov" in abstract_lower) or \
           ("autonomous disc" in abstract_lower and "discov" in abstract_lower):
            selfdriv = 1
        elif ("automated disc" in title_lower and "discov" in abstract_lower) or \
             ("automated disc" in abstract_lower and "discov" in abstract_lower):
            selfdriv = 1
    
    if not selfdriv:
        if (("accelerated" in title_lower or "accelerated" in abstract_lower) and 
            ("autonomous" in title_lower or "autonomous" in abstract_lower)):
            selfdriv = 1
        elif (("accelerated" in title_lower or "accelerated" in abstract_lower) and 
              ("automated" in title_lower or "automated" in abstract_lower)):
            selfdriv = 1
        elif (("experiment" in title_lower or "experiment" in abstract_lower) and 
              ("robot" in title_lower or "robot" in abstract_lower) and 
              ("platform" in title_lower or "platform" in abstract_lower)):
            selfdriv = 1
    
    sdl_filtered_tom = 1 if (bayes or closedloop or proopt or autocond or selfopt or selfdriv) else 0
    
    return sdl_filtered_tom


def clean_author_id(author_id):
    """Remove URL prefix from author ID"""
    if pd.isna(author_id) or author_id == '': return None
    return str(author_id).replace('https://openalex.org/', '')


def parse_authorships(raw_data_json):
    """Extract first and last author IDs"""
    if pd.isna(raw_data_json) or raw_data_json == '': return None, None
    try:
        data = json.loads(raw_data_json)
        authorships = data.get('authorships', [])
        if not authorships: return None, None
        
        first_author_id = clean_author_id(authorships[0].get('author', {}).get('id'))
        last_author_id = clean_author_id(authorships[-1].get('author', {}).get('id'))
        return first_author_id, last_author_id
    except: return None, None


def parse_paper_metadata(raw_data_json):
    """Extract paper metadata including abstract"""
    if pd.isna(raw_data_json) or raw_data_json == '': 
        return None, None, None, 0, 0, None, None
        
    try:
        data = json.loads(raw_data_json)
        
        topics = data.get('topics', [])
        primary_topic = topics[0].get('display_name') if topics else None
        all_topics = [t.get('display_name') for t in topics if t.get('display_name')]
        all_topics_str = '|'.join(all_topics) if all_topics else None
        
        journal = data.get('primary_location', {}).get('source', {}).get('display_name')
        cited_by_count = data.get('cited_by_count', 0) or 0
        publication_date = data.get('publication_date')
        
        abstract_text = None
        abstract_inverted = data.get('abstract_inverted_index')
        if abstract_inverted:
            word_positions = []
            for word, positions in abstract_inverted.items():
                for pos in positions: 
                    word_positions.append((pos, word))
            word_positions.sort(key=lambda x: x[0])
            abstract_text = ' '.join([word for pos, word in word_positions])
        
        authorships = data.get('authorships', [])
        all_institutions = set()
        for authorship in authorships:
            for inst in authorship.get('institutions', []):
                inst_id = inst.get('id')
                if inst_id: all_institutions.add(inst_id)
        num_paper_affiliations = len(all_institutions)
        
        return primary_topic, all_topics_str, journal, cited_by_count, num_paper_affiliations, publication_date, abstract_text
        
    except: 
        return None, None, None, 0, 0, None, None


# ============================================================================
# PARALLEL PROCESSING FUNCTION
# ============================================================================

def process_field_year(args):
    """Process a single (field, year) combination"""
    field_name, field_dir, year, cs_keywords, sdl_keywords = args
    
    # Locate file
    possible_files = [
        field_dir / f"{field_name}_{year}_sdl_classified.tsv",
        field_dir / f"{field_name}_{year}.tsv",
    ]
    tsv_file = next((f for f in possible_files if f.exists()), None)
    
    if not tsv_file: 
        return field_name, year, [], 0, 0, "FILE_NOT_FOUND"
    
    papers = []
    total = 0
    skipped = 0
    
    try:
        use_cols = ['article_id', 'doi', 'title', 'publication_year', 'author_count', 
                    'brown_SDL_papers', 'tomet_al_SDL', 'high_automation_dummy',
                    'AI_Paper', 'Robotics_Paper', 'raw_data']
        
        header = pd.read_csv(tsv_file, sep='\t', nrows=0).columns.tolist()
        use_cols = [col for col in use_cols if col in header]
        
        if 'raw_data' not in use_cols:
            return field_name, year, [], 0, 0, "NO_RAW_DATA"
        
        for chunk in pd.read_csv(tsv_file, sep='\t', usecols=use_cols,
                                chunksize=CHUNK_SIZE, low_memory=False, 
                                on_bad_lines='skip'):
            
            for _, row in chunk.iterrows():
                try:
                    # Parse authorships
                    first_author_id, last_author_id = parse_authorships(row['raw_data'])
                    if not first_author_id or not last_author_id:
                        skipped += 1
                        continue
                    
                    # Parse metadata
                    primary_topic, all_topics_str, journal, cited_by_count, num_affiliations, publication_date, abstract = \
                        parse_paper_metadata(row['raw_data'])
                    
                    title = row.get('title', '')
                    
                    # SDL Classifications
                    sdl_brown = row.get('brown_SDL_papers', 0)
                    if pd.isna(sdl_brown): sdl_brown = 0
                    
                    sdl_tomet = row.get('tomet_al_SDL', 0)
                    if pd.isna(sdl_tomet): sdl_tomet = 0
                    
                    high_auto = row.get('high_automation_dummy', 0)
                    if pd.isna(high_auto): high_auto = 0
                    
                    # CS Experience Classification
                    comp_sci_experience_paper = 0
                    if field_name == 'computer_science':
                        comp_sci_experience_paper = 1
                    else:
                        matches = count_keyword_matches(primary_topic, all_topics_str, 
                                                       title, abstract, cs_keywords)
                        comp_sci_experience_paper = 1 if matches >= 2 else 0
                    
                    # SDL Keyword Classification
                    matches_sdl = count_keyword_matches(primary_topic, all_topics_str, 
                                                        title, abstract, sdl_keywords)
                    sdl_keyword_measure = 1 if matches_sdl >= 1 else 0
                    number_of_SDL_words = matches_sdl
                    
                    # SDL Filtered Tom Classification
                    sdl_filtered_tom = classify_sdl_filtered_tom(title, abstract, sdl_brown, sdl_tomet)
                    
                    # Create paper record (WITHOUT author metrics - will merge later)
                    paper_record = {
                        'article_id': row['article_id'],
                        'doi': row.get('doi', ''),
                        'title': title,
                        'publication_year': row['publication_year'],
                        'publication_date': publication_date or '',
                        'author_count': row['author_count'],
                        
                        # SDL Classifications
                        'SDL_Brown': sdl_brown,
                        'SDL_Tomet': sdl_tomet,
                        'high_automation': high_auto,
                        'sdl_keyword_measure': sdl_keyword_measure,
                        'number_of_SDL_words': number_of_SDL_words,
                        'SDL_Filtered_Tom': sdl_filtered_tom,
                        
                        'AI_Paper': row.get('AI_Paper', 0),
                        'Robotics_Paper': row.get('Robotics_Paper', 0),
                        
                        'num_paper_affiliations': num_affiliations,
                        'primary_topic': primary_topic or 'MISSING',
                        'all_topics': all_topics_str or '',
                        'journal': journal or 'MISSING',
                        'cited_by_count': cited_by_count,
                        'field': field_name,
                        'abstract': abstract or '',
                        'comp_sci_experience_paper': comp_sci_experience_paper,
                        
                        # Author IDs (for merging)
                        'first_author_id': first_author_id,
                        'last_author_id': last_author_id,
                    }
                    
                    papers.append(paper_record)
                    total += 1
                    
                except Exception as e:
                    skipped += 1
                    continue
                    
    except Exception as e:
        return field_name, year, [], 0, 0, f"ERROR: {str(e)}"
    
    return field_name, year, papers, total, skipped, f"SUCCESS"


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def build_regression_dataset():
    """Build regression dataset with 3-year backward-looking author metrics"""
    
    print("\n" + "="*80)
    print("BUILDING REGRESSION DATASET (3-YEAR BACKWARD-LOOKING)")
    print("FILTERING: Journal in (Brown OR Tomet) AND Topic in (Brown OR Tomet)")
    print("="*80)
    print(f"Output: {OUTPUT_FILE}")
    print(f"Years: {YEARS[0]}-{YEARS[-1]}")
    print(f"Fields: {len(FIELDS)}")
    print(f"CPU cores: {NUM_CORES}")
    print("="*80 + "\n")
    
    # Verify files
    print("Verifying required files...")
    
    if not AUTHOR_METRICS_FILE.exists():
        print(f"  ✗ ERROR: 3-year author metrics not found")
        print(f"    {AUTHOR_METRICS_FILE}")
        sys.exit(1)
    print(f"  ✓ 3-year author metrics: {AUTHOR_METRICS_FILE}")
    
    if not CS_KEYWORDS_FILE.exists():
        print(f"  ✗ ERROR: CS keywords not found")
        sys.exit(1)
    print(f"  ✓ CS keywords: {CS_KEYWORDS_FILE}")
    
    if not SDL_KEYWORDS_FILE.exists():
        print(f"  ✗ ERROR: SDL keywords not found")
        sys.exit(1)
    print(f"  ✓ SDL keywords: {SDL_KEYWORDS_FILE}")
    
    # Verify SDL venue files
    for file_path in [SDL_BROWN_JOURNALS_FILE, SDL_TOMET_JOURNALS_FILE, 
                      SDL_BROWN_TOPICS_FILE, SDL_TOMET_TOPICS_FILE]:
        if not file_path.exists():
            print(f"  ✗ ERROR: File not found: {file_path}")
            sys.exit(1)
    
    print(f"  ✓ All SDL venue files found")
    
    # Load keywords and venues
    print("\nLoading keywords and venues...")
    cs_keywords = load_keywords(CS_KEYWORDS_FILE)
    sdl_keywords = load_keywords(SDL_KEYWORDS_FILE)
    print(f"  CS keywords: {len(cs_keywords)}")
    print(f"  SDL keywords: {len(sdl_keywords)}")
    
    sdl_journals, sdl_topics = load_sdl_venues(
        SDL_BROWN_JOURNALS_FILE, 
        SDL_TOMET_JOURNALS_FILE,
        SDL_BROWN_TOPICS_FILE,
        SDL_TOMET_TOPICS_FILE
    )
    
    # Build task list
    print(f"\n{'='*80}")
    print("Building task list...")
    
    tasks = []
    for field_name, field_dir in FIELDS.items():
        if not field_dir.exists():
            print(f"  ✗ {field_name}: directory not found")
            continue
        print(f"  ✓ {field_name}")
        for year in YEARS:
            tasks.append((field_name, field_dir, year, cs_keywords, sdl_keywords))
    
    print(f"\n  Total tasks: {len(tasks)}")
    
    # Process in parallel
    print(f"\n{'='*80}")
    print(f"PROCESSING {len(tasks)} FILES IN PARALLEL")
    print(f"{'='*80}\n")
    
    start_time = time.time()
    
    with Pool(NUM_CORES) as pool:
        results = pool.map(process_field_year, tasks)
    
    # Track results
    successful = 0
    failed = 0
    not_found = 0
    
    print("\nProcessing complete. Results:")
    for field_name, year, papers, total, skipped, status in results:
        if status == "SUCCESS":
            successful += 1
            if successful % 10 == 0:
                print(f"  ✓ {field_name}_{year}: {total:,} papers ({skipped:,} skipped)")
        elif status == "FILE_NOT_FOUND":
            not_found += 1
        else:
            failed += 1
            print(f"  ✗ {field_name}_{year}: {status}")
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*80}")
    print(f"PHASE 1 COMPLETE - {elapsed:.1f}s")
    print(f"{'='*80}")
    print(f"  Successful: {successful}")
    print(f"  Not Found: {not_found}")
    print(f"  Failed: {failed}")
    print(f"{'='*80}\n")
    
    # Combine results
    print(f"{'='*80}")
    print("COMBINING RESULTS")
    print(f"{'='*80}\n")
    
    all_papers = []
    total_papers = 0
    total_skipped = 0
    
    for field_name, year, papers, total, skipped, status in results:
        all_papers.extend(papers)
        total_papers += total
        total_skipped += skipped
    
    print(f"TOTAL BEFORE MERGING: {total_papers:,} papers ({total_skipped:,} skipped)\n")
    
    # Create DataFrame
    print(f"{'='*80}")
    print("CREATING DATAFRAME")
    print(f"{'='*80}\n")
    
    df = pd.DataFrame(all_papers)
    print(f"  DataFrame shape (before filtering): {df.shape}")
    
    # ========================================================================
    # CRITICAL: MERGE WITH 3-YEAR AUTHOR METRICS
    # ========================================================================
    print(f"\n{'='*80}")
    print("MERGING WITH 3-YEAR ROLLING AUTHOR METRICS")
    print(f"{'='*80}\n")

    print(f"  Loading 3-year author metrics...")
    author_df = pd.read_csv(AUTHOR_METRICS_FILE, low_memory=False)
    print(f"  Author-year records: {len(author_df):,}")
    print(f"  Unique authors: {author_df['author_id'].nunique():,}")

    # ========================================================================
    # MERGE FIRST AUTHOR METRICS
    # ========================================================================
    print(f"\n  Merging first author metrics...")

    # Select only needed columns for first author
    first_author_metrics_cols = [
        'author_id', 'year',
        'total_papers_3yr', 'total_citations_3yr',
        'sdl_brown_papers_3yr', 'sdl_tomet_papers_3yr',
        'top_field_3yr', 'top_topic_3yr', 'top_journal_3yr',
        'num_unique_fields_3yr', 'num_unique_topics_3yr', 'num_unique_journals_3yr'
    ]

    # Filter to only existing columns
    first_author_metrics_cols = [col for col in first_author_metrics_cols if col in author_df.columns]

    first_author_df = author_df[first_author_metrics_cols].copy()

    # Rename before merge to avoid conflicts
    first_author_rename = {
        'author_id': 'first_author_id_merge',
        'year': 'year_merge',
        'total_papers_3yr': 'first_author_papers_3yr',
        'total_citations_3yr': 'first_author_citations_3yr',
        'sdl_brown_papers_3yr': 'first_author_sdl_brown_experience_3yr',
        'sdl_tomet_papers_3yr': 'first_author_sdl_tomet_experience_3yr',
        'top_field_3yr': 'first_author_field_3yr',
        'top_topic_3yr': 'first_author_top_topic_3yr',
        'top_journal_3yr': 'first_author_top_journal_3yr',
        'num_unique_fields_3yr': 'first_author_unique_fields_count_3yr',
        'num_unique_topics_3yr': 'first_author_unique_topics_count_3yr',
        'num_unique_journals_3yr': 'first_author_unique_journals_count_3yr',
    }

    first_author_df = first_author_df.rename(columns=first_author_rename)

    # Merge
    df = df.merge(
        first_author_df,
        left_on=['first_author_id', 'publication_year'],
        right_on=['first_author_id_merge', 'year_merge'],
        how='left'
    )

    # Drop merge keys
    df = df.drop(columns=['first_author_id_merge', 'year_merge'], errors='ignore')

    print(f"  ✓ First author merge complete")
    print(f"  DataFrame shape: {df.shape}")

    # ========================================================================
    # MERGE LAST AUTHOR METRICS
    # ========================================================================
    print(f"\n  Merging last author metrics...")

    # Select only needed columns for last author
    last_author_metrics_cols = [
        'author_id', 'year',
        'total_papers_3yr', 'total_citations_3yr',
        'sdl_brown_papers_3yr', 'sdl_tomet_papers_3yr',
        'top_field_3yr', 'top_topic_3yr', 'top_journal_3yr',
        'num_unique_fields_3yr', 'num_unique_topics_3yr', 'num_unique_journals_3yr',
        'has_cs_experience_3yr',
        'avg_team_size_3yr', 'avg_team_size_last_author_3yr',
        'avg_team_size_sdl_brown_3yr', 'avg_team_size_sdl_tomet_3yr',
        'avg_team_size_high_automation_3yr',
        'author_profile_3yr', 'field_counts_3yr',
        'num_prior_years_available'
    ]

    # Filter to only existing columns
    last_author_metrics_cols = [col for col in last_author_metrics_cols if col in author_df.columns]

    last_author_df = author_df[last_author_metrics_cols].copy()

    # Rename before merge to avoid conflicts
    last_author_rename = {
        'author_id': 'last_author_id_merge',
        'year': 'year_merge',
        'total_papers_3yr': 'last_author_papers_3yr',
        'total_citations_3yr': 'last_author_citations_3yr',
        'sdl_brown_papers_3yr': 'last_author_sdl_brown_experience_3yr',
        'sdl_tomet_papers_3yr': 'last_author_sdl_tomet_experience_3yr',
        'top_field_3yr': 'last_author_field_3yr',
        'top_topic_3yr': 'last_author_top_topic_3yr',
        'top_journal_3yr': 'last_author_top_journal_3yr',
        'num_unique_fields_3yr': 'last_author_unique_fields_count_3yr',
        'num_unique_topics_3yr': 'last_author_unique_topics_count_3yr',
        'num_unique_journals_3yr': 'last_author_unique_journals_count_3yr',
        'has_cs_experience_3yr': 'last_author_has_cs_exp_3yr',
        'avg_team_size_3yr': 'last_author_avg_team_size_overall_3yr',
        'avg_team_size_last_author_3yr': 'last_author_avg_team_size_managerial_3yr',
        'avg_team_size_sdl_brown_3yr': 'last_author_avg_team_size_sdl_brown_3yr',
        'avg_team_size_sdl_tomet_3yr': 'last_author_avg_team_size_sdl_tomet_3yr',
        'avg_team_size_high_automation_3yr': 'last_author_avg_team_size_high_automation_3yr',
        'author_profile_3yr': 'last_author_profile_3yr',
        'field_counts_3yr': 'last_author_field_counts_3yr',
        'num_prior_years_available': 'last_author_num_prior_years_available',
    }

    last_author_df = last_author_df.rename(columns=last_author_rename)

    # Merge
    df = df.merge(
        last_author_df,
        left_on=['last_author_id', 'publication_year'],
        right_on=['last_author_id_merge', 'year_merge'],
        how='left'
    )

    # Drop merge keys
    df = df.drop(columns=['last_author_id_merge', 'year_merge'], errors='ignore')

    print(f"  ✓ Last author merge complete")
    print(f"  DataFrame shape: {df.shape}")

    # ========================================================================
    # SDL VENUE FILTERING
    # ========================================================================
    print(f"\n{'='*80}")
    print("APPLYING SDL VENUE FILTERING")
    print(f"{'='*80}\n")

    print(f"  Before filtering: {len(df):,} papers")

    mask = df['journal'].isin(sdl_journals) & df['primary_topic'].isin(sdl_topics)
    df = df[mask].copy()
    print(f"  After venue filtering: {len(df):,} papers")

    # Remove rows with missing key variables
    key_vars = ['author_count', 'publication_year', 'field', 
                'first_author_papers_3yr', 'last_author_papers_3yr']

    pre_dropna = len(df)
    df = df.dropna(subset=key_vars)
    print(f"  Removed {pre_dropna - len(df):,} with missing key variables")
    print(f"  FINAL after filtering: {len(df):,} papers\n")

    # Apply transformations
    print("  Applying transformations...")

    # Check if columns exist before transforming
    if 'first_author_papers_3yr' in df.columns:
        df['asinh_first_author_papers_3yr'] = np.arcsinh(df['first_author_papers_3yr'].astype(float))
    if 'first_author_citations_3yr' in df.columns:
        df['asinh_first_author_citations_3yr'] = np.arcsinh(df['first_author_citations_3yr'].astype(float))
    if 'last_author_papers_3yr' in df.columns:
        df['asinh_last_author_papers_3yr'] = np.arcsinh(df['last_author_papers_3yr'].astype(float))
    if 'last_author_citations_3yr' in df.columns:
        df['asinh_last_author_citations_3yr'] = np.arcsinh(df['last_author_citations_3yr'].astype(float))

    df['asinh_paper_citations'] = np.arcsinh(df['cited_by_count'].astype(float))
    df['log_author_count'] = np.log(df['author_count'].astype(float).replace(0, np.nan))

    print("  ✓ Transformations complete\n")
    
    # Save
    print(f"{'='*80}")
    print("SAVING DATASET")
    print(f"{'='*80}\n")
    
    print(f"  Saving to: {OUTPUT_FILE}")
    df.to_csv(OUTPUT_FILE, index=False)
    
    file_size = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"  ✓ Saved: {file_size:.1f} MB")
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")
    
    print(f"Total papers (filtered): {len(df):,}")
    print(f"\nSDL Classifications:")
    print(f"  SDL Brown: {df['SDL_Brown'].sum():,}")
    print(f"  SDL Tomet: {df['SDL_Tomet'].sum():,}")
    print(f"  SDL Keyword: {df['sdl_keyword_measure'].sum():,}")
    print(f"  SDL Filtered Tom: {df['SDL_Filtered_Tom'].sum():,}")
    print(f"  High Automation: {df['high_automation'].sum():,}")
    
    print(f"\nOther Classifications:")
    print(f"  AI Papers: {df['AI_Paper'].sum():,}")
    print(f"  Robotics Papers: {df['Robotics_Paper'].sum():,}")
    print(f"  CS Experience Papers: {df['comp_sci_experience_paper'].sum():,}")
    
    with_abstract = df['abstract'].notna().sum()
    print(f"\nPapers with abstracts: {with_abstract:,} ({with_abstract/len(df)*100:.1f}%)")
    
    print(f"\nPapers by field:")
    print(df['field'].value_counts().to_string())
    
    print(f"\nPrior years availability (last author):")
    if 'last_author_num_prior_years_available' in df.columns:
        print(df['last_author_num_prior_years_available'].value_counts().sort_index().to_string())
    
    total_elapsed = time.time() - start_time
    print(f"\n{'='*80}")
    print(f"COMPLETE - Total Time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"{'='*80}\n")
    
    return df


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    df = build_regression_dataset()

