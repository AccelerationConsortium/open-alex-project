import pandas as pd
import requests
import time

# Configuration
SDL_CSV_FILE = "data/SDL_Database_original.csv"
EMAIL = "hridanshkhaitan@gmail.com"
OUTPUT_FILE = "data/SDL_doi_distribution.csv"

def lookup_all_dois():
    """
    Lookup all DOIs from SDL database
    """
    print("Loading SDL database...")
    sdl_df = pd.read_csv(SDL_CSV_FILE, encoding='ISO-8859-1')
    dois = sdl_df['DOI'].dropna().unique()
    print(f"Found {len(dois)} unique DOIs\n")
    
    results = []
    not_found = []
    
    # Process DOIs
    for i, doi in enumerate(dois, 1):
        print(f"{i}/{len(dois)}: {doi[:50]}...", end=" ")
        
        url = f"https://api.openalex.org/works/doi:{doi.replace('https://doi.org/', '')}"
        
        try:
            response = requests.get(url, params={"mailto": EMAIL}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                field = data.get('primary_topic', {}).get('field', {}).get('display_name', 'No field')
                
                results.append({
                    'DOI': doi,
                    'Field': field,
                    'Title': data.get('title', ''),
                    'Year': data.get('publication_year', '')
                })
                print(f"✓ {field}")
            else:
                not_found.append({'DOI': doi, 'Error': f"Status {response.status_code}"})
                print(f"✗ Not found")
                
        except Exception as e:
            not_found.append({'DOI': doi, 'Error': str(e)})
            print(f"✗ Error")
        
        time.sleep(0.1)
    
    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_FILE, index=False)
    
    # Summary
    print(f"\nTotal: {len(dois)}")
    print(f"Found: {len(results)}")
    print(f"Not found: {len(not_found)}\n")
    
    # Field distribution
    if results:
        print("FIELD DISTRIBUTION\n")
        field_counts = results_df['Field'].value_counts()
        for field, count in field_counts.items():
            print(f"{field}: {count} ({count/len(results)*100:.1f}%)")
    
    # Not found DOIs
    if not_found:
        print(f"\nNot found DOIs ({len(not_found)}):")
        for item in not_found[:10]:
            print(f"  {item['DOI']}")

if __name__ == "__main__":
    lookup_all_dois()