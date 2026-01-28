"""
Code to build regression dataset for SDL analysis.
For each paper across all fields and years, extracts author information, paper metadata, and treatment variables.
Computes CS experience for papers based on topic matching with CS keywords.
Creates transformed variables (asinh, log) for use in regression analysis.
"""

# import pandas as pd,json, numpy as np
# from pathlib import Path
# import sys

# batch_size = 50000
# years = range(2012, 2026)

# fields = {
#     'chemistry': 'data/fields/chemistry',
#     'materials_science': 'data/fields/material_science', 
#     'engineering': 'data/fields/engineering',
#     'computer_science': 'data/fields/computer_science'
# }

# author_metrics_file = 'data/author/author_metrics.csv'
# cs_topics = 'data/cs_topics_only.txt'
# output_dir = 'data/regression'

# def load_cs_keywords(file_path):
#     """Load CS keywords from text file into a set for fast lookup."""
#     with open(file_path, 'r', encoding='utf-8') as f:
#         keywords = set(line.strip().lower() for line in f if line.strip())
#     return keywords


# def check_cs_topic_match(primary_topic, all_topics_str, cs_keywords_set):
#     """Check if primary topic or any topic in all_topics matches CS keywords."""
#     # Check primary topic
#     if primary_topic and primary_topic.lower().strip() in cs_keywords_set:
#         return 1
    
#     # Check all topics
#     if all_topics_str:
#         topics = [t.strip().lower() for t in all_topics_str.split('|')]
#         for topic in topics:
#             if topic in cs_keywords_set:
#                 return 1
    
#     return 0


# def clean_author_id(author_id):
#     """Remove URL prefix from author ID for lookup."""
#     if pd.isna(author_id) or author_id == '':
#         return None
#     return str(author_id).replace('https://openalex.org/', '')


# def parse_authorships(raw_data_json):
#     """Extract first and last author IDs from raw_data."""
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
#     """Extract corresponding author IDs and select primary one."""
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
#     """Extract topics (primary + all), journal, citations, affiliations count, publication date."""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return None, None, None, 0, 0, None
    
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
        
#         # Count unique affiliations
#         authorships = data.get('authorships', [])
#         all_institutions = set()
#         for authorship in authorships:
#             for inst in authorship.get('institutions', []):
#                 inst_id = inst.get('id')
#                 if inst_id:
#                     all_institutions.add(inst_id)
        
#         num_paper_affiliations = len(all_institutions)
        
#         return primary_topic, all_topics_str, journal, cited_by_count, num_paper_affiliations, publication_date
    
#     except:
#         return None, None, None, 0, 0, None


# def get_corresponding_position(first_id, last_id, corr_id, corr_ids_list):
#     """Determine position of corresponding author."""
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


# def build_regression_dataset(years):
#     """Function will build complete regression dataset from paper TSVs.
    
#     Variables:
#         years: years to extract"""
    
#     print("Building regression dataset")
    
#     # Load author metrics
#     print("Loading author metrics")
#     author_df = pd.read_csv(author_metrics_file)
#     author_df = author_df.set_index('author_id')
#     print(f"  Loaded {len(author_df):,} authors")
    
#     # Load CS keywords
#     print("Loading CS keywords")
#     cs_keywords = load_cs_keywords(cs_topics)
#     print(f"  Loaded {len(cs_keywords):,} CS keywords")
    
#     all_papers = []
#     total_papers = 0
#     total_skipped = 0
    
#     # Process each field
#     for field, location in fields.items():
#         print(f"\nProcessing {field}")
        
#         field_papers = 0
#         field_skipped = 0
        
#         # Process each year
#         for year in years:
#             f = f"{location}/{field}_{year}.tsv"
            
#             year_papers = 0
#             year_skipped = 0
            
#             try:
#                 # Read in chunks
#                 for chunk in pd.read_csv(
#                     f, 
#                     sep='\t',
#                     usecols=['article_id', 'doi', 'title', 'publication_year', 'author_count', 
#                              'SDL', 'AI_Paper', 'Robotics_Paper', 'raw_data'],
#                     chunksize=batch_size,
#                     low_memory=False,
#                     on_bad_lines='skip'
#                 ):
                    
#                     for i in chunk.index:
                        
#                         try:
#                             # Parse authorships
#                             first_author_id, last_author_id = parse_authorships(chunk.at[i, 'raw_data'])
                            
#                             if not first_author_id or not last_author_id:
#                                 year_skipped += 1
#                                 continue
                            
#                             # Parse corresponding authors
#                             primary_corr_id, all_corr_ids = parse_corresponding_authors(chunk.at[i, 'raw_data'])
                            
#                             # Parse paper metadata
#                             primary_topic, all_topics_str, journal, cited_by_count, num_affiliations, publication_date = \
#                                 parse_paper_metadata(chunk.at[i, 'raw_data'])
                            
#                             # Determine CS experience for paper
#                             if field == 'computer_science':
#                                 comp_sci_experience_paper = 1
#                             else:
#                                 comp_sci_experience_paper = check_cs_topic_match(
#                                     primary_topic, all_topics_str, cs_keywords
#                                 )
                            
#                             # Get first author metrics
#                             if first_author_id in author_df.index:
#                                 first_author = author_df.loc[first_author_id]
#                                 first_papers = first_author['total_papers']
#                                 first_citations = first_author['total_citations']
#                                 first_sdl_exp = first_author['sdl_papers']
#                                 first_field = first_author['top_field']
#                             else:
#                                 first_papers = 0
#                                 first_citations = 0
#                                 first_sdl_exp = 0
#                                 first_field = ''
                            
#                             # Get last author metrics
#                             if last_author_id in author_df.index:
#                                 last_author = author_df.loc[last_author_id]
#                                 last_papers = last_author['total_papers']
#                                 last_citations = last_author['total_citations']
#                                 last_sdl_exp = last_author['sdl_papers']
#                                 last_field = last_author['top_field']
#                             else:
#                                 last_papers = 0
#                                 last_citations = 0
#                                 last_sdl_exp = 0
#                                 last_field = ''
                            
#                             # Get corresponding author metrics
#                             if primary_corr_id and primary_corr_id in author_df.index:
#                                 corr_author = author_df.loc[primary_corr_id]
#                                 corr_papers = corr_author['total_papers']
#                                 corr_citations = corr_author['total_citations']
#                                 corr_sdl_exp = corr_author['sdl_papers']
#                             else:
#                                 corr_papers = 0
#                                 corr_citations = 0
#                                 corr_sdl_exp = 0
                            
#                             # Determine corresponding position
#                             corr_position = get_corresponding_position(
#                                 first_author_id, last_author_id, primary_corr_id, all_corr_ids
#                             )
                            
#                             # Check if first/last is corresponding
#                             first_is_corr = 1 if first_author_id in all_corr_ids else 0
#                             last_is_corr = 1 if last_author_id in all_corr_ids else 0
                            
#                             # Create paper record
#                             paper_record = {
#                                 'article_id': chunk.at[i, 'article_id'],
#                                 'doi': chunk.at[i, 'doi'] if pd.notna(chunk.at[i, 'doi']) else '',
#                                 'title': chunk.at[i, 'title'] if pd.notna(chunk.at[i, 'title']) else '',
#                                 'publication_year': chunk.at[i, 'publication_year'],
#                                 'publication_date': publication_date or '',
#                                 'author_count': chunk.at[i, 'author_count'],
#                                 'SDL': chunk.at[i, 'SDL'],
#                                 'AI_Paper': chunk.at[i, 'AI_Paper'] if pd.notna(chunk.at[i, 'AI_Paper']) else 0,
#                                 'Robotics_Paper': chunk.at[i, 'Robotics_Paper'] if pd.notna(chunk.at[i, 'Robotics_Paper']) else 0,
#                                 'num_paper_affiliations': num_affiliations,
#                                 'primary_topic': primary_topic or 'MISSING',
#                                 'all_topics': all_topics_str or '',
#                                 'journal': journal or 'MISSING',
#                                 'cited_by_count': cited_by_count,
#                                 'field': field,
#                                 'comp_sci_experience_paper': comp_sci_experience_paper,
#                                 'first_author_id': first_author_id,
#                                 'first_author_papers': first_papers,
#                                 'first_author_citations': first_citations,
#                                 'first_author_sdl_experience': first_sdl_exp,
#                                 'first_author_is_corresponding': first_is_corr,
#                                 'first_author_field': first_field,
#                                 'last_author_id': last_author_id,
#                                 'last_author_papers': last_papers,
#                                 'last_author_citations': last_citations,
#                                 'last_author_sdl_experience': last_sdl_exp,
#                                 'last_author_is_corresponding': last_is_corr,
#                                 'last_author_field': last_field,
#                                 'corresponding_author_id': primary_corr_id or '',
#                                 'corresponding_author_papers': corr_papers,
#                                 'corresponding_author_citations': corr_citations,
#                                 'corresponding_author_sdl_experience': corr_sdl_exp,
#                                 'corresponding_position': corr_position,
#                                 'num_corresponding_authors': len(all_corr_ids)
#                             }
                            
#                             all_papers.append(paper_record)
#                             year_papers += 1
                            
#                         except (json.JSONDecodeError, ValueError, KeyError):
#                             year_skipped += 1
#                             continue
                
#                 print(f"  Year {year}: {year_papers} papers ({year_skipped} skipped)")
#                 field_papers += year_papers
#                 field_skipped += year_skipped
            
#             except Exception as e:
#                 print(f"  Year {year}: Error - {str(e)[:100]}")
#                 continue
        
#         print(f"  Field total: {field_papers} papers ({field_skipped} skipped)")
#         total_papers += field_papers
#         total_skipped += field_skipped
    
#     print(f"\nTotal papers: {total_papers}")
#     print(f"Total skipped: {total_skipped}")
    
#     # Create DataFrame
#     print("\nCreating DataFrame")
#     df = pd.DataFrame(all_papers)
    
#     # Apply transformations
#     print("Applying transformations")
#     df['asinh_first_author_papers'] = np.arcsinh(df['first_author_papers'].astype(float))
#     df['asinh_first_author_citations'] = np.arcsinh(df['first_author_citations'].astype(float))
#     df['asinh_last_author_papers'] = np.arcsinh(df['last_author_papers'].astype(float))
#     df['asinh_last_author_citations'] = np.arcsinh(df['last_author_citations'].astype(float))
#     df['asinh_corresponding_papers'] = np.arcsinh(df['corresponding_author_papers'].astype(float))
#     df['asinh_corresponding_citations'] = np.arcsinh(df['corresponding_author_citations'].astype(float))
#     df['asinh_paper_citations'] = np.arcsinh(df['cited_by_count'].astype(float))
#     df['log_author_count'] = np.log(df['author_count'].astype(float).replace(0, np.nan))
    
#     # Save outputs
#     print("\nSaving outputs")
#     output_file = f"{output_dir}/regression_dataset_full.parquet"
#     df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
#     print(f"  Saved: {output_file}")
    
#     csv_file = f"{output_dir}/regression_dataset_full.csv"
#     df.to_csv(csv_file, index=False)
#     print(f"  Saved: {csv_file}")
    
#     # Print summary statistics
#     print(f"\nDataset dimensions: {df.shape}")
#     print(f"Papers by field:\n{df['field'].value_counts()}")
#     print(f"\nSDL papers: {df['SDL'].sum()}")
#     print(f"CS Experience papers: {df['comp_sci_experience_paper'].sum()}")
#     print(f"\nCS Experience by field:\n{df.groupby('field')['comp_sci_experience_paper'].agg(['sum', 'count', 'mean'])}")
    
#     return df


# # Calling functions from here
# if __name__ == "__main__":
#     df = build_regression_dataset(years)

#THIS IS THE DATASET WITH 490K PAPERS
# """
# Build regression dataset from paper TSV files
# Toggle between two configurations:
# - FULL: 26M papers (all 4 fields, no abstracts, no CS experience)
# - FILTERED: 490K papers (SDL venue matched, with abstracts, with CS experience)
# """
# import json
# import pandas as pd
# import numpy as np
# from pathlib import Path
# import sys
# from multiprocessing import Pool, cpu_count

# # ============================================================================
# # CONFIGURATION - TOGGLE BETWEEN FULL AND FILTERED
# # ============================================================================

# # UNCOMMENT ONE OF THE FOLLOWING:
# # DATASET_MODE = 'FULL'      # 26M papers: all fields, no filtering, no abstracts, no CS exp
# DATASET_MODE = 'FILTERED'  # 490K papers: SDL venue matched, with abstracts, with CS exp

# # ============================================================================
# # PATHS
# # ============================================================================

# PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# FIELDS = {
#     'chemistry': PROJECT_DIR / "data/fields" / "chemistry",
#     'materials_science': PROJECT_DIR / "data/fields" / "material_science",
#     'engineering': PROJECT_DIR / "data/fields" / "engineering",
#     'computer_science': PROJECT_DIR / "data/fields" / "computer_science"
# }

# AUTHOR_METRICS_FILE = PROJECT_DIR / "data" / "author/test" / "author_metrics.csv"

# # For FILTERED mode only
# CS_KEYWORDS_FILE = PROJECT_DIR / "data/lasso_regression" / "cs_keywords_shortlisted.txt"
# SDL_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_journals.txt"
# SDL_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_primary_topics.txt"

# OUTPUT_DIR = PROJECT_DIR / "data" / "regression/test"
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# YEARS = range(2012, 2026)
# CHUNK_SIZE = 500000

# # ============================================================================
# # HELPER FUNCTIONS
# # ============================================================================

# def load_cs_keywords(file_path):
#     """Load CS keywords from text file, skip commented lines"""
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
    
#     return 1 if len(matched_keywords) >= 2 else 0


# def clean_author_id(author_id):
#     """Remove URL prefix from author ID"""
#     if pd.isna(author_id) or author_id == '':
#         return None
#     return str(author_id).replace('https://openalex.org/', '')


# def parse_authorships(raw_data_json):
#     """Extract first and last author IDs"""
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
        
#         cleaned_ids = [clean_author_id(aid) for aid in corr_ids if aid]
#         primary_corr = cleaned_ids[0] if cleaned_ids else None
        
#         return primary_corr, cleaned_ids
#     except:
#         return None, []


# def parse_paper_metadata(raw_data_json, include_abstract=False):
#     """Extract paper metadata (topics, journal, citations, affiliations, date, abstract)"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return None, None, None, 0, 0, None, None
    
#     try:
#         data = json.loads(raw_data_json)
        
#         # Topics
#         topics = data.get('topics', [])
#         primary_topic = topics[0].get('display_name') if topics else None
#         all_topics = [t.get('display_name') for t in topics if t.get('display_name')]
#         all_topics_str = '|'.join(all_topics) if all_topics else None
        
#         # Journal
#         journal = data.get('primary_location', {}).get('source', {}).get('display_name')
        
#         # Citations
#         cited_by_count = data.get('cited_by_count', 0) or 0
        
#         # Publication date
#         publication_date = data.get('publication_date')
        
#         # Abstract (only if requested)
#         abstract_text = None
#         if include_abstract:
#             abstract_inverted = data.get('abstract_inverted_index')
#             if abstract_inverted:
#                 word_positions = []
#                 for word, positions in abstract_inverted.items():
#                     for pos in positions:
#                         word_positions.append((pos, word))
#                 word_positions.sort(key=lambda x: x[0])
#                 abstract_text = ' '.join([word for pos, word in word_positions])
        
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
    
#     if first_id == last_id:
#         return 'only'
    
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
# # PARALLEL PROCESSING FUNCTION
# # ============================================================================

# def process_field_year(args):
#     """Process a single (field, year) combination"""
#     field_name, field_dir, year, author_metrics_path, mode, cs_keywords_path = args
    
#     tsv_file = field_dir / f"{field_name}_{year}.tsv"
    
#     if not tsv_file.exists():
#         return field_name, year, [], 0, 0
    
#     # Load author metrics
#     author_df = pd.read_csv(author_metrics_path)
#     author_df = author_df.set_index('author_id')
    
#     # Load CS keywords if in FILTERED mode
#     cs_keywords = None
#     if mode == 'FILTERED':
#         cs_keywords = load_cs_keywords(cs_keywords_path)
    
#     papers = []
#     total = 0
#     skipped = 0
    
#     # Determine whether to include abstract
#     include_abstract = (mode == 'FILTERED')
    
#     try:
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
#                     # Parse authorships
#                     first_author_id, last_author_id = parse_authorships(row['raw_data'])
                    
#                     if not first_author_id or not last_author_id:
#                         skipped += 1
#                         continue
                    
#                     # Parse corresponding authors
#                     primary_corr_id, all_corr_ids = parse_corresponding_authors(row['raw_data'])
                    
#                     # Parse paper metadata
#                     primary_topic, all_topics_str, journal, cited_by_count, num_affiliations, publication_date, abstract = \
#                         parse_paper_metadata(row['raw_data'], include_abstract=include_abstract)
                    
#                     title = row.get('title', '')
                    
#                     # CS experience (FILTERED mode only)
#                     comp_sci_experience_paper = None
#                     if mode == 'FILTERED':
#                         if field_name == 'computer_science':
#                             comp_sci_experience_paper = 1
#                         else:
#                             comp_sci_experience_paper = check_cs_keyword_match(
#                                 primary_topic, all_topics_str, title, abstract, cs_keywords
#                             )
                    
#                     # Get first author metrics
#                     if first_author_id in author_df.index:
#                         first_author = author_df.loc[first_author_id]
#                         first_papers = first_author['total_papers']
#                         first_citations = first_author['total_citations']
#                         first_sdl_exp = first_author['sdl_papers']
#                         first_field = first_author['top_field']
#                     else:
#                         first_papers = 0
#                         first_citations = 0
#                         first_sdl_exp = 0
#                         first_field = ''
                    
#                     # Get last author metrics
#                     if last_author_id in author_df.index:
#                         last_author = author_df.loc[last_author_id]
#                         last_papers = last_author['total_papers']
#                         last_citations = last_author['total_citations']
#                         last_sdl_exp = last_author['sdl_papers']
#                         last_field = last_author['top_field']
#                     else:
#                         last_papers = 0
#                         last_citations = 0
#                         last_sdl_exp = 0
#                         last_field = ''
                    
#                     # Get corresponding author metrics
#                     if primary_corr_id and primary_corr_id in author_df.index:
#                         corr_author = author_df.loc[primary_corr_id]
#                         corr_papers = corr_author['total_papers']
#                         corr_citations = corr_author['total_citations']
#                         corr_sdl_exp = corr_author['sdl_papers']
#                     else:
#                         corr_papers = 0
#                         corr_citations = 0
#                         corr_sdl_exp = 0
                    
#                     # Corresponding position
#                     corr_position = get_corresponding_position(
#                         first_author_id, last_author_id, primary_corr_id, all_corr_ids
#                     )
                    
#                     # Check if first/last is corresponding
#                     first_is_corr = 1 if first_author_id in all_corr_ids else 0
#                     last_is_corr = 1 if last_author_id in all_corr_ids else 0
                    
#                     # Create paper record
#                     paper_record = {
#                         'article_id': row['article_id'],
#                         'doi': row.get('doi', ''),
#                         'title': title,
#                         'publication_year': row['publication_year'],
#                         'publication_date': publication_date or '',
#                         'author_count': row['author_count'],
#                         'SDL': row['SDL'],
#                         'AI_Paper': row.get('AI_Paper', 0),
#                         'Robotics_Paper': row.get('Robotics_Paper', 0),
#                         'num_paper_affiliations': num_affiliations,
#                         'primary_topic': primary_topic or 'MISSING',
#                         'all_topics': all_topics_str or '',
#                         'journal': journal or 'MISSING',
#                         'cited_by_count': cited_by_count,
#                         'field': field_name,
#                         'first_author_id': first_author_id,
#                         'first_author_papers': first_papers,
#                         'first_author_citations': first_citations,
#                         'first_author_sdl_experience': first_sdl_exp,
#                         'first_author_is_corresponding': first_is_corr,
#                         'first_author_field': first_field,
#                         'last_author_id': last_author_id,
#                         'last_author_papers': last_papers,
#                         'last_author_citations': last_citations,
#                         'last_author_sdl_experience': last_sdl_exp,
#                         'last_author_is_corresponding': last_is_corr,
#                         'last_author_field': last_field,
#                         'corresponding_author_id': primary_corr_id or '',
#                         'corresponding_author_papers': corr_papers,
#                         'corresponding_author_citations': corr_citations,
#                         'corresponding_author_sdl_experience': corr_sdl_exp,
#                         'corresponding_position': corr_position,
#                         'num_corresponding_authors': len(all_corr_ids)
#                     }
                    
#                     # Add abstract and CS experience for FILTERED mode
#                     if mode == 'FILTERED':
#                         paper_record['abstract'] = abstract or ''
#                         paper_record['comp_sci_experience_paper'] = comp_sci_experience_paper
                    
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

# def build_regression_dataset():
#     """Build regression dataset based on DATASET_MODE"""
    
#     print("="*80)
#     print(f"BUILDING REGRESSION DATASET - {DATASET_MODE} MODE")
#     print("="*80)
    
#     if DATASET_MODE == 'FULL':
#         print("Configuration: 26M papers (all fields, no filtering)")
#     elif DATASET_MODE == 'FILTERED':
#         print("Configuration: 490K papers (SDL venue matched, with abstracts & CS exp)")
    
#     print(f"\nOutput directory: {OUTPUT_DIR}")
#     print(f"Years: {min(YEARS)}-{max(YEARS)-1}")
#     print(f"Fields: {len(FIELDS)}")
#     print(f"CPU cores: {cpu_count()}\n")
    
#     # ========================================================================
#     # Verify files
#     # ========================================================================
    
#     print("="*80)
#     print("Verifying required files")
#     print("="*80)
    
#     if not AUTHOR_METRICS_FILE.exists():
#         print(f"❌ ERROR: {AUTHOR_METRICS_FILE}")
#         sys.exit(1)
#     print(f"✓ {AUTHOR_METRICS_FILE}")
    
#     # For FILTERED mode, verify additional files
#     sdl_journals = set()
#     sdl_topics = set()
#     cs_keywords = None
    
#     if DATASET_MODE == 'FILTERED':
#         if not CS_KEYWORDS_FILE.exists():
#             print(f"❌ ERROR: {CS_KEYWORDS_FILE}")
#             sys.exit(1)
#         print(f"✓ {CS_KEYWORDS_FILE}")
#         cs_keywords = load_cs_keywords(CS_KEYWORDS_FILE)
#         print(f"  Loaded {len(cs_keywords)} CS keywords")
        
#         if not SDL_JOURNALS_FILE.exists():
#             print(f"❌ ERROR: {SDL_JOURNALS_FILE}")
#             sys.exit(1)
#         with open(SDL_JOURNALS_FILE, 'r') as f:
#             sdl_journals = {line.strip() for line in f if line.strip()}
#         print(f"✓ {SDL_JOURNALS_FILE} ({len(sdl_journals)} journals)")
        
#         if not SDL_TOPICS_FILE.exists():
#             print(f"❌ ERROR: {SDL_TOPICS_FILE}")
#             sys.exit(1)
#         with open(SDL_TOPICS_FILE, 'r') as f:
#             sdl_topics = {line.strip() for line in f if line.strip()}
#         print(f"✓ {SDL_TOPICS_FILE} ({len(sdl_topics)} topics)")
    
#     # ========================================================================
#     # Build task list
#     # ========================================================================
    
#     print(f"\n{'='*80}")
#     print("Building task list")
#     print("="*80)
    
#     tasks = []
#     for field_name, field_dir in FIELDS.items():
#         if not field_dir.exists():
#             print(f"  ✗ {field_name}: directory not found")
#             continue
        
#         print(f"  ✓ {field_name}")
#         for year in YEARS:
#             tasks.append((field_name, field_dir, year, AUTHOR_METRICS_FILE, DATASET_MODE, CS_KEYWORDS_FILE))
    
#     print(f"\n✓ {len(tasks)} tasks ready\n")
    
#     # ========================================================================
#     # Process in parallel
#     # ========================================================================
    
#     print("="*80)
#     print("Processing in parallel")
#     print("="*80)
    
#     num_processes = min(8, len(tasks), cpu_count())
    
#     with Pool(processes=num_processes) as pool:
#         results = pool.map(process_field_year, tasks)
    
#     # ========================================================================
#     # Combine results
#     # ========================================================================
    
#     print(f"\n{'='*80}")
#     print("Combining results")
#     print("="*80)
    
#     all_papers = []
#     total_papers = 0
#     total_skipped = 0
    
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
#     # Create DataFrame and transformations
#     # ========================================================================
    
#     print("="*80)
#     print("Creating DataFrame and transformations")
#     print("="*80)
    
#     df = pd.DataFrame(all_papers)
#     print(f"  DataFrame shape: {df.shape}")
    
#     # Apply transformations
#     print("  Applying transformations...")
#     df['asinh_first_author_papers'] = np.arcsinh(df['first_author_papers'].astype(float))
#     df['asinh_first_author_citations'] = np.arcsinh(df['first_author_citations'].astype(float))
#     df['asinh_last_author_papers'] = np.arcsinh(df['last_author_papers'].astype(float))
#     df['asinh_last_author_citations'] = np.arcsinh(df['last_author_citations'].astype(float))
#     df['asinh_corresponding_papers'] = np.arcsinh(df['corresponding_author_papers'].astype(float))
#     df['asinh_corresponding_citations'] = np.arcsinh(df['corresponding_author_citations'].astype(float))
#     df['asinh_paper_citations'] = np.arcsinh(df['cited_by_count'].astype(float))
#     df['log_author_count'] = np.log(df['author_count'].astype(float).replace(0, np.nan))
    
#     print("  ✓ Transformations complete\n")
    
#     # ========================================================================
#     # Apply filtering for FILTERED mode
#     # ========================================================================
    
#     if DATASET_MODE == 'FILTERED':
#         print(f"{'='*80}")
#         print("Applying filters")
#         print("="*80)
        
#         initial_count = len(df)
        
#         # Venue filtering
#         print(f"  Applying venue filters...")
#         mask = df['journal'].isin(sdl_journals) & df['primary_topic'].isin(sdl_topics)
#         df = df[mask].copy()
#         print(f"  After venue filtering: {len(df):,}")
        
#         # Remove missing key variables
#         key_vars = ['author_count', 'publication_year', 'field', 
#                     'asinh_first_author_papers', 'asinh_last_author_papers']
#         pre_dropna = len(df)
#         df = df.dropna(subset=key_vars)
#         print(f"  Removed {pre_dropna - len(df):,} with missing key variables")
#         print(f"  Final: {len(df):,}\n")
    
#     # ========================================================================
#     # Save
#     # ========================================================================
    
#     print(f"{'='*80}")
#     print("Saving dataset")
#     print("="*80)
    
#     if DATASET_MODE == 'FULL':
#         output_file = OUTPUT_DIR / "regression_dataset_full.csv"
#     else:
#         output_file = OUTPUT_DIR / "regression_dataset_filtered.csv"
    
#     print(f"  Saving to: {output_file}")
#     df.to_csv(output_file, index=False)
    
#     file_size = output_file.stat().st_size / (1024 * 1024)
#     print(f"  Size: {file_size:.1f} MB")
#     print(f"  Rows: {len(df):,}")
#     print(f"  Columns: {len(df.columns)}")
    
#     # ========================================================================
#     # Summary
#     # ========================================================================
    
#     print(f"\n{'='*80}")
#     print("SUMMARY")
#     print("="*80)
    
#     print(f"\nTotal papers: {len(df):,}")
#     print(f"  SDL papers: {df['SDL'].sum():,}")
#     print(f"  AI papers: {df['AI_Paper'].sum():,}")
#     print(f"  Robotics papers: {df['Robotics_Paper'].sum():,}")
    
#     if DATASET_MODE == 'FILTERED':
#         with_abstract = df['abstract'].notna().sum()
#         print(f"  Papers with abstracts: {with_abstract:,} ({with_abstract/len(df)*100:.1f}%)")
#         print(f"  CS Experience papers: {df['comp_sci_experience_paper'].sum():,}")
    
#     print(f"\nPapers by field:")
#     print(df['field'].value_counts().to_string())
    
#     print(f"\n{'='*80}")
#     print("✅ COMPLETE!")
#     print("="*80)
#     print(f"\nOutput: {output_file}\n")
    
#     return df


# # ============================================================================
# # MAIN
# # ============================================================================

# if __name__ == "__main__":
#     df = build_regression_dataset()

# import json
# import pandas as pd
# import numpy as np
# from pathlib import Path
# import sys
# from multiprocessing import Pool, cpu_count

# # ============================================================================
# # CONFIGURATION - TOGGLE BETWEEN FULL AND FILTERED
# # ============================================================================

# # UNCOMMENT ONE OF THE FOLLOWING:
# # DATASET_MODE = 'FULL'      # 26M papers: all fields, no filtering, no abstracts, no CS exp
# DATASET_MODE = 'FILTERED'  # 490K papers: SDL venue matched, with abstracts, with CS exp

# # ============================================================================
# # PATHS
# # ============================================================================

# PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# FIELDS = {
#     'chemistry': PROJECT_DIR / "data/fields" / "chemistry",
#     'materials_science': PROJECT_DIR / "data/fields" / "material_science",
#     'engineering': PROJECT_DIR / "data/fields" / "engineering",
#     'computer_science': PROJECT_DIR / "data/fields" / "computer_science"
# }

# AUTHOR_METRICS_FILE = PROJECT_DIR / "data" / "author" / "author_metrics.csv"

# # For FILTERED mode only
# CS_KEYWORDS_FILE = PROJECT_DIR / "data/lasso_regression" / "cs_keywords_shortlisted.txt"
# SDL_KEYWORDS_FILE = PROJECT_DIR / "data" / "keywords" / "sdl_Keywords.csv"  # New SDL Keywords

# SDL_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_journals.txt"
# SDL_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_primary_topics.txt"

# OUTPUT_DIR = PROJECT_DIR / "data" / "regression/test"
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# YEARS = range(2012, 2026)
# CHUNK_SIZE = 500000

# # ============================================================================
# # HELPER FUNCTIONS
# # ============================================================================

# def load_keywords(file_path):
#     """Load keywords from text or CSV file, skip commented lines"""
#     keywords = set()
#     try:
#         with open(file_path, 'r', encoding='utf-8') as f:
#             for line in f:
#                 line = line.strip()
#                 if line and not line.startswith('#'):
#                     # Handle CSV by removing quotes if present
#                     if file_path.suffix == '.csv':
#                         line = line.replace('"', '').replace("'", "")
#                     keywords.add(line.lower())
#     except Exception as e:
#         print(f"Warning: Could not load keywords from {file_path}: {e}")
#     return keywords


# def count_keyword_matches(primary_topic, all_topics_str, title, abstract, keywords_set):
#     """
#     Count how many unique keywords appear in the paper metadata.
#     Returns the count of unique matched keywords.
#     """
#     if not keywords_set:
#         return 0

#     matched_keywords = set()
    
#     # Check primary topic
#     if primary_topic:
#         primary_lower = primary_topic.lower()
#         for keyword in keywords_set:
#             if keyword in primary_lower:
#                 matched_keywords.add(keyword)
    
#     # Check all topics
#     if all_topics_str:
#         all_topics_lower = all_topics_str.lower()
#         for keyword in keywords_set:
#             if keyword in all_topics_lower:
#                 matched_keywords.add(keyword)
    
#     # Check title
#     if title and isinstance(title, str):
#         title_lower = title.lower()
#         for keyword in keywords_set:
#             if keyword in title_lower:
#                 matched_keywords.add(keyword)
    
#     # Check abstract
#     if abstract and isinstance(abstract, str):
#         abstract_lower = abstract.lower()
#         for keyword in keywords_set:
#             if keyword in abstract_lower:
#                 matched_keywords.add(keyword)
    
#     return len(matched_keywords)


# def clean_author_id(author_id):
#     """Remove URL prefix from author ID"""
#     if pd.isna(author_id) or author_id == '':
#         return None
#     return str(author_id).replace('https://openalex.org/', '')


# def parse_authorships(raw_data_json):
#     """Extract first and last author IDs"""
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
        
#         cleaned_ids = [clean_author_id(aid) for aid in corr_ids if aid]
#         primary_corr = cleaned_ids[0] if cleaned_ids else None
        
#         return primary_corr, cleaned_ids
#     except:
#         return None, []


# def parse_paper_metadata(raw_data_json, include_abstract=False):
#     """Extract paper metadata (topics, journal, citations, affiliations, date, abstract)"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return None, None, None, 0, 0, None, None
    
#     try:
#         data = json.loads(raw_data_json)
        
#         # Topics
#         topics = data.get('topics', [])
#         primary_topic = topics[0].get('display_name') if topics else None
#         all_topics = [t.get('display_name') for t in topics if t.get('display_name')]
#         all_topics_str = '|'.join(all_topics) if all_topics else None
        
#         # Journal
#         journal = data.get('primary_location', {}).get('source', {}).get('display_name')
        
#         # Citations
#         cited_by_count = data.get('cited_by_count', 0) or 0
        
#         # Publication date
#         publication_date = data.get('publication_date')
        
#         # Abstract (only if requested)
#         abstract_text = None
#         if include_abstract:
#             abstract_inverted = data.get('abstract_inverted_index')
#             if abstract_inverted:
#                 word_positions = []
#                 for word, positions in abstract_inverted.items():
#                     for pos in positions:
#                         word_positions.append((pos, word))
#                 word_positions.sort(key=lambda x: x[0])
#                 abstract_text = ' '.join([word for pos, word in word_positions])
        
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
    
#     if first_id == last_id:
#         return 'only'
    
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
# # PARALLEL PROCESSING FUNCTION
# # ============================================================================

# def process_field_year(args):
#     """Process a single (field, year) combination"""
#     field_name, field_dir, year, author_metrics_path, mode, cs_keywords_path, sdl_keywords_path = args
    
#     tsv_file = field_dir / f"{field_name}_{year}.tsv"
    
#     if not tsv_file.exists():
#         return field_name, year, [], 0, 0
    
#     # Load author metrics
#     author_df = pd.read_csv(author_metrics_path)
#     author_df = author_df.set_index('author_id')
    
#     # Load keywords if in FILTERED mode
#     cs_keywords = None
#     sdl_keywords = None
#     if mode == 'FILTERED':
#         cs_keywords = load_keywords(cs_keywords_path)
#         sdl_keywords = load_keywords(sdl_keywords_path)
    
#     papers = []
#     total = 0
#     skipped = 0
    
#     # Determine whether to include abstract
#     include_abstract = (mode == 'FILTERED')
    
#     try:
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
#                     # Parse authorships
#                     first_author_id, last_author_id = parse_authorships(row['raw_data'])
                    
#                     if not first_author_id or not last_author_id:
#                         skipped += 1
#                         continue
                    
#                     # Parse corresponding authors
#                     primary_corr_id, all_corr_ids = parse_corresponding_authors(row['raw_data'])
                    
#                     # Parse paper metadata
#                     primary_topic, all_topics_str, journal, cited_by_count, num_affiliations, publication_date, abstract = \
#                         parse_paper_metadata(row['raw_data'], include_abstract=include_abstract)
                    
#                     title = row.get('title', '')
                    
#                     # --------------------------------------------------------
#                     # KEYWORD ANALYSES (FILTERED mode only)
#                     # --------------------------------------------------------
#                     comp_sci_experience_paper = 0
#                     sdl_keyword_paper = 0
#                     number_of_sdl_words = 0
                    
#                     if mode == 'FILTERED':
#                         # 1. CS Experience
#                         # Logic: Field is CS OR >= 2 keywords matched
#                         if field_name == 'computer_science':
#                             comp_sci_experience_paper = 1
#                         else:
#                             matches = count_keyword_matches(
#                                 primary_topic, all_topics_str, title, abstract, cs_keywords
#                             )
#                             comp_sci_experience_paper = 1 if matches >= 2 else 0

#                         # 2. SDL Keyword Measure
#                         # Logic: >= 1 keyword matched (phrases are specific enough)
#                         matches_sdl = count_keyword_matches(
#                             primary_topic, all_topics_str, title, abstract, sdl_keywords
#                         )
#                         number_of_sdl_words = matches_sdl
#                         sdl_keyword_paper = 1 if matches_sdl >= 1 else 0

#                     # --------------------------------------------------------
#                     # AUTHOR METRICS
#                     # --------------------------------------------------------
#                     # --- FIRST AUTHOR METRICS ---
#                     if first_author_id in author_df.index:
#                         first_author = author_df.loc[first_author_id]
#                         # Existing variables
#                         first_papers = first_author['total_papers']
#                         first_citations = first_author['total_citations']
#                         first_sdl_exp = first_author['sdl_papers']
#                         first_field = first_author['top_field']
                        
#                         # New variables
#                         first_top_topic = first_author['top_topic']
#                         first_top_journal = first_author['top_journal']
#                         first_unique_fields = first_author['num_unique_fields']
#                         first_unique_topics = first_author['num_unique_topics']
#                         first_unique_journals = first_author['num_unique_journals']
#                     else:
#                         first_papers = 0
#                         first_citations = 0
#                         first_sdl_exp = 0
#                         first_field = ''
#                         first_top_topic = ''
#                         first_top_journal = ''
#                         first_unique_fields = 0
#                         first_unique_topics = 0
#                         first_unique_journals = 0
                    
#                     # --- LAST AUTHOR METRICS ---
#                     if last_author_id in author_df.index:
#                         last_author = author_df.loc[last_author_id]
#                         # Existing variables
#                         last_papers = last_author['total_papers']
#                         last_citations = last_author['total_citations']
#                         last_sdl_exp = last_author['sdl_papers']
#                         last_field = last_author['top_field']
                        
#                         # New variables
#                         last_top_topic = last_author['top_topic']
#                         last_top_journal = last_author['top_journal']
#                         last_unique_fields = last_author['num_unique_fields']
#                         last_unique_topics = last_author['num_unique_topics']
#                         last_unique_journals = last_author['num_unique_journals']
#                     else:
#                         last_papers = 0
#                         last_citations = 0
#                         last_sdl_exp = 0
#                         last_field = ''
#                         last_top_topic = ''
#                         last_top_journal = ''
#                         last_unique_fields = 0
#                         last_unique_topics = 0
#                         last_unique_journals = 0
                    
#                     # Get corresponding author metrics
#                     if primary_corr_id and primary_corr_id in author_df.index:
#                         corr_author = author_df.loc[primary_corr_id]
#                         corr_papers = corr_author['total_papers']
#                         corr_citations = corr_author['total_citations']
#                         corr_sdl_exp = corr_author['sdl_papers']
#                     else:
#                         corr_papers = 0
#                         corr_citations = 0
#                         corr_sdl_exp = 0
                    
#                     # Corresponding position
#                     corr_position = get_corresponding_position(
#                         first_author_id, last_author_id, primary_corr_id, all_corr_ids
#                     )
                    
#                     # Check if first/last is corresponding
#                     first_is_corr = 1 if first_author_id in all_corr_ids else 0
#                     last_is_corr = 1 if last_author_id in all_corr_ids else 0
                    
#                     # Create paper record
#                     paper_record = {
#                         'article_id': row['article_id'],
#                         'doi': row.get('doi', ''),
#                         'title': title,
#                         'publication_year': row['publication_year'],
#                         'publication_date': publication_date or '',
#                         'author_count': row['author_count'],
#                         'SDL': row['SDL'],
#                         'AI_Paper': row.get('AI_Paper', 0),
#                         'Robotics_Paper': row.get('Robotics_Paper', 0),
#                         'num_paper_affiliations': num_affiliations,
#                         'primary_topic': primary_topic or 'MISSING',
#                         'all_topics': all_topics_str or '',
#                         'journal': journal or 'MISSING',
#                         'cited_by_count': cited_by_count,
#                         'field': field_name,
                        
#                         # First Author
#                         'first_author_id': first_author_id,
#                         'first_author_papers': first_papers,
#                         'first_author_citations': first_citations,
#                         'first_author_sdl_experience': first_sdl_exp,
#                         'first_author_is_corresponding': first_is_corr,
#                         'first_author_field': first_field,
#                         'first_author_top_topic': first_top_topic if pd.notna(first_top_topic) else '',
#                         'first_author_top_journal': first_top_journal if pd.notna(first_top_journal) else '',
#                         'first_author_unique_fields_count': first_unique_fields,
#                         'first_author_unique_topics_count': first_unique_topics,
#                         'first_author_unique_journals_count': first_unique_journals,

#                         # Last Author
#                         'last_author_id': last_author_id,
#                         'last_author_papers': last_papers,
#                         'last_author_citations': last_citations,
#                         'last_author_sdl_experience': last_sdl_exp,
#                         'last_author_is_corresponding': last_is_corr,
#                         'last_author_field': last_field,
#                         'last_author_top_topic': last_top_topic if pd.notna(last_top_topic) else '',
#                         'last_author_top_journal': last_top_journal if pd.notna(last_top_journal) else '',
#                         'last_author_unique_fields_count': last_unique_fields,
#                         'last_author_unique_topics_count': last_unique_topics,
#                         'last_author_unique_journals_count': last_unique_journals,

#                         # Corresponding Author
#                         'corresponding_author_id': primary_corr_id or '',
#                         'corresponding_author_papers': corr_papers,
#                         'corresponding_author_citations': corr_citations,
#                         'corresponding_author_sdl_experience': corr_sdl_exp,
#                         'corresponding_position': corr_position,
#                         'num_corresponding_authors': len(all_corr_ids)
#                     }
                    
#                     # Add abstract and CS/SDL experience for FILTERED mode
#                     if mode == 'FILTERED':
#                         paper_record['abstract'] = abstract or ''
#                         paper_record['comp_sci_experience_paper'] = comp_sci_experience_paper
#                         paper_record['SDL_Keyword_Paper'] = sdl_keyword_paper
#                         paper_record['number_of_SDL_words'] = number_of_sdl_words
                    
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

# def build_regression_dataset():
#     """Build regression dataset based on DATASET_MODE"""
    
#     print("="*80)
#     print(f"BUILDING REGRESSION DATASET - {DATASET_MODE} MODE")
#     print("="*80)
    
#     if DATASET_MODE == 'FULL':
#         print("Configuration: 26M papers (all fields, no filtering)")
#     elif DATASET_MODE == 'FILTERED':
#         print("Configuration: 490K papers (SDL venue matched, with abstracts & CS exp)")
    
#     print(f"\nOutput directory: {OUTPUT_DIR}")
#     print(f"Years: {min(YEARS)}-{max(YEARS)-1}")
#     print(f"Fields: {len(FIELDS)}")
#     print(f"CPU cores: {cpu_count()}\n")
    
#     # ========================================================================
#     # Verify files
#     # ========================================================================
    
#     print("="*80)
#     print("Verifying required files")
#     print("="*80)
    
#     if not AUTHOR_METRICS_FILE.exists():
#         print(f"❌ ERROR: {AUTHOR_METRICS_FILE}")
#         sys.exit(1)
#     print(f"✓ {AUTHOR_METRICS_FILE}")
    
#     # For FILTERED mode, verify additional files
#     sdl_journals = set()
#     sdl_topics = set()
#     cs_keywords = None
    
#     if DATASET_MODE == 'FILTERED':
#         # Check CS Keywords
#         if not CS_KEYWORDS_FILE.exists():
#             print(f"❌ ERROR: {CS_KEYWORDS_FILE}")
#             sys.exit(1)
#         print(f"✓ {CS_KEYWORDS_FILE}")
#         cs_keywords = load_keywords(CS_KEYWORDS_FILE)
#         print(f"  Loaded {len(cs_keywords)} CS keywords")

#         # Check SDL Keywords (NEW)
#         if not SDL_KEYWORDS_FILE.exists():
#             print(f"❌ ERROR: {SDL_KEYWORDS_FILE}")
#             sys.exit(1)
#         print(f"✓ {SDL_KEYWORDS_FILE}")
#         sdl_keywords = load_keywords(SDL_KEYWORDS_FILE)
#         print(f"  Loaded {len(sdl_keywords)} SDL keywords")
        
#         # Check SDL Journals/Topics
#         if not SDL_JOURNALS_FILE.exists():
#             print(f"❌ ERROR: {SDL_JOURNALS_FILE}")
#             sys.exit(1)
#         with open(SDL_JOURNALS_FILE, 'r') as f:
#             sdl_journals = {line.strip() for line in f if line.strip()}
#         print(f"✓ {SDL_JOURNALS_FILE} ({len(sdl_journals)} journals)")
        
#         if not SDL_TOPICS_FILE.exists():
#             print(f"❌ ERROR: {SDL_TOPICS_FILE}")
#             sys.exit(1)
#         with open(SDL_TOPICS_FILE, 'r') as f:
#             sdl_topics = {line.strip() for line in f if line.strip()}
#         print(f"✓ {SDL_TOPICS_FILE} ({len(sdl_topics)} topics)")
    
#     # ========================================================================
#     # Build task list
#     # ========================================================================
    
#     print(f"\n{'='*80}")
#     print("Building task list")
#     print("="*80)
    
#     tasks = []
#     for field_name, field_dir in FIELDS.items():
#         if not field_dir.exists():
#             print(f"  ✗ {field_name}: directory not found")
#             continue
        
#         print(f"  ✓ {field_name}")
#         for year in YEARS:
#             # Pass BOTH keyword paths now
#             tasks.append((field_name, field_dir, year, AUTHOR_METRICS_FILE, DATASET_MODE, CS_KEYWORDS_FILE, SDL_KEYWORDS_FILE))
    
#     print(f"\n✓ {len(tasks)} tasks ready\n")
    
#     # ========================================================================
#     # Process in parallel
#     # ========================================================================
    
#     print("="*80)
#     print("Processing in parallel")
#     print("="*80)
    
#     num_processes = min(8, len(tasks), cpu_count())
    
#     with Pool(processes=num_processes) as pool:
#         results = pool.map(process_field_year, tasks)
    
#     # ========================================================================
#     # Combine results
#     # ========================================================================
    
#     print(f"\n{'='*80}")
#     print("Combining results")
#     print("="*80)
    
#     all_papers = []
#     total_papers = 0
#     total_skipped = 0
    
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
#     # Create DataFrame and transformations
#     # ========================================================================
    
#     print("="*80)
#     print("Creating DataFrame and transformations")
#     print("="*80)
    
#     df = pd.DataFrame(all_papers)
#     print(f"  DataFrame shape: {df.shape}")
    
#     # Apply transformations
#     print("  Applying transformations...")
#     df['asinh_first_author_papers'] = np.arcsinh(df['first_author_papers'].astype(float))
#     df['asinh_first_author_citations'] = np.arcsinh(df['first_author_citations'].astype(float))
#     df['asinh_last_author_papers'] = np.arcsinh(df['last_author_papers'].astype(float))
#     df['asinh_last_author_citations'] = np.arcsinh(df['last_author_citations'].astype(float))
#     df['asinh_corresponding_papers'] = np.arcsinh(df['corresponding_author_papers'].astype(float))
#     df['asinh_corresponding_citations'] = np.arcsinh(df['corresponding_author_citations'].astype(float))
#     df['asinh_paper_citations'] = np.arcsinh(df['cited_by_count'].astype(float))
#     df['log_author_count'] = np.log(df['author_count'].astype(float).replace(0, np.nan))
    
#     print("  ✓ Transformations complete\n")
    
#     # ========================================================================
#     # Apply filtering for FILTERED mode
#     # ========================================================================
    
#     if DATASET_MODE == 'FILTERED':
#         print(f"{'='*80}")
#         print("Applying filters")
#         print("="*80)
        
#         initial_count = len(df)
        
#         # Venue filtering
#         print(f"  Applying venue filters...")
#         # Note: We keep papers that match venue/topic OR if they are SDL via keywords
#         # But per original logic, it seems we stick to venue/topic as the base universe
#         mask = df['journal'].isin(sdl_journals) & df['primary_topic'].isin(sdl_topics)
#         df = df[mask].copy()
#         print(f"  After venue filtering: {len(df):,}")
        
#         # Remove missing key variables
#         key_vars = ['author_count', 'publication_year', 'field', 
#                     'asinh_first_author_papers', 'asinh_last_author_papers']
#         pre_dropna = len(df)
#         df = df.dropna(subset=key_vars)
#         print(f"  Removed {pre_dropna - len(df):,} with missing key variables")
#         print(f"  Final: {len(df):,}\n")
    
#     # ========================================================================
#     # Save
#     # ========================================================================
    
#     print(f"{'='*80}")
#     print("Saving dataset")
#     print("="*80)
    
#     if DATASET_MODE == 'FULL':
#         output_file = OUTPUT_DIR / "regression_dataset_full.csv"
#     else:
#         output_file = OUTPUT_DIR / "regression_dataset_filtered.csv"
    
#     print(f"  Saving to: {output_file}")
#     df.to_csv(output_file, index=False)
    
#     file_size = output_file.stat().st_size / (1024 * 1024)
#     print(f"  Size: {file_size:.1f} MB")
#     print(f"  Rows: {len(df):,}")
#     print(f"  Columns: {len(df.columns)}")
    
#     # ========================================================================
#     # Summary
#     # ========================================================================
    
#     print(f"\n{'='*80}")
#     print("SUMMARY")
#     print("="*80)
    
#     print(f"\nTotal papers: {len(df):,}")
#     print(f"  SDL papers (Original): {df['SDL'].sum():,}")
    
#     if 'SDL_Keyword_Paper' in df.columns:
#         print(f"  SDL papers (Keyword): {df['SDL_Keyword_Paper'].sum():,}")
        
#     print(f"  AI papers: {df['AI_Paper'].sum():,}")
#     print(f"  Robotics papers: {df['Robotics_Paper'].sum():,}")
    
#     if DATASET_MODE == 'FILTERED':
#         with_abstract = df['abstract'].notna().sum()
#         print(f"  Papers with abstracts: {with_abstract:,} ({with_abstract/len(df)*100:.1f}%)")
#         print(f"  CS Experience papers: {df['comp_sci_experience_paper'].sum():,}")
    
#     print(f"\nPapers by field:")
#     print(df['field'].value_counts().to_string())
    
#     print(f"\n{'='*80}")
#     print("✅ COMPLETE!")
#     print("="*80)
#     print(f"\nOutput: {output_file}\n")
    
#     return df


# # ============================================================================
# # MAIN
# # ============================================================================

# if __name__ == "__main__":
#     df = build_regression_dataset()

# import json
# import pandas as pd
# import numpy as np
# from pathlib import Path
# import sys
# from multiprocessing import Pool, cpu_count

# # ============================================================================
# # CONFIGURATION - TOGGLE BETWEEN FULL AND FILTERED
# # ============================================================================

# # UNCOMMENT ONE OF THE FOLLOWING:
# # DATASET_MODE = 'FULL'      # 26M papers: all fields, no filtering, no abstracts, no CS exp
# DATASET_MODE = 'FILTERED'  # 490K papers: SDL venue matched, with abstracts, with CS exp

# # ============================================================================
# # PATHS
# # ============================================================================

# PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# FIELDS = {
#     'chemistry': PROJECT_DIR / "data/fields" / "chemistry",
#     'materials_science': PROJECT_DIR / "data/fields" / "material_science",
#     'engineering': PROJECT_DIR / "data/fields" / "engineering",
#     'computer_science': PROJECT_DIR / "data/fields" / "computer_science"
# }

# AUTHOR_METRICS_FILE = PROJECT_DIR / "data" / "author/test" / "author_metrics.csv"

# # For FILTERED mode only
# CS_KEYWORDS_FILE = PROJECT_DIR / "data/lasso_regression" / "cs_keywords_shortlisted.txt"
# SDL_KEYWORDS_FILE = PROJECT_DIR / "data" / "keywords" / "sdl_Keywords.csv" 

# SDL_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_journals.txt"
# SDL_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_primary_topics.txt"

# OUTPUT_DIR = PROJECT_DIR / "data" / "regression/test"
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# YEARS = range(2012, 2026)
# CHUNK_SIZE = 500000

# # ============================================================================
# # HELPER FUNCTIONS
# # ============================================================================

# def load_keywords(file_path):
#     """Load keywords from text or CSV file, skip commented lines"""
#     keywords = set()
#     try:
#         with open(file_path, 'r', encoding='utf-8') as f:
#             for line in f:
#                 line = line.strip()
#                 if line and not line.startswith('#'):
#                     # Handle CSV by removing quotes if present
#                     if file_path.suffix == '.csv':
#                         line = line.replace('"', '').replace("'", "")
#                     keywords.add(line.lower())
#     except Exception as e:
#         print(f"Warning: Could not load keywords from {file_path}: {e}")
#     return keywords


# def count_keyword_matches(primary_topic, all_topics_str, title, abstract, keywords_set):
#     """
#     Count how many unique keywords appear in the paper metadata.
#     Returns the count of unique matched keywords.
#     """
#     if not keywords_set:
#         return 0

#     matched_keywords = set()
    
#     # Check primary topic
#     if primary_topic:
#         primary_lower = primary_topic.lower()
#         for keyword in keywords_set:
#             if keyword in primary_lower:
#                 matched_keywords.add(keyword)
    
#     # Check all topics
#     if all_topics_str:
#         all_topics_lower = all_topics_str.lower()
#         for keyword in keywords_set:
#             if keyword in all_topics_lower:
#                 matched_keywords.add(keyword)
    
#     # Check title
#     if title and isinstance(title, str):
#         title_lower = title.lower()
#         for keyword in keywords_set:
#             if keyword in title_lower:
#                 matched_keywords.add(keyword)
    
#     # Check abstract
#     if abstract and isinstance(abstract, str):
#         abstract_lower = abstract.lower()
#         for keyword in keywords_set:
#             if keyword in abstract_lower:
#                 matched_keywords.add(keyword)
    
#     return len(matched_keywords)


# def clean_author_id(author_id):
#     """Remove URL prefix from author ID"""
#     if pd.isna(author_id) or author_id == '':
#         return None
#     return str(author_id).replace('https://openalex.org/', '')


# def parse_authorships(raw_data_json):
#     """Extract first and last author IDs"""
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
        
#         cleaned_ids = [clean_author_id(aid) for aid in corr_ids if aid]
#         primary_corr = cleaned_ids[0] if cleaned_ids else None
        
#         return primary_corr, cleaned_ids
#     except:
#         return None, []


# def parse_paper_metadata(raw_data_json, include_abstract=False):
#     """Extract paper metadata (topics, journal, citations, affiliations, date, abstract)"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return None, None, None, 0, 0, None, None
    
#     try:
#         data = json.loads(raw_data_json)
        
#         # Topics
#         topics = data.get('topics', [])
#         primary_topic = topics[0].get('display_name') if topics else None
#         all_topics = [t.get('display_name') for t in topics if t.get('display_name')]
#         all_topics_str = '|'.join(all_topics) if all_topics else None
        
#         # Journal
#         journal = data.get('primary_location', {}).get('source', {}).get('display_name')
        
#         # Citations
#         cited_by_count = data.get('cited_by_count', 0) or 0
        
#         # Publication date
#         publication_date = data.get('publication_date')
        
#         # Abstract (only if requested)
#         abstract_text = None
#         if include_abstract:
#             abstract_inverted = data.get('abstract_inverted_index')
#             if abstract_inverted:
#                 word_positions = []
#                 for word, positions in abstract_inverted.items():
#                     for pos in positions:
#                         word_positions.append((pos, word))
#                 word_positions.sort(key=lambda x: x[0])
#                 abstract_text = ' '.join([word for pos, word in word_positions])
        
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
    
#     if first_id == last_id:
#         return 'only'
    
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
# # PARALLEL PROCESSING FUNCTION
# # ============================================================================

# def process_field_year(args):
#     """Process a single (field, year) combination"""
#     field_name, field_dir, year, author_metrics_path, mode, cs_keywords_path, sdl_keywords_path = args
    
#     tsv_file = field_dir / f"{field_name}_{year}.tsv"
    
#     if not tsv_file.exists():
#         return field_name, year, [], 0, 0
    
#     # Load author metrics
#     author_df = pd.read_csv(author_metrics_path)
#     author_df = author_df.set_index('author_id')
    
#     # Load keywords if in FILTERED mode
#     cs_keywords = None
#     sdl_keywords = None
#     if mode == 'FILTERED':
#         cs_keywords = load_keywords(cs_keywords_path)
#         sdl_keywords = load_keywords(sdl_keywords_path)
    
#     papers = []
#     total = 0
#     skipped = 0
    
#     # Determine whether to include abstract
#     include_abstract = (mode == 'FILTERED')
    
#     try:
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
#                     # Parse authorships
#                     first_author_id, last_author_id = parse_authorships(row['raw_data'])
                    
#                     if not first_author_id or not last_author_id:
#                         skipped += 1
#                         continue
                    
#                     # Parse corresponding authors
#                     primary_corr_id, all_corr_ids = parse_corresponding_authors(row['raw_data'])
                    
#                     # Parse paper metadata
#                     primary_topic, all_topics_str, journal, cited_by_count, num_affiliations, publication_date, abstract = \
#                         parse_paper_metadata(row['raw_data'], include_abstract=include_abstract)
                    
#                     title = row.get('title', '')
                    
#                     # --------------------------------------------------------
#                     # KEYWORD ANALYSES (FILTERED mode only)
#                     # --------------------------------------------------------
#                     comp_sci_experience_paper = 0
#                     sdl_keyword_paper = 0
#                     number_of_sdl_words = 0
                    
#                     if mode == 'FILTERED':
#                         # 1. CS Experience
#                         # Logic: Field is CS OR >= 2 keywords matched
#                         if field_name == 'computer_science':
#                             comp_sci_experience_paper = 1
#                         else:
#                             matches = count_keyword_matches(
#                                 primary_topic, all_topics_str, title, abstract, cs_keywords
#                             )
#                             comp_sci_experience_paper = 1 if matches >= 2 else 0

#                         # 2. SDL Keyword Measure
#                         # Logic: >= 1 keyword matched (phrases are specific enough)
#                         matches_sdl = count_keyword_matches(
#                             primary_topic, all_topics_str, title, abstract, sdl_keywords
#                         )
#                         number_of_sdl_words = matches_sdl
#                         sdl_keyword_paper = 1 if matches_sdl >= 1 else 0

#                     # --------------------------------------------------------
#                     # AUTHOR METRICS
#                     # --------------------------------------------------------
#                     # --- FIRST AUTHOR METRICS ---
#                     if first_author_id in author_df.index:
#                         first_author = author_df.loc[first_author_id]
#                         # Existing variables
#                         first_papers = first_author['total_papers']
#                         first_citations = first_author['total_citations']
#                         first_sdl_exp = first_author['sdl_papers']
#                         first_field = first_author['top_field']
                        
#                         # New variables (Breadth metrics)
#                         first_top_topic = first_author['top_topic']
#                         first_top_journal = first_author['top_journal']
#                         first_unique_fields = first_author['num_unique_fields']
#                         first_unique_topics = first_author['num_unique_topics']
#                         first_unique_journals = first_author['num_unique_journals']
#                     else:
#                         first_papers = 0
#                         first_citations = 0
#                         first_sdl_exp = 0
#                         first_field = ''
#                         first_top_topic = ''
#                         first_top_journal = ''
#                         first_unique_fields = 0
#                         first_unique_topics = 0
#                         first_unique_journals = 0
                    
#                     # --- LAST AUTHOR METRICS ---
#                     if last_author_id in author_df.index:
#                         last_author = author_df.loc[last_author_id]
#                         # Existing variables
#                         last_papers = last_author['total_papers']
#                         last_citations = last_author['total_citations']
#                         last_sdl_exp = last_author['sdl_papers']
#                         last_field = last_author['top_field']
                        
#                         # Breadth variables
#                         last_top_topic = last_author['top_topic']
#                         last_top_journal = last_author['top_journal']
#                         last_unique_fields = last_author['num_unique_fields']
#                         last_unique_topics = last_author['num_unique_topics']
#                         last_unique_journals = last_author['num_unique_journals']
                        
#                         # --- NEW VARIABLES (ADDED V5) ---
#                         # CS Experience (Author Level)
#                         last_has_cs_exp = 1 if last_author.get('has_cs_experience', 0) == 1 else 0
                        
#                         # Team Size Metrics
#                         last_avg_team_overall = last_author.get('avg_team_size', 0)
#                         last_avg_team_managerial = last_author.get('avg_team_size_last_author', 0)
#                         last_avg_team_sdl = last_author.get('avg_team_size_sdl', 0)
                        
#                         # Profile & Field Counts
#                         last_profile = last_author.get('author_profile', 'Unknown')
#                         last_field_counts = last_author.get('field_counts', '{}')
                        
#                     else:
#                         last_papers = 0
#                         last_citations = 0
#                         last_sdl_exp = 0
#                         last_field = ''
#                         last_top_topic = ''
#                         last_top_journal = ''
#                         last_unique_fields = 0
#                         last_unique_topics = 0
#                         last_unique_journals = 0
                        
#                         # Defaults for new vars
#                         last_has_cs_exp = 0
#                         last_avg_team_overall = 0
#                         last_avg_team_managerial = 0
#                         last_avg_team_sdl = 0
#                         last_profile = 'Unknown'
#                         last_field_counts = '{}'
                    
#                     # Get corresponding author metrics
#                     if primary_corr_id and primary_corr_id in author_df.index:
#                         corr_author = author_df.loc[primary_corr_id]
#                         corr_papers = corr_author['total_papers']
#                         corr_citations = corr_author['total_citations']
#                         corr_sdl_exp = corr_author['sdl_papers']
#                     else:
#                         corr_papers = 0
#                         corr_citations = 0
#                         corr_sdl_exp = 0
                    
#                     # Corresponding position
#                     corr_position = get_corresponding_position(
#                         first_author_id, last_author_id, primary_corr_id, all_corr_ids
#                     )
                    
#                     # Check if first/last is corresponding
#                     first_is_corr = 1 if first_author_id in all_corr_ids else 0
#                     last_is_corr = 1 if last_author_id in all_corr_ids else 0
                    
#                     # Create paper record
#                     paper_record = {
#                         'article_id': row['article_id'],
#                         'doi': row.get('doi', ''),
#                         'title': title,
#                         'publication_year': row['publication_year'],
#                         'publication_date': publication_date or '',
#                         'author_count': row['author_count'],
#                         'SDL': row['SDL'],
#                         'AI_Paper': row.get('AI_Paper', 0),
#                         'Robotics_Paper': row.get('Robotics_Paper', 0),
#                         'num_paper_affiliations': num_affiliations,
#                         'primary_topic': primary_topic or 'MISSING',
#                         'all_topics': all_topics_str or '',
#                         'journal': journal or 'MISSING',
#                         'cited_by_count': cited_by_count,
#                         'field': field_name,
                        
#                         # First Author
#                         'first_author_id': first_author_id,
#                         'first_author_papers': first_papers,
#                         'first_author_citations': first_citations,
#                         'first_author_sdl_experience': first_sdl_exp,
#                         'first_author_is_corresponding': first_is_corr,
#                         'first_author_field': first_field,
#                         'first_author_top_topic': first_top_topic if pd.notna(first_top_topic) else '',
#                         'first_author_top_journal': first_top_journal if pd.notna(first_top_journal) else '',
#                         'first_author_unique_fields_count': first_unique_fields,
#                         'first_author_unique_topics_count': first_unique_topics,
#                         'first_author_unique_journals_count': first_unique_journals,

#                         # Last Author
#                         'last_author_id': last_author_id,
#                         'last_author_papers': last_papers,
#                         'last_author_citations': last_citations,
#                         'last_author_sdl_experience': last_sdl_exp,
#                         'last_author_is_corresponding': last_is_corr,
#                         'last_author_field': last_field,
#                         'last_author_top_topic': last_top_topic if pd.notna(last_top_topic) else '',
#                         'last_author_top_journal': last_top_journal if pd.notna(last_top_journal) else '',
#                         'last_author_unique_fields_count': last_unique_fields,
#                         'last_author_unique_topics_count': last_unique_topics,
#                         'last_author_unique_journals_count': last_unique_journals,
                        
#                         # NEW Last Author Variables
#                         'last_author_has_cs_exp': last_has_cs_exp,
#                         'last_author_avg_team_size_overall': last_avg_team_overall,
#                         'last_author_avg_team_size_managerial': last_avg_team_managerial,
#                         'last_author_avg_team_size_sdl': last_avg_team_sdl,
#                         'last_author_profile': last_profile,
#                         'last_author_field_counts': last_field_counts,

#                         # Corresponding Author
#                         'corresponding_author_id': primary_corr_id or '',
#                         'corresponding_author_papers': corr_papers,
#                         'corresponding_author_citations': corr_citations,
#                         'corresponding_author_sdl_experience': corr_sdl_exp,
#                         'corresponding_position': corr_position,
#                         'num_corresponding_authors': len(all_corr_ids)
#                     }
                    
#                     # Add abstract and CS/SDL experience for FILTERED mode
#                     if mode == 'FILTERED':
#                         paper_record['abstract'] = abstract or ''
#                         paper_record['comp_sci_experience_paper'] = comp_sci_experience_paper
#                         paper_record['SDL_Keyword_Paper'] = sdl_keyword_paper
#                         paper_record['number_of_SDL_words'] = number_of_sdl_words
                    
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

# def build_regression_dataset():
#     """Build regression dataset based on DATASET_MODE"""
    
#     print("="*80)
#     print(f"BUILDING REGRESSION DATASET - {DATASET_MODE} MODE")
#     print("="*80)
    
#     if DATASET_MODE == 'FULL':
#         print("Configuration: 26M papers (all fields, no filtering)")
#     elif DATASET_MODE == 'FILTERED':
#         print("Configuration: 490K papers (SDL venue matched, with abstracts & CS exp)")
    
#     print(f"\nOutput directory: {OUTPUT_DIR}")
#     print(f"Years: {min(YEARS)}-{max(YEARS)-1}")
#     print(f"Fields: {len(FIELDS)}")
#     print(f"CPU cores: {cpu_count()}\n")
    
#     # ========================================================================
#     # Verify files
#     # ========================================================================
    
#     print("="*80)
#     print("Verifying required files")
#     print("="*80)
    
#     if not AUTHOR_METRICS_FILE.exists():
#         print(f"❌ ERROR: {AUTHOR_METRICS_FILE}")
#         sys.exit(1)
#     print(f"✓ {AUTHOR_METRICS_FILE}")
    
#     # For FILTERED mode, verify additional files
#     sdl_journals = set()
#     sdl_topics = set()
#     cs_keywords = None
    
#     if DATASET_MODE == 'FILTERED':
#         # Check CS Keywords
#         if not CS_KEYWORDS_FILE.exists():
#             print(f"❌ ERROR: {CS_KEYWORDS_FILE}")
#             sys.exit(1)
#         print(f"✓ {CS_KEYWORDS_FILE}")
#         cs_keywords = load_keywords(CS_KEYWORDS_FILE)
#         print(f"  Loaded {len(cs_keywords)} CS keywords")

#         # Check SDL Keywords (NEW)
#         if not SDL_KEYWORDS_FILE.exists():
#             print(f"❌ ERROR: {SDL_KEYWORDS_FILE}")
#             sys.exit(1)
#         print(f"✓ {SDL_KEYWORDS_FILE}")
#         sdl_keywords = load_keywords(SDL_KEYWORDS_FILE)
#         print(f"  Loaded {len(sdl_keywords)} SDL keywords")
        
#         # Check SDL Journals/Topics
#         if not SDL_JOURNALS_FILE.exists():
#             print(f"❌ ERROR: {SDL_JOURNALS_FILE}")
#             sys.exit(1)
#         with open(SDL_JOURNALS_FILE, 'r') as f:
#             sdl_journals = {line.strip() for line in f if line.strip()}
#         print(f"✓ {SDL_JOURNALS_FILE} ({len(sdl_journals)} journals)")
        
#         if not SDL_TOPICS_FILE.exists():
#             print(f"❌ ERROR: {SDL_TOPICS_FILE}")
#             sys.exit(1)
#         with open(SDL_TOPICS_FILE, 'r') as f:
#             sdl_topics = {line.strip() for line in f if line.strip()}
#         print(f"✓ {SDL_TOPICS_FILE} ({len(sdl_topics)} topics)")
    
#     # ========================================================================
#     # Build task list
#     # ========================================================================
    
#     print(f"\n{'='*80}")
#     print("Building task list")
#     print("="*80)
    
#     tasks = []
#     for field_name, field_dir in FIELDS.items():
#         if not field_dir.exists():
#             print(f"  ✗ {field_name}: directory not found")
#             continue
        
#         print(f"  ✓ {field_name}")
#         for year in YEARS:
#             # Pass BOTH keyword paths now
#             tasks.append((field_name, field_dir, year, AUTHOR_METRICS_FILE, DATASET_MODE, CS_KEYWORDS_FILE, SDL_KEYWORDS_FILE))
    
#     print(f"\n✓ {len(tasks)} tasks ready\n")
    
#     # ========================================================================
#     # Process in parallel
#     # ========================================================================
    
#     print("="*80)
#     print("Processing in parallel")
#     print("="*80)
    
#     num_processes = min(8, len(tasks), cpu_count())
    
#     with Pool(processes=num_processes) as pool:
#         results = pool.map(process_field_year, tasks)
    
#     # ========================================================================
#     # Combine results
#     # ========================================================================
    
#     print(f"\n{'='*80}")
#     print("Combining results")
#     print("="*80)
    
#     all_papers = []
#     total_papers = 0
#     total_skipped = 0
    
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
#     # Create DataFrame and transformations
#     # ========================================================================
    
#     print("="*80)
#     print("Creating DataFrame and transformations")
#     print("="*80)
    
#     df = pd.DataFrame(all_papers)
#     print(f"  DataFrame shape: {df.shape}")
    
#     # Apply transformations
#     print("  Applying transformations...")
#     df['asinh_first_author_papers'] = np.arcsinh(df['first_author_papers'].astype(float))
#     df['asinh_first_author_citations'] = np.arcsinh(df['first_author_citations'].astype(float))
#     df['asinh_last_author_papers'] = np.arcsinh(df['last_author_papers'].astype(float))
#     df['asinh_last_author_citations'] = np.arcsinh(df['last_author_citations'].astype(float))
#     df['asinh_corresponding_papers'] = np.arcsinh(df['corresponding_author_papers'].astype(float))
#     df['asinh_corresponding_citations'] = np.arcsinh(df['corresponding_author_citations'].astype(float))
#     df['asinh_paper_citations'] = np.arcsinh(df['cited_by_count'].astype(float))
#     df['log_author_count'] = np.log(df['author_count'].astype(float).replace(0, np.nan))
    
#     print("  ✓ Transformations complete\n")
    
#     # ========================================================================
#     # Apply filtering for FILTERED mode
#     # ========================================================================
    
#     if DATASET_MODE == 'FILTERED':
#         print(f"{'='*80}")
#         print("Applying filters")
#         print("="*80)
        
#         initial_count = len(df)
        
#         # Venue filtering
#         print(f"  Applying venue filters...")
#         mask = df['journal'].isin(sdl_journals) & df['primary_topic'].isin(sdl_topics)
#         df = df[mask].copy()
#         print(f"  After venue filtering: {len(df):,}")
        
#         # Remove missing key variables
#         key_vars = ['author_count', 'publication_year', 'field', 
#                     'asinh_first_author_papers', 'asinh_last_author_papers']
#         pre_dropna = len(df)
#         df = df.dropna(subset=key_vars)
#         print(f"  Removed {pre_dropna - len(df):,} with missing key variables")
#         print(f"  Final: {len(df):,}\n")
    
#     # ========================================================================
#     # Save
#     # ========================================================================
    
#     print(f"{'='*80}")
#     print("Saving dataset")
#     print("="*80)
    
#     if DATASET_MODE == 'FULL':
#         output_file = OUTPUT_DIR / "regression_dataset_full.csv"
#     else:
#         output_file = OUTPUT_DIR / "regression_dataset_filtered_v21.csv"
    
#     print(f"  Saving to: {output_file}")
#     df.to_csv(output_file, index=False)
    
#     file_size = output_file.stat().st_size / (1024 * 1024)
#     print(f"  Size: {file_size:.1f} MB")
#     print(f"  Rows: {len(df):,}")
#     print(f"  Columns: {len(df.columns)}")
    
#     # ========================================================================
#     # Summary
#     # ========================================================================
    
#     print(f"\n{'='*80}")
#     print("SUMMARY")
#     print("="*80)
    
#     print(f"\nTotal papers: {len(df):,}")
#     print(f"  SDL papers (Original): {df['SDL'].sum():,}")
    
#     if 'SDL_Keyword_Paper' in df.columns:
#         print(f"  SDL papers (Keyword): {df['SDL_Keyword_Paper'].sum():,}")
        
#     print(f"  AI papers: {df['AI_Paper'].sum():,}")
#     print(f"  Robotics papers: {df['Robotics_Paper'].sum():,}")
    
#     if DATASET_MODE == 'FILTERED':
#         with_abstract = df['abstract'].notna().sum()
#         print(f"  Papers with abstracts: {with_abstract:,} ({with_abstract/len(df)*100:.1f}%)")
#         print(f"  CS Experience papers: {df['comp_sci_experience_paper'].sum():,}")
    
#     print(f"\nPapers by field:")
#     print(df['field'].value_counts().to_string())
    
#     print(f"\n{'='*80}")
#     print("✅ COMPLETE!")
#     print("="*80)
#     print(f"\nOutput: {output_file}\n")
    
#     return df


# # ============================================================================
# # MAIN
# # ============================================================================

# if __name__ == "__main__":
#     df = build_regression_dataset()

import pandas as pd
import numpy as np
import sys
import ast
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================
PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# Update this to point to your newly created dataset (e.g., filtered_v2.csv)
INPUT_FILE = Path("/project/def-kmcel/hridansh/openalex_project/data/regression/test/regression_dataset_filtered_v21.csv")
OUTPUT_FILE = PROJECT_DIR / "data/regression/test/regression_eda_report_v2.txt"

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

sys.stdout = Logger(OUTPUT_FILE)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def print_header(title):
    print("\n" + "="*80)
    print(title)
    print("="*80)

def print_dist(series, bins, labels):
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

    print("Loading data... (this may take a minute)")
    df = pd.read_csv(INPUT_FILE, low_memory=False)
    
    print("="*80)
    print("EXPLORATORY DATA ANALYSIS - REGRESSION DATASET (V5 - NEW VARS)")
    print("="*80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Source file: {INPUT_FILE}")
    print("="*80)

    # ============================================================================
    # 1. OVERVIEW
    # ============================================================================
    print_header("1. DATASET OVERVIEW")
    print(f"Total papers: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024**3:.2f} GB\n")
    
    print("Columns:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:>2}. {col}")

    # ============================================================================
    # 1B. ABSTRACT ANALYSIS
    # ============================================================================
    print_header("1B. ABSTRACT ANALYSIS")
    if 'abstract' in df.columns:
        with_abs = df['abstract'].notna().sum()
        no_abs = len(df) - with_abs
        print(f"Papers with abstracts: {with_abs:,} ({with_abs/len(df)*100:.2f}%)")
        print(f"Papers without abstracts: {no_abs:,} ({no_abs/len(df)*100:.2f}%)")
        
        abs_lens = df['abstract'].astype(str).apply(len)
        print(f"  Mean length (chars): {abs_lens.mean():.0f}")
    else:
        print("Abstract column not found.")

    # ============================================================================
    # 2. MISSING VALUES
    # ============================================================================
    print_header("2. MISSING VALUES ANALYSIS")
    missing = df.isnull().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    for col, val in missing.items():
        print(f"  {col}: {val:,} ({val/len(df)*100:.2f}%)")

    # ============================================================================
    # 3. DEPENDENT VARIABLE
    # ============================================================================
    print_header("3. DEPENDENT VARIABLE - TEAM SIZE (author_count)")
    print(df['author_count'].describe().to_string())
    
    print("\nTeam size distribution:")
    bins = [0, 1, 2, 3, 4, 9, 19, 49, 99, 99999]
    labels = ['1', '2', '3', '4', '5-9', '10-19', '20-49', '50-99', '100+']
    print_dist(df['author_count'], bins, labels)

    # ============================================================================
    # 4. TREATMENT VARIABLES
    # ============================================================================
    print_header("4. TREATMENT VARIABLES & SDL OVERLAP")
    sdl_orig = df['SDL'].sum()
    sdl_new = df['SDL_Keyword_Paper'].sum() if 'SDL_Keyword_Paper' in df.columns else 0
    
    print(f"  SDL (Original Measure):  {sdl_orig:,}")
    print(f"  SDL (New Keyword Measure): {sdl_new:,}")
    
    if 'SDL_Keyword_Paper' in df.columns:
        both = len(df[(df['SDL']==1) & (df['SDL_Keyword_Paper']==1)])
        print(f"  MATCHED in BOTH:         {both:,}")
        
        mask_union = (df['SDL'] == 1) | (df['SDL_Keyword_Paper'] == 1)
        print(f"\nAverage Team Size:")
        print(f"  SDL (Union):        {df[mask_union]['author_count'].mean():.2f}")
        print(f"  Non-SDL (Strict):   {df[~mask_union]['author_count'].mean():.2f}")

    # ============================================================================
    # 5. FIELD DISTRIBUTION
    # ============================================================================
    print_header("5. FIELD DISTRIBUTION")
    print(df['field'].value_counts().to_string())

    # ============================================================================
    # 5B. CS EXPERIENCE (PAPER LEVEL)
    # ============================================================================
    print_header("5B. CS EXPERIENCE ANALYSIS (PAPER LEVEL)")
    if 'comp_sci_experience_paper' in df.columns:
        cs_exp = df['comp_sci_experience_paper'].sum()
        print(f"Papers with CS experience: {cs_exp:,} ({cs_exp/len(df)*100:.2f}%)")
        print("\nAverage team size:")
        print(f"  With CS experience: {df[df['comp_sci_experience_paper']==1]['author_count'].mean():.2f}")
        print(f"  Without CS experience: {df[df['comp_sci_experience_paper']==0]['author_count'].mean():.2f}")

    # ============================================================================
    # 6. TEMPORAL DISTRIBUTION
    # ============================================================================
    print_header("6. TEMPORAL DISTRIBUTION")
    print(f"{'Year':<7}| {'Total':<8} | {'SDL(Orig)':<10}")
    print("-" * 30)
    for year in sorted(df['publication_year'].unique()):
        sub = df[df['publication_year'] == year]
        print(f"{year:<7}| {len(sub):<8,} | {sub['SDL'].sum():<10}")

    # ============================================================================
    # 7. AUTHOR METRICS (FIRST AUTHOR)
    # ============================================================================
    print_header("7. AUTHOR METRICS STATISTICS (FIRST AUTHOR)")
    cols = ['first_author_papers', 'first_author_citations', 'first_author_sdl_experience']
    print(df[cols].describe().to_string())

    # ============================================================================
    # 8. CORRESPONDING AUTHOR
    # ============================================================================
    print_header("8. CORRESPONDING AUTHOR POSITION")
    if 'corresponding_position' in df.columns:
        print(df['corresponding_position'].value_counts(dropna=False).to_string())

    # ============================================================================
    # 9-13. STANDARD CHECKS (Paper Controls, Topics, Transformed, SDL Deep Dive)
    # ============================================================================
    # (Abbreviated for space, assume similar logic to previous script for sections 9-13)
    print_header("9-13. STANDARD CHECKS (Summary)")
    print(f"Avg Affiliations: {df['num_paper_affiliations'].mean():.2f}")
    print(f"Top Topic: {df['primary_topic'].mode()[0]}")
    if 'SDL_Keyword_Paper' in df.columns:
        print("\nTop 5 Topics for New SDL Papers:")
        print(df[df['SDL_Keyword_Paper']==1]['primary_topic'].value_counts().head(5).to_string())

    # ============================================================================
    # 14. CORRELATIONS
    # ============================================================================
    print_header("14. CORRELATION WITH TEAM SIZE")
    print("Correlation with author_count:")
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    corrs = df[numeric_cols].corrwith(df['author_count']).sort_values(key=abs, ascending=False)
    
    # New variables to check specifically
    targets = ['num_paper_affiliations', 'comp_sci_experience_paper', 'SDL', 
               'last_author_avg_team_size_overall', 'last_author_avg_team_size_managerial',
               'last_author_unique_fields_count']
    
    for t in targets:
        if t in corrs:
            print(f"  {t:<40}: {corrs[t]:.4f}")

    # ============================================================================
    # 15. NEW: LAST AUTHOR PROFILE & CS EXPERIENCE
    # ============================================================================
    print_header("15. LAST AUTHOR PROFILE & CS EXPERIENCE (NEW)")
    
    # A. Last Author CS Experience
    if 'last_author_has_cs_exp' in df.columns:
        print("A. Last Author CS Experience (Author-Level)")
        has_cs = df['last_author_has_cs_exp'].sum()
        print(f"  Papers where Last Author has CS Exp: {has_cs:,} ({has_cs/len(df)*100:.2f}%)")
        
        if 'field' in df.columns:
            print("\n  Last Author CS Exp by Paper Field:")
            ct = pd.crosstab(df['field'], df['last_author_has_cs_exp'])
            if 1 in ct.columns:
                ct['% w/ CS Exp'] = ct[1] / (ct[0] + ct[1]) * 100
                print(ct.sort_values(by='% w/ CS Exp', ascending=False).to_string())

    # B. Last Author Profile
    if 'last_author_profile' in df.columns:
        print("\nB. Last Author Disciplinary Profile")
        print(df['last_author_profile'].value_counts().to_string())
        
        print("\n  Avg Team Size by Last Author Profile:")
        print(df.groupby('last_author_profile')['author_count'].mean().sort_values(ascending=False).to_string())

    # ============================================================================
    # 16. NEW: LAST AUTHOR TEAM SIZE HISTORY
    # ============================================================================
    print_header("16. LAST AUTHOR TEAM SIZE HISTORY (NEW)")
    
    team_vars = ['last_author_avg_team_size_overall', 
                 'last_author_avg_team_size_managerial', 
                 'last_author_avg_team_size_sdl']
    
    existing_team_vars = [v for v in team_vars if v in df.columns]
    
    if existing_team_vars:
        print("Descriptive Statistics (Historical Averages):")
        print(df[existing_team_vars].describe().to_string())
        
        # Hypothesis Check: 
        # Does historical managerial team size predict current team size?
        if 'last_author_avg_team_size_managerial' in df.columns:
            print("\n  Correlation: Historical Managerial Size vs Current Team Size")
            corr = df['last_author_avg_team_size_managerial'].corr(df['author_count'])
            print(f"  Pearson Correlation: {corr:.4f}")
            
            # Difference Analysis
            df['team_size_diff'] = df['author_count'] - df['last_author_avg_team_size_managerial']
            print("\n  Difference (Current Paper - Historical Managerial Avg):")
            print(f"  Mean Difference: {df['team_size_diff'].mean():.2f}")
            print("  (Positive = Current paper has larger team than their historical average)")

    # ============================================================================
    # 17. NEW: LAST AUTHOR BREADTH & FIELDS
    # ============================================================================
    print_header("17. LAST AUTHOR BREADTH & FIELDS (NEW)")
    
    breadth_vars = ['last_author_unique_fields_count', 
                    'last_author_unique_topics_count', 
                    'last_author_unique_journals_count']
    
    existing_breadth = [v for v in breadth_vars if v in df.columns]
    
    if existing_breadth:
        print("Breadth Statistics:")
        print(df[existing_breadth].describe().to_string())
    
    # Parsing Field Counts
    if 'last_author_field_counts' in df.columns:
        print("\nField Counts Analysis (Sample of 1000):")
        try:
            sample = df['last_author_field_counts'].dropna().head(1000).apply(ast.literal_eval)
            
            def get_top_field_share(d):
                if not d: return 0
                return max(d.values()) / sum(d.values())
                
            shares = sample.apply(get_top_field_share)
            print(f"  Avg Share of Papers in Top Field: {shares.mean()*100:.2f}%")
            print(f"  (Lower number = More multidisciplinary)")
        except Exception as e:
            print(f"  Could not parse field counts: {e}")

    print("\n" + "="*80)
    print("END OF REPORT")
    print("="*80)

if __name__ == "__main__":
    main()