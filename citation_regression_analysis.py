"""
Citation Regression Analysis - Team Size and SDL Effects on Citations
Tests whether SDL papers receive more citations and if this effect is mediated by team size
"""

import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from pathlib import Path
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# Input files
FULL_DATA = PROJECT_DIR / "data" / "regression" / "regression_dataset_full.csv"
SDL_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_journals.txt"
SDL_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_topics.txt"

# Output directory
OUTPUT_DIR = PROJECT_DIR / "results" / "citation_models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# FILTER SETTINGS
# ============================================================================

FILTER_CONFIG = {
    'use_journal_filter': True,       # Use matched sample
    'use_topic_filter': True,         # Use matched sample
    'random_seed': 42
}

# ============================================================================
# LOAD AND FILTER DATA
# ============================================================================

def load_and_filter_data():
    """Load full dataset and apply filters inline"""
    
    print("="*70)
    print("LOADING AND FILTERING DATA FOR CITATION ANALYSIS")
    print("="*70)
    
    # ========================================================================
    # Step 1: Load SDL venue lists
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("STEP 1: Loading SDL venue filters")
    print("="*70)
    
    sdl_journals = []
    sdl_topics = []
    
    if FILTER_CONFIG['use_journal_filter']:
        print(f"\n📂 Loading SDL journals...")
        if SDL_JOURNALS_FILE.exists():
            with open(SDL_JOURNALS_FILE, 'r') as f:
                sdl_journals = [line.strip() for line in f if line.strip()]
            print(f"   ✓ Loaded {len(sdl_journals)} journals")
    
    if FILTER_CONFIG['use_topic_filter']:
        print(f"\n📂 Loading SDL topics...")
        if SDL_TOPICS_FILE.exists():
            with open(SDL_TOPICS_FILE, 'r') as f:
                sdl_topics = [line.strip() for line in f if line.strip()]
            print(f"   ✓ Loaded {len(sdl_topics)} topics")
    
    # ========================================================================
    # Step 2: Load and filter data in chunks
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("STEP 2: Loading and filtering full dataset")
    print("="*70)
    
    print(f"\n📂 Loading: {FULL_DATA}")
    print("   Processing in chunks (this may take 10-20 minutes)...")
    
    chunks = []
    total_rows = 0
    filtered_rows = 0
    
    for chunk in pd.read_csv(FULL_DATA, chunksize=1000000, low_memory=False):
        total_rows += len(chunk)
        
        # Apply venue filters
        mask = pd.Series(True, index=chunk.index)
        
        if FILTER_CONFIG['use_journal_filter'] and len(sdl_journals) > 0:
            mask &= chunk['journal'].isin(sdl_journals)
        
        if FILTER_CONFIG['use_topic_filter'] and len(sdl_topics) > 0:
            mask &= chunk['primary_topic'].isin(sdl_topics)
        
     
        filtered_chunk = chunk[mask]
        filtered_rows += len(filtered_chunk)
        
        if len(filtered_chunk) > 0:
            chunks.append(filtered_chunk)
        
        if total_rows % 10000000 == 0:
            print(f"   Processed {total_rows:,} rows... (kept {filtered_rows:,})")
    
    print(f"\n   ✓ Processed {total_rows:,} total rows")
    print(f"   ✓ After filtering: {filtered_rows:,} papers")
    
    # Combine chunks
    df = pd.concat(chunks, ignore_index=True)
    
    print(f"\n   SDL papers: {(df['SDL'] == 1).sum():,}")
    print(f"   Non-SDL papers: {(df['SDL'] == 0).sum():,}")
    
    # ========================================================================
    # Step 3: Data cleaning
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("STEP 3: Data cleaning")
    print("="*70)
    
    initial_count = len(df)
    
    # Remove missing values
    df = df.dropna(subset=['cited_by_count', 'author_count', 'publication_year', 'field'])
    removed = initial_count - len(df)
    if removed > 0:
        print(f"\n   ✓ Removed {removed:,} papers with missing key variables")
        print(f"     Remaining: {len(df):,}")
    
    # ========================================================================
    # Step 4: Final summary
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("FINAL SAMPLE SUMMARY")
    print("="*70)
    
    print(f"\n📊 Sample size: {len(df):,} papers")
    print(f"   SDL: {(df['SDL'] == 1).sum():,} ({100*(df['SDL']==1).sum()/len(df):.2f}%)")
    print(f"   Non-SDL: {(df['SDL'] == 0).sum():,} ({100*(df['SDL']==0).sum()/len(df):.2f}%)")
    
    print(f"\n📊 Year range: {df['publication_year'].min()}-{df['publication_year'].max()}")
    
    print(f"\n📊 Citations:")
    print(f"   Overall mean: {df['cited_by_count'].mean():.2f}")
    print(f"   SDL mean: {df[df['SDL']==1]['cited_by_count'].mean():.2f}")
    print(f"   Non-SDL mean: {df[df['SDL']==0]['cited_by_count'].mean():.2f}")
    print(f"   Papers with 0 citations: {(df['cited_by_count'] == 0).sum():,} ({100*(df['cited_by_count']==0).sum()/len(df):.2f}%)")
    
    print(f"\n📊 Team size:")
    print(f"   Overall mean: {df['author_count'].mean():.2f}")
    print(f"   SDL mean: {df[df['SDL']==1]['author_count'].mean():.2f}")
    print(f"   Non-SDL mean: {df[df['SDL']==0]['author_count'].mean():.2f}")
    
    return df


# ============================================================================
# RUN CITATION REGRESSIONS
# ============================================================================

def run_citation_regressions(df):
    """Run Models 1-6 with citations as dependent variable"""
    
    print(f"\n{'='*70}")
    print("RUNNING CITATION REGRESSIONS")
    print("="*70)
    
    models = {}
    
    # ========================================================================
    # MODEL 1: Citations ~ Team Size (Baseline)
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 1: Citations ~ Team Size")
    print("="*70)
    
    formula1 = 'asinh_paper_citations ~ author_count'
    print(f"Formula: {formula1}")
    
    model1 = smf.ols(formula1, data=df).fit()
    models['model1'] = model1
    
    print(f"✓ R²={model1.rsquared:.4f}, Team size coef={model1.params['author_count']:.4f} (p={model1.pvalues['author_count']:.4f})")
    
    with open(OUTPUT_DIR / 'citation_model1.txt', 'w') as f:
        f.write(model1.summary().as_text())
    
    # ========================================================================
    # MODEL 2: + SDL Main Effect
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 2: + SDL Main Effect")
    print("="*70)
    
    formula2 = 'asinh_paper_citations ~ author_count + SDL'
    print(f"Formula: {formula2}")
    
    model2 = smf.ols(formula2, data=df).fit()
    models['model2'] = model2
    
    print(f"✓ R²={model2.rsquared:.4f}, SDL coef={model2.params['SDL']:.4f} (p={model2.pvalues['SDL']:.4f})")
    
    with open(OUTPUT_DIR / 'citation_model2.txt', 'w') as f:
        f.write(model2.summary().as_text())
    
    # ========================================================================
    # MODEL 3: + Author Controls
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 3: + Author Controls")
    print("="*70)
    
    formula3 = '''
        asinh_paper_citations ~ author_count + SDL +
        num_paper_affiliations +
        asinh_first_author_papers +
        asinh_first_author_citations +
        asinh_last_author_papers +
        asinh_last_author_citations
    '''
    
    print(f"Formula: Team size + SDL + author controls")
    
    model3 = smf.ols(formula3, data=df).fit()
    models['model3'] = model3
    
    print(f"✓ R²={model3.rsquared:.4f}, SDL coef={model3.params['SDL']:.4f} (p={model3.pvalues['SDL']:.4f})")
    
    with open(OUTPUT_DIR / 'citation_model3.txt', 'w') as f:
        f.write(model3.summary().as_text())
    
    # ========================================================================
    # MODEL 4: + Topic FE
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 4: + Topic Fixed Effects")
    print("="*70)
    
    formula4 = formula3 + ' + C(primary_topic)'
    print(f"Formula: Model 3 + Topic FE ({df['primary_topic'].nunique()} topics)")
    
    model4 = smf.ols(formula4, data=df).fit()
    models['model4'] = model4
    
    print(f"✓ R²={model4.rsquared:.4f}, SDL coef={model4.params['SDL']:.4f} (p={model4.pvalues['SDL']:.4f})")
    
    with open(OUTPUT_DIR / 'citation_model4.txt', 'w') as f:
        f.write(model4.summary().as_text())
    
    # ========================================================================
    # MODEL 5: + Journal FE
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 5: + Topic + Journal Fixed Effects")
    print("="*70)
    
    num_journals = df['journal'].nunique()
    print(f"Formula: Model 4 + Journal FE ({num_journals:,} journals)")
    
    if num_journals > 1000:
        print(f"⚠️  WARNING: {num_journals:,} journals - this may take 10-20 minutes...")
    
    formula5 = formula4 + ' + C(journal)'
    
    try:
        model5 = smf.ols(formula5, data=df).fit()
        models['model5'] = model5
        
        print(f"✓ R²={model5.rsquared:.4f}, SDL coef={model5.params['SDL']:.4f} (p={model5.pvalues['SDL']:.4f})")
        
        with open(OUTPUT_DIR / 'citation_model5.txt', 'w') as f:
            f.write(model5.summary().as_text())
    
    except Exception as e:
        print(f"✗ Model 5 failed: {e}")
        models['model5'] = None
    
    # ========================================================================
    # MODEL 6: + Team Size × SDL Interaction (KEY MODEL)
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 6: + Team Size × SDL Interaction")
    print("="*70)
    
    formula6 = '''
        asinh_paper_citations ~ author_count * SDL +
        num_paper_affiliations +
        asinh_first_author_papers +
        asinh_first_author_citations +
        asinh_last_author_papers +
        asinh_last_author_citations +
        C(primary_topic) +
        C(journal)
    '''
    
    print(f"Formula: author_count * SDL (interaction term)")
    
    try:
        model6 = smf.ols(formula6, data=df).fit()
        models['model6'] = model6
        
        print(f"✓ R²={model6.rsquared:.4f}")
        print(f"   author_count coef={model6.params['author_count']:.4f} (p={model6.pvalues['author_count']:.4f})")
        print(f"   SDL coef={model6.params['SDL']:.4f} (p={model6.pvalues['SDL']:.4f})")
        print(f"   author_count:SDL coef={model6.params['author_count:SDL']:.4f} (p={model6.pvalues['author_count:SDL']:.4f})")
        
        with open(OUTPUT_DIR / 'citation_model6.txt', 'w') as f:
            f.write(model6.summary().as_text())
    
    except Exception as e:
        print(f"✗ Model 6 failed: {e}")
        models['model6'] = None
    
    return models


# ============================================================================
# CREATE SUMMARY TABLES
# ============================================================================

def create_summary_tables(models):
    """Create comparison and coefficient tables"""
    
    print(f"\n{'='*70}")
    print("CREATING SUMMARY TABLES")
    print("="*70)
    
    # ========================================================================
    # Comparison table (all models)
    # ========================================================================
    
    comparison_data = []
    
    for i in range(1, 7):
        model = models.get(f'model{i}')
        if model is not None:
            row = {
                'Model': i,
                'author_count_coef': model.params.get('author_count', np.nan),
                'author_count_pval': model.pvalues.get('author_count', np.nan),
                'SDL_coef': model.params.get('SDL', np.nan),
                'SDL_pval': model.pvalues.get('SDL', np.nan),
                'R_squared': model.rsquared,
                'N': int(model.nobs)
            }
            
            # Add interaction term if exists (Model 6)
            if 'author_count:SDL' in model.params:
                row['interaction_coef'] = model.params['author_count:SDL']
                row['interaction_pval'] = model.pvalues['author_count:SDL']
            else:
                row['interaction_coef'] = np.nan
                row['interaction_pval'] = np.nan
            
            comparison_data.append(row)
    
    comparison_df = pd.DataFrame(comparison_data)
    comparison_df.to_csv(OUTPUT_DIR / 'citation_model_comparison.csv', index=False)
    
    print("\n📊 Citation Model Comparison:")
    print(comparison_df.to_string(index=False))
    print(f"\n✓ Saved: citation_model_comparison.csv")
    
    # ========================================================================
    # Coefficient table (key variables)
    # ========================================================================
    
    key_vars = [
        'author_count',
        'SDL',
        'author_count:SDL',
        'num_paper_affiliations',
        'asinh_first_author_papers',
        'asinh_first_author_citations',
        'asinh_last_author_papers',
        'asinh_last_author_citations'
    ]
    
    coef_table = pd.DataFrame({'Variable': key_vars})
    
    for i in range(1, 7):
        model = models.get(f'model{i}')
        if model is not None:
            coefs = []
            for var in key_vars:
                if var in model.params:
                    coef = model.params[var]
                    se = model.bse[var]
                    pval = model.pvalues[var]
                    
                    stars = ''
                    if pval < 0.01:
                        stars = '***'
                    elif pval < 0.05:
                        stars = '**'
                    elif pval < 0.1:
                        stars = '*'
                    
                    coefs.append(f"{coef:.4f}{stars}\n({se:.4f})")
                else:
                    coefs.append('-')
            
            coef_table[f'Model_{i}'] = coefs
    
    coef_table.to_csv(OUTPUT_DIR / 'citation_coefficients.csv', index=False)
    
    print("\n📊 Coefficient Table:")
    print(coef_table.to_string(index=False))
    print("\nNote: *** p<0.01, ** p<0.05, * p<0.1")
    print("Standard errors in parentheses")
    print(f"\n✓ Saved: citation_coefficients.csv")
    
    # ========================================================================
    # Fixed effects table
    # ========================================================================
    
    fe_table = pd.DataFrame({
        'Model': range(1, 7),
        'Author_Controls': ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes'],
        'Topic_FE': ['No', 'No', 'No', 'Yes', 'Yes', 'Yes'],
        'Journal_FE': ['No', 'No', 'No', 'No', 
                       'Yes' if models.get('model5') else 'Failed',
                       'Yes' if models.get('model6') else 'Failed'],
        'Interaction': ['No', 'No', 'No', 'No', 'No', 'Yes']
    })
    
    fe_table.to_csv(OUTPUT_DIR / 'citation_fixed_effects.csv', index=False)
    
    print("\n📊 Fixed Effects Summary:")
    print(fe_table.to_string(index=False))
    print(f"\n✓ Saved: citation_fixed_effects.csv")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    
    print("="*70)
    print("CITATION REGRESSION ANALYSIS")
    print("="*70)
    
    print(f"\n⚙️  Configuration:")
    print(f"   Journal filter: {'ON' if FILTER_CONFIG['use_journal_filter'] else 'OFF'}")
    print(f"   Topic filter: {'ON' if FILTER_CONFIG['use_topic_filter'] else 'OFF'}")
    
    # Load and filter data
    df = load_and_filter_data()
    
    if df is None:
        print("\n✗ Data loading failed. Exiting.")
        sys.exit(1)
    
    # Run citation regressions
    print(f"\n{'='*70}")
    print("RUNNING CITATION REGRESSION MODELS")
    print("="*70)
    print("\nThis will run 6 models:")
    print("  • Model 1: Citations ~ Team Size")
    print("  • Model 2: + SDL")
    print("  • Model 3: + Author Controls")
    print("  • Model 4: + Topic FE")
    print("  • Model 5: + Journal FE")
    print("  • Model 6: + Team Size × SDL Interaction (KEY MODEL)\n")
    
    citation_models = run_citation_regressions(df)
    
    # Create summary tables
    create_summary_tables(citation_models)
    
    # Count successful models
    successful = sum(1 for m in citation_models.values() if m is not None)
    total = len(citation_models)
    
    print("\n" + "="*70)
    print("✅ CITATION ANALYSIS FINISHED")
    print("="*70)
    print(f"\nSuccessfully ran {successful}/{total} models")
    print(f"\nResults saved to: {OUTPUT_DIR}/")
    print(f"  • citation_model1.txt through citation_model6.txt")
    print(f"  • citation_model_comparison.csv")
    print(f"  • citation_coefficients.csv")
    print(f"  • citation_fixed_effects.csv")
    
    print("\n" + "="*70)
    print("KEY INTERPRETATION NOTES")
    print("="*70)
    print("\nModel 6 (interaction model) tests:")
    print("  • author_count: Citation benefit per author for NON-SDL papers")
    print("  • SDL: Citation premium for SDL papers at team size = 0 (baseline)")
    print("  • author_count:SDL: Additional citation benefit per author for SDL papers")
    print("\nIf interaction term is:")
    print("  • Positive: SDL papers get EXTRA citation benefit from larger teams")
    print("  • Negative: SDL papers get LESS citation benefit from larger teams")
    print("  • Near zero: SDL and non-SDL papers benefit equally from larger teams")


if __name__ == "__main__":
    main()