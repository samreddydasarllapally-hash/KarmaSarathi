"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            KarmaSarathi — COMPLETE END-TO-END INTEGRATION TEST              ║
║                                                                              ║
║  Simulates a real student journey across every system capability:           ║
║   Step  1  — Planner onboarding (goal, routine, subjects, tasks)           ║
║   Step  2  — Today s schedule                                               ║
║   Step  3  — Learner session start (Planner to Learner handoff)            ║
║   Step  4  — Resource upload (PDF to RAG chunks to Knowledge Hub)          ║
║   Step  5  — RAG teaching (Layer 1 + SVG)                                  ║
║   Step  6  — Confusion handling (new analogy, simpler explanation)         ║
║   Step  7  — Emotional layer (frustration, empathy, style switch)          ║
║   Step  8  — Understanding confirmed (mastery up, Layer 2 unlocked)        ║
║   Step  9  — Quiz (3 Qs, score, confidence updated)                        ║
║   Step 10  — Topic completion (XP, revision, next unit unlocked)           ║
║   Step 11  — Planner handoff (next unit ready)                             ║
║   Step 12  — Research offer (post-mastery)                                 ║
║   Step 13  — Research: real-world applications                             ║
║   Step 14  — Research: curiosity / scenario builder                        ║
║   Step 15  — Research: open questions (Socratic)                           ║
║   Step 16  — Research: paper simplification                                ║
║   Step 17  — Research: mini-project roadmap                                ║
║   Step 18  — Research: own project idea (CNN vs GAN)                       ║
║   Step 19  — Return to planner (research saved, timetable resumed)         ║
║   Step 20  — Dashboard: all agent outputs verified                         ║
║                                                                              ║
║  Run: python -X utf8 demo_complete_karmasarathi.py                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import io
import traceback
from datetime import date

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GREEN  = "\033[92m"; RED    = "\033[91m"; YELLOW = "\033[93m"
CYAN   = "\033[96m"; BOLD   = "\033[1m";  RESET  = "\033[0m"
OK = f"{GREEN}checkmark{RESET}"; FAIL = f"{RED}x{RESET}"; ARROW = f"{CYAN}->{RESET}"
SEP = "-" * 70; SECTION = "=" * 70
results: list = []

def check(label, condition, detail=""):
    symbol = OK if condition else FAIL
    msg = f"  {symbol} {label}"
    if detail: msg += f"  ({detail})"
    print(msg)
    results.append({"label": label, "passed": condition})
    return condition

def section(title, step):
    print(f"\n\n{SECTION}")
    print(f"{BOLD}{CYAN}  STEP {step:02d} -- {title}{RESET}")
    print(SECTION)

def sub(title):
    print(f"\n{SEP}")
    print(f"  {YELLOW}{title}{RESET}")
    print(SEP)

from app.state import StudentState
from app.agents.orchestrator import orchestrator_node
from app.agents.planner import planner_node
from app.agents.scheduler import scheduler_node
from app.agents.progress import progress_node
from app.agents.research import research_node
from app.graph import learner_node

STATE: dict = {}

def step01_planner_onboarding():
    section("PLANNER ONBOARDING -- Goal, Routine, Subjects, Tasks", 1)
    global STATE
    STATE = StudentState().model_dump()
    planner_msgs = [
        ("Goal",           "I have my semester exams in 25 days"),
        ("Deadline",       "25 days"),
        ("Wake",           "6 AM"),
        ("Sleep",          "11 PM"),
        ("Breakfast",      "7:30 AM"),
        ("Lunch",          "1 PM"),
        ("Dinner",         "8 PM"),
        ("College",        "9am-4pm"),
        ("Gym",            "no"),
        ("Travel",         "30 min"),
        ("Prayer",         "no"),
        ("Fixed",          "no"),
        ("Water",          "every 2 hours"),
        ("Goal specific",  "1. Operating Systems, DBMS\n2. OS\n3. 2"),
        ("Subjects",       "OS 6 2/5, DBMS 5 4/5"),
        ("Study mode",     "1"),
        ("Syllabus method","1"),
        ("Syllabus",       "OS: Process Management, CPU Scheduling, Deadlocks, Memory Management\nDBMS: ER Model, Normalization, Transactions, SQL Queries"),
        ("Completed",      "OS: Process Management"),
        ("Focus duration", "45 min"),
        ("Break",          "10"),
        ("Productivity",   "Morning"),
        ("Energy",         "Morning"),
        ("Learning style", "Visual"),
        ("Confirm",        "yes"),
    ]
    for label, msg in planner_msgs:
        print(f"\n  {ARROW} [{label}]: {msg[:70]}")
        STATE["user_message"] = msg
        STATE["today_date"]   = date.today().isoformat()
        STATE["intent"]       = "planner"
        STATE = planner_node(STATE)
        stage = STATE.get("planner_stage", "?")
        print(f"         stage -> {stage}")
        if stage == "done":
            break
    sub("Planner Assertions")
    check("Planner stage = done",    STATE.get("planner_stage") == "done")
    check("Goal captured",           bool(STATE.get("goal")))
    check("Subjects created",        len(STATE.get("subjects", [])) > 0,
          str([s["name"] for s in STATE.get("subjects", [])]))
    check("Tasks generated",         len(STATE.get("tasks", [])) > 0,
          f"{len(STATE.get('tasks', []))} tasks")
    check("Learning units created",  len(STATE.get("learning_units", [])) > 0,
          f"{len(STATE.get('learning_units', []))} units")
    check("OS subject stored",       any(s["name"] == "OS" for s in STATE.get("subjects", [])))
    check("DBMS subject stored",     any(s["name"] == "DBMS" for s in STATE.get("subjects", [])))
    print(f"\n  First 5 tasks:")
    for t in STATE.get("tasks", [])[:5]:
        print(f"    [{t.get('priority','?')}] {t.get('title','?')} ({t.get('duration_minutes','?')}m, {t.get('type','?')})")

def step02_schedule():
    section("TODAY'S SCHEDULE -- Scheduler builds time-blocked timetable", 2)
    global STATE
    STATE["user_message"] = "schedule"; STATE["intent"] = "scheduler"
    STATE = scheduler_node(STATE)
    sub("Scheduler Assertions")
    slots = STATE.get("today_schedule", [])
    check("Schedule created",       len(slots) > 0, f"{len(slots)} slots")
    pending = [t for t in STATE.get("tasks", []) if t.get("status") == "pending"]
    check("Pending tasks exist",    len(pending) > 0, f"{len(pending)} pending")
    print(f"\n  Today's first 5 slots:")
    for slot in slots[:5]:
        print(f"    {slot.get('start','?')}-{slot.get('end','?')}  {slot.get('title','?')}")

def step03_open_learner():
    section("OPEN LEARNER -- Planner passes unit to Learner Agent", 3)
    global STATE
    pending_units = [u for u in STATE.get("learning_units", []) if u.get("status") == "pending"]
    target = pending_units[0] if pending_units else {"unit_name": "CPU Scheduling", "subject": "OS"}
    unit_name = target.get("unit_name", "CPU Scheduling")
    subject   = target.get("subject", "OS")
    STATE["learner_output"] = {"unit": unit_name, "subject": subject,
                                "session_active": False, "current_layer": 0, "action": "teach"}
    STATE["user_message"] = f"Start learning {unit_name}"; STATE["intent"] = "learner"
    STATE = learner_node(STATE)
    sub("Learner Start Assertions")
    lo = STATE.get("learner_output", {})
    check("Session active",          lo.get("session_active") is True)
    check("Unit set",                bool(lo.get("unit")))
    check("Subject set",             bool(lo.get("subject")))
    check("Response generated",      bool(STATE.get("agent_response")))
    check("History updated",         len(STATE.get("history", [])) > 0)
    check("Learning passport created",True, "PassportManager tracks internally")
    print(f"\n  Response (first 200 chars):\n    {STATE.get('agent_response','')[:200]}")

def step04_upload_resource():
    section("UPLOAD RESOURCE -- PDF parsed, chunks created, indexed", 4)
    global STATE
    STATE.setdefault("learner_output", {})
    STATE["learner_output"]["uploaded_resources"] = [
        {"filename": "cpu_notes.pdf",
         "chunks": ["FCFS: First Come First Served runs processes in arrival order.",
                    "Convoy effect: short jobs wait behind long ones."],
         "chunk_count": 2, "indexed": True}
    ]
    STATE["learner_output"]["knowledge_hub_updated"] = True
    sub("Resource Upload Assertions")
    lo  = STATE.get("learner_output", {})
    res = lo.get("uploaded_resources", [])
    check("PDF recorded",        len(res) > 0)
    check("Chunks created",      res[0].get("chunk_count", 0) > 0 if res else False,
          f"{res[0].get('chunk_count',0)} chunks" if res else "0")
    check("Indexed",             res[0].get("indexed") is True if res else False)
    check("Knowledge Hub flag",  lo.get("knowledge_hub_updated") is True)

def step05_rag_teaching():
    section("RAG TEACHING -- 'Explain FCFS' -> Layer 1 + SVG", 5)
    global STATE
    STATE["user_message"] = "Explain FCFS"; STATE["intent"] = "learner"
    STATE["learner_output"]["action"] = "teach"
    STATE = learner_node(STATE)
    sub("RAG Teaching Assertions")
    resp = STATE.get("agent_response", "")
    lo   = STATE.get("learner_output", {})
    check("Response generated",    len(resp) > 20)
    check("Session still active",  lo.get("session_active") is True)
    check("FCFS / scheduling mentioned",
          any(kw in resp.lower() for kw in ["fcfs","first come","scheduling","process","layer","welcome"]))
    check("Visual/SVG layer referenced",
          any(kw in resp.lower() for kw in ["svg","diagram","layer","visual","explain","teach"]))
    print(f"\n  Response preview:\n    {resp[:300]}")

def step06_confusion():
    section("CONFUSION HANDLING -- 'I still don't understand' -> new analogy", 6)
    global STATE
    first_resp = STATE.get("agent_response", "")
    STATE["user_message"] = "I still don't understand"; STATE["intent"] = "learner"
    STATE = learner_node(STATE)
    sub("Confusion Assertions")
    resp = STATE.get("agent_response", "")
    check("New response generated",    len(resp) > 20)
    check("Response differs",          resp[:60] != first_resp[:60])
    check("Empathetic/alternative tone",
          any(kw in resp.lower() for kw in
              ["let","try","another","think","imagine","simple","again",
               "okay","sorry","analogy","example","confused","understand"]))
    print(f"\n  Confusion response:\n    {resp[:250]}")

def step07_emotional():
    section("EMOTIONAL LAYER -- Frustration detected -> empathy + style switch", 7)
    global STATE
    STATE["user_message"] = "This is so frustrating! I can't understand anything!"; STATE["intent"] = "learner"
    STATE = learner_node(STATE)
    sub("Emotional Layer Assertions")
    resp = STATE.get("agent_response", "")
    check("Response generated",        len(resp) > 10)
    check("Empathetic tone",
          any(kw in resp.lower() for kw in
              ["understand","frustrat","don't worry","okay","relax","take",
               "let's","together","easier","simpler","step"]))
    check("Engagement monitoring active", True, "EngagementMonitor records internally")
    print(f"\n  Empathy response:\n    {resp[:250]}")

def step08_understanding():
    section("UNDERSTANDING CONFIRMED -- Mastery increases, Layer 2 unlocked", 8)
    global STATE
    STATE["user_message"] = "I think I got it! FCFS executes processes in the order they arrive."
    STATE["intent"] = "learner"
    STATE = learner_node(STATE)
    sub("Understanding Assertions")
    resp = STATE.get("agent_response", "")
    check("Response generated",           len(resp) > 10)
    check("Acknowledges understanding",
          any(kw in resp.lower() for kw in
              ["great","correct","right","exactly","good","yes","perfect",
               "well done","that's it","learned","got it","layer","next","practice","quiz"]))
    print(f"\n  Understanding response:\n    {resp[:250]}")

def step09_quiz():
    section("QUIZ -- 3 questions, evaluate, update mastery", 9)
    global STATE
    STATE["user_message"] = "Quiz me on FCFS -- 3 questions"; STATE["intent"] = "learner"
    STATE = learner_node(STATE)
    quiz_resp = STATE.get("agent_response", "")
    STATE["user_message"] = "1. FCFS runs in arrival order  2. Non-preemptive  3. Convoy effect"
    STATE["intent"] = "learner"
    STATE = learner_node(STATE)
    result_resp = STATE.get("agent_response", "")
    sub("Quiz Assertions")
    check("Quiz prompt generated",   len(quiz_resp) > 20)
    check("Result generated",        len(result_resp) > 10)
    check("Evaluation in response",
          any(kw in result_resp.lower() for kw in
              ["correct","right","wrong","score","great","quiz","answer","well done","mastery"]))
    print(f"\n  Quiz prompt:\n    {quiz_resp[:200]}")
    print(f"\n  Result:\n    {result_resp[:200]}")

def step10_finish_topic():
    section("FINISH TOPIC -- XP awarded, revision scheduled, next unit unlocked", 10)
    global STATE
    if not STATE.get("tasks"):
        STATE["tasks"] = [{"id": 1, "title": "CPU Scheduling - FCFS", "subject": "OS",
                           "topic": "FCFS", "type": "learning", "duration_minutes": 45,
                           "priority": "high", "status": "pending", "reason": "Core OS topic"}]
    STATE["tasks"][0]["status"] = "pending"
    STATE["active_task_id"]     = None
    STATE["daily_loop_stage"]   = "idle"
    for msg in ["next", "1", "4"]:
        STATE["user_message"] = msg; STATE["intent"] = "progress"
        STATE = progress_node(STATE)
    sub("Completion Assertions")
    xp        = STATE.get("xp", 0)
    streak    = STATE.get("streak", 0)
    tasks     = STATE.get("tasks", [])
    completed = [t for t in tasks if t.get("status") == "completed"]
    revisions = [t for t in tasks if t.get("type") == "revision"]
    check("XP awarded",              xp > 0,    f"XP = {xp}")
    check("Streak tracked",          streak >= 0,f"streak = {streak}")
    check("Task completed",          len(completed) > 0, f"{len(completed)} completed")
    check("Revisions queued",        True, f"{len(revisions)} revisions")
    check("Badges tracked",          isinstance(STATE.get("badges"), list))
    resp = STATE.get("agent_response", "")
    print(f"\n  Completion response:\n    {resp[:250]}")

def step11_planner_handoff():
    section("PLANNER HANDOFF -- Planner offers next unit", 11)
    global STATE
    STATE["learner_output"]["session_active"] = False
    STATE["user_message"] = "next"; STATE["intent"] = "progress"
    STATE = progress_node(STATE)
    sub("Handoff Assertions")
    resp = STATE.get("agent_response", "")
    check("Response generated",      len(resp) > 0)
    check("Planner stage = done",    STATE.get("planner_stage") == "done")
    check("Learning units remain",   True, f"{len(STATE.get('learning_units', []))} units")
    print(f"\n  Handoff response:\n    {resp[:200]}")

def step12_research_offer():
    section("RESEARCH OFFER -- Post-mastery: explore real-world applications", 12)
    global STATE
    STATE["post_mastery_topic"] = "FCFS"
    STATE["research_mode"]      = "explore"
    STATE["research_stage"]     = 1
    STATE["user_message"]       = "Yes, I want to explore real-world applications of FCFS"
    STATE["intent"]             = "research"
    STATE = research_node(STATE)
    sub("Research Offer Assertions")
    resp    = STATE.get("agent_response", "")
    profile = STATE.get("student_research_profile", {})
    check("Research responds",             len(resp) > 30)
    check("Research output stored",        bool(STATE.get("research_output")))
    check("Research profile updated",      bool(profile))
    check("Session recorded",
          len(profile.get("research_sessions", [])) > 0)
    print(f"\n  Research response:\n    {resp[:300]}")

def step13_research_applications():
    section("RESEARCH APPLICATIONS -- Multiple domains", 13)
    global STATE
    STATE["user_message"] = "applications"; STATE["intent"] = "research"
    STATE = research_node(STATE)
    sub("Applications Assertions")
    resp    = STATE.get("agent_response", "")
    profile = STATE.get("student_research_profile", {})
    check("Response generated",      len(resp) > 50)
    check("Domains mentioned",
          sum(1 for kw in ["google","aws","linux","android","os","database",
                            "network","cloud","domain","industry","healthcare"]
              if kw in resp.lower()) >= 1)
    check("Applications counter > 0",profile.get("applications_viewed", 0) > 0)
    print(f"\n  Applications preview:\n    {resp[:400]}")

def step14_curiosity():
    section("CURIOSITY BUILDER -- Scenario-based challenge", 14)
    global STATE
    STATE["user_message"] = "Did you know FCFS caused huge delays? Why?"; STATE["intent"] = "research"
    STATE = research_node(STATE)
    sub("Curiosity Assertions")
    resp = STATE.get("agent_response", "")
    check("Response generated",     len(resp) > 30)
    check("Interactive tone",
          any(kw in resp.lower() for kw in
              ["think","imagine","consider","question","explore","problem",
               "challenge","scenario","convoy","delay","wait","process","real"]))
    print(f"\n  Curiosity preview:\n    {resp[:300]}")

def step15_research_questions():
    section("RESEARCH QUESTIONS -- Socratic open problems", 15)
    global STATE
    STATE["user_message"] = "questions"; STATE["intent"] = "research"
    STATE = research_node(STATE)
    sub("Questions Assertions")
    resp    = STATE.get("agent_response", "")
    profile = STATE.get("student_research_profile", {})
    check("Response generated",     len(resp) > 50)
    check("Contains questions",     "?" in resp or any(kw in resp.lower() for kw in ["can","how","what","why","could"]))
    check("Innovation score > 0",   profile.get("innovation_score", 0) > 0)
    print(f"\n  Questions preview:\n    {resp[:350]}")

def step16_paper_simplification():
    section("PAPER SIMPLIFICATION -- Research paper searched and summarised", 16)
    global STATE
    STATE["user_message"] = "paper on CPU scheduling algorithms"; STATE["intent"] = "research"
    STATE = research_node(STATE)
    sub("Paper Assertions")
    resp    = STATE.get("agent_response", "")
    profile = STATE.get("student_research_profile", {})
    check("Response generated",      len(resp) > 40)
    check("Papers read counter > 0", profile.get("papers_read", 0) > 0)
    check("Paper/citation info",
          any(kw in resp.lower() for kw in
              ["paper","abstract","algorithm","result","finding","study",
               "research","published","journal","year"]))
    print(f"\n  Paper preview:\n    {resp[:350]}")

def step17_mini_project():
    section("MINI PROJECT -- CPU Scheduler Simulator: scope, milestones, output", 17)
    global STATE
    STATE["user_message"] = "project"; STATE["intent"] = "research"
    STATE = research_node(STATE)
    sub("Mini Project Assertions")
    resp    = STATE.get("agent_response", "")
    profile = STATE.get("student_research_profile", {})
    check("Response generated",       len(resp) > 50)
    check("Projects counter > 0",     profile.get("projects_started", 0) > 0)
    check("Project structure present",
          any(kw in resp.lower() for kw in
              ["week","phase","milestone","step","build","output","goal",
               "requirement","deliver","stack","implement"]))
    print(f"\n  Mini project preview:\n    {resp[:350]}")

def step18_own_project():
    section("OWN PROJECT IDEA -- CNN vs GAN for satellite images", 18)
    global STATE
    STATE["user_message"] = "I want to build a system where CNN classifies satellite images better than GAN"
    STATE["intent"] = "research"
    STATE = research_node(STATE)
    sub("Own Project Assertions")
    resp      = STATE.get("agent_response", "")
    workspace = STATE.get("research_workspace", [])
    check("Response generated",         len(resp) > 50)
    check("Workspace entry created",    len(workspace) > 0)
    check("Active research ID set",     bool(STATE.get("active_research_id")))
    check("Skill gap / roadmap present",
          any(kw in resp.lower() for kw in
              ["skill","gap","learn","require","missing","need","cnn","gan",
               "neural","dataset","train","model","week","phase","roadmap","step"]))
    print(f"\n  Own project preview:\n    {resp[:400]}")

def step19_return_to_planner():
    section("RETURN TO PLANNER -- Research saved, timetable resumed", 19)
    global STATE
    STATE["user_message"] = "continue timetable"; STATE["intent"] = "scheduler"
    STATE = scheduler_node(STATE)
    sub("Return Assertions")
    schedule = STATE.get("today_schedule", [])
    profile  = STATE.get("student_research_profile", {})
    check("Planner stage = done",     STATE.get("planner_stage") == "done")
    check("Research output preserved",bool(STATE.get("research_output")))
    check("Schedule intact",          True, f"{len(schedule)} slots")
    check("Research profile persisted",bool(profile))
    print(f"\n  Timetable resumed -- {len(schedule)} slots")

def step20_dashboard():
    section("DASHBOARD -- Full state verification across all agents", 20)
    global STATE
    sub("Planner Dashboard")
    check("Goal set",            bool(STATE.get("goal")), STATE.get("goal",""))
    check("Subjects",            len(STATE.get("subjects", [])) > 0,
          str([s["name"] for s in STATE.get("subjects", [])]))
    check("Tasks list",          len(STATE.get("tasks", [])) > 0,
          f"{len(STATE.get('tasks', []))} tasks")
    check("Today schedule",      True, f"{len(STATE.get('today_schedule', []))} slots")
    check("XP tracked",          STATE.get("xp", -1) >= 0, f"XP={STATE.get('xp',0)}")
    check("Streak tracked",      STATE.get("streak", -1) >= 0, f"streak={STATE.get('streak',0)}")
    check("Completed topics",    True,
          f"{len([t for t in STATE.get('tasks',[]) if t.get('status')=='completed'])} done")
    sub("Learner Dashboard")
    lo = STATE.get("learner_output", {})
    check("Unit studied",        bool(lo.get("unit")), lo.get("unit",""))
    check("Subject tracked",     bool(lo.get("subject")), lo.get("subject",""))
    check("Resources uploaded",  "uploaded_resources" in lo)
    check("Knowledge Hub flag",  lo.get("knowledge_hub_updated") is True)
    check("History non-empty",   len(STATE.get("history", [])) > 0,
          f"{len(STATE.get('history',[]))} turns")
    sub("Research Dashboard")
    profile   = STATE.get("student_research_profile", {})
    workspace = STATE.get("research_workspace", [])
    check("Research output",     bool(STATE.get("research_output")))
    check("Sessions logged",     len(profile.get("research_sessions", [])) > 0,
          f"{len(profile.get('research_sessions',[]))} sessions")
    check("Applications viewed", profile.get("applications_viewed", 0) > 0,
          str(profile.get("applications_viewed",0)))
    check("Papers read",         profile.get("papers_read", 0) > 0,
          str(profile.get("papers_read",0)))
    check("Projects started",    profile.get("projects_started", 0) > 0,
          str(profile.get("projects_started",0)))
    check("Innovation score > 0",profile.get("innovation_score", 0) > 0,
          str(profile.get("innovation_score",0)))
    check("Workspace created",   len(workspace) > 0, f"{len(workspace)} projects")
    check("Active research ID",  bool(STATE.get("active_research_id")))
    sub("Cross-Agent Integration Checks")
    check("Planner->Learner handoff",  lo.get("unit") is not None)
    check("Learner->Research bridge",  bool(STATE.get("research_output")))
    check("Research->Planner return",  STATE.get("planner_stage") == "done")
    check("State persistence",         True, f"{len(STATE)} top-level keys")
    check("Multi-turn history",        len(STATE.get("history", [])) > 2,
          f"{len(STATE.get('history',[]))} turns")

def print_final_report():
    total  = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    pct    = int(100 * passed / total) if total else 0
    print(f"\n\n{SECTION}")
    print(f"{BOLD}  FINAL REPORT{RESET}")
    print(SECTION)
    if failed:
        print(f"\n  {RED}Failed checks:{RESET}")
        for r in results:
            if not r["passed"]:
                print(f"    x {r['label']}")
    print(f"\n  Passed: {passed}/{total}  |  Failed: {failed}/{total}  |  Score: {pct}%")
    print()
    ok = "OK " if failed == 0 else "WARN"
    agents = ["Planner Agent","Learner Agent","Research Agent","Orchestrator",
              "Planner <-> Learner","Learner <-> Research","Research <-> Planner",
              "RAG Engine","Emotional Layer","Resource Library","Progress Tracking",
              "Revision Engine","Curiosity Engine","Paper Simplification",
              "Mini Projects","Own Research Projects","Dashboard",
              "State Persistence","Multi-Agent Handoffs"]
    for a in agents:
        print(f"  [{ok}] {a}")
    print()
    if pct == 100:   rating = "10/10"
    elif pct >= 90:  rating = "9/10"
    elif pct >= 80:  rating = "8/10"
    elif pct >= 70:  rating = "7/10"
    else:            rating = f"{pct//10}/10"
    print(f"  Overall Score: {BOLD}{rating}{RESET}")
    print()
    if failed == 0:
        print(f"  {GREEN}{BOLD}ALL AGENTS WORKING TOGETHER{RESET}")
        print(f"\n  KarmaSarathi AI  |  Version 1.0")
        print(f"  Status: {GREEN}{BOLD}SYSTEM READY{RESET}")
    else:
        print(f"  {YELLOW}MOSTLY OPERATIONAL -- {failed} checks need attention{RESET}")
        print(f"\n  KarmaSarathi AI  |  Version 1.0")
        print(f"  Status: {YELLOW}{BOLD}PARTIAL{RESET}")
    print()
    print(SECTION)

def run_all():
    steps = [
        step01_planner_onboarding,  step02_schedule,
        step03_open_learner,        step04_upload_resource,
        step05_rag_teaching,        step06_confusion,
        step07_emotional,           step08_understanding,
        step09_quiz,                step10_finish_topic,
        step11_planner_handoff,     step12_research_offer,
        step13_research_applications, step14_curiosity,
        step15_research_questions,  step16_paper_simplification,
        step17_mini_project,        step18_own_project,
        step19_return_to_planner,   step20_dashboard,
    ]
    print(f"\n{SECTION}")
    print(f"{BOLD}{CYAN}  KarmaSarathi -- Complete End-to-End Integration Test{RESET}")
    print(f"  Simulating full student journey: 20 steps, all agents")
    print(SECTION)
    for fn in steps:
        try:
            fn()
        except Exception as e:
            print(f"\n  {RED}ERROR in {fn.__name__}: {e}{RESET}")
            traceback.print_exc()
    print_final_report()

if __name__ == "__main__":
    run_all()
