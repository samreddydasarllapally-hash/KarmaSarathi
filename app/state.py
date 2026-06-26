from typing import Optional, Literal
from pydantic import BaseModel


class StudentState(BaseModel):
    # --- Core ---
    user_message: str = ""
    history: list[dict] = []

    # --- Orchestrator ---
    intent: Optional[Literal["planner", "tutor", "research", "progress", "scheduler", "learner", "knowledge_tracker", "daily_planner", "unknown"]] = None
    agent_response: Optional[str] = None

    # --- Planner: collected info ---
    goal: Optional[str] = None
    goal_category: Optional[str] = None       # "project" | "exam" | "competitive"
    goal_category_locked: bool = False
    deadline: Optional[str] = None

    routine: dict = {}
    wake_time: Optional[str] = None           # kept for _calc_available_hours
    sleep_time: Optional[str] = None

    topics: list[str] = []
    subjects: list[dict] = []
    goal_specific: dict = {}
    focus_duration: Optional[str] = None
    break_duration: Optional[str] = None
    productivity_peak: Optional[str] = None
    energy_peak: Optional[str] = None
    learning_style: Optional[str] = None      # "videos"|"books"|"notes"|"practice"|"mixed"
    study_mode: Optional[str] = None          # "focus"|"mixed" - Focus finishes one subject before moving to another
    syllabus_method: Optional[str] = None     # "paste"|"manual"|"upload"|"generated"
    learning_content_source: Optional[str] = None

    # --- Planner: stage machine ---
    planner_stage: Literal[
        "collect_goal",
        "collect_deadline",
        "collect_routine",
        "collect_routine_detail",
        "collect_goal_specific",
        "collect_subjects",
        "collect_study_mode",
        "collect_syllabus_method",
        "collect_syllabus_input",
        "collect_topics",
        "collect_completed",
        "collect_study_style",
        "collect_energy",
        "collect_learning_style",
        "analyze_user",
        "create_strategy",
        "create_learning_path",
        "review_plan",
        "generate_tasks",
        "done"
    ] = "collect_goal"

    topic_collection_index: int = 0
    routine_step: int = 0

    # --- Planner: analysis and strategy ---
    analysis_notes: list[str] = []
    study_strategy: dict = {}
    strategy: list[dict] = []
    structured_strategy: dict = {}
    learning_path: list[dict] = []
    topic_graph: list[dict] = []
    learning_roadmap: list[dict] = []

    # --- Planner: output ---
    available_hours: float = 0.0
    tasks: list[dict] = []
    current_task_index: int = 0

    # --- Daily Planning Cycle ---
    current_day: int = 1                      # Day number in study plan (1, 2, 3, ...)
    daily_plan_status: str = "not_started"    # "not_started"|"planning"|"in_progress"|"completed"|"reviewing"
    today_revisions_due: list[int] = []       # Learning unit IDs with revision due today
    today_practice_due: list[int] = []        # Learning unit IDs with practice due today
    today_target_units: int = 0               # Target learning units to complete today
    today_completed_units: int = 0            # Actual completed today
    recovered_time_minutes: int = 0           # Time recovered from early completions today
    auto_fill_free_time: bool = True          # Auto-start next unit when finishing early
    
    # --- Dynamic Time Recovery ---
    pending_recovery_action: Optional[dict] = None  # {time_minutes, options, context}
    
    # --- Scheduler ---
    today_schedule: list[dict] = []           # time-blocked slots for today
    day_plan: list[dict] = []                 # multi-day plan [{"day": 1, "date": "Mon 12 Jan", "tasks": [...]}]
    today_date: Optional[str] = None          # ISO date string of today's schedule
    last_scheduled_at: Optional[str] = None  # ISO time string of last schedule generation
    reschedule_needed: bool = False           # set by progress agent to trigger rescheduling
    daily_goal_count: int = 0                 # target tasks for today
    completed_today: int = 0                  # tasks completed today

    # --- Daily execution loop ---
    # Stages: "idle"|"ask_completion"|"ask_rating"|"ask_difficulty_detail"|"ask_partial"|"ask_reason"
    daily_loop_stage: str = "idle"
    active_task_id: Optional[int] = None
    xp: int = 0
    streak: int = 0
    badges: list[str] = []
    missed_days: int = 0
    total_study_minutes: int = 0              # accumulated across all completed tasks

    # --- Tutor ---
    current_task: Optional[str] = None
    current_task_type: Optional[str] = None
    tutor_layer: int = 1
    tutor_status: Optional[str] = None

    # --- Learning Units Database (Core Architecture) ---
    # Hierarchical: Subject → Chapter → Learning Unit
    # This is the PRIMARY structure for scheduling and tracking
    # Each learning unit: {
    #   id, subject, chapter, unit_name, unit_type ('concept'|'example'|'practice'|'quiz'),
    #   status ('pending'|'learning'|'completed'|'practicing'|'revision_due'|'mastered'|'archived'),
    #   completion_pct (0-100), mastery (0-5),
    #   estimated_minutes, actual_time_spent,
    #   revision_due (ISO date), practice_due (ISO date),
    #   difficulty ('easy'|'medium'|'hard'), attempts (int),
    #   last_studied (ISO datetime), next_revision (ISO date),
    #   quiz_score (0-100), quiz_attempts (int),
    #   resources: {videos: [], diagrams: [], notes: [], practice: [], quiz: []},
    #   revision_history: [{date, rating, notes, time_spent}],
    #   practice_history: [{date, score, time_spent, questions_attempted}],
    #   created_at, completed_at, last_accessed, archived_at
    # }
    learning_units: list[dict] = []
    
    # --- Knowledge Vault (archived topics — never truly deleted) ---
    # Each entry: {subject, topic, mastery, ratings, difficulty_notes, archived_on, revision_due_days: [1,3,7]}
    knowledge_vault: list[dict] = []

    # --- Spaced Repetition Queue ---
    # Each entry: {task_id, topic, subject, due_day_offset, duration_minutes, created_on_task_id}
    revision_queue: list[dict] = []

    # --- Learner agent outputs (svg, mcqs, video suggestions, revision notes)
    learner_output: dict = {}
    
    # --- Revision Notes Storage (personalized notes for each completed topic)
    # Each entry: {topic, subject, key_points, common_mistakes, remember, revision_time, created_at}
    revision_notes_db: list[dict] = []

    # --- Inter-Agent Handoff (the network backbone)
    # Signals which agent should run next after current agent finishes
    # Format: {"to": "learner"|"planner"|"research", "reason": str, "context": dict}
    agent_handoff: Optional[dict] = None
    # Where to return after a handoff completes (e.g. research → learner → research)
    return_to_agent: Optional[str] = None
    return_context: dict = {}  # preserved state for when we return

    # --- Research Agent outputs
    # Keyed by topic: {curiosity_map, connections, resources, projects, innovation_prompt}
    research_output: dict = {}

    # --- Research Workspace (persistent project notebook)
    # Each entry: {id, title, problem_statement, required_skills, known_skills, missing_skills,
    #              notes, papers, ideas, progress, status, created_at, updated_at}
    research_workspace: list[dict] = []
    active_research_id: Optional[str] = None  # currently open research project

    # --- Research Notebook (living portfolio per topic)
    # Each entry: {id, topic, problem_statement, hypotheses, papers, ideas,
    #              experiments, reflections, future_work, created_at, last_updated}
    research_notebook: list[dict] = []

    # --- Research Agent State ---
    # Current stage within a research session (0 = not started, 1-7 = pipeline stages)
    research_stage: int = 0
    # Current research mode
    research_mode: str = "explore"  # "explore"|"problem_finder"|"idea_generator"|"build_mentor"|"reflection"|"paper"

    # --- Student Research Profile (living innovation portfolio) ---
    # Tracks everything across all research sessions
    student_research_profile: dict = {}
    # {
    #   "applications_viewed": 0,
    #   "problems_explored": 0,
    #   "ideas_generated": 0,
    #   "projects_started": 0,
    #   "projects_completed": 0,
    #   "papers_read": 0,
    #   "innovation_score": 0,
    #   "research_level": "beginner",  # beginner|intermediate|advanced
    #   "prototype_built": false,
    #   "research_sessions": []  # [{topic, duration_min, mode, timestamp}]
    # }

    # --- Temp fields for inter-agent handoffs ---
    # Topic just mastered — used by progress agent for post-mastery offer
    post_mastery_topic: str = ""
    # Set True when student expresses curiosity mid-learner session
    learner_to_research_pending: bool = False
