# C8 Submission Checklist

## Repository

- [ ] `.env` is ignored and not committed
- [ ] `venv/` is ignored
- [ ] `core/`, `scripts/`, `data/`, and `app.py` are present
- [ ] `README.md` is present
- [ ] `docs/HINDSIGHT_USAGE.md` is present

## Demo evidence

- [ ] Baseline vs Hindsight triage screenshot
- [ ] Memory Inspector screenshot
- [ ] Resolve + Remember confirmation screenshot
- [ ] Learning curve screenshot / chart

## Demo sequence

1. Start Streamlit.
2. Show the production alert.
3. Run with Hindsight memory ON.
4. Show historical incidents and failed-mitigation warning.
5. Scroll to Resolve + Remember.
6. Resolve the incident.
7. Re-run the same type of alert to show retained experience.
8. Show the learning curve.

## Final checks

- [ ] No API key appears in the repository or video.
- [ ] The live app starts with `streamlit run app.py`.
- [ ] The 40 training + 10 holdout dataset remains intact.
- [ ] `data/eval_results.json` contains the measured C7 results.
