"""
scripts/batch_process_leads.py

Phase 6: Batch Test Lead Ingestion and AI Pipeline Execution.

Ingests 10 diverse, realistic leads across industries, temperature profiles,
and edge cases (Hot, Warm, Cold, Spam, Duplicates).
Runs each through the full pipeline:
  1. REST API Ingestion & Validation
  2. Duplicate Protection (409 Conflict check)
  3. Ollama Hermes 3 AI Classification (Temperature + Requirements)
  4. Hermes Agent Status Update & Audit Logging
"""

import httpx
import json
import time

BASE_URL = "http://127.0.0.1:8000"

SAMPLE_LEADS = [
    {
        "name": "David Sterling",
        "email": "dsterling@apexglobal.com",
        "phone": "+1 415 555 9012",
        "company": "Apex Global Capital",
        "message": "Urgent: We have an immediate budget of $80k approved for an AI-powered lead qualification engine. We need full integration with our Snowflake data warehouse and Salesforce CRM by Q1. Please have an enterprise solutions engineer contact me today.",
    },
    {
        "name": "Sarah Lin",
        "email": "slin@bioventurelabs.org",
        "phone": "+1 617 555 3344",
        "company": "BioVenture Labs",
        "message": "Looking for automated pipeline solutions to route inbound clinical trial inquiries to our medical liaison team. Need HIPAA compliance assurance and Slack alerts.",
    },
    {
        "name": "Vikram Malhotra",
        "email": "vikram@fintechedge.in",
        "phone": "+91 98200 11223",
        "company": "FinTech Edge India",
        "message": "Evaluating AI automation tools for our banking partner onboarding. Currently processing 2,000 inquiries monthly. Interested in testing your API capabilities next quarter.",
    },
    {
        "name": "Elena Rostova",
        "email": "elena.r@nordicretail.se",
        "phone": "+46 8 123 4567",
        "company": "Nordic Retail Group",
        "message": "Just browsing your website. Could you email me your standard pricing brochure and product deck when you get a chance?",
    },
    {
        "name": "Spam Bot 3000",
        "email": "deals@cryptomarketingblast.xyz",
        "phone": "+1 800 555 0199",
        "company": "Crypto Growth Hackers",
        "message": "Double your website traffic overnight! Guaranteed top Google rank, 50,000 backlink package for only $49. Visit our portal now or reply unsubscribe.",
    },
    {
        "name": "Marcus Vance",
        "email": "m.vance@solarislogistics.de",
        "phone": "+49 30 9876543",
        "company": "Solaris Fleet & Logistics",
        "message": "We need an intelligent dispatch and driver onboarding form automation. Looking to replace our manual Zendesk ticketing system within 60 days.",
    },
    {
        "name": "Pooja Reddy",
        "email": "pooja@zenithedtech.com",
        "phone": "+91 91765 43210",
        "company": "Zenith EdTech",
        "message": "Student admissions season is coming up. We need an automated lead scoring mechanism to filter parent inquiries based on course preference and scholarship requirements.",
    },
    {
        "name": "Tom Henderson",
        "email": "tom@hendersonlaw.co.uk",
        "phone": "+44 20 7946 0912",
        "company": "Henderson & Partners Legal",
        "message": "Does your system offer GDPR-compliant lead capture for corporate litigation inquiries? We require client data encryption at rest and in transit.",
    },
    {
        "name": "Spam SEO Offers",
        "email": "promo@fastrankings.biz",
        "phone": "+1 888 555 4321",
        "company": "FastRankings Agency",
        "message": "Exclusive promotion: Get your website reviewed by senior SEO specialists. Click here for free audit.",
    },
    {
        "name": "David Sterling (Duplicate Attempt)",
        "email": "dsterling@apexglobal.com",  # Duplicate of lead 1
        "phone": "+1 415 555 9012",
        "company": "Apex Global Capital",
        "message": "Following up on my previous request about the $80k lead qualification engine integration.",
    },
]

def main():
    client = httpx.Client(base_url=BASE_URL, timeout=120.0)
    print("=" * 70)
    print(" BATCH LEAD INGESTION & PIPELINE EXECUTION")
    print(f" Total Leads to Process: {len(SAMPLE_LEADS)}")
    print("=" * 70)

    results = []

    for idx, lead in enumerate(SAMPLE_LEADS, start=1):
        print(f"\n[{idx}/{len(SAMPLE_LEADS)}] Processing: {lead['name']} ({lead['company']})")
        
        # 1. Ingestion
        r = client.post("/api/leads", json=lead)
        if r.status_code == 409:
            print(f"  -> DUPLICATE DETECTED (409): {lead['email']}. Skipped AI inference to save tokens.")
            results.append({
                "lead_id": None,
                "name": lead["name"],
                "company": lead["company"],
                "email": lead["email"],
                "status": "duplicate_skipped",
                "temperature": "duplicate",
                "requirements": [],
            })
            continue
        elif r.status_code != 201:
            print(f"  -> INGESTION FAILED ({r.status_code}): {r.text}")
            continue

        lead_data = r.json()
        lead_id = lead_data["id"]
        print(f"  -> Lead Created (ID: {lead_id})")

        # 2. Ollama Classification
        print("  -> Calling Ollama Hermes 3 for classification...")
        t0 = time.time()
        r_ai = client.post(f"/api/leads/{lead_id}/analyze")
        dur = round(time.time() - t0, 1)
        if r_ai.status_code == 200:
            ai_data = r_ai.json()
            temp = ai_data.get("temperature", "warm")
            reqs = ai_data.get("requirements", [])
            print(f"  -> Analyzed in {dur}s | Temp: {temp.upper()} | Requirements: {len(reqs)}")
        else:
            print(f"  -> AI Analysis Failed ({r_ai.status_code})")
            temp = "unknown"
            reqs = []

        # 3. Hermes Agent Status Update
        agent_query = (
            f"Lead {lead_id} was analyzed as {temp}. "
            f"Update lead {lead_id} status to contacted with notes 'AI scored as {temp} with {len(reqs)} requirements'."
        )
        r_agent = client.post("/api/agent/query", json={"query": agent_query})
        if r_agent.status_code == 200:
            print(f"  -> Hermes Agent executed tool: {r_agent.json().get('tool_called')}")

        results.append({
            "lead_id": lead_id,
            "name": lead["name"],
            "company": lead["company"],
            "email": lead["email"],
            "status": "contacted",
            "temperature": temp,
            "requirements": reqs,
        })

    print("\n" + "=" * 70)
    print(" BATCH EXECUTION COMPLETED")
    print(f" Processed: {len(results)} leads")
    print("=" * 70)

if __name__ == "__main__":
    main()
