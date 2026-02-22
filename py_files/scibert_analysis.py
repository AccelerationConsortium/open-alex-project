
"""
SciBERT SDL Classifier - ITERATION 1 ANALYSIS
Fixed version with deduplication and validation
"""
import pandas as pd
import numpy as np  
from sklearn.feature_extraction.text import CountVectorizer
import os

# ==============================================================================
# CONFIGURATION
# ==============================================================================
PROJECT_DIR = "/project/def-kmcel/hridansh/openalex_project"

SCORES_FILE = f"{PROJECT_DIR}/data/scibert/test_2/scores.csv"
FULL_DATA_FILE = f"{PROJECT_DIR}/data/regression/regression_dataset_subset.csv"
OUTPUT_DIR = f"{PROJECT_DIR}/data/scibert/test_2"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================================================================
# LOAD AND VALIDATE DATA
# ==============================================================================

print("\n" + "="*70)
print("LOADING & VALIDATING DATA")
print("="*70)

if not os.path.exists(SCORES_FILE):
    print(f"ERROR: Scores file not found at {SCORES_FILE}")
    exit(1)

# Load scores
df_raw = pd.read_csv(SCORES_FILE)
print(f"\nRaw scores file: {len(df_raw):,} rows")

# Check for duplicates
duplicates = df_raw.duplicated(subset=['article_id'], keep=False)
n_duplicates = duplicates.sum()

if n_duplicates > 0:
    print(f"WARNING: Found {n_duplicates:,} duplicate rows!")
    print(f"  Unique article_ids: {df_raw['article_id'].nunique():,}")
    print(f"  Deduplicating by article_id (keeping first occurrence)...")
    df = df_raw.drop_duplicates(subset=['article_id'], keep='first').reset_index(drop=True)
    print(f"  After deduplication: {len(df):,} papers")
else:
    df = df_raw.copy()
    print(f"No duplicates found - data is clean")

# Verify score column
score_col = 'scibert_prob'
if score_col not in df.columns:
    print(f"\nERROR: Expected column '{score_col}' not found")
    print(f"Available columns: {list(df.columns)}")
    exit(1)

# Load text data if needed
needs_text = ('title' not in df.columns) or ('abstract' not in df.columns)

if needs_text:
    print(f"\nLoading text from: {FULL_DATA_FILE}")
    df_full = pd.read_csv(FULL_DATA_FILE, low_memory=False)
    
    # Merge only needed columns
    merge_cols = ['article_id']
    if 'title' not in df.columns:
        merge_cols.append('title')
    if 'abstract' not in df.columns:
        merge_cols.append('abstract')
    
    df = pd.merge(df, df_full[merge_cols], on='article_id', how='left')

# Prepare text
has_text = ('title' in df.columns) and ('abstract' in df.columns)
if has_text:
    df['title'] = df['title'].fillna("")
    df['abstract'] = df['abstract'].fillna("")
    df['full_text'] = df['title'] + " " + df['abstract']
else:
    print("\nWARNING: No text data available")
    df['full_text'] = ""

# Create ground truth labels
df['SDL_Brown'] = df['SDL_Brown'].fillna(0).astype(int)
df['SDL_Tomet'] = df['SDL_Tomet'].fillna(0).astype(int)
df['label_true'] = ((df['SDL_Brown'] == 1) | (df['SDL_Tomet'] == 1)).astype(int)

# Validate counts
n_brown = (df['SDL_Brown'] == 1).sum()
n_tomet = (df['SDL_Tomet'] == 1).sum()
n_both = ((df['SDL_Brown'] == 1) & (df['SDL_Tomet'] == 1)).sum()
n_sdl = (df['label_true'] == 1).sum()

print(f"\n{'='*70}")
print("DATA VALIDATION")
print(f"{'='*70}")
print(f"Total papers:     {len(df):,}")
print(f"SDL_Brown only:   {n_brown - n_both:,}")
print(f"SDL_Tomet only:   {n_tomet - n_both:,}")
print(f"Both sources:     {n_both:,}")
print(f"Total known SDL:  {n_sdl:,}")
print(f"Background:       {(df['label_true'] == 0).sum():,}")

# Sanity check
expected_sdl = n_brown + n_tomet - n_both
if n_sdl != expected_sdl:
    print(f"\nWARNING: SDL count mismatch!")
    print(f"  Computed: {n_sdl}, Expected: {expected_sdl}")

# ==============================================================================
# 1. SCORE DISTRIBUTION
# ==============================================================================

print("\n" + "="*70)
print("1. SCORE DISTRIBUTION")
print("="*70)

print(f"\nOverall Statistics:")
print(f"  Mean:   {df[score_col].mean():.4f}")
print(f"  Median: {df[score_col].median():.4f}")
print(f"  Std:    {df[score_col].std():.4f}")
print(f"  Min:    {df[score_col].min():.4f}")
print(f"  Max:    {df[score_col].max():.4f}")

print(f"\nScore Buckets:")
buckets = [
    (0.00, 0.10, "Very Low"),
    (0.10, 0.30, "Low"),
    (0.30, 0.50, "Medium-Low"),
    (0.50, 0.70, "Medium-High"),
    (0.70, 0.90, "High"),
    (0.90, 1.00, "Very High")
]

for low, high, label in buckets:
    count = ((df[score_col] >= low) & (df[score_col] < high)).sum()
    pct = count / len(df) * 100
    print(f"  {label:15} [{low:.2f}-{high:.2f}): {count:>7,} ({pct:>5.2f}%)")

# ==============================================================================
# 2. KNOWN SDL RECALL
# ==============================================================================

print("\n" + "="*70)
print("2. KNOWN SDL RECALL")
print("="*70)

known_sdl = df[df['label_true'] == 1].copy()
background = df[df['label_true'] == 0].copy()

print(f"\nKnown SDL Papers: {len(known_sdl):,}")
print(f"  Brown only: {((known_sdl['SDL_Brown'] == 1) & (known_sdl['SDL_Tomet'] == 0)).sum():,}")
print(f"  Tomet only: {((known_sdl['SDL_Brown'] == 0) & (known_sdl['SDL_Tomet'] == 1)).sum():,}")
print(f"  Both:       {((known_sdl['SDL_Brown'] == 1) & (known_sdl['SDL_Tomet'] == 1)).sum():,}")

print(f"\nScore Statistics (Known SDL):")
print(f"  Mean:   {known_sdl[score_col].mean():.4f}")
print(f"  Median: {known_sdl[score_col].median():.4f}")
print(f"  Min:    {known_sdl[score_col].min():.4f}")

print(f"\nRecall at Thresholds:")
for thresh in [0.5, 0.7, 0.9, 0.95]:
    recalled = (known_sdl[score_col] >= thresh).sum()
    recall_rate = recalled / len(known_sdl) * 100
    print(f"  >= {thresh:.2f}: {recalled:>4}/{len(known_sdl):>4} ({recall_rate:>5.1f}%)")

# Save hard misses
hard_misses = known_sdl[known_sdl[score_col] < 0.20].copy()
print(f"\nHard Misses (score < 0.20): {len(hard_misses)}")
if len(hard_misses) > 0:
    print(f"  Brown only: {((hard_misses['SDL_Brown'] == 1) & (hard_misses['SDL_Tomet'] == 0)).sum()}")
    print(f"  Tomet only: {((hard_misses['SDL_Brown'] == 0) & (hard_misses['SDL_Tomet'] == 1)).sum()}")
    print(f"  Both:       {((hard_misses['SDL_Brown'] == 1) & (hard_misses['SDL_Tomet'] == 1)).sum()}")
    
    hard_misses_path = f"{OUTPUT_DIR}/hard_misses.csv"
    hard_misses[['article_id', 'doi', 'title', score_col, 'SDL_Brown', 'SDL_Tomet']].to_csv(
        hard_misses_path, index=False
    )
    print(f"  ✓ Saved: {hard_misses_path}")

# ==============================================================================
# 3. FALSE POSITIVE ANALYSIS
# ==============================================================================

print("\n" + "="*70)
print("3. FALSE POSITIVE ANALYSIS")
print("="*70)

print(f"\nBackground Papers: {len(background):,}")
print(f"  Mean Score: {background[score_col].mean():.4f}")
print(f"  Median:     {background[score_col].median():.4f}")
print(f"  Max:        {background[score_col].max():.4f}")

print(f"\nPotential False Positives:")
for thresh in [0.5, 0.7, 0.9, 0.95]:
    fp_count = (background[score_col] >= thresh).sum()
    fp_rate = fp_count / len(background) * 100
    print(f"  >= {thresh:.2f}: {fp_count:>7,} ({fp_rate:>5.2f}%)")

# ==============================================================================
# 4. FIELD-SPECIFIC PATTERNS
# ==============================================================================

print("\n" + "="*70)
print("4. FIELD-SPECIFIC PATTERNS")
print("="*70)

print(f"\nScores by Field:")
for field in sorted(df['field'].unique()):
    field_df = df[df['field'] == field]
    avg_score = field_df[score_col].mean()
    high_conf = (field_df[score_col] > 0.9).sum()
    known_sdl_count = (field_df['label_true'] == 1).sum()
    print(f"  {field:25}: avg={avg_score:.4f}  |  >0.9: {high_conf:>6,}  |  known SDL: {known_sdl_count:>4}")

# ==============================================================================
# 5. DISTINCTIVE VOCABULARY (LOG-ODDS)
# ==============================================================================

print("\n" + "="*70)
print("5. DISTINCTIVE VOCABULARY")
print("="*70)

if not has_text:
    print("\n  ⚠ Skipping (no text data)")
else:
    high_conf = df[df[score_col] > 0.90].copy()
    low_conf = df[df[score_col] < 0.10].copy()
    
    print(f"\nHigh confidence (>0.90): {len(high_conf):,}")
    print(f"Low confidence (<0.10):  {len(low_conf):,}")
    
    if len(high_conf) >= 10 and len(low_conf) >= 10:
        subset = pd.concat([high_conf, low_conf])
        y = np.where(subset[score_col] > 0.90, 1, 0)
        
        vec = CountVectorizer(
            ngram_range=(2, 3), 
            stop_words='english', 
            min_df=5, 
            max_features=50000
        )
        
        try:
            X = vec.fit_transform(subset['full_text'])
            X_pos = X[y == 1]
            X_neg = X[y == 0]
            
            pos_counts = np.array(X_pos.sum(axis=0)).flatten() + 1
            neg_counts = np.array(X_neg.sum(axis=0)).flatten() + 1
            
            pos_norm = pos_counts / pos_counts.sum()
            neg_norm = neg_counts / neg_counts.sum()
            log_odds = np.log(pos_norm / neg_norm)
            
            vocab = {v: k for k, v in vec.vocabulary_.items()}
            
            print("\nTop 30 Phrases (HIGH scores):")
            for idx in log_odds.argsort()[::-1][:30]:
                print(f"  + {vocab[idx]:40} ({log_odds[idx]:>6.2f})")
            
            print("\nTop 30 Phrases (LOW scores):")
            for idx in log_odds.argsort()[:30]:
                print(f"  - {vocab[idx]:40} ({log_odds[idx]:>6.2f})")
            
            logodds_df = pd.DataFrame({
                'phrase': [vocab[i] for i in range(len(vocab))],
                'log_odds': log_odds
            }).sort_values('log_odds', ascending=False)
            
            logodds_path = f"{OUTPUT_DIR}/log_odds_analysis.csv"
            logodds_df.to_csv(logodds_path, index=False)
            print(f"\n  ✓ Saved: {logodds_path}")
            
        except Exception as e:
            print(f"\n  ✗ Failed: {e}")
    else:
        print("\n  ⚠ Insufficient data")

# ==============================================================================
# 6. KEYWORD CHECKS
# ==============================================================================

print("\n" + "="*70)
print("6. KEYWORD CHECKS")
print("="*70)

if not has_text:
    print("\n  ⚠ Skipping (no text data)")
else:
    print("\n[Robotics Leak]")
    for kw in ['drone', 'uav', 'autonomous vehicle', 'traffic', 'pedestrian', 'robot']:
        mask = df['full_text'].str.lower().str.contains(kw, na=False)
        if mask.sum() > 0:
            print(f"  {kw:20}: {mask.sum():>6} papers, avg={df[mask][score_col].mean():.4f}, >0.9: {(df[mask][score_col] > 0.9).sum():>5}")
    
    print("\n[Simulation Trap]")
    for kw in ['dft', 'density functional', 'molecular dynamics', 'vasp', 'gaussian', 'monte carlo']:
        mask = df['full_text'].str.lower().str.contains(kw, na=False)
        if mask.sum() > 0:
            print(f"  {kw:20}: {mask.sum():>6} papers, avg={df[mask][score_col].mean():.4f}, >0.9: {(df[mask][score_col] > 0.9).sum():>5}")
    
    print("\n[Topic Confounding]")
    for kw in ['battery', 'perovskite', 'solar cell', 'photovoltaic', 'catalyst']:
        mask = df['full_text'].str.lower().str.contains(kw, na=False)
        if mask.sum() > 0:
            print(f"  {kw:20}: {mask.sum():>6} papers, avg={df[mask][score_col].mean():.4f}, >0.9: {(df[mask][score_col] > 0.9).sum():>5}")
    
    print("\n[SDL Indicators]")
    for kw in ['microfluidic', 'flow chemistry', 'automated synthesis', 'high throughput', 'screening platform']:
        mask = df['full_text'].str.lower().str.contains(kw, na=False)
        if mask.sum() > 0:
            print(f"  {kw:20}: {mask.sum():>6} papers, avg={df[mask][score_col].mean():.4f}, >0.9: {(df[mask][score_col] > 0.9).sum():>5}")

# ==============================================================================
# 7. EXPORTS
# ==============================================================================

print("\n" + "="*70)
print("7. EXPORTS")
print("="*70)

# Top 100 (deduplicated)
top_100 = df.nlargest(100, score_col).drop_duplicates(subset=['article_id']).head(100)
top_100_path = f"{OUTPUT_DIR}/top_100_overall.csv"

export_cols = ['article_id', 'doi', score_col, 'label_true', 'field', 'SDL_Brown', 'SDL_Tomet']
if 'title' in df.columns:
    export_cols.insert(2, 'title')

top_100[export_cols].to_csv(top_100_path, index=False)
print(f"  ✓ Top 100: {top_100_path}")

# Summary
summary = {
    'Total Papers': len(df),
    'Known SDL': n_sdl,
    'Brown only': n_brown - n_both,
    'Tomet only': n_tomet - n_both,
    'Both sources': n_both,
    'High Confidence (>0.9)': int((df[score_col] > 0.9).sum()),
    'Known SDL Recall @0.9': f"{(known_sdl[score_col] > 0.9).sum() / len(known_sdl) * 100:.1f}%",
    'Mean Score (All)': f"{df[score_col].mean():.4f}",
    'Mean Score (Known SDL)': f"{known_sdl[score_col].mean():.4f}",
    'Mean Score (Background)': f"{background[score_col].mean():.4f}"
}

summary_df = pd.DataFrame([summary]).T
summary_df.columns = ['Value']
summary_path = f"{OUTPUT_DIR}/summary_statistics.csv"
summary_df.to_csv(summary_path)
print(f"  ✓ Summary: {summary_path}")

# ==============================================================================
# DIAGNOSTICS
# ==============================================================================

print("\n" + "="*70)
print("DIAGNOSTICS")
print("="*70)
print("\nKey Flags:")
print(f"  1. >50k papers scoring >0.9?           {'RED FLAG' if (df[score_col] > 0.9).sum() > 50000 else 'OK'}")
print(f"  2. Known SDL recall @0.9 >75%?         {'GOOD' if (known_sdl[score_col] > 0.9).sum() / len(known_sdl) > 0.75 else 'NEEDS WORK'}")
print(f"  3. Log-odds show SDL terms?            {'Check log_odds file' if has_text else 'N/A'}")

print("\n" + "="*70 + "\n")
