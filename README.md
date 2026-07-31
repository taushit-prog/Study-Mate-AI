# StudyMate — AI Study Planner Agent

A Flask web app that calls **IBM Watsonx.ai (Granite models)** directly via
`requests` to build personalized, day-wise study schedules, revision plans,
and a study-coach chat.

## 1. Install dependencies

```bash
cd study-planner-agent
pip install -r requirements.txt
```

## 2. Configure your `.env`

```bash
copy .env.example .env      # Windows
# or
cp .env.example .env        # Mac/Linux
```

Open `.env` and fill in **exactly** (no quotes, no spaces around `=`):

```
IBM_API_KEY=your_real_api_key_here
WATSONX_PROJECT_ID=your_real_project_id_here
WATSONX_URL=https://au-syd.ml.cloud.ibm.com
FLASK_SECRET_KEY=any-random-string
FLASK_ENV=development
```

**`WATSONX_URL` must match the region your watsonx.ai project/runtime is
actually in.** If your project was created with Sydney selected, keep
`au-syd`. If you're not sure, check IBM Cloud → your project → Manage →
General — the region is shown there.

## 3. Run it

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## 4. Check the health endpoint (optional but useful)

Visit **http://127.0.0.1:5000/api/health** in your browser. You should see:

```json
{
  "status": "ok",
  "model_primary": "ibm/granite-3-3-8b-instruct",
  "configured": true,
  ...
}
```

If `"configured": false`, your `.env` isn't being read correctly — double
check it's saved, has no typos in the variable names, and that you restarted
the server after editing it.

## Why this build won't 404 on you

The previous build failed with `404 Not Found` on the text-generation
endpoint. That happens when the exact `model_id` requested isn't deployed
in your account's region. This version tries a **list of models in order**
(`WATSONX_MODEL_ID` first, then `MODEL_FALLBACKS`) and automatically moves
to the next one if it gets a 404 — so a single unavailable model can't break
the whole app. You can see/edit this list in `agent_instructions.py`.

If **every** model in the list 404s, the app will tell you clearly instead
of failing silently — and the fix at that point is almost always one of:

1. `WATSONX_URL` region doesn't match your project's actual region.
2. The **watsonx.ai Runtime** service isn't associated with your project
   (IBM Cloud → your project → Manage → Services & integrations).
3. Your IBM Cloud account is frozen/restricted (check IBM Cloud → Manage →
   Billing and usage for any account status warnings).

## Customizing the agent

Everything about tone, study techniques, Pomodoro timings, and the model
used lives in **`agent_instructions.py`** — no need to touch `app.py`.

| Setting | What it does |
|---|---|
| `AGENT_TONE` | encouraging / strict / friendly / professional |
| `SPECIALIZED_SUBJECTS` | restrict the agent to specific subjects, or `[]` for all |
| `USE_POMODORO`, `USE_SPACED_REPETITION`, `USE_ACTIVE_RECALL` | toggle techniques on/off |
| `DIFFICULTY_PROGRESSION` | gradual / aggressive / steady |
| `WATSONX_MODEL_ID` / `MODEL_FALLBACKS` | which Granite/other models to try, in order |
| `GENERATION_PARAMS` | temperature, top_p, max tokens, etc. |

## Project structure

```
study-planner-agent/
├── app.py                   # Flask backend + Watsonx.ai calls
├── agent_instructions.py    # All customizable settings + system prompt
├── templates/index.html     # Frontend (Dashboard, Planner, Revision, Chat)
├── static/css/style.css     # Styling, dark mode, responsive layout
├── static/js/app.js         # Frontend logic
├── requirements.txt
├── .env.example
└── README.md
```

## Deployment (optional, for later)

For a simple deployment (e.g. Render, Railway, Heroku-style platforms):

1. Set the same environment variables (`IBM_API_KEY`, `WATSONX_PROJECT_ID`,
   `WATSONX_URL`, `FLASK_SECRET_KEY`, `FLASK_ENV=production`) in your
   platform's dashboard — never commit `.env`.
2. Use `gunicorn app:app` as the start command (already in
   `requirements.txt`).
