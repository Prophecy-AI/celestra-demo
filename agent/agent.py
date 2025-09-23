import os
import sys
import time
from dotenv import load_dotenv
# from openai import OpenAI
import anthropic
from google.cloud import bigquery
import polars as pl
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.complete_prompt import build_complete_sql_prompt

load_dotenv()

class CompleteAgent:
    def __init__(self):
        self.anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.bq_client = bigquery.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "unique-bonbon-472921-q8"))

    def generate_sql(self, query: str) -> str:
        system_prompt = build_complete_sql_prompt(
            med_table=os.getenv("MED_TABLE", "unique-bonbon-472921-q8.Claims.medical_claims"),
            rx_table=os.getenv("RX_TABLE", "unique-bonbon-472921-q8.Claims.rx_claims"),
        )
        resp = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {"role": "user", "content": query}
            ],
            temperature=0
        )
        return resp.content[0].text.strip()

    def execute_sql(self, sql: str):
        s = sql.strip()
        if s.startswith("```sql"):
            s = s[6:]
        if s.startswith("```"):
            s = s[3:]
        if s.endswith("```"):
            s = s[:-3]
        s = s.replace("'AND", "' AND").replace(")AND", ") AND").replace("%')AND", "%') AND")
        job = self.bq_client.query(s)
        # Convert BigQuery result to Arrow then to Polars
        arrow_table = job.result().to_arrow()
        return pl.from_arrow(arrow_table)

    def run(self, nl_query: str):
        sql = self.generate_sql(nl_query)
        print("SQL:\n" + sql)
        df = self.execute_sql(sql)
        ts = time.strftime("%Y%m%d_%H%M%S")
        os.makedirs("output", exist_ok=True)
        sql_path = f"output/complete_sql_{ts}.sql.txt"
        with open(sql_path, "w") as f:
            f.write(sql)
        out_path = f"output/complete_result_{ts}.csv"
        if df is not None:
            df.write_csv(out_path)
        print(f"SQL saved: {sql_path}")
        print(f"CSV saved: {out_path}")
        if df is not None and not df.is_empty():
            print(df.head(10))

def main():
    agent = CompleteAgent()
    import sys
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:]).strip()
        agent.run(q)
        return
    while True:
        try:
            q = input("Query: ").strip()
            if q.lower() in ["quit", "exit", "q"]:
                break
            if not q:
                continue
            agent.run(q)
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()


