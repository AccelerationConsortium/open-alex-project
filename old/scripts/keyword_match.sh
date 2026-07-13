#!/bin/bash
#SBATCH --job-name=classify_engi_AI2024
#SBATCH --account=def-kmcel          # CHANGE THIS
#SBATCH --time=01:00:00                      # 1 hour
#SBATCH --mem=64G                            # 32GB RAM
#SBATCH --cpus-per-task=1                   
#SBATCH --output=../logs/%x-%j.out
#SBATCH --error=../logs/%x-%j.err

echo "=========================================="
echo "Robotics Paper Classification for AI Engi2024"
echo "Started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "=========================================="

# Load Python and activate environment
module load python/3.11
source ~/openalex_env/bin/activate

# Navigate to project directory
cd /project/def-kmcel/hridansh/openalex_project  # CHANGE THIS

# Run the classification (AI keywords)
python sdl_keyword_analysis.py

echo ""
echo "=========================================="
echo "Completed at: $(date)"
echo "=========================================="