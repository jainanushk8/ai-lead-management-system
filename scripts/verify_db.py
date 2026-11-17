"""Quick verification of SQLite database contents after Phase 2 tests."""
import sqlite3

conn = sqlite3.connect("leads.db")
conn.row_factory = sqlite3.Row

c = conn.cursor()

print("=== LEADS TABLE ===")
c.execute("SELECT * FROM leads")
leads = [dict(r) for r in c.fetchall()]
for l in leads:
    print(f"  id={l['id']} | {l['name']} | {l['email']} | status={l['status']}")

print(f"\n=== LEAD_ANALYSIS TABLE ===")
c.execute("SELECT * FROM lead_analysis")
analysis = [dict(r) for r in c.fetchall()]
for a in analysis:
    print(f"  lead_id={a['lead_id']} | temp={a['temperature']} | status={a['analysis_status']}")

print(f"\nTotal leads: {len(leads)}, Total analyses: {len(analysis)}")

# Verify table schema
print("\n=== TABLE SCHEMAS ===")
for table in ["leads", "lead_analysis", "agent_logs"]:
    c.execute(f"PRAGMA table_info({table})")
    cols = [row["name"] for row in c.fetchall()]
    print(f"  {table}: {cols}")

conn.close()
