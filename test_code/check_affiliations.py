import pandas as pd
import json
import os

OUTPUT_DIR_CHEM = "../data/fields/chemistry"
OUTPUT_DIR_MAT = "../data/fields/material_science"
OUTPUT_DIR_ENG = "../data/fields/engineering"
OUTPUT_DIR_COMP = "../data/fields/computer_science"
OUTPUT_FILE = "sample_affiliations_multiple.csv"
CHUNK_SIZE = 100000

# Configuration for multi-affiliation check
FIELD_TO_CHECK = "Chemistry"
FIELD_FOLDER = OUTPUT_DIR_CHEM
FIELD_PREFIX = "chemistry"

def extract_raw_affiliations():
    """Extract 5 sample rows where authors have multiple affiliations (>=2)"""
    
    print("="*60)
    print("Extracting Samples with Multiple Affiliations")
    print("="*60 + "\n")
    
    all_samples = []
    
    fields = [
        ("Chemistry", OUTPUT_DIR_CHEM, "chemistry"),
        ("Materials Science", OUTPUT_DIR_MAT, "materials_science"),
        ("Engineering", OUTPUT_DIR_ENG, "engineering"),
        ("Computer Science", OUTPUT_DIR_COMP, "computer_science")
    ]
    
    for field_name, folder, prefix in fields:
        print(f"Processing {field_name}...")
        
        field_samples = []
        
        # Try multiple years until we get 5 samples
        for year in range(2012, 2026):
            if len(field_samples) >= 5:
                break
            
            input_file = os.path.join(folder, f"{prefix}_{year}.tsv")
            
            if not os.path.exists(input_file):
                continue
            
            for chunk in pd.read_csv(input_file, sep='\t', encoding='utf-8',
                                     chunksize=CHUNK_SIZE):
                
                if 'raw_data' not in chunk.columns:
                    print(f"  Warning: raw_data column not found in {field_name}")
                    break
                
                for idx in chunk.index:
                    if len(field_samples) >= 5:
                        break
                    
                    if pd.notna(chunk.at[idx, 'raw_data']):
                        try:
                            raw_data = json.loads(chunk.at[idx, 'raw_data'])
                            authorships = raw_data.get('authorships', [])
                            
                            # Check if ANY author has multiple affiliations
                            has_multiple = False
                            for authorship in authorships:
                                institutions = authorship.get('institutions', [])
                                if len(institutions) >= 2:
                                    has_multiple = True
                                    break
                            
                            # Only save if paper has authors with multiple affiliations
                            if has_multiple and len(authorships) > 0:
                                field_samples.append({
                                    'Field': field_name,
                                    'Year': chunk.at[idx, 'publication_year'],
                                    'Article_ID': chunk.at[idx, 'article_id'],
                                    'Title': chunk.at[idx, 'title'],
                                    'Raw_Authorships': json.dumps(authorships, indent=2)
                                })
                        except:
                            continue
                
                if len(field_samples) >= 5:
                    break
        
        print(f"  Collected {len(field_samples)} samples from {field_name}\n")
        all_samples.extend(field_samples)
    
    # Save to CSV
    if all_samples:
        df = pd.DataFrame(all_samples)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"Saved {len(all_samples)} samples with multiple affiliations to: {OUTPUT_FILE}\n")
    else:
        print("No samples found!")

def count_multiple_affiliations():
    """Count authors with multiple affiliations year by year"""
    
    print("\n" + "="*60)
    print(f"Counting Multiple Affiliations for {FIELD_TO_CHECK}")
    print("="*60 + "\n")
    
    results = []
    
    for year in range(2012, 2026):
        input_file = os.path.join(FIELD_FOLDER, f"{FIELD_PREFIX}_{year}.tsv")
        
        if not os.path.exists(input_file):
            print(f"Year {year}: File not found, skipping")
            continue
        
        print(f"Processing year {year}...")
        
        total_authors = 0
        authors_with_multiple = 0
        total_papers = 0
        
        for chunk in pd.read_csv(input_file, sep='\t', encoding='utf-8',
                                on_bad_lines='skip', chunksize=CHUNK_SIZE):
            
            if 'raw_data' not in chunk.columns:
                print(f"  Warning: raw_data column not found")
                break
            
            for idx in chunk.index:
                if pd.notna(chunk.at[idx, 'raw_data']):
                    try:
                        raw_data = json.loads(chunk.at[idx, 'raw_data'])
                        authorships = raw_data.get('authorships', [])
                        
                        total_papers += 1
                        
                        # Check each author in this paper
                        for authorship in authorships:
                            total_authors += 1
                            
                            # Count institutions for THIS author
                            institutions = authorship.get('institutions', [])
                            
                            # An author has multiple affiliations if len(institutions) >= 2
                            if len(institutions) >= 2:
                                authors_with_multiple += 1
                    except:
                        continue
        
        # Calculate percentage
        percentage = (authors_with_multiple / total_authors * 100) if total_authors > 0 else 0
        
        results.append({
            'Year': year,
            'Total_Papers': total_papers,
            'Total_Authors': total_authors,
            'Authors_Multiple_Affiliations': authors_with_multiple,
            'Percentage': round(percentage, 4)
        })
        
        print(f"  Papers: {total_papers:,}, Authors: {total_authors:,}, "
              f"Multiple: {authors_with_multiple:,} ({percentage:.4f}%)\n")
    
    # Save results
    if results:
        output_file = f"multiple_affiliations_{FIELD_PREFIX}.csv"
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False)
        
        print("="*60)
        print("SUMMARY")
        print("="*60)
        print(df.to_string(index=False))
        print(f"\nSaved to: {output_file}")
        print("="*60 + "\n")
    else:
        print("No data found!")

if __name__ == "__main__":
    extract_raw_affiliations()
    # count_multiple_affiliations()