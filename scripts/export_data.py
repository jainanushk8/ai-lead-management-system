"""
scripts/export_data.py

Exports all processed leads, AI classifications, and agent audit trails
from SQLite (leads.db) into structured JSON and CSV formats for Gamma AI report generation.
"""

import csv
import json
import sqlite3
import os

DB_PATH = "leads.db"
OUTPUT_DIR = "gamma"

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Query enriched lead report
    query = """
    SELECT 
        l.id AS lead_id,
        l.name,
        l.email,
        l.phone,
        l.company,
        l.message,
        l.status,
        l.created_at,
        COALESCE(a.temperature, 'unprocessed') AS temperature,
        COALESCE(a.requirements, '[]') AS requirements,
        COALESCE(a.analysis_status, 'none') AS analysis_status,
        COALESCE(a.ai_response, '') AS ai_response
    FROM leads l
    LEFT JOIN lead_analysis a ON l.id = a.lead_id
    ORDER BY l.id ASC;
    """

    rows = conn.execute(query).fetchall()
    leads_list = []
    for r in rows:
        d = dict(r)
        try:
            d["requirements"] = json.loads(d["requirements"])
        except Exception:
            pass
        leads_list.append(d)

    # 1. Export JSON
    json_path = os.path.join(OUTPUT_DIR, "report_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(leads_list, f, indent=2)
    print(f"Exported JSON to: {json_path} ({len(leads_list)} records)")

    # 2. Export CSV
    csv_path = os.path.join(OUTPUT_DIR, "report_data.csv")
    fields = [
        "lead_id", "name", "email", "phone", "company", "message",
        "status", "created_at", "temperature", "requirements", "analysis_status"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for lead in leads_list:
            row_copy = dict(lead)
            row_copy.pop("ai_response", None)
            if isinstance(row_copy["requirements"], list):
                row_copy["requirements"] = "; ".join(row_copy["requirements"])
            writer.writerow(row_copy)
    print(f"Exported CSV to: {csv_path}")

    # Summary Statistics for Gamma
    total = len(leads_list)
    hot = sum(1 for l in leads_list if l["temperature"].lower() == "hot")
    warm = sum(1 for l in leads_list if l["temperature"].lower() == "warm")
    cold = sum(1 for l in leads_list if l["temperature"].lower() == "cold")
    other = total - (hot + warm + cold)

    print("\n" + "=" * 50)
    print(" PIPELINE ANALYTICS SUMMARY")
    print("=" * 50)
    print(f" Total Leads Ingested : {total}")
    print(f" Hot Leads (High-Value): {hot}")
    print(f" Warm Leads (Exploring): {warm}")
    print(f" Cold / Spam Leads     : {cold}")
    print(f" Other / Unprocessed   : {other}")
    print("=" * 50)

    conn.close()

if __name__ == "__main__":
    main()
