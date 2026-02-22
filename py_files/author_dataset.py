## AUTHOR DATASET CREATION WITH NEW DATA 
"""
Build comprehensive author-level dataset from paper TSV files

The ouput file contains every author in the fields datasets and metrics about their publication history.
"""
import pandas as pd
import json
from collections import Counter
import numpy as np
from pathlib import Path
import multiprocessing as mp
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

# Path to Keywords
CS_KEYWORDS_FILE = PROJECT_DIR / "data/lasso_regression" / "cs_keywords_shortlisted.txt"

OUTPUT_DIR = PROJECT_DIR / "data" / "author/test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "author_metrics.csv"

YEARS = range(2004, 2026) 
CHUNK_SIZE = 500000
NUM_CORES = 10

# ============================================================================
# HELPER FUNCTIONS (CS Keyword Matching)
# ============================================================================

def load_cs_keywords(file_path):
    """Load CS keywords from text file"""
    if not file_path.exists():
        return set()
    with open(file_path, 'r', encoding='utf-8') as f:
        keywords = set(line.strip().lower() for line in f 
                      if line.strip() and not line.strip().startswith('#'))
    return keywords

def check_cs_keyword_match(primary_topic, all_topics, title, abstract, cs_keywords_set):
    """
    Check if at least 2 different CS keywords match.
    Returns True if match found.
    """
    if not cs_keywords_set:
        return False
        
    matched_keywords = set()
    
    # Check primary topic
    if primary_topic:
        primary_lower = primary_topic.lower()
        for keyword in cs_keywords_set:
            if keyword in primary_lower:
                matched_keywords.add(keyword)
                if len(matched_keywords) >= 2: return True
    
    # Check all topics (list of strings)
    if all_topics:
        for t in all_topics:
            t_lower = t.lower()
            for keyword in cs_keywords_set:
                if keyword in t_lower:
                    matched_keywords.add(keyword)
                    if len(matched_keywords) >= 2: return True
    
    # Check title
    if title and isinstance(title, str):
        title_lower = title.lower()
        for keyword in cs_keywords_set:
            if keyword in title_lower:
                matched_keywords.add(keyword)
                if len(matched_keywords) >= 2: return True
    
    # Check abstract
    if abstract and isinstance(abstract, str):
        abstract_lower = abstract.lower()
        for keyword in cs_keywords_set:
            if keyword in abstract_lower:
                matched_keywords.add(keyword)
                if len(matched_keywords) >= 2: return True
    
    return len(matched_keywords) >= 2

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
            author_id = author.get('id', '').replace('https://openalex.org/', '')
            if not author_id: continue
            
            institutions = []
            for inst in authorship.get('institutions', []):
                inst_id = inst.get('id', '').replace('https://openalex.org/', '')
                if inst_id: institutions.append(inst_id)
            
            result.append({
                'author_id': author_id,
                'author_name': author.get('display_name', ''),
                'position': idx,
                'is_first': (idx == 0),
                'is_last': (idx == num_authors - 1),
                'institutions': institutions
            })
        return result
    except:
        return []

def parse_metadata_for_cs(raw_data_json):
    """Extract metadata needed for CS checking (topics, title, abstract)"""
    if pd.isna(raw_data_json) or raw_data_json == '':
        return None, [], None, None
    try:
        data = json.loads(raw_data_json)
        
        # Topics
        topics = data.get('topics', [])
        primary_topic = topics[0].get('display_name') if topics else None
        all_topics = [t.get('display_name') for t in topics if t.get('display_name')]
        
        title = data.get('title', '')
        
        # Reconstruct Abstract
        abstract_text = None
        abstract_inverted = data.get('abstract_inverted_index')
        if abstract_inverted:
            word_positions = []
            for word, positions in abstract_inverted.items():
                for pos in positions:
                    word_positions.append((pos, word))
            word_positions.sort(key=lambda x: x[0])
            abstract_text = ' '.join([word for pos, word in word_positions])
            
        return primary_topic, all_topics, title, abstract_text
    except:
        return None, [], None, None

def parse_journal(raw_data_json):
    if pd.isna(raw_data_json) or raw_data_json == '': return None
    try:
        data = json.loads(raw_data_json)
        return data.get('primary_location', {}).get('source', {}).get('display_name')
    except: return None

def parse_corresponding_author_ids(raw_data_json):
    if pd.isna(raw_data_json) or raw_data_json == '': return []
    try:
        data = json.loads(raw_data_json)
        return [aid.replace('https://openalex.org/', '') for aid in data.get('corresponding_author_ids', []) if aid]
    except: return []

def parse_cited_by_count(raw_data_json):
    if pd.isna(raw_data_json) or raw_data_json == '': return 0
    try:
        data = json.loads(raw_data_json)
        return data.get('cited_by_count', 0) or 0
    except: return 0

# ============================================================================
# AUTHOR DATA STRUCTURE
# ============================================================================

def create_author_entry():
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
        'robotics_count': 0,
        'has_cs_exp': False,
        
        # TEAM SIZE ACCUMULATORS
        'team_size_sum': 0,             # For overall avg
        'team_size_sum_last_author': 0, # For managerial avg
        
        # SEPARATED SDL METRICS
        'sdl_brown_count': 0,           # Brown SDL papers
        'sdl_tomet_count': 0,           # Tomet et al SDL papers
        'team_size_sum_sdl_brown': 0,   # Team size on Brown SDL papers
        'team_size_sum_sdl_tomet': 0,   # Team size on Tomet SDL papers
        
        # HIGH AUTOMATION METRICS
        'high_automation_count': 0,           # High automation papers
        'team_size_sum_high_automation': 0    # Team size on high automation papers
    }

# ============================================================================
# SINGLE YEAR PROCESSING
# ============================================================================

def process_single_year_file(args):
    """Process a single year file for a given field"""
    field_name, field_dir, year = args
    
    # Locate file - check both classified and original naming
    possible_files = [
        field_dir / f"{field_name}_{year}_sdl_classified.tsv",
        field_dir / f"{field_name}_{year}.tsv",
    ]
    tsv_file = next((f for f in possible_files if f.exists()), None)
    
    if not tsv_file: 
        return {}, f"{field_name}_{year}", "FILE_NOT_FOUND"
    
    # Load CS Keywords (once per process)
    cs_keywords = load_cs_keywords(CS_KEYWORDS_FILE)
    
    author_data = {}
    rows_processed = 0
    
    try:
        # Check available columns
        sample = pd.read_csv(tsv_file, sep='\t', nrows=5)
        available_cols = set(sample.columns)
        
        # Required columns
        required = ['raw_data', 'author_count', 
                   'brown_SDL_papers', 'tomet_al_SDL',
                   'high_automation_dummy',
                   'AI_Paper', 'Robotics_Paper']
        
        columns_to_read = [col for col in required if col in available_cols]
        
        if 'raw_data' not in columns_to_read: 
            return {}, f"{field_name}_{year}", "NO_RAW_DATA"
        
        for chunk in pd.read_csv(tsv_file, sep='\t', usecols=columns_to_read,
                                chunksize=CHUNK_SIZE, low_memory=False,
                                on_bad_lines='skip'):
            
            for _, row in chunk.iterrows():
                rows_processed += 1
                try:
                    raw = row.get('raw_data')
                    authorships = parse_authorships(raw)
                    if not authorships: continue
                    
                    # Metadata Extraction
                    citations = parse_cited_by_count(raw)
                    
                    # SEPARATED SDL FLAGS
                    is_sdl_brown = row.get('brown_SDL_papers', 0) == 1
                    is_sdl_tomet = row.get('tomet_al_SDL', 0) == 1
                    is_sdl_any = is_sdl_brown or is_sdl_tomet
                    
                    # HIGH AUTOMATION FLAG
                    is_high_automation = row.get('high_automation_dummy', 0) == 1
                    
                    is_ai = row.get('AI_Paper', 0) == 1
                    is_robotics = row.get('Robotics_Paper', 0) == 1
                    
                    # Extract Team Size 
                    team_size = row.get('author_count', 0)
                    if pd.isna(team_size): team_size = 0
                    
                    # Topic/Journal for existing metrics
                    primary_topic, all_topics, title, abstract = parse_metadata_for_cs(raw)
                    journal = parse_journal(raw)
                    corresponding_ids = parse_corresponding_author_ids(raw)
                    
                    # Check CS Experience
                    is_cs_paper = False
                    if field_name == 'computer_science':
                        is_cs_paper = True
                    else:
                        is_cs_paper = check_cs_keyword_match(primary_topic, all_topics, title, abstract, cs_keywords)
                    
                    for authorship in authorships:
                        author_id = authorship['author_id']
                        if author_id not in author_data:
                            author_data[author_id] = create_author_entry()
                        
                        data = author_data[author_id]
                        
                        # Accumulate Basic Data
                        data['names'].append(authorship['author_name'])
                        data['citations_list'].append(citations)
                        data['citation_sum'] += citations
                        data['fields'].append(field_name)
                        
                        if primary_topic: data['topics'].append(primary_topic)
                        if journal: data['journals'].append(journal)
                        data['affiliations'].update(authorship['institutions'])
                        
                        data['paper_count'] += 1
                        if authorship['is_first']: data['first_author_count'] += 1
                        if authorship['is_last']: data['last_author_count'] += 1
                        if author_id in corresponding_ids: data['corresponding_author_count'] += 1
                        
                        if is_sdl_any: data['sdl_count'] += 1
                        if is_ai: data['ai_count'] += 1
                        if is_robotics: data['robotics_count'] += 1
                        if is_high_automation: data['high_automation_count'] += 1
                        
                        if is_cs_paper: data['has_cs_exp'] = True

                        # --- TEAM SIZE ACCUMULATION ---
                        # 1. Overall Team Size Sum
                        data['team_size_sum'] += team_size
                        
                        # 2. Team Size as Last Author (Managerial Proxy)
                        if authorship['is_last']:
                            data['team_size_sum_last_author'] += team_size
                            
                        # 3. SEPARATED SDL METRICS
                        if is_sdl_brown:
                            data['sdl_brown_count'] += 1
                            data['team_size_sum_sdl_brown'] += team_size
                            
                        if is_sdl_tomet:
                            data['sdl_tomet_count'] += 1
                            data['team_size_sum_sdl_tomet'] += team_size
                            
                        # 4. HIGH AUTOMATION METRICS
                        if is_high_automation:
                            data['team_size_sum_high_automation'] += team_size
                            
                except: 
                    continue
                    
        return author_data, f"{field_name}_{year}", f"SUCCESS_{rows_processed}"
        
    except Exception as e:
        return {}, f"{field_name}_{year}", f"ERROR_{str(e)}"

# ============================================================================
# MERGE DICTIONARIES
# ============================================================================

def merge_author_dicts(dict1, dict2):
    """Merge two author data dictionaries"""
    for author_id, data2 in dict2.items():
        if author_id not in dict1:
            dict1[author_id] = data2
        else:
            data1 = dict1[author_id]
            data1['names'].extend(data2['names'])
            data1['citations_list'].extend(data2['citations_list'])
            data1['fields'].extend(data2['fields'])
            data1['topics'].extend(data2['topics'])
            data1['journals'].extend(data2['journals'])
            data1['affiliations'].update(data2['affiliations'])
            
            data1['paper_count'] += data2['paper_count']
            data1['first_author_count'] += data2['first_author_count']
            data1['last_author_count'] += data2['last_author_count']
            data1['corresponding_author_count'] += data2['corresponding_author_count']
            data1['citation_sum'] += data2['citation_sum']
            data1['sdl_count'] += data2['sdl_count']
            data1['ai_count'] += data2['ai_count']
            data1['robotics_count'] += data2['robotics_count']
            data1['high_automation_count'] += data2['high_automation_count']
            
            if data2['has_cs_exp']: data1['has_cs_exp'] = True
            
            # Merge Team Size Accumulators
            data1['team_size_sum'] += data2['team_size_sum']
            data1['team_size_sum_last_author'] += data2['team_size_sum_last_author']
            
            # Merge Separated SDL Metrics
            data1['sdl_brown_count'] += data2['sdl_brown_count']
            data1['sdl_tomet_count'] += data2['sdl_tomet_count']
            data1['team_size_sum_sdl_brown'] += data2['team_size_sum_sdl_brown']
            data1['team_size_sum_sdl_tomet'] += data2['team_size_sum_sdl_tomet']
            
            # Merge High Automation Metrics
            data1['team_size_sum_high_automation'] += data2['team_size_sum_high_automation']
                
    return dict1

# ============================================================================
# AGGREGATION
# ============================================================================

def aggregate_author_metrics(all_author_data):
    """Convert accumulated data into final metrics"""
    
    print(f"\n{'='*70}")
    print(f"AGGREGATING METRICS FOR {len(all_author_data):,} AUTHORS")
    print(f"{'='*70}")
    
    rows = []
    
    for idx, (author_id, data) in enumerate(all_author_data.items()):
        if (idx + 1) % 100000 == 0:
            print(f"  Progress: {idx + 1:,} / {len(all_author_data):,} authors processed", flush=True)
        
        # Basic Stats
        author_name = Counter(data['names']).most_common(1)[0][0] if data['names'] else ''
        total_papers = data['paper_count']
        
        # --- TEAM SIZE CALCULATIONS ---
        
        # 1. Avg Team Size (Overall)
        avg_team_size = 0
        if total_papers > 0:
            avg_team_size = data['team_size_sum'] / total_papers
            
        # 2. Avg Team Size (Last Author)
        avg_team_size_last = 0
        last_papers = data['last_author_count']
        if last_papers > 0:
            avg_team_size_last = data['team_size_sum_last_author'] / last_papers
            
        # 3. SEPARATED SDL TEAM SIZES
        avg_team_size_sdl_brown = 0
        if data['sdl_brown_count'] > 0:
            avg_team_size_sdl_brown = data['team_size_sum_sdl_brown'] / data['sdl_brown_count']
            
        avg_team_size_sdl_tomet = 0
        if data['sdl_tomet_count'] > 0:
            avg_team_size_sdl_tomet = data['team_size_sum_sdl_tomet'] / data['sdl_tomet_count']
            
        # 4. HIGH AUTOMATION TEAM SIZE
        avg_team_size_high_automation = 0
        if data['high_automation_count'] > 0:
            avg_team_size_high_automation = data['team_size_sum_high_automation'] / data['high_automation_count']

        # Field Analysis
        field_counter = Counter(data['fields'])
        
        # Top Field
        if data['fields']:
            top_field_name, top_field_count = field_counter.most_common(1)[0]
            num_unique_fields = len(field_counter)
        else:
            top_field_name, top_field_count, num_unique_fields = '', 0, 0
            
        # Field Dict
        field_counts_str = str(dict(field_counter))
        
        # Author Profile
        core_fields = []
        for field, count in field_counter.items():
            if count >= 2 and (count / total_papers) > 0.10:
                core_fields.append(field)
        
        core_fields.sort()
        
        if len(core_fields) == 0:
            author_profile = f"{top_field_name}_Only" if top_field_name else "Unknown"
        elif len(core_fields) == 1:
            author_profile = f"{core_fields[0]}_Only"
        elif len(core_fields) == 2:
            author_profile = "+".join(core_fields)
        else:
            author_profile = "Generalist"
            
        # Top Topic
        if data['topics']:
            topic_counter = Counter(data['topics'])
            top_topic_name, top_topic_count = topic_counter.most_common(1)[0]
            num_unique_topics = len(topic_counter)
        else:
            top_topic_name, top_topic_count, num_unique_topics = '', 0, 0
            
        # Top Journal
        if data['journals']:
            journal_counter = Counter(data['journals'])
            top_journal_name, top_journal_count = journal_counter.most_common(1)[0]
            num_unique_journals = len(journal_counter)
        else:
            top_journal_name, top_journal_count, num_unique_journals = '', 0, 0

        rows.append({
            'author_id': author_id,
            'author_name': author_name,
            'total_papers': total_papers,
            'first_author_papers': data['first_author_count'],
            'last_author_papers': data['last_author_count'],
            'corresponding_author_papers': data['corresponding_author_count'],
            'total_citations': int(data['citation_sum']),
            'avg_citations_per_paper': round(np.mean(data['citations_list']) if data['citations_list'] else 0, 2),
            
            # --- TEAM SIZE VARIABLES ---
            'avg_team_size': round(avg_team_size, 2),
            'avg_team_size_last_author': round(avg_team_size_last, 2),
            
            # --- SEPARATED SDL METRICS ---
            'avg_team_size_sdl_brown': round(avg_team_size_sdl_brown, 2),
            'avg_team_size_sdl_tomet': round(avg_team_size_sdl_tomet, 2),
            'sdl_brown_papers': data['sdl_brown_count'],
            'sdl_tomet_papers': data['sdl_tomet_count'],
            
            # --- HIGH AUTOMATION METRICS ---
            'avg_team_size_high_automation': round(avg_team_size_high_automation, 2),
            'high_automation_papers': data['high_automation_count'],
            
            # Field Vars
            'top_field': top_field_name,
            'top_field_paper_count': top_field_count,
            'num_unique_fields': num_unique_fields,
            'field_counts': field_counts_str,
            'author_profile': author_profile,
            
            # CS Experience
            'has_cs_experience': 1 if data['has_cs_exp'] else 0,
            
            # Other Metrics
            'top_topic': top_topic_name,
            'top_topic_paper_count': top_topic_count,
            'num_unique_topics': num_unique_topics,
            'top_journal': top_journal_name,
            'top_journal_paper_count': top_journal_count,
            'num_unique_journals': num_unique_journals,
            'num_affiliations': len(data['affiliations']),
            'top_affiliation': list(data['affiliations'])[0] if data['affiliations'] else '',
            'sdl_papers': data['sdl_count'],  # Total SDL (Brown OR Tomet)
            'ai_papers': data['ai_count'],
            'robotics_papers': data['robotics_count']
        })
    
    print(f"  ✓ Completed aggregation for all {len(all_author_data):,} authors\n")
    
    return pd.DataFrame(rows)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("\n" + "="*70)
    print("BUILDING AUTHOR-LEVEL DATASET")
    print("="*70)
    print(f"Output: {OUTPUT_FILE}")
    print(f"Using {NUM_CORES} cores")
    print(f"CS Keywords: {CS_KEYWORDS_FILE}")
    print(f"Years: {YEARS[0]}-{YEARS[-1]}")
    print("="*70)
    
    # Check Directories
    fields_to_process = []
    for name, path in FIELDS.items():
        if path.exists(): 
            fields_to_process.append((name, path))
            print(f"  ✓ Found field: {name}")
        else:
            print(f"  ✗ Missing field: {name}")
    
    if not fields_to_process:
        print("\nError: No field directories found.")
        return
    
    print()
        
    # Phase 1: Parallel Processing
    tasks = [(name, path, year) for name, path in fields_to_process for year in YEARS]
    print(f"{'='*70}")
    print(f"PHASE 1: PROCESSING {len(tasks)} FILES IN PARALLEL")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    with mp.Pool(NUM_CORES) as pool:
        results = pool.map(process_single_year_file, tasks)
    
    # Track results
    successful = 0
    failed = 0
    not_found = 0
    
    for author_dict, file_name, status in results:
        if status.startswith("SUCCESS"):
            successful += 1
            rows = status.split("_")[1]
            if successful % 10 == 0:
                print(f"  ✓ Completed: {file_name} ({rows} rows)")
        elif status == "FILE_NOT_FOUND":
            not_found += 1
        else:
            failed += 1
            print(f"  ✗ Failed: {file_name} - {status}")
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*70}")
    print(f"PHASE 1 COMPLETE - {elapsed:.1f}s")
    print(f"{'='*70}")
    print(f"  Successful: {successful}")
    print(f"  Not Found: {not_found}")
    print(f"  Failed: {failed}")
    print(f"{'='*70}\n")
    
    # Phase 2: Merge
    print(f"{'='*70}")
    print(f"PHASE 2: MERGING AUTHOR DATA")
    print(f"{'='*70}\n")
    
    merge_start = time.time()
    all_author_data = {}
    
    for idx, (author_dict, file_name, status) in enumerate(results):
        if author_dict:
            all_author_data = merge_author_dicts(all_author_data, author_dict)
        if (idx + 1) % 20 == 0:
            print(f"  Merged {idx + 1}/{len(results)} files... ({len(all_author_data):,} unique authors so far)")
    
    merge_elapsed = time.time() - merge_start
    
    print(f"\n  ✓ Merge complete - {merge_elapsed:.1f}s")
    print(f"  Total unique authors: {len(all_author_data):,}\n")
        
    # Phase 3: Aggregate
    print(f"{'='*70}")
    print(f"PHASE 3: COMPUTING FINAL METRICS")
    print(f"{'='*70}\n")
    
    agg_start = time.time()
    df = aggregate_author_metrics(all_author_data)
    agg_elapsed = time.time() - agg_start
    
    print(f"  ✓ Aggregation complete - {agg_elapsed:.1f}s\n")
    
    # Save
    print(f"{'='*70}")
    print(f"SAVING TO FILE")
    print(f"{'='*70}\n")
    
    df.to_csv(OUTPUT_FILE, index=False)
    
    total_elapsed = time.time() - start_time
    
    print(f"  ✓ Saved {len(df):,} authors to:")
    print(f"    {OUTPUT_FILE}")
    print(f"\n  Columns ({len(df.columns)}):")
    for col in df.columns:
        print(f"    - {col}")
    
    print(f"\n{'='*70}")
    print(f"COMPLETE - Total Time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()

