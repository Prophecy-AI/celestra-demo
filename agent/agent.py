import os
import sys
import time
from dotenv import load_dotenv
from openai import OpenAI
from google.cloud import bigquery
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.complete_prompt import build_complete_sql_prompt

load_dotenv()

class CompleteAgent:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.bq_client = bigquery.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "unique-bonbon-472921-q8"))

    def generate_sql(self, query: str) -> str:
        system_prompt = build_complete_sql_prompt(
            med_table=os.getenv("MED_TABLE", "unique-bonbon-472921-q8.Claims.medical_claims"),
            rx_table=os.getenv("RX_TABLE", "unique-bonbon-472921-q8.Claims.rx_claims"),
        )
        resp = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=0,
        )
        return resp.choices[0].message.content.strip()

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
        return job.result().to_dataframe()

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
        if hasattr(df, "to_csv"):
            df.to_csv(out_path, index=False)
        print(f"SQL saved: {sql_path}")
        print(f"CSV saved: {out_path}")
        if df is not None and not df.empty:
            print(df.head(10).to_string(index=False))

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


