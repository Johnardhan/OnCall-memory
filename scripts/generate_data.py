import json
import os
import random
import time
from datetime import date, timedelta

from dotenv import load_dotenv
from groq import Groq


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is missing. Put it in the .env file in the project root."
    )

client = Groq(api_key=GROQ_API_KEY)

# Current Groq model IDs.
MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
]

# Keep requests slow enough to reduce rate-limit failures.
REQUEST_DELAY_SECONDS = 6.0
MAX_RETRIES_PER_MODEL = 3
INVALID_OUTPUT_RETRIES = 2

random.seed(7)


# ============================================================
# 2. FICTIONAL ENGINEERING TEAM
# ============================================================

ENGINEERS = [
    "Priya Nair",
    "Marcus Chen",
    "Sofia Alvarez",
    "Arjun Mehta",
    "Tom Becker",
]


# ============================================================
# 3. SERVICES IN NORTHWIND PAYMENTS
# ============================================================

STACKS = {
    "checkout-service": "Java/Spring Boot + Postgres + Redis",
    "payments-api": "Go + Postgres + Redis",
    "ledger-service": "Java + Postgres + Kafka",
    "notification-service": "Node.js + Kafka",
    "auth-gateway": "Go + Redis",
    "search-indexer": "Python + Kafka + Elasticsearch",
    "fraud-scoring": "Python + Kafka + Redis",
    "reporting-service": "Python + Postgres",
}


# ============================================================
# 4. SIX ROOT-CAUSE FAMILIES
# ============================================================

FAMILIES = [
    {
        "key": "db_pool",
        "root_cause": (
            "Database connection pool exhausted because connections leaked "
            "behind slow queries that never timed out"
        ),
        "fix": (
            "Raised the pool limit to 50, enabled idle-connection reaping, "
            "and added a 5 second statement timeout"
        ),
        "wrong_fix": (
            "Restarted the service pods, which cleared the errors for a few "
            "hours until the pool filled up again"
        ),
        "services": [
            "checkout-service",
            "payments-api",
            "ledger-service",
            "reporting-service",
        ],
        "experts": ["Priya Nair", "Marcus Chen"],
        "styles": [
            "5xx error rate spikes while p99 latency climbs sharply under load",
            "requests begin queueing and several endpoints become intermittently slow or unavailable",
            "traffic remains steady but request failures increase during sustained load",
        ],
        "forbidden_public_terms": [
            "connection pool",
            "pool exhausted",
            "too many clients",
            "pool has no free",
            "database connection",
        ],
    },
    {
        "key": "redis_eviction",
        "root_cause": (
            "Redis reached maxmemory and evicted hot keys, causing a cache "
            "stampede onto the primary database"
        ),
        "fix": (
            "Added TTL jitter, switched the eviction policy to allkeys-lru, "
            "raised maxmemory, and added request coalescing on hot keys"
        ),
        "wrong_fix": (
            "Flushed the entire Redis cache, which triggered an even bigger stampede"
        ),
        "services": [
            "payments-api",
            "auth-gateway",
            "fraud-scoring",
            "checkout-service",
        ],
        "experts": ["Sofia Alvarez", "Arjun Mehta"],
        "styles": [
            "request latency jumps suddenly and backend load rises far above normal",
            "a previously stable endpoint becomes slow while repeated requests surge downstream",
            "database CPU rises sharply without a matching increase in incoming traffic",
        ],
        "forbidden_public_terms": [
            "redis",
            "cache",
            "evict",
            "maxmemory",
            "oom",
            "memory limit",
        ],
    },
    {
        "key": "bad_config",
        "root_cause": (
            "A release went out with a missing or misnamed environment variable, "
            "so the service started with a broken configuration"
        ),
        "fix": (
            "Rolled back to the previous release and corrected the variable "
            "in the Helm values before redeploying"
        ),
        "wrong_fix": (
            "Scaled up replicas, which only multiplied the failing instances"
        ),
        "services": [
            "notification-service",
            "checkout-service",
            "fraud-scoring",
            "search-indexer",
        ],
        "experts": ["Tom Becker", "Priya Nair"],
        "styles": [
            "errors begin shortly after a release while the deployment still reports healthy instances",
            "new instances start successfully but requests fail immediately after startup",
            "a feature stops responding correctly after a release even though monitoring shows healthy pods",
        ],
        "forbidden_public_terms": [
            "configuration key",
            "configuration error",
            "environment variable",
            "env var",
            "helm values",
            "missing config",
            "undefined setting",
            "config.load",
        ],
    },
    {
        "key": "expired_cert",
        "root_cause": (
            "An internal TLS certificate or service secret expired because the "
            "scheduled rotation job had been failing silently"
        ),
        "fix": (
            "Rotated the certificate manually, fixed the rotation job permissions, "
            "and added an expiry alert at 14 days"
        ),
        "wrong_fix": (
            "Restarted the load balancer, which changed nothing because the certificate was still expired"
        ),
        "services": [
            "auth-gateway",
            "payments-api",
            "notification-service",
            "ledger-service",
        ],
        "experts": ["Marcus Chen", "Tom Becker"],
        "styles": [
            "calls to a dependency begin failing across multiple instances at nearly the same time",
            "an external integration suddenly returns authorization failures with no new deployment",
            "service-to-service requests drop to near zero while application traffic remains normal",
        ],
        "forbidden_public_terms": [
            "certificate",
            "cert",
            "tls",
            "ssl",
            "expired",
            "handshake",
            "credential",
            "secret rotation",
        ],
    },
    {
        "key": "kafka_poison",
        "root_cause": (
            "A poison message with a malformed payload crashed the consumer on "
            "every retry, so consumer lag kept growing"
        ),
        "fix": (
            "Moved the offending offset to the dead-letter topic, restarted the "
            "consumer group, and added schema validation before publishing"
        ),
        "wrong_fix": (
            "Increased consumer replicas, but every replica crashed on the same message"
        ),
        "services": [
            "notification-service",
            "search-indexer",
            "fraud-scoring",
            "ledger-service",
        ],
        "experts": ["Sofia Alvarez", "Arjun Mehta"],
        "styles": [
            "background processing stops while the event backlog grows continuously",
            "worker instances restart repeatedly and queued work stops progressing",
            "message processing throughput drops to zero while the service remains reachable",
        ],
        "forbidden_public_terms": [
            "kafka",
            "poison",
            "dead-letter",
            "offset",
            "deserialization",
            "schema",
            "payload",
            "consumer group",
        ],
    },
    {
        "key": "disk_full",
        "root_cause": (
            "The node disk filled up because log rotation was misconfigured "
            "after a base image change"
        ),
        "fix": (
            "Re-enabled logrotate with 7 day retention, cleared old logs, "
            "and added a disk usage alert at 80 percent"
        ),
        "wrong_fix": (
            "Expanded the volume by 20 GB, which filled up again within three days"
        ),
        "services": [
            "reporting-service",
            "search-indexer",
            "ledger-service",
            "notification-service",
        ],
        "experts": ["Arjun Mehta", "Sofia Alvarez"],
        "styles": [
            "writes begin failing and scheduled jobs start timing out",
            "background jobs become unreliable while local file operations slow down",
            "health checks degrade gradually and several write operations begin returning errors",
        ],
        "forbidden_public_terms": [
            "disk",
            "storage",
            "no space",
            "logrotate",
            "volume",
            "ephemeral storage",
            "disk pressure",
        ],
    },
]

FAM = {family["key"]: family for family in FAMILIES}


# ============================================================
# 5. EXACT DATA SPLIT
# ============================================================

TRAIN_COUNTS = {
    "db_pool": 7,
    "redis_eviction": 7,
    "bad_config": 6,
    "expired_cert": 6,
    "kafka_poison": 7,
    "disk_full": 7,
}

HOLDOUT_COUNTS = {
    "db_pool": 2,
    "redis_eviction": 2,
    "bad_config": 2,
    "expired_cert": 2,
    "kafka_poison": 1,
    "disk_full": 1,
}

assert sum(TRAIN_COUNTS.values()) == 40
assert sum(HOLDOUT_COUNTS.values()) == 10


# ============================================================
# 6. RANDOM DATE GENERATOR
# ============================================================

def rand_date(start_date, end_date):
    days = (end_date - start_date).days
    return (
        start_date + timedelta(days=random.randint(0, days))
    ).isoformat()


# ============================================================
# 7. BUILD THE INCIDENT PLAN
# ============================================================

def build_plan():
    train = []
    holdout = []

    # 40 historical incidents used to build memory.
    for family_key, count in TRAIN_COUNTS.items():
        family = FAM[family_key]

        for _ in range(count):
            engineer = (
                random.choice(family["experts"])
                if random.random() < 0.75
                else random.choice(ENGINEERS)
            )

            train.append(
                {
                    "family": family_key,
                    "service": random.choice(family["services"]),
                    "engineer": engineer,
                    "style": random.choice(family["styles"]),
                    "severity": random.choice(
                        ["SEV2", "SEV2", "SEV3", "SEV3", "SEV3", "SEV1"]
                    ),
                    "date": rand_date(
                        date(2026, 1, 5),
                        date(2026, 6, 30),
                    ),
                    "first_fix_failed": random.random() < 0.45,
                }
            )

    # 10 future/unseen incidents used only for evaluation.
    for family_key, count in HOLDOUT_COUNTS.items():
        family = FAM[family_key]

        for _ in range(count):
            holdout.append(
                {
                    "family": family_key,
                    "service": random.choice(family["services"]),
                    "engineer": random.choice(ENGINEERS),
                    "style": random.choice(family["styles"]),
                    "severity": random.choice(
                        ["SEV2", "SEV2", "SEV3", "SEV3", "SEV1"]
                    ),
                    "date": rand_date(
                        date(2026, 7, 5),
                        date(2026, 9, 20),
                    ),
                    "first_fix_failed": False,
                }
            )

    train.sort(key=lambda item: item["date"])
    holdout.sort(key=lambda item: item["date"])

    for number, item in enumerate(train, start=1):
        item["id"] = f"INC-{number:03d}"

    for number, item in enumerate(holdout, start=1):
        item["id"] = f"NEW-{number:02d}"

    return train, holdout


# ============================================================
# 8. JSON + OUTPUT NORMALIZATION
# ============================================================

def parse_json(text):
    if not text:
        raise ValueError("Groq returned an empty response.")

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("Groq did not return a JSON object.")

    return json.loads(text[start:end + 1])


def normalize_logs(logs):
    if isinstance(logs, list):
        return "\n".join(
            str(line).strip()
            for line in logs
            if str(line).strip()
        )

    if isinstance(logs, str):
        return logs.replace("\r\n", "\n").strip()

    return str(logs)


def public_text(record):
    return (
        str(record.get("alert", "")) + "\n"
        + normalize_logs(record.get("logs", ""))
    ).lower()


def find_forbidden_terms(record, forbidden_terms):
    text = public_text(record)

    return [
        term
        for term in forbidden_terms
        if term.lower() in text
    ]


# ============================================================
# 9. CALL GROQ WITH RETRIES + FALLBACK
# ============================================================

def call_llm(prompt):
    last_error = None

    for model in MODELS:
        for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
            try:
                response = client.chat.completions.create(
                    model=model,
                    temperature=0.7,
                    reasoning_effort="low",
                    max_completion_tokens=900,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    response_format={
                        "type": "json_object"
                    },
                )

                return parse_json(
                    response.choices[0].message.content
                )

            except Exception as error:
                last_error = error

                wait_seconds = min(
                    2 ** attempt,
                    12,
                )

                print(
                    f"Retrying {model} "
                    f"(attempt {attempt}/{MAX_RETRIES_PER_MODEL}) "
                    f"after {wait_seconds}s..."
                )

                time.sleep(wait_seconds)

    raise last_error


# ============================================================
# 10. BUILD GROQ PROMPT
# ============================================================

def make_prompt(
    item,
    is_holdout,
    revision=False,
    forbidden_hits=None,
):
    family = FAM[item["family"]]

    if item["first_fix_failed"]:
        resolution_minutes = random.randint(90, 240)
        first_fix_description = (
            f"First attempted fix (it FAILED): "
            f"{family['wrong_fix']}"
        )
    else:
        resolution_minutes = random.randint(15, 60)
        first_fix_description = (
            "First attempted fix: none. "
            "The correct fix was applied directly."
        )

    item["resolution_minutes"] = resolution_minutes

    if is_holdout:
        output_keys = '"alert" and "logs"'
        narrative_instruction = (
            "Do not include a narrative in the holdout record."
        )
    else:
        output_keys = '"alert", "logs" and "narrative"'
        narrative_instruction = """
"narrative": a 100 to 140 word post-mortem in plain prose,
past tense. It MUST include the engineer, service, date,
symptoms, the first failed fix and why it failed when applicable,
the true root cause, the final successful fix, and time to resolve.
The narrative is historical knowledge and MAY contain the true
root cause and fix. Do not use bullet points.
"""

    revision_instruction = ""

    if revision:
        revision_instruction = f"""
REVISION REQUIRED.
The previous public output leaked these hidden diagnostic terms:
{", ".join(forbidden_hits or [])}

Rewrite the alert and logs so they contain only observable symptoms.
Do not use or paraphrase the hidden mechanism terms.
"""

    prompt = f"""
Generate one realistic synthetic incident record for a fictional
fintech company called Northwind Payments.

Facts you MUST respect:

- Incident ID: {item["id"]}
- Date: {item["date"]}
- Service: {item["service"]}
- Technology stack: {STACKS[item["service"]]}
- Severity: {item["severity"]}
- On-call engineer: {item["engineer"]}

TRUE HISTORICAL ROOT CAUSE:
{family["root_cause"]}

FINAL SUCCESSFUL FIX:
{family["fix"]}

{first_fix_description}

OBSERVED SYMPTOM PATTERN:
{item["style"]}

PUBLIC-OUTPUT RULES:

1. The alert and logs are what the engineer sees BEFORE diagnosis.
2. The alert and logs contain observable symptoms and effects only.
3. Never directly reveal the true root cause.
4. Never name the underlying mechanism.
5. Never name the final fix.
6. Never include configuration keys, remediation steps, or
   specific internal mechanism names in the alert or logs.
7. Make the symptoms realistic but diagnostically incomplete.
8. The training narrative is historical knowledge and MAY contain
   the true cause, failed fix, successful fix, engineer, and lesson.

The following terms must NOT appear in the public alert/log text:

{", ".join(family["forbidden_public_terms"])}

{revision_instruction}

Return ONLY valid JSON with these keys:
{output_keys}

"alert":
A single PagerDuty-style alert title. Mention the service and
observable symptoms only.

"logs":
4 to 5 realistic log lines with timestamps, hostnames, and
stack-appropriate errors. Symptoms only.

{narrative_instruction}
"""

    return prompt


# ============================================================
# 11. GENERATE ONE INCIDENT WITH LEAK CHECKING
# ============================================================

def generate_incident(item, is_holdout):
    family = FAM[item["family"]]
    forbidden_hits = None

    for attempt in range(1, INVALID_OUTPUT_RETRIES + 2):
        result = call_llm(
            make_prompt(
                item=item,
                is_holdout=is_holdout,
                revision=(attempt > 1),
                forbidden_hits=forbidden_hits,
            )
        )

        if "alert" not in result or "logs" not in result:
            raise ValueError(
                f"{item['id']} returned JSON without alert/logs."
            )

        result["logs"] = normalize_logs(result["logs"])

        forbidden_hits = find_forbidden_terms(
            result,
            family["forbidden_public_terms"],
        )

        if not forbidden_hits:
            return result

        print(
            f"Public-output leak detected for {item['id']}: "
            f"{forbidden_hits}"
        )
        time.sleep(1)

    raise ValueError(
        f"Could not generate clean public output for {item['id']}."
    )


# ============================================================
# 12. MAIN GENERATION PIPELINE
# ============================================================

def main():
    os.makedirs("data", exist_ok=True)

    cache_path = "data/cache.json"

    if os.path.exists(cache_path):
        with open(
            cache_path,
            "r",
            encoding="utf-8",
        ) as file:
            cache = json.load(file)
    else:
        cache = {}

    train, holdout = build_plan()

    # Generate 40 training incidents and 10 holdout incidents.
    # Cached records are skipped so an interrupted run can resume.
    for group, is_holdout in (
        (train, False),
        (holdout, True),
    ):
        for item in group:
            if item["id"] in cache:
                print(
                    "cached",
                    item["id"],
                    item["service"],
                    item["family"],
                )
                continue

            result = generate_incident(
                item,
                is_holdout,
            )

            cache[item["id"]] = {
                **item,
                **result,
            }

            with open(
                cache_path,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    cache,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

            print(
                "done",
                item["id"],
                item["service"],
                item["family"],
            )

            time.sleep(REQUEST_DELAY_SECONDS)

    # --------------------------------------------------------
    # BUILD TRAINING DATASET
    # --------------------------------------------------------

    incidents = []

    for item in train:
        record = cache[item["id"]]
        family = FAM[record["family"]]

        record["logs"] = normalize_logs(
            record["logs"]
        )

        record["root_cause"] = family["root_cause"]
        record["fix"] = family["fix"]
        record["failed_fix"] = (
            family["wrong_fix"]
            if record["first_fix_failed"]
            else None
        )

        incidents.append(record)

    # --------------------------------------------------------
    # BUILD HOLDOUT DATASET
    # --------------------------------------------------------

    holdout_records = []

    for item in holdout:
        record = cache[item["id"]]
        family = FAM[record["family"]]

        holdout_records.append(
            {
                "id": record["id"],
                "date": record["date"],
                "service": record["service"],
                "alert": record["alert"],
                "logs": normalize_logs(record["logs"]),
                "truth_family": record["family"],
                "truth_root_cause": family["root_cause"],
                "truth_fix": family["fix"],
            }
        )

    # --------------------------------------------------------
    # FINAL SAFETY CHECK
    # --------------------------------------------------------

    for record in incidents:
        family = FAM[record["family"]]
        leaks = find_forbidden_terms(
            record,
            family["forbidden_public_terms"],
        )

        if leaks:
            raise RuntimeError(
                f"Final dataset leak in {record['id']}: {leaks}"
            )

    for record in holdout_records:
        family = FAM[record["truth_family"]]
        leaks = find_forbidden_terms(
            record,
            family["forbidden_public_terms"],
        )

        if leaks:
            raise RuntimeError(
                f"Final holdout leak in {record['id']}: {leaks}"
            )

    # --------------------------------------------------------
    # SAVE FINAL DATA
    # --------------------------------------------------------

    with open(
        "data/incidents.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            incidents,
            file,
            indent=2,
            ensure_ascii=False,
        )

    with open(
        "data/holdout.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            holdout_records,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 60)
    print("DATA GENERATION COMPLETE")
    print("=" * 60)
    print(
        f"Training incidents : {len(incidents)}"
    )
    print(
        f"Holdout incidents  : {len(holdout_records)}"
    )
    print(
        f"Total incidents    : "
        f"{len(incidents) + len(holdout_records)}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
