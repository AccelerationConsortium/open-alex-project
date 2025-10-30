import requests
import pandas as pd, json, os, time

email = "hridanshkhaitan@gmail.com" # For API 
output_directory = "data/engineering_redownload"
batch_size = 100000 # Can change according to total size 

def api_parameters(year):
    """Function to modify API parameters as needed for different fields/years."""
    url = "https://api.openalex.org/works"

    filter = "publication_year:" + str(year) + ",primary_topic.field.id:fields/22"  # Field ID for Engineering

    parameters = {"mailto": email,"filter": filter, "per-page": 200}
    return url, parameters

def process_article(article):
    """This function will extract all required fields from a single article JSON object from the OpenAlex API.
    This will return a dictionary with all required fields which can be inserted into our database."""
        # Dummy variable
    sdl = 0
    # Extract straightforward info such as id and title
    id = article.get('id', '').replace('https://openalex.org/', '')
    doi = article.get('doi', '')
    title = article.get('title', '')
    year = article.get('publication_year')
    # Get publication journal name
    journal = ''
    primary_location = article.get('primary_location')
    if primary_location:
        source = primary_location.get('source')
        if source:
            journal = source.get('display_name', '')
    # Authors information
    authorships = article.get('authorships', [])
    if len(authorships) > 0:
        author = authorships[0].get('raw_author_name', '')
    else:
        author = ''
    author_count = len(authorships)
    
    # Add column with entire data for easier future access
    raw_data = json.dumps(article)
    
    final_article = {'article_id': id, 'doi': doi, 'title': title, 'publication_year': year,
        'first_author': author, 'author_count': author_count,'journal': journal,
        'raw_data': raw_data,'SDL': sdl}
    
    return final_article


def year_by_year_extraction(year):
    """Here all articles for a specific year and field will be extracted and saved to a TSV file.
    Cursor pagination and chunking are used to ensure efficient processing given large nature of dataset.
    """
    print("Downloading ", year, "data")
    start_time = time.time()
     
    os.makedirs(output_directory, exist_ok=True)

    # Initialize counters
    cursor = "*" # This variable helps with pagination for the API call.
    count_works, count_calls, batch = 0, 0, []
    first_write = True # Allows to check if header is present

    
    # Output file name
    output_file = os.path.join(output_directory, "engineering"+"_"+str(year)+".tsv")
        
        # Call function get parameters
    url, parameters = api_parameters(year)

    while cursor:
        parameters["cursor"] = cursor
        
        # Here will send teh api request. Then for each chunk of articles returned, process each article
        # and append the batch to be appended to file later.
        try:
            response = requests.get(url, params=parameters)
            if response.status_code != 200:
                print("API Error", response.text)
                break
            year_chunk = response.json()
            articles = year_chunk.get('results')

            # Process each article by calling function
            for article in articles:

                processed_article = process_article(article)
                batch.append(processed_article)
            
            count_works += len(articles)
            count_calls += 1
            
            # Progress update
            print("Batch:",  {count_calls},  "Total:", {count_works} )
            
            # Df appened to output file once chunk size reached
            if len(batch) >= batch_size:
                df_temp = pd.DataFrame(batch)
                df_temp.to_csv(output_file, sep='\t', index=False, mode='a', header=first_write)
                first_write = False # Header doesnt get added anymore
                batch = [] 

                print("Appended chunk to file")
                 
            
            cursor = year_chunk.get('meta', {}).get('next_cursor')

        except Exception as e:
            #print("Error report:", e)
            print("Error during API call", e)
            continue
    
    # Append final chunk
    if len(batch) > 0:
            pd.DataFrame(batch).to_csv(output_file, sep='\t', index=False, mode='a', header=first_write)

    
    # Final summary
    print("Extraction complete for ", year, " Total articles added:", count_works)
    print("Time taken (seconds):", time.time() - start_time)

def extract_one_row(): 
    """This function will take save one row of data from a specific OpenAlex based data file """
    
    location = os.path.join(output_directory, "engineering_2025.tsv")
    df = pd.read_csv(location, sep='\t', nrows=1)
    print (df.head())
    # Save row 
    output_file = os.path.join(output_directory, "sample_row_2025.tsv")
    df.to_csv(output_file, sep='\t', index=False)
    
# Execute files from here
if __name__ == "__main__":
    year_by_year_extraction(2020)
    # extract_one_row() 
