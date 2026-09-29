import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

BANK_ID = "northwind-platform-sre"


def get_hindsight() -> Hindsight:
    return Hindsight(
        base_url=os.environ["HINDSIGHT_URL"],
        api_key=os.environ["HINDSIGHT_API_KEY"],
        timeout=90.0,
    )


def resolve_incident(
    incident_id: str,
    service: str,
    alert: str,
    root_cause: str,
    successful_fix: str,
    failed_fix: str,
    engineer: str,
) -> None:
    """
    Close the incident and write a durable post-mortem into Hindsight.

    This is the learning loop:
    incident -> resolution -> post-mortem -> retained memory -> future triage.
    """
    postmortem = f"""
POST-MORTEM
Incident: {incident_id}
Service: {service}
Resolved by: {engineer}
Recorded at: {datetime.now(timezone.utc).isoformat()}

Alert:
{alert}

Root cause:
{root_cause}

Successful fix:
{successful_fix}

Failed mitigation:
{failed_fix}

Lesson for future on-call engineers:
Prefer the successful fix above. Explicitly warn before repeating the failed mitigation.
Use the incident ID as historical evidence when a future incident has similar symptoms.
""".strip()

    with get_hindsight() as client:
        result = client.retain(
            bank_id=BANK_ID,
            content=postmortem,
            document_id=incident_id,
            context="Closed production incident post-mortem",
            metadata={
                "service": service,
                "source": "incident-resolution",
                "type": "postmortem",
            },
            tags=["postmortem", "resolved-incident", service],
            retain_async=False,
        )

        print(f"✅ Post-mortem retained: {incident_id}")
        print(f"   Items stored: {result.items_count}")


def future_triage(alert: str) -> None:
    with get_hindsight() as client:
        reflection = client.reflect(
            bank_id=BANK_ID,
            query=f"""
A new incident has arrived:

{alert}

Use the team's historical memory, including recently closed post-mortems.

Give:
1. likely root cause
2. immediate checks
3. recommended fix
4. a warning if a historically failed mitigation should be avoided
5. the most relevant incident ID and engineer when available

Cite evidence from memory. Do not claim certainty without evidence.
""",
            budget="mid",
            max_tokens=700,
            include_facts=True,
        )

        print("\n--- NEXT ALERT AFTER LEARNING ---")
        print(reflection.text.strip())


if __name__ == "__main__":
    # Deliberately records a newly resolved example so the next triage
    # demonstrates the closed learning loop without another Groq call.
    resolve_incident(
        incident_id="INC-POST-001",
        service="checkout-service",
        alert="checkout-service: requests failing shortly after a release",
        root_cause="The release omitted a required environment variable in Helm values.",
        successful_fix="Rolled back the release, corrected the Helm value, and redeployed.",
        failed_fix="Scaling replicas only multiplied the failing instances.",
        engineer="Priya Nair",
    )

    future_triage(
        "checkout-service: requests failing shortly after a release"
    )
