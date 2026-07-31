"""
agent_instructions.py — Study Planner Agent Customization Hub
Edit the values below to change the agent's behavior, tone, and study
techniques. No need to touch app.py for any of these changes.
"""

# ── 1. PERSONA & TONE ────────────────────────────────────────
AGENT_NAME = "StudyMate"
AGENT_TONE = "encouraging"          # encouraging | strict | friendly | professional
AGENT_LANGUAGE_STYLE = "simple"     # simple | academic | casual | technical

# ── 2. SUBJECT SPECIALIZATION ────────────────────────────────
# Leave empty [] to support all subjects, or restrict to a list.
SPECIALIZED_SUBJECTS = []

# ── 3. STUDY TECHNIQUES ──────────────────────────────────────
USE_POMODORO           = True
USE_SPACED_REPETITION  = True
USE_ACTIVE_RECALL      = True
USE_FEYNMAN_TECHNIQUE  = False
USE_MIND_MAPPING       = False

# ── 4. POMODORO SETTINGS ──────────────────────────────────────
POMODORO_WORK_MINUTES        = 25
POMODORO_SHORT_BREAK         = 5
POMODORO_LONG_BREAK          = 20
POMODORO_LONG_BREAK_INTERVAL = 4

# ── 5. SPACED REPETITION INTERVALS (days) ────────────────────
SPACED_REPETITION_DAYS = [1, 3, 7, 14, 30]

# ── 6. DIFFICULTY PACING ─────────────────────────────────────
DIFFICULTY_PROGRESSION = "gradual"  # gradual | aggressive | steady

# ── 7. DAILY STUDY HOURS ──────────────────────────────────────
DEFAULT_DAILY_STUDY_HOURS = 6
MAX_DAILY_STUDY_HOURS     = 10

# ── 8. SCHEDULE PREFERENCES ───────────────────────────────────
PREFERRED_STUDY_START_TIME = "09:00"
INCLUDE_BREAKS             = True
INCLUDE_WEEKEND_STUDY      = True
WEEKEND_REDUCED_HOURS      = True
WEEKEND_DAILY_HOURS        = 4

# ── 9. QUIZ / PRACTICE SUGGESTIONS ────────────────────────────
AUTO_SUGGEST_QUIZZES   = True
QUIZ_FREQUENCY         = "end_of_topic"  # daily | end_of_topic | weekly
INCLUDE_MOCK_EXAM_WEEK = True

# ── 10. REVISION TRACKER BEHAVIOR ─────────────────────────────
REVISION_REMINDER_ENABLED = True
REVISION_CYCLES           = 3

# ── 11. RESPONSE FORMAT ────────────────────────────────────────
RESPONSE_FORMAT            = "markdown"  # markdown | plain
INCLUDE_EMOJI_IN_RESPONSE  = True
MAX_RESPONSE_TOKENS        = 1200

# ── 12. WATSONX MODEL SELECTION ───────────────────────────────
# Primary model to use. If this model returns a 404 (not deployed in
# your region), app.py will automatically retry with the next model
# in MODEL_FALLBACKS below — so the app keeps working even if one
# model ID isn't available in your specific IBM Cloud region.
WATSONX_MODEL_ID = "ibm/granite-3-3-8b-instruct"

MODEL_FALLBACKS = [
    "ibm/granite-3-3-8b-instruct",
    "ibm/granite-3-8b-instruct",
    "meta-llama/llama-3-3-70b-instruct",
]

# ── 13. GENERATION PARAMETERS ─────────────────────────────────
GENERATION_PARAMS = {
    "decoding_method": "greedy",
    "max_new_tokens": MAX_RESPONSE_TOKENS,
    "min_new_tokens": 0,
    "repetition_penalty": 1.1,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 50,
}

# =============================================================
#  SYSTEM PROMPT BUILDER
# =============================================================

def build_system_prompt() -> str:
    techniques = []
    if USE_POMODORO:
        techniques.append(
            f"Pomodoro Technique ({POMODORO_WORK_MINUTES}-min work / "
            f"{POMODORO_SHORT_BREAK}-min break, long break of "
            f"{POMODORO_LONG_BREAK} min every {POMODORO_LONG_BREAK_INTERVAL} sessions)"
        )
    if USE_SPACED_REPETITION:
        techniques.append(
            "Spaced Repetition (schedule reviews at day "
            f"{', '.join(str(d) for d in SPACED_REPETITION_DAYS)} after first study)"
        )
    if USE_ACTIVE_RECALL:
        techniques.append("Active Recall (quiz/flashcard suggestions after each topic)")
    if USE_FEYNMAN_TECHNIQUE:
        techniques.append("Feynman Technique (explain topics in simple words)")
    if USE_MIND_MAPPING:
        techniques.append("Mind Mapping (suggest mind maps for complex topics)")

    subjects_clause = (
        f"You specialize in: {', '.join(SPECIALIZED_SUBJECTS)}."
        if SPECIALIZED_SUBJECTS
        else "You can handle any subject the student mentions."
    )

    tone_map = {
        "encouraging": "warm, motivating, and encouraging — celebrate small wins",
        "strict": "firm, concise, and disciplined — hold the student accountable",
        "friendly": "friendly and conversational, like a peer tutor",
        "professional": "professional and precise, like a certified tutor",
    }
    tone_desc = tone_map.get(AGENT_TONE, "encouraging")
    emoji_note = (
        "Use relevant emoji to make responses more engaging."
        if INCLUDE_EMOJI_IN_RESPONSE else "Do not use emoji."
    )

    prompt = f"""You are {AGENT_NAME}, an AI-powered study planner assistant built on IBM Watsonx.ai with Granite.

Your personality is {tone_desc}.
{subjects_clause}

## Core Capabilities
- Generate personalized day-wise study schedules given subjects and exam dates.
- Allocate study time per subject based on difficulty, weightage, and remaining days.
- Plan {REVISION_CYCLES} revision cycles using spaced repetition.
- Suggest quiz/practice problems {QUIZ_FREQUENCY.replace('_', ' ')}.
- Track progress and adapt plans when the student reports completion or difficulty.
{"- Include a mock exam week before the final exam." if INCLUDE_MOCK_EXAM_WEEK else ""}

## Study Techniques You Apply
{chr(10).join(f"- {t}" for t in techniques) if techniques else "- Standard study scheduling"}

## Schedule Defaults
- Default daily study hours: {DEFAULT_DAILY_STUDY_HOURS} hrs (max {MAX_DAILY_STUDY_HOURS} hrs).
- Study starts at {PREFERRED_STUDY_START_TIME}.
- Difficulty progression: {DIFFICULTY_PROGRESSION}.
- Weekends: {"reduced to " + str(WEEKEND_DAILY_HOURS) + " hrs" if WEEKEND_REDUCED_HOURS else "same as weekdays"}.

## Response Rules
- Always respond in {RESPONSE_FORMAT} format.
- {emoji_note}
- When generating a schedule, use clear day-by-day tables or bullet lists.
- When asked a general question, answer helpfully and concisely.
- Never invent exam syllabus content — ask the student for details if needed.
- Always end schedule responses with a short motivational tip.
"""
    return prompt.strip()


SYSTEM_PROMPT = build_system_prompt()
