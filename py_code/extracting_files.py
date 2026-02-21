import requests
import pandas as pd, json, os, time
import traceback

email = "hridanshkhaitan@gmail.com" # For API 
FIELD_IDS = {
    "chemistry": "16", 
    "material_science": "25",
    "engineering": "22",
    "computer_science": "17"
}

batch_size = 100000 

def api_parameters(year, field_id):

    api_key= "Mdaisdaoia1Ep80sWHGRxb"
    url = "https://api.openalex.org/works"

    filter = f"publication_year:{year},primary_topic.field.id:fields/{field_id}"
    parameters = {"api_key": api_key,"mailto": email, "filter": filter, "per-page": 200}
    return url, parameters

def process_article(article):
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
    authorships = article.get('authorships', [])
    author = authorships[0].get('raw_author_name', '') if authorships else ''
    author_count = len(authorships) if authorships else 0  

    # Add column with entire data for easier future access 
    raw_data = json.dumps(article)
    
    return {'article_id': id, 'doi': doi, 'title': title, 'publication_year': year,
        'first_author': author, 'author_count': author_count,'journal': journal,
        'raw_data': raw_data,'SDL': sdl}

def year_by_year_extraction(year, field_name, field_id):
    print(f"Downloading {field_name} {year} data")
    start_time = time.time()
    last_batch_time = time.time()
     
    # Initialize counters
    cursor = "*" 
    count_works, count_calls, batch = 0, 0, []
    first_write = True 

    # Output file name
    output_directory = f"../data/fields/{field_name}"
    os.makedirs(output_directory, exist_ok=True)
    output_file = os.path.join(output_directory, f"{field_name}_{year}.tsv")
        
    url, parameters = api_parameters(year, field_id)

    while cursor:
        parameters["cursor"] = cursor
        try:
            response = requests.get(url, params=parameters)
            if response.status_code != 200:
                print(f"CRITICAL API ERROR: {response.status_code} - {response.text}")
                break
            
            year_chunk = response.json()
            articles = year_chunk.get('results', [])

            if not articles:
                print("End of results reached.")
                break

            for article in articles:
                try:
                    processed_article = process_article(article)
                    batch.append(processed_article)
                except Exception as e:
                    continue
            
            count_works += len(articles)
            count_calls += 1
            
            # PROGRESS TRACKING: Visual indicator for every single API call (200 papers)
            if count_calls % 10 == 0:
                elapsed = time.time() - start_time
                print(f"[{field_name}] Call: {count_calls} | Total Papers: {count_works} | Elapsed: {int(elapsed)}s")
            
            if len(batch) >= batch_size:
                batch_duration = time.time() - last_batch_time
                print(f"--- WRITING TO DISK: {len(batch)} rows ({batch_duration:.2f}s for this batch) ---")
                df_temp = pd.DataFrame(batch)
                df_temp.to_csv(output_file, sep='\t', index=False, mode='a', header=first_write)
                first_write = False
                batch = []
                last_batch_time = time.time()
            
            cursor = year_chunk.get('meta', {}).get('next_cursor')

        except Exception as e:
            print(f"Error during API call: {e}")
            traceback.print_exc()
            time.sleep(2) 
            continue

    if len(batch) > 0:
        pd.DataFrame(batch).to_csv(output_file, sep='\t', index=False, mode='a', header=first_write)

    print(f"COMPLETED: {field_name} {year}. Total: {count_works} in {time.time() - start_time:.2f}s")

def extract_one_row(): 
    """This function will take save one row of data from a specific OpenAlex based data file """
    output_directory = "../data/fields/engineering"

    location = os.path.join(output_directory, "engineering_2020_sdl_classified.tsv")
    df = pd.read_csv(location, sep='\t', nrows=1)
    print (df.head())
    # Save row 
    output_file = os.path.join(output_directory, "sample_row_2024.tsv")
    df.to_csv(output_file, sep='\t', index=False)


if __name__ == "__main__":
    # Corrected the years to run 2004, 2005, and 2006
    for target_year in [2023]:
        for name, f_id in FIELD_IDS.items():
            year_by_year_extraction(target_year, name, f_id)

    # extract_one_row() 
