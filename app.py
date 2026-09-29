import streamlit as st
from core.triage import baseline_triage, memory_triage
from core.feedback import resolve_incident

st.set_page_config(
    page_title="OnCall Memory",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 OnCall Memory")
st.caption("The senior engineer who has seen this outage before.")

st.divider()

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("Demo Controls")
    memory_on = st.toggle("Hindsight Memory", value=True)
    show_inspector = st.checkbox("Show Memory Inspector", value=True)

    st.divider()
    st.markdown("**Bank**")
    st.code("northwind-platform-sre")

    st.markdown("**Demo flow**")
    st.markdown(
        "1. Alert arrives\n"
        "2. Agent triages\n"
        "3. Historical memory appears\n"
        "4. Incident is resolved\n"
        "5. Resolution becomes future memory"
    )

# -----------------------------
# Alert input
# -----------------------------
default_alert = "checkout-service: requests failing shortly after a release"

st.subheader("🚨 Production Alert")

alert = st.text_area(
    "Alert",
    value=default_alert,
    height=100,
    label_visibility="collapsed",
)

analyze = st.button(
    "🔎 Triage Incident",
    type="primary",
    use_container_width=True,
)

if analyze:
    st.session_state["last_alert"] = alert
    st.session_state["baseline"] = None
    st.session_state["memory_answer"] = None
    st.session_state["memories"] = None

    with st.spinner("Triaging incident..."):
        if memory_on:
            answer, memories = memory_triage(alert)
            st.session_state["memory_answer"] = answer
            st.session_state["memories"] = memories
        else:
            st.session_state["baseline"] = baseline_triage(alert)

# -----------------------------
# Results
# -----------------------------
if st.session_state.get("memory_answer") or st.session_state.get("baseline"):
    st.divider()
    st.subheader("🧭 Triage Result")

    if memory_on and st.session_state.get("memory_answer"):
        answer = st.session_state["memory_answer"]
        st.success("Hindsight Memory: ON")
        st.markdown(answer)

    elif st.session_state.get("baseline"):
        st.info("Hindsight Memory: OFF")
        st.markdown(st.session_state["baseline"])

    # -----------------------------
    # Memory Inspector
    # -----------------------------
    if (
        memory_on
        and show_inspector
        and st.session_state.get("memories")
    ):
        st.divider()
        st.subheader("🗃️ Memory Inspector")
        st.caption("Historical experiences retrieved before reasoning.")

        with st.expander("Show retrieved memories", expanded=True):
            st.text(st.session_state["memories"][:7000])

    # -----------------------------
    # Resolution / learning loop
    # -----------------------------
    st.divider()
    st.subheader("✅ Close Incident")

    col1, col2 = st.columns(2)

    with col1:
        incident_id = st.text_input(
            "Incident ID",
            value="INC-POST-002",
        )
        engineer = st.text_input(
            "Resolved by",
            value="Priya Nair",
        )

    with col2:
        failed_fix = st.text_input(
            "Failed mitigation",
            value="Scaled replicas, which multiplied the failing instances.",
        )
        successful_fix = st.text_input(
            "Successful fix",
            value="Rolled back the release and corrected the Helm environment variable.",
        )

    root_cause = st.text_input(
        "Root cause",
        value="The release omitted a required environment variable in Helm values.",
    )

    resolve = st.button(
        "🧠 Resolve + Remember",
        use_container_width=True,
    )

    if resolve:
        with st.spinner("Writing post-mortem to Hindsight..."):
            resolve_incident(
                incident_id=incident_id,
                service="checkout-service",
                alert=alert,
                root_cause=root_cause,
                successful_fix=successful_fix,
                failed_fix=failed_fix,
                engineer=engineer,
            )
        st.success(
            f"{incident_id} resolved. The post-mortem is now part of team memory."
        )
        st.caption(
            "Re-run the same alert to demonstrate the agent using the new experience."
        )

# -----------------------------
# Footer
# -----------------------------
st.divider()
st.caption(
    "Northwind Payments • Software Engineering / SRE • "
    "Persistent organizational memory powered by Hindsight"
)
