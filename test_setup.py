import os
from dotenv import load_dotenv
from hindsight_client import Hindsight
from groq import Groq

# Load the keys from .env
load_dotenv()

# -----------------------------
# HINDSIGHT TEST
# -----------------------------
print("Testing Hindsight...")

h = Hindsight(
    base_url=os.getenv("HINDSIGHT_URL"),
    api_key=os.getenv("HINDSIGHT_API_KEY")
)

BANK = "oncall-test"

try:
    h.create_bank(
        bank_id=BANK,
        name="OnCall Test",
        mission="I am an on-call SRE assistant that remembers past incidents."
    )
    print("✅ Hindsight bank created/ready")
except Exception as e:
    print("Bank creation note:", e)

h.retain(
    bank_id=BANK,
    content=(
        "INC-001: checkout-service returned 5xx errors. "
        "Root cause: database connection pool exhausted. "
        "Fix: increased pool size from 10 to 50. "
        "Outcome: the fix worked."
    )
)

print("✅ Memory stored")

result = h.recall(
    bank_id=BANK,
    query="checkout 5xx errors"
)

print("\nHINDSIGHT RESULTS:")
for memory in result.results:
    print("-", memory.text)

# -----------------------------
# GROQ TEST
# -----------------------------
print("\nTesting Groq...")

g = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

response = g.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {
            "role": "user",
            "content": "Say hello in exactly 5 words."
        }
    ]
)

print("GROQ RESPONSE:")
print(response.choices[0].message.content)

print("\n✅ SETUP TEST FINISHED")
