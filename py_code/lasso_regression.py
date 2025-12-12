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
REGRESSION_DATA = PROJECT_DIR / "data" / "regression" / "regression_dataset_subset.csv"

# Output directory
OUTPUT_DIR = PROJECT_DIR / "data/lasso_regression/sample" 
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
    
    print(f"\n{'=' * 80}")
    print("STEP 1: Loading regression dataset")
    print("=" * 80)
    
    if not REGRESSION_DATA.exists():
        print(f"  ✗ ERROR: Regression dataset not found: {REGRESSION_DATA}")
        sys.exit(1)
    
    df = pd.read_csv(REGRESSION_DATA, low_memory=False)
    print(f"  ✓ Loaded {len(df):,} papers")
    
    # ========================================================================
    # STEP 2: Combine text fields
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 2: Combining text fields")
    print("=" * 80)
    
    # Clean topics (replace pipe with space)
    df['topics_clean'] = df['all_topics'].fillna('').str.replace('|', ' ', regex=False)
    
    # Combine: title + abstract + topics
    df['text'] = (
        df['title'].fillna('') + ' ' +
        df['abstract'].fillna('') + ' ' +
        df['topics_clean']
    )
    
    print(f"  ✓ Combined title + abstract + topics")
    print(f"\n  Sample text (first 300 chars):")
    print(f"  {df['text'].iloc[0][:300]}...")
    
    # ========================================================================
    # STEP 3: Create labels
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 3: Creating labels")
    print("=" * 80)
    
    df['is_CS'] = (df['field'] == 'computer_science').astype(int)
    
    print(f"\n  Class distribution:")
    print(f"    CS papers (y=1):     {df['is_CS'].sum():,} ({100*df['is_CS'].mean():.1f}%)")
    print(f"    Non-CS papers (y=0): {(1-df['is_CS']).sum():,} ({100*(1-df['is_CS'].mean()):.1f}%)")
    
    # ========================================================================
    # STEP 4: Vectorize with NLTK stopwords
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 4: Vectorizing text")
    print("=" * 80)
    
    # Get NLTK stopwords
    try:
        stop_words = list(stopwords.words('english'))
        print(f"  ✓ Loaded {len(stop_words)} NLTK English stopwords")
    except:
        print("  ⚠ NLTK stopwords not found. Downloading...")
        nltk.download('stopwords')
        stop_words = list(stopwords.words('english'))
    
    print(f"\n  Vectorizer settings:")
    print(f"    N-gram range: (1, 2) - unigrams + bigrams")
    print(f"    Max features: 20,000")
    print(f"    Min document frequency: 5")
    print(f"    Lowercase: True")
    print(f"    Stop words: NLTK English ({len(stop_words)} words)")
    
    print(f"\n  Fitting vectorizer... (this may take 5-10 minutes)")
    
    vectorizer = CountVectorizer(
        ngram_range=(1, 2),
        max_features=20000,
        min_df=5,
        stop_words=stop_words,
        lowercase=True
    )
    
    X = vectorizer.fit_transform(df['text'])
    y = df['is_CS'].values
    
    print(f"\n  ✓ Feature matrix shape: {X.shape}")
    print(f"    - {X.shape[0]:,} papers")
    print(f"    - {X.shape[1]:,} features (words/bigrams)")
    
    # ========================================================================
    # STEP 5: Inspect features
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 5: Inspecting features")
    print("=" * 80)
    
    feature_names = vectorizer.get_feature_names_out()
    
    print(f"\n  Sample features (first 30):")
    print(f"  {list(feature_names[:30])}")
    
    print(f"\n  Sample features (last 30):")
    print(f"  {list(feature_names[-30:])}")
    
    # ========================================================================
    # STEP 6: Save outputs
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 6: Saving outputs")
    print("=" * 80)
    
    # Save sparse matrix
    sparse_file = OUTPUT_DIR / "X_features.npz"
    sparse.save_npz(sparse_file, X)
    print(f"  ✓ Saved: {sparse_file}")
    
    # Save labels
    labels_file = OUTPUT_DIR / "y_labels.csv"
    pd.Series(y, name='is_CS').to_csv(labels_file, index=False)
    print(f"  ✓ Saved: {labels_file}")
    
    # Save vectorizer
    vectorizer_file = OUTPUT_DIR / "vectorizer.joblib"
    joblib.dump(vectorizer, vectorizer_file)
    print(f"  ✓ Saved: {vectorizer_file}")
    
    # Save article IDs for reference
    ids_file = OUTPUT_DIR / "article_ids.csv"
    df[['article_id', 'field']].to_csv(ids_file, index=False)
    print(f"  ✓ Saved: {ids_file}")
    
    print(f"\n{'=' * 80}")
    print("✅ FEATURE MATRIX COMPLETE")
    print("=" * 80)
    print(f"\nOutputs saved to: {OUTPUT_DIR}/")
    print(f"  - X_features.npz (sparse matrix)")
    print(f"  - y_labels.csv")
    print(f"  - vectorizer.joblib")
    print(f"  - article_ids.csv\n")
    
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
    
    print(f"\n{'=' * 80}")
    print("STEP 1: Loading feature matrix and labels")
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
    
    print(f"  ✓ Loaded X: {X.shape}")
    print(f"  ✓ Loaded y: {y.shape}")
    print(f"  ✓ Loaded vectorizer: {len(vectorizer.get_feature_names_out())} features")
    
    # ========================================================================
    # STEP 2: Train/test split
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 2: Train/test split")
    print("=" * 80)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.25,
        random_state=42,
        stratify=y
    )
    
    print(f"  Training set: {X_train.shape[0]:,} papers")
    print(f"  Test set: {X_test.shape[0]:,} papers")
    print(f"\n  Training class distribution:")
    print(f"    CS (y=1): {y_train.sum():,} ({100*y_train.mean():.1f}%)")
    print(f"    Non-CS (y=0): {(1-y_train).sum():,} ({100*(1-y_train.mean()):.1f}%)")
    
    # ========================================================================
    # STEP 3: Fit Lasso-Logistic with cross-validation
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 3: Fitting Lasso-Logistic regression")
    print("=" * 80)
    
    print(f"\n  Model settings:")
    print(f"    Penalty: L1 (Lasso)")
    print(f"    CV folds: 5")
    print(f"    Solver: saga (supports L1)")
    print(f"    Max iterations: 1000")
    
    print(f"\n  Fitting model with 5-fold CV... (this may take 30-60 minutes)")
    
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
    
    print(f"\n  ✓ Model fitted")
    print(f"  Best C (regularization): {model.C_[0]:.6f}")
    
    # ========================================================================
    # STEP 4: Evaluate model
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 4: Evaluating model")
    print("=" * 80)
    
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    print(f"\n  Accuracy:")
    print(f"    Training: {100*train_score:.2f}%")
    print(f"    Test: {100*test_score:.2f}%")
    
    # Predictions for more metrics
    y_pred = model.predict(X_test)
    
    from sklearn.metrics import classification_report, confusion_matrix
    
    print(f"\n  Classification Report (Test Set):")
    print(classification_report(y_test, y_pred, target_names=['Non-CS', 'CS']))
    
    print(f"\n  Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"    [[TN={cm[0,0]:,}  FP={cm[0,1]:,}]")
    print(f"     [FN={cm[1,0]:,}  TP={cm[1,1]:,}]]")
    
    # ========================================================================
    # STEP 5: Extract discriminative words
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 5: Extracting discriminative words")
    print("=" * 80)
    
    feature_names = vectorizer.get_feature_names_out()
    coefficients = model.coef_[0]
    
    # Create DataFrame
    word_importance = pd.DataFrame({
        'word': feature_names,
        'coefficient': coefficients
    })
    
    # Count non-zero coefficients
    non_zero = (coefficients != 0).sum()
    print(f"\n  Total features: {len(coefficients):,}")
    print(f"  Non-zero coefficients: {non_zero:,} ({100*non_zero/len(coefficients):.1f}%)")
    print(f"  Eliminated by Lasso: {len(coefficients) - non_zero:,}")
    
    # Sort by coefficient
    word_importance_sorted = word_importance.sort_values('coefficient', ascending=False)
    
    # Top CS-predictive words (positive coefficients)
    cs_words = word_importance_sorted[word_importance_sorted['coefficient'] > 0]
    print(f"\n  CS-predictive words (positive coef): {len(cs_words):,}")
    
    # Top Non-CS-predictive words (negative coefficients)
    non_cs_words = word_importance_sorted[word_importance_sorted['coefficient'] < 0]
    print(f"  Non-CS-predictive words (negative coef): {len(non_cs_words):,}")
    
    print(f"\n  Top 30 CS-discriminative words:")
    print(cs_words.head(30).to_string(index=False))
    
    print(f"\n  Top 30 Non-CS-discriminative words:")
    print(non_cs_words.tail(30).to_string(index=False))
    
    # ========================================================================
    # STEP 6: Save outputs
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 6: Saving outputs")
    print("=" * 80)
    
    # Save model
    model_file = OUTPUT_DIR / "lasso_model.joblib"
    joblib.dump(model, model_file)
    print(f"  ✓ Saved: {model_file}")
    
    # Save all word importances
    importance_file = OUTPUT_DIR / "word_importance_all.csv"
    word_importance_sorted.to_csv(importance_file, index=False)
    print(f"  ✓ Saved: {importance_file}")
    
    # Save CS keywords only (positive coefficients)
    cs_keywords_file = OUTPUT_DIR / "cs_keywords_discriminative.csv"
    cs_words.to_csv(cs_keywords_file, index=False)
    print(f"  ✓ Saved: {cs_keywords_file}")
    
    # Save as simple text file (just the words)
    cs_keywords_txt = OUTPUT_DIR / "cs_keywords_discriminative.txt"
    with open(cs_keywords_txt, 'w') as f:
        for word in cs_words['word'].tolist():
            f.write(f"{word}\n")
    print(f"  ✓ Saved: {cs_keywords_txt}")
    
    # Save model summary
    summary_file = OUTPUT_DIR / "model_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("LASSO-LOGISTIC MODEL SUMMARY\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Training samples: {X_train.shape[0]:,}\n")
        f.write(f"Test samples: {X_test.shape[0]:,}\n")
        f.write(f"Features: {X_train.shape[1]:,}\n")
        f.write(f"Best C: {model.C_[0]:.6f}\n\n")
        f.write(f"Training accuracy: {100*train_score:.2f}%\n")
        f.write(f"Test accuracy: {100*test_score:.2f}%\n\n")
        f.write(f"Non-zero coefficients: {non_zero:,}\n")
        f.write(f"CS-predictive words: {len(cs_words):,}\n")
        f.write(f"Non-CS-predictive words: {len(non_cs_words):,}\n")
    print(f"  ✓ Saved: {summary_file}")
    
    print(f"\n{'=' * 80}")
    print("✅ LASSO-LOGISTIC REGRESSION COMPLETE")
    print("=" * 80)
    print(f"\nOutputs saved to: {OUTPUT_DIR}/")
    print(f"  - lasso_model.joblib")
    print(f"  - word_importance_all.csv")
    print(f"  - cs_keywords_discriminative.csv")
    print(f"  - cs_keywords_discriminative.txt")
    print(f"  - model_summary.txt\n")
    
    return model, word_importance_sorted


# ============================================================================
# STEP 3: ANALYZE AND FILTER KEYWORDS
# ============================================================================

def analyze_keywords():
    """Analyze extracted keywords and apply additional filters"""
    
    print("=" * 80)
    print("ANALYZING AND FILTERING CS KEYWORDS")
    print("=" * 80)
    
    # ========================================================================
    # STEP 1: Load word importance
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 1: Loading word importance data")
    print("=" * 80)
    
    importance_file = OUTPUT_DIR / "word_importance_all.csv"
    
    if not importance_file.exists():
        print(f"  ✗ ERROR: Word importance file not found.")
        print("  Run fit_lasso_logistic() first.")
        sys.exit(1)
    
    df = pd.read_csv(importance_file)
    print(f"  ✓ Loaded {len(df):,} words")
    
    # ========================================================================
    # STEP 2: Filter by coefficient threshold
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 2: Filtering by coefficient threshold")
    print("=" * 80)
    
    # Only positive coefficients (CS-predictive)
    cs_words = df[df['coefficient'] > 0].copy()
    print(f"  Words with positive coefficient: {len(cs_words):,}")
    
    # Different thresholds
    thresholds = [0.0, 0.1, 0.5, 1.0, 2.0]
    
    print(f"\n  Words remaining at different thresholds:")
    for thresh in thresholds:
        count = (cs_words['coefficient'] > thresh).sum()
        print(f"    > {thresh}: {count:,} words")
    
    # ========================================================================
    # STEP 3: Manual review - flag generic words
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 3: Flagging potentially generic words")
    print("=" * 80)
    
    # List of potentially generic words to review
    generic_candidates = [
        'data', 'model', 'method', 'system', 'analysis',
        'results', 'study', 'research', 'approach', 'based',
        'using', 'used', 'new', 'proposed', 'paper',
        'problem', 'solution', 'performance', 'time', 'process',
        'high', 'low', 'large', 'small', 'different',
        'optimization', 'selection', 'decision', 'modern', 'novel',
        'experimental', 'numerical', 'theoretical', 'practical', 'efficient',
        'improved', 'better', 'optimal', 'effective', 'simple'
    ]
    
    # Check which generic words appear in top CS words
    top_cs = cs_words.head(500)
    
    flagged = []
    for word in generic_candidates:
        if word in top_cs['word'].values:
            coef = top_cs[top_cs['word'] == word]['coefficient'].values[0]
            flagged.append({'word': word, 'coefficient': coef})
    
    if flagged:
        flagged_df = pd.DataFrame(flagged).sort_values('coefficient', ascending=False)
        print(f"\n  ⚠ Generic words found in top 500 CS keywords:")
        print(flagged_df.to_string(index=False))
    else:
        print(f"\n  ✓ No obviously generic words in top 500")
    
    # ========================================================================
    # STEP 4: Create filtered keyword lists
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 4: Creating filtered keyword lists")
    print("=" * 80)
    
    # Conservative list: coefficient > 0.5, exclude generic
    generic_set = set(generic_candidates)
    
    cs_conservative = cs_words[
        (cs_words['coefficient'] > 0.5) &
        (~cs_words['word'].isin(generic_set))
    ]
    
    print(f"\n  Conservative list (coef > 0.5, no generic): {len(cs_conservative):,} words")
    
    # Moderate list: coefficient > 0.1, exclude generic
    cs_moderate = cs_words[
        (cs_words['coefficient'] > 0.1) &
        (~cs_words['word'].isin(generic_set))
    ]
    
    print(f"  Moderate list (coef > 0.1, no generic): {len(cs_moderate):,} words")
    
    # Save filtered lists
    conservative_file = OUTPUT_DIR / "cs_keywords_conservative.txt"
    with open(conservative_file, 'w') as f:
        for word in cs_conservative['word'].tolist():
            f.write(f"{word}\n")
    print(f"\n  ✓ Saved: {conservative_file}")
    
    moderate_file = OUTPUT_DIR / "cs_keywords_moderate.txt"
    with open(moderate_file, 'w') as f:
        for word in cs_moderate['word'].tolist():
            f.write(f"{word}\n")
    print(f"  ✓ Saved: {moderate_file}")
    
    # ========================================================================
    # STEP 5: Show top discriminative words
    # ========================================================================
    
    print(f"\n{'=' * 80}")
    print("STEP 5: Top discriminative CS words (filtered)")
    print("=" * 80)
    
    print(f"\n  Top 50 CS-discriminative words (conservative list):")
    print(cs_conservative.head(50).to_string(index=False))
    
    print(f"\n{'=' * 80}")
    print("✅ KEYWORD ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nOutputs:")
    print(f"  - cs_keywords_conservative.txt ({len(cs_conservative):,} words)")
    print(f"  - cs_keywords_moderate.txt ({len(cs_moderate):,} words)\n")
    
    return cs_conservative, cs_moderate


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    
    # ========================================================================
    # Uncomment the function you want to run
    # ========================================================================
    
    # STEP 1: Build feature matrix (vectorize)
    # build_feature_matrix()
    
    # STEP 2: Fit Lasso-Logistic regression
    # fit_lasso_logistic()
    
    # STEP 3: Analyze and filter keywords
    analyze_keywords()