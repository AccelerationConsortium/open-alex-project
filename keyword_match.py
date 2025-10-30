import pandas as pd, json, re, os

email = "hridanshkhaitan@gmail.com"
output_directory = "data/engineering"
batch_size = 10000
words_file = "data/keywords/AI_Keywords.csv"
keyword = 'AI'

def load_keywords():
    """ This function extracts AI/Robotics keywords from a csv file, cleans 
        and stores them for further use."""
        
    df = pd.read_csv(words_file, header=None)
    
    keywords = []
    for col in df.columns: # Removes nan values and store in a list
        no_nan = df[col].dropna()  
        for a in no_nan:
            clean_word = a.strip().lower()
            if clean_word and clean_word not in keywords: 
                keywords.append(clean_word)  
    
    print(len(keywords), " keywords loaded")
    
    return keywords

def reconstruct_abstract(abstract):
    """ Converts the abstract into text format. Open alex natively stores them 
        as key value (words and positions) pairs. This helps to parse thru each abstract faster."""


    if not abstract:
        return ""

    wp = [] # word position pair being stored 
    for word, position in abstract.items():
        for p in position:
            wp.append((p, word))
    
    wp.sort()
    text = ' '.join([w for p, w in wp])
    return text.lower()

def count_keywords(text, keywords):
    """ Count keyword matches using word boundaries """
    if not text:
        return 0
    
    count = 0
    
    for keyword in keywords:
        # Use word boundaries so we don't match partial words
        regex = r'\b' + re.escape(keyword) + r'\b' # regex pattern
        matches = re.findall(regex, text)
        count += len(matches)
    
    return count

def classify_papers_for_year(year, keywords):
    """ This function counts keyword matches in abstracts for a specific year.
    Adds keyword count column and classification dummy variable. 
    Right now, it classifies papers as AI/Robotics if one match found."""
    print("Processing", year)

    input_file = os.path.join(output_directory, f"chemistry_{year}.tsv")
    
    
    temp_file = input_file.replace('.tsv', '_temp.tsv')
    header = True
    year_papers, year_classified = 0, 0
    
    # Create columns to add to the database
    keyword_count = 'number_of_'+keyword+'_words'
    keyword_dummy = keyword+'_Paper'
    
    # Used chunking to break down in batches and ensure safer checks
    f = pd.read_csv(input_file, sep='\t', chunksize=batch_size)
    for chunk in f:
        
        chunk[keyword_count] = 0
        chunk[keyword_dummy] = 0
        
        # Parse each paper to classify it and count
        for i in chunk.index:
            year_papers += 1
            
            # Get the abstract from raw_data
            text = ""
            if pd.notna(chunk.at[i, 'raw_data']):
                raw_data = json.loads(chunk.at[i, 'raw_data']) # Raw data column
                abstract = raw_data.get('abstract_inverted_index')
                text = reconstruct_abstract(abstract)
            
            # Count keywords and mark as AI paper if any found
            count = count_keywords(text, keywords)
            chunk.at[i, keyword_count] = count
                
            if count > 0: 
                chunk.at[i, keyword_dummy] = 1
                year_classified += 1
        
        # Save chunk and move to next

        chunk.to_csv(temp_file, sep='\t', index=False,mode='a', header=header)
        header = False # only write header once
    
    # Replace old file with updated one
    os.replace(temp_file, input_file)
    
    print("Papers:", year_papers, keyword, ":", year_classified)
    return year_papers, year_classified

if __name__ == "__main__":
    keywords = load_keywords()
    
    count_papers = 0
    count_classified = 0
    # year_papers, year_classified = classify_papers_for_year(year, keywords)

    for year in range(2012, 2026):
        year_papers, year_classified = classify_papers_for_year(year, keywords)
        count_papers += year_papers
        count_classified += year_classified
    
    #  Summary
    print("papers processed:", count_papers)
    print("Total", keyword, "papers:", count_classified)