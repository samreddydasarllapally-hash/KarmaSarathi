# Planner State Machine & Decision Tree

## Runtime State Machine (Detailed)

### States During Study Session

```
STATE: PLANNING
├─ Entry: Student starts day OR user requests reschedule
├─ Actions:
│  ├─ Load yesterday's progress
│  ├─ Check deadline remaining
│  ├─ Check revisions due today
│  ├─ Calculate available free time
│  ├─ Prioritize units by: [revision_due > new_learning > practice > revision_future]
│  └─ Generate optimized today's schedule
├─ Output: today_timetable with precise start/end times
└─ Exit: Show timetable to user

    ↓ (user accepts timetable)

STATE: WAITING
├─ Entry: Timetable created, awaiting next study session
├─ Actions:
│  ├─ Monitor time
│  ├─ Send reminders at session_start_time
│  ├─ Wait for user interaction
│  └─ Track state for next event
├─ Output: Reminder notification with session details
└─ Exit: User starts learning session OR reschedule request

    ↓ (user starts session)

STATE: LEARNING
├─ Entry: Student opens learning session for active task
├─ Actions:
│  ├─ Activate task (mark as "Learning")
│  ├─ Show learning unit details (chapter, mastery, time allocation)
│  ├─ Activate Learner Agent on standby
│  ├─ Start session timer (planned_end_time = now + planned_duration)
│  ├─ Monitor: Did user finish early?
│  ├─ Monitor: Did user request help?
│  └─ Show "session complete" prompt when user finishes
├─ Branches:
│  ├─ [User asks question] → Call Learner Agent → Return to LEARNING
│  ├─ [User finished early] → TIME_RECOVERY
│  ├─ [User finished on time] → SESSION_COMPLETE
│  └─ [User finished late] → SESSION_COMPLETE (with note)
└─ Exit: Session complete signal received

    ↓ (capture session end time)

STATE: TIME_RECOVERY (only if user finished early)
├─ Entry: current_time < planned_end_time
├─ Calculation: recovered_time = planned_end_time - current_time
├─ Decision Tree:
│  ├─ IF recovered_time > 20 min:
│  │  ├─ Check if next_unit_duration ≤ recovered_time
│  │  ├─ IF yes → Offer: Start next unit?
│  │  └─ IF no → Offer: Revise this unit? Practice? Rest?
│  │
│  ├─ ELIF recovered_time > 10 min:
│  │  └─ Offer: Quick practice (MCQs)? Flashcards? Rest?
│  │
│  └─ ELSE (recovered_time < 10 min):
│     └─ Offer: Quick review? Or skip to next?
│
├─ Actions (if user chooses):
│  ├─ [Start next unit] → Update schedule, go to LEARNING
│  ├─ [Practice this unit] → Add practice task, go to PRACTICE
│  ├─ [Revise now] → Trigger immediate revision, go to REVISION
│  ├─ [Rest] → Extend break, then WAITING for next session
│  └─ [Auto-fill ON] → Pack time intelligently, show new timetable, confirm
│
├─ Output: Recalculated timetable for rest of day
└─ Exit: User chooses action

    ↓ (or on time/late finish)

STATE: SESSION_COMPLETE
├─ Entry: User finishes session (early, on time, or late)
├─ Actions:
│  ├─ Capture actual_end_time
│  ├─ Calculate time_spent = actual_end_time - session_start_time
│  ├─ Ask: How much did you understand? (1-5)
│  ├─ If rating ≤ 2 → Ask: What was difficult?
│  ├─ Update learning unit:
│  │  ├─ mastery = rating
│  │  ├─ time_spent += time_in_session
│  │  ├─ attempts += 1
│  │  └─ last_studied = today
│  └─ Determine next state based on rating + deadline urgency
│
├─ Decision: Next state
│  ├─ IF rating ≥ 4 AND not_mastered_yet → Go to PRACTICE
│  ├─ ELIF rating ≤ 2 → Go to REVISION (immediate 30-min)
│  ├─ ELIF revision_due_soon → Suggest REVISION
│  └─ ELSE → Return to WAITING
│
└─ Exit: Action confirmed

    ↓ (if revision needed)

STATE: REVISION
├─ Entry: Unit needs immediate or scheduled revision
├─ Actions:
│  ├─ Load previous notes/difficulty feedback
│  ├─ Activate Learner Agent (revision mode)
│  ├─ Focus on: weak areas identified in attempts
│  ├─ Show: previous quiz scores, common mistakes
│  ├─ Run revision timer (typically 30 min)
│  └─ Ask same completion questions
│
├─ Output: Updated mastery, new revision schedule
└─ Exit: Revision session complete

    ↓ (or from SESSION_COMPLETE if rating ≥ 4)

STATE: PRACTICE
├─ Entry: Unit mastery sufficient, time for application
├─ Actions:
│  ├─ Load unit resources (MCQs, problem sets)
│  ├─ Activate Learner Agent (practice mode)
│  ├─ Run timed quiz/problems
│  ├─ Track: quiz_score, attempts, time_spent
│  ├─ Ask: Difficulty of questions?
│  └─ Recommend: Revision if score < 70%
│
├─ Output: Practice scores, mastery update
└─ Exit: Practice session complete

    ↓ (user can return to WAITING for next session)

STATE: RESCHEDULING (optional, triggered by user request)
├─ Entry: User says "I can't study at 7pm" OR "Move FCFS to tomorrow"
├─ Actions:
│  ├─ Parse request using LLM
│  ├─ Identify affected tasks
│  ├─ Check: Does moved task fit new slot?
│  ├─ Check: Does it violate dependencies?
│  ├─ Check: Is deadline still achievable?
│  ├─ Apply changes to timetable
│  └─ Show new schedule
│
├─ Output: Updated today_timetable
└─ Exit: Reschedule confirmed → Return to PLANNING or WAITING

    ↓ (at end of day)

STATE: END_OF_DAY_REVIEW
├─ Entry: Night or user ends study session for the day
├─ Actions:
│  ├─ Summarize today:
│  │  ├─ Units completed
│  │  ├─ Total time studied
│  │  ├─ XP earned
│  │  ├─ Streak status
│  │  └─ Any missed sessions?
│  ├─ Archive completed units (if fully mastered)
│  ├─ Update Knowledge Vault
│  ├─ Calculate tomorrow's revision queue
│  └─ Prepare tomorrow's learning units
│
├─ Output: End-of-day summary + XP/badge notifications
└─ Exit: Day marked complete

    ↓ (next day starts)

STATE: NEXT_DAY_PLANNING
├─ Entry: New day begins (student opens app)
├─ Actions:
│  ├─ Load yesterday's actual progress
│  ├─ Recalculate: Days remaining, units left
│  ├─ Prioritize today:
│  │  ├─ Revisions due today (highest)
│  │  ├─ Overdue revisions (critical)
│  │  ├─ New learning units
│  │  └─ Optional practice
│  ├─ Check: Still on track for deadline?
│  ├─ If behind: Compress schedule OR extend deadline discussion
│  ├─ Generate fresh today_timetable
│  └─ Show: "Here's your plan for today"
│
├─ Output: Today's new optimized timetable
└─ Exit: → PLANNING

```

---

## Decision Trees

### Decision Tree 1: What Should Happen Next?

```
Unit Status Check
    ↓
├─ Is revision due TODAY?
│  ├─ YES → Priority: HIGHEST
│  │        Action: Move to top of schedule
│  │        State: REVISION
│  │
│  └─ NO ↓
│
├─ Is revision overdue (past due date)?
│  ├─ YES → Priority: CRITICAL
│  │        Action: Must happen before new learning
│  │        State: REVISION
│  │
│  └─ NO ↓
│
├─ Has user mastered this unit? (rating ≥ 4, multiple attempts)
│  ├─ YES → Priority: PRACTICE
│  │        Action: Skip explanation, go to practice/quiz
│  │        State: PRACTICE
│  │
│  └─ NO ↓
│
├─ Has user seen this unit before? (attempts > 0)
│  ├─ YES (attempts > 1) → Action: Quick recap + practice
│  │       State: PRACTICE
│  │
│  └─ NO (attempts = 0) → Priority: LEARNING
│        Action: Full explanation from Learner Agent
│        State: LEARNING
```

### Decision Tree 2: User Finished Early

```
Session Ends Early
    ↓
Calculate: recovered_time = planned_end - actual_end
    ↓
├─ recovered_time > 30 min
│  ├─ Next unit duration ≤ recovered_time?
│  │  ├─ YES → "Start Preemptive Scheduling now?"
│  │  │        (offers start, revise, practice, rest)
│  │  │
│  │  └─ NO → "You have 30 min free."
│  │           "Options: Revise, Practice, Rest?"
│  │
│  └─ If auto-fill ON:
│     └─ Pack intelligently: short unit + break + practice
│
├─ 20 ≤ recovered_time ≤ 30 min
│  ├─ "You have 25 minutes."
│  ├─ Option 1: Start next unit (if ≤ 20 min)
│  ├─ Option 2: Practice MCQs
│  ├─ Option 3: Revise this unit
│  └─ Option 4: Rest
│
└─ recovered_time < 20 min
   ├─ "You have 15 minutes."
   ├─ Option 1: Quick flashcards
   ├─ Option 2: Rest
   └─ Option 3: Skip to next session
```

### Decision Tree 3: User Missed a Session

```
Session Missed (expected_end_time passed, not marked complete)
    ↓
Check: How many sessions missed?
    ↓
├─ 1 session → Move to next available slot today
│            Action: Keep schedule flexible
│            Notify: "Want to reschedule this?"
│
├─ 2+ sessions → Time crunch detection
│              Check: Are revisions piling up?
│              ├─ YES → Compress schedule
│              │        Defer new learning
│              │        Move revisions to urgent
│              │
│              └─ NO → Extend deadline or focus on mastery
│
└─ 3+ days missed → Catch-up mode
               Action: Priority reset
                 1. Critical revisions first
                 2. Defer low-priority learning
                 3. Extend deadline if needed
                 4. Show: "Can you catch up?"
```

### Decision Tree 4: User Requests Specific Topic

```
User: "Teach me [Topic]"
    ↓
├─ Topic exists in syllabus?
│  ├─ NO → "This topic isn't in your plan."
│  │       "Would you like to add it?"
│  │
│  └─ YES ↓
│
├─ Is it already completed?
│  ├─ YES (mastery ≥ 4) → "You've mastered this!"
│  │                      "Revise? Practice? Quiz?"
│  │
│  └─ NO (pending or partial) ↓
│
├─ Is it in today's schedule?
│  ├─ YES → "It's scheduled at 6:30pm."
│  │        "Want to do it now?"
│  │        ├─ If YES: Pause timetable → Reschedule rest of day
│  │        └─ If NO: Show countdown
│  │
│  └─ NO ↓
│
├─ Dependencies met? (prerequisites completed)
│  ├─ NO → "You need to master [Prerequisite] first."
│  │       "Want to learn that instead?"
│  │
│  └─ YES ↓
│
├─ Time available today?
│  ├─ YES (free slots exist) → "I can teach you in 25 min."
│  │                          "Pause schedule? Start now?"
│  │
│  └─ NO → "No time today."
│          "Schedule for tomorrow?"
│
└─ Action: If user agrees → Pause current timetable
                        → Teach topic
                        → Recalculate rest of day
                        → Show: "Back to your plan"
```

### Decision Tree 5: Daily Planning Cycle

```
Morning: Student Opens App
    ↓
├─ Check: Deadline (days remaining)
│  ├─ ≤ 2 days → Show urgent warning
│  └─ > 2 days → Normal planning
│
├─ Check: Revisions due today
│  └─ Load: All units with revision_due = today
│
├─ Check: Yesterday's progress
│  ├─ Completed units?
│  ├─ Incomplete units? (moved to today)
│  └─ Missed sessions? (count)
│
├─ Calculate: Today's available time
│  └─ Free slots after blocking routine
│
├─ Prioritize today's units:
│  ├─ 1. Revisions due today
│  ├─ 2. Overdue revisions
│  ├─ 3. New learning units (by priority)
│  ├─ 4. Optional practice
│  └─ 5. Optional flashcards
│
├─ Generate: today_timetable
│  ├─ Assign precise start/end times
│  ├─ Include breaks + meals
│  ├─ Show mastery for each unit
│  └─ Show estimated deadline impact
│
├─ Check: Feasibility
│  ├─ Will tasks fit in available time?
│  ├─ Is deadline still achievable?
│  ├─ If NO: Show: "You're behind. Options:"
│  │        1. Extend deadline
│  │        2. Drop low-priority topics
│  │        3. Compress breaks
│  │        4. Study extra
│  │
│  └─ If YES: Continue
│
├─ Show: "Here's today's plan"
│  ├─ Display timetable
│  ├─ Show: Total units, revisions, practice
│  └─ Offer: Customize?
│
└─ Student begins study
```

---

## Implementation Guide: Adding Decision Engine

### File Structure

```
app/agents/
├─ planner.py (existing) ← No changes
├─ scheduler.py (existing) ← Enhance _blocked_intervals
├─ progress.py (existing) ← Enhance session tracking
├─ time_recovery.py (NEW) ← Handle early finishes
├─ planner_logic.py (NEW) ← Decision trees
├─ knowledge_tracker.py (NEW) ← Learning unit profiles
├─ daily_planner.py (NEW) ← Daily planning cycle
└─ state_machine.py (NEW) ← Runtime state management
```

### Key Functions to Add

#### time_recovery.py
```python
def handle_early_finish(unit_id, planned_end, actual_end):
    """
    Called when a learning session ends early.
    Returns: user choices OR auto-packed schedule
    """
    
def calculate_time_packing(available_minutes, remaining_units):
    """
    Intelligently pack small learning units into available time.
    Returns: list of units that fit + their times
    """

def recalculate_rest_of_day(current_task_id, recovered_time):
    """
    Regenerate rest of day's timetable with recovered time.
    Returns: updated today_timetable
    """
```

#### planner_logic.py
```python
def decide_next_state(unit_state, deadline_urgency, user_mastery):
    """
    Determine: Should this unit go to LEARNING, PRACTICE, REVISION, or WAITING?
    """

def prioritize_today_units(learning_units, deadline_days_remaining):
    """
    Sort today's units by: revision_due > overdue > new_learning > optional
    """

def handle_missed_sessions(missed_count, learning_units):
    """
    Adjust schedule if student missed sessions.
    """

def route_topic_request(user_request, learning_units, user_mastery):
    """
    When user says "Teach me FCFS", determine action.
    """
```

#### knowledge_tracker.py
```python
class LearningUnit:
    id: str
    subject: str
    chapter: str
    unit_name: str
    
    # Current state
    status: str  # Pending | Learning | Completed | Practicing | Revision Due | Mastered | Archived
    
    # Metrics
    mastery: int  # 1-5
    time_spent: int  # minutes total
    attempts: int
    last_studied: date
    next_revision: date
    
    # Resources & performance
    practice_pending: bool
    quiz_score: float  # 0-100
    notes_available: bool
    videos_saved: bool
    
    # Feedback
    difficulty_feedback: str
    strength: str
    weakness: str

def update_unit_mastery(unit_id, rating, time_spent):
    """Update mastery score and schedule next revision."""

def get_units_due_today():
    """Return all units with revision_due = today."""

def get_catchup_priority(missed_days):
    """Return prioritized list of units to catch up on."""
```

#### daily_planner.py
```python
def morning_planning_cycle(student_state):
    """
    Every morning:
    1. Check deadline
    2. Check revisions due
    3. Check yesterday's actual progress
    4. Calculate available time
    5. Generate today's timetable
    """

def end_of_day_review(student_state):
    """
    End of day:
    1. Tally today's progress
    2. Update learning records
    3. Prepare tomorrow's queue
    """

def calculate_deadline_feasibility(units_left, days_remaining, avg_time_per_unit):
    """
    Can the student meet the deadline?
    Returns: feasible | behind | urgent
    """
```

---

## Testing Strategy

### Unit Tests
- `test_time_recovery.py`: Early finish scenarios
- `test_planner_logic.py`: Decision trees
- `test_knowledge_tracker.py`: Mastery calculations
- `test_daily_planner.py`: Daily cycle

### Integration Tests
- Multi-day study session (PLANNING → LEARNING → TIME_RECOVERY → PRACTICE → END_OF_DAY → NEXT_DAY)
- Missed sessions (PLANNING → WAITING → SESSION_MISSED → RESCHEDULING)
- Topic requests (LEARNING → RESCHEDULING → new LEARNING)

### Acceptance Tests
- Student can study for 5 days without manual intervention
- Planner automatically handles early finishes
- Daily cycle creates fresh optimized timetable
- Knowledge vault tracks all metrics correctly

---

## Phase 2 Milestones

**Week 1:** Dynamic Scheduling
- [ ] Precise time blocks per unit
- [ ] Time recovery logic
- [ ] Early finish detection

**Week 2:** Knowledge Tracking
- [ ] Learning unit profiles
- [ ] Mastery calculations
- [ ] Vault functionality

**Week 3:** Decision Engine
- [ ] All 5 decision trees implemented
- [ ] State machine routing
- [ ] Topic request handling

**Week 4:** Daily Planning Cycle
- [ ] Morning planning routine
- [ ] End-of-day review
- [ ] Deadline feasibility checker

**Final:** Testing & Freeze
- [ ] Integration tests pass
- [ ] 5-day study session works
- [ ] Documentation updated
- [ ] Ready for Learner Agent
