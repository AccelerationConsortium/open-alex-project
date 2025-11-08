#!/bin/bash
#SBATCH --job-name=graphs_for_COMPSCI5
#SBATCH --account=def-kmcel                  
#SBATCH --time=4:30:00                      
#SBATCH --mem=128G                           
#SBATCH --cpus-per-task=1                  
#SBATCH --output=../logs/%x-%j.out
#SBATCH --error=../logs/%x-%j.err

echo "=========================================="
echo "SDL vs Non-SDL (ALL) Graph Generation"
echo "Started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Running on node: $(hostname)"
echo "=========================================="

# Load Python and activate environment
module load python/3.11
source ~/openalex_env/bin/activate

# Navigate to project directory
cd /project/def-kmcel/hridansh/openalex_project

# Print Python info
echo ""
echo "Python environment:"
python --version
echo ""

# Run the analysis - ALL OUTPUT GOES TO LOG FILE
python SDL_comparison_graph.py

echo ""
echo "=========================================="
echo "Completed at: $(date)"
echo "=========================================="

# Show generated files
echo ""
echo "Generated files:"
ls -lh results/