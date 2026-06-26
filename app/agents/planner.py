import re
import json
import sys
import io
from datetime import datetime
from app.state import StudentState
from app.llm import ask_gemini

# Fix Windows terminal Unicode issues
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GOAL_SPECIFIC_FIELDS = {
    "project":     ["team_size", "your_role", "current_progress"],
    "exam":        ["subjects", "hardest_subject", "units_completed"],
    "competitive": ["branch", "target_score", "weak_subjects"],
}

GOAL_SPECIFIC_QUESTIONS = {
    "project": [
        ("team_size",         "How many people are in your team?"),
        ("your_role",         "What is your role in the team?"),
        ("current_progress",  "How far along are you currently?"),
    ],
    "exam": [
        ("subjects",          "Which subjects do you need to study? (comma separated)"),
        ("hardest_subject",   "Which subject do you find the hardest?"),
        ("units_completed",   "How many units have you already completed?"),
    ],
    "competitive": [
        ("branch",            "What is your branch or stream?"),
        ("target_score",      "What is your target score?"),
        ("weak_subjects",     "Which subjects are you weakest in? (comma separated)"),
    ],
}

GOAL_CATEGORY_MAP = {
    "hackathon": "project", "college project": "project",
    "personal project": "project", "project": "project",
    "semester exam": "exam", "semester": "exam",
    "mid sem": "exam", "end sem": "exam", "exam": "exam",
    "gate": "competitive", "jee": "competitive",
    "neet": "competitive", "upsc": "competitive",
    "coding interview": "competitive",
}


def _detect_category(text: str) -> str:
    lowered = text.lower()
    for keyword, category in GOAL_CATEGORY_MAP.items():
        if keyword in lowered:
            return category
    return "project"


def _extract_goal_and_deadline(message: str) -> dict:
    """Use LLM only once to extract goal name and deadline from first message."""
    prompt = f"""
Extract goal and deadline from this message: "{message}"

Return ONLY JSON:
{{
  "goal": "the thing they are preparing for e.g. Hackathon, Semester Exam, GATE",
  "deadline": "time until event e.g. 2 days, 10 days, tomorrow"
}}

If deadline not mentioned, use null. Return ONLY JSON.
"""
    try:
        raw = ask_gemini(prompt)
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except Exception:
        return {"goal": message.strip(), "deadline": None}


def _calc_available_hours(wake: str, sleep: str) -> float:
    try:
        from datetime import datetime
        w = datetime.strptime(wake.strip().upper().replace(":", " "), "%I %p")
        s = datetime.strptime(sleep.strip().upper().replace(":", " "), "%I %p")
        diff = (s - w).seconds / 3600
        return round(diff - 1.5, 1)
    except Exception:
        return 10.0


def _parse_comma_or_single(value: str) -> list:
    return [s.strip() for s in value.split(",") if s.strip()]


ROUTINE_PROMPTS = [
    ("breakfast", "What time do you typically have breakfast?"),
    ("lunch", "What time do you typically have lunch?"),
    ("dinner", "What time do you typically have dinner?"),
    ("college_hours", "Do you have college or office hours? If yes, enter start-end times like 9am-4pm; otherwise type 'no'."),
    ("gym", "Do you go to the gym regularly? If yes, enter when; otherwise type 'no'."),
    ("travel", "Do you have daily travel time? If yes, enter the usual time or duration; otherwise type 'no'."),
    ("prayer", "Do you have daily prayer / meditation time? If yes, enter when; otherwise type 'no'."),
    ("fixed_activities", "Any fixed activities that cannot be moved? If none, type 'no'."),
    ("water_interval", "Preferred water reminder interval? (e.g. every 60 min, every 2 hours, no reminder)")
]


def _parse_subject_entry(entry: str) -> dict:
    clean = entry.strip()
    # Name = only letters and spaces, stop before any digit
    name_match = re.match(r'^([A-Za-z][A-Za-z ]*)', clean)
    name = name_match.group(1).strip() if name_match else clean
    nums = re.findall(r'\d+', clean)
    confidence = int(nums[0]) if len(nums) >= 1 else 5
    completed_units = int(nums[1]) if len(nums) >= 2 else 0
    total_units = int(nums[2]) if len(nums) >= 3 else (completed_units if len(nums) >= 2 else max(completed_units, 1))
    return {
        "name": name,
        "confidence": min(max(confidence, 1), 10),
        "completed_units": completed_units,
        "total_units": max(total_units, 1),
        "topics": []
    }


def _parse_syllabus_method(message: str) -> str:
    text = message.strip().lower()
    if text.startswith("1") or "paste" in text:
        return "paste"
    if text.startswith("2") or "manual" in text:
        return "manual"
    if text.startswith("3") or "upload" in text:
        return "upload"
    if text.startswith("4") or "roadmap" in text or "generate" in text or "ai" in text:
        return "generated"
    if "no" in text and "syllabus" in text:
        return "generated"
    return "manual"


def _parse_syllabus_input(state: StudentState, text: str) -> StudentState:
    raw = text.strip()
    if not raw:
        return state

    lines = [line.strip("-*• ") for line in re.split(r'[\n;]+', raw) if line.strip()]
    subjects = {s['name'].lower(): s for s in state.subjects}
    current_subject = None
    for line in lines:
        lower = line.lower()
        if lower in subjects:
            current_subject = subjects[lower]
            continue
        for subj_name, subj in subjects.items():
            if lower.startswith(subj_name):
                current_subject = subj
                line = re.sub(rf'^{re.escape(subj["name"])}\s*[:\-]?\s*', '', line, flags=re.IGNORECASE).strip()
                break
        if current_subject and line:
            topic_texts = [t.strip() for t in re.split(r',\s*', line) if t.strip()]
            for topic_text in topic_texts:
                topic = {"title": topic_text, "status": "pending"}
                if topic not in current_subject.get("topics", []):
                    current_subject.setdefault("topics", []).append(topic)
        elif current_subject is None and state.subjects:
            topic_texts = [t.strip() for t in re.split(r',\s*', line) if t.strip()]
            for topic_text in topic_texts:
                topic = {"title": topic_text, "status": "pending"}
                if topic not in state.subjects[0].get("topics", []):
                    state.subjects[0].setdefault("topics", []).append(topic)
    state.topic_collection_index = len(state.subjects)
    return state


def _generate_roadmap_for_subjects(state: StudentState) -> StudentState:
    subjects_text = ", ".join(s["name"] for s in state.subjects)
    prompt = f"""
You are an educational planner. The student is preparing for: {state.goal}.
Subjects: {subjects_text}.
Generate a clean list of 5-8 learning topics for each subject. Return only a JSON object:
{{
  "subjects": [
    {{"name": "Subject Name", "topics": ["Topic 1", "Topic 2", ...]}},
  ]
}}
"""
    try:
        raw = ask_gemini(prompt)
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > start:
            clean = clean[start:end]
        data = json.loads(clean)
        mapping = {s['name'].lower(): s for s in state.subjects}
        for subj in data.get('subjects', []):
            target = mapping.get(subj['name'].lower())
            if target:
                target['topics'] = [{"title": t, "status": "pending"} for t in subj.get('topics', [])]
        state.topic_collection_index = len(state.subjects)
    except Exception:
        pass
    return state


def _break_into_learning_units(topic: str, subject: str) -> list[dict]:
    """
    Break a chapter/topic into learning units.
    Example: "CPU Scheduling" -> ["Need for Scheduling", "Scheduling Criteria", "FCFS", "FCFS Example", etc.]
    Returns: [{unit_name, estimated_minutes, unit_type: 'concept'|'example'|'practice'|'quiz'}]
    """
    prompt = f"""
You are an educational content planner. Break down this topic into granular learning units.

Topic: {topic}
Subject: {subject}

Create a logical learning sequence with 8-12 units. Each unit should be learnable in 10-25 minutes.
Include: concepts, examples, practice problems, and quiz.

Return ONLY a JSON array:
[
  {{"unit_name": "Why {topic} is needed", "estimated_minutes": 10, "unit_type": "concept"}},
  {{"unit_name": "Core objectives", "estimated_minutes": 8, "unit_type": "concept"}},
  {{"unit_name": "Algorithm 1 - FCFS", "estimated_minutes": 15, "unit_type": "concept"}},
  {{"unit_name": "FCFS - Worked Example", "estimated_minutes": 12, "unit_type": "example"}},
  {{"unit_name": "FCFS - Problems", "estimated_minutes": 20, "unit_type": "practice"}},
  {{"unit_name": "Algorithm 2 - SJF", "estimated_minutes": 15, "unit_type": "concept"}},
  {{"unit_name": "Comparison & Trade-offs", "estimated_minutes": 12, "unit_type": "concept"}},
  {{"unit_name": "Numerical Practice", "estimated_minutes": 25, "unit_type": "practice"}},
  {{"unit_name": "MCQs", "estimated_minutes": 15, "unit_type": "quiz"}}
]
"""
    try:
        raw = ask_gemini(prompt)
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        start = clean.find("[")
        end = clean.rfind("]") + 1
        if start != -1 and end > start:
            clean = clean[start:end]
        units = json.loads(clean)
        if isinstance(units, list) and units:
            return units
    except Exception as ex:
        print(f"[Planner] learning unit breakdown fallback for {topic}: {ex}")
    
    # Fallback: comprehensive 5-part structure
    return [
        {"unit_name": f"{topic} - Introduction", "estimated_minutes": 10, "unit_type": "concept"},
        {"unit_name": f"{topic} - Core Concepts", "estimated_minutes": 20, "unit_type": "concept"},
        {"unit_name": f"{topic} - Worked Example", "estimated_minutes": 15, "unit_type": "example"},
        {"unit_name": f"{topic} - Practice Problems", "estimated_minutes": 20, "unit_type": "practice"},
        {"unit_name": f"{topic} - Quick Quiz", "estimated_minutes": 10, "unit_type": "quiz"},
    ]


def _populate_learning_units(state: StudentState) -> StudentState:
    """
    Convert topics/chapters into granular learning units.
    This is called after topics are collected and before task generation.
    """
    if state.learning_units:  # already populated
        return state
    
    unit_id = 1
    for subj in state.subjects:
        subject_name = subj["name"]
        for topic_dict in subj.get("topics", []):
            chapter_name = topic_dict["title"]
            topic_status = topic_dict.get("status", "pending")
            
            # Break chapter into units
            units = _break_into_learning_units(chapter_name, subject_name)
            
            for unit in units:
                state.learning_units.append({
                    "id": unit_id,
                    "subject": subject_name,
                    "chapter": chapter_name,
                    "unit_name": unit["unit_name"],
                    "unit_type": unit.get("unit_type", "concept"),
                    "status": "completed" if topic_status == "done" else "pending",
                    "completion_pct": 100 if topic_status == "done" else 0,
                    "mastery": 0,
                    "estimated_minutes": unit.get("estimated_minutes", 15),
                    "actual_time_spent": 0,
                    "revision_due": None,
                    "practice_due": None,
                    "difficulty": "medium",
                    "attempts": 0,
                    "last_studied": None,
                    "next_revision": None,
                    "quiz_score": 0,
                    "quiz_attempts": 0,
                    "resources": {"videos": [], "diagrams": [], "notes": [], "practice": [], "quiz": []},
                    "revision_history": [],
                    "practice_history": [],
                    "created_at": datetime.now().isoformat(),
                    "completed_at": None,
                    "last_accessed": None,
                    "archived_at": None,
                })
                unit_id += 1
    
    return state


def _extract_learning_style(state: StudentState) -> StudentState:
    state.learning_style = state.user_message.strip().lower()
    return state


def _create_learning_path(state: StudentState) -> StudentState:
    if state.learning_path:
        return state
    priority_order = []
    if state.strategy and isinstance(state.strategy[0], dict):
        priority_order = state.strategy[0].get('priority_order', [])
    if not priority_order:
        priority_order = [s['name'] for s in state.subjects]

    ordered_subjects = sorted(
        state.subjects,
        key=lambda s: priority_order.index(s['name']) if s['name'] in priority_order else len(priority_order)
    )
    path = []
    order = 1
    for subj in ordered_subjects:
        for topic in subj.get('topics', []):
            path.append({
                'subject': subj['name'],
                'title': topic['title'],
                'status': topic.get('status', 'pending'),
                'difficulty': 'medium',
                'estimated_minutes': 45,
                'learning_order': order,
                'prerequisites': []
            })
            order += 1
        if subj.get('topics'):
            path.append({
                'subject': subj['name'],
                'title': f"Practice {subj['name']} topics",
                'status': 'pending',
                'difficulty': 'medium',
                'estimated_minutes': 45,
                'learning_order': order,
                'prerequisites': [t['title'] for t in subj.get('topics', [])]
            })
            order += 1
    state.learning_path = path
    return state


def _extract_subjects(state: StudentState) -> StudentState:
    msg = state.user_message.strip()
    if not msg:
        return state

    entries = re.split(r'[\n;,]+', msg)
    subjects = [_parse_subject_entry(entry) for entry in entries if entry.strip()]
    if subjects:
        state.subjects = subjects
        state.topics = [sub['name'] for sub in subjects]
    return state


def _extract_routine_detail(state: StudentState) -> StudentState:
    msg = state.user_message.strip()
    if not msg:
        return state

    if state.routine_step < len(ROUTINE_PROMPTS):
        key, _ = ROUTINE_PROMPTS[state.routine_step]
        state.routine[key] = msg
        state.routine_step += 1
    return state


def _extract_study_style(state: StudentState) -> StudentState:
    msg = state.user_message.strip()
    if not state.focus_duration:
        state.focus_duration = msg
    elif not state.break_duration:
        state.break_duration = msg
    elif not state.productivity_peak:
        state.productivity_peak = msg
    return state


def _extract_energy(state: StudentState) -> StudentState:
    state.energy_peak = state.user_message.strip().lower()
    return state


def _extract_info(state: StudentState) -> StudentState:
    msg = state.user_message.strip()

    if state.planner_stage in ("confirm", "generate_tasks", "done"):
        return state

    if state.planner_stage == "collect_goal":
        extracted = _extract_goal_and_deadline(msg)
        state.goal = extracted.get("goal") or msg
        if extracted.get("deadline"):
            state.deadline = extracted["deadline"]
        state.goal_category = _detect_category(state.goal)
        state.goal_category_locked = True
        if state.goal_category == "project":
            state.goal_specific["project_idea"] = msg
        return state

    if state.planner_stage == "collect_deadline":
        state.deadline = msg
        return state

    if state.planner_stage == "collect_routine":
        if not state.wake_time:
            state.wake_time = msg
        elif not state.sleep_time:
            state.sleep_time = msg
        return state

    if state.planner_stage == "collect_routine_detail":
        return _extract_routine_detail(state)

    if state.planner_stage == "collect_goal_specific":
        required = GOAL_SPECIFIC_QUESTIONS.get(state.goal_category or "project", [])
        missing = [(f, q) for f, q in required if not state.goal_specific.get(f)]
        numbered = re.findall(r'\d+\.\s*(.+?)(?=\s*\d+\.|$)', msg)
        if numbered:
            for i, value in enumerate(numbered):
                if i < len(missing):
                    field, _ = missing[i]
                    value = value.strip()
                    state.goal_specific[field] = (
                        _parse_comma_or_single(value)
                        if field in ("subjects", "weak_subjects")
                        else value
                    )
        else:
            if missing:
                field, _ = missing[0]
                state.goal_specific[field] = (
                    _parse_comma_or_single(msg)
                    if field in ("subjects", "weak_subjects")
                    else msg
                )
        return state

    if state.planner_stage == "collect_subjects":
        return _extract_subjects(state)

    if state.planner_stage == "collect_study_mode":
        cleaned = msg.lower().strip()
        if cleaned in ("1", "focus", "focus mode"):
            state.study_mode = "focus"
        elif cleaned in ("2", "mixed", "mixed mode"):
            state.study_mode = "mixed"
        else:
            state.study_mode = "mixed"  # default
        return state

    if state.planner_stage == "collect_syllabus_method":
        state.syllabus_method = _parse_syllabus_method(msg)
        state.learning_content_source = state.syllabus_method
        return state

    if state.planner_stage == "collect_syllabus_input":
        if state.syllabus_method == "generated":
            return _generate_roadmap_for_subjects(state)
        return _parse_syllabus_input(state, msg)

    if state.planner_stage == "collect_topics":
        return _extract_topics_for_current_subject(state)

    if state.planner_stage == "collect_completed":
        return _extract_completed_topics(state)

    if state.planner_stage == "collect_study_style":
        return _extract_study_style(state)

    if state.planner_stage == "collect_energy":
        return _extract_energy(state)

    if state.planner_stage == "collect_learning_style":
        return _extract_learning_style(state)

    return state


def _subjects_need_topics(state: StudentState) -> bool:
    """True if any subject still has no topics list collected."""
    return any(not s.get("topics") for s in state.subjects)


def _current_topic_subject(state: StudentState) -> dict | None:
    """Return the subject we're currently collecting topics for."""
    idx = state.topic_collection_index
    if idx < len(state.subjects):
        return state.subjects[idx]
    return None


def _extract_topics_for_current_subject(state: StudentState) -> StudentState:
    msg = state.user_message.strip()
    if not msg:
        return state
    idx = state.topic_collection_index
    if idx >= len(state.subjects):
        return state
    raw = re.split(r'[\n,;]+', msg)
    topics = [{"title": t.strip(), "status": "pending"} for t in raw if t.strip()]
    state.subjects[idx]["topics"] = topics
    state.topic_collection_index = idx + 1
    return state


def _extract_completed_topics(state: StudentState) -> StudentState:
    msg = state.user_message.strip().lower()
    # "all pending" / "none" / "no" — mark nothing as done
    if msg in ("all pending", "none", "no", "n", "all"):
        return state
    # Otherwise parse lines like "DS: Arrays, Stacks" or just "Arrays, Stacks" for the last subject
    for line in re.split(r'[\n;]+', state.user_message.strip()):
        line = line.strip()
        if not line:
            continue
        # Check if line starts with a subject name
        matched_subject = None
        for subj in state.subjects:
            if line.lower().startswith(subj["name"].lower()):
                matched_subject = subj
                # strip the subject name prefix
                line = re.sub(rf'^{re.escape(subj["name"])}\s*[:\-]?\s*', '', line, flags=re.IGNORECASE)
                break
        done_topics = [t.strip().lower() for t in re.split(r'[,]+', line) if t.strip()]
        targets = [matched_subject] if matched_subject else state.subjects
        for subj in targets:
            for topic in subj.get("topics", []):
                if topic["title"].lower() in done_topics:
                    topic["status"] = "done"
    return state


def _goal_specific_complete(state: StudentState) -> bool:
    required = [f for f, _ in GOAL_SPECIFIC_QUESTIONS.get(state.goal_category or "project", [])]
    return all(state.goal_specific.get(f) for f in required)


def _is_yes(message: str) -> bool:
    cleaned = message.strip().lower()
    return cleaned in ("yes", "y", "sure", "okay", "ok", "yeah", "yep", "sounds good", "looks good")


def _all_topics_collected(state: StudentState) -> bool:
    return state.topic_collection_index >= len(state.subjects) and not _subjects_need_topics(state)


def _next_stage(state: StudentState) -> str:
    if state.planner_stage in ("generate_tasks", "done"):
        return state.planner_stage
    if state.planner_stage == "review_plan":
        return "review_plan"  # handled in planner_node
    if not state.goal:
        return "collect_goal"
    if not state.deadline:
        return "collect_deadline"
    if not state.wake_time or not state.sleep_time:
        return "collect_routine"
    if state.routine_step < len(ROUTINE_PROMPTS):
        return "collect_routine_detail"
    if not _goal_specific_complete(state):
        return "collect_goal_specific"
    if not state.subjects:
        return "collect_subjects"
    if not state.study_mode:
        return "collect_study_mode"
    if not state.syllabus_method:
        return "collect_syllabus_method"
    if not _all_topics_collected(state):
        return "collect_syllabus_input"
    if not state.goal_specific.get("completed_topics_asked"):
        return "collect_completed"
    if not state.focus_duration or not state.break_duration or not state.productivity_peak:
        return "collect_study_style"
    if not state.energy_peak:
        return "collect_energy"
    if not state.learning_style:
        return "collect_learning_style"
    if not state.analysis_notes:
        return "analyze_user"
    if not state.strategy:
        return "create_strategy"
    return "review_plan"


def _build_question(state: StudentState) -> str:
    stage = state.planner_stage

    if stage == "collect_goal":
        return "What are you preparing for? (e.g. Hackathon, Semester Exam, GATE)"

    if stage == "collect_deadline":
        return "When is your deadline?"

    if stage == "collect_routine":
        if not state.wake_time:
            return "What time do you usually wake up?"
        return "What time do you usually go to sleep?"

    if stage == "collect_goal_specific":
        required = GOAL_SPECIFIC_QUESTIONS.get(state.goal_category or "project", [])
        missing = [(f, q) for f, q in required if not state.goal_specific.get(f)]
        if len(missing) == 1:
            return missing[0][1]
        lines = [f"{i+1}. {q}" for i, (_, q) in enumerate(missing)]
        return "Please answer the following:\n" + "\n".join(lines)

    if stage == "collect_subjects":
        return (
            "Please list your subjects with confidence (1-10) and units done/total. Example:\n"
            "DS 8 4/5, OS 3 1/5, DBMS 6 2/4"
        )

    if stage == "collect_study_mode":
        return (
            "How would you like to study?\n\n"
            "1. Focus Mode\n"
            "   Finish one subject completely before moving to another.\n"
            "   Best for: Deep mastery, fewer context switches.\n\n"
            "2. Mixed Mode\n"
            "   Study multiple subjects every day (rotating).\n"
            "   Best for: Balanced preparation, variety.\n\n"
            "Reply 1 (Focus) or 2 (Mixed)"
        )

    if stage == "collect_topics":
        subj = _current_topic_subject(state)
        if subj:
            return (
                f"What topics are in your {subj['name']} syllabus?\n"
                f"List them one per line or comma-separated. Example:\n"
                f"  Arrays, Linked Lists, Trees, Graphs"
            )
        return "Can you list the topics for your next subject?"

    if stage == "collect_completed":
        lines = []
        for subj in state.subjects:
            topic_names = ", ".join(t["title"] for t in subj.get("topics", []))
            lines.append(f"  {subj['name']}: {topic_names}")
        return (
            "Which of these topics have you already completed? \n"
            + "\n".join(lines)
            + "\n\nFormat: SubjectName: Topic1, Topic2  (or type 'all pending' if nothing is done)"
        )

    if stage == "collect_study_style":
        if not state.focus_duration:
            return "How long can you focus in one study block? (25 min, 45 min, 60 min, 90 min)"
        if not state.break_duration:
            return "How long should your breaks be? (5, 10, 15, 20)"
        return "When are you usually most productive? (Morning, Afternoon, Evening, Night)"

    if stage == "collect_energy":
        return "Do you feel more energetic in the morning or at night?"

    if stage == "collect_learning_style":
        return "How do you prefer to learn? Videos, Books, Interactive Notes, Practice Questions, or Mixed"

    if stage == "collect_routine_detail":
        if state.routine_step < len(ROUTINE_PROMPTS):
            return ROUTINE_PROMPTS[state.routine_step][1]
        return "Tell me any other daily schedule details you'd like me to consider."

    if stage == "collect_syllabus_method":
        return (
            "How would you like to provide your syllabus or topic list?\n"
            "1) Paste the syllabus text\n"
            "2) Enter topics manually per subject\n"
            "3) Upload a file (paste the text here instead)\n"
            "4) Let me generate topic suggestions for you"
        )

    if stage == "collect_syllabus_input":
        if state.syllabus_method == "paste":
            return "Paste your syllabus or topic list here. Use subject headings if possible."
        if state.syllabus_method == "manual":
            return (
                "Enter the topics for each subject in this format:\n"
                "Subject: topic1, topic2, topic3\n"
                "For example: DS: Arrays, Stacks, Trees"
            )
        if state.syllabus_method == "upload":
            return "Please paste the contents of your syllabus file here."
        if state.syllabus_method == "generated":
            return "Generating a topic roadmap now based on your subjects..."
        return "Please provide your syllabus or topic list."

    if stage == "create_learning_path":
        return "Creating a learning path from your topics and strategy..."

    if stage == "review_plan":
        return "Do you want to confirm this strategy and generate tasks? Reply yes or tell me what to change."

    return "Can you tell me more?"


def _build_strategy(state: StudentState) -> str:
    tasks = []
    if state.subjects:
        for subject in state.subjects:
            confidence = subject.get("confidence", 5)
            completed = subject.get("completed_units", 0)
            total = subject.get("total_units", 1)
            name = subject.get("name")
            ratio = completed / total if total else 0
            if confidence <= 4 or ratio < 0.5:
                tasks.append(f"Focus daily on {name}, especially weak topics.")
            elif confidence <= 6:
                tasks.append(f"Alternate {name} with stronger subjects and include practice sessions.")
            else:
                tasks.append(f"Keep {name} on a review schedule and balance with weaker subjects.")

    peak = state.productivity_peak or "your most productive time"
    goal_note = f"Your deadline is {state.deadline}."
    if state.energy_peak:
        goal_note += f" You feel more energetic in the {state.energy_peak}."
    if state.focus_duration and state.break_duration:
        goal_note += f" Use {state.focus_duration} focus blocks with {state.break_duration}-minute breaks."

    strategy_lines = [
        f"Goal: {state.goal}.",
        goal_note,
    ] + tasks

    strategy_lines.append(f"Review every night if the deadline is within 10 days.")
    return "\n".join(strategy_lines)


def _llm_strategy_hints(state: "StudentState") -> dict:
    """
    Ask LLM for a SMALL strategy JSON only — no tasks, no durations.
    Python generates everything else.
    """
    subject_lines = []
    for s in state.subjects:
        pending = [t["title"] for t in s.get("topics", []) if t.get("status") != "done"]
        subject_lines.append(f"{s['name']} (confidence {s.get('confidence',5)}/10): {', '.join(pending)}")

    prompt = f"""You are a study strategist. Return ONLY a compact JSON object, no extra text.

Goal: {state.goal} | Deadline: {state.deadline}
Subjects: {chr(10).join(subject_lines)}

Return exactly this shape:
{{"priority_order":["subject1","subject2"],"practice_subjects":["subject"],"revision_daily":true,"hard_topics":{{"SubjectName":["topic"]}}}}"""

    try:
        raw = ask_gemini(prompt)
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        s = clean.find("{")
        e = clean.rfind("}") + 1
        if s != -1 and e > s:
            clean = clean[s:e]
        data = json.loads(clean)
        if isinstance(data, dict):
            return data
    except Exception as ex:
        print(f"[Planner] strategy hints fallback: {ex}")
    return {}


def _deadline_intensity(deadline_str: str | None) -> str:
    """Return 'tight' (<= 7 days), 'moderate' (8-21), or 'relaxed' (> 21)."""
    if not deadline_str:
        return "moderate"
    nums = re.findall(r"\d+", str(deadline_str).lower())
    days = int(nums[0]) if nums else 14
    if "tomorrow" in str(deadline_str).lower():
        days = 1
    if days <= 7:
        return "tight"
    if days <= 21:
        return "moderate"
    return "relaxed"


def _generate_tasks(state: "StudentState") -> list[dict]:
    """Build task list from learning units, not chapters."""
    if not state.learning_units:
        return _build_task_fallback(state)
    
    intensity = _deadline_intensity(state.deadline)
    
    # Get focus/break durations
    focus_min = 45
    break_min = 10
    if state.focus_duration:
        nums = re.findall(r"\d+", state.focus_duration)
        if nums:
            focus_min = int(nums[0])
    if state.break_duration:
        nums = re.findall(r"\d+", str(state.break_duration))
        if nums:
            break_min = int(nums[0])
    
    # Deadline adjustments
    if intensity == "tight":
        break_after = 2
    elif intensity == "relaxed":
        break_after = 3
    else:
        break_after = 2
    
    # Get priority order from strategy
    priority = []
    if state.structured_strategy:
        priority = state.structured_strategy.get("priority_order", [])
    if not priority:
        priority = [s["name"] for s in state.subjects]
    
    # Sort learning units by priority, then by subject confidence
    def _unit_rank(unit):
        subj_name = unit["subject"]
        try:
            prio_idx = priority.index(subj_name)
        except ValueError:
            prio_idx = len(priority)
        
        # Completed units go last
        if unit.get("status") == "completed":
            return (999, prio_idx, 0)
        
        # Pending units by priority
        return (prio_idx, 0)
    
    sorted_units = sorted(state.learning_units, key=_unit_rank)
    
    # Generate tasks from learning units
    tasks: list[dict] = []
    task_id = 1
    tasks_since_break = 0
    
    for unit in sorted_units:
        if unit.get("status") == "completed":
            continue
        
        subject = unit["subject"]
        chapter = unit["chapter"]
        unit_name = unit["unit_name"]
        unit_type = unit.get("unit_type", "concept")
        est_minutes = unit.get("estimated_minutes", 15)
        
        # Determine priority based on subject confidence
        confidence = next((s.get("confidence", 5) for s in state.subjects if s["name"] == subject), 5)
        priority_label = "critical" if confidence <= 3 else ("high" if confidence <= 5 else "medium")
        difficulty = "hard" if confidence <= 4 else ("medium" if confidence <= 6 else "easy")
        energy_label = "high" if difficulty == "hard" else "medium"
        
        # Map unit_type to task_type
        if unit_type == "concept":
            task_type = "learning"
            title_prefix = "Learn"
        elif unit_type == "example":
            task_type = "learning"
            title_prefix = "Study"
        elif unit_type == "practice":
            task_type = "practice"
            title_prefix = "Practice"
        elif unit_type == "quiz":
            task_type = "quiz"
            title_prefix = "Quiz"
        else:
            task_type = "learning"
            title_prefix = "Study"
        
        tasks.append({
            "id": task_id,
            "title": f"{title_prefix}: {unit_name}",
            "subject": subject,
            "chapter": chapter,
            "topic": unit_name,
            "learning_unit_id": unit["id"],
            "type": task_type,
            "duration_minutes": est_minutes,
            "priority": priority_label,
            "difficulty": difficulty,
            "energy": energy_label,
            "depends_on": [],
            "recommended_resource_type": "explanation" if unit_type == "concept" else "practice",
            "status": "pending",
            "reason": f"{subject} - {chapter}",
        })
        task_id += 1
        tasks_since_break += 1
        
        # Add breaks
        if tasks_since_break >= break_after:
            tasks.append({
                "id": task_id, "title": "Break", "subject": "General", "topic": None,
                "type": "break", "duration_minutes": break_min,
                "priority": "low", "difficulty": "easy", "energy": "low",
                "depends_on": [], "recommended_resource_type": "none",
                "status": "pending", "reason": "Scheduled break",
            })
            task_id += 1
            tasks_since_break = 0
    
    return tasks if tasks else _build_task_fallback(state)


def _build_task_fallback(state: StudentState) -> list[dict]:
    tasks = []
    pending_topics = []
    for subj in state.subjects:
        for topic in subj.get("topics", []):
            if topic.get("status") != "done":
                pending_topics.append((subj["name"], topic["title"], subj.get("confidence", 5)))

    total_minutes = int(_calc_available_hours(state.wake_time, state.sleep_time) * 60)
    if not pending_topics:
        return [{"id": 1, "title": "Review your goal and topics", "subject": state.subjects[0]["name"] if state.subjects else "General", "topic": None, "type": "revision",
                 "duration_minutes": 30, "priority": "medium", "difficulty": "easy",
                 "energy": "low", "depends_on": [], "recommended_resource_type": "none",
                 "status": "pending", "reason": "Fallback task"}]

    duration = min(45, max(20, total_minutes // max(len(pending_topics), 1)))
    duration = 45 if duration >= 30 else 30
    task_id = 1
    for subject, topic_title, confidence in pending_topics:
        priority = "high" if confidence <= 4 else "medium"
        difficulty = "hard" if confidence <= 4 else "medium"
        tasks.append({
            "id": task_id,
            "title": f"Study {topic_title}",
            "subject": subject,
            "topic": topic_title,
            "type": "learning",
            "duration_minutes": duration,
            "priority": priority,
            "difficulty": difficulty,
            "energy": "high" if state.energy_peak and state.energy_peak.lower() == "morning" and subject.lower() == "os" else "medium",
            "depends_on": [],
            "recommended_resource_type": "explanation",
            "status": "pending",
            "reason": "Fallback task"
        })
        task_id += 1
        if task_id % 3 == 0 and total_minutes >= 15:
            tasks.append({
                "id": task_id,
                "title": "Take a short break",
                "subject": "General",
                "topic": None,
                "type": "break",
                "duration_minutes": 15,
                "priority": "low",
                "difficulty": "easy",
                "energy": "low",
                "depends_on": [],
                "recommended_resource_type": "none",
                "status": "pending",
                "reason": "Scheduled break"
            })
            task_id += 1
    return tasks


def _review_plan_response(state: StudentState) -> str:
    lines = [
        f"Goal: {state.goal} ({state.goal_category})",
        f"Deadline: {state.deadline}",
        f"Wake: {state.wake_time}  Sleep: {state.sleep_time}",
        f"Focus block: {state.focus_duration}  Break: {state.break_duration} min",
        f"Productivity peak: {state.productivity_peak}  Energy peak: {state.energy_peak}",
    ]
    if state.subjects:
        lines.append("Subjects:")
        for subject in state.subjects:
            lines.append(
                f"  - {subject['name']}: confidence {subject['confidence']}, "
                f"{subject['completed_units']}/{subject['total_units']} units"
            )
    lines.append("")
    lines.append("Here is the strategy I recommend:")
    if state.strategy:
        strat = state.strategy[0]
        lines.append(strat.get("summary", ""))
        schedule = strat.get("schedule", [])
        if schedule:
            lines.append("\nSchedule:")
            for item in schedule:
                lines.append(f"  - {item['subject']}: {item['frequency']}, {item['time_slot']}")
        if strat.get("revision"):
            lines.append(f"\nRevision: {strat['revision']}")
        if strat.get("practice"):
            lines.append(f"Practice: {strat['practice']}")
    else:
        lines.append(_build_strategy(state))
    lines.append("")
    if state.learning_path:
        lines.append("Learning path summary:")
        for item in state.learning_path[:3]:
            lines.append(f"  - {item['subject']}: {item['title']} ({item['difficulty']})")
        lines.append("  ...")
        lines.append("")
    lines.append("Reply 'yes' to confirm and generate tasks, or tell me how you'd like to adjust it.")
    return "\n".join(lines)


def _analyze_user(state: StudentState) -> StudentState:
    if state.analysis_notes:
        return state

    subjects_info = ""
    if state.subjects:
        lines = []
        for s in state.subjects:
            ratio = s.get('completed_units', 0) / max(s.get('total_units', 1), 1)
            lines.append(
                f"  - {s['name']}: confidence {s.get('confidence',5)}/10, "
                f"{s.get('completed_units',0)}/{s.get('total_units',1)} units done ({ratio*100:.0f}%)"
            )
        subjects_info = "\n".join(lines)

    prompt = f"""You are an expert study coach. Analyze this student's profile and reason about priorities.

Goal: {state.goal} (category: {state.goal_category})
Deadline: {state.deadline}
Wake: {state.wake_time}  Sleep: {state.sleep_time}
Focus block: {state.focus_duration}  Break: {state.break_duration}
Productivity peak: {state.productivity_peak}
Energy peak: {state.energy_peak}
Subjects:
{subjects_info}
Goal details: {state.goal_specific}

Think step by step:
1. How tight is the deadline?
2. Which subjects need the most attention and why?
3. What study pattern fits the student's energy and focus style?
4. Any risks or things to watch out for?

Return ONLY a JSON object:
{{
  "notes": ["concise insight 1", "concise insight 2", ...],
  "study_strategy": {{
    "priority_subjects": ["subject with highest need first"],
    "daily_revision": true or false,
    "practice_required": true or false,
    "risk": "one sentence about biggest risk"
  }}
}}"""

    try:
        raw = ask_gemini(prompt)
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > start:
            clean = clean[start:end]
        data = json.loads(clean)
        notes = data.get("notes")
        if not isinstance(notes, list) or not notes:
            notes = [f"Deadline is {state.deadline}.", "Focus on weaker subjects first."]
        strategy = data.get("study_strategy")
        if not isinstance(strategy, dict) or not strategy:
            strategy = {"priority_subjects": [], "daily_revision": True, "practice_required": True}
        state.analysis_notes = notes
        state.study_strategy = strategy
    except Exception as e:
        print(f"[Planner] analyze_user fallback: {e}")
        state.analysis_notes = [f"Deadline is {state.deadline}.", "Focus on weaker subjects first."]
        state.study_strategy = {"priority_subjects": [], "daily_revision": True, "practice_required": True}
    return state


def _create_strategy(state: StudentState, adjustment: str = "") -> StudentState:
    subjects_info_lines = []
    for s in state.subjects:
        pending = [t["title"] for t in s.get("topics", []) if t.get("status") != "done"]
        done = [t["title"] for t in s.get("topics", []) if t.get("status") == "done"]
        subjects_info_lines.append(
            f"  - {s['name']}: confidence {s.get('confidence',5)}/10 | "
            f"pending topics: {pending} | completed: {done}"
        )
    subjects_info = "\n".join(subjects_info_lines)

    adjustment_line = f"\nUser requested adjustment: {adjustment}" if adjustment else ""

    prompt = f"""You are a study strategist. Create a clear, personalized study strategy.

Goal: {state.goal} | Deadline: {state.deadline}
Wake: {state.wake_time}  Sleep: {state.sleep_time}
Focus: {state.focus_duration}  Break: {state.break_duration} min
Productivity peak: {state.productivity_peak}  Energy peak: {state.energy_peak}
Subjects with EXACT user-provided topics:
{subjects_info}
Analysis: {state.analysis_notes}
Inferred facts: {state.study_strategy}{adjustment_line}

Rules:
- NEVER invent topics. Only use topics explicitly listed above.
- Assign each subject a schedule slot based on confidence and pending topics.
- Hard/low-confidence subjects go in the energy peak slot.
- Include revision and practice cadence.

Return ONLY a JSON object:
{{
  "summary": "2-4 sentence human-readable strategy",
  "priority_order": ["subject names ordered by urgency"],
  "practice_subjects": ["subjects needing most practice"],
  "revision_daily": true,
  "focus_block": {int(state.focus_duration.split()[0]) if state.focus_duration else 45},
  "break_block": {int(state.break_duration) if state.break_duration and str(state.break_duration).isdigit() else 10},
  "daily_schedule": {{
    "morning": ["subject names"],
    "afternoon": ["subject names"],
    "evening": ["subject names"],
    "night": ["revision"]
  }},
  "schedule": [
    {{"subject": "...", "frequency": "daily|alternate|weekly", "time_slot": "morning|afternoon|evening|night"}}
  ],
  "revision": "describe revision plan",
  "practice": "describe practice plan"
}}"""

    try:
        raw = ask_gemini(prompt)
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > start:
            clean = clean[start:end]
        data = json.loads(clean)
        if not isinstance(data, dict) or not data.get("summary"):
            raise ValueError("Invalid strategy response")
        state.strategy = [data]
        # store rich strategy separately for scheduler
        state.structured_strategy = {
            "priority_order": data.get("priority_order", []),
            "practice_subjects": data.get("practice_subjects", []),
            "revision_daily": data.get("revision_daily", True),
            "focus_block": data.get("focus_block", 45),
            "break_block": data.get("break_block", 10),
            "daily_schedule": data.get("daily_schedule", {}),
        }
    except Exception as e:
        print(f"[Planner] create_strategy fallback: {e}")
        fallback_summary = _build_strategy(state)
        state.strategy = [{"summary": fallback_summary}]
        state.structured_strategy = {
            "priority_order": [],
            "practice_subjects": [],
            "revision_daily": True,
            "focus_block": int(state.focus_duration.split()[0]) if state.focus_duration and state.focus_duration.split()[0].isdigit() else 45,
            "break_block": int(state.break_duration) if state.break_duration and str(state.break_duration).isdigit() else 10,
            "daily_schedule": {},
        }
    return state



def _confirm_response(s) -> str:
    """Build a Day-1 timetable preview shown after the user confirms the plan."""
    from app.agents.scheduler import (
        _parse_time, _blocked_intervals, _free_slots, _fmt, _add,
    )
    import re as _re
    from datetime import datetime as _dt

    now   = _dt.now().replace(second=0, microsecond=0)
    wake  = _parse_time(s.wake_time or "6 AM") or now.replace(hour=6,  minute=0)
    sleep = _parse_time(s.sleep_time or "11 PM") or now.replace(hour=23, minute=0)
    start = max(now, wake)

    focus_min, break_min = 45, 10
    if s.focus_duration:
        nums = _re.findall(r"\d+", s.focus_duration)
        if nums: focus_min = int(nums[0])
    if s.break_duration:
        nums = _re.findall(r"\d+", str(s.break_duration))
        if nums: break_min = int(nums[0])

    blocked = _blocked_intervals(s.routine, wake, sleep)
    free    = _free_slots(start, sleep, blocked)

    ICONS = {"learning": "📖", "practice": "✏️", "revision": "🔄"}
    study_tasks = [t for t in s.tasks if t.get("type") != "break"][:8]

    lines = [f"\n📅 Day 1 Timetable  (from {_fmt(start)})\n"]
    slot_idx, cursor, placed, since_brk = 0, start, 0, 0
    shown_fixed: set = set()

    for task in study_tasks:
        if slot_idx >= len(free):
            break
        fs, fe = free[slot_idx]
        if cursor < fs:
            for bs, be, bl in blocked:
                if cursor <= bs < fs and bl not in shown_fixed:
                    lines.append(f"  {_fmt(bs)} – {_fmt(be)}  🔒 {bl}")
                    shown_fixed.add(bl)
            cursor = fs
        if since_brk >= 2:
            brk_end = _add(cursor, break_min)
            if brk_end <= fe:
                lines.append(f"  {_fmt(cursor)} – {_fmt(brk_end)}  ☕ Break")
                cursor = brk_end
            since_brk = 0
        dur  = task.get("duration_minutes", focus_min)
        tend = _add(cursor, dur)
        if tend > fe:
            slot_idx += 1
            if slot_idx < len(free):
                cursor = free[slot_idx][0]
            continue
        icon = ICONS.get(task.get("type", "learning"), "📌")
        lines.append(f"  {_fmt(cursor)} – {_fmt(tend)}  {icon} {task['title']}  [{task.get('subject','')}]")
        cursor = tend
        placed += 1
        since_brk += 1

    remaining = len(study_tasks) - placed
    if remaining > 0:
        lines.append(f"  ... +{remaining} more tasks across remaining days")

    total_non_break = len([t for t in s.tasks if t.get("type") != "break"])
    total_minutes   = sum(t.get("duration_minutes", focus_min) for t in s.tasks if t.get("type") != "break")
    free_per_day    = max(int(sum((e - b).total_seconds() / 60 for b, e in free)), 60)
    est_days        = max(1, round(total_minutes / free_per_day))

    header = (
        f"✅ Plan confirmed for {s.goal}!\n"
        f"  {total_non_break} tasks · ~{total_minutes // 60}h {total_minutes % 60}m total · est. {est_days} study days"
    )
    footer = "\nType 'next' to start your first session, or 'schedule' for the full timetable."
    return header + "\n".join(lines) + footer

def _daily_planning_cycle(state: StudentState) -> StudentState:
    """
    Daily Planning Cycle - Called at start of each day.
    Reassesses situation and generates optimized plan for today.
    """
    from datetime import date, timedelta
    
    today = date.today()
    
    # Check revisions due today
    state.today_revisions_due = [
        unit["id"] for unit in state.learning_units
        if unit.get("next_revision") and unit["next_revision"] <= today.isoformat()
    ]
    
    # Check practice due today
    state.today_practice_due = [
        unit["id"] for unit in state.learning_units
        if unit.get("practice_due") and unit["practice_due"] <= today.isoformat()
    ]
    
    # Calculate progress toward deadline
    completed_units = len([u for u in state.learning_units if u.get("status") in ("completed", "mastered")])
    total_units = len(state.learning_units)
    pending_units = total_units - completed_units
    
    # Parse deadline to calculate days remaining
    deadline_str = state.deadline or "10 days"
    nums = re.findall(r"\d+", deadline_str)
    days_remaining = int(nums[0]) if nums else 10
    
    if "tomorrow" in deadline_str.lower():
        days_remaining = 1
    
    # Calculate target units for today
    if days_remaining > 0 and pending_units > 0:
        state.today_target_units = max(1, round(pending_units / days_remaining))
    else:
        state.today_target_units = min(3, pending_units)  # Default: 3 units/day
    
    # Reset daily counters
    state.today_completed_units = 0
    state.recovered_time_minutes = 0
    state.daily_plan_status = "planning"
    
    # Prioritize: Revisions > Practice > New Learning
    priority_units = []
    
    # Add revision-due units first
    for unit_id in state.today_revisions_due:
        unit = next((u for u in state.learning_units if u["id"] == unit_id), None)
        if unit:
            priority_units.append({"unit": unit, "reason": "revision_due", "priority": 1})
    
    # Add practice-due units
    for unit_id in state.today_practice_due:
        unit = next((u for u in state.learning_units if u["id"] == unit_id), None)
        if unit and unit not in [p["unit"] for p in priority_units]:
            priority_units.append({"unit": unit, "reason": "practice_due", "priority": 2})
    
    # Add pending units by subject priority (from strategy)
    priority_subjects = state.structured_strategy.get("priority_order", []) if state.structured_strategy else []
    pending = [u for u in state.learning_units if u.get("status") == "pending"]
    
    for subj in priority_subjects:
        for unit in pending:
            if unit["subject"] == subj and unit not in [p["unit"] for p in priority_units]:
                priority_units.append({"unit": unit, "reason": "new_learning", "priority": 3})
    
    # Add remaining pending units
    for unit in pending:
        if unit not in [p["unit"] for p in priority_units]:
            priority_units.append({"unit": unit, "reason": "new_learning", "priority": 3})
    
    # Store today's prioritized plan
    state.daily_plan_status = "in_progress"
    
    return state


def planner_node(state: dict) -> dict:
    s = StudentState(**state)

    s = _extract_info(s)
    s.planner_stage = _next_stage(s)

    print(f"[Planner] Stage: {s.planner_stage} | Goal: {s.goal} ({s.goal_category})")

    while s.planner_stage in ("analyze_user", "create_strategy", "create_learning_path"):
        if s.planner_stage == "analyze_user":
            s = _analyze_user(s)
            s.planner_stage = "create_strategy"
            continue

        if s.planner_stage == "create_strategy":
            s = _create_strategy(s)
            # Populate learning units after strategy is created
            s = _populate_learning_units(s)
            s.planner_stage = "create_learning_path"
            continue

        if s.planner_stage == "create_learning_path":
            s = _create_learning_path(s)
            s.planner_stage = "review_plan"
            continue

    if s.planner_stage == "collect_topics":
        # after extraction, topic_collection_index was already advanced
        if _all_topics_collected(s):
            # all subjects done, move on
            s.agent_response = _build_question(s)  # will show collect_completed question
        else:
            # still more subjects to collect
            s.agent_response = _build_question(s)

    elif s.planner_stage == "collect_completed":
        # mark flag so _next_stage won't loop back here
        s.goal_specific["completed_topics_asked"] = True
        s.agent_response = _build_question(s)  # next: collect_study_style

    elif s.planner_stage == "review_plan":
        if _is_yes(s.user_message):
            s.planner_stage = "generate_tasks"
            s.available_hours = _calc_available_hours(s.wake_time, s.sleep_time)
            s.tasks = _generate_tasks(s)
            s.planner_stage = "done"
            s.agent_response = _confirm_response(s)
        else:
            # User wants to adjust — update strategy with their feedback
            adjustment = s.user_message.strip()
            s.strategy = []  # clear so _create_strategy regenerates
            s = _create_strategy(s, adjustment=adjustment)
            s.planner_stage = "review_plan"
            s.agent_response = _review_plan_response(s)

    elif s.planner_stage == "generate_tasks":
        # reached only if state was saved mid-session as generate_tasks
        s.available_hours = _calc_available_hours(s.wake_time, s.sleep_time)
        s.tasks = _generate_tasks(s)
        s.planner_stage = "done"
        s.agent_response = _confirm_response(s)

    else:
        s.agent_response = _build_question(s)

    s.history.append({"role": "user", "content": s.user_message})
    s.history.append({"role": "assistant", "content": s.agent_response})

    return s.model_dump()
