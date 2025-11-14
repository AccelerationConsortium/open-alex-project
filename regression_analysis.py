"""
Baseline Regression Analysis - Single Script
Filters data inline (no separate dataset creation) and runs Models 1-6
"""

import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from pathlib import Path
import sys

# ============================================================================
# CONFIGURATION - CHANGE THESE SETTINGS
# ============================================================================

PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# Input files
FULL_DATA = PROJECT_DIR / "data" / "regression" / "regression_dataset_full.csv"
SDL_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_journals.txt"
SDL_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_topics.txt"

# Output directory
OUTPUT_DIR = PROJECT_DIR / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# FILTER SETTINGS - CHANGE THESE
# ============================================================================

FILTER_CONFIG = {
    # Which filters to apply
    'use_journal_filter': False,      # Filter to SDL journals?
    'use_topic_filter': False,        # Filter to SDL topics?
    
    # Reproducibility
    'random_seed': 42
}

# ============================================================================
# LOAD AND FILTER DATA
# ============================================================================

def load_and_filter_data():
    """Load full dataset and apply filters inline"""
    
    print("="*70)
    print("LOADING AND FILTERING DATA")
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
    
    for chunk in pd.read_csv(FULL_DATA, chunksize=500000, low_memory=False):
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
        
        if total_rows % 5000000 == 0:
            print(f"   Processed {total_rows:,} rows... (kept {filtered_rows:,})")
    
    print(f"\n   ✓ Processed {total_rows:,} total rows")
    print(f"   ✓ After venue filtering: {filtered_rows:,} papers")
    
    # Combine chunks
    df = pd.concat(chunks, ignore_index=True)
    
    print(f"\n   SDL papers: {(df['SDL'] == 1).sum():,}")
    print(f"   Non-SDL papers: {(df['SDL'] == 0).sum():,}")

    # ========================================================================
    # Step 4: Data cleaning
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("STEP 4: Data cleaning")
    print("="*70)
    
    initial_count = len(df)
    
    # Remove missing values
    df = df.dropna(subset=['author_count', 'publication_year', 'field'])
    removed = initial_count - len(df)
    if removed > 0:
        print(f"\n   ✓ Removed {removed:,} papers with missing key variables")
        print(f"     Remaining: {len(df):,}")
    
    # ========================================================================
    # Step 5: Final summary
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("FINAL SAMPLE SUMMARY")
    print("="*70)
    
    print(f"\n📊 Sample size: {len(df):,} papers")
    print(f"   SDL: {(df['SDL'] == 1).sum():,} ({100*(df['SDL']==1).sum()/len(df):.2f}%)")
    print(f"   Non-SDL: {(df['SDL'] == 0).sum():,} ({100*(df['SDL']==0).sum()/len(df):.2f}%)")
    
    print(f"\n📊 Unique venues:")
    print(f"   Fields: {df['field'].nunique()}")
    print(f"   Years: {df['publication_year'].nunique()}")
    print(f"   Journals: {df['journal'].nunique():,}")
    print(f"   Topics: {df['primary_topic'].nunique():,}")
    
    print(f"\n📊 Team size:")
    print(f"   Overall mean: {df['author_count'].mean():.2f}")
    print(f"   SDL mean: {df[df['SDL']==1]['author_count'].mean():.2f}")
    print(f"   Non-SDL mean: {df[df['SDL']==0]['author_count'].mean():.2f}")
    
    return df


# ============================================================================
# RUN REGRESSIONS
# ============================================================================

def run_regressions(df):
    """Run Models 1-6 with progressive fixed effects"""
    
    print(f"\n{'='*70}")
    print("RUNNING BASELINE REGRESSIONS")
    print("="*70)
    
    models = {}
    
    # ========================================================================
    # MODEL 1: SDL Only
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 1: SDL Only")
    print("="*70)
    
    formula1 = 'author_count ~ SDL'
    print(f"Formula: {formula1}")
    
    model1 = smf.ols(formula1, data=df).fit()
    models['model1'] = model1
    
    print(f"✓ R²={model1.rsquared:.4f}, SDL coef={model1.params['SDL']:.4f} (p={model1.pvalues['SDL']:.4f})")
    
    with open(OUTPUT_DIR / 'model1.txt', 'w') as f:
        f.write(model1.summary().as_text())
    
    # # ========================================================================
    # # MODEL 2: + Author Controls
    # # ========================================================================
    
    # print(f"\n{'='*70}")
    # print("MODEL 2: + Author Controls")
    # print("="*70)
    
    # formula2 = '''
    #     author_count ~ SDL +
    #     num_paper_affiliations +
    #     asinh_first_author_papers +
    #     asinh_first_author_citations +
    #     asinh_last_author_papers +
    #     asinh_last_author_citations
    # '''
    
    # print(f"Formula: SDL + author controls (asinh-transformed)")
    
    # model2 = smf.ols(formula2, data=df).fit()
    # models['model2'] = model2
    
    # print(f"✓ R²={model2.rsquared:.4f}, SDL coef={model2.params['SDL']:.4f} (p={model2.pvalues['SDL']:.4f})")
    
    # with open(OUTPUT_DIR / 'model2.txt', 'w') as f:
    #     f.write(model2.summary().as_text())
    
    # # ========================================================================
    # # MODEL 3: + Year FE
    # # ========================================================================
    
    # print(f"\n{'='*70}")
    # print("MODEL 3: + Year Fixed Effects")
    # print("="*70)
    
    # formula3 = formula2 + ' + C(publication_year)'
    # print(f"Formula: Model 2 + Year FE ({df['publication_year'].nunique()} years)")
    
    # model3 = smf.ols(formula3, data=df).fit()
    # models['model3'] = model3
    
    # print(f"✓ R²={model3.rsquared:.4f}, SDL coef={model3.params['SDL']:.4f} (p={model3.pvalues['SDL']:.4f})")
    
    # with open(OUTPUT_DIR / 'model3.txt', 'w') as f:
    #     f.write(model3.summary().as_text())
    
    # # ========================================================================
    # # MODEL 4: + Field FE
    # # ========================================================================
    
    # print(f"\n{'='*70}")
    # print("MODEL 4: + Year + Field Fixed Effects")
    # print("="*70)
    
    # formula4 = formula3 + ' + C(field)'
    # print(f"Formula: Model 3 + Field FE ({df['field'].nunique()} fields)")
    
    # model4 = smf.ols(formula4, data=df).fit()
    # models['model4'] = model4
    
    # print(f"✓ R²={model4.rsquared:.4f}, SDL coef={model4.params['SDL']:.4f} (p={model4.pvalues['SDL']:.4f})")
    
    # with open(OUTPUT_DIR / 'model4.txt', 'w') as f:
    #     f.write(model4.summary().as_text())
    
    # # ========================================================================
    # # MODEL 5: + Journal FE
    # # ========================================================================
    
    # print(f"\n{'='*70}")
    # print("MODEL 5: + Year + Field + Journal Fixed Effects")
    # print("="*70)
    
    # num_journals = df['journal'].nunique()
    # print(f"Formula: Model 4 + Journal FE ({num_journals:,} journals)")
    
    # if num_journals > 1000:
    #     print(f"⚠️  WARNING: {num_journals:,} journals - this may take 10-20 minutes...")
    
    # formula5 = formula4 + ' + C(journal)'
    
    # try:
    #     model5 = smf.ols(formula5, data=df).fit()
    #     models['model5'] = model5
        
    #     print(f"✓ R²={model5.rsquared:.4f}, SDL coef={model5.params['SDL']:.4f} (p={model5.pvalues['SDL']:.4f})")
        
    #     with open(OUTPUT_DIR / 'model5.txt', 'w') as f:
    #         f.write(model5.summary().as_text())
    
    # except Exception as e:
    #     print(f"✗ Model 5 failed: {e}")
    #     models['model5'] = None
    
    # # ========================================================================
    # # MODEL 6: + Topic FE
    # # ========================================================================
    
    # print(f"\n{'='*70}")
    # print("MODEL 6: + Year + Field + Journal + Topic Fixed Effects")
    # print("="*70)
    
    # num_topics = df['primary_topic'].nunique()
    # print(f"Formula: Model 5 + Topic FE ({num_topics:,} topics)")
    
    # formula6 = formula5 + ' + C(primary_topic)' if models.get('model5') else None
    
    # if formula6:
    #     try:
    #         model6 = smf.ols(formula6, data=df).fit()
    #         models['model6'] = model6
            
    #         print(f"✓ R²={model6.rsquared:.4f}, SDL coef={model6.params['SDL']:.4f} (p={model6.pvalues['SDL']:.4f})")
            
    #         with open(OUTPUT_DIR / 'model6.txt', 'w') as f:
    #             f.write(model6.summary().as_text())
        
    #     except Exception as e:
    #         print(f"✗ Model 6 failed: {e}")
    #         models['model6'] = None
    # else:
    #     print("⚠️  Skipping Model 6 (Model 5 failed)")
    #     models['model6'] = None
    
    # return models


# ============================================================================
# CORRESPONDING AUTHOR MODELS (Models 8-9)
# ============================================================================

def run_corresponding_author_models(df):
    """Run Models 8-9 with corresponding author variables"""
    
    print(f"\n{'='*70}")
    print("CORRESPONDING AUTHOR MODELS")
    print("="*70)
    
    models = {}
    
    # ========================================================================
    # MODEL 8: With Corresponding Author Variables
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 8: + Corresponding Author Controls")
    print("="*70)
    
    formula8 = '''
        author_count ~ SDL +
        num_paper_affiliations +
        asinh_first_author_papers +
        asinh_first_author_citations +
        asinh_last_author_papers +
        asinh_last_author_citations +
        asinh_corresponding_papers +
        asinh_corresponding_citations +
        C(publication_year) +
        C(field) +
        C(journal) +
        C(primary_topic)
    '''
    
    print(f"\nFormula: Full model + corresponding author controls\n")
    
    try:
        model8 = smf.ols(formula8, data=df).fit()
        models['model8'] = model8
        
        print(model8.summary())
        
        with open(OUTPUT_DIR / 'model8.txt', 'w') as f:
            f.write(model8.summary().as_text())
    
    except Exception as e:
        print(f"✗ Model 8 failed: {e}")
        models['model8'] = None
    
    # ========================================================================
    # MODEL 9: Corresponding Author Position
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 9: + Corresponding Author Position")
    print("="*70)
    
    print(f"\nCorresponding position distribution:")
    print(df['corresponding_position'].value_counts())
    
    formula9 = '''
        author_count ~ SDL +
        num_paper_affiliations +
        asinh_first_author_papers +
        asinh_first_author_citations +
        asinh_last_author_papers +
        asinh_last_author_citations +
        C(corresponding_position) +
        C(publication_year) +
        C(field) +
        C(journal) +
        C(primary_topic)
    '''
    
    print(f"\nFormula: Full model + corresponding position categories\n")
    
    try:
        model9 = smf.ols(formula9, data=df).fit()
        models['model9'] = model9
        
        print(model9.summary())
        
        with open(OUTPUT_DIR / 'model9.txt', 'w') as f:
            f.write(model9.summary().as_text())
    
    except Exception as e:
        print(f"✗ Model 9 failed: {e}")
        models['model9'] = None
    
    return models


# ============================================================================
# AI/ROBOTICS SUBSAMPLE MODELS (Models 21-26)
# ============================================================================

def run_subsample_models(df):
    """Run Models 21-26 on AI/Robotics subsamples"""
    
    print(f"\n{'='*70}")
    print("AI/ROBOTICS SUBSAMPLE MODELS")
    print("="*70)
    
    models = {}
    
    # Base formula with all controls and FE
    base_formula = '''
        author_count ~ SDL +
        num_paper_affiliations +
        asinh_first_author_papers +
        asinh_first_author_citations +
        asinh_last_author_papers +
        asinh_last_author_citations +
        C(publication_year) +
        C(field) +
        C(journal) +
        C(primary_topic)
    '''
    
    # # ========================================================================
    # # MODEL 21: AI Papers Only
    # # ========================================================================
    
    # print(f"\n{'='*70}")
    # print("MODEL 21: AI Papers Only")
    # print("="*70)
    
    # df_ai = df[df['AI_Paper'] == 1].copy()
    
    # print(f"\nAI Papers subsample:")
    # print(f"   Total: {len(df_ai):,}")
    # print(f"   SDL: {(df_ai['SDL'] == 1).sum()}")
    # print(f"   Non-SDL: {(df_ai['SDL'] == 0).sum()}")
    
    # if len(df_ai) > 0:
    #     try:
    #         model21 = smf.ols(base_formula, data=df_ai).fit()
    #         models['model21'] = model21
            
    #         print(f"\n{model21.summary()}")
            
    #         with open(OUTPUT_DIR / 'model21_ai_only.txt', 'w') as f:
    #             f.write(model21.summary().as_text())
        
    #     except Exception as e:
    #         print(f"✗ Model 21 failed: {e}")
    #         models['model21'] = None
    # else:
    #     print("✗ No AI papers in sample")
    #     models['model21'] = None
    
    # # ========================================================================
    # # MODEL 22: Robotics Papers Only
    # # ========================================================================
    
    # print(f"\n{'='*70}")
    # print("MODEL 22: Robotics Papers Only")
    # print("="*70)
    
    # df_robotics = df[df['Robotics_Paper'] == 1].copy()
    
    # print(f"\nRobotics Papers subsample:")
    # print(f"   Total: {len(df_robotics):,}")
    # print(f"   SDL: {(df_robotics['SDL'] == 1).sum()}")
    # print(f"   Non-SDL: {(df_robotics['SDL'] == 0).sum()}")
    
    # if len(df_robotics) > 0:
    #     try:
    #         model22 = smf.ols(base_formula, data=df_robotics).fit()
    #         models['model22'] = model22
            
    #         print(f"\n{model22.summary()}")
            
    #         with open(OUTPUT_DIR / 'model22_robotics_only.txt', 'w') as f:
    #             f.write(model22.summary().as_text())
        
    #     except Exception as e:
    #         print(f"✗ Model 22 failed: {e}")
    #         models['model22'] = None
    # else:
    #     print("✗ No Robotics papers in sample")
    #     models['model22'] = None
    
    # ========================================================================
    # MODEL 23: AI + Robotics Combined
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 23: AI + Robotics Combined")
    print("="*70)
    
    df_ai_robotics = df[(df['AI_Paper'] == 1) & (df['Robotics_Paper'] == 1)].copy()
    
    print(f"\nAI + Robotics Papers subsample:")
    print(f"   Total: {len(df_ai_robotics):,}")
    print(f"   AI only: {((df_ai_robotics['AI_Paper'] == 1) & (df_ai_robotics['Robotics_Paper'] == 0)).sum()}")
    print(f"   Robotics only: {((df_ai_robotics['Robotics_Paper'] == 1) & (df_ai_robotics['AI_Paper'] == 0)).sum()}")
    print(f"   Both: {((df_ai_robotics['AI_Paper'] == 1) & (df_ai_robotics['Robotics_Paper'] == 1)).sum()}")
    print(f"   SDL: {(df_ai_robotics['SDL'] == 1).sum()}")
    
    formula23 = '''
        author_count ~ SDL + AI_Paper + Robotics_Paper +
        num_paper_affiliations +
        asinh_first_author_papers +
        asinh_first_author_citations +
        asinh_last_author_papers +
        asinh_last_author_citations +
        C(publication_year) +
        C(field) +
        C(journal) +
        C(primary_topic)
    '''
    
    if len(df_ai_robotics) > 0:
        try:
            model23 = smf.ols(formula23, data=df_ai_robotics).fit()
            models['model23'] = model23
            
            print(f"\n{model23.summary()}")
            
            with open(OUTPUT_DIR / 'model23_ai_robotics.txt', 'w') as f:
                f.write(model23.summary().as_text())
        
        except Exception as e:
            print(f"✗ Model 23 failed: {e}")
            models['model23'] = None
    else:
        print("✗ No AI/Robotics papers in sample")
        models['model23'] = None
    
    # # ========================================================================
    # # MODEL 24: AI × SDL Interaction
    # # ========================================================================
    
    # print(f"\n{'='*70}")
    # print("MODEL 24: AI × SDL Interaction")
    # print("="*70)
    
    # formula24 = '''
    #     author_count ~ SDL * AI_Paper +
    #     num_paper_affiliations +
    #     asinh_first_author_papers +
    #     asinh_first_author_citations +
    #     asinh_last_author_papers +
    #     asinh_last_author_citations +
    #     C(publication_year) +
    #     C(field) +
    #     C(journal) +
    #     C(primary_topic)
    # '''
    
    # print(f"\nFormula: SDL × AI_Paper interaction\n")
    
    # try:
    #     model24 = smf.ols(formula24, data=df).fit()
    #     models['model24'] = model24
        
    #     print(model24.summary())
        
    #     with open(OUTPUT_DIR / 'model24_ai_interaction.txt', 'w') as f:
    #         f.write(model24.summary().as_text())
    
    # except Exception as e:
    #     print(f"✗ Model 24 failed: {e}")
    #     models['model24'] = None
    
    # # ========================================================================
    # # MODEL 25: Robotics × SDL Interaction
    # # ========================================================================
    
    # print(f"\n{'='*70}")
    # print("MODEL 25: Robotics × SDL Interaction")
    # print("="*70)
    
    # formula25 = '''
    #     author_count ~ SDL * Robotics_Paper +
    #     num_paper_affiliations +
    #     asinh_first_author_papers +
    #     asinh_first_author_citations +
    #     asinh_last_author_papers +
    #     asinh_last_author_citations +
    #     C(publication_year) +
    #     C(field) +
    #     C(journal) +
    #     C(primary_topic)
    # '''
    
    # print(f"\nFormula: SDL × Robotics_Paper interaction\n")
    
    # try:
    #     model25 = smf.ols(formula25, data=df).fit()
    #     models['model25'] = model25
        
    #     print(model25.summary())
        
    #     with open(OUTPUT_DIR / 'model25_robotics_interaction.txt', 'w') as f:
    #         f.write(model25.summary().as_text())
    
    # except Exception as e:
    #     print(f"✗ Model 25 failed: {e}")
    #     models['model25'] = None
    
    # # ========================================================================
    # # MODEL 26: Three-Way Interaction
    # # ========================================================================
    
    # print(f"\n{'='*70}")
    # print("MODEL 26: SDL × AI × Robotics Three-Way Interaction")
    # print("="*70)
    
    # formula26 = '''
    #     author_count ~ SDL * AI_Paper * Robotics_Paper +
    #     num_paper_affiliations +
    #     asinh_first_author_papers +
    #     asinh_first_author_citations +
    #     asinh_last_author_papers +
    #     asinh_last_author_citations +
    #     C(publication_year) +
    #     C(field) +
    #     C(journal) +
    #     C(primary_topic)
    # '''
    
    # print(f"\nFormula: SDL × AI_Paper × Robotics_Paper three-way interaction\n")
    
    # try:
    #     model26 = smf.ols(formula26, data=df).fit()
    #     models['model26'] = model26
        
    #     print(model26.summary())
        
    #     with open(OUTPUT_DIR / 'model26_threeway_interaction.txt', 'w') as f:
    #         f.write(model26.summary().as_text())
    
    # except Exception as e:
    #     print(f"✗ Model 26 failed: {e}")
    #     models['model26'] = None
    
    return models


# ============================================================================
# CREATE SUMMARY TABLES
# ============================================================================

def create_summary_tables(models):
    """Create comparison and coefficient tables for all models"""
    
    print(f"\n{'='*70}")
    print("CREATING SUMMARY TABLES")
    print("="*70)
    
    # ========================================================================
    # Comparison table (all models)
    # ========================================================================
    
    comparison_data = []
    
    # Models 1-6, 8-9, 21-26
    model_numbers = list(range(1, 7)) + [8, 9] + list(range(21, 27))
    
    for i in model_numbers:
        model = models.get(f'model{i}')
        if model is not None:
            comparison_data.append({
                'Model': i,
                'SDL_coef': model.params.get('SDL', np.nan),
                'SDL_se': model.bse.get('SDL', np.nan),
                'SDL_pval': model.pvalues.get('SDL', np.nan),
                'R_squared': model.rsquared,
                'Adj_R_squared': model.rsquared_adj,
                'N': int(model.nobs)
            })
    
    comparison_df = pd.DataFrame(comparison_data)
    comparison_df.to_csv(OUTPUT_DIR / 'model_comparison_all.csv', index=False)
    
    print("\n📊 Model Comparison (All Models):")
    print(comparison_df.to_string(index=False))
    print(f"\n✓ Saved: model_comparison_all.csv")
    
    # ========================================================================
    # Coefficient table (baseline models 1-6)
    # ========================================================================
    
    key_vars = [
        'SDL',
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
    
    coef_table.to_csv(OUTPUT_DIR / 'coefficients_baseline.csv', index=False)
    
    print("\n📊 Coefficient Table (Baseline Models 1-6):")
    print(coef_table.to_string(index=False))
    print("\nNote: *** p<0.01, ** p<0.05, * p<0.1")
    print("Standard errors in parentheses")
    print(f"\n✓ Saved: coefficients_baseline.csv")
    
    # ========================================================================
    # Fixed effects table
    # ========================================================================
    
    fe_table = pd.DataFrame({
        'Model': range(1, 7),
        'Year_FE': ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes'],
        'Field_FE': ['No', 'No', 'No', 'Yes', 'Yes', 'Yes'],
        'Journal_FE': ['No', 'No', 'No', 'No', 
                       'Yes' if models.get('model5') else 'Failed',
                       'Yes' if models.get('model6') else 'Failed'],
        'Topic_FE': ['No', 'No', 'No', 'No', 'No',
                     'Yes' if models.get('model6') else 'Failed']
    })
    
    fe_table.to_csv(OUTPUT_DIR / 'fixed_effects.csv', index=False)
    
    print("\n📊 Fixed Effects Summary (Baseline):")
    print(fe_table.to_string(index=False))
    print(f"\n✓ Saved: fixed_effects.csv")
    
    # ========================================================================
    # Subsample summary
    # ========================================================================
    
    subsample_models = []
    for i in [21, 22, 23, 24, 25, 26]:
        model = models.get(f'model{i}')
        if model is not None:
            subsample_models.append({
                'Model': i,
                'Description': {
                    21: 'AI only',
                    22: 'Robotics only',
                    23: 'AI + Robotics',
                    24: 'AI × SDL interaction',
                    25: 'Robotics × SDL interaction',
                    26: 'Three-way interaction'
                }[i],
                'N': int(model.nobs),
                'SDL_coef': model.params.get('SDL', np.nan),
                'R_squared': model.rsquared
            })
    
    if subsample_models:
        subsample_df = pd.DataFrame(subsample_models)
        subsample_df.to_csv(OUTPUT_DIR / 'subsample_summary.csv', index=False)
        
        print("\n📊 Subsample Models Summary:")
        print(subsample_df.to_string(index=False))
        print(f"\n✓ Saved: subsample_summary.csv")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    
    print("="*70)
    print("COMPLETE REGRESSION ANALYSIS")
    print("="*70)
    
    print(f"\n⚙️  Configuration:")
    print(f"   Journal filter: {'ON' if FILTER_CONFIG['use_journal_filter'] else 'OFF'}")
    print(f"   Topic filter: {'ON' if FILTER_CONFIG['use_topic_filter'] else 'OFF'}")
   
    # Load and filter data
    df = load_and_filter_data()
    
    if df is None:
        print("\n✗ Data loading failed. Exiting.")
        sys.exit(1)
    
    # ========================================================================
    # Run all regression models
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("RUNNING ALL REGRESSION MODELS")
    print("="*70)
    print("\nThis will run:")
    print("  • Models 1-6: Baseline with progressive FE")
    print("  • Models 8-9: Corresponding author models")
    print("  • Models 21-26: AI/Robotics subsample models")
    print("\nTotal: 14 regression models\n")
    
    all_models = {}
    
    # Baseline models (1-6)
    print(f"\n{'#'*70}")
    print("# PART 1: BASELINE MODELS (1-6)")
    print(f"{'#'*70}")
    baseline_models = run_regressions(df)
    all_models.update(baseline_models)
    
    # # Corresponding author models (8-9)
    # print(f"\n{'#'*70}")
    # print("# PART 2: CORRESPONDING AUTHOR MODELS (8-9)")
    # print(f"{'#'*70}")
    # corr_models = run_corresponding_author_models(df)
    # all_models.update(corr_models)
    
    # # AI/Robotics subsample models (21-26)
    # print(f"\n{'#'*70}")
    # print("# PART 3: AI/ROBOTICS SUBSAMPLE MODELS (21-26)")
    # print(f"{'#'*70}")
    # subsample_models = run_subsample_models(df)
    # all_models.update(subsample_models)
    
    # ========================================================================
    # Create summary tables
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("CREATING SUMMARY TABLES")
    print("="*70)
    
    create_summary_tables(all_models)
    
    # Count successful models
    successful = sum(1 for m in all_models.values() if m is not None)
    total = len(all_models)
    
    print("\n" + "="*70)
    print("✅ COMPLETE ANALYSIS FINISHED")
    print("="*70)
    print(f"\nSuccessfully ran {successful}/{total} models")
    print(f"\nResults saved to: {OUTPUT_DIR}/")
    print(f"  • model1.txt through model6.txt (Baseline)")
    print(f"  • model8.txt, model9.txt (Corresponding author)")
    print(f"  • model21.txt through model26.txt (AI/Robotics)")
    print(f"  • model_comparison.csv")
    print(f"  • coefficients.csv")
    print(f"  • fixed_effects.csv")


if __name__ == "__main__":
    main()