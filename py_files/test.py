# import requests
# import pandas as pd
# import time
# from pathlib import Path

# # --- CONFIGURATION ---
# PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# EMAIL = "hridanshkhaitan@gmail.com"  # Using your email for the OpenAlex polite pool
# INPUT_FILE = PROJECT_DIR / "data/tometal_table4.csv" # Path to the table you created
# OUTPUT_MISSING = "missing_dois.csv"
# OUTPUT_FOUND = "found_in_openalex.csv"
# OUTPUT_FILE = "sdl_table_4_with_oa_data.csv"

# def get_oa_data(doi):
#     """
#     Queries OpenAlex for a specific DOI and extracts the primary research field.
#     """
#     # Clean the DOI for the filter
#     clean_doi = doi.strip().replace("https://doi.org/", "")
#     url = f"https://api.openalex.org/works"
#     params = {
#         'filter': f"doi:{clean_doi}",
#         'mailto': EMAIL,
#         'select': 'id,primary_topic' # Selecting only needed fields for speed
#     }

#     try:
#         response = requests.get(url, params=params, timeout=10)
#         if response.status_code == 200:
#             results = response.json().get('results', [])
#             if results:
#                 work = results[0]
#                 # Extract Field from the primary_topic object
#                 topic = work.get('primary_topic')
#                 field = topic.get('field', {}).get('display_name') if topic else "Unknown"
#                 return True, field
#         return False, "Not Found"
#     except Exception as e:
#         return False, f"Error: {str(e)}"

# def process_table():
#     # Load your manual table
#     df = pd.read_csv(INPUT_FILE)
    
#     found_status = []
#     fields = []
    
#     total = len(df)
#     print(f"Starting OpenAlex cross-reference for {total} items...")

#     for index, row in df.iterrows():
#         doi = str(row['DOI'])
        
#         # Call the API
#         is_found, field_name = get_oa_data(doi)
        
#         found_status.append(is_found)
#         fields.append(field_name)
        
#         # Logging progress
#         status_text = "✓" if is_found else "✗"
#         print(f"[{index+1}/{total}] {status_text} DOI: {doi} | Field: {field_name}")
        
#         # Respect OpenAlex polite pool limits
#         time.sleep(0.5)

#     # Add the new columns
#     df['Found_in_OpenAlex'] = found_status
#     df['Field'] = fields

#     # Save the updated table
#     df.to_csv(OUTPUT_FILE, index=False)
#     print(f"\nProcessing Complete! Updated table saved to: {OUTPUT_FILE}")

# if __name__ == "__main__":
#     process_table()


# import requests
# import pandas as pd
# import json
# import time
# import re
# import os
# from pathlib import Path
# # --- CONFIGURATION ---
# # Based on your infrastructure context

# BASE_DIRECTORY = Path("/project/def-kmcel/hridansh/openalex_project/")


# # --- CONFIGURATION ---
# EMAIL = "hridanshkhaitan@gmail.com"
# INPUT_FILE = BASE_DIRECTORY / "py_code/found_in_openalex.csv"  # 53 papers from Table 4
# OUTPUT_FILE = BASE_DIRECTORY / "high_automation_full_metadata.csv"

# # --- PATHS TO KEYWORD FILES (Update based on your local paths) ---
# #
# AI_KEYWORDS_FILE = BASE_DIRECTORY / "data/keywords/test/AI_Keywords_combined.csv"
# ROBO_KEYWORDS_FILE = BASE_DIRECTORY / "data/keywords/test/robotics_Keywords_generated.csv"

# def load_keywords(file_path):
#     """Loads keywords from a CSV and flattens them into a list."""
#     if os.path.exists(file_path):
#         # Assumes keywords are in the first column
#         df = pd.read_csv(file_path)
#         return df.iloc[:, 0].dropna().tolist()
#     else:
#         print(f"Warning: Keyword file not found at {file_path}")
#         return []

# def count_keywords(text, keywords):
#     if not text or not keywords: return 0
#     # Uses word boundary \b to avoid partial matches
#     pattern = re.compile(r'\b(' + '|'.join([re.escape(str(k)) for k in keywords]) + r')\b', re.IGNORECASE)
#     return len(re.findall(pattern, text))

# def undo_inverted_index(inverted_index):
#     if not inverted_index: return ""
#     word_list = []
#     for word, positions in inverted_index.items():
#         for pos in positions:
#             word_list.append((word, pos))
#     word_list.sort(key=lambda x: x[1])
#     return " ".join([x[0] for x in word_list])

# def process_oa_data():
#     # Load keywords from your project CSVs
#     ai_list = load_keywords(AI_KEYWORDS_FILE)
#     robo_list = load_keywords(ROBO_KEYWORDS_FILE)
    
#     df_refs = pd.read_csv(INPUT_FILE)
#     final_batch = []

#     print(f"Starting extraction for {len(df_refs)} papers...")

#     for index, row in df_refs.iterrows():
#         doi = row['Original_DOI'].replace("https://doi.org/", "")
#         url = f"https://api.openalex.org/works/https://doi.org/{doi}"
        
#         try:
#             response = requests.get(url, params={'mailto': EMAIL})
#             if response.status_code == 200:
#                 article = response.json()
                
#                 # 1. Basic Metadata
#                 id_oa = article.get('id', '').replace('https://openalex.org/', '')
#                 title = article.get('title', '')
#                 year = article.get('publication_year')
                
#                 # 2. Authors & Journal
#                 authorships = article.get('authorships', [])
#                 first_author = authorships[0].get('raw_author_name', '') if authorships else ''
#                 author_count = len(authorships)
#                 journal = article.get('primary_location', {}).get('source', {}).get('display_name', '')

#                 # 3. Topic Extraction
#                 topic_names = [t.get('display_name', '') for t in article.get('topics', [])]
#                 combined_topics = " ".join(topic_names)

#                 # 4. Abstract Reconstruction
#                 abstract = undo_inverted_index(article.get('abstract_inverted_index'))

#                 # 5. Combined Text Analysis (readme.md logic)
#                 # Scanning Title + Abstract + Topics
#                 full_text_for_matching = f"{title} {abstract} {combined_topics}".lower()
                
#                 num_robo = count_keywords(full_text_for_matching, robo_list)
#                 num_ai = count_keywords(full_text_for_matching, ai_list)

#                 # 6. Row Construction
#                 final_batch.append({
#                     'article_id': id_oa,
#                     'doi': f"https://doi.org/{doi}",
#                     'title': title,
#                     'publication_year': year,
#                     'first_author': first_author,
#                     'author_count': author_count,
#                     'journal': journal,
#                     'raw_data': json.dumps(article),
#                     'SDL': 1, 
#                     'number_of_Robotics_words': num_robo,
#                     'Robotics_Paper': 1 if num_robo > 0 else 0,
#                     'number_of_AI_words': num_ai,
#                     'AI_Paper': 1 if num_ai > 0 else 0
#                 })
#                 print(f"[{index+1}] Processed: {doi}")
            
#             time.sleep(0.5) # Polite Pool delay

#         except Exception as e:
#             print(f"Error processing {doi}: {e}")

#     # Output to CSV
#     pd.DataFrame(final_batch).to_csv(OUTPUT_FILE, index=False)
#     print(f"\nFinal dataset with 13 columns saved to {OUTPUT_FILE}")

# if __name__ == "__main__":
#     process_oa_data()


# import pandas as pd
# import os
# import glob
# from multiprocessing import Pool, cpu_count
# from pathlib import Path

# # --- CONFIGURATION ---
# BASE_DIRECTORY = Path("/project/def-kmcel/hridansh/openalex_project/data/fields")

# HIGH_AUTO_FILE = "/project/def-kmcel/hridansh/openalex_project/high_automation_full_metadata.csv"
# CORES = 8 # As requested

# def update_single_file(args):
#     """
#     Processes a single TSV file: updates existing papers to 1 or 0 
#     and returns a list of DOIs processed to help identify what's missing.
#     """
#     file_path, high_auto_dois = args
#     try:
#         df = pd.read_csv(file_path, sep='\t')
        
#         # Initialize column to 0 for all existing papers
#         df['high_automation_tometal'] = 0
        
#         # Vectorized update for matches
#         mask = df['doi'].isin(high_auto_dois)
#         df.loc[mask, 'high_automation_tometal'] = 1
        
#         # Save back to TSV
#         df.to_csv(file_path, sep='\t', index=False)
        
#         found_dois = set(df.loc[mask, 'doi'].tolist())
#         return found_dois
#     except Exception as e:
#         print(f"Error processing {file_path}: {e}")
#         return set()

# def main():
#     # 1. Load High Automation Data
#     high_auto_df = pd.read_csv(HIGH_AUTO_FILE)
#     high_auto_dois = set(high_auto_df['doi'].unique())
    
#     # 2. Get all TSV files in the project structure
#     search_path = os.path.join(BASE_DIRECTORY, "**", "*.tsv")
#     tsv_files = glob.glob(search_path, recursive=True)
    
#     print(f"Starting parallel update of {len(tsv_files)} files using {CORES} cores...")
    
#     # 3. Multiprocessing Execution
#     task_args = [(f, high_auto_dois) for f in tsv_files]
#     with Pool(processes=CORES) as pool:
#         results = pool.map(update_single_file, task_args)
    
#     # 4. Identify papers that didn't exist and need to be added
#     all_found_dois = set().union(*results)
#     missing_dois = high_auto_dois - all_found_dois
    
#     if missing_dois:
#         print(f"Found {len(missing_dois)} papers missing from local folders. Appending them now...")
        
#         for m_doi in missing_dois:
#             paper_row = high_auto_df[high_auto_df['doi'] == m_doi].copy()
#             paper_row['high_automation_tometal'] = 1
            
#             # Determine correct folder and filename based on metadata
#             # Matches logic: data/{field}/{field}_{year}.tsv
#             year = paper_row['publication_year'].values[0]
            
#             # Note: You may need to adjust this mapping logic based on how 
#             # you categorize these specific 53 papers into your 4 field folders.
#             # Here we default to 'chemistry' or a logic based on your tech stack.
#             field = "chemistry" 
#             target_file = os.path.join(BASE_DIRECTORY, field, f"{field}_{year}.tsv")
            
#             if os.path.exists(target_file):
#                 paper_row.to_csv(target_file, sep='\t', index=False, mode='a', header=False)
#                 print(f"Appended {m_doi} to {target_file}")
#             else:
#                 print(f"Warning: Could not find target file {target_file} for missing paper.")

#     print("\nUpdate complete. All existing papers set to 0, Table 4 papers set to 1.")

# if __name__ == "__main__":
#     main()

#ADDING BROWN SDL PAPERS
# import pandas as pd
# import numpy as np
# import os
# import glob
# import re
# from concurrent.futures import ProcessPoolExecutor, as_completed
# from tqdm import tqdm  # Progress tracking library

# # --- CONFIGURATION ---
# # Adjust these paths to your exact cluster locations
# FIELDS_BASE_DIR = "../data/fields"   # Input folder with field_year.tsv files
# SDL_INPUT_FILE = "../data/sdl/brown_SDL_papers.csv"

# OUTPUT_DIR = "../data/fields_final"            # Output folder
# CORES = 8                                      # Number of cores to use


# def normalize_doi(doi):
#     """Normalizes DOI for consistent O(1) matching."""
#     if pd.isna(doi):
#         return ""
#     return str(doi).replace("https://doi.org/", "").strip().lower()

# def load_sdl_reference(sdl_file):
#     """
#     Loads verified SDL papers, DROPS redundant columns, and prepares for integration.
#     """
#     if not os.path.exists(sdl_file):
#         raise FileNotFoundError(f"SDL file not found: {sdl_file}")
        
#     print(f"Loading SDL reference from {sdl_file}...")
#     df_sdl = pd.read_csv(sdl_file)
    
#     # Create normalized DOI for matching logic
#     df_sdl['doi_norm'] = df_sdl['doi'].apply(normalize_doi)
    
#     # Set the flag
#     df_sdl['brown_SDL_papers'] = 1
    
#     # --- CLEANUP: Drop Redundant Columns ---
#     # We remove 'Full Citation' and the original 'DOI' (uppercase) 
#     # because we already have the OpenAlex 'doi' (lowercase) and specific metadata columns.
#     cols_to_drop = ['SDL', 'high_automation_tometal', 'Full Citation', 'DOI']
    
#     # Only drop if they actually exist to avoid errors
#     existing_drop_cols = [c for c in cols_to_drop if c in df_sdl.columns]
#     if existing_drop_cols:
#         print(f"Dropping redundant columns: {existing_drop_cols}")
#         df_sdl = df_sdl.drop(columns=existing_drop_cols)

#     # Build lookup dict {Year: Set(DOIs)}
#     sdl_lookup = {}
#     if 'publication_year' in df_sdl.columns:
#         years = df_sdl['publication_year'].dropna().unique()
#         for year in years:
#             year_int = int(year)
#             dois = set(df_sdl[df_sdl['publication_year'] == year_int]['doi_norm'].values)
#             sdl_lookup[year_int] = dois
#     else:
#         print("WARNING: 'publication_year' not found in SDL file. Appending logic may fail.")
        
#     return df_sdl, sdl_lookup

# def process_single_file(file_path, df_sdl_ref, sdl_lookup):
#     """
#     Worker function to process one TSV file in-place.
#     """
#     file_name = os.path.basename(file_path)
    
#     try:
#         # Extract Year from filename (e.g., "chemistry_2004.tsv")
#         year_match = re.search(r'_(\d{4})\.tsv', file_name)
#         if not year_match:
#             return f"SKIPPED {file_name} (No year pattern found)"
        
#         file_year = int(year_match.group(1))
        
#         # Load Data
#         df = pd.read_csv(file_path, sep='\t', low_memory=False)
        
#         # 1. Remove Old Columns from the Field File
#         cols_to_remove = ['SDL', 'high_automation_tometal']
#         df.drop(columns=[c for c in cols_to_remove if c in df.columns], inplace=True)
        
#         # 2. Initialize Target Column
#         if 'brown_SDL_papers' not in df.columns:
#             df['brown_SDL_papers'] = 0
        
#         # 3. Match Existing Papers
#         # We use the existing 'doi' column in the field file
#         df['temp_doi_norm'] = df['doi'].apply(normalize_doi)
        
#         relevant_sdl_dois = sdl_lookup.get(file_year, set())
        
#         existing_count = 0
#         if relevant_sdl_dois:
#             mask = df['temp_doi_norm'].isin(relevant_sdl_dois)
#             df.loc[mask, 'brown_SDL_papers'] = 1
#             existing_count = mask.sum()
            
#         # 4. Append Missing Papers
#         append_count = 0
#         if relevant_sdl_dois:
#             current_file_dois = set(df['temp_doi_norm'].values)
#             missing_dois = relevant_sdl_dois - current_file_dois
            
#             if missing_dois:
#                 # Get the missing rows from reference
#                 rows_to_append = df_sdl_ref[df_sdl_ref['doi_norm'].isin(missing_dois)].copy()
                
#                 # Drop the norm column before appending so it doesn't leak into the file
#                 rows_to_append = rows_to_append.drop(columns=['doi_norm'], errors='ignore')
                
#                 # Append to the main dataframe
#                 # ignore_index=True resets the index to continuous 0...N
#                 df = pd.concat([df, rows_to_append], ignore_index=True)
                
#                 # Ensure the flag is 1 (fillna handles cases where concat might have introduced NaNs)
#                 df['brown_SDL_papers'] = df['brown_SDL_papers'].fillna(0).astype(int)
                
#                 append_count = len(missing_dois)

#         # 5. Cleanup & Save
#         if 'temp_doi_norm' in df.columns:
#             df.drop(columns=['temp_doi_norm'], inplace=True)
            
#         # Overwrite file
#         df.to_csv(file_path, sep='\t', index=False)
        
#         return f"Processed {file_name}: Marked {existing_count} | Appended {append_count}"

#     except Exception as e:
#         return f"ERROR in {file_name}: {e}"

# def main():
#     # 1. Load Reference
#     try:
#         df_sdl_ref, sdl_lookup = load_sdl_reference(SDL_INPUT_FILE)
#         print(f"Reference loaded: {len(df_sdl_ref)} papers.")
#     except Exception as e:
#         print(f"Critical Error Loading Reference: {e}")
#         return

#     # 2. Find Files (Recursive)
#     search_pattern = os.path.join(FIELDS_BASE_DIR, "**", "*.tsv")
#     files = glob.glob(search_pattern, recursive=True)
    
#     print(f"Found {len(files)} files in {FIELDS_BASE_DIR}")
    
#     if not files:
#         print("No files found! Check path.")
#         return

#     # 3. Execute
#     print(f"Starting processing on {CORES} cores...")
    
#     with ProcessPoolExecutor(max_workers=CORES) as executor:
#         future_to_file = {
#             executor.submit(process_single_file, f, df_sdl_ref, sdl_lookup): f 
#             for f in files
#         }
        
#         for future in tqdm(as_completed(future_to_file), total=len(files), desc="Updating Files"):
#             res = future.result()
#             # Only print errors to keep console clean
#             if "ERROR" in res:
#                 tqdm.write(res)

#     print("\nProcessing Complete.")

# if __name__ == "__main__":
#     main()

# import pandas as pd
# import numpy as np
# import os
# import multiprocessing as mp
# from pathlib import Path
# from tabulate import tabulate # Optional: pip install tabulate for pretty printing

# # ============================================================================
# # CONFIGURATION
# # ============================================================================

# PROJECT_DIR = Path("/project/def-kmcel/hridansh/openalex_project")

# FIELDS = {
#     'chemistry': PROJECT_DIR / "data/fields/chemistry",
#     # 'material_science': PROJECT_DIR / "data/fields/material_science",
#     # 'engineering': PROJECT_DIR / "data/fields/engineering",
#     # 'computer_science': PROJECT_DIR / "data/fields/computer_science"
# }

# YEARS = range(2004, 2025)
# NUM_CORES = 4

# # ============================================================================
# # WORKER FUNCTION
# # ============================================================================

# def check_file_sanity(args):
#     """Analyzes a single file for row counts and missing values"""
#     field_name, field_dir, year = args
    
#     # Locate file
#     possible_files = [
#         field_dir / f"{field_name}_{year}_classified.tsv",
#         field_dir / f"{field_name.replace('_', '')}_{year}_classified.tsv",
#     ]
#     tsv_file = next((f for f in possible_files if f.exists()), None)
    
#     if not tsv_file:
#         return None

#     try:
#         # Read file (we read everything to check all columns for NaNs)
#         df = pd.read_csv(tsv_file, sep='\t', low_memory=False)
        
#         row_count = len(df)
#         # Get missing value counts per column
#         null_counts = df.isnull().sum()
#         cols_with_nans = null_counts[null_counts > 0].to_dict()
        
#         return {
#             'field': field_name,
#             'year': year,
#             'total_papers': row_count,
#             'columns_found': list(df.columns),
#             'missing_values': cols_with_nans,
#             'has_nans': len(cols_with_nans) > 0
#         }
#     except Exception as e:
#         return {'field': field_name, 'year': year, 'error': str(e)}

# # ============================================================================
# # MAIN EXECUTION
# # ============================================================================

# def main():
#     print("="*80)
#     print("DATASET SANITY CHECK (Row Counts & Missing Values)")
#     print("="*80)

#     tasks = []
#     for name, path in FIELDS.items():
#         if path.exists():
#             for year in YEARS:
#                 tasks.append((name, path, year))

#     print(f"Analyzing {len(tasks)} files using {NUM_CORES} cores...")

#     with mp.Pool(NUM_CORES) as pool:
#         results = pool.map(check_file_sanity, tasks)

#     # Filter out None results (missing files) and organize by field
#     valid_results = [r for r in results if r is not None]
    
#     for field in FIELDS.keys():
#         field_data = [r for r in valid_results if r['field'] == field]
#         if not field_data:
#             continue

#         print(f"\n\n>>> FIELD: {field.upper()}")
        
#         table_rows = []
#         for res in field_data:
#             if 'error' in res:
#                 table_rows.append([res['year'], "ERROR", "-", res['error']])
#                 continue

#             # Format the missing values dict into a readable string
#             nan_info = ""
#             if res['has_nans']:
#                 nan_info = ", ".join([f"{col}: {count}" for col, count in res['missing_values'].items()])
#             else:
#                 nan_info = "None"

#             table_rows.append([
#                 res['year'], 
#                 f"{res['total_papers']:,}", 
#                 "YES" if res['has_nans'] else "CLEAN", 
#                 nan_info
#             ])

#         headers = ["Year", "Total Papers", "Any NaNs?", "Missing Value Details (Col: Count)"]
#         print(tabulate(table_rows, headers=headers, tablefmt="grid"))

# if __name__ == "__main__":
#     main()


import requests
import json

# Your dimensions.ai login credentials
EMAIL = "h.khaitan@mail.utoronto.ca"
PASSWORD = "03#Hridanshkha"

# Step 1: Authenticate
login_url = "https://app.dimensions.ai/api/auth.json"
login_resp = requests.post(
    login_url,
    json={"username": EMAIL, "password": PASSWORD}
)

print("Login status:", login_resp.status_code)
print("Response:", login_resp.json())

# If login worked, you'll get a token
if "token" in login_resp.json():
    token = login_resp.json()["token"]
    print("\nAuthentication successful! Token received.")
    
    # Step 2: Try a simple test query
    headers = {"Authorization": f"JWT {token}"}
    
    test_query = """
    search publications
    where year = 2020
    and title = "self-driving laboratory"
    return publications[id+title+year+authors]
    limit 5
    """
    
    resp = requests.post(
        "https://app.dimensions.ai/api/dsl.json",
        data=test_query,
        headers=headers
    )
    
    print("\nQuery status:", resp.status_code)
    result = resp.json()
    print("Result:", json.dumps(result, indent=2))
    
else:
    print("Authentication failed - check credentials")