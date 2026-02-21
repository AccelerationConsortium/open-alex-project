# #ATTEMPT TWO SDL CLASSIFICATION TO ADD FOLLOWING COLUMNS:
# # - tomet_al_SDL (1/0)
# # - tomet_al_SDL_document_type (string) 
# # - brown_SDL_papers (1/0)
# # - high_automation_dummy (1/0)
# import pandas as pd
# import json
# import os
# import time
# from multiprocessing import Pool, Manager
# from functools import partial
# import traceback

# # ============================================================================
# # CONFIGURATION
# # ============================================================================

# YEARS = list(range(2004, 2026))  # 2004-2025
# N_CORES = 8
# CHUNK_SIZE = 50000

# # Reference dataset paths
# TOMET_AL_PATH = '../data/sdl/tomet_al_SDL_papers.csv'
# BROWN_PATH = '../data/sdl/brown_SDL_papers.csv'
# HIGH_AUTO_PATH = '../data/tomet_al_table4.csv'

# # Output path for missing papers
# MISSING_PAPERS_PATH = '../data/missing_sdl_papers.csv'

# # ============================================================================
# # CONFIGURATION
# # ============================================================================

# # Fields to process in the field datasets
# FIELDS = ['materials_science']

# # Fields to load from SDL reference datasets (usually keep all 4)
# SDL_FIELDS = ['chemistry', 'materials_science', 'engineering', 'computer_science']

# # ============================================================================
# # HELPER FUNCTIONS
# # ============================================================================

# def normalize_doi(doi):
#     """Normalize DOI for consistent matching"""
#     if pd.isna(doi) or doi == '':
#         return None
#     doi = str(doi).strip().lower()
#     # Remove common prefixes
#     doi = doi.replace('https://doi.org/', '')
#     doi = doi.replace('http://doi.org/', '')
#     doi = doi.replace('doi:', '')
#     return doi if doi else None

# def extract_field_from_raw_data(raw_data_str):
#     """Extract field name from raw_data JSON"""
#     try:
#         if pd.isna(raw_data_str):
#             return None
#         data = json.loads(raw_data_str)
#         primary_topic = data.get('primary_topic', {})
#         field = primary_topic.get('field', {})
#         field_name = field.get('display_name', '').lower().replace(' ', '_')
#         return field_name
#     except:
#         return None

# def load_reference_datasets():
#     """Load all reference datasets and create field-specific lookup dictionaries"""
#     print("\n" + "="*80)
#     print("LOADING REFERENCE DATASETS")
#     print("="*80)
#     print(f"Loading SDL papers for fields: {SDL_FIELDS}")
    
#     # Field-specific lookups - for SDL_FIELDS (all fields in reference data)
#     reference_data = {
#         'tomet_al': {field: {} for field in SDL_FIELDS},
#         'brown': {field: {} for field in SDL_FIELDS},
#         'high_automation': {field: {} for field in SDL_FIELDS}
#     }
    
#     # Field name mapping (raw_data fields → our field names)
#     field_mapping = {
#         'chemistry': 'chemistry',
#         'materials_science': 'materials_science',
#         'material_science': 'materials_science',
#         'engineering': 'engineering',
#         'computer_science': 'computer_science'
#     }
    
#     # Load Tomet et al
#     print("\n[1/3] Loading Tomet et al SDL papers...")
#     try:
#         df_tomet = pd.read_csv(TOMET_AL_PATH)
#         print(f"  - Loaded {len(df_tomet)} papers")
        
#         field_counts = {field: 0 for field in SDL_FIELDS}
        
#         for _, row in df_tomet.iterrows():
#             doi_norm = normalize_doi(row.get('DOI', ''))
#             if not doi_norm:
#                 continue
            
#             # Extract field from raw_data
#             paper_field = extract_field_from_raw_data(row.get('raw_data', ''))
#             if paper_field in field_mapping:
#                 mapped_field = field_mapping[paper_field]
#                 # Only add if this field is in our SDL_FIELDS list
#                 if mapped_field in SDL_FIELDS:
#                     reference_data['tomet_al'][mapped_field][doi_norm] = {
#                         'document_type': row.get('Document Type', 'Not Applicable'),
#                         'full_row': row.to_dict()
#                     }
#                     field_counts[mapped_field] += 1
        
#         print(f"  - By field:")
#         for field in SDL_FIELDS:
#             print(f"    - {field}: {field_counts[field]} papers")
#     except Exception as e:
#         print(f"  ERROR loading Tomet et al: {e}")
#         traceback.print_exc()
    
#     # Load Brown
#     print("\n[2/3] Loading Brown SDL papers...")
#     try:
#         df_brown = pd.read_csv(BROWN_PATH)
#         print(f"  - Loaded {len(df_brown)} papers")
        
#         field_counts = {field: 0 for field in SDL_FIELDS}
        
#         for _, row in df_brown.iterrows():
#             doi_norm = normalize_doi(row.get('doi', ''))
#             if not doi_norm:
#                 continue
            
#             # Extract field from raw_data
#             paper_field = extract_field_from_raw_data(row.get('raw_data', ''))
#             if paper_field in field_mapping:
#                 mapped_field = field_mapping[paper_field]
#                 # Only add if this field is in our SDL_FIELDS list
#                 if mapped_field in SDL_FIELDS:
#                     reference_data['brown'][mapped_field][doi_norm] = {
#                         'full_row': row.to_dict()
#                     }
#                     field_counts[mapped_field] += 1
        
#         print(f"  - By field:")
#         for field in SDL_FIELDS:
#             print(f"    - {field}: {field_counts[field]} papers")
#     except Exception as e:
#         print(f"  ERROR loading Brown: {e}")
#         traceback.print_exc()
    
#     # Load High Automation
#     print("\n[3/3] Loading High Automation papers...")
#     try:
#         df_high_auto = pd.read_csv(HIGH_AUTO_PATH)
#         print(f"  - Loaded {len(df_high_auto)} papers")
        
#         field_counts = {field: 0 for field in SDL_FIELDS}
        
#         for _, row in df_high_auto.iterrows():
#             doi_norm = normalize_doi(row.get('DOI', ''))
#             if not doi_norm:
#                 continue
            
#             # Extract field from raw_data
#             paper_field = extract_field_from_raw_data(row.get('raw_data', ''))
#             if paper_field in field_mapping:
#                 mapped_field = field_mapping[paper_field]
#                 # Only add if this field is in our SDL_FIELDS list
#                 if mapped_field in SDL_FIELDS:
#                     reference_data['high_automation'][mapped_field][doi_norm] = {
#                         'full_row': row.to_dict()
#                     }
#                     field_counts[mapped_field] += 1
        
#         print(f"  - By field:")
#         for field in SDL_FIELDS:
#             print(f"    - {field}: {field_counts[field]} papers")
#     except Exception as e:
#         print(f"  ERROR loading High Automation: {e}")
#         traceback.print_exc()
    
#     print("\n" + "="*80)
#     print("REFERENCE DATASETS LOADED SUCCESSFULLY")
#     print("="*80)
    
#     return reference_data

# def process_chunk(chunk, reference_data, field):
#     """Process a chunk of data and add SDL classification columns"""
#     # Add new columns with defaults
#     chunk['tomet_al_SDL'] = 0
#     chunk['tomet_al_SDL_document_type'] = 'Not Applicable'
#     chunk['brown_SDL_papers'] = 0
#     chunk['high_automation_dummy'] = 0
    
#     # Track matches
#     matches = {
#         'tomet_al': 0,
#         'brown': 0,
#         'high_automation': 0
#     }
    
#     # Get field-specific lookups
#     tomet_lookup = reference_data['tomet_al'][field]
#     brown_lookup = reference_data['brown'][field]
#     high_auto_lookup = reference_data['high_automation'][field]
    
#     # Iterate through chunk and match
#     for idx in chunk.index:
#         doi_norm = normalize_doi(chunk.at[idx, 'doi'])
        
#         if not doi_norm:
#             continue
        
#         # Check Tomet et al (field-specific)
#         if doi_norm in tomet_lookup:
#             chunk.at[idx, 'tomet_al_SDL'] = 1
#             chunk.at[idx, 'tomet_al_SDL_document_type'] = tomet_lookup[doi_norm]['document_type']
#             matches['tomet_al'] += 1
        
#         # Check Brown (field-specific)
#         if doi_norm in brown_lookup:
#             chunk.at[idx, 'brown_SDL_papers'] = 1
#             matches['brown'] += 1
        
#         # Check High Automation (field-specific)
#         if doi_norm in high_auto_lookup:
#             chunk.at[idx, 'high_automation_dummy'] = 1
#             matches['high_automation'] += 1
    
#     return chunk, matches

# def process_single_file(args):
#     """Process a single field-year file"""
#     field, year, reference_data = args
    
#     input_file = f'../data/fields/{field}/{field}_{year}.tsv'
#     output_file = f'../data/fields/{field}/{field}_{year}_sdl_classified.tsv'
    
#     # Check if input file exists
#     if not os.path.exists(input_file):
#         return {
#             'field': field,
#             'year': year,
#             'status': 'SKIPPED',
#             'reason': 'File not found',
#             'papers_processed': 0,
#             'matches': {'tomet_al': 0, 'brown': 0, 'high_automation': 0}
#         }
    
#     try:
#         start_time = time.time()
#         total_papers = 0
#         total_matches = {'tomet_al': 0, 'brown': 0, 'high_automation': 0}
#         first_chunk = True
        
#         # Process file in chunks
#         for chunk_num, chunk in enumerate(pd.read_csv(input_file, sep='\t', chunksize=CHUNK_SIZE), 1):
#             processed_chunk, chunk_matches = process_chunk(chunk, reference_data, field)
            
#             # Write to output file
#             processed_chunk.to_csv(
#                 output_file,
#                 sep='\t',
#                 index=False,
#                 mode='a',
#                 header=first_chunk
#             )
#             first_chunk = False
            
#             # Update totals
#             total_papers += len(chunk)
#             for key in total_matches:
#                 total_matches[key] += chunk_matches[key]
        
#         elapsed = time.time() - start_time
        
#         return {
#             'field': field,
#             'year': year,
#             'status': 'SUCCESS',
#             'papers_processed': total_papers,
#             'matches': total_matches,
#             'time_seconds': elapsed
#         }
        
#     except Exception as e:
#         return {
#             'field': field,
#             'year': year,
#             'status': 'ERROR',
#             'error': str(e),
#             'traceback': traceback.format_exc()
#         }

# def find_missing_papers(reference_data, fields, years):
#     """Find papers in reference datasets that are not in field files"""
#     print("\n" + "="*80)
#     print("FINDING MISSING PAPERS")
#     print("="*80)
    
#     # Collect all DOIs from field files (field-specific)
#     field_dois = {field: set() for field in fields}
    
#     print("\nScanning field files for DOIs...")
#     for field in fields:
#         for year in years:
#             input_file = f'../data/fields/{field}/{field}_{year}.tsv'
#             if not os.path.exists(input_file):
#                 continue
            
#             try:
#                 for chunk in pd.read_csv(input_file, sep='\t', chunksize=CHUNK_SIZE, usecols=['doi']):
#                     chunk_dois = chunk['doi'].apply(normalize_doi).dropna()
#                     field_dois[field].update(chunk_dois)
#             except Exception as e:
#                 print(f"  ✗ Error reading {field} {year}: {e}")
        
#         print(f"  ✓ {field}: {len(field_dois[field])} unique DOIs")
    
#     # Find missing papers (check all SDL_FIELDS, but only for fields we're processing)
#     missing_papers = []
    
#     print("\nChecking Tomet et al papers...")
#     tomet_missing = 0
#     for field in SDL_FIELDS:
#         # Only check missing for fields we're actually processing
#         if field not in fields:
#             continue
#         for doi_norm, data in reference_data['tomet_al'][field].items():
#             if doi_norm not in field_dois[field]:
#                 row = data['full_row'].copy()
#                 row['Source_Classification'] = 'tomet_al'
#                 row['Expected_Field'] = field
#                 missing_papers.append(row)
#                 tomet_missing += 1
#     print(f"  - Found {tomet_missing} missing papers")
    
#     print("\nChecking Brown papers...")
#     brown_missing = 0
#     for field in SDL_FIELDS:
#         # Only check missing for fields we're actually processing
#         if field not in fields:
#             continue
#         for doi_norm, data in reference_data['brown'][field].items():
#             if doi_norm not in field_dois[field]:
#                 row = data['full_row'].copy()
#                 row['Source_Classification'] = 'brown'
#                 row['Expected_Field'] = field
#                 missing_papers.append(row)
#                 brown_missing += 1
#     print(f"  - Found {brown_missing} missing papers")
    
#     print("\nChecking High Automation papers...")
#     high_auto_missing = 0
#     for field in SDL_FIELDS:
#         # Only check missing for fields we're actually processing
#         if field not in fields:
#             continue
#         for doi_norm, data in reference_data['high_automation'][field].items():
#             if doi_norm not in field_dois[field]:
#                 row = data['full_row'].copy()
#                 row['Source_Classification'] = 'high_automation'
#                 row['Expected_Field'] = field
#                 missing_papers.append(row)
#                 high_auto_missing += 1
#     print(f"  - Found {high_auto_missing} missing papers")
    
#     # Save missing papers
#     if missing_papers:
#         df_missing = pd.DataFrame(missing_papers)
#         df_missing.to_csv(MISSING_PAPERS_PATH, index=False)
#         print(f"\n✓ Saved {len(missing_papers)} missing papers to {MISSING_PAPERS_PATH}")
#     else:
#         print("\n✓ No missing papers found!")
    
#     return len(missing_papers)

# # ============================================================================
# # MAIN EXECUTION
# # ============================================================================

# def main():
#     print("\n" + "="*80)
#     print("SDL CLASSIFICATION PIPELINE")
#     print("="*80)
#     print(f"Processing fields: {FIELDS}")
#     print(f"Loading SDL data for: {SDL_FIELDS}")
#     print(f"Years: {YEARS[0]}-{YEARS[-1]}")
#     print(f"Cores: {N_CORES}")
#     print(f"Chunk Size: {CHUNK_SIZE}")
#     print("="*80)
    
#     overall_start = time.time()
    
#     # Step 1: Load reference datasets
#     reference_data = load_reference_datasets()
    
#     # Step 2: Prepare tasks for parallel processing
#     print("\n" + "="*80)
#     print("PREPARING CLASSIFICATION TASKS")
#     print("="*80)
    
#     tasks = []
#     for field in FIELDS:
#         for year in YEARS:
#             tasks.append((field, year, reference_data))
    
#     print(f"\nTotal tasks: {len(tasks)}")
    
#     # Step 3: Process files in parallel
#     print("\n" + "="*80)
#     print("PROCESSING FILES (8 CORES)")
#     print("="*80 + "\n")
    
#     with Pool(N_CORES) as pool:
#         results = pool.map(process_single_file, tasks)
    
#     # Step 4: Generate summary
#     print("\n" + "="*80)
#     print("PROCESSING SUMMARY")
#     print("="*80)
    
#     successful = [r for r in results if r['status'] == 'SUCCESS']
#     errors = [r for r in results if r['status'] == 'ERROR']
#     skipped = [r for r in results if r['status'] == 'SKIPPED']
    
#     print(f"\n✓ Successfully processed: {len(successful)} files")
#     print(f"⊘ Skipped (not found): {len(skipped)} files")
#     print(f"✗ Errors: {len(errors)} files")
    
#     if successful:
#         print("\n" + "-"*80)
#         print("CLASSIFICATION STATISTICS BY FIELD")
#         print("-"*80)
        
#         for field in FIELDS:
#             field_results = [r for r in successful if r['field'] == field]
#             if not field_results:
#                 continue
            
#             total_papers = sum(r['papers_processed'] for r in field_results)
#             total_tomet = sum(r['matches']['tomet_al'] for r in field_results)
#             total_brown = sum(r['matches']['brown'] for r in field_results)
#             total_high_auto = sum(r['matches']['high_automation'] for r in field_results)
#             total_time = sum(r['time_seconds'] for r in field_results)
            
#             print(f"\n{field.upper()}")
#             print(f"  Total Papers: {total_papers:,}")
#             print(f"  Tomet et al SDL: {total_tomet:,}")
#             print(f"  Brown SDL: {total_brown:,}")
#             print(f"  High Automation: {total_high_auto:,}")
#             print(f"  Processing Time: {total_time:.2f}s")
        
#         print("\n" + "-"*80)
#         print("CLASSIFICATION STATISTICS BY YEAR")
#         print("-"*80)
        
#         for year in YEARS:
#             year_results = [r for r in successful if r['year'] == year]
#             if not year_results:
#                 continue
            
#             total_papers = sum(r['papers_processed'] for r in year_results)
#             total_tomet = sum(r['matches']['tomet_al'] for r in year_results)
#             total_brown = sum(r['matches']['brown'] for r in year_results)
#             total_high_auto = sum(r['matches']['high_automation'] for r in year_results)
            
#             print(f"\n{year}")
#             print(f"  Total Papers: {total_papers:,}")
#             print(f"  Tomet et al SDL: {total_tomet:,}")
#             print(f"  Brown SDL: {total_brown:,}")
#             print(f"  High Automation: {total_high_auto:,}")
    
#     if errors:
#         print("\n" + "-"*80)
#         print("ERRORS")
#         print("-"*80)
#         for err in errors:
#             print(f"\n{err['field']} {err['year']}:")
#             print(f"  {err['error']}")
    
#     # Step 5: Find missing papers
#     missing_count = find_missing_papers(reference_data, FIELDS, YEARS)
    
#     # Final summary
#     overall_elapsed = time.time() - overall_start
    
#     print("\n" + "="*80)
#     print("PIPELINE COMPLETE")
#     print("="*80)
#     print(f"Total Execution Time: {overall_elapsed:.2f}s ({overall_elapsed/60:.2f} minutes)")
#     print(f"Files Processed: {len(successful)}")
#     print(f"Missing Papers: {missing_count}")
#     print("="*80 + "\n")

# if __name__ == "__main__":
#     main()


### ATTEMPT TWO EDA
import pandas as pd
import os
import glob
import multiprocessing as mp
from pathlib import Path
import traceback

# ============================================================================
# CONFIGURATION
# ============================================================================

# Path to the files generated by your v2 script
FIELDS_BASE_DIR = Path("../data/fields")
OUTPUT_FIELDS = ['materials_science', 'chemistry', 'engineering', 'computer_science']
YEARS = range(2023, 2026)
NUM_CORES = 4

# Expected file suffix from your v2 code
FILE_SUFFIX = "_sdl_classified.tsv"

# ============================================================================
# WORKER FUNCTION
# ============================================================================

def analyze_file(args):
    field, year = args
    file_path = FIELDS_BASE_DIR / field / f"{field}_{year}{FILE_SUFFIX}"
    
    if not file_path.exists():
        return {
            'Field': field, 'Year': year, 'Status': 'MISSING',
            'Total Rows': 0, 'Tomet': 0, 'Brown': 0, 'HighAuto': 0
        }

    try:
        # Load only necessary columns for speed
        cols_to_check = [
            'doi', 
            'tomet_al_SDL', 
            'brown_SDL_papers', 
            'high_automation_dummy',
            'tomet_al_SDL_document_type'
        ]
        
        # Using low_memory=False to prevent mixed type warnings
        df = pd.read_csv(file_path, sep='\t', usecols=lambda c: c in cols_to_check, low_memory=False)
        
        row_count = len(df)
        
        # 1. Check for Missing Values in critical columns
        missing_doi = df['doi'].isnull().sum() if 'doi' in df.columns else row_count
        
        # 2. Sum Classification columns (Safety check: treat NaNs as 0)
        tomet_count = df['tomet_al_SDL'].fillna(0).sum() if 'tomet_al_SDL' in df.columns else 0
        brown_count = df['brown_SDL_papers'].fillna(0).sum() if 'brown_SDL_papers' in df.columns else 0
        high_auto_count = df['high_automation_dummy'].fillna(0).sum() if 'high_automation_dummy' in df.columns else 0
        
        # 3. Check Document Types validity
        # If we have Tomet matches, do we have Doc Types?
        valid_doc_types = 0
        if 'tomet_al_SDL_document_type' in df.columns:
            # Count non-default values
            valid_doc_types = df[~df['tomet_al_SDL_document_type'].isin(['Not Applicable', 'nan'])].shape[0]

        return {
            'Field': field,
            'Year': year,
            'Status': 'OK',
            'Total Rows': row_count,
            'Missing DOIs': missing_doi,
            'Tomet': int(tomet_count),
            'Brown': int(brown_count),
            'HighAuto': int(high_auto_count),
            'DocTypes': valid_doc_types
        }

    except Exception as e:
        return {
            'Field': field, 'Year': year, 'Status': f"ERROR: {str(e)}",
            'Total Rows': 0, 'Tomet': 0, 'Brown': 0, 'HighAuto': 0
        }

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("="*100)
    print("EDA SANITY CHECK: SDL CLASSIFIED DATASETS")
    print("="*100)

    # Prepare tasks
    tasks = []
    for field in OUTPUT_FIELDS:
        for year in YEARS:
            tasks.append((field, year))

    print(f"Scanning {len(tasks)} files across {NUM_CORES} cores...")
    
    # Run Parallel Processing
    with mp.Pool(NUM_CORES) as pool:
        results = pool.map(analyze_file, tasks)

    # Sort results for display
    results.sort(key=lambda x: (x['Field'], x['Year']))
    
    # Create DataFrame for display
    df_results = pd.DataFrame(results)
    
    # Print Summary Tables by Field
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.colheader_justify', 'right')

    for field in OUTPUT_FIELDS:
        print(f"\n>>> FIELD: {field.upper()}")
        field_data = df_results[df_results['Field'] == field].drop(columns=['Field'])
        
        if field_data.empty:
            print("No data found.")
            continue
            
        # Add a total row at the bottom
        sums = field_data.select_dtypes(include='number').sum()
        total_row = pd.DataFrame(sums).T
        total_row['Year'] = 'TOTAL'
        total_row['Status'] = '-'
        
        final_display = pd.concat([field_data, total_row], ignore_index=True)
        
        # Reorder columns
        cols = ['Year', 'Status', 'Total Rows', 'Missing DOIs', 'Tomet', 'Brown', 'HighAuto', 'DocTypes']
        # Check if columns exist before selecting
        cols = [c for c in cols if c in final_display.columns]
        
        # Format numbers with commas
        formatters = {
            'Total Rows': '{:,.0f}'.format,
            'Missing DOIs': '{:,.0f}'.format,
            'Tomet': '{:,.0f}'.format,
            'Brown': '{:,.0f}'.format,
            'HighAuto': '{:,.0f}'.format,
            'DocTypes': '{:,.0f}'.format
        }
        
        print(final_display.to_string(index=False, formatters=formatters))
        
        # Quick Health Check
        total_rows = sums['Total Rows']
        if total_rows == 0:
            print("!! WARNING: Field appears empty or files are missing.")
        
        total_matches = sums['Tomet'] + sums['Brown'] + sums['HighAuto']
        if total_matches == 0:
            print("!! WARNING: Zero SDL matches found. Check your reference matching logic.")

    print("\n" + "="*100)
    print("SANITY CHECK COMPLETE")
    print("="*100)

if __name__ == "__main__":
    main()