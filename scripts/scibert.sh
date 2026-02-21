#!/bin/bash
#SBATCH --job-name=scibert_sdl
#SBATCH --account=def-kmcel
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G                
#SBATCH --gpus-per-node=1         # Request 1 GPU
#SBATCH --output=../logs/%x-%j.out
#SBATCH --error=../logs/%x-%j.err

echo "=========================================="
echo "Training SciBERT Classifier"
echo "Started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Running on node: $(hostname)"
echo "GPU Device: $CUDA_VISIBLE_DEVICES"
echo "=========================================="

# Load Python and standard scientific stack
module load python/3.11
module load scipy-stack
module load arrow/17.0.0

# Activate your environment
source ~/openalex_env/bin/activate

# Navigate to code directory
cd /project/def-kmcel/hridansh/openalex_project/py_code

# Debug Info
echo ""
echo "Python environment:"
python --version
echo "Checking for GPU availability in Python..."
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()} ({torch.cuda.get_device_name(0)})')"
echo ""

# Run the training script
time python scibert_2.py

echo ""
echo "=========================================="
echo "Completed at: $(date)"
echo "=========================================="