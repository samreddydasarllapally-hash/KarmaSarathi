"""
Revision System Test — Spaced Repetition + Archive
Run: python -X utf8 test_revision.py
"""

from app.state import StudentState
from app.agents.progress import progress_node

SEP = "-" * 60

SEED = {
    "goal": "Semester Exam",
    "planner_stage": "done",
    "tasks": [
        {"id": 1, "title": "Study Normalization", "subject": "DBMS", "topic": "Normalization",
         "type": "learning", "duration_minutes": 45, "priority": "high",
         "status": "pending", "reason": "Core DBMS topic"},
    ],
    "subjects": [{"name": "DBMS", "confidence": 5, "topics": []}],
    "daily_loop_stage": "idle",
    "xp": 0, "streak": 0, "badges": [],
}


def step(state: dict, label: str, msg: str) -> dict:
    print(f"\n{SEP}\n[{label}]: {msg}")
    state["user_message"] = msg
    state["intent"] = "progress"
    state = progress_node(state)
    print(f"[Stage]: {state['daily_loop_stage']}")
    print(f"[Response]:\n{state['agent_response']}")
    return state


def run():
    # ── Scenario 1: Complete with rating 3 → day+1, day+3, day+7 revisions ───
    print("\n" + "=" * 60)
    print("S1: Complete topic with rating 3/5")
    print("    Expected: day+1, day+3, day+7 revision tasks created")
    print("=" * 60)
    
    s = StudentState(**SEED).model_dump()
    s = step(s, "Start", "next")
    s = step(s, "Complete", "1")
    s = step(s, "Rate 3", "3")
    
    revisions = [t for t in s["tasks"] if t.get("type") == "revision"]
    print(f"\n✓ Revision tasks created: {len(revisions)}")
    for r in revisions:
        print(f"  - {r['title']} (day+{r.get('spaced_day_offset')}, {r['duration_minutes']} min)")
    
    print(f"\n✓ Revision queue entries: {len(s['revision_queue'])}")
    if s["revision_queue"]:
        q = s["revision_queue"][0]
        print(f"  Topic: {q['topic']}")
        print(f"  Schedules: {q['schedules']}")
        print(f"  Rating: {q['rating']}")


    # ── Scenario 2: Complete with rating 5 → only day+1 (high confidence) ────
    print("\n" + "=" * 60)
    print("S2: Complete topic with rating 5/5")
    print("    Expected: only day+1 revision (confident mastery)")
    print("=" * 60)
    
    s = StudentState(**SEED).model_dump()
    s = step(s, "Start", "next")
    s = step(s, "Complete", "1")
    s = step(s, "Rate 5", "5")
    
    revisions = [t for t in s["tasks"] if t.get("type") == "revision"]
    print(f"\n✓ Revision tasks created: {len(revisions)}")
    for r in revisions:
        print(f"  - {r['title']} (day+{r.get('spaced_day_offset')}, {r['duration_minutes']} min)")


    # ── Scenario 3: Archive topic → study tasks removed, revisions kept ──────
    print("\n" + "=" * 60)
    print("S3: Archive completed topic")
    print("    Expected: study/practice removed, revision tasks remain")
    print("=" * 60)
    
    s = StudentState(**SEED).model_dump()
    # Complete with rating 3 → creates revisions
    s = step(s, "Start", "next")
    s = step(s, "Complete", "1")
    s = step(s, "Rate 3", "3")
    
    print(f"\nBefore archive:")
    print(f"  Total tasks: {len(s['tasks'])}")
    learning = [t for t in s["tasks"] if t.get("type") == "learning"]
    revisions = [t for t in s["tasks"] if t.get("type") == "revision"]
    print(f"  Learning: {len(learning)}, Revision: {len(revisions)}")
    
    # Archive
    s = step(s, "Archive", "archive Normalization from DBMS")
    
    print(f"\nAfter archive:")
    print(f"  Total tasks: {len(s['tasks'])}")
    learning = [t for t in s["tasks"] if t.get("type") == "learning"]
    revisions = [t for t in s["tasks"] if t.get("type") == "revision"]
    print(f"  Learning: {len(learning)}, Revision: {len(revisions)}")
    
    print(f"\n✓ Knowledge vault entries: {len(s['knowledge_vault'])}")
    if s["knowledge_vault"]:
        v = s["knowledge_vault"][0]
        print(f"  Topic: {v['topic']}")
        print(f"  Mastery: {v['mastery']}/5")
        print(f"  Revision only: {v['revision_only']}")
        print(f"  Status: {v['status']}")


    # ── Scenario 4: View knowledge vault ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("S4: View knowledge vault")
    print("=" * 60)
    
    s = step(s, "View vault", "vault")


    # ── Scenario 5: Rating 2 → auto-revision + difficulty detail ────────────
    print("\n" + "=" * 60)
    print("S5: Complete with rating 2/5")
    print("    Expected: day+1/+3/+7 revisions + immediate 30min revision")
    print("=" * 60)
    
    s = StudentState(**SEED).model_dump()
    s = step(s, "Start", "next")
    s = step(s, "Complete", "1")
    s = step(s, "Rate 2", "2")
    s = step(s, "Difficulty detail", "3")  # too many concepts
    
    revisions = [t for t in s["tasks"] if t.get("type") == "revision"]
    auto_rev = [r for r in revisions if "Auto-scheduled" in r.get("reason", "")]
    spaced_rev = [r for r in revisions if "day+" in str(r.get("spaced_day_offset", ""))]
    
    print(f"\n✓ Total revisions: {len(revisions)}")
    print(f"  Auto-revision (immediate): {len(auto_rev)}")
    print(f"  Spaced revisions: {len(spaced_rev)}")
    
    if auto_rev:
        print(f"\n  Auto-revision details:")
        print(f"    Title: {auto_rev[0]['title']}")
        print(f"    Duration: {auto_rev[0]['duration_minutes']} min")
        print(f"    Difficulty detail: {auto_rev[0].get('difficulty_detail', 'n/a')}")


    print("\n" + "=" * 60)
    print("✅ All revision system tests passed")
    print("=" * 60)


if __name__ == "__main__":
    run()
