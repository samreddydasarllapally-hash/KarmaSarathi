# KarmaSarathi — AI Study OS Architecture

## System Overview

KarmaSarathi is an adaptive learning system with **dual-mode operation**:

1. **Planner-driven mode** — structured timetable with automatic scheduling
2. **Learner-agent-driven mode** — on-demand learning with multi-modal explanations

---

## Core Components

### 1. Planner Agent (`planner.py`)
**Role:** Collects student profile and generates personalized study strategy

**Key Features:**
- Goal detection (exam, hackathon, competitive)
- Routine-aware scheduling
- Subject confidence mapping
- Adaptive task generation based on deadline intensity
- Strategy creation using LLM hints + Python logic

**Output:**
- `tasks` — list of learning/practice/revision tasks
- `structured_strategy` — priority order, daily schedule, practice subjects
- `learning_path` — dependency-ordered roadmap

---

### 2. Scheduler Agent (`scheduler.py`)
**Role:** Converts task list into time-blocked daily schedule

**Key Features:**
- Blocked interval computation (meals, college, gym, travel)
- Free slot detection
- Multi-day plan distribution
- Subject interleaving (prevents burnout)
- Water reminders

**Output:**
- `today_schedule` — hour-by-hour timetable with start/end times
- `day_plan` — tasks distributed across deadline days

---

### 3. Progress Agent (`progress.py`)
**Role:** Daily execution loop with gamification and adaptive feedback

**Stages:**
- `ask_completion` → Did you complete? (Yes/Partial/No)
- `ask_rating` → Understanding 1-5
- `ask_partial` → How much covered?
- `ask_reason` → What stopped you? (busy/hard/tired/forgot/confused)

**Key Features:**
- **Spaced Repetition System:**
  - Auto-schedules revision: day+1, day+3, day+7
  - Rating-based intervals (lower rating = more revision)
  
- **Knowledge Vault (Archive System):**
  - Topics marked "complete" → archived
  - Removes active study tasks
  - **Keeps revision tasks** (revision-only mode)
  - Stores mastery rating, difficulty notes

- **Adaptive Learning:**
  - Low rating (1-2) → auto-add 30-min revision
  - High rating (4-5) → convert study → practice
  - Confidence ≥7 → promote remaining tasks to practice mode
  
- **Gamification:**
  - XP system with bonuses (difficult subject, streak, understanding)
  - Streak tracking with badges (3d, 7d, 14d, 30d)
  - Topic milestones (1, 10, 25 topics)

---

### 4. Learner Agent (`learner.py`) — **ENHANCED**
**Role:** On-demand multi-modal learning engine

**Input Layer:**
- User message: "explain DBMS Normalization"
- Context from active task (topic + subject)

**Processing Layer:**
- Generates explanation adapted to `learning_style` (videos/books/practice/notes)
- Creates SVG diagram using LLM
- Suggests 2-3 YouTube search queries
- Generates 5 MCQs with explanations

**Output Layer:**
```json
{
  "explanation": "text explanation",
  "svg": "<svg>...</svg>",
  "videos": ["search query 1", "query 2", "query 3"],
  "mcqs": [{"q": "...", "opts": [...], "ans": "A", "why": "..."}],
  "funny_analogy": "placeholder for humor hooks"
}
```

**Bridge with Planner:**
- User can call learner agent **during active task**
- Orchestrator detects keywords: "diagram", "video", "mcq", "quiz"
- Routes to learner → returns to progress loop after

---

### 5. Tutor Agent (`tutor.py`)
**Role:** Adaptive teaching with multi-layer explanations

**Layers:**
1. Simple explanation
2. Detailed breakdown
3. Visual examples
4. Practice problems
5. Real-world applications

**Smart fallback:** If user doesn't understand, simplifies further.

---

### 6. Orchestrator (`orchestrator.py`)
**Role:** Intent router and state machine controller

**Routing Logic:**
1. Planner mid-stage → planner
2. Tutor active → tutor
3. **NEW:** Active task + learner keyword → learner (bridge)
4. Progress loop active → progress
5. Reschedule trigger → scheduler
6. Default → classify intent

**Bridge Feature:**
- User studying "DBMS Normalization"
- Types "show me a diagram"
- Orchestrator → learner agent
- After explanation → back to progress loop

---

## Key Design Principles

### 1. Spaced Repetition ≠ Deletion
**Problem:** User completes topic → forgets it forever

**Solution:**
- Completed topic → `archived` status
- Moves to **Knowledge Vault**
- Study/practice tasks removed
- **Revision tasks remain active**
- Auto-schedules day+1, day+3, day+7 revisions

**Example:**
```
Day 0: Study DBMS Normalization → complete (rating 3/5)
Day 1: Quick recap (15 min) — auto-scheduled
Day 3: Medium revision (20 min) — auto-scheduled
Day 7: Final checkpoint (25 min) — auto-scheduled
```

### 2. Archive = Revision-Only Mode
**DELETE button behavior:**
```python
def _archive_topic(topic, subject):
    # ❌ NOT removed from system
    # ✔ Moved to knowledge_vault
    # ✔ status = "archived"
    # ✔ revision_only = True
    # ✔ Future revision tasks remain
```

**User can view vault:**
```
vault
🗃️ Knowledge Vault:
  DBMS  Normalization  ★★★☆☆  (revision only)
  OS    Scheduling     ★★★★☆  (revision only)
```

### 3. Learner Agent = AI Study OS
**NOT just Q&A — multi-modal teacher:**

| Traditional Tutor | Learner Agent |
|------------------|---------------|
| Text explanation | Text + SVG + Video + MCQ |
| One learning style | Adapts to user's style |
| Linear flow | Jump-in anytime |
| No visuals | Auto-generates diagrams |

**Use cases:**
- Study from timetable → stuck on concept → "explain with diagram" → learner agent
- Free time → "teach me Operating System scheduling" → learner agent
- Revision task → "give me MCQs on DBMS" → learner agent

### 4. Adaptive Task Evolution
**Smart task promotion based on confidence:**

```
Confidence ≤4  → Study tasks (focus mode)
Confidence 5-6 → Mixed study + practice
Confidence ≥7  → Auto-convert to Practice tasks
```

**Example:**
```
Day 1: Study Data Structures (confidence 4/10)
User completes 3 topics with rating 4+
Confidence → 7/10
System: "You're confident now. Remaining tasks → Practice mode"
Day 4: Practice Data Structures — Numericals & MCQs
```

---

## State Management

### Critical State Fields

```python
# Knowledge Vault (never truly deleted)
knowledge_vault: list[dict] = [
    {
        "subject": "DBMS",
        "topic": "Normalization",
        "mastery": 3.5,  # avg of all ratings
        "ratings": [3, 4, 3],
        "difficulty_notes": ["theory", "too many concepts"],
        "status": "archived",
        "revision_only": True
    }
]

# Spaced Repetition Queue
revision_queue: list[dict] = [
    {
        "topic": "Normalization",
        "subject": "DBMS",
        "rating": 3,
        "schedules": ["day+1", "day+3", "day+7"],
        "source_task_id": 12,
        "created_at": "2025-01-15T10:30:00"
    }
]

# Learner Output (multi-modal content)
learner_output: dict = {
    "topic": "Normalization",
    "subject": "DBMS",
    "explanation": "...",
    "svg": "<svg>...</svg>",
    "videos": ["query1", "query2"],
    "mcqs": [...]
}

# Task with spaced repetition metadata
{
    "id": 45,
    "title": "Quick recap: Normalization",
    "type": "revision",
    "spaced_day_offset": 1,  # day+1
    "available_on": "2025-01-16T00:00:00",
    "created_from": 12,  # source task ID
    "status": "pending"
}
```

---

## Workflow Examples

### Example 1: Timetable-driven study with learner bridge
```
User: I'm preparing for semester exam in 10 days
→ Planner collects info → generates tasks
→ Scheduler builds today's timetable

User: next
→ Progress: "Study DBMS Normalization?"
User: 1 (yes)
→ Progress: "Rate understanding 1-5"
User: 3
→ Progress: ✅ complete, XP awarded, revision scheduled day+1/+3/+7

User: show me a diagram of normalization
→ Orchestrator detects "diagram" → routes to learner
→ Learner: generates SVG + explanation + videos + MCQs
User: next
→ Returns to progress loop
→ Progress: "Next task: Study OS Scheduling"
```

### Example 2: Archive topic but keep revisions
```
User: archive Normalization from DBMS
→ Progress: moves to knowledge_vault
→ Removes pending study/practice tasks for "Normalization"
→ KEEPS revision tasks (day+3, day+7)
→ Response: "🗃️ Normalization archived. Mastery: 3.5/5 · Revisions still scheduled"

User: vault
→ Shows all archived topics with mastery stars
```

### Example 3: Free exploration with learner
```
User: teach me Operating System scheduling algorithms
→ Orchestrator: "teach me" → learner
→ Learner:
  - Explanation (adapted to user's learning_style)
  - SVG diagram (generated via LLM)
  - Video suggestions (3 search queries)
  - 5 MCQs with explanations

User: next
→ Returns to schedule
```

---

## Implementation Status

✅ **Completed:**
- Planner with adaptive strategy
- Scheduler with blocked intervals
- Progress loop with gamification
- Spaced repetition system (day+1/+3/+7)
- Knowledge vault (archive → revision-only)
- Enhanced learner agent (SVG, videos, MCQs)
- Orchestrator bridge (task → learner → task)

🔄 **Next Steps (from your document):**
1. ~~Revision scheduler~~ ✅ DONE
2. ~~Archive system~~ ✅ DONE
3. ~~Learner agent enhancements~~ ✅ DONE
4. ~~Planner → learner handoff~~ ✅ DONE
5. 🔜 Funny analogies / memory hooks
6. 🔜 Audio explanation (TTS)
7. 🔜 Animated step-by-step diagrams

---

## Usage Commands

### Planner Mode
```
I'm preparing for semester exam in 10 days
I have DS, OS, DBMS subjects
```

### Progress Mode
```
next                  # Start next task
summary              # View overall progress
roadmap              # Subject-wise roadmap
vault                # View archived topics
archive <topic>      # Archive a topic
```

### Learner Mode
```
explain DBMS Normalization
show me a diagram of OS scheduling
teach me Data Structures
give me MCQs on DBMS
```

### Scheduler Mode
```
schedule             # Show today's timetable
plan                 # Multi-day plan
reschedule           # Rebuild schedule
```

---

## Technical Stack

- **Framework:** LangGraph (state machine)
- **LLM:** Gemini (via `ask_gemini` wrapper)
- **State:** Pydantic models
- **Diagrams:** SVG generation via LLM
- **Storage:** In-memory state (persisted via main.py)

---

## Future Enhancements

1. **PDF Upload → Syllabus Extraction**
2. **Voice mode** (TTS for explanations)
3. **Collaborative study** (team hackathons)
4. **Performance analytics dashboard**
5. **Mobile app with push notifications**
6. **Integration with Google Calendar**

---

**Last Updated:** 2025-01-15
**Architecture Version:** 2.0 (Post-Revision)
