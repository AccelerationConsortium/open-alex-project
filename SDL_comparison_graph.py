import pandas as pd, matplotlib.pyplot as plt, numpy as np, json, os

batch_size = 100000
fields = {
        'chemistry': 'data/chemistry',
        'materials_science': 'data/material_science',
        'engineering': 'data/engineering'
}

def extract_sdl_data(years):
    """Function will extract all author counts for all papers in the database where SDL = 1.
    """
    print("Extracting SDL papers")
    
    sdl_data, year_labels = [], []
    
    for year in years:
        authors = []
        
        for field, location in fields.items():
            f = os.path.join(location, f"{field}_{year}.tsv")
  
            for chunk in pd.read_csv(f, sep='\t', usecols=['author_count', 'SDL'], chunksize=batch_size):
                chunk = chunk.dropna(subset=['author_count', 'SDL'])
                sdl_papers = chunk[chunk['SDL'] == 1]
                author_column = sdl_papers['author_count'].tolist()
                authors.extend(author_column)
        
        if len(authors) > 0:
            sdl_data.append(authors)
            year_labels.append(year)
    
    total = 0
    for row in sdl_data:
        total += len(row)
    print("Total SDL papers:", total)
    
    return sdl_data, year_labels


def get_journal(years):
    """Helper function to get a list of all uniqe journals from SDL papers."""
    print("Collecting SDL journals")
    
    sdl_journals = set()
    
    
    for year in years:
        for field, location in fields.items():
            f = os.path.join(location, f"{field}_{year}.tsv")

            
            for chunk in pd.read_csv(f, sep='\t', usecols=['journal', 'SDL'], chunksize=batch_size):
                sdl_papers = chunk[chunk['SDL'] == 1]
                journals = sdl_papers['journal'].dropna().tolist()
                sdl_journals.update(journals)
    
    print(len(sdl_journals),  "unique journals")
    return sdl_journals

def get_topic(years):
    """Helper function to get a list of all unique topics from SDL papers."""
    print("Collecting SDL topics")
    
    sdl_topics = set()
    
    for year in years:
        for field, location in fields.items():
            f = os.path.join(location, f"{field}_{year}.tsv")

            
            for chunk in pd.read_csv(f, sep='\t', usecols=['SDL', 'raw_data'], chunksize=batch_size):
                sdl_papers = chunk[chunk['SDL'] == 1]
                
                # go through raw data for each paper and extract primary topci
                for raw in sdl_papers['raw_data'].dropna():
                    data = json.loads(raw)
                    topic = data.get('primary_topic', {}).get('display_name')
                    if topic:
                        sdl_topics.add(topic)

    
    print(len(sdl_topics), "unique topics")
    return sdl_topics


def extract_non_sdl_data(filter='none', sdl_journals, sdl_topics, years):
    """
    Function to extract all the data where SDL = 0. This will also have a filter function to 
    extract only papers from the same journals or topics or both as the SDL papers.

    Variables (Below is a list of what values to input when calling the function):
        filter: 'none', 'journals', 'topics', or 'both'
        sdl_journals: output of get_journal() function. Input 'none' if not used
        sdl_topics: output of get_topic() function. Input 'none' if not used
        years: years to extract"""

    print(f"Extracting non-SDL papers")
    
    non_sdl_data, year_labels = [], []

    
    # First the columns which are to be extracted is chosen
    if filter == "none":
        columns = ['author_count', 'SDL']
    elif filter == 'journals':
        columns = ['author_count', 'SDL', 'journal']
    elif filter == 'topics':
        columns = ['author_count', 'SDL', 'raw_data']
    else:
        columns = ['author_count', 'SDL', 'journal', 'raw_data']

    # Based on filter, per year extraction is done
    for year in years:
        authors = []
        
        for field, location in fields.items():
            f = os.path.join(location, f"{field}_{year}.tsv")
            

            for chunk in pd.read_csv(f, sep='\t', usecols=columns, chunksize=batch_size):
                chunk = chunk.dropna(subset=['author_count', 'SDL'])
                non_sdlpapers = chunk[chunk['SDL'] == 0]
                
                # Choose which data to extract based on the filter
                if filter == 'none':
                    author_column = non_sdlpapers['author_count'].tolist()
                    authors.extend(author_column)

                elif filter == 'journals':
                    a = non_sdlpapers[non_sdlpapers['journal'].isin(sdl_journals)]
                    author_column = a['author_count'].tolist()
                    authors.extend(author_column)

                elif filter == 'topics':
                    for i in non_sdlpapers.index:
                        data = json.loads(non_sdlpapers.at[i, 'raw_data'])
                        b = data.get('primary_topic', {})
                        topic = b.get('display_name')
                        
                        if topic and topic in sdl_topics:
                            authors.append(non_sdlpapers.at[i, 'author_count'])

                else: # both journals and topics
                    for i in non_sdlpapers.index:

                        journal = chunk.at[i, 'journal']
                        if pd.isna(journal):
                            continue

                        if journal not in sdl_journals:
                            continue
                       
                        c = json.loads(chunk.at[i, 'raw_data'])
                        topic = c.get('primary_topic', {}).get('display_name')
                            
                        if topic and topic in sdl_topics:
                            authors.append(chunk.at[i, 'author_count'])

        
        
        non_sdl_data.append(authors)
        year_labels.append(year)
        print(len(authors), "non-SDL papers in",  year)
    total = 0 
    for row in non_sdl_data:
        total += len(row)
    print(f"Total non-SDL papers:", total)
    
    return non_sdl_data, year_labels


def extract_ai_robotics_non_sdl(keyword_type='AI', years):
    """
    Function will extract data based on whether paper is classified as AI/Robotics. 
    Additionally, will only extract data where SDL = 0
    
    Variables(Below is a list of what values to input when calling the function):
        keyword_type: 'AI' or 'Robotics'
        years: years to extract"""

    print(f"Extracting papers for keyword", keyword_type)
    
    data, year_labels = [], []
    
    column = keyword_type + '_Paper'
    
    # Per year extraction 
    for year in years:
        authors = []
        
        for field, location in fields.items():
            f = os.path.join(location, f"{field}_{year}.tsv")

            for chunk in pd.read_csv(f, sep='\t', usecols=['author_count', 'SDL', column], 
                                    chunksize=batch_size):
                chunk = chunk.dropna(subset=['author_count', 'SDL', column])
                
                # Get AI/Robotics papers that are NOT SDL
                filtered = chunk[(chunk[column] == 1) & (chunk['SDL'] == 0)]
                authors.extend(filtered['author_count'].tolist())
        
        if len(authors) > 0:
            data.append(authors)
            year_labels.append(year)
            print(f"  Year {year}: {len(authors)} {keyword_type} papers")
    
    total = sum(len(d) for d in data)
    print(f"Total {keyword_type} papers (non-SDL): {total}\n")
    
    return data, year_labels

def plot_team_size_comparison(sdl_data, non_sdl_data, year_labels, title_suffix=""):
    """Function to plot team size comparison given data for sdl and non sdl papers.
    
    Variables:
        sdl_data: output of extract_sdl_data function
        non_sdl_data: output of extract_non_sdl_data function
        year_labels: list of years corresponding to the data
        title_suffix: Plot title for context"""
    
    sdl_means = [np.mean(d) for d in sdl_data]
    sdl_stds = [np.std(d) for d in sdl_data]
    non_sdl_means = [np.mean(d) for d in non_sdl_data]
    non_sdl_stds = [np.std(d) for d in non_sdl_data]
    
    x = np.arange(len(year_labels))
    width = 0.35
    
    plt.figure(figsize=(12, 6))
    plt.bar(x - width/2, sdl_means, width, yerr=sdl_stds, label='SDL Papers', capsize=5)
    plt.bar(x + width/2, non_sdl_means, width, yerr=non_sdl_stds, label='Non-SDL Papers', capsize=5)
    
    plt.xlabel('Year')
    plt.ylabel('Average Team Size')
    plt.title(f'Team Size Comparison: SDL vs Non-SDL Papers{title_suffix}')
    plt.xticks(x, year_labels)
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    
    filename = f'team_size{title_suffix.lower().replace(" ", "_").replace("(", "").replace(")", "")}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.show()
    
    # Print statistics
    print(f"\nSUMMARY STATISTICS")
    print(f"Year    SDL Mean    SDL Std    Non-SDL Mean    Non-SDL Std    Difference")
    print("-" * 80)
    
    for i, year in enumerate(year_labels):
        diff = sdl_means[i] - non_sdl_means[i]
        print(f"{year}    {sdl_means[i]:.2f}        {sdl_stds[i]:.2f}       "
              f"{non_sdl_means[i]:.2f}            {non_sdl_stds[i]:.2f}           {diff:.2f}")
    
    print("-" * 80)
    all_sdl = [item for sublist in sdl_data for item in sublist]
    all_non_sdl = [item for sublist in non_sdl_data for item in sublist]
    
    overall_sdl_mean = np.mean(all_sdl)
    overall_sdl_std = np.std(all_sdl)
    overall_non_sdl_mean = np.mean(all_non_sdl)
    overall_non_sdl_std = np.std(all_non_sdl)
    overall_diff = overall_sdl_mean - overall_non_sdl_mean
    
    print(f"OVERALL {overall_sdl_mean:.2f}        {overall_sdl_std:.2f}       "
          f"{overall_non_sdl_mean:.2f}            {overall_non_sdl_std:.2f}           {overall_diff:.2f}")

# Calling functions from here
if __name__ == "__main__":
    
    # OPTION 1: All data (no filtering)
    sdl_data, sdl_years = extract_sdl_data(range(2012-2026))
    non_sdl_data, non_sdl_years = extract_non_sdl_data(filter='none')
    plot_team_size_comparison(sdl_data, non_sdl_data, sdl_years, " (All Data)")
    
    # # OPTION 2: Same journals only
    # sdl_data, sdl_years = extract_sdl_data()
    # sdl_journals = get_journal()
    # non_sdl_data, non_sdl_years = extract_non_sdl_data(filter='journals', sdl_journals=sdl_journals)
    # plot_team_size_comparison(sdl_data, non_sdl_data, sdl_years, " (Same Journals)")
    
    # # OPTION 3: Same topics only
    # sdl_data, sdl_years = extract_sdl_data()
    # sdl_topics = get_topic()
    # non_sdl_data, non_sdl_years = extract_non_sdl_data(filter='topics', sdl_topics=sdl_topics)
    # plot_team_size_comparison(sdl_data, non_sdl_data, sdl_years, " (Same Topics)")
    
    # # OPTION 4: SDL vs AI papers
    # sdl_data, sdl_years = extract_sdl_data()
    # ai_data, ai_years = extract_ai_robotics_non_sdl(keyword_type='AI')
    # plot_team_size_comparison(sdl_data, ai_data, sdl_years, " (SDL vs AI)")
    
    # # OPTION 5: SDL vs Robotics papers
    # sdl_data, sdl_years = extract_sdl_data()
    # robotics_data, robotics_years = extract_ai_robotics_non_sdl(keyword_type='Robotics')
    # plot_team_size_comparison(sdl_data, robotics_data, sdl_years, " (SDL vs Robotics)")
    
    # # OPTION 6: Same journals AND topics
    # sdl_data, sdl_years = extract_sdl_data()
    # sdl_journals = get_journal()
    # sdl_topics = get_topic()
    # non_sdl_data, non_sdl_years = extract_non_sdl_data(filter='both', 
    #                                                     sdl_journals=sdl_journals, 
    #                                                     sdl_topics=sdl_topics)
    # plot_team_size_comparison(sdl_data, non_sdl_data, sdl_years, " (Same Journals and Topics)")