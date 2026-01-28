# import pandas as pd
# import re
# from pathlib import Path
# import sys

# # ============================================================================
# # CONFIGURATION
# # ============================================================================

# # Keywords file (currently set to Robotics)
# KEYWORDS_FILE = Path("/project/def-kmcel/hridansh/openalex_project/data/keywords/test/AI_Keywords_combined.csv")

# # Input dataset
# INPUT_FILE = Path("/project/def-kmcel/hridansh/openalex_project/data/regression/test/regression_dataset_filtered_v3.csv")

# # Output file (v3)
# OUTPUT_FILE = Path("/project/def-kmcel/hridansh/openalex_project/data/regression/test/regression_dataset_filtered_v4.csv")

# # Columns to update
# COUNT_COL = 'number_of_AI_words'
# BINARY_COL = 'AI_Paper'

# # ============================================================================
# # FUNCTIONS
# # ============================================================================

# def load_keywords(file_path):
#     print(f"Loading keywords from: {file_path}")
#     if not file_path.exists():
#         print(f"❌ Error: Keywords file not found at {file_path}")
#         sys.exit(1)
        
#     try:
#         df = pd.read_csv(file_path, header=None)
#         keywords = set()
#         for col in df.columns:
#             clean_col = df[col].dropna().astype(str)
#             for word in clean_col:
#                 clean_word = word.strip().lower()
#                 if clean_word:
#                     keywords.add(clean_word)
        
#         keywords_list = sorted(list(keywords))
#         print(f"✓ Loaded {len(keywords_list)} unique keywords.")
#         return keywords_list
#     except Exception as e:
#         print(f"❌ Error reading keywords file: {e}")
#         sys.exit(1)

# def compile_keyword_patterns(keywords):
#     print("Compiling regex patterns...")
#     patterns = []
#     for keyword in keywords:
#         # \b ensures we don't match partial words (e.g. 'robotic' inside 'probotic')
#         pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
#         patterns.append(pattern)
#     return patterns

# def count_matches(text, patterns):
#     if not isinstance(text, str) or not text:
#         return 0
    
#     count = 0
#     for pattern in patterns:
#         matches = pattern.findall(text)
#         count += len(matches)
#     return count

# # ============================================================================
# # MAIN EXECUTION
# # ============================================================================

# def main():
#     print("="*60)
#     print("RE-RUNNING ROBOTICS CLASSIFICATION (Title + Abstract + Topics)")
#     print("="*60)
    
#     # 1. Load Data
#     print(f"Reading dataset: {INPUT_FILE}")
#     if not INPUT_FILE.exists():
#         print(f"❌ Error: Input file not found.")
#         sys.exit(1)
        
#     df = pd.read_csv(INPUT_FILE, low_memory=False)
#     print(f"✓ Loaded {len(df):,} papers.")
    
#     # 2. Load Keywords
#     keywords = load_keywords(KEYWORDS_FILE)
#     patterns = compile_keyword_patterns(keywords)
    
#     # 3. Prepare Search Text (Title + Abstract + Topics)
#     print("\nPreparing combined search text (Title + Abstract + Topics)...")
    
#     # We combine columns with a space separator. 
#     # fillna('') ensures we don't lose data if one field is missing.
#     search_text = (
#         df['title'].fillna('') + ' ' + 
#         df['abstract'].fillna('') + ' ' + 
#         df['all_topics'].fillna('')
#     )
    
#     # 4. Process Papers
#     print(f"Scanning combined text for {len(patterns)} keywords...")
#     print("This may take a few minutes...")
    
#     counts = search_text.apply(lambda x: count_matches(x, patterns))
    
#     # 5. Update DataFrame
#     print("\nUpdating columns...")
    
#     old_binary_sum = df[BINARY_COL].sum() if BINARY_COL in df.columns else 0
    
#     df[COUNT_COL] = counts
#     df[BINARY_COL] = (counts > 0).astype(int)
    
#     new_binary_sum = df[BINARY_COL].sum()
    
#     # 6. Statistics
#     print("-" * 60)
#     print("CLASSIFICATION RESULTS")
#     print("-" * 60)
#     print(f"Previous Robotics Papers: {old_binary_sum:,}")
#     print(f"New Robotics Papers:      {new_binary_sum:,}")
#     print(f"Difference:               {new_binary_sum - old_binary_sum:+,}")
#     print("-" * 60)
    
#     # Sanity Check: Check for "robot" matches that are still 0
#     # Note: We verify against the COMBINED text now
#     missed = df[
#         (search_text.str.contains('robot', case=False, na=False)) & 
#         (df[BINARY_COL] == 0)
#     ]
#     print(f"Papers with 'robot' in Title/Abs/Topics but labeled 0: {len(missed)}")
    
#     # 7. Save
#     print(f"\nSaving to: {OUTPUT_FILE}")
#     df.to_csv(OUTPUT_FILE, index=False)
#     print("✅ Done.")

# if __name__ == "__main__":
#     main()


## ADDING SDL KEYWORD MEASURES

# import pandas as pd
# import re
# from pathlib import Path
# import sys

# # ============================================================================
# # CONFIGURATION
# # ============================================================================

# # INPUT: The output from your last step (v3)
# INPUT_FILE = Path("/project/def-kmcel/hridansh/openalex_project/data/regression/regression_dataset_subset.csv")

# # KEYWORDS: Your SDL keywords file
# KEYWORDS_FILE = Path("/project/def-kmcel/hridansh/openalex_project/data/keywords/sdl_Keywords.csv")

# # OUTPUT: New version (v4)
# OUTPUT_FILE = Path("/project/def-kmcel/hridansh/openalex_project/data/regression/test/regression_dataset_filtered_v4.csv")

# # ============================================================================
# # FUNCTIONS
# # ============================================================================

# def load_keywords(file_path):
#     print(f"Loading keywords from: {file_path}")
#     if not file_path.exists():
#         print(f"❌ Error: Keywords file not found at {file_path}")
#         sys.exit(1)
        
#     try:
#         # Assumes one keyword per row
#         df = pd.read_csv(file_path, header=None)
#         keywords = set()
#         for col in df.columns:
#             clean_col = df[col].dropna().astype(str)
#             for word in clean_col:
#                 clean_word = word.strip().lower()
#                 if clean_word:
#                     keywords.add(clean_word)
        
#         k_list = sorted(list(keywords))
#         print(f"✓ Loaded {len(k_list)} unique SDL keywords.")
#         return k_list
#     except Exception as e:
#         print(f"❌ Error reading keywords file: {e}")
#         sys.exit(1)

# def compile_patterns(keywords):
#     print("Compiling regex patterns...")
#     # \b ensures exact word matches
#     return [re.compile(r'\b' + re.escape(k) + r'\b', re.IGNORECASE) for k in keywords]

# def count_matches(text, patterns):
#     if not isinstance(text, str) or not text:
#         return 0
#     count = 0
#     for pattern in patterns:
#         if pattern.search(text): 
#              matches = pattern.findall(text)
#              count += len(matches)
#     return count

# # ============================================================================
# # MAIN
# # ============================================================================

# def main():
#     print("="*60)
#     print("ADDING SDL KEYWORD MEASURES (NO CHUNKING)")
#     print("="*60)

#     # 1. Setup
#     if not INPUT_FILE.exists():
#         print(f"❌ Input file not found: {INPUT_FILE}")
#         sys.exit(1)
        
#     keywords = load_keywords(KEYWORDS_FILE)
#     patterns = compile_patterns(keywords)
    
#     # 2. Load Data
#     print(f"Reading full dataset from {INPUT_FILE}...")
#     df = pd.read_csv(INPUT_FILE, low_memory=False)
#     print(f"✓ Loaded {len(df):,} rows.")
    
#     # 3. Create Search Text
#     print("Creating combined text field (Title + Abstract + Topics)...")
#     # Combine columns safely
#     titles = df['title'].fillna('') if 'title' in df.columns else pd.Series(['']*len(df))
#     abstracts = df['abstract'].fillna('') if 'abstract' in df.columns else pd.Series(['']*len(df))
#     topics = df['all_topics'].fillna('') if 'all_topics' in df.columns else pd.Series(['']*len(df))
    
#     combined_text = titles + ' ' + abstracts + ' ' + topics
    
#     # 4. Count Matches
#     print(f"Scanning {len(df):,} papers against {len(patterns)} keywords...")
#     counts = combined_text.apply(lambda x: count_matches(x, patterns))
    
#     # 5. Add Columns
#     print("Updating dataframe...")
#     df['number_of_SDL_words'] = counts
#     df['SDL_Keyword_Paper'] = (counts > 0).astype(int)
    
#     total_sdl_matches = df['SDL_Keyword_Paper'].sum()
    
#     # 6. Save
#     print(f"Saving to {OUTPUT_FILE}...")
#     df.to_csv(OUTPUT_FILE, index=False)
    
#     # 7. Summary
#     print("-" * 60)
#     print("DONE")
#     print("-" * 60)
#     print(f"Total Papers:       {len(df):,}")
#     print(f"SDL Keyword Matches:{total_sdl_matches:,}")
#     print(f"Saved to:           {OUTPUT_FILE}")
#     print("-" * 60)

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

# INPUT: Your latest dataset (v4) containing both SDL measures
INPUT_FILE = Path("/project/def-kmcel/hridansh/openalex_project/data/regression/test/regression_dataset_subset.csv")
OUTPUT_FILE = Path("/project/def-kmcel/hridansh/openalex_project/data/regression/test/eda_report_v4_sdl_comparison.txt")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_section(title):
    print("=" * 80)
    print(title)
    print("=" * 80)

def calculate_stats(df):
    # ------------------------------------------------------------------------
    # 0. HEADER & OVERVIEW
    # ------------------------------------------------------------------------
    print("=" * 80)
    print("EXPLORATORY DATA ANALYSIS - REGRESSION DATASET (V4)")
    print("=" * 80)
    print(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Source file: {INPUT_FILE}")
    print("=" * 80 + "\n")

    print_section("DATASET OVERVIEW")
    print("Sample: SDL VENUE MATCHED PAPERS")
    print(f"Total papers: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1e9:.2f} GB\n")
    
    print("Columns:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:>2}. {col}")
    print("")

    # ------------------------------------------------------------------------
    # 1B. ABSTRACT ANALYSIS
    # ------------------------------------------------------------------------
    print_section("1B. ABSTRACT ANALYSIS")
    
    if 'abstract' in df.columns:
        has_abstract = df['abstract'].notna()
        print(f"Papers with abstracts: {has_abstract.sum():,} ({has_abstract.mean()*100:.2f}%)")
        print(f"Papers without abstracts: {(~has_abstract).sum():,} ({(~has_abstract).mean()*100:.2f}%)\n")
        
        # Calc lengths only for non-null abstracts
        abstract_lens = df.loc[has_abstract, 'abstract'].astype(str).str.len()
        print("Abstract length statistics (characters):")
        print(f"  Mean: {abstract_lens.mean():.0f}")
        print(f"  Median: {abstract_lens.median():.0f}")
        print(f"  Min: {abstract_lens.min()}")
        print(f"  Max: {abstract_lens.max()}\n")

        # Word count estimation
        word_counts = df.loc[has_abstract, 'abstract'].astype(str).str.split().str.len()
        print("Abstract word count:")
        print(f"  Mean: {word_counts.mean():.0f}")
        print(f"  Median: {word_counts.median():.0f}")
        print(f"  Max: {word_counts.max()}\n")

        print("Abstracts by field:")
        for field in df['field'].unique():
            field_mask = df['field'] == field
            n_field = field_mask.sum()
            n_abs = (field_mask & has_abstract).sum()
            print(f"  {field:<20}: {n_abs:,} / {n_field:,} ({n_abs/n_field*100:.2f}%)")
    else:
        print("No abstract column found.")
    print("")

    # ------------------------------------------------------------------------
    # 2. MISSING VALUES ANALYSIS
    # ------------------------------------------------------------------------
    print_section("2. MISSING VALUES ANALYSIS")
    print("Columns with missing values:")
    missing = df.isnull().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    for col, count in missing.items():
        print(f"  {col}: {count:,} ({count/len(df)*100:.2f}%)")
    print("")

    # ------------------------------------------------------------------------
    # 3. DEPENDENT VARIABLE
    # ------------------------------------------------------------------------
    print_section("3. DEPENDENT VARIABLE - TEAM SIZE (author_count)")
    print(df['author_count'].describe().to_string())
    print("\nTeam size distribution:")
    
    bins = [0, 1, 2, 3, 4, 9, 19, 49, 99, 99999]
    labels = ['1', '2', '3', '4', '5-9', '10-19', '20-49', '50-99', '100+']
    cuts = pd.cut(df['author_count'], bins=bins, labels=labels)
    dist = cuts.value_counts().sort_index()
    
    for label, count in dist.items():
        print(f"  {label:<8}: {count:,} ({count/len(df)*100:.2f}%)")
    print("")

    # ------------------------------------------------------------------------
    # 4. TREATMENT VARIABLES (UPDATED WITH NEW SDL MEASURE)
    # ------------------------------------------------------------------------
    print_section("4. TREATMENT VARIABLES & SDL OVERLAP")
    
    # Define masks
    sdl_orig_mask = df['SDL'] == 1
    sdl_new_mask = df['SDL_Keyword_Paper'] == 1  # The new measure
    ai_mask = df['AI_Paper'] == 1
    robo_mask = df['Robotics_Paper'] == 1
    
    # Basic Counts
    print("Paper Counts by Category:")
    print(f"  SDL (Original Measure):  {sdl_orig_mask.sum():,} ({sdl_orig_mask.mean()*100:.2f}%)")
    print(f"  SDL (New Phrase Measure):{sdl_new_mask.sum():,} ({sdl_new_mask.mean()*100:.2f}%)")
    print(f"  AI Papers:               {ai_mask.sum():,} ({ai_mask.mean()*100:.2f}%)")
    print(f"  Robotics Papers:         {robo_mask.sum():,} ({robo_mask.mean()*100:.2f}%)")
    
    # --- NEW: SDL OVERLAP ANALYSIS ---
    print("\n" + "-"*40)
    print("SDL MEASURE COMPARISON (Original vs New)")
    print("-" * 40)
    
    overlap_both = (sdl_orig_mask & sdl_new_mask).sum()
    only_orig = (sdl_orig_mask & ~sdl_new_mask).sum()
    only_new = (~sdl_orig_mask & sdl_new_mask).sum()
    union_total = overlap_both + only_orig + only_new
    
    print(f"Total Unique SDL Papers (Union): {union_total:,}")
    print(f"  1. MATCHED in BOTH:      {overlap_both:,}")
    print(f"  2. Only in ORIGINAL:     {only_orig:,}")
    print(f"  3. Only in NEW MEASURE:  {only_new:,}")
    
    print("\nOverlap Logic Check:")
    if sdl_orig_mask.sum() > 0:
        print(f"  % of Original captured by New: {overlap_both/sdl_orig_mask.sum()*100:.1f}%")
    if sdl_new_mask.sum() > 0:
        print(f"  % of New captured by Original: {overlap_both/sdl_new_mask.sum()*100:.1f}%")

    # Team Sizes
    print("\nAverage Team Size by Group:")
    print(f"  SDL (Original):     {df.loc[sdl_orig_mask, 'author_count'].mean():.2f}")
    print(f"  SDL (New Measure):  {df.loc[sdl_new_mask, 'author_count'].mean():.2f}")
    print(f"  SDL (Union):        {df.loc[sdl_orig_mask | sdl_new_mask, 'author_count'].mean():.2f}")
    print(f"  Non-SDL (Strict):   {df.loc[~(sdl_orig_mask | sdl_new_mask), 'author_count'].mean():.2f}")
    print(f"  AI Papers:          {df.loc[ai_mask, 'author_count'].mean():.2f}")
    print(f"  Robotics Papers:    {df.loc[robo_mask, 'author_count'].mean():.2f}")
    print("")

    # ------------------------------------------------------------------------
    # 5. FIELD DISTRIBUTION
    # ------------------------------------------------------------------------
    print_section("5. FIELD DISTRIBUTION")
    print(df['field'].value_counts().to_string())
    
    print("\nSDL Papers by Field (Original vs New):")
    print(f"{'Field':<20} | {'Original':<10} | {'New':<10}")
    print("-" * 45)
    for field in df['field'].unique():
        f_mask = df['field'] == field
        n_orig = (f_mask & sdl_orig_mask).sum()
        n_new = (f_mask & sdl_new_mask).sum()
        print(f"{field:<20} | {n_orig:<10} | {n_new:<10}")
    print("")

    # ------------------------------------------------------------------------
    # 5B. CS EXPERIENCE
    # ------------------------------------------------------------------------
    print_section("5B. CS EXPERIENCE ANALYSIS")
    cs_exp = df['comp_sci_experience_paper'] == 1
    
    print(f"Papers with CS experience: {cs_exp.sum():,} ({cs_exp.mean()*100:.2f}%)")
    
    print("\nCS experience by field:")
    for field in df['field'].unique():
        field_mask = df['field'] == field
        n_cs = (field_mask & cs_exp).sum()
        n_total = field_mask.sum()
        print(f"  {field:<20}: {n_cs:,} / {n_total:,} ({n_cs/n_total*100:.2f}%)")
    
    print("\nAverage team size:")
    print(f"  With CS experience: {df.loc[cs_exp, 'author_count'].mean():.2f}")
    print(f"  Without CS experience: {df.loc[~cs_exp, 'author_count'].mean():.2f}")
    print("")

    # ------------------------------------------------------------------------
    # 6. TEMPORAL DISTRIBUTION
    # ------------------------------------------------------------------------
    print_section("6. TEMPORAL DISTRIBUTION")
    print(f"{'Year':<6} | {'Total':<8} | {'SDL(Orig)':<10} | {'SDL(New)':<10}")
    print("-" * 40)
    years = sorted(df['publication_year'].unique())
    for year in years:
        y_mask = df['publication_year'] == year
        n_papers = y_mask.sum()
        n_orig = (y_mask & sdl_orig_mask).sum()
        n_new = (y_mask & sdl_new_mask).sum()
        print(f"{year:<6} | {n_papers:<8,} | {n_orig:<10} | {n_new:<10}")
    print("")

    # ------------------------------------------------------------------------
    # 7. AUTHOR METRICS
    # ------------------------------------------------------------------------
    print_section("7. AUTHOR METRICS STATISTICS")
    cols = ['first_author_papers', 'first_author_citations', 'first_author_sdl_experience']
    print("First author metrics:")
    print(df[cols].describe().to_string())
    print("")

    # ------------------------------------------------------------------------
    # 8. CORRESPONDING POS
    # ------------------------------------------------------------------------
    print_section("8. CORRESPONDING AUTHOR POSITION")
    if 'corresponding_position' in df.columns:
        print(df['corresponding_position'].fillna('missing').value_counts().to_string())
    print("")

    # ------------------------------------------------------------------------
    # 9. CONTROLS & 10. TOPICS
    # ------------------------------------------------------------------------
    print_section("9. PAPER-LEVEL CONTROLS")
    print("Affiliations per paper:")
    print(df['num_paper_affiliations'].describe().to_string())
    
    print("\nTop 15 journals:")
    print(df['journal'].value_counts().head(15).to_string())

    print_section("10. ALL TOPICS ANALYSIS")
    print("Top 15 topics (primary):")
    print(df['primary_topic'].value_counts().head(15).to_string())
    print("")

    # ------------------------------------------------------------------------
    # 11. TRANSFORMED
    # ------------------------------------------------------------------------
    print_section("11. TRANSFORMED VARIABLES")
    transform_cols = [c for c in df.columns if 'asinh' in c or 'log_' in c]
    for col in transform_cols:
        print(f"{col}: Mean={df[col].mean():.4f}, Std={df[col].std():.4f}")
    print("")

    # ------------------------------------------------------------------------
    # 13. SDL DEEP DIVE (EXPANDED)
    # ------------------------------------------------------------------------
    print_section("13. SDL PAPER DEEP DIVE")
    
    print("Top 10 Topics for ORIGINAL SDL Papers:")
    print(df.loc[sdl_orig_mask, 'primary_topic'].value_counts().head(10).to_string())
    
    print("\nTop 10 Topics for NEW PHRASE SDL Papers:")
    print(df.loc[sdl_new_mask, 'primary_topic'].value_counts().head(10).to_string())
    
    print("\nTop 10 Topics for 'ONLY NEW' Papers (missed by original):")
    only_new_mask = (~sdl_orig_mask & sdl_new_mask)
    if only_new_mask.sum() > 0:
        print(df.loc[only_new_mask, 'primary_topic'].value_counts().head(10).to_string())
    else:
        print("  (None)")
    print("")

    # ------------------------------------------------------------------------
    # 14. CORRELATION
    # ------------------------------------------------------------------------
    print_section("14. CORRELATION WITH TEAM SIZE")
    numeric_df = df.select_dtypes(include=[np.number])
    corrs = numeric_df.corrwith(df['author_count']).sort_values(ascending=False)
    
    interest_cols = ['num_paper_affiliations', 'comp_sci_experience_paper', 
                     'AI_Paper', 'Robotics_Paper', 'SDL', 'SDL_Keyword_Paper', 
                     'cited_by_count']
    
    print("Correlation with author_count:")
    for col in interest_cols:
        if col in corrs:
            print(f"  {col:<30}: {corrs[col]:.4f}")
    
    print("\n" + "="*80)
    print("END OF REPORT")
    print("="*80)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if not INPUT_FILE.exists():
        print(f"Error: Input file {INPUT_FILE} not found.")
        sys.exit(1)
        
    print(f"Loading data from {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE, low_memory=False)
    
    # Redirect output to file AND print to console
    with open(OUTPUT_FILE, 'w') as f:
        class Tee(object):
            def __init__(self, *files):
                self.files = files
            def write(self, obj):
                for f in self.files:
                    f.write(obj)
            def flush(self):
                for f in self.files:
                    f.flush()
        
        original_stdout = sys.stdout
        sys.stdout = Tee(sys.stdout, f)
        
        try:
            calculate_stats(df)
        finally:
            sys.stdout = original_stdout

    print(f"\nReport saved to {OUTPUT_FILE}")