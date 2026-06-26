from app.state import StudentState
from app.llm import ask_gemini

LAYER_LABELS = {1: "Simple", 2: "Structured", 3: "Advanced"}

UNDERSTANDING_CHECK_PROMPT = """
You are evaluating a student's understanding of a concept.

Topic: {topic}
Teaching layer: {layer} ({layer_label})
Student's response: "{response}"

Evaluate the response and return ONE of these exact words:
- "low" — if the response is wrong, vague, or shows no understanding
- "medium" — if the response shows partial understanding
- "high" — if the response is correct and shows clear understanding

Return ONLY one word. No explanation.
"""

TEACH_PROMPT = """
You are KarmaSarathi, an expert tutor teaching Layer {layer}: {layer_label}.

Topic: {topic}
Goal context: {goal}

Layer 1 (Simple): Use a real-world analogy. No jargon. Build intuition only.
Layer 2 (Structured): Explain components, relationships, and how it works step by step.
Layer 3 (Advanced): Go deep — edge cases, internals, comparisons with alternatives.

Teach this topic at Layer {layer} in 3-5 sentences.
End with exactly ONE open question to check understanding.
Do not number the question. Do not say "Question:". Just ask it naturally at the end.
"""

ADAPT_PROMPT = """
You are KarmaSarathi, a supportive tutor.

Topic: {topic}
The student showed {level} understanding.
Their response: "{response}"

{level_instruction}

Keep it to 2-3 sentences, then ask one follow-up question.
"""

LEVEL_INSTRUCTIONS = {
    "low": "Re-explain using a simpler analogy. Break it into the smallest possible idea first.",
    "medium": "Acknowledge what they got right. Clarify the gap with a targeted example.",
}


def _teach_layer(topic: str, layer: int, goal: str) -> str:
    prompt = TEACH_PROMPT.format(
        layer=layer,
        layer_label=LAYER_LABELS[layer],
        topic=topic,
        goal=goal
    )
    return ask_gemini(prompt)


def _check_understanding(topic: str, layer: int, response: str) -> str:
    prompt = UNDERSTANDING_CHECK_PROMPT.format(
        topic=topic,
        layer=layer,
        layer_label=LAYER_LABELS[layer],
        response=response
    )
    result = ask_gemini(prompt).strip().lower()
    return result if result in ("low", "medium", "high") else "medium"


def _adapt_response(topic: str, level: str, response: str) -> str:
    prompt = ADAPT_PROMPT.format(
        topic=topic,
        level=level,
        response=response,
        level_instruction=LEVEL_INSTRUCTIONS.get(level, "")
    )
    return ask_gemini(prompt)


def tutor_node(state: dict) -> dict:
    s = StudentState(**state)

    topic = s.current_task or s.user_message
    goal = s.goal or "general study"

    print(f"[Tutor] Topic: {topic} | Layer: {s.tutor_layer} | Status: {s.tutor_status}")

    # First visit — start teaching Layer 1
    if s.tutor_status is None or s.tutor_status == "teaching" and s.tutor_layer == 1 and not s.history:
        s.tutor_status = "checking"
        s.agent_response = _teach_layer(topic, s.tutor_layer, goal)

    # Student replied — evaluate their understanding
    elif s.tutor_status == "checking":
        level = _check_understanding(topic, s.tutor_layer, s.user_message)
        print(f"[Tutor] Understanding level: {level}")

        if level == "high":
            if s.tutor_layer < 3:
                # Advance to next layer
                s.tutor_layer += 1
                s.tutor_status = "checking"
                s.agent_response = (
                    f"Great understanding! Let's go deeper.\n\n"
                    + _teach_layer(topic, s.tutor_layer, goal)
                )
            else:
                # All 3 layers complete — mark task done
                s.tutor_status = "done"
                s.tasks[s.current_task_index]["status"] = "completed"
                s.current_task_index += 1
                s.tutor_layer = 1  # reset for next task
                s.agent_response = (
                    f"Excellent! You've mastered {topic}. ✓\n\n"
                    f"Moving to your next task..."
                )
        else:
            # Re-teach or clarify
            s.tutor_status = "checking"
            s.agent_response = _adapt_response(topic, level, s.user_message)

    # Fallback
    else:
        s.tutor_status = "checking"
        s.agent_response = _teach_layer(topic, s.tutor_layer, goal)

    s.history.append({"role": "user", "content": s.user_message})
    s.history.append({"role": "assistant", "content": s.agent_response})

    return s.model_dump()
