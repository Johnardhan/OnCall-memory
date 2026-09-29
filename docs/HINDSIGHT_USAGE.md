# Hindsight Usage

## Bank

Bank ID:

`northwind-platform-sre`

The bank represents the shared long-term memory of the software engineering / SRE team.

## What is retained

Each incident is converted to a durable narrative containing:

- incident ID
- service
- date/time
- alert
- logs/symptoms
- incident narrative
- root cause
- successful fix
- failed mitigation
- resolving engineer

## Recall

When a new alert arrives, the application asks Hindsight to find historical incidents with similar symptoms and underlying causes, including incidents from other services.

The UI exposes the retrieved material through the Memory Inspector.

## Reflect

The memory-enabled triage path asks Hindsight to synthesize the historical context into an operational diagnosis.

The reasoning instructions require:

- incident IDs when evidence exists
- preference for fixes that worked previously
- explicit warnings about historically failed mitigations
- no unsupported certainty

## Learning loop

Resolved incidents are converted into post-mortems and retained back into the same team bank.

Therefore:

```text
Incident
   -> resolution
   -> post-mortem
   -> retain
   -> future recall
   -> improved context for the next incident
```

## What the demo proves

The demo is designed to make the difference between stateless reasoning and persistent organizational memory visible in a short interaction.

C4 shows different answers with and without memory.

C5 shows a resolved incident becoming future memory.

C7 measures retrieval behavior on a 10-incident holdout as memory grows from 0 to 40 training incidents.
