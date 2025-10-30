#!/bin/bash
#SBATCH --job-name=sdl_team_analysis
#SBATCH --account=def-kmcel          # CHANGE THIS to your prof's account
#SBATCH --time=02:00:00                      # 2 hours
#SBATCH --mem=64G                            # 64GB RAM
#SBATCH --cpus-per-task=4                    # 4 CPU cores
#SBATCH --output=../logs/%x-%j.out
#SBATCH --error=../logs/%x-%j.err

echo "=========================================="
echo "SDL vs Non-SDL Team Size Analysis"
echo "Started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Running on node: $(hostname)"
echo "=========================================="

# Load Python and activate environment
module load python/3.11
source ~/openalex_env/bin/activate

# Navigate to project directory
cd /project/def-kmcel/hridansh/openalex_project

# Print environment info
echo ""
echo "Python version:"
python --version
echo ""
echo "Installed packages:"
pip list | grep -E "pandas|matplotlib|seaborn|numpy"
echo ""

# Run the analysis
echo "Starting SDL vs non-SDL team size analysis..."
python SDL_comparison_graph.py

echo ""
echo "=========================================="
echo "Analysis completed at: $(date)"
echo "=========================================="

# Show what was created
echo ""
echo "Output files created:"
ls -lh results/*.png 2>/dev/null || echo "No PNG files found"
ls -lh results/*.csv 2>/dev/null || echo "No CSV files found"
echo ""
echo "Disk usage:"
du -sh results/