
# """
# Build author-level dataset with THREE-YEAR BACKWARD-LOOKING ROLLING AVERAGES
# - Each row = author-year combination
# - Metrics computed from T-3, T-2, T-1 (excluding current year T)
# - Handles edge cases for early years (2004-2006)
# """
# import pandas as pd
# import json
# from collections import Counter, defaultdict
# import numpy as np
# from pathlib import Path
# import multiprocessing as mp
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

# CS_KEYWORDS_FILE = PROJECT_DIR / "data/lasso_regression" / "cs_keywords_shortlisted.txt"

# OUTPUT_DIR = PROJECT_DIR / "data" / "yearly_data/test"
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# OUTPUT_FILE = OUTPUT_DIR / "author_metrics_3yr_rolling.csv"

# YEARS = range(2004, 2026)  # 2004-2025
# CHUNK_SIZE = 500000
# NUM_CORES = 8

# # ============================================================================
# # HELPER FUNCTIONS
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
#     """Check if at least 2 different CS keywords match"""
#     if not cs_keywords_set:
#         return False
        
#     matched_keywords = set()
    
#     if primary_topic:
#         primary_lower = primary_topic.lower()
#         for keyword in cs_keywords_set:
#             if keyword in primary_lower:
#                 matched_keywords.add(keyword)
#                 if len(matched_keywords) >= 2: return True
    
#     if all_topics:
#         for t in all_topics:
#             t_lower = t.lower()
#             for keyword in cs_keywords_set:
#                 if keyword in t_lower:
#                     matched_keywords.add(keyword)
#                     if len(matched_keywords) >= 2: return True
    
#     if title and isinstance(title, str):
#         title_lower = title.lower()
#         for keyword in cs_keywords_set:
#             if keyword in title_lower:
#                 matched_keywords.add(keyword)
#                 if len(matched_keywords) >= 2: return True
    
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
#     """Extract metadata needed for CS checking"""
#     if pd.isna(raw_data_json) or raw_data_json == '':
#         return None, [], None, None
#     try:
#         data = json.loads(raw_data_json)
#         topics = data.get('topics', [])
#         primary_topic = topics[0].get('display_name') if topics else None
#         all_topics = [t.get('display_name') for t in topics if t.get('display_name')]
#         title = data.get('title', '')
        
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
# # PAPER RECORD STRUCTURE (Per Author-Year)
# # ============================================================================

# def create_paper_record():
#     """Create a single paper record for an author"""
#     return {
#         'year': 0,
#         'author_name': '',
#         'field': '',
#         'topic': '',
#         'journal': '',
#         'citations': 0,
#         'team_size': 0,
#         'is_first': False,
#         'is_last': False,
#         'is_corresponding': False,
#         'is_sdl_brown': False,
#         'is_sdl_tomet': False,
#         'is_high_automation': False,
#         'is_ai': False,
#         'is_robotics': False,
#         'is_cs_paper': False,
#         'institutions': []
#     }

# # ============================================================================
# # PROCESS SINGLE YEAR FILE
# # ============================================================================

# def process_single_year_file(args):
#     """
#     Process a single year file
#     Returns: dict mapping author_id → list of paper records
#     """
#     field_name, field_dir, year = args
    
#     possible_files = [
#         field_dir / f"{field_name}_{year}.tsv",
#         field_dir / f"{field_name}_{year}.tsv",
#     ]
#     tsv_file = next((f for f in possible_files if f.exists()), None)
    
#     if not tsv_file: 
#         return {}, f"{field_name}_{year}", "FILE_NOT_FOUND"
    
#     cs_keywords = load_cs_keywords(CS_KEYWORDS_FILE)
    
#     # Dict: author_id → list of paper records
#     author_papers = defaultdict(list)
#     rows_processed = 0
    
#     try:
#         sample = pd.read_csv(tsv_file, sep='\t', nrows=5)
#         available_cols = set(sample.columns)
        
#         required = ['raw_data', 'author_count', 'publication_year',
#                    'brown_SDL_papers', 'tomet_al_SDL',
#                    'high_automation_dummy',
#                    'AI_Paper', 'Robotics_Paper']
        
#         columns_to_read = [col for col in required if col in available_cols]
        
#         if 'raw_data' not in columns_to_read: 
#             return {}, f"{field_name}_{year}", "NO_RAW_DATA"
        
#         for chunk in pd.read_csv(tsv_file, sep='\t', usecols=columns_to_read,
#                                 chunksize=CHUNK_SIZE, low_memory=False,
#                                 on_bad_lines='skip'):
            
#             for _, row in chunk.iterrows():
#                 rows_processed += 1
#                 try:
#                     raw = row.get('raw_data')
#                     authorships = parse_authorships(raw)
#                     if not authorships: continue
                    
#                     # paper_year = row.get('publication_year')
#                     # if pd.isna(paper_year): continue
#                     # paper_year = int(paper_year)
                    
#                     paper_year = row.get('publication_year')
#                     if pd.isna(paper_year):
#                         paper_year = year  # fall back to the year from the task args tuple
#                     else:
#                         paper_year = int(paper_year)



#                     # Paper-level metadata - ENSURE PROPER TYPES
#                     citations = parse_cited_by_count(raw)
#                     citations = int(citations) if not pd.isna(citations) else 0
                    
#                     is_sdl_brown = row.get('brown_SDL_papers', 0) == 1
#                     is_sdl_tomet = row.get('tomet_al_SDL', 0) == 1
#                     is_high_automation = row.get('high_automation_dummy', 0) == 1
#                     is_ai = row.get('AI_Paper', 0) == 1
#                     is_robotics = row.get('Robotics_Paper', 0) == 1
                    
#                     # FIX: Ensure team_size is always an integer
#                     team_size = row.get('author_count', 0)
#                     if pd.isna(team_size):
#                         team_size = 0
#                     else:
#                         team_size = int(float(team_size))  # Convert via float first to handle string numbers
                    
#                     primary_topic, all_topics, title, abstract = parse_metadata_for_cs(raw)
#                     journal = parse_journal(raw)
#                     corresponding_ids = parse_corresponding_author_ids(raw)
                    
#                     is_cs_paper = False
#                     if field_name == 'computer_science':
#                         is_cs_paper = True
#                     else:
#                         is_cs_paper = check_cs_keyword_match(primary_topic, all_topics, title, abstract, cs_keywords)
                    
#                     # Create paper record for each author
#                     for authorship in authorships:
#                         author_id = authorship['author_id']
                        
#                         paper_rec = {
#                             'year': paper_year,
#                             'author_name': authorship['author_name'],
#                             'field': field_name,
#                             'topic': primary_topic or '',
#                             'journal': journal or '',
#                             'citations': citations,
#                             'team_size': team_size,  # Now guaranteed to be int
#                             'is_first': authorship['is_first'],
#                             'is_last': authorship['is_last'],
#                             'is_corresponding': (author_id in corresponding_ids),
#                             'is_sdl_brown': is_sdl_brown,
#                             'is_sdl_tomet': is_sdl_tomet,
#                             'is_high_automation': is_high_automation,
#                             'is_ai': is_ai,
#                             'is_robotics': is_robotics,
#                             'is_cs_paper': is_cs_paper,
#                             'institutions': authorship['institutions']
#                         }
                        
#                         author_papers[author_id].append(paper_rec)
                        
#                 except Exception as e:
#                     # Optionally log errors for debugging
#                     # print(f"Error processing row: {e}")
#                     continue
                    
#         return dict(author_papers), f"{field_name}_{year}", f"SUCCESS_{rows_processed}"
        
#     except Exception as e:
#         return {}, f"{field_name}_{year}", f"ERROR_{str(e)}"

# # ============================================================================
# # MERGE AUTHOR PAPERS
# # ============================================================================

# def merge_author_papers(dict1, dict2):
#     """Merge two author_papers dictionaries"""
#     for author_id, papers in dict2.items():
#         if author_id not in dict1:
#             dict1[author_id] = papers
#         else:
#             dict1[author_id].extend(papers)
#     return dict1

# # ============================================================================
# # COMPUTE 3-YEAR BACKWARD METRICS
# # ============================================================================

# def compute_3yr_backward_metrics(author_id, papers_list, target_year):
#     """
#     Compute 3-year backward-looking metrics for an author in target_year
#     Uses data from years [target_year-3, target_year-2, target_year-1] ONLY
    
#     Returns: dict of metrics for this author-year
#     """
    
#     # Filter papers to 3-year backward window
#     window_start = target_year - 3
#     window_end = target_year - 1
    
#     prior_papers = [p for p in papers_list if window_start <= p['year'] <= window_end]
    
#     # Edge case: no prior data
#     if not prior_papers:
#         return create_empty_metrics(author_id, target_year, 0)
    
#     # Determine how many prior years we have
#     prior_years = sorted(set(p['year'] for p in prior_papers))
#     num_prior_years = len(prior_years)
    
#     # Get author name (most common)
#     names = [p['author_name'] for p in prior_papers if p['author_name']]
#     author_name = Counter(names).most_common(1)[0][0] if names else ''
    
#     # ========================================================================
#     # PAPER COUNTS
#     # ========================================================================
#     total_papers_3yr = len(prior_papers)
#     first_author_papers_3yr = sum(1 for p in prior_papers if p['is_first'])
#     last_author_papers_3yr = sum(1 for p in prior_papers if p['is_last'])
#     corresponding_papers_3yr = sum(1 for p in prior_papers if p['is_corresponding'])
    
#     sdl_brown_papers_3yr = sum(1 for p in prior_papers if p['is_sdl_brown'])
#     sdl_tomet_papers_3yr = sum(1 for p in prior_papers if p['is_sdl_tomet'])
#     high_automation_papers_3yr = sum(1 for p in prior_papers if p['is_high_automation'])
#     ai_papers_3yr = sum(1 for p in prior_papers if p['is_ai'])
#     robotics_papers_3yr = sum(1 for p in prior_papers if p['is_robotics'])
    
#     # ========================================================================
#     # CITATIONS
#     # ========================================================================
#     total_citations_3yr = sum(p['citations'] for p in prior_papers)
#     avg_citations_per_paper_3yr = round(total_citations_3yr / total_papers_3yr, 2) if total_papers_3yr > 0 else 0
    
#     # ========================================================================
#     # TEAM SIZE AVERAGES
#     # ========================================================================
    
#     # 1. Overall avg team size
#     avg_team_size_3yr = 0
#     if total_papers_3yr > 0:
#         avg_team_size_3yr = round(sum(p['team_size'] for p in prior_papers) / total_papers_3yr, 2)
    
#     # 2. Avg team size as last author (managerial)
#     last_author_papers = [p for p in prior_papers if p['is_last']]
#     avg_team_size_last_author_3yr = 0
#     if last_author_papers:
#         avg_team_size_last_author_3yr = round(sum(p['team_size'] for p in last_author_papers) / len(last_author_papers), 2)
    
#     # 3. Avg team size on Brown SDL papers
#     brown_papers = [p for p in prior_papers if p['is_sdl_brown']]
#     avg_team_size_sdl_brown_3yr = 0
#     if brown_papers:
#         avg_team_size_sdl_brown_3yr = round(sum(p['team_size'] for p in brown_papers) / len(brown_papers), 2)
    
#     # 4. Avg team size on Tomet SDL papers
#     tomet_papers = [p for p in prior_papers if p['is_sdl_tomet']]
#     avg_team_size_sdl_tomet_3yr = 0
#     if tomet_papers:
#         avg_team_size_sdl_tomet_3yr = round(sum(p['team_size'] for p in tomet_papers) / len(tomet_papers), 2)
    
#     # 5. Avg team size on high automation papers
#     high_auto_papers = [p for p in prior_papers if p['is_high_automation']]
#     avg_team_size_high_automation_3yr = 0
#     if high_auto_papers:
#         avg_team_size_high_automation_3yr = round(sum(p['team_size'] for p in high_auto_papers) / len(high_auto_papers), 2)
    
#     # ========================================================================
#     # FIELD ANALYSIS
#     # ========================================================================
#     fields = [p['field'] for p in prior_papers if p['field']]
#     field_counter = Counter(fields)
    
#     if field_counter:
#         top_field_3yr, top_field_count_3yr = field_counter.most_common(1)[0]
#         num_unique_fields_3yr = len(field_counter)
#     else:
#         top_field_3yr, top_field_count_3yr, num_unique_fields_3yr = '', 0, 0
    
#     field_counts_str = str(dict(field_counter))
    
#     # Author Profile (based on 3-year field distribution)
#     core_fields = []
#     for field, count in field_counter.items():
#         if count >= 2 and (count / total_papers_3yr) > 0.10:
#             core_fields.append(field)
    
#     core_fields.sort()
    
#     if len(core_fields) == 0:
#         author_profile_3yr = f"{top_field_3yr}_Only" if top_field_3yr else "Unknown"
#     elif len(core_fields) == 1:
#         author_profile_3yr = f"{core_fields[0]}_Only"
#     elif len(core_fields) == 2:
#         author_profile_3yr = "+".join(core_fields)
#     else:
#         author_profile_3yr = "Generalist"
    
#     # ========================================================================
#     # TOPIC ANALYSIS
#     # ========================================================================
#     topics = [p['topic'] for p in prior_papers if p['topic']]
#     topic_counter = Counter(topics)
    
#     if topic_counter:
#         top_topic_3yr, top_topic_count_3yr = topic_counter.most_common(1)[0]
#         num_unique_topics_3yr = len(topic_counter)
#     else:
#         top_topic_3yr, top_topic_count_3yr, num_unique_topics_3yr = '', 0, 0
    
#     # ========================================================================
#     # JOURNAL ANALYSIS
#     # ========================================================================
#     journals = [p['journal'] for p in prior_papers if p['journal']]
#     journal_counter = Counter(journals)
    
#     if journal_counter:
#         top_journal_3yr, top_journal_count_3yr = journal_counter.most_common(1)[0]
#         num_unique_journals_3yr = len(journal_counter)
#     else:
#         top_journal_3yr, top_journal_count_3yr, num_unique_journals_3yr = '', 0, 0
    
#     # ========================================================================
#     # CS EXPERIENCE (in past 3 years)
#     # ========================================================================
#     has_cs_experience_3yr = 1 if any(p['is_cs_paper'] for p in prior_papers) else 0
    
#     # ========================================================================
#     # AFFILIATIONS
#     # ========================================================================
#     all_institutions = set()
#     for p in prior_papers:
#         all_institutions.update(p['institutions'])
    
#     num_affiliations_3yr = len(all_institutions)
#     top_affiliation_3yr = list(all_institutions)[0] if all_institutions else ''
    
#     # ========================================================================
#     # RETURN METRICS DICT
#     # ========================================================================
#     return {
#         'author_id': author_id,
#         'author_name': author_name,
#         'year': target_year,
#         'num_prior_years_available': num_prior_years,
        
#         # Paper counts
#         'total_papers_3yr': total_papers_3yr,
#         'first_author_papers_3yr': first_author_papers_3yr,
#         'last_author_papers_3yr': last_author_papers_3yr,
#         'corresponding_author_papers_3yr': corresponding_papers_3yr,
        
#         # SDL classifications
#         'sdl_brown_papers_3yr': sdl_brown_papers_3yr,
#         'sdl_tomet_papers_3yr': sdl_tomet_papers_3yr,
#         'high_automation_papers_3yr': high_automation_papers_3yr,
#         'ai_papers_3yr': ai_papers_3yr,
#         'robotics_papers_3yr': robotics_papers_3yr,
        
#         # Citations
#         'total_citations_3yr': total_citations_3yr,
#         'avg_citations_per_paper_3yr': avg_citations_per_paper_3yr,
        
#         # Team sizes
#         'avg_team_size_3yr': avg_team_size_3yr,
#         'avg_team_size_last_author_3yr': avg_team_size_last_author_3yr,
#         'avg_team_size_sdl_brown_3yr': avg_team_size_sdl_brown_3yr,
#         'avg_team_size_sdl_tomet_3yr': avg_team_size_sdl_tomet_3yr,
#         'avg_team_size_high_automation_3yr': avg_team_size_high_automation_3yr,
        
#         # Field
#         'top_field_3yr': top_field_3yr,
#         'top_field_paper_count_3yr': top_field_count_3yr,
#         'num_unique_fields_3yr': num_unique_fields_3yr,
#         'field_counts_3yr': field_counts_str,
#         'author_profile_3yr': author_profile_3yr,
        
#         # Topic
#         'top_topic_3yr': top_topic_3yr,
#         'top_topic_paper_count_3yr': top_topic_count_3yr,
#         'num_unique_topics_3yr': num_unique_topics_3yr,
        
#         # Journal
#         'top_journal_3yr': top_journal_3yr,
#         'top_journal_paper_count_3yr': top_journal_count_3yr,
#         'num_unique_journals_3yr': num_unique_journals_3yr,
        
#         # CS Experience
#         'has_cs_experience_3yr': has_cs_experience_3yr,
        
#         # Affiliations
#         'num_affiliations_3yr': num_affiliations_3yr,
#         'top_affiliation_3yr': top_affiliation_3yr,
#     }


# def create_empty_metrics(author_id, target_year, num_prior_years):
#     """Create empty metrics for years with no prior data"""
#     return {
#         'author_id': author_id,
#         'author_name': '',
#         'year': target_year,
#         'num_prior_years_available': num_prior_years,
        
#         'total_papers_3yr': 0,
#         'first_author_papers_3yr': 0,
#         'last_author_papers_3yr': 0,
#         'corresponding_author_papers_3yr': 0,
        
#         'sdl_brown_papers_3yr': 0,
#         'sdl_tomet_papers_3yr': 0,
#         'high_automation_papers_3yr': 0,
#         'ai_papers_3yr': 0,
#         'robotics_papers_3yr': 0,
        
#         'total_citations_3yr': 0,
#         'avg_citations_per_paper_3yr': 0,
        
#         'avg_team_size_3yr': 0,
#         'avg_team_size_last_author_3yr': 0,
#         'avg_team_size_sdl_brown_3yr': 0,
#         'avg_team_size_sdl_tomet_3yr': 0,
#         'avg_team_size_high_automation_3yr': 0,
        
#         'top_field_3yr': '',
#         'top_field_paper_count_3yr': 0,
#         'num_unique_fields_3yr': 0,
#         'field_counts_3yr': '{}',
#         'author_profile_3yr': 'Unknown',
        
#         'top_topic_3yr': '',
#         'top_topic_paper_count_3yr': 0,
#         'num_unique_topics_3yr': 0,
        
#         'top_journal_3yr': '',
#         'top_journal_paper_count_3yr': 0,
#         'num_unique_journals_3yr': 0,
        
#         'has_cs_experience_3yr': 0,
        
#         'num_affiliations_3yr': 0,
#         'top_affiliation_3yr': '',
#     }


# # ============================================================================
# # GENERATE AUTHOR-YEAR RECORDS
# # ============================================================================

# def generate_author_year_records(all_author_papers):
#     """
#     For each author, create one row per year they published
#     Each row contains 3-year backward-looking metrics
#     """
    
#     print(f"\n{'='*70}")
#     print(f"GENERATING AUTHOR-YEAR RECORDS")
#     print(f"{'='*70}\n")
    
#     records = []
#     total_authors = len(all_author_papers)
    
#     for idx, (author_id, papers_list) in enumerate(all_author_papers.items()):
#         if (idx + 1) % 100000 == 0:
#             print(f"  Progress: {idx + 1:,} / {total_authors:,} authors processed", flush=True)
        
#         # Get all years this author published
#         years_published = sorted(set(p['year'] for p in papers_list))
        
#         # Create one record per year
#         for target_year in years_published:
#             metrics = compute_3yr_backward_metrics(author_id, papers_list, target_year)
#             records.append(metrics)
    
#     print(f"  ✓ Generated {len(records):,} author-year records\n")
    
#     return pd.DataFrame(records)


# # ============================================================================
# # MAIN EXECUTION
# # ============================================================================

# def main():
#     print("\n" + "="*70)
#     print("BUILDING 3-YEAR BACKWARD-LOOKING AUTHOR METRICS")
#     print("="*70)
#     print(f"Output: {OUTPUT_FILE}")
#     print(f"Using {NUM_CORES} cores")
#     print(f"CS Keywords: {CS_KEYWORDS_FILE}")
#     print(f"Years: {YEARS[0]}-{YEARS[-1]}")
#     print("="*70)
    
#     # Check Directories
#     fields_to_process = []
#     for name, path in FIELDS.items():
#         if path.exists(): 
#             fields_to_process.append((name, path))
#             print(f"  ✓ Found field: {name}")
#         else:
#             print(f"  ✗ Missing field: {name}")
    
#     if not fields_to_process:
#         print("\nError: No field directories found.")
#         return
    
#     print()
        
#     # Phase 1: Parallel Processing
#     tasks = [(name, path, year) for name, path in fields_to_process for year in YEARS]
#     print(f"{'='*70}")
#     print(f"PHASE 1: PROCESSING {len(tasks)} FILES IN PARALLEL")
#     print(f"{'='*70}\n")
    
#     start_time = time.time()
    
#     with mp.Pool(NUM_CORES) as pool:
#         results = pool.map(process_single_year_file, tasks)
    
#     # Track results
#     successful = 0
#     failed = 0
#     not_found = 0
    
#     for author_papers, file_name, status in results:
#         if status.startswith("SUCCESS"):
#             successful += 1
#             rows = status.split("_")[1]
#             if successful % 10 == 0:
#                 print(f"  ✓ Completed: {file_name} ({rows} rows)")
#         elif status == "FILE_NOT_FOUND":
#             not_found += 1
#         else:
#             failed += 1
#             print(f"  ✗ Failed: {file_name} - {status}")
    
#     elapsed = time.time() - start_time
    
#     print(f"\n{'='*70}")
#     print(f"PHASE 1 COMPLETE - {elapsed:.1f}s")
#     print(f"{'='*70}")
#     print(f"  Successful: {successful}")
#     print(f"  Not Found: {not_found}")
#     print(f"  Failed: {failed}")
#     print(f"{'='*70}\n")
    
#     # Phase 2: Merge
#     print(f"{'='*70}")
#     print(f"PHASE 2: MERGING AUTHOR PAPERS")
#     print(f"{'='*70}\n")
    
#     merge_start = time.time()
#     all_author_papers = {}
    
#     for idx, (author_papers, file_name, status) in enumerate(results):
#         if author_papers:
#             all_author_papers = merge_author_papers(all_author_papers, author_papers)
#         if (idx + 1) % 20 == 0:
#             print(f"  Merged {idx + 1}/{len(results)} files... ({len(all_author_papers):,} unique authors so far)")
    
#     merge_elapsed = time.time() - merge_start
    
#     print(f"\n  ✓ Merge complete - {merge_elapsed:.1f}s")
#     print(f"  Total unique authors: {len(all_author_papers):,}\n")
        
#     # Phase 3: Generate Author-Year Records
#     print(f"{'='*70}")
#     print(f"PHASE 3: COMPUTING 3-YEAR BACKWARD METRICS")
#     print(f"{'='*70}\n")
    
#     agg_start = time.time()
#     df = generate_author_year_records(all_author_papers)
#     agg_elapsed = time.time() - agg_start
    
#     print(f"  ✓ Computation complete - {agg_elapsed:.1f}s\n")
    
#     # Phase 4: Save
#     print(f"{'='*70}")
#     print(f"SAVING TO FILE")
#     print(f"{'='*70}\n")
    
#     df.to_csv(OUTPUT_FILE, index=False)
    
#     total_elapsed = time.time() - start_time
    
#     file_size = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    
#     print(f"  ✓ Saved {len(df):,} author-year records to:")
#     print(f"    {OUTPUT_FILE}")
#     print(f"  File size: {file_size:.1f} MB")
    
#     print(f"\n  Columns ({len(df.columns)}):")
#     for col in df.columns:
#         print(f"    - {col}")
    
#     # Summary Statistics
#     print(f"\n{'='*70}")
#     print(f"SUMMARY STATISTICS")
#     print(f"{'='*70}\n")
    
#     print(f"Total author-year records: {len(df):,}")
#     print(f"Unique authors: {df['author_id'].nunique():,}")
#     print(f"Year range: {df['year'].min()}-{df['year'].max()}")
    
#     print(f"\nPrior years availability:")
#     print(df['num_prior_years_available'].value_counts().sort_index().to_string())
    
#     print(f"\nRecords by year:")
#     print(df['year'].value_counts().sort_index().to_string())
    
#     print(f"\n{'='*70}")
#     print(f"COMPLETE - Total Time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
#     print(f"{'='*70}\n")

# if __name__ == "__main__":
#     main()

"""
Exploratory Data Analysis (EDA) for 3-Year Rolling Author Metrics Dataset
Adapted for author_metrics_3yr_rolling.csv output structure
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")
DATA_FILE = PROJECT_DIR / "data" / "yearly_data/test" / "author_metrics_3yr_rolling.csv"
OUTPUT_DIR = PROJECT_DIR / "data" / "yearly_data/test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "eda_author_3yr_rolling.txt"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_number(num):
    return f"{num:,}"

def format_percentage(num, total):
    if total == 0:
        return "0.00%"
    return f"{num/total*100:.2f}%"

def print_section(title, level=1):
    if level == 1:
        return f"\n{'='*80}\n{title}\n{'='*80}\n"
    elif level == 2:
        return f"\n{title}\n{'-'*80}\n"
    else:
        return f"\n{title}:\n"

def categorize_count(count, bins, labels):
    for i, (lower, upper) in enumerate(bins):
        if lower <= count < upper:
            return labels[i]
    return labels[-1]

# ============================================================================
# MAIN EDA FUNCTION
# ============================================================================

def generate_eda():
    print("Loading data... (this may take a minute due to size)")

    output = []
    output.append(print_section("EXPLORATORY DATA ANALYSIS - 3-YEAR ROLLING AUTHOR METRICS", 1))
    output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    output.append(f"Source file: {DATA_FILE}\n")
    output.append("="*80 + "\n")

    df = pd.read_csv(DATA_FILE, low_memory=False)

    # ========================================================================
    # 1. DATASET OVERVIEW
    # ========================================================================
    output.append(print_section("1. DATASET OVERVIEW", 1))

    total_records = len(df)
    unique_authors = df['author_id'].nunique()
    total_columns = len(df.columns)
    memory_mb = df.memory_usage(deep=True).sum() / (1024**2)

    output.append(f"Total author-year records: {format_number(total_records)}\n")
    output.append(f"Unique authors: {format_number(unique_authors)}\n")
    output.append(f"Total columns: {total_columns}\n")
    output.append(f"Memory usage: {memory_mb:.2f} MB\n")
    output.append(f"\nColumns:\n")
    for i, col in enumerate(df.columns, 1):
        output.append(f"  {i:2d}. {col}\n")

    # ========================================================================
    # 2. TEMPORAL COVERAGE
    # ========================================================================
    output.append(print_section("2. TEMPORAL COVERAGE", 1))

    year_min = df['year'].min()
    year_max = df['year'].max()
    year_range = year_max - year_min + 1

    output.append(f"Year range: {year_min}-{year_max} ({year_range} years)\n\n")
    output.append("Records by year:\n")
    year_counts = df['year'].value_counts().sort_index()
    for year, count in year_counts.items():
        output.append(f"  {year}: {format_number(count):>12s}\n")
    output.append(f"\nAverage records per year: {format_number(int(total_records / year_range))}\n")

    # ========================================================================
    # 3. PRIOR YEARS AVAILABILITY
    # ========================================================================
    output.append(print_section("3. PRIOR YEARS AVAILABILITY (DATA QUALITY)", 1))

    # FIX: num_prior_years_available = 0 means author published in year T but had
    # no papers in [T-3, T-2, T-1]. This is expected for first-year authors.
    prior_years_dist = df['num_prior_years_available'].value_counts().sort_index()
    output.append("Distribution of prior years available (0 = no prior data, up to 3 = full window):\n")
    for num_years, count in prior_years_dist.items():
        pct = format_percentage(count, total_records)
        label = "no prior data" if num_years == 0 else f"{num_years} prior year(s)"
        output.append(f"  {num_years} ({label}): {format_number(count):>12s} ({pct})\n")

    output.append("\nPrior years availability by publication year:\n")
    prior_by_year = df.groupby('year')['num_prior_years_available'].value_counts().unstack(fill_value=0)
    for year in sorted(df['year'].unique()):
        if year in prior_by_year.index:
            output.append(f"  {year}: ")
            for num_prior in sorted(prior_by_year.columns):
                count = prior_by_year.loc[year, num_prior]
                output.append(f"{num_prior}yr={format_number(count):>8s}  ")
            output.append("\n")

    # Records with FULL 3-year window vs partial
    full_window = (df['num_prior_years_available'] == 3).sum()
    partial_window = (df['num_prior_years_available'].between(1, 2)).sum()
    no_prior = (df['num_prior_years_available'] == 0).sum()

    output.append(f"\nSummary:\n")
    output.append(f"  Full 3-year window available: {format_number(full_window)} ({format_percentage(full_window, total_records)})\n")
    output.append(f"  Partial window (1-2 years):   {format_number(partial_window)} ({format_percentage(partial_window, total_records)})\n")
    output.append(f"  No prior data (0 years):      {format_number(no_prior)} ({format_percentage(no_prior, total_records)})\n")

    # ========================================================================
    # 4. MISSING VALUES ANALYSIS
    # ========================================================================
    output.append(print_section("4. MISSING VALUES ANALYSIS", 1))

    missing = df.isnull().sum()
    missing = missing[missing > 0].sort_values(ascending=False)

    if len(missing) > 0:
        output.append(f"Columns with missing values ({len(missing)} total):\n")
        for col, count in missing.items():
            pct = format_percentage(count, total_records)
            output.append(f"  {col}: {format_number(count)} ({pct})\n")
    else:
        output.append("  No missing values detected.\n")

    # ========================================================================
    # 5. PUBLICATION COUNTS STATISTICS (3-YEAR WINDOW)
    # ========================================================================
    output.append(print_section("5. PUBLICATION COUNTS STATISTICS (3-YEAR WINDOW)", 1))

    paper_cols = [
        'total_papers_3yr', 'first_author_papers_3yr', 'last_author_papers_3yr',
        'corresponding_author_papers_3yr', 'sdl_brown_papers_3yr', 'sdl_tomet_papers_3yr',
        'high_automation_papers_3yr', 'ai_papers_3yr', 'robotics_papers_3yr'
    ]
    paper_cols = [col for col in paper_cols if col in df.columns]

    output.append("Descriptive statistics:\n")
    output.append(df[paper_cols].describe().to_string() + "\n\n")

    # NOTE: Records where total_papers_3yr == 0 are authors publishing in year T
    # for the first time (no prior 3-year window). Showing distributions for
    # records WITH prior data only, for interpretability.
    has_prior = df[df['total_papers_3yr'] > 0]
    n_has_prior = len(has_prior)
    output.append(f"Records with prior papers in 3-year window: {format_number(n_has_prior)} "
                  f"({format_percentage(n_has_prior, total_records)})\n\n")

    output.append("Publication count distributions (3-year window, among records with prior data):\n\n")

    bins = [(0, 1), (1, 5), (5, 10), (10, 20), (20, 50), (50, 100), (100, 500), (500, 1000), (1000, float('inf'))]
    labels = ['0', '1-4', '5-9', '10-19', '20-49', '50-99', '100-499', '500-999', '1000+']

    for col in ['total_papers_3yr', 'first_author_papers_3yr', 'last_author_papers_3yr']:
        if col not in df.columns:
            continue

        output.append(f"{col}:\n")
        df['temp_cat'] = df[col].apply(lambda x: categorize_count(x, bins, labels))
        dist = df['temp_cat'].value_counts().reindex(labels, fill_value=0)

        for cat, count in dist.items():
            pct = format_percentage(count, total_records)
            output.append(f"  {cat:10s}: {format_number(count):>12s} ({pct})\n")
        output.append("\n")
        df.drop('temp_cat', axis=1, inplace=True)

    # ========================================================================
    # 6. CITATION STATISTICS (3-YEAR WINDOW)
    # ========================================================================
    output.append(print_section("6. CITATION STATISTICS (3-YEAR WINDOW)", 1))

    citation_cols = ['total_citations_3yr', 'avg_citations_per_paper_3yr']
    citation_cols = [col for col in citation_cols if col in df.columns]

    output.append(df[citation_cols].describe().to_string() + "\n\n")

    output.append("Citation milestones (3-year window):\n")
    if 'total_citations_3yr' in df.columns:
        for threshold in [0, 10, 100, 1000, 10000]:
            count = (df['total_citations_3yr'] >= threshold).sum()
            label = f"{threshold}" if threshold == 0 else f"{threshold}+"
            output.append(f"  Author-years with {label} citations: {format_number(count)}\n")

    # ========================================================================
    # 7. FIELD DISTRIBUTION (3-YEAR WINDOW)
    # ========================================================================
    output.append(print_section("7. FIELD DISTRIBUTION (3-YEAR WINDOW)", 1))

    if 'top_field_3yr' in df.columns:
        output.append("Author-years by top field (includes empty string for no-prior-data records):\n")
        field_dist = df['top_field_3yr'].fillna('').value_counts()
        output.append(field_dist.to_string() + "\n\n")

        # Among records with prior data only
        output.append("Author-years by top field (records WITH prior data only):\n")
        field_dist_prior = has_prior['top_field_3yr'].fillna('').value_counts()
        output.append(field_dist_prior.to_string() + "\n\n")

        if 'num_unique_fields_3yr' in df.columns:
            output.append("Multi-field activity (3-year window):\n")
            field_counts = df['num_unique_fields_3yr'].value_counts().sort_index()
            for num_fields, count in field_counts.items():
                pct = format_percentage(count, total_records)
                plural = "field" if num_fields == 1 else "fields"
                output.append(f"  {num_fields} {plural}: {format_number(count):>12s} ({pct})\n")

    # ========================================================================
    # 8. AUTHOR PROFILES (3-YEAR WINDOW)
    # ========================================================================
    output.append(print_section("8. AUTHOR PROFILES (3-YEAR WINDOW)", 1))

    if 'author_profile_3yr' in df.columns:
        output.append("Top 20 author profiles (all records):\n")
        profile_dist = df['author_profile_3yr'].fillna('Unknown').value_counts().head(20)
        output.append(profile_dist.to_string() + "\n\n")

        output.append("Top 20 author profiles (records WITH prior data only):\n")
        profile_dist_prior = has_prior['author_profile_3yr'].fillna('Unknown').value_counts().head(20)
        output.append(profile_dist_prior.to_string() + "\n")

    # ========================================================================
    # 9. LONGITUDINAL AUTHOR ANALYSIS
    # ========================================================================
    output.append(print_section("9. LONGITUDINAL AUTHOR ANALYSIS", 1))

    years_per_author = df.groupby('author_id')['year'].nunique()

    output.append("Distribution of observation years per author:\n")
    years_dist = years_per_author.value_counts().sort_index()
    for num_years, count in years_dist.head(22).items():
        pct = format_percentage(count, unique_authors)
        output.append(f"  {num_years:2d} year(s): {format_number(count):>10s} ({pct})\n")

    if len(years_dist) > 22:
        remaining = years_dist.iloc[22:].sum()
        output.append(f"  ... {format_number(int(remaining))} more\n")

    output.append(f"\nAverage years observed per author: {years_per_author.mean():.2f}\n")
    output.append(f"Median years observed per author: {years_per_author.median():.0f}\n")

    # FIX: Authors who appear in only 1 year — these are authors with no prior
    # window data AND no future data in the dataset. Distinguish from
    # single-year publishers by checking if they have total_papers_3yr > 0.
    one_year_authors = (years_per_author == 1).sum()
    output.append(f"\nAuthors observed in exactly 1 year: {format_number(one_year_authors)} "
                  f"({format_percentage(one_year_authors, unique_authors)})\n")
    output.append("  (These authors appear only once across all field-year files)\n")

    # ========================================================================
    # 10. TOP AUTHOR-YEAR RECORDS
    # ========================================================================
    output.append(print_section("10. TOP AUTHOR-YEAR RECORDS", 1))

    if 'total_papers_3yr' in df.columns:
        output.append(print_section("Top 20 most productive author-years (3-year window):", 2))
        cols_to_show = [c for c in ['author_name', 'year', 'num_prior_years_available',
                                     'total_papers_3yr', 'total_citations_3yr',
                                     'top_field_3yr', 'top_topic_3yr'] if c in df.columns]
        top_productive = df.nlargest(20, 'total_papers_3yr')[cols_to_show]
        output.append(top_productive.to_string(index=False) + "\n")

    if 'total_citations_3yr' in df.columns:
        output.append(print_section("Top 20 most cited author-years (3-year window):", 2))
        cols_to_show = [c for c in ['author_name', 'year', 'num_prior_years_available',
                                     'total_papers_3yr', 'total_citations_3yr',
                                     'avg_citations_per_paper_3yr', 'top_field_3yr'] if c in df.columns]
        top_cited = df.nlargest(20, 'total_citations_3yr')[cols_to_show]
        output.append(top_cited.to_string(index=False) + "\n")

    # ========================================================================
    # 11. SDL/AI/ROBOTICS INVOLVEMENT (3-YEAR WINDOW)
    # ========================================================================
    output.append(print_section("11. SDL/AI/ROBOTICS INVOLVEMENT (3-YEAR WINDOW)", 1))

    sdl_cols = {
        'sdl_brown_papers_3yr': 'SDL Brown',
        'sdl_tomet_papers_3yr': 'SDL Tomet',
        'high_automation_papers_3yr': 'High Automation',
        'ai_papers_3yr': 'AI',
        'robotics_papers_3yr': 'Robotics',
    }

    output.append("Author-years with at least 1 paper in category (3-year window):\n")
    for col, label in sdl_cols.items():
        if col in df.columns:
            count = (df[col] > 0).sum()
            pct = format_percentage(count, total_records)
            output.append(f"  {label}: {format_number(count)} ({pct})\n")

    # SDL trends over time
    output.append(print_section("SDL/AI/Robotics trends over time:", 2))

    for col, label in sdl_cols.items():
        if col not in df.columns:
            continue

        output.append(f"\n{label} ({col}) by year:\n")
        sdl_by_year = df.groupby('year')[col].agg(
            total_papers='sum',
            avg_per_author_year='mean',
            author_years_with_papers=lambda x: (x > 0).sum()
        )

        for year, row in sdl_by_year.iterrows():
            output.append(f"  {year}: Total={int(row['total_papers']):>6d}, "
                         f"Avg={row['avg_per_author_year']:>5.3f}, "
                         f"AuthorYears={int(row['author_years_with_papers']):>6d}\n")

    # Top SDL author-years
    if 'sdl_tomet_papers_3yr' in df.columns:
        output.append(print_section("Top 20 SDL author-years (by Tomet papers, 3-year window):", 2))
        sdl_display_cols = [c for c in ['author_name', 'year', 'num_prior_years_available',
                                         'total_papers_3yr', 'sdl_brown_papers_3yr',
                                         'sdl_tomet_papers_3yr', 'high_automation_papers_3yr',
                                         'top_field_3yr'] if c in df.columns]
        top_sdl = df[df['sdl_tomet_papers_3yr'] > 0].nlargest(20, 'sdl_tomet_papers_3yr')[sdl_display_cols]
        output.append(top_sdl.to_string(index=False) + "\n")

    # ========================================================================
    # 12. TEAM SIZE ANALYSIS (3-YEAR WINDOW)
    # ========================================================================
    output.append(print_section("12. TEAM SIZE ANALYSIS (3-YEAR WINDOW)", 1))

    team_size_cols = [
        'avg_team_size_3yr', 'avg_team_size_last_author_3yr',
        'avg_team_size_sdl_brown_3yr', 'avg_team_size_sdl_tomet_3yr',
        'avg_team_size_high_automation_3yr'
    ]
    team_size_cols = [col for col in team_size_cols if col in df.columns]

    output.append("Descriptive statistics (all records, including zeros for no-prior-data):\n")
    output.append(df[team_size_cols].describe().to_string() + "\n\n")

    # FIX: Zeros in avg_team_size_3yr mean no prior data, not actual team size of 0.
    # Show stats for non-zero values separately to avoid misleading means.
    output.append("Descriptive statistics (records where avg_team_size_3yr > 0 only):\n")
    non_zero_team = df[df['avg_team_size_3yr'] > 0]
    output.append(non_zero_team[team_size_cols].describe().to_string() + "\n\n")

    if 'avg_team_size_3yr' in df.columns:
        output.append("Distribution of Overall Avg Team Size (3-year window, non-zero only):\n")
        bins = [(0, 1), (1, 2), (2, 4), (4, 7), (7, 11), (11, 21), (21, float('inf'))]
        labels = ['<1', '1-2', '2-4', '4-7', '7-11', '11-20', '20+']
        n_nonzero = len(non_zero_team)

        non_zero_team = non_zero_team.copy()
        non_zero_team['temp_cat'] = non_zero_team['avg_team_size_3yr'].apply(
            lambda x: categorize_count(x, bins, labels))
        dist = non_zero_team['temp_cat'].value_counts().reindex(labels, fill_value=0)
        for cat, count in dist.items():
            pct = format_percentage(count, n_nonzero)
            output.append(f"  {cat:10s}: {format_number(count):>12s} ({pct})\n")

    output.append(print_section("Team size trends over time (mean among non-zero records):", 2))

    for col in ['avg_team_size_3yr', 'avg_team_size_last_author_3yr']:
        if col not in df.columns:
            continue

        output.append(f"\n{col} by year (non-zero records only):\n")
        non_zero_by_year = df[df[col] > 0].groupby('year')[col].agg(['mean', 'median', 'std', 'count'])

        for year, row in non_zero_by_year.iterrows():
            output.append(f"  {year}: Mean={row['mean']:>5.2f}, "
                         f"Median={row['median']:>5.2f}, "
                         f"Std={row['std']:>5.2f}, "
                         f"N={int(row['count']):>8,}\n")

    # ========================================================================
    # 13. CS EXPERIENCE ANALYSIS (3-YEAR WINDOW)
    # ========================================================================
    output.append(print_section("13. CS EXPERIENCE ANALYSIS (3-YEAR WINDOW)", 1))

    if 'has_cs_experience_3yr' in df.columns:
        cs_exp_count = (df['has_cs_experience_3yr'] == 1).sum()
        cs_exp_pct = format_percentage(cs_exp_count, total_records)
        output.append(f"Total author-years with CS experience (3yr window): {format_number(cs_exp_count)} ({cs_exp_pct})\n\n")

        if 'top_field_3yr' in df.columns:
            output.append("CS experience rate by top field:\n")
            cs_by_field = pd.crosstab(
                df['top_field_3yr'].fillna('Unknown'),
                df['has_cs_experience_3yr'],
                margins=True
            )
            cs_by_field.columns = [f'cs_exp={c}' for c in cs_by_field.columns]
            output.append(cs_by_field.to_string() + "\n")

    # ========================================================================
    # 14. HIGH AUTOMATION OVERLAP ANALYSIS
    # ========================================================================
    output.append(print_section("14. HIGH AUTOMATION OVERLAP ANALYSIS", 1))

    if 'high_automation_papers_3yr' in df.columns:
        high_auto_records = df[df['high_automation_papers_3yr'] > 0]
        n_high_auto = len(high_auto_records)

        output.append(f"Author-years with >=1 High Automation paper (3yr window): {format_number(n_high_auto)}\n\n")

        if n_high_auto > 0:
            output.append("Among High Automation author-years:\n")
            for col, label in [('sdl_brown_papers_3yr', 'SDL Brown'),
                                ('sdl_tomet_papers_3yr', 'SDL Tomet'),
                                ('ai_papers_3yr', 'AI'),
                                ('robotics_papers_3yr', 'Robotics')]:
                if col in df.columns:
                    overlap = (high_auto_records[col] > 0).sum()
                    output.append(f"  Also have {label} paper: {format_number(overlap)} "
                                  f"({format_percentage(overlap, n_high_auto)})\n")

            output.append("\nAvg Team Size Comparison (High Automation author-years, non-zero only):\n")
            for col, label in [('avg_team_size_3yr', 'Overall'),
                                ('avg_team_size_high_automation_3yr', 'On High Auto Papers'),
                                ('avg_team_size_last_author_3yr', 'As Last Author')]:
                if col in high_auto_records.columns:
                    non_zero_vals = high_auto_records[high_auto_records[col] > 0][col]
                    if len(non_zero_vals) > 0:
                        output.append(f"  {label}: mean={non_zero_vals.mean():.2f}, "
                                      f"median={non_zero_vals.median():.2f}\n")

    # ========================================================================
    # 15. YEAR-OVER-YEAR CHANGES (AUTHOR EVOLUTION)
    # ========================================================================
    output.append(print_section("15. YEAR-OVER-YEAR CHANGES (AUTHOR EVOLUTION)", 1))

    # Only authors with 2+ observed years AND prior data
    multi_year_ids = df.groupby('author_id').filter(
        lambda x: len(x) >= 2 and (x['total_papers_3yr'] > 0).any()
    )
    n_multi = multi_year_ids['author_id'].nunique()

    output.append(f"Authors with 2+ years of observation (and at least 1 year with prior data): "
                  f"{format_number(n_multi)}\n\n")

    if n_multi > 0:
        output.append("Average year-over-year changes:\n")

        for col in ['total_papers_3yr', 'total_citations_3yr', 'avg_team_size_3yr']:
            if col not in df.columns:
                continue

            # FIX: Use .copy() to avoid SettingWithCopyWarning
            sorted_df = multi_year_ids[['author_id', 'year', col]].sort_values(
                ['author_id', 'year']
            ).copy()

            # Only compute change where BOTH years have non-zero values
            # (zeros indicate no prior data, not true zeros)
            sorted_df['prev_val'] = sorted_df.groupby('author_id')[col].shift(1)
            valid_mask = (sorted_df[col] > 0) & (sorted_df['prev_val'] > 0)
            sorted_df['yoy_change'] = np.where(
                valid_mask,
                (sorted_df[col] - sorted_df['prev_val']) / sorted_df['prev_val'] * 100,
                np.nan
            )

            valid_changes = sorted_df['yoy_change'].dropna()
            # Clip extreme outliers
            valid_changes = valid_changes[valid_changes.between(-100, 1000)]

            if len(valid_changes) > 0:
                output.append(f"\n  {col}:\n")
                output.append(f"    N transitions: {format_number(len(valid_changes))}\n")
                output.append(f"    Mean change:   {valid_changes.mean():>6.2f}%\n")
                output.append(f"    Median change: {valid_changes.median():>6.2f}%\n")
                output.append(f"    Std dev:       {valid_changes.std():>6.2f}%\n")
                output.append(f"    % increasing:  {format_percentage((valid_changes > 0).sum(), len(valid_changes))}\n")
                output.append(f"    % decreasing:  {format_percentage((valid_changes < 0).sum(), len(valid_changes))}\n")

    # ========================================================================
    # 16. AFFILIATIONS ANALYSIS (3-YEAR WINDOW)
    # ========================================================================
    output.append(print_section("16. AFFILIATIONS ANALYSIS (3-YEAR WINDOW)", 1))

    if 'num_affiliations_3yr' in df.columns:
        output.append("Affiliations per author-year (3-year window):\n")
        output.append(df['num_affiliations_3yr'].describe().to_string() + "\n\n")

        aff_dist = df['num_affiliations_3yr'].value_counts().sort_index().head(15)
        output.append("Distribution (top 15 values):\n")
        for n_aff, count in aff_dist.items():
            pct = format_percentage(count, total_records)
            output.append(f"  {n_aff} affiliation(s): {format_number(count):>10s} ({pct})\n")

    # ========================================================================
    # FOOTER
    # ========================================================================
    output.append("\n" + "="*80 + "\n")
    output.append("END OF REPORT\n")
    output.append("="*80 + "\n")

    with open(OUTPUT_FILE, 'w') as f:
        f.writelines(output)

    print(''.join(output))
    print(f"\n\nReport saved to: {OUTPUT_FILE}")
    print(f"File size: {OUTPUT_FILE.stat().st_size / 1024:.2f} KB")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print(f"\nStarting EDA for 3-Year Rolling Author Metrics...")
    print(f"Data file: {DATA_FILE}\n")

    if not DATA_FILE.exists():
        print(f"ERROR: Data file not found: {DATA_FILE}")
        exit(1)

    generate_eda()
    print("\n✓ EDA Complete!")