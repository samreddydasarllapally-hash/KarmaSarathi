"""
Progress Agent test — all scenarios.
Run: python -X utf8 test_progress.py
"""

from app.state import StudentState
from app.agents.progress import progress_node

SEP = "-" * 60

SEED_TASKS = [
    {"id": 1, "title": "Study CPU Scheduling", "subject": "OS",
     "topic": "CPU Scheduling", "type": "learning", "duration_minutes": 45,
     "priority": "high", "difficulty": "hard", "energy": "high",
     "depends_on": [], "recommended_resource_type": "explanation",
     "status": "pending", "reason": "Weakest subject"},
    {"id": 2, "title": "Study Deadlocks", "subject": "OS",
     "topic": "Deadlocks", "type": "learning", "duration_minutes": 45,
     "priority": "high", "difficulty": "medium", "energy": "high",
     "depends_on": [1], "recommended_resource_type": "explanation",
     "status": "pending", "reason": "Follows CPU Scheduling"},
    {"id": 3, "title": "Study Normalization", "subject": "DBMS",
     "topic": "Normalization", "type": "learning", "duration_minutes": 45,
     "priority": "medium", "difficulty": "medium", "energy": "medium",
     "depends_on": [], "recommended_resource_type": "article",
     "status": "pending", "reason": "DBMS practice needed"},
    {"id": 4, "title": "Practice Normalization", "subject": "DBMS",
     "topic": "Normalization", "type": "practice", "duration_minutes": 30,
     "priority": "medium", "difficulty": "medium", "energy": "medium",
     "depends_on": [3], "recommended_resource_type": "practice",
     "status": "pending", "reason": "Reinforce Normalization"},
]

SEED_SUBJECTS = [
    {"name": "OS",   "confidence": 3, "topics": []},
    {"name": "DBMS", "confidence": 6, "topics": []},
]


def fresh(extra: dict = {}) -> dict:
    s = StudentState(
        goal="Semester Exam", planner_stage="done",
        tasks=[dict(t) for t in SEED_TASKS],
        subjects=[dict(s) for s in SEED_SUBJECTS],
        daily_loop_stage="idle", xp=0, streak=0, badges=[],
    )
    d = s.model_dump()
    d.update(extra)
    return d


def step(state: dict, label: str, msg: str) -> dict:
    print(f"\n{SEP}\n[USER — {label}]: {msg}")
    state["user_message"] = msg
    state["intent"] = "progress"
    state = progress_node(state)
    print(f"[STAGE]: {state['daily_loop_stage']}")
    print(f"[BOT]:\n{state['agent_response']}")
    return state


def run():
    # ── S1: complete + rating 4 (XP breakdown + streak) ──────────────────────
    print("\n" + "=" * 60)
    print("S1: Complete, rate 4/5 — XP breakdown + streak")
    print("=" * 60)
    s = fresh()
    s = step(s, "start",  "next")
    s = step(s, "yes",    "1")
    s = step(s, "rate 4", "4")
    print(f"  → XP={s['xp']}  Streak={s['streak']}  StudyMin={s['total_study_minutes']}")

    # ── S2: complete + rating 2 → difficulty detail stage ────────────────────
    print("\n" + "=" * 60)
    print("S2: Complete, rate 2/5 → ask_difficulty_detail")
    print("=" * 60)
    s = fresh()
    s = step(s, "start",       "next")
    s = step(s, "yes",         "1")
    s = step(s, "rate 2",      "2")      # → ask_difficulty_detail
    s = step(s, "detail",      "1")      # theory → idle
    rev = [t for t in s["tasks"] if t.get("rescheduled")]
    print(f"  → Revision added: {[t['title'] for t in rev]}")
    print(f"  → Difficulty detail: {rev[0].get('difficulty_detail') if rev else 'n/a'}")

    # ── S3: partial 50% ───────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("S3: Partial 50%")
    print("=" * 60)
    s = fresh()
    s = step(s, "start",    "next")
    s = step(s, "partial",  "2")
    s = step(s, "50%",      "2")
    rescheduled = [t for t in s["tasks"] if t.get("rescheduled")]
    print(f"  → Rescheduled: {[(t['title'], t['duration_minutes']) for t in rescheduled]}")

    # ── S4: no → hard → split ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("S4: No — hard → split")
    print("=" * 60)
    s = fresh()
    s = step(s, "start",  "next")
    s = step(s, "no",     "3")
    s = step(s, "hard",   "2")
    split = [t for t in s["tasks"] if "Part" in t.get("title", "")]
    print(f"  → Split: {[(t['id'], t['title'], t['duration_minutes']) for t in split]}")

    # ── S5: no → confused → tutor route ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("S5: No — confused → Tutor route")
    print("=" * 60)
    s = fresh()
    s = step(s, "start",    "next")
    s = step(s, "no",       "3")
    s = step(s, "confused", "5")
    print(f"  → Intent={s['intent']}  current_task={s['current_task']}")

    # ── S6: missed 3 days → sessions halved ──────────────────────────────────
    print("\n" + "=" * 60)
    print("S6: 3 missed days → sessions shortened")
    print("=" * 60)
    s = fresh({"missed_days": 3})
    s = step(s, "start", "next")
    short = [t for t in s["tasks"] if t.get("duration_minutes", 45) <= 25]
    print(f"  → Shortened: {[(t['title'], t['duration_minutes']) for t in short]}")

    # ── S7: roadmap view ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("S7: Roadmap view")
    print("=" * 60)
    s = fresh()
    s["tasks"][0]["status"] = "completed"
    s["tasks"][1]["status"] = "completed"
    s["xp"] = 130
    s["streak"] = 3
    s["badges"] = ["🔥 3-Day Streak", "🏅 First Topic"]
    s = step(s, "roadmap", "roadmap")

    # ── S8: rich summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("S8: Rich summary")
    print("=" * 60)
    s = step(s, "summary", "summary")

    # ── S9: end-of-day ───────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("S9: End-of-day closure")
    print("=" * 60)
    s["total_study_minutes"] = 130
    s = step(s, "goodnight", "good night")

    # ── S10: varied encouragement across multiple completions ────────────────
    print("\n" + "=" * 60)
    print("S10: Varied encouragement (3 completions)")
    print("=" * 60)
    s = fresh()
    for i in range(3):
        s = step(s, f"start {i+1}",  "next")
        s = step(s, f"yes {i+1}",    "yes")
        s = step(s, f"rate 5 ({i+1})", "5")
        print(f"  → encouragement snippet: {s['agent_response'].splitlines()[-1]}")


if __name__ == "__main__":
    run()
