from fastapi import FastAPI
from pydantic import BaseModel
from app.graph import karma_graph
from app.state import StudentState

app = FastAPI(title="KarmaSarathi AI")

# In-memory session store: session_id → state dict
# Good enough for hackathon; replace with Redis/DB later
sessions: dict[str, dict] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    # Load existing session state or start fresh
    current_state = sessions.get(req.session_id, StudentState().model_dump())

    # Inject the new user message
    current_state["user_message"] = req.message

    # If planner was already active and not done, force intent to planner
    if current_state.get("planner_stage") and current_state["planner_stage"] != "done":
        current_state["intent"] = "planner"

    # Run through the graph
    result = karma_graph.invoke(current_state)

    # Save updated state back to session
    sessions[req.session_id] = result

    return {
        "intent": result.get("intent"),
        "planner_stage": result.get("planner_stage"),
        "response": result.get("agent_response"),
        "tasks": result.get("tasks", []),
        "today_schedule": result.get("today_schedule", []),
        "learner_output": result.get("learner_output"),
    }


@app.get("/session/{session_id}")
def get_session(session_id: str):
    return sessions.get(session_id, {})


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    sessions.pop(session_id, None)
    return {"status": "cleared"}


@app.get("/")
def root():
    return {"status": "KarmaSarathi is running"}
