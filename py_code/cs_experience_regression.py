"""
CS Experience Regression Analysis
Runs 5 different regression specifications using CS experience variables
Models 1-5
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
FULL_DATA = PROJECT_DIR / "data" / "regression/test" / "regression_dataset_filtered.csv"
SDL_JOURNALS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_journals.txt"
SDL_TOPICS_FILE = PROJECT_DIR / "data" / "sdl" / "sdl_primary_topics.txt"

# Output directory
OUTPUT_DIR = PROJECT_DIR / "data_regression_results/test/cs_experience_models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FILTER_CONFIG = {
    'use_journal_filter': True,
    'use_topic_filter': True,
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
    
    # Load SDL venue lists
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
    
    # Load and filter data in chunks
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
    
    # Data cleaning
    print(f"\n{'='*70}")
    print("STEP 3: Data cleaning")
    print("="*70)
    
    initial_count = len(df)
    
    df = df.dropna(subset=['author_count', 'publication_year', 'field'])
    removed = initial_count - len(df)
    if removed > 0:
        print(f"\n   ✓ Removed {removed:,} papers with missing key variables")
        print(f"     Remaining: {len(df):,}")
    
    # Create CS experience variables
    print(f"\n{'='*70}")
    print("STEP 4: Creating CS experience variables")
    print("="*70)
    
    # Check what CS experience columns exist
    cs_cols = [col for col in df.columns if 'cs_experience' in col.lower() or 'comp_sci_experience' in col.lower()]
    print(f"\nFound CS experience columns: {cs_cols}")
    
    # Create share variable if it doesn't exist
    # Assuming we have first_author_cs_experience and last_author_cs_experience as binary
    # If we have comp_sci_experience_paper, use that
    
    if 'comp_sci_experience_paper' in df.columns:
        # This is paper-level CS experience (binary)
        print("\n   Using existing comp_sci_experience_paper variable")
        df['paper_has_cs_experience'] = df['comp_sci_experience_paper']
    
    # Create author position CS experience variables if they don't exist
    if 'first_author_cs_experience' not in df.columns:
        if 'first_author_field' in df.columns:
            df['first_author_cs_experience'] = (df['first_author_field'] == 'computer_science').astype(int)
            print("\n   Created first_author_cs_experience from first_author_field")
        else:
            df['first_author_cs_experience'] = 0
            print("\n   ⚠️  Warning: Could not create first_author_cs_experience")
    
    if 'last_author_cs_experience' not in df.columns:
        if 'last_author_field' in df.columns:
            df['last_author_cs_experience'] = (df['last_author_field'] == 'computer_science').astype(int)
            print("\n   Created last_author_cs_experience from last_author_field")
        else:
            df['last_author_cs_experience'] = 0
            print("\n   ⚠️  Warning: Could not create last_author_cs_experience")
    
    # Print distribution
    print(f"\n   CS experience distribution:")
    if 'paper_has_cs_experience' in df.columns:
        print(f"     Papers with CS experience: {df['paper_has_cs_experience'].sum():,} ({100*df['paper_has_cs_experience'].mean():.2f}%)")
    print(f"     First authors with CS exp: {df['first_author_cs_experience'].sum():,} ({100*df['first_author_cs_experience'].mean():.2f}%)")
    print(f"     Last authors with CS exp: {df['last_author_cs_experience'].sum():,} ({100*df['last_author_cs_experience'].mean():.2f}%)")
    
    # Final summary
    print(f"\n{'='*70}")
    print("FINAL SAMPLE SUMMARY")
    print("="*70)
    
    print(f"\n📊 Sample size: {len(df):,} papers")
    print(f"   SDL: {(df['SDL'] == 1).sum():,} ({100*(df['SDL']==1).sum()/len(df):.2f}%)")
    print(f"   Non-SDL: {(df['SDL'] == 0).sum():,} ({100*(df['SDL']==0).sum()/len(df):.2f}%)")
    
    return df


# ============================================================================
# CS EXPERIENCE REGRESSION MODELS
# ============================================================================

def run_cs_experience_models(df):
    """Run Models 1-5 with CS experience variables"""
    
    print(f"\n{'='*70}")
    print("CS EXPERIENCE REGRESSION MODELS")
    print("="*70)
    
    models = {}
    
    # Check which CS variables are available
    has_paper_cs = 'paper_has_cs_experience' in df.columns
    has_first_cs = 'first_author_cs_experience' in df.columns
    has_last_cs = 'last_author_cs_experience' in df.columns
    
    print(f"\nAvailable CS variables:")
    print(f"   Paper-level CS: {has_paper_cs}")
    print(f"   First author CS: {has_first_cs}")
    print(f"   Last author CS: {has_last_cs}")
    
    # ========================================================================
    # MODEL 1: Option 1 - Paper-level CS Experience
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 1: Paper-Level CS Experience")
    print("="*70)
    print("\nTests: Do papers with CS-experienced authors have different team sizes?")
    print("       Does this differ for SDL papers?")
    
    if has_paper_cs:
        formula1 = '''
            author_count ~ SDL +
            paper_has_cs_experience +
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
        
        print(f"\nFormula: SDL + paper_has_cs_experience + author controls + Full FE")
        
        try:
            model1 = smf.ols(formula1, data=df).fit()
            models['model1'] = model1
            
            print(f"\n✓ Model converged")
            print(f"   R²={model1.rsquared:.4f}")
            print(f"   SDL coef={model1.params['SDL']:.4f} (p={model1.pvalues['SDL']:.4f})")
            print(f"   CS exp coef={model1.params['paper_has_cs_experience']:.4f} (p={model1.pvalues['paper_has_cs_experience']:.4f})")
            
            with open(OUTPUT_DIR / 'model1_paper_cs_experience.txt', 'w') as f:
                f.write(model1.summary().as_text())
            
            print(f"\n✓ Saved: model1_paper_cs_experience.txt")
        
        except Exception as e:
            print(f"\n✗ Model 1 failed: {e}")
            models['model1'] = None
    else:
        print("\n✗ Skipping Model 1 - paper_has_cs_experience not available")
        models['model1'] = None
    
    # ========================================================================
    # MODEL 2: Option 2 - First/Last Author CS Experience
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 2: First/Last Author CS Experience")
    print("="*70)
    print("\nTests: Does CS experience of first/last authors affect team size?")
    print("       Treats CS as author characteristic rather than paper characteristic")
    
    if has_first_cs and has_last_cs:
        formula2 = '''
            author_count ~ SDL +
            first_author_cs_experience +
            last_author_cs_experience +
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
        
        print(f"\nFormula: SDL + first/last CS experience + author controls + Full FE")
        
        try:
            model2 = smf.ols(formula2, data=df).fit()
            models['model2'] = model2
            
            print(f"\n✓ Model converged")
            print(f"   R²={model2.rsquared:.4f}")
            print(f"   SDL coef={model2.params['SDL']:.4f} (p={model2.pvalues['SDL']:.4f})")
            print(f"   First author CS coef={model2.params['first_author_cs_experience']:.4f} (p={model2.pvalues['first_author_cs_experience']:.4f})")
            print(f"   Last author CS coef={model2.params['last_author_cs_experience']:.4f} (p={model2.pvalues['last_author_cs_experience']:.4f})")
            
            with open(OUTPUT_DIR / 'model2_author_cs_experience.txt', 'w') as f:
                f.write(model2.summary().as_text())
            
            print(f"\n✓ Saved: model2_author_cs_experience.txt")
        
        except Exception as e:
            print(f"\n✗ Model 2 failed: {e}")
            models['model2'] = None
    else:
        print("\n✗ Skipping Model 2 - first/last CS experience not available")
        models['model2'] = None
    
    # ========================================================================
    # MODEL 3: Option 3 - SDL × CS Experience Interaction
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 3: SDL × CS Experience Interaction")
    print("="*70)
    print("\nTests: Do SDL papers with CS-experienced teams behave differently?")
    print("       Are SDL effects moderated by CS experience?")
    
    if has_paper_cs:
        formula3 = '''
            author_count ~ SDL * paper_has_cs_experience +
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
        
        print(f"\nFormula: SDL × paper_has_cs_experience interaction + controls + Full FE")
        
        try:
            model3 = smf.ols(formula3, data=df).fit()
            models['model3'] = model3
            
            print(f"\n✓ Model converged")
            print(f"   R²={model3.rsquared:.4f}")
            print(f"   SDL coef={model3.params['SDL']:.4f} (p={model3.pvalues['SDL']:.4f})")
            print(f"   CS exp coef={model3.params['paper_has_cs_experience']:.4f} (p={model3.pvalues['paper_has_cs_experience']:.4f})")
            
            # Check for interaction term
            interaction_vars = [var for var in model3.params.index if 'SDL' in var and 'cs_experience' in var.lower()]
            if interaction_vars:
                for var in interaction_vars:
                    print(f"   Interaction ({var}) coef={model3.params[var]:.4f} (p={model3.pvalues[var]:.4f})")
            
            with open(OUTPUT_DIR / 'model3_sdl_cs_interaction.txt', 'w') as f:
                f.write(model3.summary().as_text())
            
            print(f"\n✓ Saved: model3_sdl_cs_interaction.txt")
        
        except Exception as e:
            print(f"\n✗ Model 3 failed: {e}")
            models['model3'] = None
    else:
        print("\n✗ Skipping Model 3 - paper_has_cs_experience not available")
        models['model3'] = None
    
    # ========================================================================
    # MODEL 4: Option 4 - Last Author CS (PI Focus)
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 4: Last Author CS Experience (PI Focus)")
    print("="*70)
    print("\nTests: Does PI (last author) CS background affect SDL team dynamics?")
    print("       Focuses on senior researcher (PI) characteristics")
    
    if has_last_cs:
        formula4 = '''
            author_count ~ SDL * last_author_cs_experience +
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
        
        print(f"\nFormula: SDL × last_author_cs_experience + controls + Full FE")
        
        try:
            model4 = smf.ols(formula4, data=df).fit()
            models['model4'] = model4
            
            print(f"\n✓ Model converged")
            print(f"   R²={model4.rsquared:.4f}")
            print(f"   SDL coef={model4.params['SDL']:.4f} (p={model4.pvalues['SDL']:.4f})")
            print(f"   Last author CS coef={model4.params['last_author_cs_experience']:.4f} (p={model4.pvalues['last_author_cs_experience']:.4f})")
            
            # Check for interaction
            interaction_vars = [var for var in model4.params.index if 'SDL' in var and 'last_author_cs' in var.lower()]
            if interaction_vars:
                for var in interaction_vars:
                    print(f"   Interaction ({var}) coef={model4.params[var]:.4f} (p={model4.pvalues[var]:.4f})")
            
            with open(OUTPUT_DIR / 'model4_last_author_cs_interaction.txt', 'w') as f:
                f.write(model4.summary().as_text())
            
            print(f"\n✓ Saved: model4_last_author_cs_interaction.txt")
        
        except Exception as e:
            print(f"\n✗ Model 4 failed: {e}")
            models['model4'] = None
    else:
        print("\n✗ Skipping Model 4 - last_author_cs_experience not available")
        models['model4'] = None
    
    # ========================================================================
    # MODEL 5: Option 5 - Citation Impact with CS Experience
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("MODEL 5: Citation Impact with CS Experience")
    print("="*70)
    print("\nTests: Do SDL papers with CS-experienced teams get more citations?")
    print("       Uses citations as dependent variable")
    
    if has_paper_cs and 'asinh_paper_citations' in df.columns:
        formula5 = '''
            asinh_paper_citations ~ SDL * paper_has_cs_experience +
            author_count +
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
        
        print(f"\nFormula: asinh(citations) ~ SDL × CS experience + controls + Full FE")
        
        try:
            model5 = smf.ols(formula5, data=df).fit()
            models['model5'] = model5
            
            print(f"\n✓ Model converged")
            print(f"   R²={model5.rsquared:.4f}")
            print(f"   SDL coef={model5.params['SDL']:.4f} (p={model5.pvalues['SDL']:.4f})")
            print(f"   CS exp coef={model5.params['paper_has_cs_experience']:.4f} (p={model5.pvalues['paper_has_cs_experience']:.4f})")
            
            # Check for interaction
            interaction_vars = [var for var in model5.params.index if 'SDL' in var and 'cs_experience' in var.lower()]
            if interaction_vars:
                for var in interaction_vars:
                    print(f"   Interaction ({var}) coef={model5.params[var]:.4f} (p={model5.pvalues[var]:.4f})")
            
            with open(OUTPUT_DIR / 'model5_citations_cs_interaction.txt', 'w') as f:
                f.write(model5.summary().as_text())
            
            print(f"\n✓ Saved: model5_citations_cs_interaction.txt")
        
        except Exception as e:
            print(f"\n✗ Model 5 failed: {e}")
            models['model5'] = None
    else:
        print("\n✗ Skipping Model 5 - paper_has_cs_experience or citations not available")
        models['model5'] = None
    
    return models


# ============================================================================
# CREATE SUMMARY TABLES
# ============================================================================

def create_summary_tables(models):
    """Create comparison tables for CS experience models"""
    
    print(f"\n{'='*70}")
    print("CREATING SUMMARY TABLES")
    print("="*70)
    
    # Comparison table
    comparison_data = []
    
    for i in range(1, 6):
        model = models.get(f'model{i}')
        if model is not None:
            row = {
                'Model': i,
                'Description': {
                    1: 'Paper-level CS',
                    2: 'Author-level CS',
                    3: 'SDL × CS interaction',
                    4: 'Last author CS × SDL',
                    5: 'Citations with CS'
                }.get(i, f'Model {i}'),
                'SDL_coef': model.params.get('SDL', np.nan),
                'SDL_se': model.bse.get('SDL', np.nan),
                'SDL_pval': model.pvalues.get('SDL', np.nan),
                'R_squared': model.rsquared,
                'Adj_R_squared': model.rsquared_adj,
                'N': int(model.nobs)
            }
            
            # Add CS experience coefficient if available
            cs_vars = [v for v in model.params.index if 'cs_experience' in v.lower() and ':' not in v]
            if cs_vars:
                row['CS_coef'] = model.params[cs_vars[0]]
                row['CS_pval'] = model.pvalues[cs_vars[0]]
            
            # Add interaction coefficient if available
            interaction_vars = [v for v in model.params.index if 'SDL' in v and 'cs_experience' in v.lower()]
            if interaction_vars:
                row['Interaction_coef'] = model.params[interaction_vars[0]]
                row['Interaction_pval'] = model.pvalues[interaction_vars[0]]
            
            comparison_data.append(row)
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        comparison_df.to_csv(OUTPUT_DIR / 'cs_models_comparison.csv', index=False)
        
        print("\n📊 CS Experience Models Comparison:")
        print(comparison_df.to_string(index=False))
        print(f"\n✓ Saved: cs_models_comparison.csv")
    else:
        print("\n⚠️  No models succeeded - cannot create comparison table")
    
    # Interpretation guide
    interpretation = """
CS EXPERIENCE MODELS - INTERPRETATION GUIDE
==========================================

MODEL 1 (Paper-level CS):
- Tests whether papers with CS-experienced authors have different team sizes
- Main effect: paper_has_cs_experience coefficient
- Interpretation: Papers with CS experience have X more/fewer authors on average

MODEL 2 (Author-level CS):
- Tests whether first/last author CS experience affects team size
- Main effects: first_author_cs_experience and last_author_cs_experience
- Interpretation: When first/last author has CS background, team is X larger/smaller

MODEL 3 (SDL × CS interaction):
- Tests whether SDL effect differs for CS-experienced teams
- Key coefficient: SDL:paper_has_cs_experience interaction
- Interpretation: SDL effect on team size is X larger/smaller when team has CS experience

MODEL 4 (Last author CS × SDL):
- Tests whether PI (last author) CS background moderates SDL effect
- Key coefficient: SDL:last_author_cs_experience interaction
- Interpretation: SDL effect differs when PI has CS background

MODEL 5 (Citations with CS):
- Tests whether CS experience affects citation impact
- Dependent variable: asinh(citations) instead of team size
- Key coefficient: SDL:paper_has_cs_experience interaction
- Interpretation: SDL papers with CS experience get X% more/fewer citations
"""
    
    with open(OUTPUT_DIR / 'interpretation_guide.txt', 'w') as f:
        f.write(interpretation)
    
    print("\n✓ Saved: interpretation_guide.txt")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    
    print("="*70)
    print("CS EXPERIENCE REGRESSION ANALYSIS")
    print("Models 1-5")
    print("="*70)
    
    print(f"\n⚙️  Configuration:")
    print(f"   Journal filter: {'ON' if FILTER_CONFIG['use_journal_filter'] else 'OFF'}")
    print(f"   Topic filter: {'ON' if FILTER_CONFIG['use_topic_filter'] else 'OFF'}")
    
    # Load and filter data
    df = load_and_filter_data()
    
    if df is None:
        print("\n✗ Data loading failed. Exiting.")
        sys.exit(1)
    
    # Run CS experience models
    print(f"\n{'='*70}")
    print("RUNNING CS EXPERIENCE MODELS")
    print("="*70)
    print("\nThis will run:")
    print("  • Model 1: Paper-level CS experience")
    print("  • Model 2: First/Last author CS experience")
    print("  • Model 3: SDL × CS experience interaction")
    print("  • Model 4: Last author CS × SDL interaction")
    print("  • Model 5: Citation impact with CS experience")
    print("\nTotal: 5 regression models\n")
    
    models = run_cs_experience_models(df)
    
    # Create summary tables
    create_summary_tables(models)
    
    # Count successful models
    successful = sum(1 for m in models.values() if m is not None)
    total = len(models)
    
    print("\n" + "="*70)
    print("✅ CS EXPERIENCE ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nSuccessfully ran {successful}/{total} models")
    print(f"\nResults saved to: {OUTPUT_DIR}/")
    print(f"  • model1_paper_cs_experience.txt")
    print(f"  • model2_author_cs_experience.txt")
    print(f"  • model3_sdl_cs_interaction.txt")
    print(f"  • model4_last_author_cs_interaction.txt")
    print(f"  • model5_citations_cs_interaction.txt")
    print(f"  • cs_models_comparison.csv")
    print(f"  • interpretation_guide.txt")


if __name__ == "__main__":
    main()