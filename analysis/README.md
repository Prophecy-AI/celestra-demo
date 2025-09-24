# Pharmaceutical Analytics System

## Dynamic LLM-Based Analysis

This system uses OpenAI's most advanced model (GPT-4o) to dynamically generate analysis code for each query, providing unlimited analytical flexibility for pharmaceutical market research.

## Core Architecture

```
analysis/
├── main.py                      # Entry point for analytics queries
├── config.py                    # API keys and model configuration
├── dynamic_query_processor.py   # Orchestrates dynamic analysis
├── query_analyzer.py            # LLM generates custom analysis code
├── data_loader.py               # BigQuery data access (loads all available data)
├── visualization.py             # Dynamic visualization generation
├── ARCHITECTURE.md              # System architecture documentation
└── images/                      # Generated visualizations with heatmaps
```

## Key Features

### 1. Advanced LLM Code Generation
- Uses GPT-4o with optimized prompts for pharmaceutical expertise
- Generates FDA-standard statistical analysis code
- Creates publication-quality visualizations with heatmaps
- No pre-written methods - each query gets custom code

### 2. Comprehensive Statistical Analysis
- Appropriate tests selected dynamically (Chi-square, T-tests, ANOVA, etc.)
- Proper p-value calculations based on actual data
- Effect sizes and confidence intervals
- Multiple comparison corrections when needed

### 3. Professional Visualizations
- Multi-panel figures with subplots
- Automatic heatmap generation for correlations
- Statistical annotations (p-values, percentages)
- Pharmaceutical-grade color schemes

### 4. Technical Data as Proof
- Every insight backed by statistical evidence
- Detailed methodology documentation
- Data quality indicators
- Complete transparency in calculations

## Usage

```bash
cd analysis
python main.py
```

Then enter any pharmaceutical market research query.

## Example Queries

- "Compare market share between Tremfya and Rinvoq across specialties"
- "What drives prescriber choice for diabetes medications?"
- "Analyze patient adherence patterns for psoriasis drugs"
- "Show geographic variations in GLP-1 prescribing"
- "Identify high-value prescribers for Mounjaro"

## Data Sources

All available data is loaded (no artificial limits):
- `rx_claims`: Complete prescription claims dataset
- `medical_claims`: Medical claims data
- `providers_bio`: Healthcare provider information
- `provider_payments`: Provider payment data

## System Optimizations

- **Model**: GPT-4o for best code generation quality
- **Temperature**: 0.1 for consistent, accurate code
- **Max Tokens**: 3000 for comprehensive analysis
- **Data Loading**: Full datasets, no 50k limits
- **Visualizations**: Always includes heatmaps and multi-panel figures

## Output Structure

Each query returns:
1. **Insights**: Key findings in plain language
2. **Technical Data**: Complete statistical evidence as proof
3. **Visualizations**: Professional charts saved to images/
4. **Results**: Raw analysis output for transparency

The technical data section provides comprehensive proof for all claims made in the insights, including p-values, effect sizes, sample sizes, and methodology.