"""
Cohort Definition Tool for reproducible healthcare research
"""
import os
import json
import re
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from .base import BaseTool


class CohortDefinitionTool(BaseTool):
    """Define and validate research cohorts with reproducible criteria"""
    
    # Supported operators for different data types
    OPERATORS = {
        "comparison": ["equals", "not_equals", "greater_than", "less_than", 
                      "greater_or_equal", "less_or_equal", "between", "not_between"],
        "string": ["contains", "not_contains", "starts_with", "ends_with", 
                  "matches_regex", "in", "not_in"],
        "null": ["is_null", "is_not_null"],
        "date": ["before", "after", "on_or_before", "on_or_after", "between_dates"]
    }
    
    # SQL operator mappings for different dialects
    SQL_OPERATORS = {
        "equals": "=",
        "not_equals": "!=",
        "greater_than": ">",
        "less_than": "<",
        "greater_or_equal": ">=",
        "less_or_equal": "<=",
        "is_null": "IS NULL",
        "is_not_null": "IS NOT NULL"
    }

    @property
    def name(self) -> str:
        return "DefineCohort"

    @property
    def schema(self) -> Dict:
        return {
            "name": "DefineCohort",
            "description": "Define research cohorts with explicit, reproducible criteria. Generates SQL queries and human-readable descriptions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "cohort_name": {
                        "type": "string",
                        "description": "Descriptive name for the cohort (e.g., 'high_volume_humira_prescribers')"
                    },
                    "description": {
                        "type": "string",
                        "description": "Human-readable description of the cohort's purpose"
                    },
                    "base_table": {
                        "type": "string",
                        "description": "Primary table for the cohort query (e.g., 'rx_claims', 'medical_claims')"
                    },
                    "inclusion_criteria": {
                        "type": "array",
                        "description": "List of inclusion criteria (all must be met)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string", "description": "Database field name"},
                                "operator": {"type": "string", "description": "Comparison operator"},
                                "value": {"description": "Value(s) to compare against"},
                                "case_sensitive": {"type": "boolean", "default": False},
                                "group": {"type": "string", "description": "Optional grouping for OR logic"}
                            },
                            "required": ["field", "operator"]
                        }
                    },
                    "exclusion_criteria": {
                        "type": "array",
                        "description": "List of exclusion criteria (any match excludes the record)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string"},
                                "operator": {"type": "string"},
                                "value": {},
                                "case_sensitive": {"type": "boolean", "default": False},
                                "group": {"type": "string"}
                            },
                            "required": ["field", "operator"]
                        }
                    },
                    "temporal_constraints": {
                        "type": "object",
                        "description": "Time-based constraints for the cohort",
                        "properties": {
                            "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                            "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                            "date_field": {"type": "string", "description": "Field to apply date filter to"},
                            "lookback_days": {"type": "integer", "description": "Days to look back from end_date"},
                            "rolling_window": {"type": "boolean", "description": "Use rolling window instead of fixed dates"}
                        }
                    },
                    "aggregation_rules": {
                        "type": "object",
                        "description": "Rules for aggregating records per entity",
                        "properties": {
                            "group_by": {"type": "string", "description": "Field to group by (e.g., 'PRESCRIBER_NPI_NBR')"},
                            "having_conditions": {
                                "type": "array",
                                "description": "Conditions on aggregated values",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "aggregate": {"type": "string", "enum": ["count", "sum", "avg", "min", "max"]},
                                        "field": {"type": "string"},
                                        "operator": {"type": "string"},
                                        "value": {"type": "number"}
                                    }
                                }
                            }
                        }
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["sql", "json", "both"],
                        "default": "both",
                        "description": "Output format for the cohort definition"
                    },
                    "sql_dialect": {
                        "type": "string",
                        "enum": ["bigquery", "postgresql", "mysql", "sqlite", "standard"],
                        "default": "bigquery",
                        "description": "SQL dialect for query generation"
                    },
                    "validate_fields": {
                        "type": "boolean",
                        "default": True,
                        "description": "Validate field names against known schemas"
                    },
                    "save_definition": {
                        "type": "boolean",
                        "default": True,
                        "description": "Save cohort definition to workspace for reproducibility"
                    }
                },
                "required": ["cohort_name", "base_table", "inclusion_criteria"]
            }
        }

    async def execute(self, input: Dict) -> Dict:
        """Execute cohort definition and generate outputs"""
        try:
            # Extract parameters
            cohort_name = input["cohort_name"]
            description = input.get("description", f"Cohort: {cohort_name}")
            base_table = input["base_table"]
            inclusion_criteria = input.get("inclusion_criteria", [])
            exclusion_criteria = input.get("exclusion_criteria", [])
            temporal_constraints = input.get("temporal_constraints", {})
            aggregation_rules = input.get("aggregation_rules", {})
            output_format = input.get("output_format", "both")
            sql_dialect = input.get("sql_dialect", "bigquery")
            validate_fields = input.get("validate_fields", True)
            save_definition = input.get("save_definition", True)
            
            # Validate criteria
            validation_errors = self._validate_criteria(
                inclusion_criteria, 
                exclusion_criteria,
                validate_fields,
                base_table
            )
            
            if validation_errors:
                return {
                    "content": f"Validation errors found:\n" + "\n".join(validation_errors),
                    "is_error": True
                }
            
            # Generate SQL query
            sql_query = self._generate_sql(
                base_table=base_table,
                inclusion_criteria=inclusion_criteria,
                exclusion_criteria=exclusion_criteria,
                temporal_constraints=temporal_constraints,
                aggregation_rules=aggregation_rules,
                dialect=sql_dialect
            )
            
            # Generate human-readable description
            human_description = self._generate_human_description(
                cohort_name=cohort_name,
                description=description,
                inclusion_criteria=inclusion_criteria,
                exclusion_criteria=exclusion_criteria,
                temporal_constraints=temporal_constraints,
                aggregation_rules=aggregation_rules
            )
            
            # Create cohort definition object
            cohort_definition = {
                "cohort_name": cohort_name,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "base_table": base_table,
                "inclusion_criteria": inclusion_criteria,
                "exclusion_criteria": exclusion_criteria,
                "temporal_constraints": temporal_constraints,
                "aggregation_rules": aggregation_rules,
                "sql_query": sql_query,
                "sql_dialect": sql_dialect,
                "human_description": human_description,
                "metadata": {
                    "version": "1.0",
                    "tool": "CohortDefinitionTool",
                    "validated": validate_fields
                }
            }
            
            # Save cohort definition if requested
            saved_path = None
            if save_definition:
                saved_path = self._save_cohort_definition(cohort_name, cohort_definition)
            
            # Format output based on requested format
            if output_format == "sql":
                output_content = f"SQL Query ({sql_dialect}):\n\n{sql_query}"
            elif output_format == "json":
                output_content = json.dumps(cohort_definition, indent=2)
            else:  # both
                output_content = f"""
Cohort Definition: {cohort_name}
{'=' * 60}

HUMAN-READABLE DESCRIPTION:
{human_description}

SQL QUERY ({sql_dialect}):
{sql_query}

COHORT STATISTICS:
- Inclusion criteria: {len(inclusion_criteria)} conditions
- Exclusion criteria: {len(exclusion_criteria)} conditions
- Temporal constraints: {'Yes' if temporal_constraints else 'No'}
- Aggregation rules: {'Yes' if aggregation_rules else 'No'}
"""
                if saved_path:
                    output_content += f"\nCohort definition saved to: {saved_path}"
            
            return {
                "content": output_content,
                "is_error": False,
                "cohort_definition": cohort_definition  # Include for downstream tools
            }
            
        except Exception as e:
            return {
                "content": f"Error creating cohort definition: {str(e)}",
                "is_error": True
            }
    
    def _validate_criteria(self, inclusion: List[Dict], exclusion: List[Dict], 
                          validate_fields: bool, base_table: str) -> List[str]:
        """Validate criteria for errors"""
        errors = []
        
        # Combine all criteria for validation
        all_criteria = inclusion + exclusion
        
        for i, criterion in enumerate(all_criteria):
            # Check required fields
            if "field" not in criterion:
                errors.append(f"Criterion {i+1}: Missing 'field'")
                continue
                
            if "operator" not in criterion:
                errors.append(f"Criterion {i+1}: Missing 'operator'")
                continue
            
            operator = criterion["operator"]
            field = criterion["field"]
            
            # Validate operator
            all_operators = sum(self.OPERATORS.values(), [])
            if operator not in all_operators:
                errors.append(f"Criterion {i+1}: Invalid operator '{operator}'. Valid operators: {all_operators}")
            
            # Check if value is required for this operator
            if operator not in ["is_null", "is_not_null"] and "value" not in criterion:
                errors.append(f"Criterion {i+1}: Operator '{operator}' requires a 'value'")
            
            # Validate value types for specific operators
            if "value" in criterion:
                value = criterion["value"]
                
                if operator in ["between", "not_between", "between_dates"]:
                    if not isinstance(value, list) or len(value) != 2:
                        errors.append(f"Criterion {i+1}: Operator '{operator}' requires a list of 2 values")
                
                if operator in ["in", "not_in"]:
                    if not isinstance(value, list):
                        errors.append(f"Criterion {i+1}: Operator '{operator}' requires a list of values")
            
            # Validate field names if requested (would need schema information)
            if validate_fields:
                # This would check against known schemas - simplified for now
                if base_table == "rx_claims":
                    known_fields = ["PRESCRIBER_NPI_NBR", "NDC_DRUG_NM", "SERVICE_DATE_DD", 
                                  "DISPENSED_QUANTITY_VAL", "PRESCRIBER_NPI_STATE_CD", 
                                  "PAYER_PLAN_CHANNEL_NM", "TRANSACTION_STATUS_NM"]
                    if field.upper() not in [f.upper() for f in known_fields] and not field.startswith("NDC_"):
                        errors.append(f"Warning: Field '{field}' not in known schema for {base_table}")
        
        return errors
    
    def _generate_sql(self, base_table: str, inclusion_criteria: List[Dict],
                     exclusion_criteria: List[Dict], temporal_constraints: Dict,
                     aggregation_rules: Dict, dialect: str) -> str:
        """Generate SQL query for the cohort"""
        
        # Handle table name based on dialect
        if dialect == "bigquery":
            # Assume full BigQuery table name if not provided
            if "." not in base_table:
                table_name = f"`unique-bonbon-472921-q8.Claims.{base_table}`"
            else:
                table_name = f"`{base_table}`"
        else:
            table_name = base_table
        
        # Build SELECT clause
        if aggregation_rules and "group_by" in aggregation_rules:
            select_clause = f"SELECT {aggregation_rules['group_by']}"
            # Add aggregation fields
            if "having_conditions" in aggregation_rules:
                for condition in aggregation_rules["having_conditions"]:
                    agg_func = condition["aggregate"].upper()
                    field = condition.get("field", "*")
                    select_clause += f",\n       {agg_func}({field}) as {agg_func.lower()}_{field.lower()}"
        else:
            select_clause = "SELECT *"
        
        # Build FROM clause
        from_clause = f"FROM {table_name}"
        
        # Build WHERE clause
        where_conditions = []
        
        # Add inclusion criteria
        inclusion_groups = self._group_criteria(inclusion_criteria)
        for group_name, criteria_list in inclusion_groups.items():
            if group_name == "default":
                # AND logic for ungrouped criteria
                for criterion in criteria_list:
                    condition = self._build_sql_condition(criterion, dialect)
                    if condition:
                        where_conditions.append(condition)
            else:
                # OR logic within groups
                group_conditions = []
                for criterion in criteria_list:
                    condition = self._build_sql_condition(criterion, dialect)
                    if condition:
                        group_conditions.append(condition)
                if group_conditions:
                    where_conditions.append(f"({' OR '.join(group_conditions)})")
        
        # Add temporal constraints
        if temporal_constraints:
            date_field = temporal_constraints.get("date_field", "SERVICE_DATE_DD")
            
            if "start_date" in temporal_constraints:
                where_conditions.append(f"{date_field} >= '{temporal_constraints['start_date']}'")
            
            if "end_date" in temporal_constraints:
                where_conditions.append(f"{date_field} <= '{temporal_constraints['end_date']}'")
            
            if "lookback_days" in temporal_constraints and "end_date" in temporal_constraints:
                if dialect == "bigquery":
                    where_conditions.append(
                        f"{date_field} >= DATE_SUB('{temporal_constraints['end_date']}', "
                        f"INTERVAL {temporal_constraints['lookback_days']} DAY)"
                    )
                else:
                    where_conditions.append(
                        f"{date_field} >= '{temporal_constraints['end_date']}'::date - "
                        f"INTERVAL '{temporal_constraints['lookback_days']} days'"
                    )
        
        # Add exclusion criteria (with NOT)
        exclusion_groups = self._group_criteria(exclusion_criteria)
        exclusion_conditions = []
        
        for group_name, criteria_list in exclusion_groups.items():
            if group_name == "default":
                for criterion in criteria_list:
                    condition = self._build_sql_condition(criterion, dialect)
                    if condition:
                        exclusion_conditions.append(condition)
            else:
                group_conditions = []
                for criterion in criteria_list:
                    condition = self._build_sql_condition(criterion, dialect)
                    if condition:
                        group_conditions.append(condition)
                if group_conditions:
                    exclusion_conditions.append(f"({' OR '.join(group_conditions)})")
        
        if exclusion_conditions:
            where_conditions.append(f"NOT ({' OR '.join(exclusion_conditions)})")
        
        # Build WHERE clause
        where_clause = ""
        if where_conditions:
            where_clause = f"WHERE {' AND '.join(where_conditions)}"
        
        # Build GROUP BY clause
        group_by_clause = ""
        if aggregation_rules and "group_by" in aggregation_rules:
            group_by_clause = f"GROUP BY {aggregation_rules['group_by']}"
        
        # Build HAVING clause
        having_clause = ""
        if aggregation_rules and "having_conditions" in aggregation_rules:
            having_conditions = []
            for condition in aggregation_rules["having_conditions"]:
                agg_func = condition["aggregate"].upper()
                field = condition.get("field", "*")
                operator = self.SQL_OPERATORS.get(condition["operator"], condition["operator"])
                value = condition["value"]
                having_conditions.append(f"{agg_func}({field}) {operator} {value}")
            
            if having_conditions:
                having_clause = f"HAVING {' AND '.join(having_conditions)}"
        
        # Combine all clauses
        sql_parts = [select_clause, from_clause]
        if where_clause:
            sql_parts.append(where_clause)
        if group_by_clause:
            sql_parts.append(group_by_clause)
        if having_clause:
            sql_parts.append(having_clause)
        
        sql_query = "\n".join(sql_parts)
        
        return sql_query
    
    def _build_sql_condition(self, criterion: Dict, dialect: str) -> str:
        """Build SQL condition from a criterion"""
        field = criterion["field"]
        operator = criterion["operator"]
        value = criterion.get("value")
        case_sensitive = criterion.get("case_sensitive", False)
        
        # Handle NULL checks
        if operator == "is_null":
            return f"{field} IS NULL"
        elif operator == "is_not_null":
            return f"{field} IS NOT NULL"
        
        # Handle different operators
        if operator in self.SQL_OPERATORS:
            # Simple comparison operators
            if isinstance(value, str):
                if not case_sensitive and dialect in ["postgresql", "mysql"]:
                    return f"LOWER({field}) {self.SQL_OPERATORS[operator]} LOWER('{value}')"
                else:
                    return f"{field} {self.SQL_OPERATORS[operator]} '{value}'"
            else:
                return f"{field} {self.SQL_OPERATORS[operator]} {value}"
        
        # String operations
        elif operator == "contains":
            if not case_sensitive:
                if dialect == "bigquery":
                    return f"LOWER({field}) LIKE LOWER('%{value}%')"
                else:
                    return f"LOWER({field}) LIKE LOWER('%{value}%')"
            else:
                return f"{field} LIKE '%{value}%'"
        
        elif operator == "not_contains":
            if not case_sensitive:
                return f"LOWER({field}) NOT LIKE LOWER('%{value}%')"
            else:
                return f"{field} NOT LIKE '%{value}%'"
        
        elif operator == "starts_with":
            if not case_sensitive:
                return f"LOWER({field}) LIKE LOWER('{value}%')"
            else:
                return f"{field} LIKE '{value}%'"
        
        elif operator == "ends_with":
            if not case_sensitive:
                return f"LOWER({field}) LIKE LOWER('%{value}')"
            else:
                return f"{field} LIKE '%{value}'"
        
        elif operator == "in":
            if isinstance(value, list):
                values_str = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in value])
                if not case_sensitive:
                    return f"LOWER({field}) IN ({values_str.lower()})"
                else:
                    return f"{field} IN ({values_str})"
        
        elif operator == "not_in":
            if isinstance(value, list):
                values_str = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in value])
                if not case_sensitive:
                    return f"LOWER({field}) NOT IN ({values_str.lower()})"
                else:
                    return f"{field} NOT IN ({values_str})"
        
        elif operator == "between":
            if isinstance(value, list) and len(value) == 2:
                return f"{field} BETWEEN {value[0]} AND {value[1]}"
        
        elif operator == "not_between":
            if isinstance(value, list) and len(value) == 2:
                return f"{field} NOT BETWEEN {value[0]} AND {value[1]}"
        
        elif operator == "between_dates":
            if isinstance(value, list) and len(value) == 2:
                return f"{field} BETWEEN '{value[0]}' AND '{value[1]}'"
        
        elif operator == "matches_regex":
            if dialect == "bigquery":
                return f"REGEXP_CONTAINS({field}, r'{value}')"
            elif dialect == "postgresql":
                return f"{field} ~ '{value}'"
            elif dialect == "mysql":
                return f"{field} REGEXP '{value}'"
            else:
                # Fallback to LIKE for unsupported dialects
                return f"{field} LIKE '{value}'"
        
        # Date operations
        elif operator == "before":
            return f"{field} < '{value}'"
        
        elif operator == "after":
            return f"{field} > '{value}'"
        
        elif operator == "on_or_before":
            return f"{field} <= '{value}'"
        
        elif operator == "on_or_after":
            return f"{field} >= '{value}'"
        
        return ""
    
    def _group_criteria(self, criteria: List[Dict]) -> Dict[str, List[Dict]]:
        """Group criteria by their 'group' field for OR logic"""
        groups = {}
        
        for criterion in criteria:
            group_name = criterion.get("group", "default")
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(criterion)
        
        return groups
    
    def _generate_human_description(self, cohort_name: str, description: str,
                                   inclusion_criteria: List[Dict],
                                   exclusion_criteria: List[Dict],
                                   temporal_constraints: Dict,
                                   aggregation_rules: Dict) -> str:
        """Generate human-readable description of the cohort"""
        
        lines = []
        lines.append(f"COHORT: {cohort_name}")
        lines.append(f"PURPOSE: {description}")
        lines.append("")
        
        # Inclusion criteria
        if inclusion_criteria:
            lines.append("INCLUSION CRITERIA (all must be met):")
            inclusion_groups = self._group_criteria(inclusion_criteria)
            
            for group_name, criteria_list in inclusion_groups.items():
                if group_name != "default":
                    lines.append(f"  At least one of the following (Group: {group_name}):")
                    prefix = "    - "
                else:
                    prefix = "  - "
                
                for criterion in criteria_list:
                    desc = self._describe_criterion(criterion)
                    lines.append(f"{prefix}{desc}")
        
        # Exclusion criteria
        if exclusion_criteria:
            lines.append("")
            lines.append("EXCLUSION CRITERIA (any match excludes):")
            exclusion_groups = self._group_criteria(exclusion_criteria)
            
            for group_name, criteria_list in exclusion_groups.items():
                if group_name != "default":
                    lines.append(f"  Any of the following (Group: {group_name}):")
                    prefix = "    - "
                else:
                    prefix = "  - "
                
                for criterion in criteria_list:
                    desc = self._describe_criterion(criterion)
                    lines.append(f"{prefix}{desc}")
        
        # Temporal constraints
        if temporal_constraints:
            lines.append("")
            lines.append("TEMPORAL CONSTRAINTS:")
            
            if "start_date" in temporal_constraints:
                lines.append(f"  - Start date: {temporal_constraints['start_date']}")
            
            if "end_date" in temporal_constraints:
                lines.append(f"  - End date: {temporal_constraints['end_date']}")
            
            if "lookback_days" in temporal_constraints:
                lines.append(f"  - Lookback period: {temporal_constraints['lookback_days']} days")
            
            if "date_field" in temporal_constraints:
                lines.append(f"  - Date field: {temporal_constraints['date_field']}")
        
        # Aggregation rules
        if aggregation_rules:
            lines.append("")
            lines.append("AGGREGATION RULES:")
            
            if "group_by" in aggregation_rules:
                lines.append(f"  - Group by: {aggregation_rules['group_by']}")
            
            if "having_conditions" in aggregation_rules:
                lines.append("  - Having conditions:")
                for condition in aggregation_rules["having_conditions"]:
                    agg = condition["aggregate"]
                    field = condition.get("field", "records")
                    op = self._describe_operator(condition["operator"])
                    val = condition["value"]
                    lines.append(f"    - {agg.upper()} of {field} {op} {val}")
        
        return "\n".join(lines)
    
    def _describe_criterion(self, criterion: Dict) -> str:
        """Generate human-readable description of a single criterion"""
        field = criterion["field"]
        operator = criterion["operator"]
        value = criterion.get("value", "")
        
        # Make field names more readable
        field_readable = field.replace("_", " ").title()
        
        # Describe based on operator
        if operator == "equals":
            return f"{field_readable} equals '{value}'"
        elif operator == "not_equals":
            return f"{field_readable} not equals '{value}'"
        elif operator == "greater_than":
            return f"{field_readable} greater than {value}"
        elif operator == "less_than":
            return f"{field_readable} less than {value}"
        elif operator == "greater_or_equal":
            return f"{field_readable} greater than or equal to {value}"
        elif operator == "less_or_equal":
            return f"{field_readable} less than or equal to {value}"
        elif operator == "contains":
            return f"{field_readable} contains '{value}'"
        elif operator == "not_contains":
            return f"{field_readable} does not contain '{value}'"
        elif operator == "starts_with":
            return f"{field_readable} starts with '{value}'"
        elif operator == "ends_with":
            return f"{field_readable} ends with '{value}'"
        elif operator == "in":
            values_str = ", ".join([f"'{v}'" for v in value])
            return f"{field_readable} is one of: {values_str}"
        elif operator == "not_in":
            values_str = ", ".join([f"'{v}'" for v in value])
            return f"{field_readable} is not one of: {values_str}"
        elif operator == "between":
            return f"{field_readable} between {value[0]} and {value[1]}"
        elif operator == "not_between":
            return f"{field_readable} not between {value[0]} and {value[1]}"
        elif operator == "is_null":
            return f"{field_readable} is missing/null"
        elif operator == "is_not_null":
            return f"{field_readable} is not missing/null"
        elif operator == "matches_regex":
            return f"{field_readable} matches pattern '{value}'"
        elif operator == "before":
            return f"{field_readable} before {value}"
        elif operator == "after":
            return f"{field_readable} after {value}"
        elif operator == "on_or_before":
            return f"{field_readable} on or before {value}"
        elif operator == "on_or_after":
            return f"{field_readable} on or after {value}"
        elif operator == "between_dates":
            return f"{field_readable} between {value[0]} and {value[1]}"
        else:
            return f"{field_readable} {operator} {value}"
    
    def _describe_operator(self, operator: str) -> str:
        """Convert operator to human-readable form"""
        mappings = {
            "equals": "equals",
            "not_equals": "not equals",
            "greater_than": "is greater than",
            "less_than": "is less than",
            "greater_or_equal": "is at least",
            "less_or_equal": "is at most"
        }
        return mappings.get(operator, operator)
    
    def _save_cohort_definition(self, cohort_name: str, definition: Dict) -> str:
        """Save cohort definition to workspace"""
        # Create cohorts directory if it doesn't exist
        cohorts_dir = os.path.join(self.workspace_dir, ".cohorts")
        os.makedirs(cohorts_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\s-]', '', cohort_name).strip().replace(' ', '_')
        filename = f"{safe_name}_{timestamp}.json"
        filepath = os.path.join(cohorts_dir, filename)
        
        # Save definition
        with open(filepath, 'w') as f:
            json.dump(definition, f, indent=2, default=str)
        
        # Also save as "latest" for easy access
        latest_path = os.path.join(cohorts_dir, f"{safe_name}_latest.json")
        with open(latest_path, 'w') as f:
            json.dump(definition, f, indent=2, default=str)
        
        return filepath

