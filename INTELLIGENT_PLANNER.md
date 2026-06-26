# Intelligent Planner Architecture — Complete Design

**Status:** Architecture finalized, implementation in progress
**Target:** 95%+ planner completion before Learner Agent integration

---

## 🎯 The 5 Core Responsibilities

### 1. ✅ Planning (95% Complete)

**What it does:**
- Collects student goals, routine, syllabus
- Breaks chapters into learning units
- Creates learning path with dependencies
- Generates study tasks

**Status:**
- ✅ Goal collection working
- ✅ Routine collection working
- ✅ Syllabus parsing working
- ✅ Learning unit breakdown working (8-12 units per chapter)
- ✅ Study mode selection (Focus vs Mixed)
- ✅ Task generation from units

**No major changes needed here.**

---

### 2. 🔄 Scheduling (70% Complete)

**What it should answer:**
> When exactly should this learning unit happen?

**Current state:**
```
Morning  ← Too vague
```

**Target state:**
```
6:00-6:15  Introduction
6:15-6:25  Break
6:25-6:40  FCFS
6:40-6:50  Quick Recap
```

**What's needed:**

#### A. Free-Slot Calculation
```python
Wake: 6 AM
Breakfast: 7:30-8:00 AM
College: 9:00 AM - 4:00 PM
Travel: 30 min (4:00-4:30 PM)
Dinner: 8:00-8:30 PM
Sleep: 11 PM

↓ Calculate free slots

Free slots:
  6:00-7:30    (90 min)
  8:00-9:00    (60 min)
  4:30-8:00    (210 min)
  8:30-11:00   (150 min)

Total: 510 min (8.5 hours)
```

#### B. Time-Block Generation
```python
6:00-6:15   Learn: Introduction to CPU Scheduling
6:15-6:23   Learn: Why scheduling is needed
6:23-6:33   Break (10 min)
6:33-6:48   Learn: FCFS Algorithm
6:48-7:00   Study: FCFS Example
7:00-7:30   Breakfast
```

#### C. Dynamic Timetable Recalculation
- User finishes early → recalculate rest of day
- User finishes late → adjust next slot
- User skips session → redistribute tasks
- User studies extra → update tomorrow's plan

**Files to modify:**
- `app/agents/scheduler.py` — Enhance time-blocking logic

---

### 3. 🔄 Progress Management (80% Complete)

**Current states:**
```
Completed, Partial, Skipped
```

**Enhanced state machine:**
```
pending
  ↓
learning (active session)
  ↓
completed (understood)
  ↓
practicing (reinforcement)
  ↓
revision_due (needs review)
  ↓
mastered (5/5 rating, multiple attempts)
  ↓
archived (in knowledge vault)
```

**State transitions:**

| From | To | Trigger |
|------|-----|---------|
| pending | learning | User starts unit |
| learning | completed | User finishes with rating 3-5 |
| learning | pending | User skips |
| completed | practicing | Practice task scheduled |
| completed | revision_due | Revision date reached |
| practicing | mastered | Multiple successful practice sessions |
| mastered | archived | User archives or auto-archive after 30 days |
| revision_due | completed | Revision session done |

**Implementation:**
- ✅ Status field added to learning_units
- 🔄 State transition logic needed in progress agent
- 🔄 Auto-progression based on mastery

---

### 4. 🔄 Knowledge Tracking (90% Complete)

**Goal:** Complete learning record for every unit

**Current structure (enhanced):**
```python
{
    "id": 4,
    "subject": "OS",
    "chapter": "CPU Scheduling",
    "unit_name": "FCFS Algorithm",
    "unit_type": "concept",
    "status": "completed",
    "mastery": 4,  # 0-5
    "estimated_minutes": 15,
    "actual_time_spent": 18,
    "attempts": 2,
    "last_studied": "2025-01-15T10:30:00",
    "next_revision": "2025-01-16",  # Tomorrow
    "practice_due": "2025-01-17",
    "quiz_score": 80,
    "quiz_attempts": 1,
    "difficulty": "medium",
    "resources": {
        "videos": ["https://youtube.com/..."],
        "diagrams": ["fcfs_diagram.svg"],
        "notes": ["fcfs_notes.md"],
        "practice": ["problem_set_1.pdf"],
        "quiz": ["fcfs_mcq.json"]
    },
    "revision_history": [
        {
            "date": "2025-01-15T10:30:00",
            "rating": 4,
            "notes": "Understood concept well",
            "time_spent": 18
        }
    ],
    "practice_history": [
        {
            "date": "2025-01-15T11:00:00",
            "score": 80,
            "time_spent": 20,
            "questions_attempted": 10
        }
    ],
    "created_at": "2025-01-14T09:00:00",
    "completed_at": "2025-01-15T10:48:00",
    "last_accessed": "2025-01-15T10:48:00",
    "archived_at": None
}
```

**This becomes the student's permanent learning record.**

**Status:**
- ✅ Structure defined
- ✅ Fields added to state
- 🔄 Population logic needed in progress agent
- 🔄 Query interface needed (search, filter, analytics)

---

### 5. 🔄 Decision Making (60% Complete)

**Goal:** Intelligent daily planning engine

#### Example Decisions:

**Scenario 1: Revision overdue**
```
Start of day

↓ Check revisions due

FCFS revision due today

↓ Decision

Highest priority
Schedule first
```

**Scenario 2: Finished early**
```
User finishes in 18 min
Estimated: 45 min
Recovered: 27 min

↓ Decision

Next unit = 15 min → Fits!

Auto-start (if enabled)
OR
Offer choices
```

**Scenario 3: User mastered topic**
```
FCFS mastery = 5

↓ Decision

Skip explanation phase

Schedule practice only
```

**Scenario 4: User requests specific topic**
```
User: "Teach me FCFS"

↓ Decision

Already completed? → Revision mode
Pending? → Schedule immediately
Not in syllabus? → Offer to add
```

**Scenario 5: Missed 3 days**
```
3 days missed

↓ Check deadline

Still 5 days left

↓ Decision

Redistribute tasks
Shorten sessions
Increase daily target
```

**Implementation needed:**
- Daily planning cycle function
- Revision priority engine
- Time recovery handler
- User request parser
- Deadline tracking

---

## 🔄 Daily Planning Cycle

**NEW: Core intelligence loop**

### Morning Planning:
```
Start Day (6:00 AM)
    ↓
Check deadline (7 days left)
    ↓
Check revisions due (FCFS, SJF)
    ↓
Check practice due (Normalization)
    ↓
Check yesterday's progress (2/3 completed)
    ↓
Calculate today's free time (8.5 hours)
    ↓
Generate today's priority list:
  1. FCFS revision (15 min) — due today
  2. SJF revision (15 min) — due today
  3. Normalization practice (20 min) — due today
  4. Round Robin (20 min) — new learning
  5. Priority Scheduling (15 min) — new learning
    ↓
Generate time-blocked timetable
    ↓
Study sessions begin
```

### During Day:
```
User completes task

↓ Update knowledge tracking

↓ Check for time recovery

↓ Offer next action

↓ Recalculate remaining schedule
```

### End of Day:
```
End-of-day review (10:30 PM)
    ↓
Calculate progress:
  • Completed: 4/5 tasks
  • Time: 72 min
  • Mastery: Avg 4.2/5
    ↓
Check if on track for deadline
    ↓
Prepare tomorrow:
  • Revisions due: 2 units
  • Practice due: 1 unit
  • New learning: 3 units
  • Est. time: 90 min
    ↓
Good night message
```

---

## ⚡ Dynamic Time Recovery

**Status:** 🔄 Implemented, needs integration

### Feature: When User Finishes Early

**Example:**
```
Estimated: 45 min
Actual: 25 min
Recovered: 20 min
```

**Option 1: User controls (auto_fill_free_time = False)**
```
⏱ You finished 20 minutes early!

What would you like to do?

1. Start next unit: Scheduling Criteria (15 min)
2. Revise FCFS (10 min quick recap)
3. Practice OS MCQs (15 min)
4. Take an early break

Reply 1-4 or 'continue' to follow schedule.
```

**Option 2: Auto-fill (auto_fill_free_time = True)**
```
⏱ You finished 20 minutes early!
   Auto-starting: Scheduling Criteria (15 min)

Type 'skip' if you'd rather take a break instead.
```

**If next unit too long:**
```
⏱ You finished 20 minutes early!
   Next unit (Round Robin) needs 30 min.

Quick activities:
  • 10-min quick recap of FCFS
  • 15-min practice MCQs
  • Take early break

Type 'recap', 'mcq', or 'break'.
```

**Smart packing:**
```
Recovered: 35 min

↓ Find units that fit

Scheduling Criteria (15 min) ✓
FCFS Problems (20 min) ✓

↓ Schedule both

35 min fully utilized
```

---

## 📊 Planner Intelligence Checklist

Can the planner answer these questions?

| Question | Status |
|----------|--------|
| What should the student study next? | ✅ Yes |
| When exactly should they study it? | 🔄 Partial (needs precise time-blocking) |
| Can they skip it? | ✅ Yes |
| Can they resume later? | ✅ Yes |
| What if they finish early? | ✅ Yes (dynamic time recovery) |
| What if they study extra? | 🔄 Needs implementation |
| What if they miss three days? | 🔄 Partial (shortens sessions, needs redistribution) |
| What revisions are due today? | ✅ Yes (daily planning cycle) |
| Can they change subjects? | ✅ Yes (only if user chooses) |
| Are they on track for deadline? | 🔄 Needs implementation |
| Which unit goes to Learner Agent? | ✅ Yes |

**Completion: 8/11 = 73%**

---

## 🚀 Remaining Work for 95% Completion

### High Priority (This Session):

1. **Precise Time-Blocking** ⭐⭐⭐⭐⭐
   - Enhance scheduler to respect all routine blocks
   - Generate minute-by-minute schedule
   - File: `app/agents/scheduler.py`

2. **Daily Planning Cycle Integration** ⭐⭐⭐⭐⭐
   - Call at start of day
   - Integrate with progress agent
   - File: `app/agents/planner.py` (function exists, needs integration)

3. **Time Recovery Integration** ⭐⭐⭐⭐⭐
   - Complete progress agent integration
   - Test early completion flow
   - File: `app/agents/progress.py` (function exists, needs testing)

### Medium Priority (Next Session):

4. **User Topic Selection** ⭐⭐⭐⭐
   - "Teach me FCFS" → Jump to unit
   - Search learning_units by name
   - File: `app/agents/orchestrator.py`

5. **Focus Mode Enforcement** ⭐⭐⭐⭐
   - Respect study_mode in task ordering
   - Finish subject before switching
   - File: `app/agents/planner.py`

6. **Deadline Tracking** ⭐⭐⭐⭐
   - Daily progress vs deadline
   - "On track" indicator
   - Alerts if falling behind
   - File: `app/agents/planner.py`

### Low Priority (Polish):

7. **Rich Commands** ⭐⭐⭐
   - "Resume yesterday", "Skip today", etc.
   - File: `app/agents/orchestrator.py`

8. **Analytics** ⭐⭐
   - Time per subject, mastery trends
   - File: New `analytics.py`

---

## 📁 File Structure

```
app/
├── state.py              ✅ Enhanced with daily planning fields
├── agents/
│   ├── planner.py        🔄 Added daily_planning_cycle(), needs integration
│   ├── scheduler.py      🔄 Needs precise time-blocking enhancement
│   ├── progress.py       🔄 Added time recovery, needs full integration
│   ├── orchestrator.py   🔄 Needs user topic selection
│   ├── learner.py        ⏸ Wait for planner freeze
│   └── tutor.py          ✅ No changes needed
```

---

## 🎯 Target Experience

### User says: "I'm preparing for semester exam in 10 days"
```
Planner collects info
→ Breaks OS into 11 units, DBMS into 9, DS into 8
→ Creates 28 learning units total
→ Estimates 420 min total (7 hours)
→ Available: 8.5 hours/day
→ Plan: 2-3 days for OS, 2 days DBMS, 1 day DS, rest = revision
```

### Day 1 Morning (6:00 AM):
```
Daily Planning Cycle runs:
  • Revisions due: None (day 1)
  • Practice due: None
  • Target: 5 units today (OS priority)
  • Free time: 8.5 hours
  • Schedule generated:
    6:00-6:10   Intro to CPU Scheduling
    6:10-6:18   Why scheduling needed
    6:18-6:28   Break
    6:28-6:36   Core objectives
    ... etc
```

### User finishes "Intro" in 7 min (estimated 10):
```
⏱ You finished 3 minutes early!
   Auto-starting: Why scheduling needed (8 min)
```

### User finishes day with 5/5 units:
```
🌙 Day Complete!
  • Completed: 5/5 units
  • Mastery: Avg 4.2/5
  • Time: 68 min (vs 75 min estimated)
  • On track: ✅ Yes
  
Tomorrow: 2 revisions + 4 new units
Good night! 😴
```

---

## 🎊 When is the Planner "Complete"?

**Criteria:**
1. ✅ All 5 responsibilities implemented
2. ✅ Daily planning cycle working
3. ✅ Dynamic time recovery working
4. ✅ Precise time-blocking
5. ✅ Knowledge tracking comprehensive
6. ✅ Can answer all 11 intelligence questions
7. ✅ User topic selection working
8. ✅ Focus mode enforced

**Current: 73% → Target: 95%+**

**ETA: 2-3 more focused sessions**

---

## 📝 Next Steps

**This Session:**
1. Test daily planning cycle
2. Test time recovery flow
3. Enhance scheduler time-blocking

**Next Session:**
4. User topic selection
5. Focus mode enforcement
6. Deadline tracking

**Then:** Freeze planner, build Learner Agent.

---

**Bottom Line:**
> The planner should be a smart daily coach, not a static task list generator.

This architecture makes it intelligent.
