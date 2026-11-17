"""
scripts/test_ollama_service.py

Simple script to verify the Ollama classification service works.
"""
import asyncio
import json
from app.services.ollama_service import classify_lead

async def main():
    sample_message = "I am looking for a CRM platform with AI lead scoring and integration with Outlook."
    result = await classify_lead(lead_id=1, message=sample_message)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
