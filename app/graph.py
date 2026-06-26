from langgraph.graph import StateGraph, END
from app.agents.orchestrator import orchestrator_node
from app.agents.planner import planner_node
from app.agents.scheduler import scheduler_node
from app.agents.tutor import tutor_node
from app.agents.research import research_node
from app.agents.progress import progress_node
from app.agents.daily_planner import daily_planner_node
from app.agents.decision_engine import decision_engine
from app.agents.knowledge_tracker import generate_knowledge_report, get_unit_profile


def learner_node(state: dict) -> dict:
    """
    LangGraph node wrapper for LearnerAgent.
    Instantiates a fresh LearnerAgent per call (all persistence lives in state).
    """
    from app.state import StudentState
    from app.agents.learner import LearnerAgent
    from app.llm import ask_gemini

    class _LLM:
        def invoke(self, prompt):
            class R:
                content = ask_gemini(prompt)
            return R()

    s       = StudentState(**state)
    agent   = LearnerAgent(_LLM(), user_id="student", state=state)
    lo      = s.learner_output or {}
    unit    = lo.get("unit") or lo.get("topic") or s.user_message
    subject = lo.get("subject", s.subjects[0]["name"] if s.subjects else "General")

    # Wire planner handoff so unit completion events update planner state
    agent.wire_planner(state)

    # Start or resume session
    if not lo.get("session_active"):
        result = agent.start_learning_session(unit, subject)
        state["learner_output"] = {
            **lo, "unit": unit, "subject": subject,
            "session_active": True, "current_layer": 0, "action": "teach"
        }
        s.agent_response = result.get("message", f"Let's learn: {unit}")
        s.history.append({"role": "assistant", "content": s.agent_response})
        out = s.model_dump()
        out["learner_output"] = state["learner_output"]
        return out

    # Active session — process interaction
    context = {
        "current_layer": lo.get("current_layer", 1),
        "action":        lo.get("action", "teach"),
        "subject":       subject,
    }
    result = agent.process_learning_interaction(s.user_message, context)

    # Advance layer on layer_complete
    if result.get("type") == "layer_complete":
        state["learner_output"]["current_layer"] = result.get("next_layer", 1)
        state["learner_output"]["action"] = "teach"
    elif result.get("type") in ("unit_complete", "session_end"):
        state["learner_output"]["session_active"] = False

    # Return to research/planner if handoff was set
    if s.return_to_agent:
        s.intent = s.return_to_agent

    s.agent_response = result.get("message") or result.get("explanation", "")
    if result.get("type") == "unit_complete" and result.get("summary"):
        s.agent_response += "\n\n**Topic Summary:**\n" + result["summary"]

    s.history.append({"role": "user",      "content": s.user_message})
    s.history.append({"role": "assistant", "content": s.agent_response})
    out = s.model_dump()
    out["learner_output"] = state["learner_output"]
    return out


def knowledge_tracker_node(state: dict) -> dict:
    from app.state import StudentState
    import re
    s   = StudentState(**state)
    msg = s.user_message.strip().lower()
    if "knowledge report" in msg or "mastery" in msg:
        s.agent_response = generate_knowledge_report(state)
    elif "unit profile" in msg:
        nums = re.findall(r"\d+", msg)
        unit_id = int(nums[0]) if nums else 1
        s.agent_response = get_unit_profile(state, unit_id)
    else:
        s.agent_response = (
            "Type 'knowledge report' for mastery overview "
            "or 'unit profile <id>' for specific unit details."
        )
    s.history.append({"role": "assistant", "content": s.agent_response})
    return s.model_dump()


def route_after_orchestrator(state: dict) -> str:
    intent = state.get("intent", "unknown")
    routes = {
        "planner":           "planner",
        "learner":           "learner",
        "scheduler":         "scheduler",
        "tutor":             "tutor",
        "research":          "research",
        "progress":          "progress",
        "daily_planner":     "daily_planner",
        "knowledge_tracker": "knowledge_tracker",
    }
    return routes.get(intent, END)


def build_graph():
    graph = StateGraph(dict)

    graph.add_node("orchestrator",      orchestrator_node)
    graph.add_node("planner",           planner_node)
    graph.add_node("scheduler",         scheduler_node)
    graph.add_node("learner",           learner_node)
    graph.add_node("tutor",             tutor_node)
    graph.add_node("research",          research_node)
    graph.add_node("progress",          progress_node)
    graph.add_node("daily_planner",     daily_planner_node)
    graph.add_node("knowledge_tracker", knowledge_tracker_node)

    graph.set_entry_point("orchestrator")

    graph.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "planner":           "planner",
            "learner":           "learner",
            "scheduler":         "scheduler",
            "tutor":             "tutor",
            "research":          "research",
            "progress":          "progress",
            "daily_planner":     "daily_planner",
            "knowledge_tracker": "knowledge_tracker",
            END:                 END,
        },
    )

    for node in ("planner", "scheduler", "learner", "tutor",
                 "research", "progress", "daily_planner", "knowledge_tracker"):
        graph.add_edge(node, END)

    return graph.compile()


karma_graph = build_graph()
