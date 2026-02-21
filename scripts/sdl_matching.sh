#!/bin/bash
#SBATCH --job-name=scibert_iteratiion2
#SBATCH --account=def-kmcel          # CHANGE THIS
#SBATCH --time=01:00:00                      # 30 minutes (should be enough for 3 years)
#SBATCH --mem=128G                            # 32GB RAM
#SBATCH --cpus-per-task=1                    
#SBATCH --output=../logs/%x-%j.out
#SBATCH --error=../logs/%x-%j.err

echo "=========================================="
echo "SDL Matching for Engi 2022"
echo "Started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "=========================================="

# Load Python and activate environment
module load python/3.11
source ~/openalex_env/bin/activate

# Navigate to project directory
cd /project/def-kmcel/hridansh/openalex_project/py_code  # CHANGE THIS

# Run the SDL matching
python sciBert.py

echo ""
echo "=========================================="
echo "Completed at: $(date)"
echo "=========================================="