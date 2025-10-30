""" Code used to extract engineering data from Open Alex.
"""
import requests
import pandas as pd
import json
import os

EMAIL = "hridanshkhaitan@gmail.com"
OUTPUT_DIR = "data/engineering"
CHUNK_SIZE = 100000  

def setup_api_params(year):
    url = "https://api.openalex.org/works"
    
    params = {
        "mailto": EMAIL,
        "filter": f"publication_year:{year},primary_topic.field.id:fields/22",
        "per-page": 200,
    }
    
    return url, params

def process_article(article):
    """
    Extract only essential fields to minimize storage.
    Excludes raw_data and other unused fields.
    """
    
    # Basic information
    article_id = article.get('id', '').replace('https://openalex.org/', '')
    doi = article.get('doi', '')
    title = article.get('title', '')
    year = article.get('publication_year', '')
    
    # Author information
    authorships = article.get('authorships', [])
    first_author = ''
    if len(authorships) > 0:
        first_author = authorships[0].get('raw_author_name', '')
    
    author_count = len(authorships)
    
    # Get all author names
    all_authors = '; '.join([a.get('raw_author_name', '') for a in authorships if a.get('raw_author_name')])
    
    # Journal information
    journal = ''
    primary_location = article.get('primary_location')
    if primary_location:
        source = primary_location.get('source')
        if source:
            journal = source.get('display_name', '')
    
    # Abstract - store as JSON string
    abstract_inverted = article.get('abstract_inverted_index')
    abstract_json = json.dumps(abstract_inverted) if abstract_inverted else ''
    
    # Citation count
    cited_by_count = article.get('cited_by_count', 0)
    
    # Open access status
    open_access = article.get('open_access', {})
    is_oa = open_access.get('is_oa', False) if open_access else False
    
    # Related works
    related_works = article.get('related_works', [])
    related_works_json = json.dumps(related_works) if related_works else ''
    
    # Primary topic
    primary_topic = article.get('primary_topic', {})
    primary_topic_name = primary_topic.get('display_name', '') if primary_topic else ''
    
    # All topics
    topics = article.get('topics', [])
    topics_list = [t.get('display_name', '') for t in topics]
    topics_json = json.dumps(topics_list) if topics_list else ''
    
    # SDL column
    sdl = 0
    
    return {
        'article_id': article_id,
        'doi': doi,
        'title': title,
        'publication_year': year,
        'first_author': first_author,
        'author_count': author_count,
        'all_authors': all_authors,
        'journal': journal,
        'abstract_inverted_index': abstract_json,
        'cited_by_count': cited_by_count,
        'is_open_access': is_oa,
        'related_works': related_works_json,
        'primary_topic': primary_topic_name,
        'topics': topics_json,
        'SDL': sdl
    }

def extract_articles_for_year(year):
    """
    Extract all articles for a specific year and save to TSV file.
    Uses cursor pagination and chunks for memory-efficient processing.
    """
    print("Extracting year:", year)
    
    url, params = setup_api_params(year)
    
    cursor_param = "*"
    count_works = 0
    count_api_calls = 0
    batch_data = []
    
    output_file = os.path.join(OUTPUT_DIR, f"engineering_{year}.tsv")
    first_write = True
        
    while cursor_param:
        params["cursor"] = cursor_param
        
        try:
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                print("API Error", response.text)
                break
            
            data = response.json()
            articles = data.get('results', [])
            
            for article in articles:
                processed_article = process_article(article)
                batch_data.append(processed_article)
            
            count_works += len(articles)
            count_api_calls += 1
            
            print(f"Batch {count_api_calls}: +{len(articles)} articles | Total: {count_works}")
            
            # Write in chunks
            if len(batch_data) >= CHUNK_SIZE:
                df = pd.DataFrame(batch_data)
                df.to_csv(output_file, sep='\t', index=False, 
                         mode='a', header=first_write)
                first_write = False
                print("Appended chunk to file")
                batch_data = []  
            
            cursor_param = data.get('meta', {}).get('next_cursor')

        except Exception as e:
            print("Error during API call:", e)
            continue
    
    # Write remaining data
    if batch_data:
        df = pd.DataFrame(batch_data)
        df.to_csv(output_file, sep='\t', index=False, 
                 mode='a', header=first_write)
    
    print("Extraction complete for year:", year)
    print("Total articles:", count_works)

if __name__ == "__main__":
    for year in range(2012, 2026):
        extract_articles_for_year(year)

""" Code used to do SDL matching for engineering
"""


# # FOLLOWING CODE ONLY FOR ENGINEERING
# def normalize_doi(doi):
#     """Normalize DOI format for comparison"""
#     if pd.isna(doi) or doi == '':
#         return None
    
#     doi = str(doi).strip().lower()
#     doi = doi.replace('https://doi.org/', '')
#     doi = doi.replace('http://doi.org/', '')
#     doi = doi.replace('doi:', '')
    
#     return doi if doi else None

# def SDL_change():
#     """
#     This function takes DOIs from the SDL database in a text file and tries to find their match in the year files.
#     Whenever a match is found, it updates the SDL column to 1.
#     """

#     # Load DOIs and normalize
#     print(f"Loading DOIs from SDL Database")
#     with open(dois_file, 'r') as f:
#         dois_raw = [line.strip() for line in f if line.strip()]
    
#     dois_to_update = set(normalize_doi(doi) for doi in dois_raw if normalize_doi(doi))
#     print(f"Loaded {len(dois_to_update)} unique DOIs\n")
        
#     total_matches = 0
    
#     # Process each year file
#     for year in range(2025, 2026):
#         input_file = os.path.join(output_directory, f"engineering_{year}.tsv")
        
#         if not os.path.exists(input_file):
#             print(f"Year {year}: File not found, skipping")
#             continue
            
#         print(f"Processing year {year}...")
        
#         output_file = os.path.join(output_directory, f"engineering_{year}_updated.tsv")
#         first_write = True
#         year_matches = 0
        
#         # Process file in chunks
#         for chunk in pd.read_csv(input_file, sep='\t', encoding='utf-8',
#                                 chunksize=batch_size):
            
#             # Normalize DOIs in chunk
#             chunk['doi_normalized'] = chunk['doi'].apply(normalize_doi)
            
#             # Update SDL if there's a match
#             mask = chunk['doi_normalized'].isin(dois_to_update)
#             chunk.loc[mask, 'SDL'] = 1
#             year_matches += mask.sum()
            
#             # Drop temporary column
#             chunk = chunk.drop('doi_normalized', axis=1)
            
#             # Write chunk to output file
#             chunk.to_csv(output_file, sep='\t', index=False, 
#                         mode='a', header=first_write, encoding='utf-8')
#             first_write = False
        
#         print(f"  Matches found: {year_matches}")
#         total_matches += year_matches
        
#         # Replace original file with updated file
#         os.replace(output_file, input_file)
    
#     print(f"\nTotal matches found: {total_matches}")

#     return total_matches


# if __name__ == "__main__":
#     SDL_change()

""" This part  is used to ai/keyword matching for engineering
"""
import pandas as pd
import json
import re
import os

# Configuration
EMAIL = "hridanshkhaitan@gmail.com"
OUTPUT_DIR = "data/engineering"
CHUNK_SIZE = 10000
KEYWORDS_FILE = "data/keywords/AI_Keywords.csv"
KEYWORD_TYPE = 'AI'

def load_keywords():
    """Load and process keywords from CSV file"""
    
    print(f"Loading {KEYWORD_TYPE} keywords from {KEYWORDS_FILE}...")
    
    keywords_df = pd.read_csv(KEYWORDS_FILE, header=None)
    
    # Flatten all columns into single list
    keywords = []
    for col in keywords_df.columns:
        keywords.extend(keywords_df[col].dropna().tolist())
    
    # Clean and normalize
    keywords = [k.strip().lower() for k in keywords if k.strip()]
    keywords = list(set(keywords))
    
    print(f"Loaded {len(keywords)} unique keywords\n")
    
    return keywords

def reconstruct_abstract(abstract_json):
    """Reconstruct abstract text from JSON string of inverted index"""
    if not abstract_json or abstract_json == '':
        return ""
    
    try:
        abstract_inverted = json.loads(abstract_json)
        word_positions = []
        for word, positions in abstract_inverted.items():
            for pos in positions:
                word_positions.append((pos, word))
        
        word_positions.sort()
        return ' '.join([word for pos, word in word_positions]).lower()
    except:
        return ""

def count_keywords(text, keywords):
    """Count keyword matches in text using word boundaries"""
    if not text:
        return 0
    
    count = 0
    text_lower = text.lower()
    
    for keyword in keywords:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        matches = re.findall(pattern, text_lower)
        count += len(matches)
    
    return count

def classify_papers_for_year(year, keywords):
    """
    Classify papers for a specific year by counting keyword matches in abstracts.
    Adds two columns: keyword count and classification dummy variable.
    """
    
    input_file = os.path.join(OUTPUT_DIR, f"engineering_{year}.tsv")
    
    if not os.path.exists(input_file):
        print(f"Year {year}: File not found, skipping")
        return 0, 0
    
    print(f"Processing year {year}")
    
    output_file = input_file.replace('.tsv', '_temp.tsv')
    first_write = True
    year_papers = 0
    year_classified = 0
    
    # Set column names based on keyword type
    count_col = f'number_of_{KEYWORD_TYPE}_words'
    dummy_col = f'{KEYWORD_TYPE}_Paper'
    
    # Process file in chunks
    for chunk in pd.read_csv(input_file, sep='\t', encoding='utf-8',
                             chunksize=CHUNK_SIZE):
        
        # Initialize new columns
        chunk[count_col] = 0
        chunk[dummy_col] = 0
        
        # Process each row
        for index in chunk.index:
            year_papers += 1
            
            # Extract and reconstruct abstract
            abstract_text = ""
            if pd.notna(chunk.at[index, 'abstract_inverted_index']):
                abstract_json = chunk.at[index, 'abstract_inverted_index']
                abstract_text = reconstruct_abstract(abstract_json)
            
            # Count keywords and classify
            if abstract_text:
                keyword_count = count_keywords(abstract_text, keywords)
                chunk.at[index, count_col] = keyword_count
                
                if keyword_count > 0:
                    chunk.at[index, dummy_col] = 1
                    year_classified += 1
        
        # Write chunk to output file
        chunk.to_csv(output_file, sep='\t', index=False,
                    mode='a', header=first_write, encoding='utf-8')
        first_write = False
    
    # Replace original file with updated file
    os.replace(output_file, input_file)
    
    print(f"  Papers: {year_papers}, {KEYWORD_TYPE}: {year_classified}")
    
    return year_papers, year_classified

if __name__ == "__main__":
    print(f"\n{KEYWORD_TYPE} Paper Classification for Engineering")
    print("="*60 + "\n")

    keywords = load_keywords()
    
    total_papers = 0
    total_classified = 0
    
    for year in range(2016, 2017):
        year_papers, year_classified = classify_papers_for_year(year, keywords)
        total_papers += year_papers
        total_classified += year_classified
    
    # Overall summary
    print("\n" + "="*60)
    print("OVERALL SUMMARY")
    print("="*60)
    print(f"Total papers processed: {total_papers}")
    print(f"Total {KEYWORD_TYPE} papers: {total_classified}")
    print("="*60 + "\n")

