"""
Test: Inter-Agent Network — all 6 handoff directions
Run: python test_network.py
"""
import json
from app.graph import karma_graph
from app.state import StudentState

SEP  = "─" * 65
HEAD = "═" * 65

def send(state: dict, msg: str, label: str = "") -> dict:
    from datetime import date
    state["today_date"] = date.today().isoformat()
    state["user_message"] = msg
    result = karma_graph.invoke(state)
    tag = f"[{label}] " if label else ""
    print(f"\n{SEP}")
    print(f"USER  : {msg}")
    print(f"INTENT: {result.get('intent')}  |  stage: {result.get('planner_stage')}  |  loop: {result.get('daily_loop_stage')}")
    if result.get("agent_handoff"):
        print(f"HANDOFF→ {result['agent_handoff']}")
    if result.get("return_to_agent"):
        print(f"RETURN← {result['return_to_agent']}")
    print(f"BOT   :\n{result.get('agent_response','')[:400]}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1 — Research Mode 2: Idea-First (no planner needed)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{HEAD}")
print("TEST 1 — Research Mode 2: Idea-First Entry")
print(HEAD)

state = StudentState().model_dump()
state["planner_stage"] = "done"
state["tasks"] = []

state = send(state, "I want to build a crop monitoring drone", "Idea-First")

# Check workspace created
ws = state.get("research_workspace", [])
print(f"\n✓ Workspace entries: {len(ws)}")
if ws:
    w = ws[0]
    print(f"  Title   : {w.get('title')}")
    print(f"  Missing : {w.get('missing_skills', [])[:3]}")
    print(f"  Known   : {w.get('known_skills', [])[:3]}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2 — Research → Planner handoff (option 1: build roadmap)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{HEAD}")
print("TEST 2 — Research → Planner Handoff")
print(HEAD)

state = send(state, "1", "Research→Planner")
print(f"\n✓ Intent after selecting '1': {state.get('intent')}")
print(f"  return_to_agent: {state.get('return_to_agent')}")
print(f"  goal set to    : {state.get('goal')}")
print(f"  planner_stage  : {state.get('planner_stage')}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3 — Research → Learner handoff (option 2: teach first skill)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{HEAD}")
print("TEST 3 — Research → Learner Handoff")
print(HEAD)

state2 = StudentState().model_dump()
state2["planner_stage"] = "done"
state2["tasks"] = []

state2 = send(state2, "I want to build a flood detection system using satellite images", "Idea")
state2 = send(state2, "2", "Research→Learner")

print(f"\n✓ Intent after selecting '2': {state2.get('intent')}")
print(f"  return_to_agent: {state2.get('return_to_agent')}")
lo = state2.get("learner_output", {})
print(f"  Learner topic  : {lo.get('topic', 'N/A')}")
print(f"  SVG generated  : {'yes' if lo.get('svg') else 'no'}")
print(f"  MCQs           : {len(lo.get('mcqs', []))}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4 — Learner → Research return
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{HEAD}")
print("TEST 4 — Learner → Research Return (continue research)")
print(HEAD)

state2 = send(state2, "continue research", "Learner→Research return")
print(f"\n✓ Intent: {state2.get('intent')}")
print(f"  return_to_agent after return: {state2.get('return_to_agent')}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5 — Progress → Research (post-mastery offer)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{HEAD}")
print("TEST 5 — Progress → Research (Post-Mastery Offer)")
print(HEAD)

state3 = StudentState().model_dump()
state3["planner_stage"] = "done"
state3["subjects"] = [{"name": "OS", "confidence": 6}]
state3["tasks"] = [
    {
        "id": 1, "title": "Study CPU Scheduling", "subject": "OS",
        "topic": "CPU Scheduling", "type": "learning",
        "duration_minutes": 45, "priority": "high",
        "difficulty": "medium", "energy": "high",
        "status": "active", "reason": "Core OS topic",
        "depends_on": [], "recommended_resource_type": "explanation",
    }
]
state3["active_task_id"] = 1
state3["daily_loop_stage"] = "ask_completion"

# Complete task
state3 = send(state3, "1", "Complete")        # Yes, completed
state3 = send(state3, "4", "Rate 4/5")        # Rating 4 → sets offer_research

print(f"\n✓ offer_research flag on task: {state3['tasks'][0].get('offer_research', False)}")
print(f"  daily_loop_stage: {state3.get('daily_loop_stage')}")

# Orchestrator should now see offer_research and route to progress for post-mastery
state3 = send(state3, "next", "Post-mastery trigger")
print(f"\n✓ Post-mastery stage: {state3.get('daily_loop_stage')}")

# Choose option 2 → Research
state3 = send(state3, "2", "Choose Research")
print(f"\n✓ Intent: {state3.get('intent')}")
print(f"  agent_handoff: {state3.get('agent_handoff')}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6 — Learner bridge during active task (diagram request)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{HEAD}")
print("TEST 6 — Learner Bridge During Active Task")
print(HEAD)

state4 = StudentState().model_dump()
state4["planner_stage"] = "done"
state4["subjects"] = [{"name": "DBMS", "confidence": 5}]
state4["tasks"] = [
    {
        "id": 1, "title": "Study Normalization", "subject": "DBMS",
        "topic": "Normalization", "type": "learning",
        "duration_minutes": 45, "priority": "high",
        "difficulty": "medium", "energy": "medium",
        "status": "active", "reason": "Core DBMS topic",
        "depends_on": [], "recommended_resource_type": "explanation",
    }
]
state4["active_task_id"] = 1
state4["daily_loop_stage"] = "ask_completion"
state4["learning_style"] = "videos"

state4 = send(state4, "show me a diagram", "Bridge trigger")
lo4 = state4.get("learner_output", {})
print(f"\n✓ Learner triggered during task: {state4.get('intent') == 'learner'}")
print(f"  Topic    : {lo4.get('topic', 'N/A')}")
print(f"  SVG      : {'yes' if lo4.get('svg') else 'no'}")
print(f"  active_task_id preserved: {state4.get('active_task_id')}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 7 — Research Mode 1: Exploration after learning
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{HEAD}")
print("TEST 7 — Research Mode 1: Exploration After Learning")
print(HEAD)

state5 = StudentState().model_dump()
state5["planner_stage"] = "done"
state5["subjects"] = [{"name": "ML", "confidence": 7}]
state5["tasks"] = [
    {"id": 1, "title": "Study CNN", "subject": "ML", "topic": "CNN",
     "type": "learning", "status": "completed", "duration_minutes": 45,
     "priority": "high", "difficulty": "medium", "energy": "high",
     "depends_on": [], "recommended_resource_type": "explanation",
     "understanding_rating": 5}
]

state5 = send(state5, "explore CNN applications", "Mode 1 Exploration")
ro = state5.get("research_output", {})
print(f"\n✓ Research output keys: {list(ro.keys())[:3]}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 8 — Research workspace command
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{HEAD}")
print("TEST 8 — Research Workspace View")
print(HEAD)

state5 = send(state5, "workspace", "Workspace view")


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{HEAD}")
print("ALL TESTS COMPLETE")
print(HEAD)
print("""
Handoffs tested:
  ✓ Research → Planner  (idea → build roadmap)
  ✓ Research → Learner  (idea → teach missing skill)
  ✓ Learner  → Research (continue after learning)
  ✓ Progress → Research (post-mastery offer)
  ✓ Progress → Learner  (bridge: diagram during task)
  ✓ Research Mode 1     (exploration after learning)
  ✓ Research Workspace  (persistent project notebook)
""")
