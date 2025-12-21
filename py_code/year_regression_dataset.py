import json, pandas as pd
import numpy as np
from pathlib import Path
import sys
from multiprocessing import Pool, cpu_count

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

FIELDS = {
    'chemistry': PROJECT_DIR / "data/fields" / "chemistry",
    'materials_science': PROJECT_DIR / "data/fields" / "material_science", 
    'engineering': PROJECT_DIR / "data/fields" / "engineering",
    'computer_science': PROJECT_DIR / "data/fields" / "computer_science"
}

AUTHOR_METRICS_FILE = PROJECT_DIR / "data" / "yearly_data/test" / "author_metrics_yearly.csv"
CS_KEYWORDS_FILE = PROJECT_DIR / "data/lasso_regression" / "cs_keywords_shortlisted.txt"  # Computer science keywords file

# --- SDL FILTER CONFIGURATION ---
SDL_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_journals.txt"
SDL_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_primary_topics.txt"

FILTER_CONFIG = {
    'use_journal_filter': True,
    'use_topic_filter': True,
}
# -----------------------------------------------------------

OUTPUT_DIR = PROJECT_DIR / "data" / "yearly_data/test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = range(2012, 2026)
CHUNK_SIZE = 500000

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_cs_keywords(file_path):
    """Load CS keywords from text file into a set for fast lookup, skip commented lines"""
    with open(file_path, 'r', encoding='utf-8') as f:
        keywords = set(line.strip().lower() for line in f 
                      if line.strip() and not line.strip().startswith('#'))
    return keywords


def check_cs_keyword_match(primary_topic, all_topics_str, title, abstract, cs_keywords_set):
    """
    Check if at least 2 different CS keywords match in topics, title, or abstract.
    Returns 1 if >= 2 different keywords found, 0 otherwise.
    """
    matched_keywords = set()
    
    # Check primary topic
    if primary_topic:
        primary_lower = primary_topic.lower()
        for keyword in cs_keywords_set:
            if keyword in primary_lower:
                matched_keywords.add(keyword)
                if len(matched_keywords) >= 2:
                    return 1
    
    # Check all topics
    if all_topics_str:
        all_topics_lower = all_topics_str.lower()
        for keyword in cs_keywords_set:
            if keyword in all_topics_lower:
                matched_keywords.add(keyword)
                if len(matched_keywords) >= 2:
                    return 1
    
    # Check title
    if title and isinstance(title, str):
        title_lower = title.lower()
        for keyword in cs_keywords_set:
            if keyword in title_lower:
                matched_keywords.add(keyword)
                if len(matched_keywords) >= 2:
                    return 1
    
    # Check abstract
    if abstract and isinstance(abstract, str):
        abstract_lower = abstract.lower()
        for keyword in cs_keywords_set:
            if keyword in abstract_lower:
                matched_keywords.add(keyword)
                if len(matched_keywords) >= 2:
                    return 1
    
    # Return 1 if at least 2 different keywords matched, 0 otherwise
    return 1 if len(matched_keywords) >= 2 else 0


def clean_author_id(author_id):
    """Remove URL prefix from author ID for lookup"""
    if pd.isna(author_id) or author_id == '':
        return None
    return str(author_id).replace('https://openalex.org/', '')


def parse_authorships(raw_data_json):
    """Extract first and last author IDs from raw_data"""
    if pd.isna(raw_data_json) or raw_data_json == '':
        return None, None
    
    try:
        data = json.loads(raw_data_json)
        authorships = data.get('authorships', [])
        
        if not authorships:
            return None, None
        
        first_author_id = clean_author_id(authorships[0].get('author', {}).get('id'))
        last_author_id = clean_author_id(authorships[-1].get('author', {}).get('id'))
        
        return first_author_id, last_author_id
    
    except:
        return None, None


def parse_corresponding_authors(raw_data_json):
    """Extract corresponding author IDs and select primary one"""
    if pd.isna(raw_data_json) or raw_data_json == '':
        return None, []
    
    try:
        data = json.loads(raw_data_json)
        corr_ids = data.get('corresponding_author_ids', [])
        
        if not corr_ids:
            return None, []
        
        # Clean IDs
        cleaned_ids = [clean_author_id(aid) for aid in corr_ids if aid]
        
        # Primary corresponding = first one in list
        primary_corr = cleaned_ids[0] if cleaned_ids else None
        
        return primary_corr, cleaned_ids
    
    except:
        return None, []


def parse_paper_metadata(raw_data_json):
    """Extract topics (primary + all), journal, citations, affiliations count, publication date, abstract"""
    if pd.isna(raw_data_json) or raw_data_json == '':
        return None, None, None, 0, 0, None, None
    
    try:
        data = json.loads(raw_data_json)
        
        # Topics - get ALL topics
        topics = data.get('topics', [])
        primary_topic = topics[0].get('display_name') if topics else None
        
        # Extract all topic names as a list
        all_topics = [t.get('display_name') for t in topics if t.get('display_name')]
        # Convert to pipe-separated string for CSV storage
        all_topics_str = '|'.join(all_topics) if all_topics else None
        
        # Journal
        journal = data.get('primary_location', {}).get('source', {}).get('display_name')
        
        # Citations
        cited_by_count = data.get('cited_by_count', 0) or 0
        
        # Publication date
        publication_date = data.get('publication_date')
        
        # Abstract - convert from inverted index to paragraph form
        abstract_text = None
        abstract_inverted = data.get('abstract_inverted_index')
        if abstract_inverted:
            # Inverted index format: {"word": [position1, position2, ...]}
            # Need to reconstruct the original text
            word_positions = []
            for word, positions in abstract_inverted.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            # Sort by position and join words
            word_positions.sort(key=lambda x: x[0])
            abstract_text = ' '.join([word for pos, word in word_positions])
        
        # Count unique affiliations
        authorships = data.get('authorships', [])
        all_institutions = set()
        for authorship in authorships:
            for inst in authorship.get('institutions', []):
                inst_id = inst.get('id')
                if inst_id:
                    all_institutions.add(inst_id)
        
        num_paper_affiliations = len(all_institutions)
        
        return primary_topic, all_topics_str, journal, cited_by_count, num_paper_affiliations, publication_date, abstract_text
    
    except:
        return None, None, None, 0, 0, None, None


def get_corresponding_position(first_id, last_id, corr_id, corr_ids_list):
    """Determine position of corresponding author"""
    if not corr_id:
        return 'missing'
    
    if first_id == last_id:  # Single author
        return 'only'
    
    # Check if first or last
    is_first = (corr_id == first_id)
    is_last = (corr_id == last_id)
    
    if is_first and is_last:
        return 'both'
    elif is_first:
        return 'first'
    elif is_last:
        return 'last'
    else:
        return 'middle'


# ============================================================================
# PARALLEL PROCESSING FUNCTION (YEAR-LEVEL)
# ============================================================================
def process_field_year(args):
    """Process a single (field, year) combination - designed to run in parallel"""
    field_name, field_dir, year, author_metrics_path, cs_keywords_path = args
    
    tsv_file = field_dir / f"{field_name}_{year}.tsv"
    
    if not tsv_file.exists():
        return field_name, year, [], 0, 0
    
    # Load YEARLY author metrics (each process gets its own copy)
    # Key change: we now have (author_id, year) as the index
    author_df = pd.read_csv(author_metrics_path)
    # Create multi-index for fast lookup by (author_id, year)
    author_df = author_df.set_index(['author_id', 'year'])
    
    # Load CS keywords (each process gets its own copy)
    cs_keywords = load_cs_keywords(cs_keywords_path)
    
    papers = []
    total = 0
    skipped = 0
    
    try:
        # Read in chunks
        for chunk in pd.read_csv(
            tsv_file, 
            sep='\t',
            usecols=['article_id', 'doi', 'title', 
                     'publication_year', 'author_count', 'SDL', 
                     'AI_Paper', 'Robotics_Paper', 'raw_data'],
            chunksize=CHUNK_SIZE,
            low_memory=False,
            on_bad_lines='skip'
        ):
            
            for _, row in chunk.iterrows():
                
                try:
                    # Get publication year for this paper
                    pub_year = row['publication_year']
                    
                    # Parse authorships
                    first_author_id, last_author_id = parse_authorships(row['raw_data'])
                    
                    if not first_author_id or not last_author_id:
                        skipped += 1
                        continue
                    
                    # Parse corresponding authors
                    primary_corr_id, all_corr_ids = parse_corresponding_authors(row['raw_data'])
                    
                    # Parse paper metadata (INCLUDES ABSTRACT)
                    primary_topic, all_topics_str, journal, cited_by_count, num_affiliations, publication_date, abstract = \
                        parse_paper_metadata(row['raw_data'])
                    
                    # Get title from row
                    title = row.get('title', '')
                    
                    # Determine CS experience for paper using KEYWORD MATCHING
                    if field_name == 'computer_science':
                        comp_sci_experience_paper = 1
                    else:
                        # Check if at least 2 different keywords match in topics/title/abstract
                        comp_sci_experience_paper = check_cs_keyword_match(
                            primary_topic, all_topics_str, title, abstract, cs_keywords
                        )
                    
                    # ============================================================
                    # KEY CHANGE: Look up author metrics for THIS SPECIFIC YEAR
                    # ============================================================
                    
                    # Get first author metrics (cumulative up to pub_year)
                    if (first_author_id, pub_year) in author_df.index:
                        first_author = author_df.loc[(first_author_id, pub_year)]
                        first_papers = first_author['total_papers_to_date']
                        first_citations = first_author['total_citations_to_date']
                        first_sdl_exp = first_author['sdl_papers_to_date']
                        first_field = first_author['top_field_to_date']
                    else:
                        # If author not in metrics for this year, use zeros
                        first_papers = 0
                        first_citations = 0
                        first_sdl_exp = 0
                        first_field = ''
                    
                    # Get last author metrics (cumulative up to pub_year)
                    if (last_author_id, pub_year) in author_df.index:
                        last_author = author_df.loc[(last_author_id, pub_year)]
                        last_papers = last_author['total_papers_to_date']
                        last_citations = last_author['total_citations_to_date']
                        last_sdl_exp = last_author['sdl_papers_to_date']
                        last_field = last_author['top_field_to_date']
                    else:
                        last_papers = 0
                        last_citations = 0
                        last_sdl_exp = 0
                        last_field = ''
                    
                    # Get corresponding author metrics (cumulative up to pub_year)
                    if primary_corr_id and (primary_corr_id, pub_year) in author_df.index:
                        corr_author = author_df.loc[(primary_corr_id, pub_year)]
                        corr_papers = corr_author['total_papers_to_date']
                        corr_citations = corr_author['total_citations_to_date']
                        corr_sdl_exp = corr_author['sdl_papers_to_date']
                    else:
                        corr_papers = 0
                        corr_citations = 0
                        corr_sdl_exp = 0
                    
                    # Determine corresponding position
                    corr_position = get_corresponding_position(
                        first_author_id, last_author_id, primary_corr_id, all_corr_ids
                    )
                    
                    # Check if first/last is corresponding
                    first_is_corr = 1 if first_author_id in all_corr_ids else 0
                    last_is_corr = 1 if last_author_id in all_corr_ids else 0
                    
                    # Create paper record
                    paper_record = {
                        # Identifiers
                        'article_id': row['article_id'],
                        'doi': row.get('doi', ''),
                        'title': title,
                        'abstract': abstract or '',
                        'publication_year': row['publication_year'],
                        'publication_date': publication_date or '',
                        
                        # Dependent variable
                        'author_count': row['author_count'],
                        
                        # Treatment variables
                        'SDL': row['SDL'],
                        'AI_Paper': row.get('AI_Paper', 0),
                        'Robotics_Paper': row.get('Robotics_Paper', 0),
                        
                        # Paper-level controls
                        'num_paper_affiliations': num_affiliations,
                        'primary_topic': primary_topic or 'MISSING',
                        'all_topics': all_topics_str or '',
                        'journal': journal or 'MISSING',
                        'cited_by_count': cited_by_count,
                        'field': field_name,
                        'comp_sci_experience_paper': comp_sci_experience_paper,
                        
                        # First author metrics (CUMULATIVE TO DATE)
                        'first_author_id': first_author_id,
                        'first_author_papers': first_papers,
                        'first_author_citations': first_citations,
                        'first_author_sdl_experience': first_sdl_exp,
                        'first_author_is_corresponding': first_is_corr,
                        'first_author_field': first_field,
                        
                        # Last author metrics (CUMULATIVE TO DATE)
                        'last_author_id': last_author_id,
                        'last_author_papers': last_papers,
                        'last_author_citations': last_citations,
                        'last_author_sdl_experience': last_sdl_exp,
                        'last_author_is_corresponding': last_is_corr,
                        'last_author_field': last_field,
                        
                        # Corresponding author metrics (CUMULATIVE TO DATE)
                        'corresponding_author_id': primary_corr_id or '',
                        'corresponding_author_papers': corr_papers,
                        'corresponding_author_citations': corr_citations,
                        'corresponding_author_sdl_experience': corr_sdl_exp,
                        'corresponding_position': corr_position,
                        'num_corresponding_authors': len(all_corr_ids)
                    }
                    
                    papers.append(paper_record)
                    total += 1
                    
                except Exception as e:
                    skipped += 1
        
    except Exception as e:
        pass
    
    return field_name, year, papers, total, skipped

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def load_sdl_venues():
    """Load SDL journals and topics for filtering"""
    sdl_journals = set()
    sdl_topics = set()
    
    print("\n--- Loading SDL Venue Lists ---")
    
    if FILTER_CONFIG['use_journal_filter'] and SDL_JOURNALS_FILE.exists():
        with open(SDL_JOURNALS_FILE, 'r') as f:
            sdl_journals = {line.strip() for line in f if line.strip()}
        print(f"✓ Loaded {len(sdl_journals)} SDL journals.")
    elif FILTER_CONFIG['use_journal_filter']:
        print(f"❌ ERROR: SDL journals file not found: {SDL_JOURNALS_FILE}")
    
    if FILTER_CONFIG['use_topic_filter'] and SDL_TOPICS_FILE.exists():
        with open(SDL_TOPICS_FILE, 'r') as f:
            sdl_topics = {line.strip() for line in f if line.strip()}
        print(f"✓ Loaded {len(sdl_topics)} SDL topics.")
    elif FILTER_CONFIG['use_topic_filter']:
        print(f"❌ ERROR: SDL topics file not found: {SDL_TOPICS_FILE}")

    return sdl_journals, sdl_topics


def build_regression_dataset():
    """Build complete regression dataset using parallel processing (year-level)"""
    
    print("="*80)
    print("BUILDING FILTERED REGRESSION DATASET WITH YEARLY AUTHOR METRICS")
    print("="*80)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"Years: {min(YEARS)}-{max(YEARS)-1}")
    print(f"Fields: {len(FIELDS)}")
    print(f"Filtering: SDL journals AND topics (matched venue design)")
    print(f"CPU cores available: {cpu_count()}")
    print(f"Using up to 20 parallel processes\n")
    
    # ========================================================================
    # STEP 1: Verify files exist
    # ========================================================================
    
    print("="*80)
    print("STEP 1: Verifying required files")
    print("="*80)
    
    if not AUTHOR_METRICS_FILE.exists():
        print(f"❌ ERROR: Author metrics file not found: {AUTHOR_METRICS_FILE}")
        sys.exit(1)
    print(f"✓ Found: {AUTHOR_METRICS_FILE}")
    
    if not CS_KEYWORDS_FILE.exists():
        print(f"❌ ERROR: CS keywords file not found: {CS_KEYWORDS_FILE}")
        sys.exit(1)
    print(f"✓ Found: {CS_KEYWORDS_FILE}")
    
    # Load and display CS keywords count
    cs_keywords = load_cs_keywords(CS_KEYWORDS_FILE)
    print(f"✓ Loaded {len(cs_keywords)} CS keywords\n")
    
    # Load SDL venue lists for filtering
    sdl_journals, sdl_topics = load_sdl_venues()
    
    # ========================================================================
    # STEP 2: Build task list (field, year combinations)
    # ========================================================================
    
    print("="*80)
    print("STEP 2: Building task list")
    print("="*80)
    
    tasks = []
    for field_name, field_dir in FIELDS.items():
        if not field_dir.exists():
            print(f"  ✗ {field_name}: directory not found")
            continue
        
        print(f"  ✓ {field_name}: {field_dir}")
        for year in YEARS:
            tasks.append((field_name, field_dir, year, AUTHOR_METRICS_FILE, CS_KEYWORDS_FILE))
    
    print(f"\n✓ {len(tasks)} tasks ready (field × year combinations)\n")
    
    # ========================================================================
    # STEP 3: Process tasks in parallel
    # ========================================================================
    
    print("="*80)
    print("STEP 3: Processing tasks in parallel")
    print("="*80)
    print("Progress will be displayed as tasks complete...\n")
    
    num_processes = min(20, len(tasks), cpu_count())
    
    with Pool(processes=num_processes) as pool:
        results = pool.map(process_field_year, tasks)
    
    # ========================================================================
    # STEP 4: Combine results
    # ========================================================================
    
    print(f"\n{'='*80}")
    print("STEP 4: Combining results")
    print("="*80)
    
    all_papers = []
    total_papers = 0
    total_skipped = 0
    
    # Group by field for summary
    field_summary = {}
    
    for field_name, year, papers, total, skipped in results:
        all_papers.extend(papers)
        total_papers += total
        total_skipped += skipped
        
        if field_name not in field_summary:
            field_summary[field_name] = {'papers': 0, 'skipped': 0}
        field_summary[field_name]['papers'] += total
        field_summary[field_name]['skipped'] += skipped
    
    for field_name, stats in field_summary.items():
        print(f"  {field_name}: {stats['papers']:,} papers ({stats['skipped']:,} skipped)")
    
    print(f"\nTOTAL: {total_papers:,} papers ({total_skipped:,} skipped)\n")
    
    # ========================================================================
    # STEP 5: Create DataFrame and apply transformations
    # ========================================================================
    
    print("="*80)
    print("STEP 5: Creating DataFrame and transformations")
    print("="*80)
    
    df = pd.DataFrame(all_papers)
    print(f"  DataFrame shape: {df.shape}")
    
    # Apply asinh transformations
    print("  Applying transformations...")
    df['asinh_first_author_papers'] = np.arcsinh(df['first_author_papers'].astype(float))
    df['asinh_first_author_citations'] = np.arcsinh(df['first_author_citations'].astype(float))
    df['asinh_last_author_papers'] = np.arcsinh(df['last_author_papers'].astype(float))
    df['asinh_last_author_citations'] = np.arcsinh(df['last_author_citations'].astype(float))
    df['asinh_corresponding_papers'] = np.arcsinh(df['corresponding_author_papers'].astype(float))
    df['asinh_corresponding_citations'] = np.arcsinh(df['corresponding_author_citations'].astype(float))
    df['asinh_paper_citations'] = np.arcsinh(df['cited_by_count'].astype(float))
    
    # Log transform (handle zeros by filtering or using log1p)
    df['log_author_count'] = np.log(df['author_count'].astype(float).replace(0, np.nan))
    
    print("  ✓ Transformations complete\n")
    
    # ========================================================================
    # STEP 6: Apply Regression Filters and Save Filtered Dataset
    # ========================================================================
    
    print(f"\n{'='*80}")
    print("STEP 6: Applying Regression Filters and Saving Filtered Dataset")
    print("="*80)
    
    df_filtered = df.copy()
    initial_count = len(df_filtered)
    
    # --- Filter 1 & 2: SDL Venue Filters ---
    print(f"  Applying venue filters (Journals={FILTER_CONFIG['use_journal_filter']}, Topics={FILTER_CONFIG['use_topic_filter']})...")
    
    mask = pd.Series(True, index=df_filtered.index)
    
    if FILTER_CONFIG['use_journal_filter'] and len(sdl_journals) > 0:
        mask &= df_filtered['journal'].isin(sdl_journals)
    
    if FILTER_CONFIG['use_topic_filter'] and len(sdl_topics) > 0:
        mask &= df_filtered['primary_topic'].isin(sdl_topics)
    
    df_filtered = df_filtered[mask].copy()
    
    print(f"  Rows after venue filtering: {len(df_filtered):,}")
    
    # --- Filter 3: Remove Missing Key Regression Variables ---
    key_vars = ['author_count', 'publication_year', 'field', 'asinh_first_author_papers', 'asinh_last_author_papers']
    
    pre_dropna_count = len(df_filtered)
    df_filtered = df_filtered.dropna(subset=key_vars)
    removed_missing = pre_dropna_count - len(df_filtered)
    
    print(f"  Removed {removed_missing:,} rows with missing key regression variables.")
    print(f"  Final filtered rows: {len(df_filtered):,}")
    
    # Save as CSV
    csv_file_filtered = OUTPUT_DIR / "regression_dataset_filtered_yearly_with_abstract.csv"
    print(f"\nSaving FILTERED dataset: {csv_file_filtered}")
    df_filtered.to_csv(csv_file_filtered, index=False)
    csv_size_filtered = csv_file_filtered.stat().st_size / (1024 * 1024)
    print(f"  Size: {csv_size_filtered:.1f} MB")
    
    # ========================================================================
    # STEP 7: Summary statistics
    # ========================================================================
    
    print(f"\n{'='*80}")
    print("SUMMARY STATISTICS - FILTERED DATASET")
    print("="*80)
    
    print(f"\nTotal papers: {len(df_filtered):,}")
    print(f"  SDL papers: {df_filtered['SDL'].sum():,}")
    print(f"  Non-SDL papers: {(df_filtered['SDL'] == 0).sum():,}")
    print(f"  CS Experience papers (KEYWORD MATCHING): {df_filtered['comp_sci_experience_paper'].sum():,}")
    
    # Check abstracts in filtered dataset
    filtered_with_abstract = df_filtered['abstract'].notna().sum()
    print(f"  Papers with abstracts: {filtered_with_abstract:,} ({filtered_with_abstract/len(df_filtered)*100:.1f}%)")
    
    print(f"\nPapers by field:")
    print(df_filtered['field'].value_counts().to_string())
    
    print(f"\nCS Experience by field:")
    print(df_filtered.groupby('field')['comp_sci_experience_paper'].agg(['sum', 'count', 'mean']).to_string())
    
    print(f"\nPapers by year:")
    print(df_filtered['publication_year'].value_counts().sort_index().to_string())
    
    print(f"\nAuthor metrics summary (first authors):")
    print(df_filtered[['first_author_papers', 'first_author_citations', 'first_author_sdl_experience']].describe().to_string())
    
    print(f"\nAuthor metrics summary (last authors):")
    print(df_filtered[['last_author_papers', 'last_author_citations', 'last_author_sdl_experience']].describe().to_string())
    
    print(f"\n{'='*80}")
    print("✅ COMPLETE!")
    print("="*80)
    print(f"\nOutput file:")
    print(f"  {csv_file_filtered}")
    print(f"  Size: {csv_size_filtered:.1f} MB\n")
    
    return df_filtered


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    df_final = build_regression_dataset()
