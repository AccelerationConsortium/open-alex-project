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



# # NEW REGRESSION DATASET 2004 ONWARDS

# """
# Build regression dataset from field TSV files with author metrics
# - Separated SDL metrics (Brown, Tomet)
# - High automation papers
# - SDL Filtered Tom classification
# - SDL VENUE FILTERING (journals + topics)
# - No corresponding author variables
# - Multiprocessing with progress tracking
# """
# import json
# import pandas as pd
# import numpy as np
# from pathlib import Path
# import sys
# from multiprocessing import Pool
# import time

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

# AUTHOR_METRICS_FILE = PROJECT_DIR / "data" / "author/test" / "author_metrics_full.csv"

# CS_KEYWORDS_FILE = PROJECT_DIR / "data/lasso_regression" / "cs_keywords_shortlisted.txt"
# SDL_KEYWORDS_FILE = PROJECT_DIR / "data" / "keywords" / "sdl_Keywords.csv"

# # SDL VENUE FILTERING FILES (CRITICAL - MISSING IN NEW VERSION)
# SDL_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_journals.txt"
# SDL_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_primary_topics.txt"

# OUTPUT_DIR = PROJECT_DIR / "data" / "regression/test"
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# OUTPUT_FILE = OUTPUT_DIR / "regression_dataset_filtered_2004_onwards.csv"

# YEARS = range(2004, 2026)  # 2004-2025
# CHUNK_SIZE = 500000
# NUM_CORES = 8  # As requested

# # ============================================================================
# # HELPER FUNCTIONS
# # ============================================================================

# def load_keywords(file_path):
#     """Load keywords from text or CSV file"""
#     keywords = set()
#     try:
#         with open(file_path, 'r', encoding='utf-8') as f:
#             for line in f:
#                 line = line.strip()
#                 if line and not line.startswith('#'):
#                     if file_path.suffix == '.csv':
#                         line = line.replace('"', '').replace("'", "")
#                     keywords.add(line.lower())
#     except Exception as e:
#         print(f"Warning: Could not load keywords from {file_path}: {e}")
#     return keywords


# def load_sdl_venues(journals_file, topics_file):
#     """Load SDL journals and topics for filtering"""
#     journals = set()
#     topics = set()
    
#     try:
#         with open(journals_file, 'r', encoding='utf-8') as f:
#             journals = {line.strip() for line in f if line.strip()}
#         print(f"  Loaded {len(journals)} SDL journals")
#     except Exception as e:
#         print(f"  Warning: Could not load SDL journals: {e}")
    
#     try:
#         with open(topics_file, 'r', encoding='utf-8') as f:
#             topics = {line.strip() for line in f if line.strip()}
#         print(f"  Loaded {len(topics)} SDL topics")
#     except Exception as e:
#         print(f"  Warning: Could not load SDL topics: {e}")
    
#     return journals, topics


# def count_keyword_matches(primary_topic, all_topics_str, title, abstract, keywords_set):
#     """Count how many unique keywords appear in the paper metadata"""
#     if not keywords_set: return 0
#     matched_keywords = set()
    
#     if primary_topic:
#         primary_lower = primary_topic.lower()
#         for keyword in keywords_set:
#             if keyword in primary_lower: 
#                 matched_keywords.add(keyword)
    
#     if all_topics_str:
#         all_topics_lower = all_topics_str.lower()
#         for keyword in keywords_set:
#             if keyword in all_topics_lower: 
#                 matched_keywords.add(keyword)
    
#     if title and isinstance(title, str):
#         title_lower = title.lower()
#         for keyword in keywords_set:
#             if keyword in title_lower: 
#                 matched_keywords.add(keyword)
    
#     if abstract and isinstance(abstract, str):
#         abstract_lower = abstract.lower()
#         for keyword in keywords_set:
#             if keyword in abstract_lower: 
#                 matched_keywords.add(keyword)
    
#     return len(matched_keywords)


# def classify_sdl_filtered_tom(title, abstract):
#     """
#     Classify paper using SDL Filtered Tom definition
#     Returns 1 if paper matches ANY of the 6 category criteria
#     """
#     if pd.isna(title): title = ""
#     if pd.isna(abstract): abstract = ""
    
#     title_lower = title.lower()
#     abstract_lower = abstract.lower()
    
#     # Category 1: Bayesian Optimization
#     bayes = 0
#     if "bayes" in title_lower or "bayes" in abstract_lower:
#         if "optim" in title_lower or "optim" in abstract_lower:
#             bayes = 1
    
#     # Category 2: Closed-loop
#     closedloop = 0
#     closed_terms = ["closed-loop", "closed loop", "closedloop"]
#     for term in closed_terms:
#         if term in title_lower or term in abstract_lower:
#             closedloop = 1
#             break
    
#     # Category 3: Process optimization
#     proopt = 0
#     if "process opt" in title_lower or "process opt" in abstract_lower:
#         proopt = 1
    
#     # Category 4: Autonomous condition optimization
#     autocond = 0
#     if ("auton" in title_lower and "optim" in title_lower) or \
#        ("auton" in abstract_lower and "optim" in abstract_lower):
#         autocond = 1
    
#     # Category 5: Self-optimizing
#     selfopt = 0
#     selfopt_terms = ["self-opt", "self opt"]
#     for term in selfopt_terms:
#         if term in title_lower or term in abstract_lower:
#             selfopt = 1
#             break
    
#     # Category 6: Self-driving (comprehensive)
#     selfdriv = 0
    
#     selfdriv_simple = [
#         "self-driv", "self driv",
#         "autonomous experimentation",
#         "automated exper",
#         "autonomous chemi",
#         "automated chemi",
#         "autonomous lab",
#         "automated lab",
#         "autonomous synth",
#         "automated synth",
#         "acceleration materials platform",
#         "acceleration platform",
#         "high-throughput"
#     ]
    
#     for term in selfdriv_simple:
#         if term in title_lower or term in abstract_lower:
#             selfdriv = 1
#             break
    
#     if not selfdriv:
#         if ("autonomous disc" in title_lower and "discov" in abstract_lower) or \
#            ("autonomous disc" in abstract_lower and "discov" in abstract_lower):
#             selfdriv = 1
#         elif ("automated disc" in title_lower and "discov" in abstract_lower) or \
#              ("automated disc" in abstract_lower and "discov" in abstract_lower):
#             selfdriv = 1
    
#     if not selfdriv:
#         if (("accelerated" in title_lower or "accelerated" in abstract_lower) and 
#             ("autonomous" in title_lower or "autonomous" in abstract_lower)):
#             selfdriv = 1
#         elif (("accelerated" in title_lower or "accelerated" in abstract_lower) and 
#               ("automated" in title_lower or "automated" in abstract_lower)):
#             selfdriv = 1
#         elif (("experiment" in title_lower or "experiment" in abstract_lower) and 
#               ("robot" in title_lower or "robot" in abstract_lower) and 
#               ("platform" in title_lower or "platform" in abstract_lower)):
#             selfdriv = 1
    
#     sdl_filtered_tom = 1 if (bayes or closedloop or proopt or autocond or selfopt or selfdriv) else 0
    
#     return sdl_filtered_tom


# def clean_author_id(author_id):
#     """Remove URL prefix from author ID"""
#     if pd.isna(author_id) or author_id == '': return None
#     return str(author_id).replace('https://openalex.org/', '')


# def parse_authorships(raw_data_json):
#     """Extract first and last author IDs"""
#     if pd.isna(raw_data_json) or raw_data_json == '': return None, None
#     try:
#         data = json.loads(raw_data_json)
#         authorships = data.get('authorships', [])
#         if not authorships: return None, None
        
#         first_author_id = clean_author_id(authorships[0].get('author', {}).get('id'))
#         last_author_id = clean_author_id(authorships[-1].get('author', {}).get('id'))
#         return first_author_id, last_author_id
#     except: return None, None


# def parse_paper_metadata(raw_data_json):
#     """Extract paper metadata including abstract"""
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
        
#         # Abstract (reconstruct from inverted index)
#         abstract_text = None
#         abstract_inverted = data.get('abstract_inverted_index')
#         if abstract_inverted:
#             word_positions = []
#             for word, positions in abstract_inverted.items():
#                 for pos in positions: 
#                     word_positions.append((pos, word))
#             word_positions.sort(key=lambda x: x[0])
#             abstract_text = ' '.join([word for pos, word in word_positions])
        
#         # Affiliations
#         authorships = data.get('authorships', [])
#         all_institutions = set()
#         for authorship in authorships:
#             for inst in authorship.get('institutions', []):
#                 inst_id = inst.get('id')
#                 if inst_id: all_institutions.add(inst_id)
#         num_paper_affiliations = len(all_institutions)
        
#         return primary_topic, all_topics_str, journal, cited_by_count, num_paper_affiliations, publication_date, abstract_text
        
#     except: 
#         return None, None, None, 0, 0, None, None


# # ============================================================================
# # PARALLEL PROCESSING FUNCTION
# # ============================================================================

# def process_field_year(args):
#     """Process a single (field, year) combination"""
#     field_name, field_dir, year, author_metrics_path, cs_keywords, sdl_keywords = args
    
#     # Locate file
#     possible_files = [
#         field_dir / f"{field_name}_{year}_sdl_classified.tsv",
#         field_dir / f"{field_name}_{year}.tsv",
#     ]
#     tsv_file = next((f for f in possible_files if f.exists()), None)
    
#     if not tsv_file: 
#         return field_name, year, [], 0, 0, "FILE_NOT_FOUND"
    
#     # Load author metrics
#     author_df = pd.read_csv(author_metrics_path).set_index('author_id')
    
#     papers = []
#     total = 0
#     skipped = 0
    
#     try:
#         # Columns to read
#         use_cols = ['article_id', 'doi', 'title', 'publication_year', 'author_count', 
#                     'brown_SDL_papers', 'tomet_al_SDL', 'high_automation_dummy',
#                     'AI_Paper', 'Robotics_Paper', 'raw_data']
        
#         # Check which columns exist
#         header = pd.read_csv(tsv_file, sep='\t', nrows=0).columns.tolist()
#         use_cols = [col for col in use_cols if col in header]
        
#         if 'raw_data' not in use_cols:
#             return field_name, year, [], 0, 0, "NO_RAW_DATA"
        
#         for chunk in pd.read_csv(tsv_file, sep='\t', usecols=use_cols,
#                                 chunksize=CHUNK_SIZE, low_memory=False, 
#                                 on_bad_lines='skip'):
            
#             for _, row in chunk.iterrows():
#                 try:
#                     # Parse authorships
#                     first_author_id, last_author_id = parse_authorships(row['raw_data'])
#                     if not first_author_id or not last_author_id:
#                         skipped += 1
#                         continue
                    
#                     # Parse metadata
#                     primary_topic, all_topics_str, journal, cited_by_count, num_affiliations, publication_date, abstract = \
#                         parse_paper_metadata(row['raw_data'])
                    
#                     title = row.get('title', '')
                    
#                     # SDL Classifications
#                     sdl_brown = row.get('brown_SDL_papers', 0)
#                     if pd.isna(sdl_brown): sdl_brown = 0
                    
#                     sdl_tomet = row.get('tomet_al_SDL', 0)
#                     if pd.isna(sdl_tomet): sdl_tomet = 0
                    
#                     high_auto = row.get('high_automation_dummy', 0)
#                     if pd.isna(high_auto): high_auto = 0
                    
#                     # CS Experience Classification
#                     comp_sci_experience_paper = 0
#                     if field_name == 'computer_science':
#                         comp_sci_experience_paper = 1
#                     else:
#                         matches = count_keyword_matches(primary_topic, all_topics_str, 
#                                                        title, abstract, cs_keywords)
#                         comp_sci_experience_paper = 1 if matches >= 2 else 0
                    
#                     # SDL Keyword Classification
#                     matches_sdl = count_keyword_matches(primary_topic, all_topics_str, 
#                                                         title, abstract, sdl_keywords)
#                     sdl_keyword_measure = 1 if matches_sdl >= 1 else 0
#                     number_of_SDL_words = matches_sdl  # Count for compatibility
                    
#                     # SDL Filtered Tom Classification
#                     sdl_filtered_tom = classify_sdl_filtered_tom(title, abstract)
                    
#                     # First Author Metrics
#                     if first_author_id in author_df.index:
#                         first_author = author_df.loc[first_author_id]
#                         f_papers = first_author['total_papers']
#                         f_cites = first_author['total_citations']
#                         f_sdl_brown = first_author.get('sdl_brown_papers', 0)
#                         f_sdl_tomet = first_author.get('sdl_tomet_papers', 0)
#                         f_field = first_author['top_field']
#                         f_top_topic = first_author['top_topic']
#                         f_top_journal = first_author['top_journal']
#                         f_uniq_fields = first_author['num_unique_fields']
#                         f_uniq_topics = first_author['num_unique_topics']
#                         f_uniq_journals = first_author['num_unique_journals']
#                     else:
#                         f_papers, f_cites = 0, 0
#                         f_sdl_brown, f_sdl_tomet = 0, 0
#                         f_field, f_top_topic, f_top_journal = '', '', ''
#                         f_uniq_fields, f_uniq_topics, f_uniq_journals = 0, 0, 0
                    
#                     # Last Author Metrics
#                     if last_author_id in author_df.index:
#                         last_author = author_df.loc[last_author_id]
#                         l_papers = last_author['total_papers']
#                         l_cites = last_author['total_citations']
#                         l_sdl_brown = last_author.get('sdl_brown_papers', 0)
#                         l_sdl_tomet = last_author.get('sdl_tomet_papers', 0)
#                         l_field = last_author['top_field']
#                         l_top_topic = last_author['top_topic']
#                         l_top_journal = last_author['top_journal']
#                         l_uniq_fields = last_author['num_unique_fields']
#                         l_uniq_topics = last_author['num_unique_topics']
#                         l_uniq_journals = last_author['num_unique_journals']
#                         l_has_cs = 1 if last_author.get('has_cs_experience', 0) == 1 else 0
#                         l_avg_team = last_author.get('avg_team_size', 0)
#                         l_avg_team_man = last_author.get('avg_team_size_last_author', 0)
#                         l_avg_team_sdl_brown = last_author.get('avg_team_size_sdl_brown', 0)
#                         l_avg_team_sdl_tomet = last_author.get('avg_team_size_sdl_tomet', 0)
#                         l_avg_team_high_auto = last_author.get('avg_team_size_high_automation', 0)
#                         l_profile = last_author.get('author_profile', 'Unknown')
#                         l_field_counts = last_author.get('field_counts', '{}')
#                     else:
#                         l_papers, l_cites = 0, 0
#                         l_sdl_brown, l_sdl_tomet = 0, 0
#                         l_field, l_top_topic, l_top_journal = '', '', ''
#                         l_uniq_fields, l_uniq_topics, l_uniq_journals = 0, 0, 0
#                         l_has_cs = 0
#                         l_avg_team, l_avg_team_man = 0, 0
#                         l_avg_team_sdl_brown, l_avg_team_sdl_tomet = 0, 0
#                         l_avg_team_high_auto = 0
#                         l_profile, l_field_counts = 'Unknown', '{}'
                    
#                     # Create paper record
#                     paper_record = {
#                         'article_id': row['article_id'],
#                         'doi': row.get('doi', ''),
#                         'title': title,
#                         'publication_year': row['publication_year'],
#                         'publication_date': publication_date or '',
#                         'author_count': row['author_count'],
                        
#                         # SDL Classifications (separated)
#                         'SDL_Brown': sdl_brown,
#                         'SDL_Tomet': sdl_tomet,
#                         'high_automation': high_auto,
#                         'sdl_keyword_measure': sdl_keyword_measure,
#                         'number_of_SDL_words': number_of_SDL_words,  # Added for compatibility
#                         'SDL_Filtered_Tom': sdl_filtered_tom,
                        
#                         'AI_Paper': row.get('AI_Paper', 0),
#                         'Robotics_Paper': row.get('Robotics_Paper', 0),
                        
#                         'num_paper_affiliations': num_affiliations,
#                         'primary_topic': primary_topic or 'MISSING',
#                         'all_topics': all_topics_str or '',
#                         'journal': journal or 'MISSING',
#                         'cited_by_count': cited_by_count,
#                         'field': field_name,
#                         'abstract': abstract or '',
#                         'comp_sci_experience_paper': comp_sci_experience_paper,
                        
#                         # First Author
#                         'first_author_id': first_author_id,
#                         'first_author_papers': f_papers,
#                         'first_author_citations': f_cites,
#                         'first_author_sdl_brown_experience': f_sdl_brown,
#                         'first_author_sdl_tomet_experience': f_sdl_tomet,
#                         'first_author_field': f_field,
#                         'first_author_top_topic': f_top_topic if pd.notna(f_top_topic) else '',
#                         'first_author_top_journal': f_top_journal if pd.notna(f_top_journal) else '',
#                         'first_author_unique_fields_count': f_uniq_fields,
#                         'first_author_unique_topics_count': f_uniq_topics,
#                         'first_author_unique_journals_count': f_uniq_journals,
                        
#                         # Last Author
#                         'last_author_id': last_author_id,
#                         'last_author_papers': l_papers,
#                         'last_author_citations': l_cites,
#                         'last_author_sdl_brown_experience': l_sdl_brown,
#                         'last_author_sdl_tomet_experience': l_sdl_tomet,
#                         'last_author_field': l_field,
#                         'last_author_top_topic': l_top_topic if pd.notna(l_top_topic) else '',
#                         'last_author_top_journal': l_top_journal if pd.notna(l_top_journal) else '',
#                         'last_author_unique_fields_count': l_uniq_fields,
#                         'last_author_unique_topics_count': l_uniq_topics,
#                         'last_author_unique_journals_count': l_uniq_journals,
#                         'last_author_has_cs_exp': l_has_cs,
#                         'last_author_avg_team_size_overall': l_avg_team,
#                         'last_author_avg_team_size_managerial': l_avg_team_man,
#                         'last_author_avg_team_size_sdl_brown': l_avg_team_sdl_brown,
#                         'last_author_avg_team_size_sdl_tomet': l_avg_team_sdl_tomet,
#                         'last_author_avg_team_size_high_automation': l_avg_team_high_auto,
#                         'last_author_profile': l_profile,
#                         'last_author_field_counts': l_field_counts,
#                     }
                    
#                     papers.append(paper_record)
#                     total += 1
                    
#                 except Exception as e:
#                     skipped += 1
#                     continue
                    
#     except Exception as e:
#         return field_name, year, [], 0, 0, f"ERROR: {str(e)}"
    
#     return field_name, year, papers, total, skipped, f"SUCCESS"


# # ============================================================================
# # MAIN PROCESSING
# # ============================================================================

# def build_regression_dataset():
#     """Build regression dataset with SDL venue filtering"""
    
#     print("\n" + "="*80)
#     print("BUILDING REGRESSION DATASET (FILTERED MODE)")
#     print("="*80)
#     print(f"Output: {OUTPUT_FILE}")
#     print(f"Years: {YEARS[0]}-{YEARS[-1]}")
#     print(f"Fields: {len(FIELDS)}")
#     print(f"CPU cores: {NUM_CORES}")
#     print("="*80 + "\n")
    
#     # Verify files
#     print("Verifying required files...")
    
#     if not AUTHOR_METRICS_FILE.exists():
#         print(f"  ✗ ERROR: Author metrics not found")
#         print(f"    {AUTHOR_METRICS_FILE}")
#         sys.exit(1)
#     print(f"  ✓ Author metrics: {AUTHOR_METRICS_FILE}")
    
#     if not CS_KEYWORDS_FILE.exists():
#         print(f"  ✗ ERROR: CS keywords not found")
#         sys.exit(1)
#     print(f"  ✓ CS keywords: {CS_KEYWORDS_FILE}")
    
#     if not SDL_KEYWORDS_FILE.exists():
#         print(f"  ✗ ERROR: SDL keywords not found")
#         sys.exit(1)
#     print(f"  ✓ SDL keywords: {SDL_KEYWORDS_FILE}")
    
#     if not SDL_JOURNALS_FILE.exists():
#         print(f"  ✗ ERROR: SDL journals file not found")
#         sys.exit(1)
#     print(f"  ✓ SDL journals: {SDL_JOURNALS_FILE}")
    
#     if not SDL_TOPICS_FILE.exists():
#         print(f"  ✗ ERROR: SDL topics file not found")
#         sys.exit(1)
#     print(f"  ✓ SDL topics: {SDL_TOPICS_FILE}")
    
#     # Load keywords and venues
#     print("\nLoading keywords and venues...")
#     cs_keywords = load_keywords(CS_KEYWORDS_FILE)
#     sdl_keywords = load_keywords(SDL_KEYWORDS_FILE)
#     print(f"  CS keywords: {len(cs_keywords)}")
#     print(f"  SDL keywords: {len(sdl_keywords)}")
    
#     sdl_journals, sdl_topics = load_sdl_venues(SDL_JOURNALS_FILE, SDL_TOPICS_FILE)
    
#     # Build task list
#     print(f"\n{'='*80}")
#     print("Building task list...")
    
#     tasks = []
#     for field_name, field_dir in FIELDS.items():
#         if not field_dir.exists():
#             print(f"  ✗ {field_name}: directory not found")
#             continue
#         print(f"  ✓ {field_name}")
#         for year in YEARS:
#             tasks.append((field_name, field_dir, year, AUTHOR_METRICS_FILE, 
#                          cs_keywords, sdl_keywords))
    
#     print(f"\n  Total tasks: {len(tasks)}")
    
#     # Process in parallel
#     print(f"\n{'='*80}")
#     print(f"PROCESSING {len(tasks)} FILES IN PARALLEL")
#     print(f"{'='*80}\n")
    
#     start_time = time.time()
    
#     with Pool(NUM_CORES) as pool:
#         results = pool.map(process_field_year, tasks)
    
#     # Track results
#     successful = 0
#     failed = 0
#     not_found = 0
    
#     print("\nProcessing complete. Results:")
#     for field_name, year, papers, total, skipped, status in results:
#         if status == "SUCCESS":
#             successful += 1
#             if successful % 10 == 0:
#                 print(f"  ✓ {field_name}_{year}: {total:,} papers ({skipped:,} skipped)")
#         elif status == "FILE_NOT_FOUND":
#             not_found += 1
#         else:
#             failed += 1
#             print(f"  ✗ {field_name}_{year}: {status}")
    
#     elapsed = time.time() - start_time
    
#     print(f"\n{'='*80}")
#     print(f"PHASE 1 COMPLETE - {elapsed:.1f}s")
#     print(f"{'='*80}")
#     print(f"  Successful: {successful}")
#     print(f"  Not Found: {not_found}")
#     print(f"  Failed: {failed}")
#     print(f"{'='*80}\n")
    
#     # Combine results
#     print(f"{'='*80}")
#     print("COMBINING RESULTS")
#     print(f"{'='*80}\n")
    
#     all_papers = []
#     total_papers = 0
#     total_skipped = 0
#     field_summary = {}
    
#     for field_name, year, papers, total, skipped, status in results:
#         all_papers.extend(papers)
#         total_papers += total
#         total_skipped += skipped
        
#         if field_name not in field_summary:
#             field_summary[field_name] = {'papers': 0, 'skipped': 0}
#         field_summary[field_name]['papers'] += total
#         field_summary[field_name]['skipped'] += skipped
    
#     print("Papers by field:")
#     for field_name, stats in field_summary.items():
#         print(f"  {field_name}: {stats['papers']:,} papers ({stats['skipped']:,} skipped)")
    
#     print(f"\nTOTAL BEFORE FILTERING: {total_papers:,} papers ({total_skipped:,} skipped)\n")
    
#     # Create DataFrame
#     print(f"{'='*80}")
#     print("CREATING DATAFRAME")
#     print(f"{'='*80}\n")
    
#     df = pd.DataFrame(all_papers)
#     print(f"  DataFrame shape (before filtering): {df.shape}")
#     print(f"  Columns: {len(df.columns)}")
    
#     # ========================================================================
#     # CRITICAL: SDL VENUE FILTERING (WAS MISSING IN NEW VERSION)
#     # ========================================================================
#     print(f"\n{'='*80}")
#     print("APPLYING SDL VENUE FILTERING")
#     print(f"{'='*80}\n")
    
#     print(f"  Before filtering: {len(df):,} papers")
    
#     # Filter by SDL journals AND topics
#     print(f"  Applying venue filters...")
#     mask = df['journal'].isin(sdl_journals) & df['primary_topic'].isin(sdl_topics)
#     df = df[mask].copy()
#     print(f"  After venue filtering: {len(df):,} papers")
    
#     # Remove rows with missing key variables
#     key_vars = ['author_count', 'publication_year', 'field', 
#                 'first_author_papers', 'last_author_papers']
    
#     pre_dropna = len(df)
#     df = df.dropna(subset=key_vars)
#     print(f"  Removed {pre_dropna - len(df):,} with missing key variables")
#     print(f"  FINAL after filtering: {len(df):,} papers\n")
    
#     # Apply transformations
#     print("  Applying transformations...")
#     df['asinh_first_author_papers'] = np.arcsinh(df['first_author_papers'].astype(float))
#     df['asinh_first_author_citations'] = np.arcsinh(df['first_author_citations'].astype(float))
#     df['asinh_last_author_papers'] = np.arcsinh(df['last_author_papers'].astype(float))
#     df['asinh_last_author_citations'] = np.arcsinh(df['last_author_citations'].astype(float))
#     df['asinh_paper_citations'] = np.arcsinh(df['cited_by_count'].astype(float))
#     df['log_author_count'] = np.log(df['author_count'].astype(float).replace(0, np.nan))
    
#     print("  ✓ Transformations complete\n")
    
#     # Save
#     print(f"{'='*80}")
#     print("SAVING DATASET")
#     print(f"{'='*80}\n")
    
#     print(f"  Saving to: {OUTPUT_FILE}")
#     df.to_csv(OUTPUT_FILE, index=False)
    
#     file_size = OUTPUT_FILE.stat().st_size / (1024 * 1024)
#     print(f"  ✓ Saved: {file_size:.1f} MB")
    
#     # Summary
#     print(f"\n{'='*80}")
#     print("SUMMARY")
#     print(f"{'='*80}\n")
    
#     print(f"Total papers (filtered): {len(df):,}")
#     print(f"\nSDL Classifications:")
#     print(f"  SDL Brown: {df['SDL_Brown'].sum():,}")
#     print(f"  SDL Tomet: {df['SDL_Tomet'].sum():,}")
#     print(f"  SDL Keyword: {df['sdl_keyword_measure'].sum():,}")
#     print(f"  SDL Filtered Tom: {df['SDL_Filtered_Tom'].sum():,}")
#     print(f"  High Automation: {df['high_automation'].sum():,}")
    
#     print(f"\nOther Classifications:")
#     print(f"  AI Papers: {df['AI_Paper'].sum():,}")
#     print(f"  Robotics Papers: {df['Robotics_Paper'].sum():,}")
#     print(f"  CS Experience Papers: {df['comp_sci_experience_paper'].sum():,}")
    
#     with_abstract = df['abstract'].notna().sum()
#     print(f"\nPapers with abstracts: {with_abstract:,} ({with_abstract/len(df)*100:.1f}%)")
    
#     print(f"\nPapers by field:")
#     print(df['field'].value_counts().to_string())
    
#     total_elapsed = time.time() - start_time
#     print(f"\n{'='*80}")
#     print(f"COMPLETE - Total Time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
#     print(f"{'='*80}\n")
    
#     return df


# # ============================================================================
# # MAIN
# # ============================================================================

# if __name__ == "__main__":
#     df = build_regression_dataset()


# # NEW REGRESSION DATASET 2004 ONWARDS (BROWN + TOMET VENUE FILTERING)

"""
Build regression dataset from field TSV files with author metrics
- Separated SDL metrics (Brown, Tomet)
- High automation papers
- SDL Filtered Tom classification
- SDL VENUE FILTERING: Now uses Brown + Tomet combined journals and topics
- No corresponding author variables
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

AUTHOR_METRICS_FILE = PROJECT_DIR / "data" / "author" / "author_metrics.csv"

CS_KEYWORDS_FILE = PROJECT_DIR / "data/lasso_regression" / "cs_keywords_shortlisted.txt"
SDL_KEYWORDS_FILE = PROJECT_DIR / "data" / "keywords" / "sdl_Keywords.csv"

# ============================================================================
# CRITICAL CHANGE: SDL VENUE FILTERING FILES
# ============================================================================
# UPDATED: Now uses 4 separate files (Brown + Tomet journals and topics)
# Will combine them into union sets for filtering
SDL_BROWN_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "brown_journals.csv"
SDL_TOMET_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "tom_journals.csv"
SDL_BROWN_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "brown_primary_topics.csv"
SDL_TOMET_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "tom_primary_topics.csv"

OUTPUT_DIR = PROJECT_DIR / "data" / "regression/test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "regression_dataset_filtered_2004_12345.csv"

YEARS = range(2004, 2026)  # 2004-2025
CHUNK_SIZE = 500000
NUM_CORES = 8

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
    """
    Load SDL journals and topics from 4 separate CSV files
    Returns union (deduplicated) of Brown and Tomet venues
    
    Filter logic: Paper must match:
      - Journal in (Brown journals OR Tomet journals) AND
      - Topic in (Brown topics OR Tomet topics)
    """
    brown_journals = set()
    tomet_journals = set()
    brown_topics = set()
    tomet_topics = set()
    
    # Load Brown journals
    try:
        df = pd.read_csv(brown_journals_file, header=None)
        brown_journals = {str(val).strip() for val in df[0].dropna() if str(val).strip()}
        print(f"  Loaded {len(brown_journals)} Brown journals")
    except Exception as e:
        print(f"  Warning: Could not load Brown journals: {e}")
    
    # Load Tomet journals
    try:
        df = pd.read_csv(tomet_journals_file, header=None,sep='\t',on_bad_lines='skip')
        tomet_journals = {str(val).strip() for val in df[0].dropna() if str(val).strip()}
        print(f"  Loaded {len(tomet_journals)} Tomet journals")
    except Exception as e:
        print(f"  Warning: Could not load Tomet journals: {e}")
    
    # Load Brown topics
    try:
        df = pd.read_csv(brown_topics_file, header=None)
        brown_topics = {str(val).strip() for val in df[0].dropna() if str(val).strip()}
        print(f"  Loaded {len(brown_topics)} Brown topics")
    except Exception as e:
        print(f"  Warning: Could not load Brown topics: {e}")
    
    # Load Tomet topics
    try:
        df = pd.read_csv(tomet_topics_file, header=None)
        tomet_topics = {str(val).strip() for val in df[0].dropna() if str(val).strip()}
        print(f"  Loaded {len(tomet_topics)} Tomet topics")
    except Exception as e:
        print(f"  Warning: Could not load Tomet topics: {e}")
    
    # Combine into unions (automatically deduplicates)
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
    """
    Classify paper using SDL Filtered Tom definition
    
    CRITICAL CHANGE: Only applies to papers already classified as SDL
    
    Logic:
    1. IF paper is NOT SDL (Brown=0 AND Tomet=0): Return 0 (skip keyword check)
    2. IF paper IS SDL (Brown=1 OR Tomet=1): Check keywords
       - Returns 1 if matches ANY of the 6 category criteria
       - Returns 0 if no keyword matches found
    
    This means SDL_Filtered_Tom is a SUBSET of (Brown OR Tomet)
    """
    # CRITICAL: Only check keywords if paper is already SDL
    if sdl_brown == 0 and sdl_tomet == 0:
        return 0  # Not an SDL paper, don't check keywords
    
    # Paper IS SDL (Brown=1 OR Tomet=1), now check for keyword matches
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
    
    # Category 6: Self-driving (comprehensive)
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
    
    # Return 1 if ANY category matches, 0 if SDL but no keyword matches
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
        
        # Topics
        topics = data.get('topics', [])
        primary_topic = topics[0].get('display_name') if topics else None
        all_topics = [t.get('display_name') for t in topics if t.get('display_name')]
        all_topics_str = '|'.join(all_topics) if all_topics else None
        
        # Journal
        journal = data.get('primary_location', {}).get('source', {}).get('display_name')
        
        # Citations
        cited_by_count = data.get('cited_by_count', 0) or 0
        
        # Publication date
        publication_date = data.get('publication_date')
        
        # Abstract (reconstruct from inverted index)
        abstract_text = None
        abstract_inverted = data.get('abstract_inverted_index')
        if abstract_inverted:
            word_positions = []
            for word, positions in abstract_inverted.items():
                for pos in positions: 
                    word_positions.append((pos, word))
            word_positions.sort(key=lambda x: x[0])
            abstract_text = ' '.join([word for pos, word in word_positions])
        
        # Affiliations
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
    field_name, field_dir, year, author_metrics_path, cs_keywords, sdl_keywords = args
    
    # Locate file
    possible_files = [
        field_dir / f"{field_name}_{year}_sdl_classified.tsv",
        field_dir / f"{field_name}_{year}.tsv",
    ]
    tsv_file = next((f for f in possible_files if f.exists()), None)
    
    if not tsv_file: 
        return field_name, year, [], 0, 0, "FILE_NOT_FOUND"
    
    # Load author metrics
    author_df = pd.read_csv(author_metrics_path).set_index('author_id')
    
    papers = []
    total = 0
    skipped = 0
    
    try:
        # Columns to read
        use_cols = ['article_id', 'doi', 'title', 'publication_year', 'author_count', 
                    'brown_SDL_papers', 'tomet_al_SDL', 'high_automation_dummy',
                    'AI_Paper', 'Robotics_Paper', 'raw_data']
        
        # Check which columns exist
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
                    # CRITICAL: Now only checks keywords if paper is SDL (Brown=1 OR Tomet=1)
                    sdl_filtered_tom = classify_sdl_filtered_tom(title, abstract, sdl_brown, sdl_tomet)
                    
                    # First Author Metrics
                    if first_author_id in author_df.index:
                        first_author = author_df.loc[first_author_id]
                        f_papers = first_author['total_papers']
                        f_cites = first_author['total_citations']
                        f_sdl_brown = first_author.get('sdl_brown_papers', 0)
                        f_sdl_tomet = first_author.get('sdl_tomet_papers', 0)
                        f_field = first_author['top_field']
                        f_top_topic = first_author['top_topic']
                        f_top_journal = first_author['top_journal']
                        f_uniq_fields = first_author['num_unique_fields']
                        f_uniq_topics = first_author['num_unique_topics']
                        f_uniq_journals = first_author['num_unique_journals']
                    else:
                        f_papers, f_cites = 0, 0
                        f_sdl_brown, f_sdl_tomet = 0, 0
                        f_field, f_top_topic, f_top_journal = '', '', ''
                        f_uniq_fields, f_uniq_topics, f_uniq_journals = 0, 0, 0
                    
                    # Last Author Metrics
                    if last_author_id in author_df.index:
                        last_author = author_df.loc[last_author_id]
                        l_papers = last_author['total_papers']
                        l_cites = last_author['total_citations']
                        l_sdl_brown = last_author.get('sdl_brown_papers', 0)
                        l_sdl_tomet = last_author.get('sdl_tomet_papers', 0)
                        l_field = last_author['top_field']
                        l_top_topic = last_author['top_topic']
                        l_top_journal = last_author['top_journal']
                        l_uniq_fields = last_author['num_unique_fields']
                        l_uniq_topics = last_author['num_unique_topics']
                        l_uniq_journals = last_author['num_unique_journals']
                        l_has_cs = 1 if last_author.get('has_cs_experience', 0) == 1 else 0
                        l_avg_team = last_author.get('avg_team_size', 0)
                        l_avg_team_man = last_author.get('avg_team_size_last_author', 0)
                        l_avg_team_sdl_brown = last_author.get('avg_team_size_sdl_brown', 0)
                        l_avg_team_sdl_tomet = last_author.get('avg_team_size_sdl_tomet', 0)
                        l_avg_team_high_auto = last_author.get('avg_team_size_high_automation', 0)
                        l_profile = last_author.get('author_profile', 'Unknown')
                        l_field_counts = last_author.get('field_counts', '{}')
                    else:
                        l_papers, l_cites = 0, 0
                        l_sdl_brown, l_sdl_tomet = 0, 0
                        l_field, l_top_topic, l_top_journal = '', '', ''
                        l_uniq_fields, l_uniq_topics, l_uniq_journals = 0, 0, 0
                        l_has_cs = 0
                        l_avg_team, l_avg_team_man = 0, 0
                        l_avg_team_sdl_brown, l_avg_team_sdl_tomet = 0, 0
                        l_avg_team_high_auto = 0
                        l_profile, l_field_counts = 'Unknown', '{}'
                    
                    # Create paper record
                    paper_record = {
                        'article_id': row['article_id'],
                        'doi': row.get('doi', ''),
                        'title': title,
                        'publication_year': row['publication_year'],
                        'publication_date': publication_date or '',
                        'author_count': row['author_count'],
                        
                        # SDL Classifications (separated)
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
                        
                        # First Author
                        'first_author_id': first_author_id,
                        'first_author_papers': f_papers,
                        'first_author_citations': f_cites,
                        'first_author_sdl_brown_experience': f_sdl_brown,
                        'first_author_sdl_tomet_experience': f_sdl_tomet,
                        'first_author_field': f_field,
                        'first_author_top_topic': f_top_topic if pd.notna(f_top_topic) else '',
                        'first_author_top_journal': f_top_journal if pd.notna(f_top_journal) else '',
                        'first_author_unique_fields_count': f_uniq_fields,
                        'first_author_unique_topics_count': f_uniq_topics,
                        'first_author_unique_journals_count': f_uniq_journals,
                        
                        # Last Author
                        'last_author_id': last_author_id,
                        'last_author_papers': l_papers,
                        'last_author_citations': l_cites,
                        'last_author_sdl_brown_experience': l_sdl_brown,
                        'last_author_sdl_tomet_experience': l_sdl_tomet,
                        'last_author_field': l_field,
                        'last_author_top_topic': l_top_topic if pd.notna(l_top_topic) else '',
                        'last_author_top_journal': l_top_journal if pd.notna(l_top_journal) else '',
                        'last_author_unique_fields_count': l_uniq_fields,
                        'last_author_unique_topics_count': l_uniq_topics,
                        'last_author_unique_journals_count': l_uniq_journals,
                        'last_author_has_cs_exp': l_has_cs,
                        'last_author_avg_team_size_overall': l_avg_team,
                        'last_author_avg_team_size_managerial': l_avg_team_man,
                        'last_author_avg_team_size_sdl_brown': l_avg_team_sdl_brown,
                        'last_author_avg_team_size_sdl_tomet': l_avg_team_sdl_tomet,
                        'last_author_avg_team_size_high_automation': l_avg_team_high_auto,
                        'last_author_profile': l_profile,
                        'last_author_field_counts': l_field_counts,
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
    """
    Build regression dataset with SDL venue filtering
    
    Filtering approach:
    - Reads 4 CSV files: Brown journals, Tomet journals, Brown topics, Tomet topics
    - Creates union (deduplicated) of journals and topics
    - Keeps papers where:
        * Journal matches (Brown OR Tomet journals) AND
        * Primary topic matches (Brown OR Tomet topics)
    """
    
    print("\n" + "="*80)
    print("BUILDING REGRESSION DATASET")
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
        print(f"  ✗ ERROR: Author metrics not found")
        print(f"    {AUTHOR_METRICS_FILE}")
        sys.exit(1)
    print(f"  ✓ Author metrics: {AUTHOR_METRICS_FILE}")
    
    if not CS_KEYWORDS_FILE.exists():
        print(f"  ✗ ERROR: CS keywords not found")
        sys.exit(1)
    print(f"  ✓ CS keywords: {CS_KEYWORDS_FILE}")
    
    if not SDL_KEYWORDS_FILE.exists():
        print(f"  ✗ ERROR: SDL keywords not found")
        sys.exit(1)
    print(f"  ✓ SDL keywords: {SDL_KEYWORDS_FILE}")
    
    # ========================================================================
    # CRITICAL: Verify all 4 SDL venue files exist
    # ========================================================================
    if not SDL_BROWN_JOURNALS_FILE.exists():
        print(f"  ✗ ERROR: Brown journals file not found")
        print(f"    Expected: {SDL_BROWN_JOURNALS_FILE}")
        sys.exit(1)
    print(f"  ✓ Brown journals: {SDL_BROWN_JOURNALS_FILE}")
    
    if not SDL_TOMET_JOURNALS_FILE.exists():
        print(f"  ✗ ERROR: Tomet journals file not found")
        print(f"    Expected: {SDL_TOMET_JOURNALS_FILE}")
        sys.exit(1)
    print(f"  ✓ Tomet journals: {SDL_TOMET_JOURNALS_FILE}")
    
    if not SDL_BROWN_TOPICS_FILE.exists():
        print(f"  ✗ ERROR: Brown topics file not found")
        print(f"    Expected: {SDL_BROWN_TOPICS_FILE}")
        sys.exit(1)
    print(f"  ✓ Brown topics: {SDL_BROWN_TOPICS_FILE}")
    
    if not SDL_TOMET_TOPICS_FILE.exists():
        print(f"  ✗ ERROR: Tomet topics file not found")
        print(f"    Expected: {SDL_TOMET_TOPICS_FILE}")
        sys.exit(1)
    print(f"  ✓ Tomet topics: {SDL_TOMET_TOPICS_FILE}")
    
    # Load keywords and venues
    print("\nLoading keywords and venues...")
    cs_keywords = load_keywords(CS_KEYWORDS_FILE)
    sdl_keywords = load_keywords(SDL_KEYWORDS_FILE)
    print(f"  CS keywords: {len(cs_keywords)}")
    print(f"  SDL keywords: {len(sdl_keywords)}")
    
    # Load Brown + Tomet venues (will be combined into union)
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
            tasks.append((field_name, field_dir, year, AUTHOR_METRICS_FILE, 
                         cs_keywords, sdl_keywords))
    
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
    field_summary = {}
    
    for field_name, year, papers, total, skipped, status in results:
        all_papers.extend(papers)
        total_papers += total
        total_skipped += skipped
        
        if field_name not in field_summary:
            field_summary[field_name] = {'papers': 0, 'skipped': 0}
        field_summary[field_name]['papers'] += total
        field_summary[field_name]['skipped'] += skipped
    
    print("Papers by field:")
    for field_name, stats in field_summary.items():
        print(f"  {field_name}: {stats['papers']:,} papers ({stats['skipped']:,} skipped)")
    
    print(f"\nTOTAL BEFORE FILTERING: {total_papers:,} papers ({total_skipped:,} skipped)\n")
    
    # Create DataFrame
    print(f"{'='*80}")
    print("CREATING DATAFRAME")
    print(f"{'='*80}\n")
    
    df = pd.DataFrame(all_papers)
    print(f"  DataFrame shape (before filtering): {df.shape}")
    print(f"  Columns: {len(df.columns)}")
    
    # ========================================================================
    # CRITICAL: SDL VENUE FILTERING (Brown OR Tomet)
    # ========================================================================
    print(f"\n{'='*80}")
    print("APPLYING SDL VENUE FILTERING")
    print("Filter: (Journal in Brown OR Tomet) AND (Topic in Brown OR Tomet)")
    print(f"{'='*80}\n")
    
    print(f"  Before filtering: {len(df):,} papers")
    
    # Filter: Paper must have:
    #   - Journal in (Brown journals OR Tomet journals) AND
    #   - Topic in (Brown topics OR Tomet topics)
    print(f"  Applying venue filters...")
    print(f"    Journals to match (union): {len(sdl_journals):,}")
    print(f"    Topics to match (union): {len(sdl_topics):,}")
    
    mask = df['journal'].isin(sdl_journals) & df['primary_topic'].isin(sdl_topics)
    df = df[mask].copy()
    print(f"  After venue filtering: {len(df):,} papers")
    
    # Remove rows with missing key variables
    key_vars = ['author_count', 'publication_year', 'field', 
                'first_author_papers', 'last_author_papers']
    
    pre_dropna = len(df)
    df = df.dropna(subset=key_vars)
    print(f"  Removed {pre_dropna - len(df):,} with missing key variables")
    print(f"  FINAL after filtering: {len(df):,} papers\n")
    
    # Apply transformations
    print("  Applying transformations...")
    df['asinh_first_author_papers'] = np.arcsinh(df['first_author_papers'].astype(float))
    df['asinh_first_author_citations'] = np.arcsinh(df['first_author_citations'].astype(float))
    df['asinh_last_author_papers'] = np.arcsinh(df['last_author_papers'].astype(float))
    df['asinh_last_author_citations'] = np.arcsinh(df['last_author_citations'].astype(float))
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
