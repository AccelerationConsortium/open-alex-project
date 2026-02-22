"""
SDL Modification Script

This script takes SDL DOI's from the Tom Et al list and sets SDL = 1 for matching papers 
in the year wise data files.
"""
import pandas as pd, os

output_directory = "data/fields/engineering"  # CHANGE IF NEEDED
# sdl_file = "data/brown_SDL_papers.csv"  
dois_file = "data/SDL_dois.txt"
batch_size = 500000 

def SDL_change():
    """ This function takes DOIs from the SDL database in a text file and tries to find their match in the year files.
    Whever a match is found, it updates the SDL column to 1. """

    # Load DOIs into a set for fast lookup
    with open(dois_file, 'r') as f:
        dois_to_update = set()
        for line in f:
            if line.strip() != '':
                dois_to_update.add(line.strip())
        
    total_match = 0
    
    # Process each year file except 2025 (no SDL yet in 2025)
    for year in range(2004, 2025): # CHANGE IF MORE DATA ADDED
        # Define input file path with year as string
        str_year = str(year)
        input_file = os.path.join(output_directory, f"engineering_{str_year}.tsv")
        # input_file = os.path.join(output_directory, "engineering_" +year+".tsv")
        print("Processing year:", year)
        
        temp = os.path.join(output_directory, f"engineering_{year}_updated.tsv")
        header = True
        matches_per_year = 0
        
        
        # Process file in chunks
        f = pd.read_csv(input_file, sep='\t', chunksize=batch_size)
        for chunk in f:
            
            # Update SDL if there's a match
            # Slower method than using pandas 
            # for i in chunk.index:
            #      if chunk['doi'][i] in dois_to_update:
            #             chunk['SDL'][i] = 1
            #             matches_per_year += 1
                        
                        
            doi_indicator = chunk['doi'].isin(dois_to_update)
            chunk.loc[doi_indicator, 'SDL'] = 1
            matches_per_year += doi_indicator.sum()
            
            # Add to output
            
            chunk.to_csv(temp, sep='\t', index=False, mode='a', header=header)
            header = False # change so that header is only once
        total_match += matches_per_year

        print("Matches found in", year, ":", matches_per_year )
        os.replace(temp, input_file)
    
    print("Total matches:", total_match)

    return total_match

if __name__ == "__main__":
    SDL_change()