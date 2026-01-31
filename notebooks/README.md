# Analysis Notebook

This notebook contains the complete voyage optimization analysis with accurate tipping point data.

## Running the Notebook

### Option 1: Using Jupyter (Recommended)

```bash
# Install dependencies (if not already installed)
pip install jupyter pandas numpy matplotlib seaborn scipy

# Start Jupyter
jupyter notebook

# Open analysis.ipynb in the browser
```

### Option 2: Using VS Code

1. Open the notebook file `analysis.ipynb` in VS Code
2. Select a Python kernel when prompted
3. Run all cells (Ctrl+Alt+Enter or "Run All" button)

### Option 3: Command Line Execution

```bash
# Install nbconvert if not installed
pip install nbconvert

# Execute the notebook
jupyter nbconvert --to notebook --execute analysis.ipynb --output analysis_executed.ipynb
```

## Dependencies

The notebook requires these Python packages:
- pandas
- numpy
- matplotlib
- seaborn
- scipy (for optimization)

Install all at once:
```bash
pip install pandas numpy matplotlib seaborn scipy jupyter
```

**Note:** Conda is NOT required. Standard pip installation works fine.

## Key Results in the Notebook

### Tipping Point Analysis (Cell 18)
- **Bunker Price Tipping Point**: +31% increase (profit: $5.8M → $4.0M)
- **Port Delay Tipping Point**: +46 days (profit: $5.8M → $2.3M)

### Detailed Sensitivity Tables (Cell 19)
- Complete bunker price sensitivity from -20% to +50%
- Complete port delay sensitivity from 0 to 60 days
- Switching advantage calculations

### Executive Summary (Cell 23)
- Optimal portfolio profit: **$5,803,558**
- 4 Cargill vessels assigned to market cargoes
- 3 committed cargoes covered by market vessel hires

### Requirements Verification (Cell 25)
- Confirms all datathon requirements completed
- Maps deliverables to requirement specification

## Troubleshooting

### Kernel Crashes
If the Jupyter kernel crashes, try:
1. Restart the kernel: Kernel → Restart Kernel
2. Run cells sequentially rather than all at once
3. Check that all dependencies are installed

### Import Errors
If you see `ModuleNotFoundError`, install the missing package:
```bash
pip install <package-name>
```

### Path Issues
The notebook automatically handles path setup. If you move it, ensure:
- The notebook is in the `notebooks/` directory
- The `src/` directory exists at `../src/` relative to the notebook
- The `data/` directory exists at `../data/` relative to the notebook
