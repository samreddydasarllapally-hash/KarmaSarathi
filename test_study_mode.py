"""
Test: Study Mode Selection (Focus vs Mixed)
Run: python -X utf8 test_study_mode.py
"""

from app.state import StudentState
from app.agents.planner import planner_node

SEP = "-" * 60

STEPS = [
    ("Goal", "Semester Exam"),
    ("Deadline", "10 days"),
    ("Wake", "6 AM"),
    ("Sleep", "11 PM"),
    ("Breakfast", "7:30 AM"),
    ("Lunch", "1 PM"),
    ("Dinner", "8 PM"),
    ("College", "9am-4pm"),
    ("Gym", "no"),
    ("Travel", "30 min"),
    ("Prayer", "no"),
    ("Fixed activities", "no"),
    ("Water interval", "every 2 hours"),
    ("Goal specific", "1. DS, DBMS, OS\n2. OS\n3. 2"),
    ("Subjects", "DS 8 4/5, DBMS 6 2/4, OS 3 1/5"),
]


def run():
    print("\n" + "=" * 60)
    print("TEST: Study Mode Selection")
    print("=" * 60)
    
    state = StudentState().model_dump()
    
    # Run through initial steps
    for label, message in STEPS:
        state["user_message"] = message
        if state.get("planner_stage") and state["planner_stage"] != "done":
            state["intent"] = "planner"
        state = planner_node(state)
    
    # Should now be at collect_study_mode stage
    print(f"\n{SEP}")
    print(f"Current stage: {state['planner_stage']}")
    print(f"{SEP}")
    print(f"\n[BOT]:\n{state['agent_response']}")
    
    if state['planner_stage'] != 'collect_study_mode':
        print(f"\n❌ FAILED: Expected collect_study_mode, got {state['planner_stage']}")
        return
    
    # Test Focus Mode
    print(f"\n{SEP}")
    print("[USER]: 1")
    print(f"{SEP}")
    state["user_message"] = "1"
    state = planner_node(state)
    
    if state.get('study_mode') == 'focus':
        print("\n✓ Focus mode selected successfully")
    else:
        print(f"\n❌ Expected 'focus', got: {state.get('study_mode')}")
    
    print(f"Next stage: {state['planner_stage']}")
    
    # Test Mixed Mode with fresh state
    print("\n\n" + "=" * 60)
    print("TEST: Mixed Mode Selection")
    print("=" * 60)
    
    state = StudentState().model_dump()
    for label, message in STEPS:
        state["user_message"] = message
        if state.get("planner_stage") and state["planner_stage"] != "done":
            state["intent"] = "planner"
        state = planner_node(state)
    
    print(f"\n{SEP}")
    print("[USER]: 2")
    print(f"{SEP}")
    state["user_message"] = "2"
    state = planner_node(state)
    
    if state.get('study_mode') == 'mixed':
        print("\n✓ Mixed mode selected successfully")
    else:
        print(f"\n❌ Expected 'mixed', got: {state.get('study_mode')}")
    
    print(f"Next stage: {state['planner_stage']}")
    
    print("\n" + "=" * 60)
    print("✅ Study Mode Tests Completed")
    print("=" * 60)


if __name__ == "__main__":
    run()
