import json
from pathlib import Path


DATA_DIR = Path("data")
TRAIN_FILE = DATA_DIR / "incidents.json"
HOLDOUT_FILE = DATA_DIR / "holdout.json"

TRAIN_BACKUP = DATA_DIR / "incidents_before_clean.json"
HOLDOUT_BACKUP = DATA_DIR / "holdout_before_clean.json"


# ============================================================
# SAFE PUBLIC INCIDENT TEMPLATES
#
# IMPORTANT:
# We rebuild ONLY alert + logs locally.
# No Groq/API call is used.
#
# The historical narrative, root_cause, fix, and failed_fix
# are preserved exactly as they are.
# ============================================================

PUBLIC_PATTERNS = {
    "db_pool": {
        "alerts": [
            "{service}: elevated 5xx errors and rising latency under load",
            "{service}: intermittent request failures and increasing p99 latency",
            "{service}: request queueing detected with rising error rate",
        ],
        "logs": [
            "WARN request latency increased above the normal service budget",
            "ERROR upstream operation timed out while handling request",
            "WARN active requests are queueing behind slow operations",
            "ERROR request failed after repeated backend timeouts",
        ],
    },
    "redis_eviction": {
        "alerts": [
            "{service}: backend latency spike with elevated request failures",
            "{service}: downstream response times increased sharply",
            "{service}: sudden dependency load increase and request degradation",
        ],
        "logs": [
            "WARN downstream response time increased above the normal range",
            "ERROR request exceeded dependency timeout budget",
            "WARN repeated backend requests detected during traffic spike",
            "ERROR request failed after downstream retries were exhausted",
        ],
    },
    "bad_config": {
        "alerts": [
            "{service}: requests failing shortly after a release",
            "{service}: newly started instances returning request errors",
            "{service}: post-release request failures despite healthy instances",
        ],
        "logs": [
            "INFO service startup health check completed successfully",
            "ERROR request handler initialization did not complete correctly",
            "WARN newly started instance returned an application error",
            "ERROR request failed with internal service error",
        ],
    },
    "expired_cert": {
        "alerts": [
            "{service}: integration requests suddenly rejected",
            "{service}: elevated authorization failures from downstream dependency",
            "{service}: service-to-service requests failing without a new release",
        ],
        "logs": [
            "WARN downstream integration response rate dropped sharply",
            "ERROR request to dependency was rejected",
            "WARN authorization failures increased across multiple instances",
            "ERROR retry budget exhausted while contacting dependency",
        ],
    },
    "kafka_poison": {
        "alerts": [
            "{service}: background processing halted while backlog increases",
            "{service}: worker restart loop with growing processing backlog",
            "{service}: event processing throughput dropped to zero",
        ],
        "logs": [
            "WARN background processing backlog continues to increase",
            "ERROR worker failed while processing an incoming event",
            "WARN retry threshold reached for a processing task",
            "ERROR processing loop terminated unexpectedly",
        ],
    },
    "disk_full": {
        "alerts": [
            "{service}: write operations failing and scheduled jobs timing out",
            "{service}: local write failures causing job degradation",
            "{service}: background jobs failing during output operations",
        ],
        "logs": [
            "WARN local write operations are taking longer than normal",
            "ERROR application failed while writing required output",
            "WARN scheduled task did not complete within its execution window",
            "ERROR temporary output operation failed",
        ],
    },
}


# Absolute safety list for the PUBLIC portion only.
# These terms must never appear in alert/log text.
FORBIDDEN = [
    "connection pool",
    "too many clients",
    "database connection",
    "database pool",
    "redis",
    "cache",
    "maxmemory",
    "oom",
    "memory limit",
    "environment variable",
    "env var",
    "configuration",
    "config",
    "configuration key",
    "configuration error",
    "undefined setting",
    "missing setting",
    "helm",
    "certificate",
    "cert",
    "tls",
    "ssl",
    "expired",
    "handshake",
    "credential",
    "secret",
    "kafka",
    "poison",
    "dead-letter",
    "offset",
    "deserialization",
    "consumer group",
    "consumer",
    "payload",
    "schema",
    "disk",
    "storage",
    "no space",
    "logrotate",
    "volume",
    "ephemeral",
]


def normalize_public_text(alert, logs):
    if isinstance(logs, list):
        logs_text = "\n".join(str(x) for x in logs)
    else:
        logs_text = str(logs)

    return f"{alert}\n{logs_text}".lower()


def find_forbidden(text):
    lower = text.lower()
    return sorted(
        {
            term
            for term in FORBIDDEN
            if term.lower() in lower
        }
    )


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def rebuild_public_fields(record, pattern_index):
    family = record.get("family") or record.get("truth_family")

    if family not in PUBLIC_PATTERNS:
        raise ValueError(
            f"{record.get('id')}: unknown family {family!r}"
        )

    patterns = PUBLIC_PATTERNS[family]

    service = record["service"]

    alert = patterns["alerts"][
        pattern_index % len(patterns["alerts"])
    ].format(service=service)

    log_lines = []

    for index, template in enumerate(
        patterns["logs"]
    ):
        minute = 10 + ((pattern_index + index) % 40)
        second = 10 + (index * 11)

        log_lines.append(
            f"{record['date']}T08:{minute:02d}:{second:02d}Z "
            f"{service}-node-{index + 1} "
            f"{template}"
        )

    record["alert"] = alert
    record["logs"] = "\n".join(log_lines)

    return record


def main():
    if not TRAIN_FILE.exists():
        raise FileNotFoundError(
            f"Missing {TRAIN_FILE}"
        )

    if not HOLDOUT_FILE.exists():
        raise FileNotFoundError(
            f"Missing {HOLDOUT_FILE}"
        )

    incidents = load_json(TRAIN_FILE)
    holdout = load_json(HOLDOUT_FILE)

    # --------------------------------------------------------
    # Backup existing files once.
    # --------------------------------------------------------

    if not TRAIN_BACKUP.exists():
        save_json(
            TRAIN_BACKUP,
            incidents,
        )

    if not HOLDOUT_BACKUP.exists():
        save_json(
            HOLDOUT_BACKUP,
            holdout,
        )

    # --------------------------------------------------------
    # Rebuild ONLY public fields locally.
    # --------------------------------------------------------

    for index, record in enumerate(incidents):
        rebuild_public_fields(
            record,
            index,
        )

    for index, record in enumerate(holdout):
        rebuild_public_fields(
            record,
            index + len(incidents),
        )

    # --------------------------------------------------------
    # Validate public text.
    # --------------------------------------------------------

    leaks = []

    for record in incidents + holdout:
        text = normalize_public_text(
            record["alert"],
            record["logs"],
        )

        found = find_forbidden(text)

        if found:
            leaks.append(
                {
                    "id": record["id"],
                    "terms": found,
                }
            )

    if leaks:
        print("PUBLIC LEAKS REMAIN")
        print("=" * 60)

        for leak in leaks:
            print(
                f"{leak['id']}: {', '.join(leak['terms'])}"
            )

        raise RuntimeError(
            f"{len(leaks)} records still contain forbidden public terms."
        )

    # --------------------------------------------------------
    # Validate counts.
    # --------------------------------------------------------

    if len(incidents) != 40:
        raise RuntimeError(
            f"Expected 40 training incidents, got {len(incidents)}"
        )

    if len(holdout) != 10:
        raise RuntimeError(
            f"Expected 10 holdout incidents, got {len(holdout)}"
        )

    # --------------------------------------------------------
    # Save final clean data.
    # --------------------------------------------------------

    save_json(
        TRAIN_FILE,
        incidents,
    )

    save_json(
        HOLDOUT_FILE,
        holdout,
    )

    print()
    print("=" * 60)
    print("DATASET CLEANUP COMPLETE")
    print("=" * 60)
    print(f"Training incidents : {len(incidents)}")
    print(f"Holdout incidents  : {len(holdout)}")
    print("Public leak matches: 0")
    print("=" * 60)
    print()
    print("No Groq API call was made.")
    print("Historical narratives and root-cause fields were preserved.")
    print(f"Backup: {TRAIN_BACKUP}")
    print(f"Backup: {HOLDOUT_BACKUP}")


if __name__ == "__main__":
    main()
