"""
test_r9_only.py  —  R9 Multi-turn test only (with rate-limit guards)
"""
import sys, time
from datetime import date
from app.agents.research import research_node
from app.state import StudentState

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; C = "\033[96m"; B = "\033[1m"; X = "\033[0m"
HEAD = "=" * 68

def section(t): print(f"\n{HEAD}\n  {B}{C}{t}{X}\n{HEAD}")
def ok(tid, d=""): print(f"  {G}PASS{X}  [{tid}]  {d}")
def fail(tid, d=""): print(f"  {R}FAIL{X}  [{tid}]  {d}"); sys.exit(1)

def make_state(msg, topic="Generative Adversarial Networks", subject="Deep Learning"):
    s = StudentState().model_dump()
    s["user_message"] = msg
    s["planner_stage"] = "done"
    s["intent"] = "research"
    s["research_mode"] = "explore"
    s["post_mastery_topic"] = topic
    s["subjects"] = [{"name": subject}]
    s["today_date"] = date.today().isoformat()
    s["tasks"] = [
        {"id": 1, "topic": "Neural Networks", "subject": subject, "status": "completed", "mastery": 4.5},
        {"id": 2, "topic": topic, "subject": subject, "status": "completed", "mastery": 4.2},
    ]
    return s

def invoke(state, label=""):
    result = research_node(state)
    resp = result.get("agent_response", "")
    print(f"\n  {Y}MSG{X}  : {state['user_message']}")
    print(f"  MODE : {result.get('research_mode')}  |  stage: {result.get('research_stage')}")
    print(f"  {C}RESP{X} : {resp[:400]}{'...' if len(resp)>400 else ''}")
    return result

section("R9 -- Multi-Turn (explore -> problems -> innovate -> profile)")
try:
    s = make_state("I want to research on GAN")

    print(f"\n  {B}Turn 1: Explore{X}")
    s = invoke(s, "T1")
    assert s.get("agent_response"), "T1 empty"
    h1 = len(s.get("history", []))

    print("\n  [guard] 6s sleep...")
    time.sleep(6)

    print(f"\n  {B}Turn 2: Open Problems{X}")
    s["user_message"] = "What are the open research problems in GAN?"
    s = invoke(s, "T2")
    assert s.get("agent_response"), "T2 empty"
    h2 = len(s.get("history", []))

    print("\n  [guard] 6s sleep...")
    time.sleep(6)

    print(f"\n  {B}Turn 3: Innovation{X}")
    s["user_message"] = "Give me an innovative idea to solve one of those GAN problems"
    s = invoke(s, "T3")
    assert s.get("agent_response"), "T3 empty"
    h3 = len(s.get("history", []))

    print("\n  [guard] 3s sleep...")
    time.sleep(3)

    print(f"\n  {B}Turn 4: Profile{X}")
    s["user_message"] = "research profile"
    s = invoke(s, "T4")
    assert s.get("agent_response"), "T4 empty"

    prof  = s.get("student_research_profile", {})
    score = prof.get("innovation_score", 0)
    sess  = len(prof.get("research_sessions", []))
    probs = prof.get("problems_explored", 0)
    ideas = prof.get("ideas_generated", 0)

    print(f"\n  {B}--- Profile Summary ---{X}")
    print(f"    innovation_score  = {score}")
    print(f"    research_sessions = {sess}")
    print(f"    problems_explored = {probs}")
    print(f"    ideas_generated   = {ideas}")
    print(f"    history growth    : {h1} -> {h2} -> {h3}")

    assert h3 > h1, "History not growing"
    assert score > 0, "Innovation score not tracking"

    ok("R9", f"Multi-turn OK | history={h3} | score={score} | sessions={sess}")
    if probs > 0: ok("R9-problems", f"problems_explored={probs}")
    if ideas > 0: ok("R9-ideas",   f"ideas_generated={ideas}")

except Exception as e:
    fail("R9", str(e))
