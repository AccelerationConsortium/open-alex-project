""" Code for the following:
1. Count total rows in each TSV File
2. Breakdown of missing DOIs
3. Count of total ai/robotics papers in TSV files
"""

import pandas as pd
import os

# Configuration
OUTPUT_DIR = "data/engineering_redownload/"
CHUNK_SIZE = 10000

def count_rows_per_year():
    """This function returns the total number of rows of data each TSV file has."""

    total_all_years = 0
    
    for year in range(2022, 2023):
        input_file = os.path.join(OUTPUT_DIR, f"engineering_{year}.tsv")
        
        # Count total rows using chunks
        year_count = 0
        for chunk in pd.read_csv(input_file,sep='\t', chunksize=CHUNK_SIZE):
            year_count += len(chunk)
        
        print("Rows in ", year, ":", year_count)
        total_all_years += year_count
    
    print("Total rows:", total_all_years)

def analyze_dois_per_year():
    """This function gives a complete breakdown of the DOI's missing in each yaer of the dataset.  
    Missing could be in terms of NaN or empty strings."""

    count_rows = 0
    total_missing = 0
    
    for year in range(2012, 2026):
        input_file = os.path.join(OUTPUT_DIR, f"materials_science_{year}.tsv")

        row_count = 0
        missing_count = 0
        
        for chunk in pd.read_csv(input_file, sep='\t', chunksize=CHUNK_SIZE):
            row_count += len(chunk)
            
            # Count missing DOIs for each chunk
            missing_in_chunk = chunk['doi'].isna().sum()  # Check for NaN
            missing_in_chunk += (chunk['doi'] == '').sum()  # Check for empty strings
            
            missing_count += missing_in_chunk
        
        percent_missing = (missing_count / row_count * 100) 
        
        print("Missing in year ", year, ":", percent_missing)
        
        count_rows += row_count
        total_missing += missing_count
    
    overall_percent = (total_missing / count_rows * 100)
    print("Total missing %: ", overall_percent)


OUTPUT_DIR = "data/fields/engineering/"

def count_ai_robotics_papers():
    """Count AI and Robotics papers per year in engineering data"""
    
    print("="*60)
    print("Counting AI and Robotics Papers in Engineering")
    print("="*60 + "\n")
    
    print(f"{'Year':<8} {'Total':<12} {'AI Papers':<12} {'AI %':<10} {'Robotics':<12} {'Robotics %':<10}")
    print("-" * 75)
    
    overall_total = 0
    overall_ai = 0
    overall_robotics = 0
    
    for year in range(2024, 2026):
        eng_file = os.path.join(OUTPUT_DIR, f"engineering_{year}.tsv")
        
        if not os.path.exists(eng_file):
            continue
        
        year_total = 0
        year_ai = 0
        year_robotics = 0
        
        # Count in chunks
        for chunk in pd.read_csv(eng_file, sep='\t', encoding='utf-8',
                               chunksize=CHUNK_SIZE):
            
            year_total += len(chunk)
            
            # Count AI papers
            if 'AI_Paper' in chunk.columns:
                year_ai += (chunk['AI_Paper'] == 1).sum()
            
            # Count Robotics papers
            if 'Robotics_Paper' in chunk.columns:
                year_robotics += (chunk['Robotics_Paper'] == 1).sum()
        
        # Calculate percentages
        ai_pct = (year_ai / year_total * 100) if year_total > 0 else 0
        robotics_pct = (year_robotics / year_total * 100) if year_total > 0 else 0
        
        print(f"{year:<8} {year_total:<12,} {year_ai:<12,} {ai_pct:<10.2f} {year_robotics:<12,} {robotics_pct:<10.2f}")
        
        overall_total += year_total
        overall_ai += year_ai
        overall_robotics += year_robotics
    
    # Overall statistics
    print("-" * 75)
    overall_ai_pct = (overall_ai / overall_total * 100) if overall_total > 0 else 0
    overall_robotics_pct = (overall_robotics / overall_total * 100) if overall_total > 0 else 0
    
    print(f"{'TOTAL':<8} {overall_total:<12,} {overall_ai:<12,} {overall_ai_pct:<10.2f} {overall_robotics:<12,} {overall_robotics_pct:<10.2f}")
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
#     # analyze_dois_per_year()
    # count_rows_per_year()
    count_ai_robotics_papers()