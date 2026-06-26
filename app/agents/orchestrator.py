from app.state import StudentState
from datetime import date

INTENT_RULES = {
    "daily_planner": [
        "dashboard", "deadline", "plan today", "morning", "goodnight",
        "good night", "end of day", "progress report", "how am i doing"
    ],
    "scheduler": [
        "schedule", "timetable", "today", "free time", "reschedule",
        "day plan", "plan my day", "current time", "today's schedule",
        "when can i study"
    ],
    "learner": [
        "learn", "diagram", "visualize", "show me", "quiz", "mcq",
        "explain with diagram", "visual", "teach me", "svg", "video"
    ],
    "planner": [
        "exam", "hackathon", "deadline",
        "days left", "prepare", "plan", "syllabus", "when should i"
    ],
    "tutor": [
        "explain", "teach", "understand", "what is", "how does",
        "i don't get", "concept", "confused about", "help with"
    ],
    "research": [
        "project", "idea", "research", "paper", "build", "innovate",
        "github", "find", "suggest", "what can i make",
        "explore", "curiosity", "application", "real world", "deeper",
        "innovation", "repo", "open source"
    ],
    "knowledge_tracker": [
        "knowledge report", "mastery", "unit profile", "show unit"
    ],
}

TASK_TYPE_TO_AGENT = {
    "learning":  "tutor",
    "revision":  "tutor",
    "research":  "research",
    "coding":    "tutor",   # tutor guides coding tasks until coding agent exists
    "break":     None,      # breaks need no agent
}


def classify_intent(message: str) -> str:
    lowered = message.lower()
    scores = {intent: 0 for intent in INTENT_RULES}
    for intent, keywords in INTENT_RULES.items():
        for kw in keywords:
            if kw in lowered:
                scores[intent] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


def orchestrator_node(state: dict) -> dict:
    s = StudentState(**state)
    msg = s.user_message.strip().lower()

    # ── Priority 0: Pending agent handoff from a previous agent ─────────────
    # An agent (e.g. research) set agent_handoff = {"to": "learner", ...}
    # Consume it once and route.
    if s.agent_handoff and s.agent_handoff.get("to"):
        dest = s.agent_handoff["to"]
        s.intent = dest
        print(f"[Orchestrator] Consuming handoff → {dest}")
        # Don't clear agent_handoff here — the destination agent clears it
        return s.model_dump()

    # ── Priority 1: Return-to-agent signal ───────────────────────────────────
    # After learner finishes a handoff task, "continue research" returns to research.
    if s.return_to_agent == "research" and any(
        kw in msg for kw in ["continue research", "back to research", "return to research", "continue project"]
    ):
        s.intent = "research"
        # Don't clear return_to_agent yet — research node clears it on entry
        print(f"[Orchestrator] 'continue research' → research (return handoff)")
        return s.model_dump()

    if s.return_to_agent and s.return_to_agent not in ("research",):
        dest = s.return_to_agent
        s.intent = dest
        s.return_to_agent = None
        print(f"[Orchestrator] Return handoff → {dest}")
        return s.model_dump()

    # ── Priority 2: Daily planning / end-of-day ──────────────────────────────
    today = date.today().isoformat()
    is_new_day = s.today_date != today
    if is_new_day and s.planner_stage == "done":
        s.intent = "daily_planner"
        print(f"[Orchestrator] New day → daily_planner")
        return s.model_dump()
    if any(kw in msg for kw in ["dashboard", "deadline", "goodnight", "good night", "end of day"]):
        s.intent = "daily_planner"
        print(f"[Orchestrator] Daily planner keyword → daily_planner")
        return s.model_dump()

    # ── Priority 3: Planner mid-conversation ─────────────────────────────────
    if s.planner_stage not in ("done", None):
        s.intent = "planner"
        print(f"[Orchestrator] Planner active (stage: {s.planner_stage}) → planner")
        return s.model_dump()

    # ── Priority 4: Tutor mid-lesson ─────────────────────────────────────────
    if s.tutor_status == "checking":
        s.intent = "tutor"
        print(f"[Orchestrator] Tutor active (layer: {s.tutor_layer}) → tutor")
        return s.model_dump()


    # ── Priority 4.2: Curiosity bridge from learner to research ───────────────
    if s.learner_output and s.learner_output.get("session_active"):
        curiosity_kw = [
            "this is interesting", "where is this used", "real world applications",
            "real world uses", "why do we learn this", "is this used in",
            "how is this used", "where do we use"
        ]
        if any(kw in msg for kw in curiosity_kw):
            active_unit = s.learner_output.get("unit") or s.learner_output.get("topic") or (s.subjects[0]["name"] if s.subjects else "this topic")
            s.intent = "research"
            s.post_mastery_topic = active_unit
            s.research_mode = "explore"
            s.research_stage = 1
            s.return_to_agent = "learner"
            s.user_message = f"explore applications of {active_unit}"
            print(f"[Orchestrator] Learner curiosity bridge for {active_unit} → research")
            return s.model_dump()

    # ── Priority 4.5: Learner mid-lesson ──────────────────────────────────────
    if s.learner_output and s.learner_output.get("session_active"):
        s.intent = "learner"
        print(f"[Orchestrator] Learner active (layer: {s.learner_output.get('current_layer')}) → learner")
        return s.model_dump()

    # ── Priority 5: Post-mastery research offer ──────────────────────────────
    # When a task is just completed with high rating (>=4), offer research exploration.
    # The progress agent sets a flag `offer_research` on the task.
    if s.daily_loop_stage == "idle" and s.planner_stage == "done":
        recently_completed = [
            t for t in s.tasks
            if t.get("status") == "completed"
            and t.get("offer_research")
            and not t.get("research_offered")
        ]
        if recently_completed:
            task = recently_completed[0]
            task["research_offered"] = True  # mark so we don't offer again
            topic = task.get("topic") or task.get("title", "this topic")
            s.intent = "progress"  # stays in progress to deliver the offer message
            s.agent_response = (
                f"🎯 You've mastered **{topic}**!\n\n"
                f"Would you like to:\n"
                f"  1) Continue next topic\n"
                f"  2) Explore real-world applications (Research)\n"
                f"  3) Build a project using {topic}\n"
                f"  4) Read research papers on {topic}\n"
                f"  5) Skip"
            )
            s.daily_loop_stage = "ask_post_mastery"
            s.post_mastery_topic = topic  # temp context
            s.history.append({"role": "assistant", "content": s.agent_response})
            return s.model_dump()

    # ── Priority 6: Knowledge tracker ────────────────────────────────────────
    if any(kw in msg for kw in ["knowledge report", "unit profile"]):
        s.intent = "knowledge_tracker"
        print(f"[Orchestrator] Knowledge tracker → knowledge_tracker")
        return s.model_dump()

    # ── Priority 7: Learner bridge (diagram/MCQ requested during active task) ─
    if s.active_task_id:
        learner_kw = ["diagram", "visualize", "video", "mcq", "quiz", "svg", "show me", "explain"]
        if any(kw in msg for kw in learner_kw):
            s.intent = "learner"
            print(f"[Orchestrator] Learner bridge during task → learner")
            return s.model_dump()

    # ── Priority 8: Research keywords (idea-first or exploration) ────────────
    research_kw = [
        "i want to build", "i want to make", "i want to create",
        "build a", "make a", "develop a",
        "explore", "research", "paper", "innovation", "real world",
        "application", "project idea", "workspace"
    ]
    if any(kw in msg for kw in research_kw):
        s.intent = "research"
        print(f"[Orchestrator] Research keyword → research")
        return s.model_dump()

    # ── Priority 9: Explicit reschedule ──────────────────────────────────────
    if s.planner_stage == "done" and s.tasks:
        pending = [t for t in s.tasks if t.get("status") == "pending"]
        if pending and ((s.reschedule_needed and s.daily_loop_stage in ("idle", "")) or "reschedule" in msg or "schedule" in msg):
            s.intent = "scheduler"
            print(f"[Orchestrator] Scheduler triggered → scheduler")
            return s.model_dump()

    # ── Priority 10: Progress loop active ────────────────────────────────────
    if s.daily_loop_stage not in ("idle", "") or s.active_task_id is not None:
        if "schedule" in msg or "timetable" in msg:
            s.intent = "scheduler"
            return s.model_dump()
        if s.intent not in ("tutor", "learner", "research"):
            s.intent = "progress"
            print(f"[Orchestrator] Progress loop active ({s.daily_loop_stage}) → progress")
            return s.model_dump()

    # ── Priority 11: Planner done → start schedule + progress ────────────────
    if s.planner_stage == "done" and s.tasks:
        pending = [t for t in s.tasks if t.get("status") == "pending"]
        if pending:
            if s.reschedule_needed or not s.today_schedule:
                s.intent = "scheduler"
                print(f"[Orchestrator] Planner done → scheduler")
                return s.model_dump()
            s.intent = "progress"
            s.daily_loop_stage = "idle"
            print(f"[Orchestrator] Planner done → progress")
            return s.model_dump()

    # ── Priority 12: Classify intent from message ─────────────────────────────
    s.intent = classify_intent(s.user_message)
    print(f"[Orchestrator] '{s.user_message}' → {s.intent}")
    return s.model_dump()
