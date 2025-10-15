"""
Tests for CohortDefinitionTool - comprehensive test coverage
"""
import pytest
import tempfile
import os
import json
from agent_v5.tools.cohort import CohortDefinitionTool


@pytest.mark.asyncio
async def test_cohort_tool_initialization():
    """Test 1: Tool initializes correctly"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        assert tool.name == "DefineCohort"
        assert tool.workspace_dir == tmpdir
        assert "DefineCohort" in tool.schema["name"]


@pytest.mark.asyncio
async def test_simple_cohort_definition():
    """Test 2: Simple cohort with basic inclusion criteria"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        result = await tool.execute({
            "cohort_name": "humira_prescribers",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "equals",
                    "value": "HUMIRA"
                }
            ],
            "output_format": "sql",
            "sql_dialect": "bigquery"
        })
        
        assert result["is_error"] is False
        assert "SELECT *" in result["content"]
        assert "NDC_DRUG_NM = 'HUMIRA'" in result["content"]
        assert "rx_claims" in result["content"]


@pytest.mark.asyncio
async def test_complex_cohort_with_exclusions():
    """Test 3: Complex cohort with inclusion and exclusion criteria"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        result = await tool.execute({
            "cohort_name": "high_volume_rinvoq_prescribers",
            "description": "High-volume RINVOQ prescribers excluding reversed transactions",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "equals",
                    "value": "RINVOQ"
                },
                {
                    "field": "DISPENSED_QUANTITY_VAL",
                    "operator": "greater_than",
                    "value": 30
                }
            ],
            "exclusion_criteria": [
                {
                    "field": "TRANSACTION_STATUS_NM",
                    "operator": "equals",
                    "value": "Reversed"
                }
            ],
            "output_format": "both"
        })
        
        assert result["is_error"] is False
        assert "NDC_DRUG_NM = 'RINVOQ'" in result["content"]
        assert "DISPENSED_QUANTITY_VAL > 30" in result["content"]
        assert "NOT (TRANSACTION_STATUS_NM = 'Reversed')" in result["content"]
        assert "HUMAN-READABLE DESCRIPTION:" in result["content"]


@pytest.mark.asyncio
async def test_temporal_constraints():
    """Test 4: Cohort with temporal constraints"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        result = await tool.execute({
            "cohort_name": "recent_prescribers",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "equals",
                    "value": "HUMIRA"
                }
            ],
            "temporal_constraints": {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "date_field": "SERVICE_DATE_DD"
            }
        })
        
        assert result["is_error"] is False
        assert "SERVICE_DATE_DD >= '2024-01-01'" in result["content"]
        assert "SERVICE_DATE_DD <= '2024-12-31'" in result["content"]


@pytest.mark.asyncio
async def test_aggregation_rules():
    """Test 5: Cohort with aggregation and having conditions"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        result = await tool.execute({
            "cohort_name": "high_volume_prescribers",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "in",
                    "value": ["HUMIRA", "RINVOQ", "SKYRIZI"]
                }
            ],
            "aggregation_rules": {
                "group_by": "PRESCRIBER_NPI_NBR",
                "having_conditions": [
                    {
                        "aggregate": "count",
                        "field": "*",
                        "operator": "greater_than",
                        "value": 50
                    },
                    {
                        "aggregate": "sum",
                        "field": "DISPENSED_QUANTITY_VAL",
                        "operator": "greater_or_equal",
                        "value": 1000
                    }
                ]
            },
            "sql_dialect": "bigquery"
        })
        
        assert result["is_error"] is False
        assert "GROUP BY PRESCRIBER_NPI_NBR" in result["content"]
        assert "COUNT(*) > 50" in result["content"]
        assert "SUM(DISPENSED_QUANTITY_VAL) >= 1000" in result["content"]


@pytest.mark.asyncio
async def test_or_logic_with_groups():
    """Test 6: Cohort with OR logic using groups"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        result = await tool.execute({
            "cohort_name": "immunology_prescribers",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "equals",
                    "value": "HUMIRA",
                    "group": "abbvie_drugs"
                },
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "equals",
                    "value": "RINVOQ",
                    "group": "abbvie_drugs"
                },
                {
                    "field": "PRESCRIBER_NPI_STATE_CD",
                    "operator": "in",
                    "value": ["CA", "TX", "NY"],
                    "case_sensitive": True  # Set to true for exact match
                }
            ]
        })
        
        assert result["is_error"] is False
        # Should have OR logic for grouped criteria
        assert "(NDC_DRUG_NM = 'HUMIRA' OR NDC_DRUG_NM = 'RINVOQ')" in result["content"]
        # And regular AND for ungrouped
        assert "PRESCRIBER_NPI_STATE_CD IN ('CA', 'TX', 'NY')" in result["content"]


@pytest.mark.asyncio
async def test_string_operations():
    """Test 7: Test various string operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        result = await tool.execute({
            "cohort_name": "test_string_ops",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "contains",
                    "value": "HUMIRA",
                    "case_sensitive": True  # Set for exact pattern match
                },
                {
                    "field": "NDC_PREFERRED_BRAND_NM",
                    "operator": "starts_with",
                    "value": "RIN",
                    "case_sensitive": True  # Set for exact pattern match
                },
                {
                    "field": "PRESCRIBER_NPI_STATE_CD",
                    "operator": "not_in",
                    "value": ["AK", "HI"],
                    "case_sensitive": True  # Set for exact pattern match
                }
            ]
        })
        
        assert result["is_error"] is False
        assert "LIKE '%HUMIRA%'" in result["content"]
        assert "LIKE 'RIN%'" in result["content"]
        assert "NOT IN ('AK', 'HI')" in result["content"]


@pytest.mark.asyncio
async def test_null_handling():
    """Test 8: Test NULL handling operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        result = await tool.execute({
            "cohort_name": "complete_records",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "PRESCRIBER_NPI_NBR",
                    "operator": "is_not_null"
                },
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "is_not_null"
                }
            ],
            "exclusion_criteria": [
                {
                    "field": "TRANSACTION_STATUS_NM",
                    "operator": "is_null"
                }
            ]
        })
        
        assert result["is_error"] is False
        assert "PRESCRIBER_NPI_NBR IS NOT NULL" in result["content"]
        assert "NDC_DRUG_NM IS NOT NULL" in result["content"]
        assert "NOT (TRANSACTION_STATUS_NM IS NULL)" in result["content"]


@pytest.mark.asyncio
async def test_between_operations():
    """Test 9: Test BETWEEN operations for numbers and dates"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        result = await tool.execute({
            "cohort_name": "moderate_volume",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "DISPENSED_QUANTITY_VAL",
                    "operator": "between",
                    "value": [10, 100]
                },
                {
                    "field": "SERVICE_DATE_DD",
                    "operator": "between_dates",
                    "value": ["2024-01-01", "2024-06-30"]
                }
            ]
        })
        
        assert result["is_error"] is False
        assert "DISPENSED_QUANTITY_VAL BETWEEN 10 AND 100" in result["content"]
        assert "SERVICE_DATE_DD BETWEEN '2024-01-01' AND '2024-06-30'" in result["content"]


@pytest.mark.asyncio
async def test_cohort_definition_saving():
    """Test 10: Test saving cohort definition to file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        result = await tool.execute({
            "cohort_name": "test_save",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "equals",
                    "value": "HUMIRA"
                }
            ],
            "save_definition": True
        })
        
        assert result["is_error"] is False
        assert "Cohort definition saved to:" in result["content"]
        
        # Check that files were created
        cohorts_dir = os.path.join(tmpdir, ".cohorts")
        assert os.path.exists(cohorts_dir)
        
        # Check latest file exists
        latest_file = os.path.join(cohorts_dir, "test_save_latest.json")
        assert os.path.exists(latest_file)
        
        # Verify JSON content
        with open(latest_file, 'r') as f:
            saved_def = json.load(f)
            assert saved_def["cohort_name"] == "test_save"
            assert saved_def["base_table"] == "rx_claims"


@pytest.mark.asyncio
async def test_validation_errors():
    """Test 11: Test validation error handling"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        # Missing field
        result = await tool.execute({
            "cohort_name": "invalid_cohort",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "operator": "equals",
                    "value": "HUMIRA"
                }
            ]
        })
        
        assert result["is_error"] is True
        assert "Missing 'field'" in result["content"]
        
        # Invalid operator
        result = await tool.execute({
            "cohort_name": "invalid_operator",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "invalid_op",
                    "value": "HUMIRA"
                }
            ]
        })
        
        assert result["is_error"] is True
        assert "Invalid operator" in result["content"]
        
        # Missing value for non-null operator
        result = await tool.execute({
            "cohort_name": "missing_value",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "equals"
                }
            ]
        })
        
        assert result["is_error"] is True
        assert "requires a 'value'" in result["content"]


@pytest.mark.asyncio
async def test_human_readable_description():
    """Test 12: Test human-readable description generation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        result = await tool.execute({
            "cohort_name": "comprehensive_cohort",
            "description": "Test cohort for validation",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "in",
                    "value": ["HUMIRA", "RINVOQ"]
                },
                {
                    "field": "DISPENSED_QUANTITY_VAL",
                    "operator": "greater_than",
                    "value": 30
                }
            ],
            "exclusion_criteria": [
                {
                    "field": "TRANSACTION_STATUS_NM",
                    "operator": "equals",
                    "value": "Reversed"
                }
            ],
            "temporal_constraints": {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "date_field": "SERVICE_DATE_DD"
            },
            "output_format": "both"
        })
        
        assert result["is_error"] is False
        
        # Check human-readable description
        content = result["content"]
        assert "COHORT: comprehensive_cohort" in content
        assert "PURPOSE: Test cohort for validation" in content
        assert "INCLUSION CRITERIA" in content
        assert "Ndc Drug Nm is one of: 'HUMIRA', 'RINVOQ'" in content
        assert "Dispensed Quantity Val greater than 30" in content
        assert "EXCLUSION CRITERIA" in content
        assert "Transaction Status Nm equals 'Reversed'" in content
        assert "TEMPORAL CONSTRAINTS" in content
        assert "Start date: 2024-01-01" in content
        assert "End date: 2024-12-31" in content


@pytest.mark.asyncio
async def test_different_sql_dialects():
    """Test 13: Test SQL generation for different dialects"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        # Test BigQuery dialect
        result_bq = await tool.execute({
            "cohort_name": "test_bq",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "matches_regex",
                    "value": "HUMIRA.*"
                }
            ],
            "sql_dialect": "bigquery",
            "output_format": "sql"
        })
        
        assert "REGEXP_CONTAINS" in result_bq["content"]
        
        # Test PostgreSQL dialect
        result_pg = await tool.execute({
            "cohort_name": "test_pg",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "matches_regex",
                    "value": "HUMIRA.*"
                }
            ],
            "sql_dialect": "postgresql",
            "output_format": "sql"
        })
        
        assert "~" in result_pg["content"]  # PostgreSQL regex operator
        
        # Test MySQL dialect
        result_mysql = await tool.execute({
            "cohort_name": "test_mysql",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "matches_regex",
                    "value": "HUMIRA.*"
                }
            ],
            "sql_dialect": "mysql",
            "output_format": "sql"
        })
        
        assert "REGEXP" in result_mysql["content"]


@pytest.mark.asyncio
async def test_case_sensitivity():
    """Test 14: Test case-sensitive vs case-insensitive operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        # Case-insensitive (default)
        result_insensitive = await tool.execute({
            "cohort_name": "case_insensitive",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "contains",
                    "value": "humira",
                    "case_sensitive": False
                }
            ],
            "sql_dialect": "postgresql",
            "output_format": "sql"
        })
        
        assert "LOWER" in result_insensitive["content"]
        
        # Case-sensitive
        result_sensitive = await tool.execute({
            "cohort_name": "case_sensitive",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "contains",
                    "value": "HUMIRA",
                    "case_sensitive": True
                }
            ],
            "sql_dialect": "postgresql",
            "output_format": "sql"
        })
        
        assert "LOWER" not in result_sensitive["content"]


@pytest.mark.asyncio
async def test_lookback_period():
    """Test 15: Test lookback period in temporal constraints"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = CohortDefinitionTool(tmpdir)
        
        result = await tool.execute({
            "cohort_name": "lookback_cohort",
            "base_table": "rx_claims",
            "inclusion_criteria": [
                {
                    "field": "NDC_DRUG_NM",
                    "operator": "equals",
                    "value": "HUMIRA"
                }
            ],
            "temporal_constraints": {
                "end_date": "2024-12-31",
                "lookback_days": 90,
                "date_field": "SERVICE_DATE_DD"
            },
            "sql_dialect": "bigquery",
            "output_format": "sql"
        })
        
        assert result["is_error"] is False
        assert "DATE_SUB" in result["content"]
        assert "INTERVAL 90 DAY" in result["content"]
