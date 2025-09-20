DATA_DICTIONARY_PROVIDERS = """
[
  {"name":"type_1_npi","type":"STRING","desc":"Unique identifier (Type 1 NPI) for an individual healthcare provider.","example":"1033439047"},
  {"name":"type_2_npi_names","type":"ARRAY<STRING>","desc":"Organization names (Type 2 NPIs) associated with the provider.","example":["OHIO STATE UNIVERSITY HOSPITAL","BRAIN AND SPINE INSTITUTE"]},
  {"name":"type_2_npis","type":"ARRAY<STRING>","desc":"Organization NPI numbers (Type 2 NPIs) affiliated with the provider.","example":["1477554814","1740231448"]},
  {"name":"first_name","type":"STRING","desc":"Provider's given name.","example":"ANDREW"},
  {"name":"middle_name","type":"STRING","desc":"Provider's middle name or initial.","example":"JAMES"},
  {"name":"last_name","type":"STRING","desc":"Provider's family name.","example":"GROSSBACH"},
  {"name":"gender","type":"STRING","desc":"Provider's gender.","example":"M"},
  {"name":"specialties","type":"ARRAY<STRING>","desc":"Clinical specialties of the provider.","example":["NEUROLOGICAL SURGERY"]},
  {"name":"conditions_tags","type":"ARRAY<STRING>","desc":"Tags of medical conditions associated with the provider.","example":["SPINAL STENOSIS"]},
  {"name":"conditions","type":"ARRAY<STRING>","desc":"Medical conditions treated by the provider.","example":["TENDINITIS"]},
  {"name":"cities","type":"ARRAY<STRING>","desc":"Cities where the provider practices.","example":["Columbus"]},
  {"name":"states","type":"ARRAY<STRING>","desc":"US states where the provider practices.","example":["OH"]},
  {"name":"counties","type":"ARRAY<STRING>","desc":"Counties where the provider practices.","example":["Franklin County"]},
  {"name":"city_states","type":"ARRAY<STRING>","desc":"Combined city and state labels.","example":["Columbus, OH"]},
  {"name":"hospital_names","type":"ARRAY<STRING>","desc":"Hospitals the provider is affiliated with.","example":["Ronald Reagan UCLA Medical Center"]},
  {"name":"system_names","type":"ARRAY<STRING>","desc":"Health systems the provider is affiliated with.","example":["UC San Diego Health"]},
  {"name":"affiliations","type":"ARRAY<STRING>","desc":"Other affiliations for the provider (departments, networks).","example":["Dept. of Neurology, OSU"]},
  {"name":"best_type_2_npi","type":"STRING","desc":"Primary or best-matching organization NPI.","example":"1477554814"},
  {"name":"best_hospital_name","type":"STRING","desc":"Primary or best-matching hospital name.","example":"Ronald Reagan UCLA Medical Center"},
  {"name":"best_system_name","type":"STRING","desc":"Primary or best-matching health system.","example":"UC San Diego Health"},
  {"name":"phone","type":"STRING","desc":"Provider's contact phone number.","example":"(614) 555-1234"},
  {"name":"email","type":"STRING","desc":"Provider's contact email address.","example":"andrew.smith@university.edu"},
  {"name":"linkedin","type":"STRING","desc":"Provider's LinkedIn profile URL.","example":"https://www.linkedin.com/in/andrew-smith-md"},
  {"name":"twitter","type":"STRING","desc":"Provider's Twitter/X handle or URL.","example":"@DrSmith"},
  {"name":"has_youtube","type":"BOOL","desc":"Whether the provider has a YouTube channel.","example":true},
  {"name":"has_podcast","type":"BOOL","desc":"Whether the provider has a podcast.","example":false},
  {"name":"has_linkedin","type":"BOOL","desc":"Whether the provider has a LinkedIn profile.","example":true},
  {"name":"has_twitter","type":"BOOL","desc":"Whether the provider has a Twitter/X profile.","example":true},
  {"name":"num_payments","type":"INT","desc":"Number of reported payments associated with the provider.","example":617},
  {"name":"num_clinical_trials","type":"INT","desc":"Number of clinical trials associated with the provider.","example":2},
  {"name":"num_publications","type":"INT","desc":"Number of publications associated with the provider.","example":52},
  {"name":"org_type","type":"STRING","desc":"Type of organization for the provider's main affiliation.","example":"General Acute Care Hospital"}
]
"""

PLAN_SCHEMA = """
{
  "type": "object",
  "required": ["filters", "projection", "limit"],
  "properties": {
    "filters": {
      "type": "object",
      "properties": {
        "specialty_any": { "type": ["array","null"], "items": { "type": "string" } },
        "state_any":     { "type": ["array","null"], "items": { "type": "string" } },
        "hospital_any":  { "type": ["array","null"], "items": { "type": "string" } },
        "system_any":    { "type": ["array","null"], "items": { "type": "string" } },
        "org_type_any":  { "type": ["array","null"], "items": { "type": "string" } },
        "publications_min": { "type": ["integer","null"] }
      },
      "additionalProperties": false
    },
    "projection": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["npi","name","states","specialties","hospital_names","system_names","num_publications","num_clinical_trials","num_payments","org_type"]
      }
    },
    "order_by": {
      "type": ["array","null"],
      "items": { "type": "string" }
    },
    "limit": { "type": "integer" },
    "plan_notes": { "type": ["string","null"] }
  },
  "additionalProperties": false
}
"""
SYSTEM_PROMPT = f"""
You are a planning agent. Convert the user's natural-language request into a single JSON Plan for filtering rows from a local Pandas DataFrame named `providers`.

Rules:
- Output ONLY a valid JSON object that conforms to the Plan Schema (below).
- Use ONLY the columns listed in the Data Dictionary (below). Do NOT invent columns.
- For list/array columns (specialties, states, hospital_names, system_names), match case-insensitively, any-of.
- "name" in projection = first_name + " " + last_name.
- If any field cannot be determined, set it to null (or empty list) and add a short reason in "plan_notes".
- If the user asks for "top N ..." you must:
  • Set "limit" = N
  • Set "order_by" with a sensible metric in DESC order:
      - Mentions publications → ["num_publications DESC","name ASC"]
      - Mentions trials → ["num_clinical_trials DESC","name ASC"]
      - Mentions payments → ["num_payments DESC","name ASC"]
      - If no metric is mentioned → ["name ASC"]
- Ignore claims/prescriptions entirely.

---------------------
DATA DICTIONARY
---------------------
{DATA_DICTIONARY_PROVIDERS}

---------------------
PLAN SCHEMA
---------------------
{PLAN_SCHEMA}
"""