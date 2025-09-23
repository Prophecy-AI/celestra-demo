# Celestra Demo

Healthcare data analysis system for querying medical and prescription claims.

## Requirements

- Python 3.8+
- Google Cloud BigQuery credentials
- Anthropic API key
- E2B API key (for sandbox mode)

## Setup

```bash
pip install -r requirements.txt
```

Set environment variables in `.env`:
```
ANTHROPIC_API_KEY=your_key
GOOGLE_CLOUD_PROJECT=your_project
MED_TABLE=unique-bonbon-472921-q8.Claims.medical_claims
RX_TABLE=unique-bonbon-472921-q8.Claims.rx_claims
```

## Usage

### Interactive Python Analysis
```bash
python main.py
```
Generates Python code using Claude Sonnet 4 and executes in E2B sandbox for data analysis.

### SQL Query Mode
```bash
python sql_test.py
```
Generates SQL queries using Claude Sonnet 4 and executes against BigQuery.

### Multi-Agent System
```bash
python agent/main_agent.py
```
Orchestrates specialized agents for complex healthcare queries.

## Architecture

- **main.py**: Python code generation with E2B sandbox execution
- **sql_test.py**: Direct BigQuery SQL generation and execution
- **agent/**: Multi-agent system
  - `main_agent.py`: Orchestrator for coordinating sub-agents
  - `rx_claims_agent.py`: Prescription claims specialist
  - `med_claims_agent.py`: Medical claims specialist
  - `agent.py`: Combined claims agent
- **prompts/**: System prompts for different agents
- **data/**: CSV files for local analysis

## Data Sources

- Medical claims: Diagnoses, procedures, patient visits
- Prescription claims: Drug prescriptions, dispensing data
- Provider data: Healthcare provider information with embeddings