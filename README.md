# OnCall Memory

> The senior engineer who has seen this outage before.

OnCall Memory is an AI-assisted SRE incident triage system for Northwind Payments. Its core capability is persistent organizational memory: production incidents, successful fixes, failed mitigations, and the engineers who resolved them are retained in Hindsight and recalled when a new incident arrives.

## Why this exists

Engineering organizations accumulate incident knowledge across alerts, logs, post-mortems, tickets, pull requests, chat, and people. The same underlying failure can appear with different symptoms across different services.

A normal LLM can reason about the current alert. Retrieval can find existing information. OnCall Memory adds persistent experience: what happened before, what worked, what failed, and who solved it.

## Core demo

1. A fresh production alert arrives.
2. The baseline agent reasons only from the current alert.
3. The Hindsight-enabled agent recalls historical incidents across services.
4. The agent cites incident IDs and previous successful fixes.
5. It warns when a proposed mitigation failed previously.
6. Closing the incident writes a post-mortem back into Hindsight.
7. A later incident can use that newly retained experience.

## Architecture

```text
Streamlit UI
    |
    +--> Baseline triage --------> Groq LLM
    |
    +--> Memory triage
            |
            +--> Hindsight recall
            +--> Hindsight reflect
            +--> Groq reasoning
    |
    +--> Resolve incident
            |
            +--> Post-mortem
            +--> Hindsight retain
            |
            +--> Future alerts use the new memory
```

## Project structure

```text
core/
  memory.py
  triage.py
  feedback.py

scripts/
  generate_data.py
  load_data.py
  run_triage.py
  run_feedback.py
  eval_learning.py
  run_eval.py

data/
  incidents.json
  holdout.json
  eval_results.json
  learning_curve.svg

app.py
.env
```

## Hindsight memory design

One team bank is used:

`northwind-platform-sre`

Memory contains incident ID, service, alert/symptoms, narrative, root cause, successful fix, failed mitigation, and resolver.

The application uses:

- `retain` / `retain_batch` to store incident experience
- `recall` to retrieve relevant historical experience
- `reflect` to reason over retrieved experience

## Evaluation

A held-out set of 10 incidents was evaluated while training memory increased from 0 to 10, 20, 30, and 40 incidents.

Measured metric: whether at least one of the top-5 retrieved memories belonged to the same failure family as the holdout incident.

Observed results:

```text
Memory size      Hit rate
0                0%
10               90%
20               100%
30               100%
40               100%
```

This measures memory retrieval behavior on the prepared holdout set. It is not a claim that the system resolves every production incident correctly.

## Run

Activate the Python environment, then:

```powershell
streamlit run app.py
```

For terminal demos:

```powershell
python -m scripts.run_triage
python -m scripts.run_feedback
python -m scripts.run_eval
```

## Important

Never commit `.env` or API keys.
