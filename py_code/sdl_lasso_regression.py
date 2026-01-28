# import pandas as pd
# import numpy as np
# from pathlib import Path
# import sys
# import nltk
# from nltk.corpus import stopwords
# from sklearn.feature_extraction.text import CountVectorizer
# from sklearn.linear_model import LogisticRegressionCV
# from sklearn.model_selection import train_test_split
# from scipy import sparse
# import joblib

# # ============================================================================
# # CONFIGURATION
# # ============================================================================

# PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# # Input: Latest version of your regression dataset (v3 has the robot/sdl counts, but v2 is fine too)
# # Using v3 as it is the most recent
# REGRESSION_DATA = PROJECT_DIR / "data/regression/test/regression_dataset_subset.csv"

# # Output directory for SDL lasso results
# OUTPUT_DIR = PROJECT_DIR / "data/lasso_regression/sdl" 
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# # Sampling Rate for Negatives (as requested)
# NEGATIVE_SAMPLE_RATE = 0.05  # 5%

# # ============================================================================
# # STEP 1: BUILD FEATURE MATRIX (VECTORIZE)
# # ============================================================================

# def build_feature_matrix():
#     print("=" * 80)
#     print("STEP 1: BUILDING DATASET & FEATURE MATRIX")
#     print("=" * 80)
    
#     # 1. Load Data
#     print(f"Loading data from {REGRESSION_DATA}...")
#     if not REGRESSION_DATA.exists():
#         print(f"❌ Error: File not found.")
#         sys.exit(1)
        
#     df_full = pd.read_csv(REGRESSION_DATA, low_memory=False)
#     print(f"  ✓ Loaded {len(df_full):,} total papers.")

#     # 2. Filter Data (Create Contrast Set)
#     print("\nCreating Training Set:")
    
#     # Positives: All SDL papers (SDL=1)
#     # We use .copy() to avoid SettingWithCopy warnings
#     positives = df_full[df_full['SDL'] == 1].copy()
    
#     # Negatives: Non-SDL papers (SDL=0) from Chemistry OR Materials Science
#     # We intentionally exclude CS/Engineering to force the model to find "Science" keywords vs "Automated Science" keywords
#     negative_pool = df_full[
#         (df_full['SDL'] == 0) & 
#         (df_full['field'].isin(['chemistry', 'materials_science']))
#     ]
    
#     # Sample 5% of negatives
#     negatives = negative_pool.sample(frac=NEGATIVE_SAMPLE_RATE, random_state=42).copy()
    
#     # Combine and Shuffle
#     df = pd.concat([positives, negatives]).sample(frac=1, random_state=42).reset_index(drop=True)
    
#     # Calculate Labels
#     y = df['SDL'].values
    
#     print(f"  ✓ Positives (SDL=1): {len(positives):,}")
#     print(f"  ✓ Negatives (SDL=0): {len(negatives):,} (sampled from {len(negative_pool):,})")
#     print(f"  ✓ Total Training Size: {len(df):,}")
#     print(f"  ✓ Class Balance: {y.mean()*100:.2f}% Positive")

#     # 3. Prepare Text
#     print("\nPreparing text fields...")
#     # Clean topics (replace pipe with space)
#     df['topics_clean'] = df['all_topics'].fillna('').str.replace('|', ' ', regex=False)
    
#     # Combine: title + abstract + topics
#     df['text'] = (
#         df['title'].fillna('') + ' ' +
#         df['abstract'].fillna('') + ' ' +
#         df['topics_clean']
#     )
    
#     # 4. Vectorize
#     print("\nVectorizing text (Unigrams + Bigrams)...")
    
#     # Load Stopwords
#     try:
#         stop_words = list(stopwords.words('english'))
#     except:
#         print("  Downloading NLTK stopwords...")
#         nltk.download('stopwords')
#         stop_words = list(stopwords.words('english'))
        
#     # Custom vectorizer settings (Matched to your CS Code)
#     vectorizer = CountVectorizer(
#         ngram_range=(3, 5),
#         max_features=20000,    # Kept same as CS code
#         min_df=3,              # Kept same as CS code
#         stop_words=stop_words,
#         lowercase=True
#     )
    
#     X = vectorizer.fit_transform(df['text'])
    
#     print(f"  ✓ Feature Matrix Shape: {X.shape[0]:,} rows × {X.shape[1]:,} features")
    
#     # 5. Save Outputs
#     print("\nSaving intermediate files...")
#     sparse.save_npz(OUTPUT_DIR / "X_features.npz", X)
#     pd.Series(y, name='SDL').to_csv(OUTPUT_DIR / "y_labels.csv", index=False)
#     joblib.dump(vectorizer, OUTPUT_DIR / "vectorizer.joblib")
    
#     # Save IDs so we know exactly which papers were used in training
#     df[['article_id', 'doi', 'SDL', 'field', 'publication_year']].to_csv(OUTPUT_DIR / "training_metadata.csv", index=False)
    
#     print("✅ Feature Matrix Complete.\n")
#     return X, y, vectorizer

# # ============================================================================
# # STEP 2: FIT LASSO-LOGISTIC REGRESSION
# # ============================================================================

# def fit_lasso_logistic():
#     print("=" * 80)
#     print("STEP 2: FITTING LASSO-LOGISTIC REGRESSION")
#     print("=" * 80)
    
#     # 1. Load Data
#     X_file = OUTPUT_DIR / "X_features.npz"
#     if not X_file.exists():
#         print("❌ Feature matrix not found. Run Step 1 first.")
#         sys.exit(1)
        
#     X = sparse.load_npz(X_file)
#     y = pd.read_csv(OUTPUT_DIR / "y_labels.csv")['SDL'].values
#     vectorizer = joblib.load(OUTPUT_DIR / "vectorizer.joblib")
    
#     # 2. Train/Test Split
#     # Stratify is CRITICAL here because positives are rare
#     X_train, X_test, y_train, y_test = train_test_split(
#         X, y, test_size=0.25, random_state=42, stratify=y
#     )
    
#     print(f"  Train: {X_train.shape[0]:,} papers ({y_train.sum()} SDL)")
#     print(f"  Test:  {X_test.shape[0]:,} papers ({y_test.sum()} SDL)")
    
#     # 3. Fit Model
#     print("\nFitting Model (L1 Penalty, Balanced Class Weights)...")
#     print("  Note: Using 'balanced' weights to handle 1:12 class imbalance.")
    
#     model = LogisticRegressionCV(
#         penalty='l1',
#         solver='saga',
#         cv=5,
#         Cs=10,
#         class_weight='balanced',  # <--- CRITICAL CHANGE for SDL vs CS
#         random_state=42,
#         max_iter=2000,            # Increased iter for convergence with sparse data
#         n_jobs=-1,
#         verbose=1
#     )
    
#     model.fit(X_train, y_train)
#     print(f"  ✓ Model fitted. Best C: {model.C_[0]:.4f}")
    
#     # 4. Metrics
#     train_score = model.score(X_train, y_train)
#     test_score = model.score(X_test, y_test)
#     print(f"\n  Accuracy:")
#     print(f"    Train: {train_score:.2%}")
#     print(f"    Test:  {test_score:.2%}")
    
#     # 5. Extract Coefficients
#     print("\nExtracting coefficients...")
#     feature_names = vectorizer.get_feature_names_out()
#     coefs = model.coef_[0]
    
#     # Create DataFrame
#     word_imp = pd.DataFrame({
#         'word': feature_names,
#         'coefficient': coefs,
#         'abs_coefficient': np.abs(coefs)
#     }).sort_values('coefficient', ascending=False)
    
#     # Add category label
#     word_imp['category'] = 'neutral'
#     word_imp.loc[word_imp['coefficient'] > 0, 'category'] = 'SDL-predictive'
#     word_imp.loc[word_imp['coefficient'] < 0, 'category'] = 'Non-SDL-predictive'

#     # Stats
#     non_zero = (coefs != 0).sum()
#     sdl_words = (coefs > 0).sum()
    
#     print(f"  Non-zero coefficients: {non_zero:,}")
#     print(f"  SDL-Predictive words:  {sdl_words:,}")
    
#     # 6. Save Outputs
#     joblib.dump(model, OUTPUT_DIR / "lasso_model.joblib")
#     word_imp.to_csv(OUTPUT_DIR / "word_importance.csv", index=False)
    
#     # Create Summary Text File (Same format as CS)
#     summary_file = OUTPUT_DIR / "model_summary.txt"
#     with open(summary_file, 'w') as f:
#         f.write("SDL LASSO-LOGISTIC MODEL SUMMARY\n")
#         f.write("=" * 80 + "\n\n")
#         f.write(f"Training samples: {X_train.shape[0]:,}\n")
#         f.write(f"Test samples: {X_test.shape[0]:,}\n")
#         f.write(f"Features: {X_train.shape[1]:,}\n")
#         f.write(f"Best C: {model.C_[0]:.6f}\n\n")
#         f.write(f"Training accuracy: {100*train_score:.2f}%\n")
#         f.write(f"Test accuracy: {100*test_score:.2f}%\n\n")
#         f.write(f"Non-zero coefficients: {non_zero:,}\n")
#         f.write(f"  SDL-predictive words: {sdl_words:,}\n")
#         f.write("TOP 50 SDL-DISCRIMINATIVE WORDS:\n")
#         f.write("-" * 80 + "\n")
#         top_50 = word_imp[word_imp['coefficient'] > 0].head(50)
#         for _, row in top_50.iterrows():
#             f.write(f"{row['word']:<30} {row['coefficient']:>10.4f}\n")
            
#     print(f"  ✓ Model summary saved to: {summary_file}")
#     print("✅ Model Fitting Complete.\n")
#     return model, word_imp

# # ============================================================================
# # STEP 3: ANALYZE & FILTER KEYWORDS
# # ============================================================================

# def analyze_keywords():
#     print("=" * 80)
#     print("STEP 3: ANALYZING & FILTERING KEYWORDS")
#     print("=" * 80)
    
#     # 1. Load Results
#     df = pd.read_csv(OUTPUT_DIR / "word_importance.csv")
    
#     # 2. Filter for Positive (SDL-Predictive) Words
#     sdl_words = df[df['coefficient'] > 0].copy()
    
#     # 3. Create Threshold Columns (Same as CS code)
#     sdl_words['threshold_all'] = sdl_words['coefficient'] > 0.0
#     sdl_words['threshold_weak'] = sdl_words['coefficient'] > 0.1
#     sdl_words['threshold_moderate'] = sdl_words['coefficient'] > 0.5
#     sdl_words['threshold_strong'] = sdl_words['coefficient'] > 1.0
    
#     # 4. Save Filtered List
#     output_file = OUTPUT_DIR / "sdl_keywords_filtered.csv"
#     sdl_words.to_csv(output_file, index=False)
#     print(f"  ✓ Saved comprehensive list: {output_file}")
    
#     # 5. Save Recommended List (Coefficient > 0.1)
#     # Note: 0.1 is a safer cutoff for small data than 0.5, but you can adjust
#     recommended = sdl_words[sdl_words['coefficient'] > 0.1]
    
#     txt_file = OUTPUT_DIR / "sdl_keywords_recommended.txt"
#     with open(txt_file, 'w') as f:
#         f.write(f"# SDL-discriminative keywords (coefficient > 0.1)\n")
#         f.write(f"# Total: {len(recommended):,} words\n\n")
#         for word in recommended['word']:
#             f.write(f"{word}\n")
            
#     print(f"  ✓ Saved recommended list: {txt_file}")
    
#     # 6. Display Top Words
#     print("\nTOP 50 SDL WORDS:")
#     print("-" * 50)
#     print(sdl_words.head(50)[['word', 'coefficient']].to_string(index=False))
#     print("-" * 50)

# # ============================================================================
# # MAIN
# # ============================================================================

# if __name__ == "__main__":
#     # Run full pipeline
#     build_feature_matrix()
#     fit_lasso_logistic()
#     analyze_keywords()


## PHRASE MINING APPROACH

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# Input: Same dataset used for Lasso
REGRESSION_DATA = PROJECT_DIR / "data/regression/test/regression_dataset_subset.csv"

# Output directory
OUTPUT_DIR = PROJECT_DIR / "data/phrase_mining"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Sampling Rate for Background Set (Negatives)
# Using same 5% logic as Lasso to keep comparisons fair
NEGATIVE_SAMPLE_RATE = 0.05 

# Phrase Settings
MIN_PHRASE_LENGTH = 2   # Minimum words (e.g. "closed loop")
MAX_PHRASE_LENGTH = 4   # Maximum words (e.g. "autonomous closed loop optimization")
MIN_SDL_PAPERS = 2      # Phrase must appear in at least this many SDL papers

# ============================================================================
# STEP 1: PREPARE DATA (TARGET VS BACKGROUND)
# ============================================================================

def get_text_data():
    print("=" * 80)
    print("STEP 1: PREPARING TARGET VS BACKGROUND DATA")
    print("=" * 80)
    
    # 1. Load Data
    print(f"Loading data from {REGRESSION_DATA}...")
    if not REGRESSION_DATA.exists():
        print(f"❌ Error: File not found.")
        sys.exit(1)
        
    df_full = pd.read_csv(REGRESSION_DATA, low_memory=False)
    print(f"  ✓ Loaded {len(df_full):,} total papers.")

    # 2. Split Data (Same logic as Lasso)
    print("\nCreating Comparison Sets:")
    
    # Target: All SDL papers (SDL=1)
    positives = df_full[df_full['SDL'] == 1].copy()
    
    # Background: Non-SDL papers from Chem OR MatSci
    # (Matches your Lasso logic: excluding CS/Eng to compare against "Standard Science")
    negative_pool = df_full[
        (df_full['SDL'] == 0) & 
        (df_full['field'].isin(['chemistry', 'materials_science']))
    ]
    
    # Sample negatives
    negatives = negative_pool.sample(frac=NEGATIVE_SAMPLE_RATE, random_state=42).copy()
    
    print(f"  ✓ Target (SDL):      {len(positives):,} papers")
    print(f"  ✓ Background (Neg):  {len(negatives):,} papers (sampled from {len(negative_pool):,})")

    # 3. Clean Text Helper
    def clean_text(df):
        return (
            df['title'].fillna('') + ' ' + 
            df['abstract'].fillna('') + ' ' + 
            df['all_topics'].fillna('').str.replace('|', ' ', regex=False)
        )

    text_sdl = clean_text(positives)
    text_neg = clean_text(negatives)
    
    return text_sdl, text_neg

# ============================================================================
# STEP 2: EXTRACT AND COUNT PHRASES
# ============================================================================

def extract_phrases():
    print("\n" + "=" * 80)
    print("STEP 2: VECTORIZING & COUNTING PHRASES")
    print("=" * 80)
    
    text_sdl, text_neg = get_text_data()
    
    print(f"\nVectorizing phrases ({MIN_PHRASE_LENGTH}-{MAX_PHRASE_LENGTH} words)...")
    
    # Load Stopwords
    try:
        stop_words = list(stopwords.words('english'))
    except:
        print("  Downloading NLTK stopwords...")
        nltk.download('stopwords')
        stop_words = list(stopwords.words('english'))

    # Add generic academic stopwords to reduce noise
    # (Phrases like "in this paper" or "using a new" are distinctive but useless)
    custom_stops = stop_words + [
        'paper', 'study', 'results', 'using', 'used', 'method', 'based', 
        'new', 'reported', 'demonstrate', 'proposed', 'analysis', 'high', 'low',
        'via', 'due', 'show', 'approach', 'system', 'process', 'application'
    ]

    # Initialize Vectorizer
    # We fit ONLY on SDL papers first. We only care about phrases that actually exist in SDL.
    vectorizer = CountVectorizer(
        ngram_range=(MIN_PHRASE_LENGTH, MAX_PHRASE_LENGTH),
        min_df=MIN_SDL_PAPERS,   # Must appear in X SDL papers to matter
        stop_words=custom_stops,
        max_features=100000      # Cap at 100k phrases to save memory
    )
    
    print("  Fitting vocabulary on SDL papers...")
    X_sdl = vectorizer.fit_transform(text_sdl)
    vocab = vectorizer.get_feature_names_out()
    
    print(f"  ✓ Found {len(vocab):,} candidate phrases in SDL set.")
    
    print("  Counting frequencies in Background set...")
    # Use the same vocabulary to count occurences in the negative set
    X_neg = vectorizer.transform(text_neg)
    
    return vocab, X_sdl, X_neg

# ============================================================================
# STEP 3: CALCULATE DISTINCTIVENESS
# ============================================================================

def calculate_stats(vocab, X_sdl, X_neg):
    print("\n" + "=" * 80)
    print("STEP 3: CALCULATING DISTINCTIVENESS RATIOS")
    print("=" * 80)
    
    # 1. Sum counts per phrase
    counts_sdl = np.array(X_sdl.sum(axis=0)).flatten()
    counts_neg = np.array(X_neg.sum(axis=0)).flatten()
    
    # 2. Normalize (Term Frequency)
    # We must normalize because the Negative set is much larger (600 vs 7000)
    total_phrases_sdl = counts_sdl.sum()
    total_phrases_neg = counts_neg.sum()
    
    tf_sdl = counts_sdl / total_phrases_sdl
    tf_neg = counts_neg / total_phrases_neg
    
    print(f"  Total phrase occurrences (SDL): {total_phrases_sdl:,}")
    print(f"  Total phrase occurrences (Neg): {total_phrases_neg:,}")
    
    # 3. Calculate Ratio
    # Formula: (Freq in SDL) / (Freq in Background)
    # Add tiny epsilon to avoid division by zero
    epsilon = 1e-9
    distinctiveness = tf_sdl / (tf_neg + epsilon)
    
    # 4. Create DataFrame
    results = pd.DataFrame({
        'phrase': vocab,
        'count_in_sdl': counts_sdl,
        'count_in_neg': counts_neg,
        'distinctiveness_score': distinctiveness
    })
    
    return results

# ============================================================================
# STEP 4: FILTER AND SAVE
# ============================================================================

def filter_and_save(results):
    print("\n" + "=" * 80)
    print("STEP 4: FILTERING AND SAVING")
    print("=" * 80)
    
    # Filter: Must be >10x more likely in SDL than Background
    # This kills "battery materials" (ratio ~1) and keeps "self driving" (ratio >100)
    filtered = results[results['distinctiveness_score'] > 10].copy()
    
    # Ranking Score: Balance "Uniqueness" with "Frequency"
    # We want phrases that are unique AND appear often.
    # Score = Ratio * log(Count)
    filtered['final_score'] = filtered['distinctiveness_score'] * np.log(filtered['count_in_sdl'])
    
    filtered = filtered.sort_values('final_score', ascending=False)
    
    # Save CSV
    out_csv = OUTPUT_DIR / "distinctive_sdl_phrases.csv"
    filtered.to_csv(out_csv, index=False)
    print(f"  ✓ Saved full analysis: {out_csv}")
    
    # Save Top 100 Recommended List
    out_txt = OUTPUT_DIR / "sdl_phrases_recommended.txt"
    with open(out_txt, 'w') as f:
        f.write(f"# Top 100 Distinctive Phrases (Ratio > 10)\n")
        f.write(f"# Generated from {len(filtered)} candidates\n\n")
        for phrase in filtered.head(100)['phrase']:
            f.write(f"{phrase}\n")
            
    print(f"  ✓ Saved top 100 list: {out_txt}")
    
    # Display Preview
    print("\nTOP 20 DISTINCTIVE PHRASES PREVIEW:")
    print("-" * 90)
    print(f"{'PHRASE':<45} | {'SDL COUNT':<10} | {'RATIO (x times more likely)':<25}")
    print("-" * 90)
    for _, row in filtered.head(20).iterrows():
        print(f"{row['phrase']:<45} | {row['count_in_sdl']:<10} | {row['distinctiveness_score']:.1f}x")
    print("-" * 90)
    print("\n✅ PHRASE MINING COMPLETE")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    vocab, X_sdl, X_neg = extract_phrases()
    results = calculate_stats(vocab, X_sdl, X_neg)
    filter_and_save(results)