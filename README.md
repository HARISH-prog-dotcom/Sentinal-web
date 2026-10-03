# SentinelWeb (educational prototype)

Monitors requests to a demo app, flags suspicious patterns with rules + a trained model,
and shows them on a dashboard. Use only on your own local demo. Never test sites you do not own.

## Run (macOS)
    cd sentinelweb
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python train_model.py        # rebuilds models/sqli_model.joblib on YOUR machine (takes ~5 s)
    python evaluate.py           # writes results.md (rules vs ML vs combined)
    uvicorn main:app --reload

Open http://127.0.0.1:8000, then in a second terminal (same folder, venv active):

    python simulate.py

Always run train_model.py once: a model saved with a different scikit-learn version may not load.
If the model is missing, SentinelWeb still runs with rules only.

## How detection works
- SQL injection: fixed rules (HIGH, blocked in demo) + ML model trained on SQLiV3.csv.
  If only the model flags an input, it is MEDIUM, "Flagged", and never auto-blocked.
- XSS: rules only (the SQLi dataset does not cover XSS).
- Failed logins and request rate: sliding-window counters.

## Files
- main.py, detection.py, db.py, static/index.html - app, rules, storage, dashboard
- ml.py            - loads the model, scores text (threshold set at top)
- train_model.py   - cleans data/SQLiV3.csv, trains and saves the model + metrics
- evaluate.py      - compares rules / ML / combined on a held-out test split
- simulate.py      - safe test scenarios

## Dataset
data/SQLiV3.csv from Kaggle (SQLi dataset). Check and cite the dataset's license/author in your slides.
Cleaning: ~390 rows had shifted columns or conflicting labels and are dropped (30,919 -> 30,529).

## Threshold choice (test split, 6,106 rows)
| Threshold | Recall | False alarms |
|---|---|---|
| 0.5 | 98.8% | 1 |
| 0.7 (used) | 98.3% | 1 |
| 0.9 | 93.7% | 0 |

## Optional: AI answers in the chatbot (free key)
The chatbot answers from rules first. Only when no rule matches does it ask a free AI model.
1. Get a free key: Google AI Studio (aistudio.google.com, "Get API key") or Groq (console.groq.com, "API Keys").
2. In the project folder: `cp .env.example .env`, then open `.env` (e.g. `nano .env`) and paste your key.
3. Restart the server (changes to .env are not picked up by --reload).
4. `.env` is listed in .gitignore. Never upload it to GitHub or share it.
Without a key, the chatbot still works with rules only.
Only summary numbers are sent to the AI service, never IPs, evidence text, or logs.