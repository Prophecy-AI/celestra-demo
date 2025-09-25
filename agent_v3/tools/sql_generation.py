"""
SQL generation tools for agent_v3
"""
import os
import re
import anthropic
from typing import Dict, Any
from .base import Tool, ToolResult
from .logger import tool_log


class TextToSQLRx(Tool):
    """Generate SQL for rx_claims table queries"""

    def __init__(self):
        super().__init__(
            name="text_to_sql_rx",
            description="Convert natural language request to SQL for rx_claims table"
        )
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt with data dictionary"""
        return """
You are a BigQuery Standard SQL generator for prescription (Rx) claims data analysis.

TASK: Convert natural language queries into executable BigQuery Standard SQL.

CRITICAL: Output ONLY the SQL query. No explanations, no descriptions, no text before or after the SQL.

TABLE: `unique-bonbon-472921-q8.Claims.rx_claims`

KEY COLUMNS:
- PRESCRIBER_NPI_NBR: STRING - National Provider Identifier of prescribing physician
- NDC: STRING - National Drug Code identifying the specific medication
- NDC_DRUG_NM: STRING - Drug name as identified by NDC
- NDC_GENERIC_NM: STRING - Generic name of the medication
- NDC_PREFERRED_BRAND_NM: STRING - Preferred brand name of the medication
- SERVICE_DATE_DD: DATE - Date when the pharmacy service was provided
- DATE_PRESCRIPTION_WRITTEN_DD: DATE - Date when prescription was written
- PRESCRIBER_NPI_STATE_CD: STRING - State code where prescriber is located
- PRESCRIBER_NPI_ZIP5_CD: STRING - Five-digit ZIP code of prescriber
- DISPENSED_QUANTITY_VAL: NUMERIC - Quantity of medication dispensed
- DAYS_SUPPLY_VAL: NUMERIC - Number of days the medication supply should last
- TOTAL_PAID_AMT: NUMERIC - Total amount paid for the prescription
- PAYER_PAYER_NM: STRING - Name of the insurance payer

COLUMN SELECTION PRIORITY:
- For prescriber queries: Include ONLY PRESCRIBER_NPI_NBR and requested metrics
- For drug queries: Include ONLY NDC, NDC_DRUG_NM and requested metrics
- NEVER use SELECT * - be extremely selective with columns

AGGREGATION RULES:
- For counting prescribers: COUNT(DISTINCT PRESCRIBER_NPI_NBR)
- For counting prescriptions: COUNT(*) or COUNT(DISTINCT DISPENSE_NBR)
- For total volume: SUM(DISPENSED_QUANTITY_VAL)

DATE FILTERING:
- Use DATE_PRESCRIPTION_WRITTEN_DD for when prescriptions were written
- Use SERVICE_DATE_DD for when prescriptions were filled
- Always use DATE format: '2024-01-01'

DRUG NAME MATCHING:
- Use UPPER() for case-insensitive drug name matching
- Check multiple name fields: NDC_DRUG_NM, NDC_GENERIC_NM, NDC_PREFERRED_BRAND_NM
- Example: WHERE UPPER(NDC_DRUG_NM) LIKE '%HUMIRA%' OR UPPER(NDC_PREFERRED_BRAND_NM) LIKE '%HUMIRA%'

OUTPUT FORMAT:
- Return clean, executable BigQuery Standard SQL
- Include appropriate GROUP BY when using aggregations
- Add ORDER BY for meaningful result ordering
- LIMIT results appropriately (typically 100-1000 rows)
"""

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Generate SQL from natural language request"""
        error = self.validate_parameters(parameters, ["request"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        request = parameters["request"]
        tool_log("text_to_sql_rx", f"Request: {request[:100]}...")

        try:
            # Call LLM to generate SQL
            tool_log("text_to_sql_rx", "Calling Claude for SQL generation")
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                temperature=0,
                system=self.system_prompt,
                messages=[{"role": "user", "content": request}]
            )

            # Extract SQL from response
            sql = response.content[0].text.strip()

            # Clean up SQL (remove markdown if present)
            sql = re.sub(r'^```sql\s*', '', sql)
            sql = re.sub(r'\s*```$', '', sql)
            sql = sql.strip()

            # Validate it looks like SQL
            if not sql.upper().startswith(('SELECT', 'WITH')):
                tool_log("text_to_sql_rx", "Invalid SQL - doesn't start with SELECT/WITH", "error")
                return ToolResult(
                    success=False,
                    data={},
                    error="Generated text does not appear to be valid SQL"
                )

            # Extract estimated scope from the SQL
            scope = self._extract_scope(sql, request)
            tool_log("text_to_sql_rx", f"SQL generated ({len(sql)} chars), scope: {scope}", "success")
            tool_log("text_to_sql_rx", f"SQL: {sql[:200]}...", "sql")

            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "explanation": f"Query to find {self._extract_intent(request)}",
                    "estimated_scope": scope
                }
            )

        except Exception as e:
            tool_log("text_to_sql_rx", f"Failed: {str(e)}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"SQL generation failed: {str(e)}"
            )

    def _extract_intent(self, request: str) -> str:
        """Extract the main intent from the request"""
        request_lower = request.lower()

        if "prescriber" in request_lower:
            if "count" in request_lower:
                return "prescriber counts"
            return "prescribers"
        elif "drug" in request_lower or "medication" in request_lower:
            return "drug/medication data"
        elif "prescription" in request_lower:
            return "prescription data"
        else:
            return "healthcare data"

    def _extract_scope(self, sql: str, request: str) -> str:
        """Extract the scope of the query"""
        sql_upper = sql.upper()

        # Look for drug names
        drug_match = re.search(r"LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        drug_name = drug_match.group(1) if drug_match else None

        # Look for state filters
        state_match = re.search(r"STATE_CD\s*=\s*'([^']+)'", sql, re.IGNORECASE)
        state = state_match.group(1) if state_match else None

        # Look for date ranges
        date_match = re.search(r"DATE[^><=]*([><=]+)\s*'(\d{4}-\d{2}-\d{2})'", sql, re.IGNORECASE)
        has_date_filter = date_match is not None

        # Build scope description
        scope_parts = []

        if drug_name:
            scope_parts.append(f"{drug_name}")

        if "PRESCRIBER" in sql_upper:
            scope_parts.append("prescribers")
        elif "PRESCRIPTION" in sql_upper or "RX" in sql_upper:
            scope_parts.append("prescriptions")

        if state:
            scope_parts.append(f"in {state}")

        if has_date_filter:
            scope_parts.append("with date filters")

        return " ".join(scope_parts) if scope_parts else "All relevant data"


class TextToSQLMed(Tool):
    """Generate SQL for med_claims table queries"""

    def __init__(self):
        super().__init__(
            name="text_to_sql_med",
            description="Convert natural language request to SQL for med_claims table"
        )
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt with data dictionary"""
        return """
You are a BigQuery Standard SQL generator for medical claims data analysis.

TASK: Convert natural language queries into executable BigQuery Standard SQL.

CRITICAL: Output ONLY the SQL query. No explanations, no descriptions, no text before or after the SQL.

TABLE: `unique-bonbon-472921-q8.Claims.medical_claims`

KEY COLUMNS:
- PRIMARY_HCP: STRING - Primary Healthcare Provider identifier
- PRIMARY_HCP_NAME: STRING - Full name of the primary healthcare provider
- PRIMARY_HCO: STRING - Primary Healthcare Organization identifier
- PRIMARY_HCO_NAME: STRING - Name of the primary healthcare organization
- condition_label: STRING - Label describing the primary medical condition treated
- PROCEDURE_CD: STRING - Medical procedure code (CPT, HCPCS)
- PROCEDURE_CODE_DESC: STRING - Description of the medical procedure
- STATEMENT_FROM_DD: DATE - Start date of billing period
- STATEMENT_TO_DD: DATE - End date of billing period
- RENDERING_PROVIDER_STATE: STRING - State where services were rendered
- RENDERING_PROVIDER_ZIP: STRING - ZIP code where services were rendered
- CLAIM_CHARGE_AMT: NUMERIC - Total charge amount for the claim
- distinct_patient_count: INTEGER - Count of unique patients
- total_claim_count: INTEGER - Total number of claims

COLUMN SELECTION PRIORITY:
- For provider/HCP queries: Include ONLY PRIMARY_HCP and requested metrics
- For organization/HCO queries: Include ONLY PRIMARY_HCO and requested metrics
- For condition queries: Include ONLY condition_label and requested metrics
- NEVER use SELECT * - be extremely selective with columns

AGGREGATION RULES:
- For counting providers: COUNT(DISTINCT PRIMARY_HCP)
- For counting organizations: COUNT(DISTINCT PRIMARY_HCO)
- For counting patients: SUM(distinct_patient_count) or COUNT(DISTINCT patient_identifier)
- For counting claims: SUM(total_claim_count) or COUNT(*)

CONDITION MATCHING:
- Use condition_label for diagnosis/condition searches
- Use UPPER() for case-insensitive matching
- Example: WHERE UPPER(condition_label) LIKE '%RHEUMATOID ARTHRITIS%'

DATE FILTERING:
- Use STATEMENT_FROM_DD for service start dates
- Use STATEMENT_TO_DD for service end dates
- Always use DATE format: '2024-01-01'

OUTPUT FORMAT:
- Return clean, executable BigQuery Standard SQL
- Include appropriate GROUP BY when using aggregations
- Add ORDER BY for meaningful result ordering
- LIMIT results appropriately (typically 100-1000 rows)
"""

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Generate SQL from natural language request"""
        error = self.validate_parameters(parameters, ["request"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        request = parameters["request"]
        tool_log("text_to_sql_rx", f"Request: {request[:100]}...")

        try:
            # Call LLM to generate SQL
            tool_log("text_to_sql_rx", "Calling Claude for SQL generation")
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                temperature=0,
                system=self.system_prompt,
                messages=[{"role": "user", "content": request}]
            )

            # Extract SQL from response
            sql = response.content[0].text.strip()

            # Clean up SQL (remove markdown if present)
            sql = re.sub(r'^```sql\s*', '', sql)
            sql = re.sub(r'\s*```$', '', sql)
            sql = sql.strip()

            # Validate it looks like SQL
            if not sql.upper().startswith(('SELECT', 'WITH')):
                tool_log("text_to_sql_rx", "Invalid SQL - doesn't start with SELECT/WITH", "error")
                return ToolResult(
                    success=False,
                    data={},
                    error="Generated text does not appear to be valid SQL"
                )

            # Extract estimated scope from the SQL
            scope = self._extract_scope(sql, request)
            tool_log("text_to_sql_rx", f"SQL generated ({len(sql)} chars), scope: {scope}", "success")
            tool_log("text_to_sql_rx", f"SQL: {sql[:200]}...", "sql")

            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "explanation": f"Query to find {self._extract_intent(request)}",
                    "estimated_scope": scope
                }
            )

        except Exception as e:
            tool_log("text_to_sql_rx", f"Failed: {str(e)}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"SQL generation failed: {str(e)}"
            )

    def _extract_intent(self, request: str) -> str:
        """Extract the main intent from the request"""
        request_lower = request.lower()

        if "provider" in request_lower or "hcp" in request_lower:
            if "count" in request_lower:
                return "provider counts"
            return "healthcare providers"
        elif "condition" in request_lower or "diagnosis" in request_lower:
            return "medical conditions"
        elif "procedure" in request_lower:
            return "medical procedures"
        elif "organization" in request_lower or "hco" in request_lower:
            return "healthcare organizations"
        else:
            return "medical claims data"

    def _extract_scope(self, sql: str, request: str) -> str:
        """Extract the scope of the query"""
        sql_upper = sql.upper()

        # Look for condition names
        condition_match = re.search(r"condition_label[^']*LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        condition = condition_match.group(1) if condition_match else None

        # Look for state filters
        state_match = re.search(r"STATE\s*=\s*'([^']+)'", sql, re.IGNORECASE)
        state = state_match.group(1) if state_match else None

        # Look for date ranges
        date_match = re.search(r"STATEMENT[^><=]*([><=]+)\s*'(\d{4}-\d{2}-\d{2})'", sql, re.IGNORECASE)
        has_date_filter = date_match is not None

        # Build scope description
        scope_parts = []

        if condition:
            scope_parts.append(f"{condition}")

        if "PRIMARY_HCP" in sql_upper:
            scope_parts.append("providers")
        elif "PRIMARY_HCO" in sql_upper:
            scope_parts.append("organizations")

        if state:
            scope_parts.append(f"in {state}")

        if has_date_filter:
            scope_parts.append("with date filters")

        return " ".join(scope_parts) if scope_parts else "All relevant data"


class TextToSQLProviderPayments(Tool):
    """Generate SQL for provider_payment table queries"""
    def __init__(self):
        super().__init__(
            name="text_to_sql_provider_payments",
            description="Convert natural language request to SQL for provider_payments table"
        )
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt with data dictionary"""
        return """
You are a BigQuery Standard SQL generator for Healthcare Providers Payments data analysis.

TASK: Convert natural language queries into executable BigQuery Standard SQL.

CRITICAL: Output ONLY the SQL query. No explanations, no descriptions, no text before or after the SQL.

TABLE: `unique-bonbon-472921-q8.HCP.provider_payments`

KEY COLUMNS:
- npi_number: STRING - National Provider Identifier
- associated_product: STRING - Associated product
- nature_of_payment: STRING - Nature of payment
- payer_company: STRING - Payer company
- product_type: STRING - Product type
- program_year: INTEGER - Program year
- record_id: STRING - Record ID
- total_payment_amount: FLOAT -Total payment amount

COLUMN SELECTION PRIORITY:
- For provider payment queries: Include ONLY npi_number and requested metrics
- NEVER use SELECT * - be extremely selective with columns

AGGREGATION RULES:
- For counting providers: COUNT(DISTINCT npi_number)
- For total payment amount: SUM(total_payment_amount)
- For total payment amount by product type: SUM(total_payment_amount) GROUP BY product_type
- For total payment amount by payer company: SUM(total_payment_amount) GROUP BY payer_company
- For total payment amount by program year: SUM(total_payment_amount) GROUP BY program_year
- For total payment amount by record id: SUM(total_payment_amount) GROUP BY record_id

ITEM MATCHING:
- Use UPPER() for case-insensitive item matching
- Check multiple name fields: associated_product, nature_of_payment, payer_company, product_type, program_year, record_id

OUTPUT FORMAT:
- Return clean, executable BigQuery Standard SQL
- Include appropriate GROUP BY when using aggregations
- Add ORDER BY for meaningful result ordering
- LIMIT results appropriately (typically 100-1000 rows)
"""

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Generate SQL from natural language request"""
        error = self.validate_parameters(parameters, ["request"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        request = parameters["request"]
        tool_log("text_to_sql_rx", f"Request: {request[:100]}...")

        try:
            # Call LLM to generate SQL
            tool_log("text_to_sql_rx", "Calling Claude for SQL generation")
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                temperature=0,
                system=self.system_prompt,
                messages=[{"role": "user", "content": request}]
            )

            # Extract SQL from response
            sql = response.content[0].text.strip()

            # Clean up SQL (remove markdown if present)
            sql = re.sub(r'^```sql\s*', '', sql)
            sql = re.sub(r'\s*```$', '', sql)
            sql = sql.strip()

            # Validate it looks like SQL
            if not sql.upper().startswith(('SELECT', 'WITH')):
                tool_log("text_to_sql_rx", "Invalid SQL - doesn't start with SELECT/WITH", "error")
                return ToolResult(
                    success=False,
                    data={},
                    error="Generated text does not appear to be valid SQL"
                )

            # Extract estimated scope from the SQL
            scope = self._extract_scope(sql, request)
            tool_log("text_to_sql_rx", f"SQL generated ({len(sql)} chars), scope: {scope}", "success")
            tool_log("text_to_sql_rx", f"SQL: {sql[:200]}...", "sql")

            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "explanation": f"Query to find {self._extract_intent(request)}",
                    "estimated_scope": scope
                }
            )

        except Exception as e:
            tool_log("text_to_sql_rx", f"Failed: {str(e)}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"SQL generation failed: {str(e)}"
            )

    def _extract_intent(self, request: str) -> str:
        """Extract the main intent from the request"""
        request_lower = request.lower()

        if "payment" in request_lower or "amount" in request_lower or "total" in request_lower:
            return "provider payment amounts"
        elif "payer" in request_lower or "company" in request_lower:
            return "payer companies"
        elif "product" in request_lower or "drug" in request_lower or "associated product" in request_lower:
            return "associated products"
        elif "nature" in request_lower and "payment" in request_lower:
            return "nature of payment"
        elif "program year" in request_lower or "year" in request_lower:
            return "program year"
        elif "record id" in request_lower or "id" in request_lower:
            return "payment record id"
        elif "provider" in request_lower or "npi" in request_lower or "doctor" in request_lower:
            return "provider payment data"
        else:
            return "healthcare provider payment data"

    def _extract_scope(self, sql: str, request: str) -> str:
        """Extract the scope of the query"""
        sql_upper = sql.upper()

        # Extract possible scope elements from the SQL for providers_bio

        # Look for specialty
        specialty_match = re.search(r"SPECIALTY\s*=\s*'([^']+)'", sql, re.IGNORECASE)
        specialty = specialty_match.group(1) if specialty_match else None

        # Look for certifications (array field, may use UNNEST or LIKE)
        cert_match = re.search(r"CERTIFICATIONS.*(?:LIKE|=)\s+'%?([^'%]+)%?'", sql, re.IGNORECASE)
        certification = cert_match.group(1) if cert_match else None

        # Look for education (array field)
        education_match = re.search(r"EDUCATION.*(?:LIKE|=)\s+'%?([^'%]+)%?'", sql, re.IGNORECASE)
        education = education_match.group(1) if education_match else None

        # Look for awards (array field)
        awards_match = re.search(r"AWARDS.*(?:LIKE|=)\s+'%?([^'%]+)%?'", sql, re.IGNORECASE)
        award = awards_match.group(1) if awards_match else None

        # Look for memberships (array field)
        membership_match = re.search(r"MEMBERSHIPS.*(?:LIKE|=)\s+'%?([^'%]+)%?'", sql, re.IGNORECASE)
        membership = membership_match.group(1) if membership_match else None

        # Look for conditions treated (array field)
        conditions_match = re.search(r"CONDITIONS_TREATED.*(?:LIKE|=)\s+'%?([^'%]+)%?'", sql, re.IGNORECASE)
        condition = conditions_match.group(1) if conditions_match else None

        # Look for title
        title_match = re.search(r"TITLE\s*=\s*'([^']+)'", sql, re.IGNORECASE)
        title = title_match.group(1) if title_match else None

        # Look for npi_number
        npi_match = re.search(r"NPI_NUMBER\s*=\s*'([^']+)'", sql, re.IGNORECASE)
        npi_number = npi_match.group(1) if npi_match else None

        # Look for state (sometimes in specialty or address, but not a direct column in providers_bio)
        # If state is referenced in the request, try to extract it
        state_match = re.search(r"STATE\s*=\s*'([^']+)'", sql, re.IGNORECASE)
        state = state_match.group(1) if state_match else None

        # Build scope description
        scope_parts = []

        if npi_number:
            scope_parts.append(f"npi_number: {npi_number}")
        if title:
            scope_parts.append(f"title: {title}")
        if specialty:
            scope_parts.append(f"specialty: {specialty}")
        if certification:
            scope_parts.append(f"certification: {certification}")
        if education:
            scope_parts.append(f"education: {education}")
        if award:
            scope_parts.append(f"award: {award}")
        if membership:
            scope_parts.append(f"membership: {membership}")
        if condition:
            scope_parts.append(f"condition treated: {condition}")
        if state:
            scope_parts.append(f"state: {state}")

        if not scope_parts:
            scope_parts.append("provider biographical data")

        return " ".join(scope_parts) if scope_parts else "All relevant data"


class TextToSQLProvidersBio(Tool):
    """Generate SQL for rx_claims table queries"""

    def __init__(self):
        super().__init__(
            name="text_to_sql_providers_bio",
            description="Convert natural language request to SQL for providers_bio table"
        )
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt with data dictionary"""
        return """
You are a BigQuery Standard SQL generator for Healthcare Providers Biographical data analysis.

TASK: Convert natural language queries into executable BigQuery Standard SQL.

CRITICAL: Output ONLY the SQL query. No explanations, no descriptions, no text before or after the SQL.

TABLE: `unique-bonbon-472921-q8.HCP.providers_bio`

KEY COLUMNS:
- npi_number: STRING - National Provider Identifier
- title: STRING - Professional title of the provider
- specialty: STRING - Medical specialty
- certifications: ARRAY<STRING> - Certifications held by the provider
- education: ARRAY<STRING> - Educational background of the provider
- awards: ARRAY<STRING> - Awards received by the provider
- memberships: ARRAY<STRING> - Professional memberships of the provider
- conditions_treated: ARRAY<STRING> - Conditions treated by the provider

COLUMN SELECTION PRIORITY:
- NEVER use SELECT * - be extremely selective with columns

AGGREGATION RULES:
- For counting providers: COUNT(DISTINCT npi_number)

ITEM MATCHING:
- Use UPPER() for case-insensitive item matching
- Check multiple name fields: certifications, education, awards, memberships, conditions_treated
- Example: WHERE EXISTS (
  SELECT 1
  FROM UNNEST(field) AS something
  WHERE UPPER(something) LIKE '%item%'
);

OUTPUT FORMAT:
- Return clean, executable BigQuery Standard SQL
- Include appropriate GROUP BY when using aggregations
- Add ORDER BY for meaningful result ordering
- LIMIT results appropriately (typically 100-1000 rows)
"""

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Generate SQL from natural language request"""
        error = self.validate_parameters(parameters, ["request"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        request = parameters["request"]
        tool_log("text_to_sql_rx", f"Request: {request[:100]}...")

        try:
            # Call LLM to generate SQL
            tool_log("text_to_sql_rx", "Calling Claude for SQL generation")
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                temperature=0,
                system=self.system_prompt,
                messages=[{"role": "user", "content": request}]
            )

            # Extract SQL from response
            sql = response.content[0].text.strip()

            # Clean up SQL (remove markdown if present)
            sql = re.sub(r'^```sql\s*', '', sql)
            sql = re.sub(r'\s*```$', '', sql)
            sql = sql.strip()

            # Validate it looks like SQL
            if not sql.upper().startswith(('SELECT', 'WITH')):
                tool_log("text_to_sql_rx", "Invalid SQL - doesn't start with SELECT/WITH", "error")
                return ToolResult(
                    success=False,
                    data={},
                    error="Generated text does not appear to be valid SQL"
                )

            # Extract estimated scope from the SQL
            scope = self._extract_scope(sql, request)
            tool_log("text_to_sql_rx", f"SQL generated ({len(sql)} chars), scope: {scope}", "success")
            tool_log("text_to_sql_rx", f"SQL: {sql[:200]}...", "sql")

            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "explanation": f"Query to find {self._extract_intent(request)}",
                    "estimated_scope": scope
                }
            )

        except Exception as e:
            tool_log("text_to_sql_rx", f"Failed: {str(e)}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"SQL generation failed: {str(e)}"
            )

    def _extract_intent(self, request: str) -> str:
        """Extract the main intent from the request"""
        request_lower = request.lower()

        if "specialty" in request_lower:
            return "provider specialties"
        elif "certification" in request_lower:
            return "provider certifications"
        elif "education" in request_lower or "school" in request_lower or "university" in request_lower:
            return "provider education"
        elif "award" in request_lower:
            return "provider awards"
        elif "membership" in request_lower:
            return "provider memberships"
        elif "condition" in request_lower and "treat" in request_lower:
            return "conditions treated by providers"
        elif "provider" in request_lower or "npi" in request_lower:
            return "provider biographical data"
        else:
            return "healthcare provider data"

    def _extract_scope(self, sql: str, request: str) -> str:
        """Extract the scope of the query"""
        sql_upper = sql.upper()

        # Look for specialty
        specialty_match = re.search(r"SPECIALTY\s*=\s*'([^']+)'", sql, re.IGNORECASE)
        specialty = specialty_match.group(1) if specialty_match else None

        # Look for certifications
        cert_match = re.search(r"CERTIFICATIONS\s+LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        certification = cert_match.group(1) if cert_match else None

        # Look for education
        education_match = re.search(r"EDUCATION\s+LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        education = education_match.group(1) if education_match else None

        # Look for awards
        awards_match = re.search(r"AWARDS\s+LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        award = awards_match.group(1) if awards_match else None

        # Look for memberships
        membership_match = re.search(r"MEMBERSHIPS\s+LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        membership = membership_match.group(1) if membership_match else None

        # Look for conditions treated
        conditions_match = re.search(r"CONDITIONS_TREATED\s+LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        condition = conditions_match.group(1) if conditions_match else None

        # Look for state
        state_match = re.search(r"STATE\s*=\s*'([^']+)'", sql, re.IGNORECASE)
        state = state_match.group(1) if state_match else None

        # Build scope description
        scope_parts = []

        if specialty:
            scope_parts.append(f"specialty: {specialty}")
        if certification:
            scope_parts.append(f"certification: {certification}")
        if education:
            scope_parts.append(f"education: {education}")
        if award:
            scope_parts.append(f"award: {award}")
        if membership:
            scope_parts.append(f"membership: {membership}")
        if condition:
            scope_parts.append(f"condition treated: {condition}")
        if state:
            scope_parts.append(f"state: {state}")

        if not scope_parts:
            scope_parts.append("provider biographical data")

        return " ".join(scope_parts) if scope_parts else "All relevant data"

