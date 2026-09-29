import os
from dotenv import load_dotenv
from groq import Groq
from hindsight_client import Hindsight

load_dotenv()

BANK_ID = "northwind-platform-sre"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def get_hindsight() -> Hindsight:
    return Hindsight(
        base_url=os.environ["HINDSIGHT_URL"],
        api_key=os.environ["HINDSIGHT_API_KEY"],
        timeout=90.0,
    )


def get_groq() -> Groq:
    return Groq(api_key=os.environ["GROQ_API_KEY"])


def baseline_triage(alert: str) -> str:
    """LLM triage with NO Hindsight memory."""
    client = get_groq()
    prompt = f"""
You are an on-call SRE for a payments company.

Analyze this alert using ONLY the alert text. Do not invent historical incidents,
previous fixes, engineers, or root-cause certainty.

Alert:
{alert}

Return:
1. Most likely causes
2. Immediate checks
3. Safest next action
4. Confidence and what evidence is missing

Keep the answer concise and operational.
"""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a careful senior SRE."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()


def memory_triage(alert: str) -> tuple[str, str]:
    """Hindsight recall + reflect: diagnosis grounded in retained incidents."""
    with get_hindsight() as client:
        recall = client.recall(
            bank_id=BANK_ID,
            query=(
                f"Find historical incidents similar to this alert: {alert}. "
                "Look across services for the same underlying failure family, "
                "successful fixes, failed fixes, and engineers who resolved them."
            ),
            max_tokens=5000,
            budget="mid",
            include_source_facts=True,
        )

        memories = "\n".join(
            f"- {item.text}" for item in recall.results[:8]
        )

        reflection = client.reflect(
            bank_id=BANK_ID,
            query=f"""
We are triaging a live production alert:

{alert}

Use the team's historical incident memory. Connect similar incidents even
when they affected different services.

Important rules:
- Cite incident IDs when evidence exists.
- Prefer fixes that previously worked.
- Warn explicitly if a proposed mitigation previously failed.
- Do not claim certainty when the evidence is weak.
- State the likely root cause, immediate checks, recommended action, and
  relevant prior engineer(s).
""",
            context=memories,
            budget="mid",
            max_tokens=700,
            include_facts=True,
        )

        answer = reflection.text.strip()
        return answer, memories


def demo(alert: str) -> None:
    print("\n" + "=" * 80)
    print("C4 — BASELINE VS HINDSIGHT MEMORY")
    print("=" * 80)
    print(f"\nALERT:\n{alert}\n")

    print("\n--- WITHOUT MEMORY ---")
    print(baseline_triage(alert))

    print("\n--- WITH HINDSIGHT MEMORY ---")
    answer, memories = memory_triage(alert)
    print(answer)

    print("\n--- MEMORY INSPECTOR ---")
    print(memories[:5000])


if __name__ == "__main__":
    demo(
        "checkout-service: requests failing shortly after a release"
    )
