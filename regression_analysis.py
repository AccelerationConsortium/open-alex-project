# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# import scipy.stats as stats
# from sklearn.linear_model import LinearRegression
# from sklearn.preprocessing import OneHotEncoder
# from sklearn.compose import ColumnTransformer
# from sklearn.pipeline import Pipeline
# from sklearn.metrics import r2_score

# # ============================================================================
# # CONFIGURATION
# # ============================================================================
# DATA_FILE = "data/regression/regression_dataset_clean.csv"

# # ============================================================================
# # LOAD DATA
# # ============================================================================
# print("📂 Loading cleaned dataset...")
# df = pd.read_csv(DATA_FILE)
# print(f"✅ Loaded {len(df):,} rows and {len(df.columns)} columns\n")

# # ============================================================================
# # BASIC CHECKS
# # ============================================================================
# print("🔍 Columns available:")
# print(df.columns.tolist())

# # Convert SDL to numeric if needed
# if df["SDL"].dtype == "object":
#     df["SDL"] = df["SDL"].astype(int)

# # Drop any remaining missing values in key variables
# df = df.dropna(subset=[
#     "author_count",
#     "num_paper_affiliations",
#     "first_author_papers",
#     "first_author_citations",
#     "journal",
#     "primary_topic"
# ])

# print(f"\n✅ After cleaning: {len(df):,} rows")

# # ============================================================================
# # DEFINE FEATURES AND TARGET
# # ============================================================================
# target = "author_count"
# numerical_features = [
#     "first_author_papers",
#     "first_author_citations",
#     "num_paper_affiliations",
#     "SDL"
# ]
# categorical_features = ["journal", "primary_topic"]

# X = df[numerical_features + categorical_features]
# y = df[target]

# # ============================================================================
# # PREPROCESSING: ONE-HOT ENCODE CATEGORICAL VARIABLES
# # ============================================================================
# # Limit categories to avoid explosion (optional but recommended)
# for col in categorical_features:
#     top_categories = df[col].value_counts().nlargest(100).index  # keep top 100
#     X[col] = np.where(X[col].isin(top_categories), X[col], "Other")

# preprocessor = ColumnTransformer(
#     transformers=[
#         ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
#         ("num", "passthrough", numerical_features)
#     ]
# )

# # ============================================================================
# # LINEAR REGRESSION MODEL
# # ============================================================================
# print("\n⚙️ Running Linear Regression (Scikit-Learn)...")

# model = Pipeline(steps=[
#     ("preprocessor", preprocessor),
#     ("regressor", LinearRegression())
# ])

# model.fit(X, y)
# y_pred = model.predict(X)

# # ============================================================================
# # OUTPUT SUMMARY
# # ============================================================================
# print("\n" + "="*70)
# print("📈 REGRESSION SUMMARY")
# print("="*70)

# r2 = r2_score(y, y_pred)
# n = len(y)
# p = len(model.named_steps["regressor"].coef_)
# adj_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1)

# print(f"R²: {r2:.4f}")
# print(f"Adjusted R²: {adj_r2:.4f}")

# # Extract coefficients (after preprocessing)
# feature_names = model.named_steps["preprocessor"].get_feature_names_out()
# coef_df = pd.DataFrame({
#     "variable": feature_names,
#     "coef": model.named_steps["regressor"].coef_
# })

# # Save coefficients
# coef_df.to_csv("data/regression/regression_results.csv", index=False)
# print("\n💾 Saved regression results → data/regression/regression_results.csv")

# # ============================================================================
# # MODEL DIAGNOSTICS (on residuals)
# # ============================================================================
# print("\n🔍 Checking model diagnostics...")

# residuals = y - y_pred

# # Q-Q Plot
# plt.figure()
# stats.probplot(residuals, dist="norm", plot=plt)
# plt.title("Normal Q-Q Plot of Residuals")
# plt.show()

# # Residuals vs Fitted
# plt.figure()
# plt.scatter(y_pred, residuals, alpha=0.5)
# plt.axhline(0, color="r", linestyle="--")
# plt.xlabel("Fitted Values")
# plt.ylabel("Residuals")
# plt.title("Residuals vs Fitted")
# plt.show()


import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import numpy as np

# ============================================================================
# CONFIGURATION
# ============================================================================

INPUT_FILE = "data/regression/regression_dataset_clean.csv"
RESULTS_DIR = "data/regression/results"

# Create results directory
import os
os.makedirs(RESULTS_DIR, exist_ok=True)

# ============================================================================
# REGRESSION ANALYSIS
# ============================================================================

def run_regression_analysis():
    """Run OLS regression models"""
    
    print("="*70)
    print("REGRESSION ANALYSIS")
    print("="*70)
    
    # Load cleaned data
    print(f"\n📂 Loading: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, low_memory=False)
    print(f"   Loaded {len(df):,} papers")
    
    # Quick summary
    print(f"\n📊 Data summary:")
    print(f"   Fields: {df['field'].nunique()}")
    print(f"   Journals: {df['journal'].nunique():,}")
    print(f"   Topics: {df['primary_topic'].nunique():,}")
    print(f"   SDL papers: {(df['SDL'] == 1).sum():,}")
    print(f"   Non-SDL papers: {(df['SDL'] == 0).sum():,}")
    
    # ========================================================================
    # MODEL 1: Basic Controls Only
    # ========================================================================
    
    print("\n" + "="*70)
    print("MODEL 1: Basic Controls")
    print("="*70)
    print("\nFormula: author_count ~ num_paper_affiliations + first_author_papers + first_author_citations")
    
    formula1 = '''
    author_count ~ 
        num_paper_affiliations + 
        first_author_papers + 
        first_author_citations
    '''
    
    model1 = smf.ols(formula1, data=df).fit()
    print(model1.summary())
    
    # Save results
    with open(f'{RESULTS_DIR}/model1_basic.txt', 'w') as f:
        f.write(model1.summary().as_text())
    
    # ========================================================================
    # MODEL 2: Add Field Fixed Effects
    # ========================================================================
    
    print("\n" + "="*70)
    print("MODEL 2: + Field Fixed Effects")
    print("="*70)
    print("\nFormula: ... + C(field)")
    
    formula2 = '''
    author_count ~ 
        num_paper_affiliations + 
        first_author_papers + 
        first_author_citations +
        C(field)
    '''
    
    model2 = smf.ols(formula2, data=df).fit()
    print(model2.summary())
    
    with open(f'{RESULTS_DIR}/model2_field_fe.txt', 'w') as f:
        f.write(model2.summary().as_text())
    
    # ========================================================================
    # MODEL 3: Add SDL Indicator
    # ========================================================================
    
    print("\n" + "="*70)
    print("MODEL 3: + SDL Indicator")
    print("="*70)
    print("\nFormula: ... + SDL")
    
    formula3 = '''
    author_count ~ 
        SDL +
        num_paper_affiliations + 
        first_author_papers + 
        first_author_citations +
        C(field)
    '''
    
    model3 = smf.ols(formula3, data=df).fit()
    print(model3.summary())
    
    with open(f'{RESULTS_DIR}/model3_sdl.txt', 'w') as f:
        f.write(model3.summary().as_text())
    
    # ========================================================================
    # MODEL 4: Add Topic Fixed Effects (if not too many topics)
    # ========================================================================
    
    num_topics = df['primary_topic'].nunique()
    
    if num_topics <= 100:  # Only run if manageable number of topics
        print("\n" + "="*70)
        print("MODEL 4: + Topic Fixed Effects")
        print("="*70)
        print(f"\nFormula: ... + C(primary_topic) [{num_topics} topics]")
        
        formula4 = '''
        author_count ~ 
            SDL +
            num_paper_affiliations + 
            first_author_papers + 
            first_author_citations +
            C(field) +
            C(primary_topic)
        '''
        
        try:
            model4 = smf.ols(formula4, data=df).fit()
            print(model4.summary())
            
            with open(f'{RESULTS_DIR}/model4_topic_fe.txt', 'w') as f:
                f.write(model4.summary().as_text())
        except Exception as e:
            print(f"⚠️  Could not run Model 4: {e}")
            print("   (Too many topics or memory issue)")
            model4 = None
    else:
        print(f"\n⚠️  Skipping Model 4 - too many topics ({num_topics})")
        model4 = None
    
    # ========================================================================
    # MODEL COMPARISON
    # ========================================================================
    
    print("\n" + "="*70)
    print("MODEL COMPARISON")
    print("="*70)
    
    comparison = pd.DataFrame({
        'Model': ['Model 1: Basic', 'Model 2: + Field FE', 'Model 3: + SDL'],
        'R-squared': [model1.rsquared, model2.rsquared, model3.rsquared],
        'Adj R-squared': [model1.rsquared_adj, model2.rsquared_adj, model3.rsquared_adj],
        'N': [int(model1.nobs), int(model2.nobs), int(model3.nobs)]
    })
    
    if model4 is not None:
        comparison = pd.concat([comparison, pd.DataFrame({
            'Model': ['Model 4: + Topic FE'],
            'R-squared': [model4.rsquared],
            'Adj R-squared': [model4.rsquared_adj],
            'N': [int(model4.nobs)]
        })], ignore_index=True)
    
    print(comparison.to_string(index=False))
    
    comparison.to_csv(f'{RESULTS_DIR}/model_comparison.csv', index=False)
    
    # ========================================================================
    # KEY COEFFICIENTS TABLE
    # ========================================================================
    
    print("\n" + "="*70)
    print("KEY COEFFICIENTS")
    print("="*70)
    
    key_vars = ['SDL', 'num_paper_affiliations', 'first_author_papers', 'first_author_citations']
    
    coef_table = pd.DataFrame({
        'Variable': key_vars
    })
    
    # Model 1 (no SDL)
    coef_table['Model 1 Coef'] = [
        '-',
        f"{model1.params.get('num_paper_affiliations', np.nan):.4f}",
        f"{model1.params.get('first_author_papers', np.nan):.4f}",
        f"{model1.params.get('first_author_citations', np.nan):.4f}"
    ]
    
    # Model 3 (with SDL)
    coef_table['Model 3 Coef'] = [
        f"{model3.params.get('SDL', np.nan):.4f}",
        f"{model3.params.get('num_paper_affiliations', np.nan):.4f}",
        f"{model3.params.get('first_author_papers', np.nan):.4f}",
        f"{model3.params.get('first_author_citations', np.nan):.4f}"
    ]
    
    coef_table['Model 3 P-value'] = [
        f"{model3.pvalues.get('SDL', np.nan):.4f}",
        f"{model3.pvalues.get('num_paper_affiliations', np.nan):.4f}",
        f"{model3.pvalues.get('first_author_papers', np.nan):.4f}",
        f"{model3.pvalues.get('first_author_citations', np.nan):.4f}"
    ]
    
    print(coef_table.to_string(index=False))
    
    coef_table.to_csv(f'{RESULTS_DIR}/key_coefficients.csv', index=False)
    
    # ========================================================================
    # VISUALIZATIONS
    # ========================================================================
    
    print("\n" + "="*70)
    print("CREATING VISUALIZATIONS")
    print("="*70)
    
    # 1. Coefficient plot for Model 3
    fig, ax = plt.subplots(figsize=(10, 6))
    
    params_to_plot = ['SDL', 'num_paper_affiliations', 'first_author_papers', 'first_author_citations']
    coefs = [model3.params.get(p, 0) for p in params_to_plot]
    conf_int = model3.conf_int()
    errors = [(conf_int.loc[p, 1] - conf_int.loc[p, 0])/2 if p in conf_int.index else 0 for p in params_to_plot]
    
    labels = ['SDL', 'Num Affiliations', 'First Author Papers', 'First Author Citations']
    
    ax.errorbar(coefs, range(len(coefs)), xerr=errors, fmt='o', capsize=5, capthick=2)
    ax.axvline(x=0, color='red', linestyle='--', alpha=0.5)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xlabel('Coefficient Estimate')
    ax.set_title('Model 3: Effect on Team Size (with 95% CI)')
    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{RESULTS_DIR}/coefficients_plot.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✅ Saved: coefficients_plot.png")
    
    # 2. Residuals plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(model3.fittedvalues, model3.resid, alpha=0.3, s=1)
    ax.axhline(y=0, color='red', linestyle='--')
    ax.set_xlabel('Fitted Values')
    ax.set_ylabel('Residuals')
    ax.set_title('Model 3: Residual Plot')
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{RESULTS_DIR}/residuals_plot.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✅ Saved: residuals_plot.png")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    print("\n" + "="*70)
    print("✅ REGRESSION ANALYSIS COMPLETE!")
    print("="*70)
    print(f"\n📁 Results saved to: {RESULTS_DIR}/")
    print(f"   • model1_basic.txt")
    print(f"   • model2_field_fe.txt")
    print(f"   • model3_sdl.txt")
    if model4 is not None:
        print(f"   • model4_topic_fe.txt")
    print(f"   • model_comparison.csv")
    print(f"   • key_coefficients.csv")
    print(f"   • coefficients_plot.png")
    print(f"   • residuals_plot.png")
    
    print("\n" + "="*70)
    
    return {
        'model1': model1,
        'model2': model2,
        'model3': model3,
        'model4': model4
    }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    models = run_regression_analysis()