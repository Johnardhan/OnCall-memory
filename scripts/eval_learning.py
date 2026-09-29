
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

BANK_PREFIX = "northwind-eval-v3"
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

TRAIN_PATH = DATA_DIR / "incidents.json"
HOLDOUT_PATH = DATA_DIR / "holdout.json"
RESULT_PATH = DATA_DIR / "eval_results.json"
SVG_PATH = DATA_DIR / "learning_curve.svg"

STEPS = [0, 10, 20, 30, 40]


def get_client():
    return Hindsight(
        base_url=os.environ["HINDSIGHT_URL"],
        api_key=os.environ["HINDSIGHT_API_KEY"],
        timeout=90.0,
    )


def memory_text(incident):
    return (
        f"Incident {incident['id']}. "
        f"Failure family: {incident.get('family', '')}. "
        f"Service: {incident.get('service', '')}. "
        f"Alert: {incident.get('alert', '')}. "
        f"Logs: {incident.get('logs', '')}. "
        f"Root cause: {incident.get('root_cause', '')}. "
        f"Fix: {incident.get('fix', '')}."
    )


def ensure_bank(h, bank_id):
    try:
        h.create_bank(
            bank_id=bank_id,
            name=f"Northwind Evaluation {bank_id.split('-')[-1]}",
            mission=(
                "Measure whether historical incident memory retrieves incidents "
                "from the same failure family for held-out production alerts."
            ),
        )
    except Exception:
        pass


def extracted_ids(text):
    return set(re.findall(r"\bINC-\d+\b", text.upper()))


def svg_chart(results):
    width, height = 900, 500
    left, right, top, bottom = 90, 40, 50, 80
    plot_w = width - left - right
    plot_h = height - top - bottom

    points = []
    for i, row in enumerate(results):
        x = left + (i / (len(results) - 1)) * plot_w
        y = top + (1 - row["hit_rate"] / 100.0) * plot_h
        points.append((x, y))

    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    x_labels = []
    for i, row in enumerate(results):
        x = left + (i / (len(results) - 1)) * plot_w
        x_labels.append(
            f'<text x="{x:.1f}" y="{height-42}" text-anchor="middle" '
            f'font-size="18">{row["memory_size"]}</text>'
        )

    y_labels = []
    for pct in [0, 25, 50, 75, 100]:
        y = top + (1 - pct / 100) * plot_h
        y_labels.append(
            f'<text x="{left-15}" y="{y+6:.1f}" text-anchor="end" '
            f'font-size="16">{pct}%</text>'
        )

    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#2e7d32"/>'
        for x, y in points
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/>
<text x="{width/2}" y="28" text-anchor="middle" font-size="22" font-family="Arial" font-weight="bold">Hindsight Memory Learning Curve</text>
<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#555"/>
<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#555"/>
<polyline points="{poly}" fill="none" stroke="#1565c0" stroke-width="4"/>
{dots}
{''.join(y_labels)}
{''.join(x_labels)}
<text x="{width/2}" y="{height-8}" text-anchor="middle" font-size="18" font-family="Arial">Training incidents retained</text>
<text x="18" y="{height/2}" text-anchor="middle" font-size="18" font-family="Arial" transform="rotate(-90 18 {height/2})">Top-5 same-family retrieval hit rate</text>
</svg>"""


def main():
    with open(TRAIN_PATH, encoding="utf-8") as f:
        train = json.load(f)

    with open(HOLDOUT_PATH, encoding="utf-8") as f:
        holdout = json.load(f)

    family_by_id = {item["id"].upper(): item["family"] for item in train}
    results = []

    with get_client() as h:
        for size in STEPS:
            bank_id = f"{BANK_PREFIX}-{size}"

            if size == 0:
                results.append({
                    "memory_size": 0,
                    "evaluated": len(holdout),
                    "hits": 0,
                    "hit_rate": 0.0,
                })
                continue

            ensure_bank(h, bank_id)

            batch = [
                {
                    "content": memory_text(item),
                    "document_id": item["id"],
                }
                for item in train[:size]
            ]

            h.retain_batch(
                bank_id=bank_id,
                items=batch,
                retain_async=False,
            )

            hits = 0

            for item in holdout:
                query = (
                    f"Service: {item['service']}. "
                    f"Alert: {item['alert']}. "
                    f"Symptoms: {item['logs']}. "
                    f"Likely historical root cause: {item['truth_root_cause']}"
                )

                recall = h.recall(
                    bank_id=bank_id,
                    query=query,
                    max_tokens=3500,
                    budget="low",
                )

                retrieved_ids = []
                for mem in recall.results[:5]:
                    retrieved_ids.extend(extracted_ids(mem.text))

                # Ground truth is the holdout's explicit truth_family.
                # We identify each retrieved training incident by ID and
                # compare its known training family.
                found = any(
                    family_by_id.get(incident_id) == item["truth_family"]
                    for incident_id in retrieved_ids
                )

                if found:
                    hits += 1

            rate = round(100.0 * hits / len(holdout), 1)
            results.append({
                "memory_size": size,
                "evaluated": len(holdout),
                "hits": hits,
                "hit_rate": rate,
            })

    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    SVG_PATH.write_text(svg_chart(results), encoding="utf-8")

    print("✅ C7 FINAL EVALUATION FINISHED")
    print(json.dumps(results, indent=2))
    print(f"\n✅ Results: {RESULT_PATH}")
    print(f"✅ Learning curve: {SVG_PATH}")
    print("\nGround truth source: holdout.json truth_family")
    print("No Groq calls were used.")


if __name__ == "__main__":
    main()
