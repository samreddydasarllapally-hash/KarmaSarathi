"""
Full end-to-end planner test.
Run: python -X utf8 test_planner.py
"""

from app.state import StudentState
from app.agents.planner import planner_node

STEPS = [
    # Phase 1 — Goal
    ("Goal",              "Semester Exam"),
    # Phase 2 — Deadline + Routine
    ("Deadline",          "10 days"),
    ("Wake time",         "6 AM"),
    ("Sleep time",        "11 PM"),
    # Routine detail sub-steps (9 prompts from ROUTINE_PROMPTS)
    ("Breakfast",         "7:30 AM"),
    ("Lunch",             "1 PM"),
    ("Dinner",            "8 PM"),
    ("College hours",     "9am-4pm"),
    ("Gym",               "no"),
    ("Travel",            "30 min"),
    ("Prayer",            "no"),
    ("Fixed activities",  "no"),
    ("Water interval",    "every 2 hours"),
    # Phase 3 — Goal specific
    ("Goal specific",     "1. DS, DBMS, OS\n2. OS\n3. 2"),
    # Phase 4 — Subjects
    ("Subjects",          "DS 8 4/5, DBMS 6 2/4, OS 3 1/5"),
    # Phase 5 — Syllabus method (1=paste, 2=manual, 3=upload, 4=generate)
    ("Syllabus method",   "1"),
    # Phase 6 — Syllabus input (paste format: Subject: topic1, topic2)
    ("Syllabus input",
     "DS: Arrays, Stacks, Queues, Trees, Graphs\n"
     "DBMS: ER Model, Normalization, Transactions, SQL Queries, Indexing\n"
     "OS: CPU Scheduling, Deadlocks, Memory Management, Virtual Memory, File Systems"),
    # Phase 7 — Completed topics
    ("Completed topics",  "DS: Arrays, Stacks\nDBMS: ER Model"),
    # Phase 8 — Study style
    ("Focus duration",    "45 min"),
    ("Break duration",    "10"),
    ("Productivity peak", "Morning"),
    # Phase 9 — Energy
    ("Energy peak",       "Morning"),
    # Phase 10 — Learning style
    ("Learning style",    "Videos"),
    # analyze + create_strategy + create_learning_path run automatically
    # Phase 11 — Review: adjust then confirm
    ("Review — adjust",   "I want more DBMS practice"),
    ("Review — confirm",  "yes"),
]

SEP = "-" * 60


def run():
    state = StudentState().model_dump()

    for label, message in STEPS:
        print(f"\n{SEP}")
        print(f"[USER — {label}]: {message[:80]}{'...' if len(message) > 80 else ''}")

        state["user_message"] = message
        if state.get("planner_stage") and state["planner_stage"] != "done":
            state["intent"] = "planner"

        state = planner_node(state)

        stage = state.get("planner_stage")
        response = state.get("agent_response", "")
        print(f"[STAGE]: {stage}")
        print(f"[BOT]:\n{response}")

        if stage == "done":
            _print_results(state)
            return

    # If we ran out of steps before done
    final_stage = state.get("planner_stage")
    if final_stage != "done":
        print(f"\n{SEP}")
        print(f"[NOTE] Ran out of test steps. Final stage: {final_stage}")
        print("[SUBJECTS & TOPICS]:")
        for s in state.get("subjects", []):
            pending = [t["title"] for t in s.get("topics", []) if t.get("status") != "done"]
            done = [t["title"] for t in s.get("topics", []) if t.get("status") == "done"]
            print(f"  {s['name']}: pending={pending} | done={done}")
        print(f"\n[ROUTINE]: {state.get('routine', {})}")
        print(f"[LEARNING STYLE]: {state.get('learning_style')}")
        print(f"[SYLLABUS METHOD]: {state.get('syllabus_method')}")
        print(f"[LEARNING PATH]: {len(state.get('learning_path', []))} items")


def _print_results(state):
    print(f"\n{SEP}")
    print("[TASKS GENERATED]:")
    for t in state.get("tasks", []):
        subj = t.get("subject", "")
        topic = t.get("topic", "")
        reason = f" — {t['reason']}" if t.get("reason") else ""
        label_str = f"[{subj} / {topic}]" if topic else f"[{subj}]"
        print(
            f"  [{t.get('priority','?')}] {t['title']} "
            f"({t['duration_minutes']} min, {t['type']}) {label_str}{reason}"
        )

    print(f"\n[STRUCTURED STRATEGY]:")
    for k, v in state.get("structured_strategy", {}).items():
        print(f"  {k}: {v}")

    print(f"\n[ROUTINE COLLECTED]:")
    for k, v in state.get("routine", {}).items():
        print(f"  {k}: {v}")

    print(f"\n[LEARNING PATH] ({len(state.get('learning_path', []))} items):")
    for item in state.get("learning_path", []):
        status = "done" if item.get("status") == "done" else "pending"
        print(f"  [{item['learning_order']}] {item['subject']} → {item['title']} ({item['difficulty']}, {item['estimated_minutes']} min) [{status}]")


if __name__ == "__main__":
    run()
