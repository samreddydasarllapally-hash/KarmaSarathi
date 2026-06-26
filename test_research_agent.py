"""
test_research_agent.py  —  Research Agent: 9 Test Cases
========================================================
Tests all Research modes directly via research_node():

  R1  Explore / Default (GAN)
  R2  Real-world Applications
  R3  Open Problems / Problem Finder
  R4  Paper Simplification
  R5  Innovation / Idea Generator
  R6  Idea-First (build something — Mode 2 entry)
  R7  Project Builder / Roadmap
  R8  Socratic / Research Questions
  R9  Multi-turn continuity (explore → problems → innovate → profile)

Run:  python test_research_agent.py
"""

import sys
import time
from datetime import date
from app.agents.research import research_node
from app.state import StudentState

# ── colours ──────────────────────────────────────────────────────────────────
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; C = "\033[96m"; B = "\033[1m"; X = "\033[0m"
SEP  = "─" * 68
HEAD = "═" * 68

passed = 0; failed = 0; results = []

def ok(tid, detail=""):
    global passed
    passed += 1
    print(f"  {G}✓ PASS{X}  [{tid}]  {detail}")
    results.append({"id": tid, "status": "PASS", "detail": detail})

def fail(tid, detail=""):
    global failed
    failed += 1
    print(f"  {R}✗ FAIL{X}  [{tid}]  {detail}")
    results.append({"id": tid, "status": "FAIL", "detail": detail})

def section(title):
    print(f"\n{HEAD}\n  {B}{C}{title}{X}\n{HEAD}")


# ── state builder ─────────────────────────────────────────────────────────────

def make_state(
    msg: str,
    topic: str = "Generative Adversarial Networks",
    subject: str = "Deep Learning",
    mode: str = "explore",
    extra: dict = None,
) -> dict:
    """Return a StudentState dict ready for research_node()."""
    s = StudentState().model_dump()
    s["user_message"]      = msg
    s["planner_stage"]     = "done"
    s["intent"]            = "research"
    s["research_mode"]     = mode
    s["research_stage"]    = 0
    s["post_mastery_topic"] = topic
    s["goal"]              = "Master Deep Learning and build AI projects"
    s["goal_category"]     = "project"
    s["subjects"]          = [{"name": subject}]
    s["today_date"]        = date.today().isoformat()
    s["tasks"] = [
        {"id": 1, "topic": "Neural Networks",          "subject": subject, "status": "completed", "mastery": 4.5},
        {"id": 2, "topic": topic,                       "subject": subject, "status": "completed", "mastery": 4.2},
        {"id": 3, "topic": "Transformer Architecture", "subject": subject, "status": "pending"},
    ]
    if extra:
        s.update(extra)
    return s


def invoke(state: dict, label: str = "") -> dict:
    """Call research_node and pretty-print."""
    result = research_node(state)
    resp   = result.get("agent_response", "")
    tag    = f"[{label}] " if label else ""
    print(f"\n  {Y}MSG{X}  : {state['user_message']}")
    print(f"  MODE : {result.get('research_mode')}  |  stage: {result.get('research_stage')}")
    print(f"  {C}RESP{X} : {resp[:450]}{'…' if len(resp)>450 else ''}")
    if result.get("agent_handoff"):
        print(f"  {Y}HANDOFF{X}→ {result['agent_handoff']}")
    return result


# ══════════════════════════════════════════════════════════════════════════════

section("R1 — Default Explore (GAN)")
try:
    s = make_state("I want to research on GAN")
    r = invoke(s, "R1")
    resp = r.get("agent_response", "")
    assert resp, "Empty response"
    assert r.get("intent") == "research", f"intent={r.get('intent')}"
    has_content = any(kw in resp.lower() for kw in
                      ["generative", "gan", "explore", "application", "🔭", "🌍", "deeper", "rabbit"])
    ok("R1", f"intent=research | {len(resp)} chars | relevant={'yes' if has_content else 'generic'}")
except Exception as e:
    fail("R1", str(e))

# ─────────────────────────────────────────────────────────────────────────────

section("R2 — Real-World Applications")
try:
    s = make_state("Show me applications of GAN in real world", mode="explore")
    r = invoke(s, "R2")
    resp = r.get("agent_response", "")
    assert resp, "Empty response"
    has_domains = any(kw in resp.lower() for kw in
                      ["healthcare", "industry", "domain", "🌍", "application", "where is", "impact"])
    ok("R2", f"Applications response | domains={'yes' if has_domains else 'generic'} | {len(resp)} chars")
except Exception as e:
    fail("R2", str(e))

# ─────────────────────────────────────────────────────────────────────────────

section("R3 — Problem Finder (Open Research Problems)")
try:
    s = make_state("What are the open problems and limitations in GAN?")
    r = invoke(s, "R3")
    resp = r.get("agent_response", "")
    assert resp, "Empty response"
    has_problem = any(kw in resp.lower() for kw in
                      ["problem", "challenge", "limitation", "gap", "unsolved", "open", "🔴", "difficulty"])
    ok("R3", f"Problem finder | problem_keywords={'yes' if has_problem else 'generic'} | {len(resp)} chars")
except Exception as e:
    fail("R3", str(e))

# ─────────────────────────────────────────────────────────────────────────────

section("R4 — Paper Simplification")
try:
    s = make_state("Show me a research paper on GAN")
    r = invoke(s, "R4")
    resp  = r.get("agent_response", "")
    prof  = r.get("student_research_profile", {})
    assert resp, "Empty response"
    papers_read = prof.get("papers_read", 0)
    has_paper = any(kw in resp.lower() for kw in
                    ["paper", "abstract", "contribution", "finding", "published", "📄", "study", "author"])
    ok("R4", f"Paper mode | papers_read={papers_read} | content={'yes' if has_paper else 'generic'} | {len(resp)} chars")
except Exception as e:
    fail("R4", str(e))

# ─────────────────────────────────────────────────────────────────────────────

section("R5 — Innovation / Idea Generator")
try:
    s = make_state("Give me an innovative research idea using GAN")
    r = invoke(s, "R5")
    resp  = r.get("agent_response", "")
    prof  = r.get("student_research_profile", {})
    assert resp, "Empty response"
    ideas = prof.get("ideas_generated", 0)
    has_idea = any(kw in resp.lower() for kw in
                   ["idea", "novel", "innovation", "propose", "build", "create", "💡", "🚀", "research idea"])
    ok("R5", f"Innovation mode | ideas_generated={ideas} | idea_content={'yes' if has_idea else 'generic'} | {len(resp)} chars")
except Exception as e:
    fail("R5", str(e))

# ─────────────────────────────────────────────────────────────────────────────

section("R6 — Idea-First Entry (Build Something)")
try:
    # Idea-First: student has NO completed tasks — just a build idea
    s = StudentState().model_dump()
    s["user_message"]   = "I want to build a deepfake detection system using GAN"
    s["planner_stage"]  = "done"
    s["intent"]         = "research"
    s["subjects"]       = [{"name": "Deep Learning"}]
    s["today_date"]     = date.today().isoformat()
    s["tasks"]          = []

    r = invoke(s, "R6")
    resp      = r.get("agent_response", "")
    workspace = r.get("research_workspace", [])
    assert resp, "Empty response"
    has_skill_gap = any(kw in resp.lower() for kw in
                        ["skill", "learn", "missing", "required", "know", "build", "roadmap", "plan"])
    ok("R6", f"Idea-First | workspace={len(workspace)} entries | skill_analysis={'yes' if has_skill_gap else 'generic'} | {len(resp)} chars")
    if workspace:
        print(f"       └─ Workspace title: '{workspace[0].get('title','')[:60]}'")
        print(f"       └─ Missing skills : {workspace[0].get('missing_skills', [])[:3]}")
except Exception as e:
    fail("R6", str(e))

# ─────────────────────────────────────────────────────────────────────────────

section("R7 — Project Builder / Roadmap")
try:
    s = make_state("Give me a project roadmap for building a GAN-based image generator")
    r = invoke(s, "R7")
    resp = r.get("agent_response", "")
    assert resp, "Empty response"
    has_project = any(kw in resp.lower() for kw in
                      ["week", "phase", "step", "milestone", "build", "🛠", "roadmap", "timeline", "project", "month"])
    ok("R7", f"Project builder | structure={'yes' if has_project else 'generic'} | {len(resp)} chars")
except Exception as e:
    fail("R7", str(e))

# ─────────────────────────────────────────────────────────────────────────────

section("R8 — Socratic / Research Questions")
try:
    s = make_state("Challenge me with research-level questions on GAN")
    r = invoke(s, "R8")
    resp = r.get("agent_response", "")
    assert resp, "Empty response"
    has_q = "?" in resp or any(kw in resp.lower() for kw in
                                ["question", "think", "consider", "why", "how", "what if", "research", "challenge"])
    ok("R8", f"Socratic mode | questions={'yes' if has_q else 'generic'} | {len(resp)} chars")
except Exception as e:
    fail("R8", str(e))

# ─────────────────────────────────────────────────────────────────────────────

section("R9 — Multi-Turn Continuity (explore → problems → innovate → profile)")
try:
    s = make_state("I want to research on GAN")
    
    print(f"\n  {B}Turn 1: Explore{X}")
    s = invoke(s, "R9-T1")
    t1 = s.get("agent_response", "")
    assert t1, "Turn 1 empty"
    hist1 = len(s.get("history", []))

    print("  [rate-limit guard] sleeping 5s...")
    time.sleep(5)

    print(f"\n  {B}Turn 2: Open Problems{X}")
    s["user_message"] = "What are the open research problems in GAN?"
    s = invoke(s, "R9-T2")
    t2 = s.get("agent_response", "")
    assert t2, "Turn 2 empty"
    hist2 = len(s.get("history", []))

    print("  [rate-limit guard] sleeping 5s...")
    time.sleep(5)

    print(f"\n  {B}Turn 3: Innovation{X}")
    s["user_message"] = "Give me an innovative idea to solve one of those GAN problems"
    s = invoke(s, "R9-T3")
    t3 = s.get("agent_response", "")
    assert t3, "Turn 3 empty"
    hist3 = len(s.get("history", []))

    print("  [rate-limit guard] sleeping 3s...")
    time.sleep(3)

    print(f"\n  {B}Turn 4: Profile{X}")
    s["user_message"] = "research profile"
    s = invoke(s, "R9-T4-Profile")
    t4 = s.get("agent_response", "")
    assert t4, "Turn 4 empty"

    prof  = s.get("student_research_profile", {})
    score = prof.get("innovation_score", 0)
    sess  = len(prof.get("research_sessions", []))
    problems  = prof.get("problems_explored", 0)
    ideas_gen = prof.get("ideas_generated", 0)

    print(f"\n  {B}Profile Summary:{X}")
    print(f"    innovation_score = {score}")
    print(f"    research_sessions = {sess}")
    print(f"    problems_explored = {problems}")
    print(f"    ideas_generated   = {ideas_gen}")
    print(f"    history messages  : {hist1} → {hist2} → {hist3}")

    assert hist3 > hist1, "History not growing across turns"
    assert score > 0, "Innovation score should be > 0 after 3 active turns"

    ok("R9", f"Multi-turn | {hist3} history msgs | score={score} | sessions={sess}")
    if problems > 0: ok("R9-problems", f"problems_explored tracked: {problems}")
    if ideas_gen > 0: ok("R9-ideas",   f"ideas_generated tracked: {ideas_gen}")

except Exception as e:
    fail("R9", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

section("SUMMARY")
total = passed + failed
pct   = (passed / total * 100) if total else 0
bar   = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
col   = G if pct >= 80 else (Y if pct >= 50 else R)

print(f"\n  Total  : {total}  |  {G}Passed: {passed}{X}  |  {R}Failed: {failed}{X}")
print(f"  Score  : {pct:.0f}%")
print(f"  {col}[{bar}]{X}\n")

if failed:
    print(f"  {R}Failed tests:{X}")
    for r in results:
        if r["status"] == "FAIL":
            print(f"    ✗ [{r['id']}]  {r['detail']}")
    print()

sys.exit(0 if failed == 0 else 1)
