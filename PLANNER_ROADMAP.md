# KarmaSarathi Planner — Complete Roadmap to Stability

**Status:** 90–95% Complete  
**Phase:** Stabilization before Learner Agent  
**Target:** Freeze Planner architecture with intelligent decision engine  

---

## Overview: Five Planner Responsibilities

### 1. ✅ Planning (95% Complete)
The planner already knows what to teach.

**Currently implemented:**
- ✅ Collects goals (exam, hackathon, competitive)
- ✅ Collects routine (meals, college, gym, travel, fixed activities)
- ✅ Collects syllabus (subjects → chapters)
- ✅ Breaks chapters into learning units
- ✅ Detects study mode (Focus | Mixed)
- ✅ Creates learning path with dependency ordering
- ✅ Generates task types (learning, practice, revision)

**No major changes needed.** This foundation is solid.

---

### 2. 🔄 Scheduling (60% Complete)
The planner knows what, but not exactly when and how to adapt.

**Currently implemented:**
- ✅ Basic routine-aware time blocking (meals, college, gym)
- ✅ Free slot detection
- ✅ Multi-day distribution

**Missing:**
- ❌ Precise time allocation per learning unit (6:00–6:15 Learn, 6:15–6:25 Break, 6:25–6:40 Practice)
- ❌ Dynamic timetable recalculation
- ❌ Early completion handling → time recovery
- ❌ Late completion rescheduling
- ❌ Missed session recovery
- ❌ User-requested rescheduling
- ❌ Time packing (fill small gaps with short units)
- ❌ Next-day carryover logic

**Priority:** **⭐⭐⭐⭐⭐ CRITICAL**

This is where the planner becomes adaptive. Right now:
```
Morning (static)
↓
Schedule created once at day start
↓
No adjustment if user finishes early/late
```

Should be:
```
Morning (dynamic)
↓
User finishes CPU Scheduling in 25 min (planned: 45)
↓
Planner recovers 20 minutes
↓
Recalculates rest of day
↓
Offers choices or auto-fills
```

---

### 3. 🔄 Progress Management (70% Complete)
Status tracking exists but is too simple.

**Currently implemented:**
- ✅ Completion tracking (Yes/Partial/No)
- ✅ Understanding rating (1-5)
- ✅ Spaced repetition scheduling
- ✅ Archive system (Knowledge Vault)
- ✅ Attempt counting
- ✅ Time tracking per topic

**Missing:**
- ❌ Unified status field with full lifecycle:
  - `Pending` → scheduled but not started
  - `Learning` → currently active
  - `Completed` → finished learning phase
  - `Practicing` → in practice mode
  - `Revision Due` → marked for review
  - `Mastered` → high confidence, revision-only
  - `Archived` → mastered, stored in vault

**Priority:** ⭐⭐⭐⭐☆

This makes tracking intuitive and supports all downstream decisions.

---

### 4. ❌ Knowledge Tracking (10% Complete)
**THE BIGGEST MISSING PIECE.** This becomes the student's learning record.

**Currently implemented:**
- Partial state tracking in StudentState

**Missing:**
- ❌ Unified Learning Unit Profile

Each learning unit should store:
```python
{
  "id": "OS-CH3-U2",
  "subject": "OS",
  "chapter": "CPU Scheduling",
  "unit_name": "FCFS",
  "status": "Mastered",
  
  "mastery": 4,           # 1-5 scale
  "time_spent": 38,       # minutes
  "attempts": 2,
  "last_studied": "2025-06-25",
  "next_revision": "2025-06-27",
  
  "practice_pending": True,
  "quiz_score": 80,       # %
  "notes_available": True,
  "videos_saved": True,
  
  "difficulty_feedback": "Could use more practice on edge cases",
  "strength": "Understands basic concept",
  "weakness": "Struggles with waiting time calculation"
}
```

**Priority:** ⭐⭐⭐⭐⭐ CRITICAL

This is the "brain" of the planner. Every decision flows from this data.

---

### 5. ❌ Decision Making (20% Complete)
The planner should think, not just schedule.

**Currently implemented:**
- Basic task assignment logic

**Missing:**
- ❌ Intelligent decision engine

Examples the planner should handle:

**Scenario 1: Revision Overdue**
```
Check: Any revision due today?
  ↓
  Yes → Highest priority
  ↓
Move to top of today's schedule
```

**Scenario 2: Finished Early**
```
User completes FCFS in 25 min (planned: 45)
  ↓
Recovered time: 20 min
  ↓
Is next unit ≤20 min?
  ↓
  Yes → Start it
  No → Offer choices: revise, practice, early break
```

**Scenario 3: Mastered Unit**
```
User mastered FCFS (rating: 5, multiple attempts)
  ↓
Skip explanation phase
  ↓
Schedule practice + revision only
```

**Scenario 4: User-Requested Topic**
```
User: "Teach me FCFS"
  ↓
Already completed?
  ↓
  Yes → Resume practice phase
  No → Pause timetable, schedule immediately
```

**Scenario 5: Multiple Missed Days**
```
User missed 3 days
  ↓
Revision units piling up
  ↓
Compress schedule:
  - Critical revisions → today
  - Defer new learning
  - Extend deadline
```

**Priority:** ⭐⭐⭐⭐⭐ CRITICAL

This separates a smart planner from a scheduler.

---

## Runtime State Machine

The planner should always be in one of these states during a study session:

```
┌─────────────────────────────────────────┐
│     Daily Initialization                 │
│  (Check deadline, revisions, progress)   │
└────────┬────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│     Planning State                       │
│  (Assess today's capacity & create      │
│   optimized timetable)                  │
└────────┬────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│     Waiting State                        │
│  (Timetable created, awaiting next      │
│   session or user action)               │
└────────┬────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│     Learning State                       │
│  (Active learning session with learner  │
│   agent on standby)                     │
└────┬─────────────────────┬──────────────┘
     ↓ (early finish)      ↓ (on time or late)
┌──────────────┐    ┌──────────────────┐
│Time Recovery │    │Session Complete  │
│& Adaptation  │    │& Rating          │
└──────┬───────┘    └────────┬─────────┘
       └───────┬─────────────┘
              ↓
┌─────────────────────────────────────────┐
│     Revision State (if needed)           │
│  (Immediate follow-up revisions for     │
│   low ratings)                          │
└────────┬────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│     Practice State                       │
│  (MCQs, quizzes, problem-solving)       │
└────────┬────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│     Rescheduling State (optional)        │
│  (If user requests changes or system    │
│   needs to adapt)                       │
└────────┬────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│     End-of-Day Review                    │
│  (Tally progress, prepare tomorrow)      │
└────────┬────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│     Next Day Planning                    │
└─────────────────────────────────────────┘
```

---

## The "Brain": Events That Wake the Planner

The planner should react to:

### Event 1: User Finishes Early ⭐⭐⭐⭐⭐
**Current behavior:** Nothing (time is lost)  
**Desired behavior:**
```
BEFORE:
4:30–5:15  Study CPU Scheduling (planned: 45 min)
5:15–5:45  Revision
5:45–5:55  Break
5:55–6:40  Study Deadlocks

USER FINISHES AT 4:55 (25 min)

AFTER:
4:55–5:05  Recovered time available
  ↓
  → Offer: Start next unit? Revise? Practice? Rest?
  ↓
  → If "start next": Auto-pack learning unit if ≤ 20 min
  ↓
  → If no: Respect choice, show when to continue
```

### Event 2: User Misses a Session
**Current behavior:** Task remains pending  
**Desired behavior:**
```
Planned: 5:15–5:45 Revision Session A

USER DIDN'T COMPLETE

Planner thinks:
  1. Revision overdue?
  2. How many days missed?
  3. Are future revisions stacking?
  4. Can we compress schedule?
  ↓
Actions:
  - Move Session A to today (high priority)
  - Defer new learning
  - Extend other deadlines if needed
  - Notify user
```

### Event 3: User Studies Extra
**Current behavior:** Extra work is noted, but not leveraged  
**Desired behavior:**
```
User completes 2 extra topics

Planner thinks:
  1. Mark completed
  2. Unlock dependent topics
  3. Can we compress schedule?
  4. Can we free up revision time?
  ↓
Actions:
  - Update mastery & difficulty
  - Unlock next units
  - Recalculate deadline feasibility
  - Adjust tomorrow's schedule
```

### Event 4: User Requests a Specific Topic
**Current behavior:** Not implemented  
**Desired behavior:**
```
User: "Teach me FCFS"

Planner thinks:
  1. Already completed?
  2. Is it in today's schedule?
  3. How long will it take?
  ↓
If already done:
  → Resume practice/revision phase
  → Show mastery score
  
If not started:
  → Pause timetable (with user consent)
  → Schedule immediately
  → Reallocate rest of day
  → Resume timetable after
```

### Event 5: User Says Deadline Changed
**Current behavior:** Manual reset needed  
**Desired behavior:**
```
User: "I only have 5 days now" (was 10)

Planner thinks:
  1. Recalculate: what's possible in 5 days?
  2. Which topics are most important?
  3. Can we compress?
  4. What must be dropped to focus?
  ↓
Actions:
  - Recalculate learning path priority
  - Compress schedule (reduce breaks? shorter explanations?)
  - Move less critical topics to "optional"
  - Show realistic projections
```

---

## Daily Planning Cycle ⭐⭐⭐⭐⭐

**This is the feature that makes the planner feel intelligent.**

Instead of:
```
Day 1: Create full 10-day plan
Days 2-10: Only react to task completions
```

Do:
```
Every morning:
  1. Check deadline remaining
  2. Check revisions due today
  3. Check unfinished learning units
  4. Assess yesterday's actual progress
  5. Calculate today's available free time
  6. Generate TODAY'S timetable (fresh optimization)
  7. Show user the day's structure
  ↓
During the day:
  8. Continuously update as sessions complete
  9. Dynamically recover time from early finishes
  10. Adapt based on user feedback
  ↓
End of day:
  11. Review what happened
  12. Mark completions & update mastery
  13. Calculate tomorrow's strategy
```

**Benefits:**
- Not rigid: adapts to real progress daily
- Resilient: if user missed a day, tomorrow's plan accounts for it
- Optimized: each day is planned fresh with latest data
- Intelligent: uses actual learning speed, not estimates

---

## Feature 14: Dynamic Time Recovery ⭐⭐⭐⭐⭐

**Problem:**
```
Planned:
  6:00–6:45  Learn FCFS

Reality:
  6:00–6:22  Learned FCFS

Result:
  23 minutes unused
  → Wasted study time
  → Schedule broken for rest of day
```

**Solution — Dynamic Time Recovery:**

When a session ends earlier than planned:

1. **Detect:** `current_time < planned_end_time`
2. **Calculate:** `recovered_time = planned_end - current_time`
3. **Offer choices:**
   ```
   ✅ FCFS completed in 22 min (planned: 45)
   
   You have 23 minutes before next break.
   
   What would you like to do?
   1. Start next learning unit
   2. Revise FCFS right now
   3. Practice FCFS questions
   4. Take an early break
   5. Let me decide automatically
   ```

4. **Pack time intelligently:**
   ```
   Remaining: 23 min
   
   Next topic: Preemptive Scheduling (20 min)
   → Can fit! Start immediately
   
   OR
   
   Next topic: Banker's Algorithm (40 min)
   → Can't fit! Offer: Flashcards (10 min) + Practice MCQs (10 min)
   ```

5. **Recalculate rest of day:**
   ```
   Old:
     6:45–7:15  Break
     7:15–8:00  Study Deadlock
   
   New:
     6:22–6:30  Quick Recall
     6:30–6:45  Practice Questions
     6:45–7:00  Break
     7:00–7:45  Study Deadlock
   ```

6. **Auto-fill mode (optional):**
   ```
   Setting: "Auto-fill free time" → ON
   
   System automatically:
     - Packs small units into gaps
     - Fills with practice/revision
     - Shows updated timetable
     - User confirms before starting
   ```

---

## Knowledge Tracking: Questions the Planner Should Answer

| Question | Planner Can Answer? | Implementation Status |
|----------|---------------------|----------------------|
| What should the student study next? | ✅ Yes | **Done** |
| When exactly should they study it? | 🔄 Partial | Needs precise scheduling |
| Can they skip it? | ✅ Yes | **Done** (depends on priority) |
| Can they resume later? | 🔄 Partial | Needs checkpoint tracking |
| What if they finish early? | ❌ No | **Dynamic Time Recovery** |
| What if they study extra? | 🔄 Partial | Needs event handling |
| What if they miss three days? | ❌ No | **Catch-up logic** |
| What revisions are due today? | ✅ Yes | **Done** (spaced repetition) |
| Can they change subjects? | 🔄 Partial | Needs user-requested topics |
| Are they on track for deadline? | ✅ Yes | **Done** (basic check) |
| Which unit for Learner Agent? | ✅ Yes | **Done** (active task) |

**Target:** ✅ All green before Learner Agent integration.

---

## Implementation Priorities

### Phase 2A: Dynamic Scheduling (Week 1)
**Focus:** Make scheduling precise and adaptive.

**Tasks:**
1. Enhance `scheduler.py`:
   - Precise time blocks per learning unit (e.g., 6:15–6:30)
   - Time recovery logic
   - Early finish detection

2. Add to `state.py`:
   - `session_start_time`, `session_planned_end`
   - `session_actual_end` (updated during learning)
   - `recovered_time` tracking

3. Update `progress.py`:
   - When session completes early, capture actual end time
   - Trigger time recovery flow
   - Show user the choices

4. Add `time_recovery.py`:
   - New agent to handle early finish scenarios
   - Intelligent time packing
   - Auto-fill logic

---

### Phase 2B: Knowledge Tracking (Week 2)
**Focus:** Create unified learning unit profiles.

**Tasks:**
1. Redesign learning unit structure:
   - Add all fields from the profile template
   - Create LearningUnit dataclass

2. Update `state.py`:
   - Expand learning_units to full structure
   - Add lookup functions

3. Create `knowledge_tracker.py`:
   - Agent to maintain & query knowledge vault
   - Scoring & mastery algorithms
   - Prediction engine (next revision date, etc.)

---

### Phase 2C: Decision Engine (Week 3)
**Focus:** Add intelligent routing based on learning state.

**Tasks:**
1. Create `planner_logic.py`:
   - Decision tree for each scenario
   - Routing logic based on knowledge state
   - Priority scoring

2. Integrate with orchestrator:
   - Route decisions through logic engine
   - Update state based on decisions

3. Add to `progress.py`:
   - Trigger decision engine on key events
   - Auto-update tasks based on decisions

---

### Phase 2D: Daily Planning Cycle (Week 4)
**Focus:** Make planning adaptive.

**Tasks:**
1. Create `daily_planner.py`:
   - Morning initialization routine
   - End-of-day review
   - Tomorrow preparation

2. Update main loop:
   - Call daily planner every morning
   - Compare plan vs. actual progress
   - Adjust for tomorrow

3. Add cycle to orchestrator:
   - Start each day with cycle
   - Update user on daily status

---

## Completion Checklist: Planner Ready for Learner Agent

- [ ] **Scheduling:** Precise time blocks, early finish handling, time recovery
- [ ] **Knowledge Tracking:** Unified learning unit profiles, full state machine
- [ ] **Decision Engine:** Handles all 5 event scenarios intelligently
- [ ] **Daily Cycle:** Morning planning, end-of-day review, tomorrow prep
- [ ] **Progress Queries:** All 11 questions answered correctly
- [ ] **User Testing:** 3+ study sessions showing stable behavior
- [ ] **Documentation:** Updated ARCHITECTURE.md with new components
- [ ] **Integration Tests:** Planner + Scheduler + Progress working together
- [ ] **Edge Cases:** Missed days, deadline changes, extra studying handled
- [ ] **Learner Agent Bridge:** Clear API for Learner Agent to hook into

---

## When to Freeze the Planner

The planner is frozen when:

1. ✅ All 5 responsibilities are fully implemented
2. ✅ Decision engine handles all event scenarios
3. ✅ Daily planning cycle working smoothly
4. ✅ User can study a full week without manual intervention
5. ✅ No "patches" needed for edge cases
6. ✅ Learner Agent can cleanly hook into learning units

**Estimated timeline:** 3–4 weeks of focused development.

---

## After Planner is Frozen: Learner Agent Foundation

Once the Planner is stable:

1. **Learner Agent receives:**
   - Current active learning unit (from planner)
   - Learning style preferences
   - Mastery level
   - Time remaining for session

2. **Learner Agent returns:**
   - Multi-modal explanation
   - SVG diagram
   - Video search suggestions
   - Practice MCQs

3. **Loop:**
   - User studies, asks questions → Learner Agent responds
   - Session completes → back to Progress Agent
   - Planner updates knowledge state

**This bridge only works if Planner is rock-solid.**

---

## Why Freeze Before Learner Agent?

**If Learner Agent exists before Planner is stable:**

```
Planner (incomplete)
  ↓
  "Study FCFS"
  ↓
Learner Agent explains FCFS
  ↓
User asks "When should I practice?"
  ↓
Planner hesitates (doesn't know scheduling)
  ↓
Learner Agent starts compensating
  ↓
Responsibilities blur
  ↓
System becomes unmaintainable
```

**If Planner is complete first:**

```
Planner (complete)
  ↓
  "Study FCFS (6:30–6:50)"
  "Practice will be 7:00–7:20"
  "Next revision: Tomorrow at 10am"
  ↓
Learner Agent explains FCFS
  ↓
User asks "When should I practice?"
  ↓
Planner answers (knows exactly)
  ↓
Learner Agent focuses on teaching
  ↓
Clear separation, maintainable system
```

This is the right sequence.

---

## Next Steps

1. **Read this document** with the team
2. **Choose Phase 2A start date** (Dynamic Scheduling)
3. **Create feature branches** for each phase
4. **Update ARCHITECTURE.md** with new components
5. **Begin implementation** with daily cycles

The planner is close. Three to four more weeks of focused work will make it bulletproof.
