"""
sdl_presentation_charts.py
Generates descriptive charts for the professor's July presentation.
Run on Narval against the 655K venue-filtered dataset.

Usage: python sdl_presentation_charts.py
Output: saves PNG files to ./presentation_charts/
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# ── CONFIGURE PATHS ──────────────────────────────────────────────────────────
# Adjust DATA_FILE to wherever the 655K subset lives on your system
DATA_FILE = Path("/project/def-kmcel/hridansh/openalex_project/data/regression/regression_dataset_subset.csv")

# Output directory (will be created)
OUT_DIR = Path("./presentation_charts")
OUT_DIR.mkdir(exist_ok=True)

# ── STYLE ────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

BLUE   = "#2563EB"
ORANGE = "#EA580C"
GRAY   = "#94A3B8"
GREEN  = "#16A34A"
PURPLE = "#7C3AED"

SDL_DEF = "SDL_Tomet"   # primary SDL definition to use throughout


# ── LOAD DATA ────────────────────────────────────────────────────────────────
print(f"Loading {DATA_FILE} ...")
COLS = [
    "publication_year", "author_count", "journal", "field",
    "SDL_Brown", "SDL_Tomet", "SDL_Filtered_Tom", "sdl_keyword_measure",
    "high_automation", "AI_Paper", "Robotics_Paper",
    "cited_by_count", "abstract",
]
# Only load columns that exist
avail = pd.read_csv(DATA_FILE, nrows=0).columns.tolist()
use_cols = [c for c in COLS if c in avail]
df = pd.read_csv(DATA_FILE, usecols=use_cols, low_memory=False)

# Filter to 2012–2024 (drop pre-2012 sparse years and incomplete 2025)
df = df[(df["publication_year"] >= 2012) & (df["publication_year"] <= 2024)].copy()
print(f"Loaded {len(df):,} papers (2012–2024)")

sdl_mask = df[SDL_DEF] == 1
years = sorted(df["publication_year"].unique())

# ─────────────────────────────────────────────────────────────────────────────
# Chart 1: SDL paper counts by year (absolute)
# ─────────────────────────────────────────────────────────────────────────────
print("Generating Chart 1: SDL counts by year ...")

sdl_by_year = df[sdl_mask].groupby("publication_year").size()
total_by_year = df.groupby("publication_year").size()

fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(sdl_by_year.index, sdl_by_year.values, color=BLUE, edgecolor="white", linewidth=0.5)
ax.set_xlabel("Publication Year")
ax.set_ylabel("Number of SDL Papers")
ax.set_title("SDL Paper Counts by Year\n(Tomet definition, venue-filtered dataset)", pad=12)
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
ax.set_xticks(years)
ax.tick_params(axis="x", rotation=45)

# Annotate bars
for yr, cnt in sdl_by_year.items():
    ax.text(yr, cnt + 0.5, str(cnt), ha="center", va="bottom", fontsize=9)

plt.tight_layout()
plt.savefig(OUT_DIR / "chart1_sdl_counts_by_year.png", bbox_inches="tight")
plt.close()

# ─────────────────────────────────────────────────────────────────────────────
# Chart 2: SDL share (%) of total papers by year
# ─────────────────────────────────────────────────────────────────────────────
print("Generating Chart 2: SDL share by year ...")

sdl_share = (sdl_by_year / total_by_year * 100).reindex(years).fillna(0)

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(sdl_share.index, sdl_share.values, color=BLUE, linewidth=2.5, marker="o", markersize=6)
ax.fill_between(sdl_share.index, sdl_share.values, alpha=0.15, color=BLUE)
ax.set_xlabel("Publication Year")
ax.set_ylabel("SDL Papers as % of Yearly Total")
ax.set_title("SDL Research as Share of Total Publications\n(Tomet definition, venue-filtered dataset)", pad=12)
ax.set_xticks(years)
ax.tick_params(axis="x", rotation=45)
ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=3))

plt.tight_layout()
plt.savefig(OUT_DIR / "chart2_sdl_share_by_year.png", bbox_inches="tight")
plt.close()

# ─────────────────────────────────────────────────────────────────────────────
# Chart 3: SDL definitions comparison (counts by year, stacked context)
# ─────────────────────────────────────────────────────────────────────────────
print("Generating Chart 3: SDL definitions comparison ...")

def_cols = {
    "Tomet":       ("SDL_Tomet",          BLUE),
    "Filtered Tomet": ("SDL_Filtered_Tom", ORANGE),
    "Brown":       ("SDL_Brown",          GREEN),
    "Keyword":     ("sdl_keyword_measure", PURPLE),
}
def_cols = {k: v for k, v in def_cols.items() if v[0] in df.columns}

fig, ax = plt.subplots(figsize=(10, 5))
for label, (col, color) in def_cols.items():
    series = df[df[col] == 1].groupby("publication_year").size().reindex(years, fill_value=0)
    ax.plot(years, series.values, label=label, color=color, linewidth=2, marker="o", markersize=5)

ax.set_xlabel("Publication Year")
ax.set_ylabel("Number of SDL Papers")
ax.set_title("SDL Paper Counts by Definition and Year", pad=12)
ax.legend(frameon=False)
ax.set_xticks(years)
ax.tick_params(axis="x", rotation=45)

plt.tight_layout()
plt.savefig(OUT_DIR / "chart3_sdl_definitions_comparison.png", bbox_inches="tight")
plt.close()

# ─────────────────────────────────────────────────────────────────────────────
# Chart 4: Mean team size — SDL vs non-SDL by year
# ─────────────────────────────────────────────────────────────────────────────
print("Generating Chart 4: Team size trends ...")

team_sdl     = df[sdl_mask].groupby("publication_year")["author_count"].mean()
team_non_sdl = df[~sdl_mask].groupby("publication_year")["author_count"].mean()

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(team_sdl.index, team_sdl.values, color=BLUE, linewidth=2.5,
        marker="o", markersize=6, label="SDL papers")
ax.plot(team_non_sdl.index, team_non_sdl.values, color=GRAY, linewidth=2.5,
        marker="s", markersize=5, label="Non-SDL papers", linestyle="--")
ax.set_xlabel("Publication Year")
ax.set_ylabel("Mean Team Size (Author Count)")
ax.set_title("Mean Team Size: SDL vs. Non-SDL Papers Over Time\n(Tomet definition)", pad=12)
ax.legend(frameon=False)
ax.set_xticks(years)
ax.tick_params(axis="x", rotation=45)

plt.tight_layout()
plt.savefig(OUT_DIR / "chart4_team_size_sdl_vs_non_sdl.png", bbox_inches="tight")
plt.close()

# ─────────────────────────────────────────────────────────────────────────────
# Chart 5: SDL papers by field (stacked bar)
# ─────────────────────────────────────────────────────────────────────────────
print("Generating Chart 5: SDL by field over time ...")

if "field" in df.columns:
    field_colors = {
        "engineering":      BLUE,
        "materials_science": ORANGE,
        "computer_science":  GREEN,
        "chemistry":         PURPLE,
    }
    field_data = (
        df[sdl_mask]
        .groupby(["publication_year", "field"])
        .size()
        .unstack(fill_value=0)
        .reindex(years, fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    bottom = np.zeros(len(years))
    for field in ["engineering", "materials_science", "computer_science", "chemistry"]:
        if field in field_data.columns:
            vals = field_data[field].values
            ax.bar(years, vals, bottom=bottom,
                   color=field_colors.get(field, GRAY),
                   label=field.replace("_", " ").title(),
                   edgecolor="white", linewidth=0.5)
            bottom += vals

    ax.set_xlabel("Publication Year")
    ax.set_ylabel("Number of SDL Papers")
    ax.set_title("SDL Papers by Field and Year\n(Tomet definition)", pad=12)
    ax.legend(frameon=False, loc="upper left")
    ax.set_xticks(years)
    ax.tick_params(axis="x", rotation=45)

    plt.tight_layout()
    plt.savefig(OUT_DIR / "chart5_sdl_by_field.png", bbox_inches="tight")
    plt.close()

# ─────────────────────────────────────────────────────────────────────────────
# Chart 6: SDL + AI + Robotics overlap (Venn-style bar for 2012-2024)
# ─────────────────────────────────────────────────────────────────────────────
print("Generating Chart 6: SDL / AI / Robotics overlap ...")

if "AI_Paper" in df.columns and "Robotics_Paper" in df.columns:
    sdl  = df[SDL_DEF] == 1
    ai   = df["AI_Paper"] == 1
    robo = df["Robotics_Paper"] == 1

    groups = {
        "SDL only":            (sdl & ~ai & ~robo).sum(),
        "SDL + AI":            (sdl & ai & ~robo).sum(),
        "SDL + Robotics":      (sdl & ~ai & robo).sum(),
        "SDL + AI + Robotics": (sdl & ai & robo).sum(),
    }

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.barh(list(groups.keys()), list(groups.values()),
                   color=[GRAY, BLUE, ORANGE, GREEN], edgecolor="white")
    ax.set_xlabel("Number of Papers")
    ax.set_title("SDL Paper Overlap with AI and Robotics Classification\n(2012–2024, Tomet definition)", pad=12)
    for bar, val in zip(bars, groups.values()):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=10)
    ax.set_xlim(0, max(groups.values()) * 1.15)

    plt.tight_layout()
    plt.savefig(OUT_DIR / "chart6_sdl_ai_robotics_overlap.png", bbox_inches="tight")
    plt.close()

# ─────────────────────────────────────────────────────────────────────────────
# Chart 7: Team size distribution — SDL vs non-SDL (box + strip)
# ─────────────────────────────────────────────────────────────────────────────
print("Generating Chart 7: Team size distribution ...")

fig, ax = plt.subplots(figsize=(7, 5))
data_groups = [
    df[~sdl_mask]["author_count"].clip(upper=20),
    df[sdl_mask]["author_count"].clip(upper=20),
]
bp = ax.boxplot(data_groups, patch_artist=True, widths=0.5,
                medianprops=dict(color="black", linewidth=2))
bp["boxes"][0].set_facecolor(GRAY)
bp["boxes"][1].set_facecolor(BLUE)
for element in ["whiskers", "caps", "fliers"]:
    for item in bp[element]:
        item.set(color=GRAY if bp[element].index(item) < 2 else BLUE)

ax.set_xticklabels(["Non-SDL", "SDL"])
ax.set_ylabel("Team Size (Author Count, capped at 20)")
ax.set_title("Team Size Distribution: SDL vs. Non-SDL\n(2012–2024, Tomet definition)", pad=12)

# Annotate means
for i, (label, data) in enumerate(zip(["Non-SDL", "SDL"], data_groups), start=1):
    mean_val = data.mean()
    ax.text(i, mean_val + 0.3, f"mean={mean_val:.1f}", ha="center", fontsize=10, color="black")

plt.tight_layout()
plt.savefig(OUT_DIR / "chart7_team_size_distribution.png", bbox_inches="tight")
plt.close()

# ─────────────────────────────────────────────────────────────────────────────
# Summary table (printed, not a chart)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("SUMMARY STATISTICS FOR SLIDES")
print("=" * 60)

total = len(df)
n_sdl = sdl_mask.sum()
print(f"\nDataset: {total:,} papers (2012–2024, venue-filtered)")
print(f"SDL papers (Tomet): {n_sdl} ({n_sdl/total*100:.2f}%)")
print(f"Mean team size — SDL:     {df[sdl_mask]['author_count'].mean():.2f}")
print(f"Mean team size — Non-SDL: {df[~sdl_mask]['author_count'].mean():.2f}")
print(f"SDL papers missing abstract: {(sdl_mask & df['abstract'].isna()).sum() if 'abstract' in df.columns else 'N/A'}")

if "cited_by_count" in df.columns:
    print(f"\nMean citations — SDL:     {df[sdl_mask]['cited_by_count'].mean():.1f}")
    print(f"Mean citations — Non-SDL: {df[~sdl_mask]['cited_by_count'].mean():.1f}")

print(f"\nSDL paper counts by field:")
if "field" in df.columns:
    print(df[sdl_mask]["field"].value_counts().to_string())

print(f"\nCharts saved to: {OUT_DIR.resolve()}/")
print("Files:")
for f in sorted(OUT_DIR.glob("*.png")):
    print(f"  {f.name}")
