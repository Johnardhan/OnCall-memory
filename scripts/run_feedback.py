from core.feedback import resolve_incident, future_triage

if __name__ == "__main__":
    resolve_incident(
        incident_id="INC-POST-001",
        service="checkout-service",
        alert="checkout-service: requests failing shortly after a release",
        root_cause="The release omitted a required environment variable in Helm values.",
        successful_fix="Rolled back the release, corrected the Helm value, and redeployed.",
        failed_fix="Scaling replicas only multiplied the failing instances.",
        engineer="Priya Nair",
    )
    future_triage("checkout-service: requests failing shortly after a release")
