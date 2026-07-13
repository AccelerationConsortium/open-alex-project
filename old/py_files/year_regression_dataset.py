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
                    
                    #NEW ADDITION
                    raw_year = row.get('publication_year')
                    try:
                        pub_year = int(float(raw_year))
                    except (TypeError, ValueError):
                        skipped += 1
                        continue





                    # Create paper record (WITHOUT author metrics - will merge later)
                    paper_record = {
                        'article_id': row['article_id'],
                        'doi': row.get('doi', ''),
                        'title': title,
                        'publication_year': pub_year,
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

    # # Merge
    # df = df.merge(
    #     first_author_df,
    #     left_on=['first_author_id', 'publication_year'],
    #     right_on=['first_author_id_merge', 'year_merge'],
    #     how='left'
    # )

    # Sort author metrics by year
    author_df_sorted = author_df.sort_values(['author_id', 'year'])

    # For each paper, find the latest author-year row where year <= publication_year
    # Use merge_asof (requires sorted data)
    df = df.sort_values('publication_year')

    df = pd.merge_asof(
        df,
        first_author_df.rename(columns={'first_author_id_merge': 'first_author_id', 
                                        'year_merge': 'publication_year'}),
        on='publication_year',
        by='first_author_id',
        direction='backward'  # find latest row where author year <= paper year
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

    #NEW ADDITION
    author_metric_cols = [col for col in df.columns if '_3yr' in col or '_prior_' in col]
    df[author_metric_cols] = df[author_metric_cols].fillna(0)



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

