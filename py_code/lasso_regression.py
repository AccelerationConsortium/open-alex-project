import pandas as pd
import numpy as np
from pathlib import Path
import sys
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegressionCV
from sklearn.model_selection import train_test_split
from scipy import sparse
import joblib

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# Input: Your regression dataset with abstracts (490k papers)
REGRESSION_DATA = PROJECT_DIR / "data" / "regression/test" / "regression_dataset_filtered.csv"

# Output directory
OUTPUT_DIR = PROJECT_DIR / "data/lasso_regression/test" 
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# STEP 1: BUILD FEATURE MATRIX (VECTORIZE)
# ============================================================================

def build_feature_matrix():
    """Vectorize text data into document-term matrix"""
    
    print("=" * 80)
    print("BUILDING FEATURE MATRIX (VECTORIZATION)")
    print("=" * 80)
    
    # ========================================================================
    # STEP 1: Load regression dataset
    # ========================================================================
    
    print(f"\nSTEP 1: Loading regression dataset")
    print("=" * 80)
    
    if not REGRESSION_DATA.exists():
        print(f"  ✗ ERROR: Regression dataset not found: {REGRESSION_DATA}")
        sys.exit(1)
    
    df = pd.read_csv(REGRESSION_DATA, low_memory=False)
    print(f"  ✓ Loaded {len(df):,} papers")
    
    # ========================================================================
    # STEP 2: Combine text fields & create labels
    # ========================================================================
    
    print(f"\nSTEP 2: Preparing text and labels")
    print("=" * 80)
    
    # Clean topics (replace pipe with space)
    df['topics_clean'] = df['all_topics'].fillna('').str.replace('|', ' ', regex=False)
    
    # Combine: title + abstract + topics
    df['text'] = (
        df['title'].fillna('') + ' ' +
        df['abstract'].fillna('') + ' ' +
        df['topics_clean']
    )
    
    # Create labels
    df['is_CS'] = (df['field'] == 'computer_science').astype(int)
    
    print(f"  ✓ Combined title + abstract + topics")
    print(f"\n  Class distribution:")
    print(f"    CS papers (y=1):     {df['is_CS'].sum():,} ({100*df['is_CS'].mean():.1f}%)")
    print(f"    Non-CS papers (y=0): {(1-df['is_CS']).sum():,} ({100*(1-df['is_CS'].mean()):.1f}%)")
    
    # ========================================================================
    # STEP 3: Vectorize with NLTK stopwords
    # ========================================================================
    
    print(f"\nSTEP 3: Vectorizing text")
    print("=" * 80)
    
    # Get NLTK stopwords
    try:
        stop_words = list(stopwords.words('english'))
        print(f"  ✓ Loaded {len(stop_words)} NLTK English stopwords")
    except:
        print("  ⚠ NLTK stopwords not found. Downloading...")
        nltk.download('stopwords')
        stop_words = list(stopwords.words('english'))
    
    print(f"\n  Settings: unigrams + bigrams, max 20k features, min_df=3")
    print(f"  Fitting vectorizer...")
    
    vectorizer = CountVectorizer(
        ngram_range=(1, 2),
        max_features=20000,
        min_df=3,
        stop_words=stop_words,
        lowercase=True
    )
    
    X = vectorizer.fit_transform(df['text'])
    y = df['is_CS'].values
    
    print(f"\n  ✓ Feature matrix: {X.shape[0]:,} papers × {X.shape[1]:,} features")
    
    # ========================================================================
    # STEP 4: Save outputs
    # ========================================================================
    
    print(f"\nSTEP 4: Saving outputs")
    print("=" * 80)
    
    # Save sparse matrix
    sparse_file = OUTPUT_DIR / "X_features.npz"
    sparse.save_npz(sparse_file, X)
    print(f"  ✓ Feature matrix: {sparse_file}")
    
    # Save labels
    labels_file = OUTPUT_DIR / "y_labels.csv"
    pd.Series(y, name='is_CS').to_csv(labels_file, index=False)
    print(f"  ✓ Labels: {labels_file}")
    
    # Save vectorizer
    vectorizer_file = OUTPUT_DIR / "vectorizer.joblib"
    joblib.dump(vectorizer, vectorizer_file)
    print(f"  ✓ Vectorizer: {vectorizer_file}")
    
    # Save article IDs for reference
    ids_file = OUTPUT_DIR / "article_ids.csv"
    df[['article_id', 'field']].to_csv(ids_file, index=False)
    print(f"  ✓ Article IDs: {ids_file}")
    
    print(f"\n{'=' * 80}")
    print("✅ FEATURE MATRIX COMPLETE\n")
    
    return X, y, vectorizer


# ============================================================================
# STEP 2: FIT LASSO-LOGISTIC REGRESSION
# ============================================================================

def fit_lasso_logistic():
    """Fit Lasso-Logistic regression to identify discriminative CS keywords"""
    
    print("=" * 80)
    print("FITTING LASSO-LOGISTIC REGRESSION")
    print("=" * 80)
    
    # ========================================================================
    # STEP 1: Load feature matrix and labels
    # ========================================================================
    
    print(f"\nSTEP 1: Loading data")
    print("=" * 80)
    
    X_file = OUTPUT_DIR / "X_features.npz"
    y_file = OUTPUT_DIR / "y_labels.csv"
    vectorizer_file = OUTPUT_DIR / "vectorizer.joblib"
    
    if not X_file.exists() or not y_file.exists():
        print(f"  ✗ ERROR: Feature files not found.")
        print("  Run build_feature_matrix() first.")
        sys.exit(1)
    
    X = sparse.load_npz(X_file)
    y = pd.read_csv(y_file)['is_CS'].values
    vectorizer = joblib.load(vectorizer_file)
    
    print(f"  ✓ Loaded feature matrix: {X.shape[0]:,} papers × {X.shape[1]:,} features")
    
    # # ========================================================================
    # # STEP 2: Train/test split
    # # ========================================================================
    
    # print(f"\nSTEP 2: Train/test split")
    # print("=" * 80)
    
    # X_train, X_test, y_train, y_test = train_test_split(
    #     X, y,
    #     test_size=0.25,
    #     random_state=42,
    #     train_size=100000,
    #     stratify=y
    # )


    # Optional: Sample data for faster training
    SAMPLE_SIZE = 100000  # Set to None to use full dataset
    if SAMPLE_SIZE and len(y) > SAMPLE_SIZE:
        print(f"  ⚠ Sampling {SAMPLE_SIZE:,} papers from {len(y):,} for faster training")
        X, _, y, _ = train_test_split(X, y, train_size=SAMPLE_SIZE, stratify=y, random_state=42)
        print(f"  ✓ Sampled to: {X.shape[0]:,} papers")

    # ========================================================================
    # STEP 2: Train/test split
    # ========================================================================

    print(f"\nSTEP 2: Train/test split")
    print("=" * 80)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.25,
        random_state=42,
        stratify=y
    )
    
    print(f"  Train: {X_train.shape[0]:,} papers ({100*y_train.mean():.1f}% CS)")
    print(f"  Test:  {X_test.shape[0]:,} papers ({100*y_test.mean():.1f}% CS)")
    
    # ========================================================================
    # STEP 3: Fit Lasso-Logistic with cross-validation
    # ========================================================================
    
    print(f"\nSTEP 3: Fitting Lasso-Logistic regression")
    print("=" * 80)
    
    print(f"  Settings: L1 penalty, 5-fold CV, saga solver")
    print(f"  Fitting model (this may take 30-60 minutes)...")
    
    model = LogisticRegressionCV(
        penalty='l1',
        solver='saga',
        cv=5,
        Cs=5,
        random_state=42,
        max_iter=1000,
        n_jobs=-1,
        verbose=1
    )
    
    model.fit(X_train, y_train)
    
    print(f"\n  ✓ Model fitted. Best C = {model.C_[0]:.6f}")
    
    # ========================================================================
    # STEP 4: Evaluate model
    # ========================================================================
    
    print(f"\nSTEP 4: Evaluating model")
    print("=" * 80)
    
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    print(f"\n  Accuracy:")
    print(f"    Training: {100*train_score:.2f}%")
    print(f"    Test:     {100*test_score:.2f}%")
    
    # Predictions for more metrics
    y_pred = model.predict(X_test)
    
    from sklearn.metrics import classification_report, confusion_matrix
    
    print(f"\n  Classification Report (Test Set):")
    print(classification_report(y_test, y_pred, target_names=['Non-CS', 'CS']))
    
    # ========================================================================
    # STEP 5: Extract discriminative words
    # ========================================================================
    
    print(f"\nSTEP 5: Extracting discriminative words")
    print("=" * 80)
    
    feature_names = vectorizer.get_feature_names_out()
    coefficients = model.coef_[0]
    
    # Create DataFrame with all word importance info
    word_importance = pd.DataFrame({
        'word': feature_names,
        'coefficient': coefficients,
        'abs_coefficient': np.abs(coefficients)
    })
    
    # Sort by coefficient (descending)
    word_importance = word_importance.sort_values('coefficient', ascending=False)
    
    # Add category label
    word_importance['category'] = 'neutral'
    word_importance.loc[word_importance['coefficient'] > 0, 'category'] = 'CS-predictive'
    word_importance.loc[word_importance['coefficient'] < 0, 'category'] = 'non-CS-predictive'
    
    # Count non-zero coefficients
    non_zero = (coefficients != 0).sum()
    cs_words = (coefficients > 0).sum()
    non_cs_words = (coefficients < 0).sum()
    
    print(f"\n  Total features: {len(coefficients):,}")
    print(f"  Non-zero coefficients: {non_zero:,} ({100*non_zero/len(coefficients):.1f}%)")
    print(f"    CS-predictive (positive): {cs_words:,}")
    print(f"    Non-CS-predictive (negative): {non_cs_words:,}")
    
    print(f"\n  Top 30 CS-discriminative words:")
    print(word_importance[word_importance['coefficient'] > 0].head(30)[['word', 'coefficient']].to_string(index=False))
    
    # ========================================================================
    # STEP 6: Save outputs
    # ========================================================================
    
    print(f"\nSTEP 6: Saving outputs")
    print("=" * 80)
    
    # Save model
    model_file = OUTPUT_DIR / "lasso_model.joblib"
    joblib.dump(model, model_file)
    print(f"  ✓ Model: {model_file}")
    
    # Save comprehensive word importance file (all words, all metrics)
    importance_file = OUTPUT_DIR / "word_importance.csv"
    word_importance.to_csv(importance_file, index=False)
    print(f"  ✓ Word importance (all): {importance_file}")
    
    # Save model summary with key metrics
    summary_file = OUTPUT_DIR / "model_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("LASSO-LOGISTIC MODEL SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Training samples: {X_train.shape[0]:,}\n")
        f.write(f"Test samples: {X_test.shape[0]:,}\n")
        f.write(f"Features: {X_train.shape[1]:,}\n")
        f.write(f"Best C: {model.C_[0]:.6f}\n\n")
        f.write(f"Training accuracy: {100*train_score:.2f}%\n")
        f.write(f"Test accuracy: {100*test_score:.2f}%\n\n")
        f.write(f"Non-zero coefficients: {non_zero:,}\n")
        f.write(f"  CS-predictive words: {cs_words:,}\n")
        f.write(f"  Non-CS-predictive words: {non_cs_words:,}\n")
        f.write(f"Eliminated by Lasso: {len(coefficients) - non_zero:,}\n\n")
        f.write("TOP 50 CS-DISCRIMINATIVE WORDS:\n")
        f.write("-" * 80 + "\n")
        top_50 = word_importance[word_importance['coefficient'] > 0].head(50)
        for _, row in top_50.iterrows():
            f.write(f"{row['word']:<30} {row['coefficient']:>10.4f}\n")
    print(f"  ✓ Model summary: {summary_file}")
    
    print(f"\n{'=' * 80}")
    print("✅ LASSO-LOGISTIC REGRESSION COMPLETE\n")
    
    return model, word_importance


# ============================================================================
# STEP 3: ANALYZE AND FILTER KEYWORDS
# ============================================================================

def analyze_keywords():
    """Analyze extracted keywords and apply coefficient threshold filters"""
    
    print("=" * 80)
    print("ANALYZING CS KEYWORDS")
    print("=" * 80)
    
    # ========================================================================
    # STEP 1: Load word importance
    # ========================================================================
    
    print(f"\nSTEP 1: Loading word importance data")
    print("=" * 80)
    
    importance_file = OUTPUT_DIR / "word_importance.csv"
    
    if not importance_file.exists():
        print(f"  ✗ ERROR: Word importance file not found.")
        print("  Run fit_lasso_logistic() first.")
        sys.exit(1)
    
    df = pd.read_csv(importance_file)
    print(f"  ✓ Loaded {len(df):,} words")
    
    # ========================================================================
    # STEP 2: Filter by coefficient threshold
    # ========================================================================
    
    print(f"\nSTEP 2: Filtering by coefficient threshold")
    print("=" * 80)
    
    # Only positive coefficients (CS-predictive)
    cs_words = df[df['coefficient'] > 0].copy()
    print(f"  Total CS-predictive words: {len(cs_words):,}")
    
    # Different thresholds
    thresholds = [0.0, 0.1, 0.5, 1.0, 2.0]
    
    print(f"\n  Words remaining at different thresholds:")
    for thresh in thresholds:
        count = (cs_words['coefficient'] > thresh).sum()
        print(f"    coef > {thresh:>3}: {count:>5,} words")
    
    # ========================================================================
    # STEP 3: Create filtered keyword lists
    # ========================================================================
    
    print(f"\nSTEP 3: Creating filtered keyword lists")
    print("=" * 80)
    
    # Apply different coefficient thresholds
    filters = {
        'all': 0.0,
        'weak': 0.1,
        'moderate': 0.5,
        'strong': 1.0
    }
    
    results = {}
    
    for name, threshold in filters.items():
        filtered = cs_words[cs_words['coefficient'] > threshold]
        results[name] = filtered
        print(f"  {name:>10} filter (coef > {threshold}): {len(filtered):>5,} words")
    
    # Save comprehensive results file with threshold annotations
    output_file = OUTPUT_DIR / "cs_keywords_filtered.csv"
    
    # Add threshold columns to original cs_words
    cs_words['threshold_all'] = cs_words['coefficient'] > 0.0
    cs_words['threshold_weak'] = cs_words['coefficient'] > 0.1
    cs_words['threshold_moderate'] = cs_words['coefficient'] > 0.5
    cs_words['threshold_strong'] = cs_words['coefficient'] > 1.0
    
    cs_words.to_csv(output_file, index=False)
    print(f"\n  ✓ Saved: {output_file}")
    
    # Also save simple text file with recommended keywords (moderate threshold)
    txt_file = OUTPUT_DIR / "cs_keywords_recommended.txt"
    with open(txt_file, 'w') as f:
        f.write(f"# CS-discriminative keywords (coefficient > 0.5)\n")
        f.write(f"# Total: {len(results['moderate']):,} words\n\n")
        for word in results['moderate']['word'].tolist():
            f.write(f"{word}\n")
    print(f"  ✓ Saved: {txt_file}")
    
    # ========================================================================
    # STEP 4: Show top discriminative words
    # ========================================================================
    
    print(f"\nSTEP 4: Top CS-discriminative words")
    print("=" * 80)
    
    print(f"\n  Top 50 words (moderate filter, coef > 0.5):")
    print(results['moderate'].head(50)[['word', 'coefficient']].to_string(index=False))
    
    print(f"\n{'=' * 80}")
    print("✅ KEYWORD ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nOutputs:")
    print(f"  - cs_keywords_filtered.csv (all CS words with threshold indicators)")
    print(f"  - cs_keywords_recommended.txt ({len(results['moderate']):,} words, coef > 0.5)\n")
    
    return cs_words, results


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    
    # STEP 1: Build feature matrix (vectorize)
    # build_feature_matrix()
    
    # STEP 2: Fit Lasso-Logistic regression
    fit_lasso_logistic()
    
    # STEP 3: Analyze and filter keywords
    analyze_keywords()