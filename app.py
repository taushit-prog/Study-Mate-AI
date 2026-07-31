"""
app.py — Study Planner Agent
Flask backend that calls IBM Watsonx.ai (Granite) directly via requests.
"""

import os
import time
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from agent_instructions import SYSTEM_PROMPT, WATSONX_MODEL_ID, MODEL_FALLBACKS, GENERATION_PARAMS

# ── Load environment variables ──────────────────────────────
load_dotenv()

IBM_API_KEY        = os.getenv("IBM_API_KEY", "").strip()
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "").strip()
WATSONX_URL        = os.getenv("WATSONX_URL", "https://au-syd.ml.cloud.ibm.com").strip().rstrip("/")
FLASK_SECRET_KEY   = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

# ── Flask app setup ──────────────────────────────────────────
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.config["SESSION_PERMANENT"] = False

# ── IAM token cache ──────────────────────────────────────────
_iam_token_cache = {"token": None, "expires_at": 0}

# Build the ordered list of models to try (primary first, then fallbacks,
# de-duplicated while preserving order).
_MODEL_CANDIDATES = list(dict.fromkeys([WATSONX_MODEL_ID] + list(MODEL_FALLBACKS)))


def get_iam_token() -> str:
    """Fetch (or return cached) IBM IAM bearer token."""
    now = time.time()
    if _iam_token_cache["token"] and now < _iam_token_cache["expires_at"] - 60:
        return _iam_token_cache["token"]

    resp = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": IBM_API_KEY,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _iam_token_cache["token"] = data["access_token"]
    _iam_token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return _iam_token_cache["token"]


def _build_prompt(messages: list[dict], extra_system: str = "") -> str:
    system_text = SYSTEM_PROMPT
    if extra_system:
        system_text += f"\n\n{extra_system}"

    parts = [f"<|system|>\n{system_text}\n<|end|>"]
    for msg in messages:
        parts.append(f"<|{msg['role']}|>\n{msg['content']}\n<|end|>")
    parts.append("<|assistant|>")
    return "\n".join(parts)


def _call_model(model_id: str, prompt: str, token: str) -> requests.Response:
    url = f"{WATSONX_URL}/ml/v1/text/generation?version=2024-05-31"
    payload = {
        "model_id": model_id,
        "project_id": WATSONX_PROJECT_ID,
        "input": prompt,
        "parameters": GENERATION_PARAMS,
    }
    return requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=payload,
        timeout=60,
    )


def call_watsonx(messages: list[dict], extra_system: str = "") -> str:
    """
    Send a conversation to Watsonx.ai text generation endpoint and return
    the assistant reply as a string. Automatically retries with fallback
    models if the primary model isn't available (404) in this region.
    """
    if not IBM_API_KEY or not WATSONX_PROJECT_ID:
        return (
            "⚠️ **Configuration required** — please set `IBM_API_KEY` and "
            "`WATSONX_PROJECT_ID` in your `.env` file, then restart the app."
        )

    full_prompt = _build_prompt(messages, extra_system)

    try:
        token = get_iam_token()
    except requests.exceptions.HTTPError as exc:
        return f"❌ IBM authentication failed ({exc.response.status_code}). Check IBM_API_KEY in .env."
    except requests.exceptions.RequestException as exc:
        return f"❌ Network error while authenticating: {exc}"

    last_error = None
    for model_id in _MODEL_CANDIDATES:
        try:
            resp = _call_model(model_id, full_prompt, token)
            if resp.status_code == 404:
                # This model isn't deployed in this region/project — try next.
                last_error = f"404 for model '{model_id}'"
                continue
            resp.raise_for_status()
            result = resp.json()
            return result["results"][0]["generated_text"].strip()
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response else "?"
            body = exc.response.text[:500] if exc.response else str(exc)
            if status == 404:
                last_error = f"404 for model '{model_id}'"
                continue
            return f"❌ Watsonx API error {status} (model: {model_id}): {body}"
        except requests.exceptions.RequestException as exc:
            return f"❌ Network error: {exc}"
        except (KeyError, IndexError) as exc:
            return f"❌ Unexpected response format from Watsonx: {exc}"

    return (
        "❌ None of the configured models were found in your region "
        f"({WATSONX_URL}). Tried: {', '.join(_MODEL_CANDIDATES)}. "
        f"Last error: {last_error}. "
        "Verify WATSONX_URL matches your project's region and that "
        "watsonx.ai Runtime is associated with your project."
    )


# ── Helper — conversation history ───────────────────────────

def get_history() -> list[dict]:
    return session.get("chat_history", [])


def push_history(role: str, content: str) -> None:
    history = get_history()
    history.append({"role": role, "content": content})
    session["chat_history"] = history[-40:]


# ═══════════════════════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    push_history("user", message)
    reply = call_watsonx(get_history())
    push_history("assistant", reply)
    return jsonify({"reply": reply})


@app.route("/api/chat/clear", methods=["POST"])
def clear_chat():
    session.pop("chat_history", None)
    return jsonify({"status": "cleared"})


@app.route("/api/schedule/generate", methods=["POST"])
def generate_schedule():
    data = request.get_json(silent=True) or {}
    subjects = data.get("subjects", [])
    exam_date = data.get("exam_date", "")
    daily_hrs = data.get("daily_hours", 6)
    start_date = data.get("start_date", datetime.today().strftime("%Y-%m-%d"))

    if not subjects or not exam_date:
        return jsonify({"error": "subjects and exam_date are required"}), 400

    subjects_text = "\n".join(
        f"  - {s.get('name', 'Subject')} "
        f"(difficulty: {s.get('difficulty', 'medium')}, "
        f"priority: {s.get('priority', 'normal')})"
        for s in subjects
    )

    prompt = f"""Create a complete day-wise study schedule with the following details:

**Study Start Date:** {start_date}
**Exam Date:** {exam_date}
**Daily Study Hours Available:** {daily_hrs} hours
**Subjects:**
{subjects_text}

Please provide:
1. A day-wise schedule table (Date | Subject | Topics | Hours | Technique)
2. Subject-wise time allocation summary
3. Revision cycle plan using spaced repetition
4. Quiz/practice suggestions per subject
5. A motivational closing tip
"""
    push_history("user", prompt)
    reply = call_watsonx(get_history())
    push_history("assistant", reply)
    return jsonify({"schedule": reply})


@app.route("/api/exams/countdown", methods=["POST"])
def exam_countdown():
    data = request.get_json(silent=True) or {}
    exams = data.get("exams", [])
    today = datetime.today().date()

    result = []
    for exam in exams:
        try:
            exam_d = datetime.strptime(exam["date"], "%Y-%m-%d").date()
            delta = (exam_d - today).days
            status = "upcoming" if delta > 0 else ("today" if delta == 0 else "past")
            result.append({
                "name": exam["name"],
                "date": exam["date"],
                "days_left": delta,
                "status": status,
            })
        except (ValueError, KeyError):
            continue

    result.sort(key=lambda x: x["days_left"] if x["days_left"] >= 0 else 9999)
    return jsonify({"exams": result})


@app.route("/api/revision/plan", methods=["POST"])
def revision_plan():
    data = request.get_json(silent=True) or {}
    subject = data.get("subject", "")
    topics = data.get("topics", [])
    exam_dt = data.get("exam_date", "")
    weak_areas = data.get("weak_areas", [])

    if not subject or not topics:
        return jsonify({"error": "subject and topics are required"}), 400

    weak_clause = (
        f"\n**Weak areas to focus on:** {', '.join(weak_areas)}"
        if weak_areas else ""
    )

    prompt = f"""Create a detailed revision plan for:

**Subject:** {subject}
**Topics to revise:** {', '.join(topics)}{weak_clause}
**Exam Date:** {exam_dt or 'Not specified'}

Include:
1. Priority order for revision (start with weakest/highest-weightage)
2. Spaced repetition schedule for each topic
3. Active recall quiz questions for each topic (3-5 questions)
4. Estimated time per topic
5. Daily revision timetable for the final week before the exam
"""
    push_history("user", prompt)
    reply = call_watsonx(get_history())
    push_history("assistant", reply)
    return jsonify({"plan": reply})


@app.route("/api/tip", methods=["GET"])
def daily_tip():
    today = datetime.today().strftime("%A, %B %d")
    prompt = (
        f"Give me one concise, actionable study tip for {today}. "
        "Make it specific, practical, and motivating. Keep it under 3 sentences."
    )
    tip = call_watsonx([{"role": "user", "content": prompt}])
    return jsonify({"tip": tip})


@app.route("/api/health")
def health():
    configured = bool(IBM_API_KEY and WATSONX_PROJECT_ID)
    return jsonify({
        "status": "ok",
        "model_primary": WATSONX_MODEL_ID,
        "model_fallbacks": MODEL_FALLBACKS,
        "watsonx_url": WATSONX_URL,
        "configured": configured,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


# ═══════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    print(f"Study Planner Agent starting on http://127.0.0.1:{port}")
    print(f"   Region URL : {WATSONX_URL}")
    print(f"   Model      : {WATSONX_MODEL_ID} (+ {len(MODEL_FALLBACKS)-1} fallbacks)")
    print(f"   API Key    : {'SET' if IBM_API_KEY else 'MISSING'}")
    print(f"   Project ID : {'SET' if WATSONX_PROJECT_ID else 'MISSING'}")
    app.run(host="0.0.0.0", port=port, debug=debug)
