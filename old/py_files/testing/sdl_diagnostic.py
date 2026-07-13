# #!/usr/bin/env python3
# """Profile all regression/author datasets: columns, rows, year range, key flag counts."""
# import glob, os
# import pandas as pd

# BASE = "/project/def-kmcel/hridansh/openalex_project/data"
# PATTERNS = ["regression/*.csv", "yearly_data/*.csv", "yearly_data/test/*.csv",
#             "author/*.csv", "author/*/*.csv"]
# BIG_FILE_GB = 3.0  # header-only above this

# FLAG_COLS = ['SDL', 'SDL_Tomet', 'SDL_Brown', 'SDL_Filtered_Tom', 'sdl_keyword_measure',
#              'high_automation', 'AI_Paper', 'Robotics_Paper', 'comp_sci_experience_paper']

# for pat in PATTERNS:
#     for path in sorted(glob.glob(os.path.join(BASE, pat))):
#         size_gb = os.path.getsize(path) / 1e9
#         print(f"\n{'='*80}\n{path}  ({size_gb:.2f} GB)")
#         try:
#             header = pd.read_csv(path, nrows=0).columns.tolist()
#         except Exception as e:
#             print(f"  could not read header: {e}"); continue
#         print(f"  {len(header)} columns: {header}")

#         if size_gb > BIG_FILE_GB:
#             print("  [large file - header only]"); continue

#         want = [c for c in FLAG_COLS + ['publication_year'] if c in header]
#         if not want:
#             n = sum(len(c) for c in pd.read_csv(path, usecols=[header[0]], chunksize=1_000_000))
#             print(f"  rows: {n:,}"); continue

#         n, yr_min, yr_max = 0, None, None
#         sums = {c: 0 for c in want if c != 'publication_year'}
#         for chunk in pd.read_csv(path, usecols=want, chunksize=1_000_000, low_memory=False):
#             n += len(chunk)
#             if 'publication_year' in chunk:
#                 y = pd.to_numeric(chunk['publication_year'], errors='coerce')
#                 yr_min = min(yr_min, y.min()) if yr_min is not None else y.min()
#                 yr_max = max(yr_max, y.max()) if yr_max is not None else y.max()
#             for c in sums:
#                 sums[c] += pd.to_numeric(chunk[c], errors='coerce').fillna(0).sum()
#         print(f"  rows: {n:,}   years: {yr_min}-{yr_max}")
#         for c, s in sums.items():
#             print(f"  {c}: {int(s):,}")

#!/usr/bin/env python3
import pandas as pd
path = "/project/def-kmcel/hridansh/openalex_project/data/regression/regression_dataset_subset.csv"
df = pd.read_csv(path, usecols=['field', 'comp_sci_experience_paper', 'SDL_Tomet', 'SDL_Brown'])
print(df.groupby('field')['comp_sci_experience_paper'].agg(['sum', 'count', 'mean']))
sdl = (df.SDL_Tomet == 1) | (df.SDL_Brown == 1)
print("\nCS-experience rate among SDL papers:", df.loc[sdl, 'comp_sci_experience_paper'].mean().round(3))
print("CS-experience rate among non-SDL:   ", df.loc[~sdl, 'comp_sci_experience_paper'].mean().round(3))