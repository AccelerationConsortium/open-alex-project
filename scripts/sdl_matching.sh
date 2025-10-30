#!/bin/bash
#SBATCH --job-name=sdl_matching
#SBATCH --account=def-kmcel          # CHANGE THIS
#SBATCH --time=00:30:00                      # 30 minutes (should be enough for 3 years)
#SBATCH --mem=16G                            # 32GB RAM
#SBATCH --cpus-per-task=2                    
#SBATCH --output=../logs/%x-%j.out
#SBATCH --error=../logs/%x-%j.err

echo "=========================================="
echo "SDL Matching for Engineering (2012, 2016, 2022)"
echo "Started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "=========================================="

# Load Python and activate environment
module load python/3.11
source ~/openalex_env/bin/activate

# Navigate to project directory
cd /project/def-kmcel/hridansh/openalex_project  # CHANGE THIS

# Run the SDL matching
python SDL_modify.py

echo ""
echo "=========================================="
echo "Completed at: $(date)"
echo "=========================================="