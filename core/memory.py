import os
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

HINDSIGHT_URL = os.getenv("HINDSIGHT_URL")
HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY")
BANK_ID = "northwind-platform-sre"

if not HINDSIGHT_URL:
    raise RuntimeError("HINDSIGHT_URL is missing from .env")
if not HINDSIGHT_API_KEY:
    raise RuntimeError("HINDSIGHT_API_KEY is missing from .env")


def get_client() -> Hindsight:
    return Hindsight(
        base_url=HINDSIGHT_URL,
        api_key=HINDSIGHT_API_KEY,
        timeout=60.0,
    )


def ensure_bank(client: Hindsight) -> None:
    client.create_bank(
        bank_id=BANK_ID,
        name="Northwind Platform SRE Memory",
        mission=(
            "Remember software incidents, symptoms, root causes, fixes, failed fixes, "
            "services, and engineers involved in production incidents. Connect similar "
            "incidents across different services. Preserve outcomes so future incident "
            "triage can warn when a proposed fix failed previously and cite incident IDs."
        ),
    )


def incident_to_memory(incident: dict) -> str:
    incident_id = incident.get("id", "unknown")
    service = incident.get("service", "unknown")
    timestamp = incident.get("timestamp", "")
    alert = incident.get("alert", "")
    logs = incident.get("logs", "")
    narrative = incident.get("narrative", "")
    root_cause = incident.get("root_cause", "")
    fix = incident.get("fix", "")
    failed_fix = incident.get("failed_fix", "")
    engineer = incident.get("resolved_by", incident.get("engineer", ""))

    return f"""
Production incident {incident_id}
Service: {service}
Timestamp: {timestamp}
Alert: {alert}
Logs/symptoms: {logs}
Incident narrative: {narrative}
Root cause: {root_cause}
Successful fix: {fix}
Previously failed fix: {failed_fix}
Resolved by: {engineer}
""".strip()


def load_incidents(path: str = "data/incidents.json") -> int:
    import json

    with open(path, "r", encoding="utf-8") as f:
        incidents = json.load(f)

    with get_client() as client:
        ensure_bank(client)

        # Batch retain is supported by the current Hindsight Python SDK.
        items = [{"content": incident_to_memory(x)} for x in incidents]
        print(f"Retaining {len(items)} incidents into bank '{BANK_ID}'...")

        client.retain_batch(
            bank_id=BANK_ID,
            items=items,
            retain_async=False,
        )

        print("✅ All incidents retained.")

        query = (
            "A production service has rising latency and request failures. "
            "Have similar symptoms happened in another service, what was the root cause, "
            "and which fix actually worked?"
        )
        result = client.recall(
            bank_id=BANK_ID,
            query=query,
            types=["experience", "world", "observation"],
            max_tokens=4096,
            budget="mid",
        )

        print(f"\n✅ Recall returned {len(result.results)} memories")
        for i, memory in enumerate(result.results[:5], 1):
            print(f"\n--- Match {i} ---")
            print(memory.text[:1200])

    return len(incidents)


if __name__ == "__main__":
    load_incidents()
