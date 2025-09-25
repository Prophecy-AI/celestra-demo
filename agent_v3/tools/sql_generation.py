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
        from datetime import datetime
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        return f"""
You are a BigQuery Standard SQL generator for prescription (Rx) claims data analysis.

TASK: Convert natural language queries into executable BigQuery Standard SQL.

CRITICAL: Output ONLY the SQL query. No explanations, no descriptions, no text before or after the SQL.

CURRENT DATE: Today is {current_date}. When users ask for "recent", "current", "this year", "last month", etc., use BigQuery date functions:
- CURRENT_DATE() for today's date
- DATE_SUB(CURRENT_DATE(), INTERVAL n DAY/MONTH/YEAR) for past periods
- Example: "recent prescriptions" → WHERE SERVICE_DATE_DD >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
- Example: "this year" → WHERE EXTRACT(YEAR FROM SERVICE_DATE_DD) = EXTRACT(YEAR FROM CURRENT_DATE())

TABLE: `unique-bonbon-472921-q8.Claims.rx_claims`

KEY COLUMNS:
- PRESCRIBER_NPI_NBR: STRING - National Provider Identifier of prescribing physician
- NDC: STRING - National Drug Code identifying the specific medication
- NDC_DRUG_NM: STRING - Drug name as identified by NDC
- NDC_GENERIC_NM: STRING - Generic name of the medication
- NDC_PREFERRED_BRAND_NM: STRING - Preferred brand name of the medication
- NDC_DESC: STRING - Detailed product description (high-cardinality text)
- NDC_DOSAGE_FORM_NM: STRING - Dosage form label (tablet, injectable, etc.)
- NDC_DRUG_FORM_NM: STRING - Drug formulation descriptor (varies widely)
- NDC_DRUG_BASE_NM: STRING - Base chemical name for the drug
- NDC_DRUG_CLASS_NM: STRING - Therapeutic class label
- NDC_DRUG_GROUP_NM: STRING - Drug group category
- NDC_DRUG_SUBCLASS_NM: STRING - Drug subclass category
- SERVICE_DATE_DD: DATE - Date when the pharmacy service was provided
- DATE_PRESCRIPTION_WRITTEN_DD: DATE - Date when prescription was written
- PRESCRIBER_NPI_STATE_CD: STRING - State code where prescriber is located
- PRESCRIBER_NPI_ZIP5_CD: STRING - Five-digit ZIP code of prescriber
- DISPENSED_QUANTITY_VAL: NUMERIC - Quantity of medication dispensed
- DAYS_SUPPLY_VAL: NUMERIC - Number of days the medication supply should last
- TOTAL_PAID_AMT: NUMERIC - Total amount paid for the prescription
- PAYER_PAYER_NM: STRING - Individual payer organization name (high-cardinality)
- PAYER_PLAN_CHANNEL_NM: STRING - Payer channel grouping (Commercial, Medicare, etc.)
- PAYER_PLAN_SUBCHANNEL_NM: STRING - Detailed payer subchannel category
- TRANSACTION_STATUS_NM: STRING - Claim transaction outcome (Dispensed, Reversed, etc.)
- FINAL_STATUS_CD: STRING - Adjudication status code from claims processing
- ADMIN_SERVICE_LINE: STRING - Administrative service line category
- ADMIN_SUBSERVICE_LINE: STRING - Administrative subservice detail
- CLINICAL_SERVICE_LINE: STRING - Clinical service line category
- CLINICAL_SUBSERVICE_LINE: STRING - Clinical subservice specialty detail
- PRESCRIBER_NPI_HCP_SEGMENT_DESC: STRING - Prescriber segment descriptor
- PHARMACY_NPI_STATE_CD: STRING - Pharmacy state code

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
- LIMIT results to 1,000,000 (1M) rows

## RX CLAIMS LOOKUP CONTEXT

- Curated categorical values:
  - NDC_GENERIC_NM: Upadacitinib, Baricitinib, Tofacitinib Citrate, Secukinumab, Secukinumab (300 Mg Dose), Ixekizumab, Abrocitinib, Tofacitinib Citrate Er, Risankizumab-Rzaa, Risankizumab-Rzaa(150 Mg Dose), Tildrakizumab-Asmn, Adalimumab, Tofacitinib, Guselkumab, Upadacitinib Er, Apremilast, Ustekinumab, Dupilumab
  - NDC_PREFERRED_BRAND_NM: Cosentyx, Tremfya, Xeljanz, Rinvoq, Taltz, Dupixent, Cibinqo, Stelara, Ilumya, Humira, Skyrizi, Olumiant, Otezla
  - NDC_IMPLIED_BRAND_NM: Xeljanz_Pfizer Inc., Otezla_Amgen, Inc., Taltz_Eli Lilly & Co., Cibinqo_Eli Lilly & Co., Dupixent_Sanofi, Skyrizi_Abbvie, Inc., Cibinqo_Pfizer Inc., Humira, Cosentyx_Novartis Ag, Otezla, Ilumya_Sun Pharmaceutical Industries Ltd., Taltz, Otezla_Metagenics, Inc., Otezla_Trimarc Labs, Rinvoq_Abbvie, Inc., Cosentyx, Humira_Abbvie, Inc., Dupixent_Alcon Ag, Rinvoq_Icu Medical, Inc., Stelara_Johnson & Johnson, Rinvoq_Baxter International, Inc., Otezla_Celgene Corporation, Ilumya_Perrigo Co. Plc, Tremfya_Johnson & Johnson, Olumiant_Gsms, Inc., Tremfya, Olumiant_Eli Lilly & Co., Rinvoq, Xeljanz_Shoreline Pharmaceuticals, Inc., Cosentyx_Nutramax Laboratories, Inc., Olumiant_Dr. Reddy's Laboratories Ltd.
  - NDC_DRUG_CLASS_NM: Anti-Tnf-Alpha - Monoclonal Antibodies, Antipsoriatics, Inflammatory Bowel Agents, Eczema Agents, Antirheumatic - Enzyme Inhibitors, Phosphodiesterase 4 (Pde4) Inhibitors
  - NDC_DRUG_GROUP_NM: Analgesics - Anti-Inflammatory, Dermatologicals, Gastrointestinal Agents - Misc.
  - NDC_DRUG_SUBCLASS_NM: Antirheumatic - Janus Kinase (Jak) Inhibitors, Anti-Tnf-Alpha - Monoclonal Antibodies, Atopic Dermatitis - Janus Kinase (Jak) Inhibitors, Atopic Dermatitis - Monoclonal Antibodies, Interleukin Antagonists, Antipsoriatics - Systemic, Phosphodiesterase 4 (Pde4) Inhibitors
  - PAYER_PLAN_SUBCHANNEL_NM: Medicare / FFS (Part B), Commercial / Health Insurance Marketplace, Dual Medicaid / Medicare / Unspecified, Commercial / Cash or Self-Pay, Other / Government / Federal Program, Medicaid / CHIP, Other / Government / Champus - TRICARE, Medicare / Advantage (Part C), Other / Liability / Workers' Compensation, Other / Liability / Auto Medical, Other / Government / Veterans Affairs, Commercial / Voucher, Commercial / Discount Card, Other / Other, Other / Government / State or Local Program, Medicaid / Managed, Medicare / Advantage (Part D), Medicaid / FFS, Other / Unknown, Medicaid / Unspecified, Commercial / Commercial, Commercial / Medicare / Supplemental (Part B), Medicare / Unspecified, Commercial / Dental
  - PAYER_PLAN_CHANNEL_NM: Medicare, Other, Medicaid, Commercial, Dual (Medicaid/Medicare)
  - TRANSACTION_STATUS_NM: Reversed, Reject, Dispensed
  - CLINICAL_SERVICE_LINE: Neurology, ENT, Signs and Symptoms, Ophthalmology, General Surgery, Unknown, Neonatology, Urology, Vascular Services, Obstetrics, Other Trauma, Orthopedics, Cardiac Services, Spine, Gynecology, Oncology/Hematology (Medical), General Medicine
"""

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Generate SQL from natural language request"""
        error = self.validate_parameters(parameters, ["request"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        request = parameters["request"]
        tool_log("text_to_sql_rx", f"Request: {request}...")

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
            tool_log("text_to_sql_rx", f"SQL: {sql}...", "sql")

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
        from datetime import datetime
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        return f"""
You are a BigQuery Standard SQL generator for medical claims data analysis.

TASK: Convert natural language queries into executable BigQuery Standard SQL.

CRITICAL: Output ONLY the SQL query. No explanations, no descriptions, no text before or after the SQL.

CURRENT DATE: Today is {current_date}. When users ask for "recent", "current", "this year", "last month", etc., use BigQuery date functions:
- CURRENT_DATE() for today's date
- DATE_SUB(CURRENT_DATE(), INTERVAL n DAY/MONTH/YEAR) for past periods
- Example: "recent claims" → WHERE STATEMENT_FROM_DD >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
- Example: "this year" → WHERE EXTRACT(YEAR FROM STATEMENT_FROM_DD) = EXTRACT(YEAR FROM CURRENT_DATE())

TABLE: `unique-bonbon-472921-q8.Claims.medical_claims`

KEY COLUMNS:
- PRIMARY_HCP: STRING - Primary Healthcare Provider identifier
- PRIMARY_HCP_NAME: STRING - Full name of the primary healthcare provider
- PRIMARY_HCO: STRING - Primary Healthcare Organization identifier
- PRIMARY_HCO_NAME: STRING - Name of the primary healthcare organization
- PRIMARY_HCO_SOURCE: STRING - Source system for organization record
- PRIMARY_HCO_PROVIDER_CLASSIFICATION: STRING - Organization type/classification
- PRIMARY_HCP_SEGMENT: STRING - Primary HCP segment categorization
- PRIMARY_HCP_SOURCE: STRING - Source system for provider record
- condition_label: STRING - Label describing the primary medical condition treated
- PROCEDURE_CD: STRING - Medical procedure code (CPT, HCPCS)
- PROCEDURE_CODE_DESC: STRING - Description of the medical procedure
- STATEMENT_FROM_DD: DATE - Start date of billing period
- STATEMENT_TO_DD: DATE - End date of billing period
- RENDERING_PROVIDER_STATE: STRING - State where services were rendered
- RENDERING_PROVIDER_ZIP: STRING - ZIP code where services were rendered
- RENDERING_PROVIDER_SEGMENT: STRING - Rendering provider segment categorization
- CLAIM_CHARGE_AMT: NUMERIC - Total charge amount for the claim
- distinct_patient_count: INTEGER - Count of unique patients
- total_claim_count: INTEGER - Total number of claims
- CLAIM_CATEGORY: STRING - Claim grouping/category label
- PAYER_1_NAME: STRING - Primary payer organization name (high-cardinality)
- PAYER_1_CHANNEL_NAME: STRING - Payer channel grouping (Commercial, Medicare, etc.)
- PAYER_1_SUBCHANNEL_NAME: STRING - Detailed payer subchannel category
- ENCOUNTER_CHANNEL_NM: STRING - Encounter channel category
- ENCOUNTER_SUBCHANNEL_NM: STRING - Encounter subchannel detail
- claim_year: INTEGER - Service year field

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
- LIMIT results to 1,000,000 (1M) rows

## MEDICAL CLAIMS LOOKUP CONTEXT

- Curated categorical values:
  - PAYER_1_SUBCHANNEL_NAME: Other / Government / Corrections, Other / Government / Champus - TRICARE, Other / Government / State or Local Program, Dual Medicaid / Medicare C-SNP, Dual Medicaid / Medicare / Unspecified, Medicaid / FFS, Medicare / FFS (Part B), Other / Unknown, Commercial / Cash or Self-Pay, Medicare / Advantage (Part C), Other / Liability / Auto Medical, Commercial / Voucher, Commercial / Health Insurance Marketplace, Commercial / Medicare / Supplemental (Part B), Medicaid / Unspecified, Medicare / Unspecified, Other / Government / Veterans Affairs, Medicaid / CHIP, Commercial / Discount Card, Medicare / FFS (Part A), Other / Other, Commercial / Behavioral, Dual Medicaid / PACE Program, Other / Government / Federal Program, Other / Liability / Workers' Compensation, Other / Liability / Life or Property, Medicare / Employer Group Waiver Plan, Commercial / Dental Marketplace, Commercial / Commercial, Commercial / Dental, Medicaid / Managed, Medicare / Advantage (Part D)
  - PAYER_1_CHANNEL_NAME: Medicaid, Dual (Medicaid/Medicare), Other, Commercial, Medicare
  - ENCOUNTER_CHANNEL_NM: Medicaid, Dual (Medicaid/Medicare), Other, Commercial, Medicare
  - condition_label: Chronic Rhinosinusitis with Nasal Polyps, Psoriasis, Eosinophilic Esophagitis, Hidradenitis Suppurativa, Asthma, Alopecia, Ankylosing Spondylitis, Uveitis, Ulcerative Colitis, Axial Spondyloarthritis, Rheumatoid Arthritis, Atopic Dermatitis, Crohn's Disease, Psoriatic Arthritis, Juvenile Idiopathic Arthritis
"""

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Generate SQL from natural language request"""
        error = self.validate_parameters(parameters, ["request"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        request = parameters["request"]
        tool_log("text_to_sql_rx", f"Request: {request}...")

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
            tool_log("text_to_sql_rx", f"SQL: {sql}...", "sql")

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