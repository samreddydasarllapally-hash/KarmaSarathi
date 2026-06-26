# KarmaSarathi - Phase 1 Improvements Status

**Last Updated:** Current Session
**Goal:** Freeze planner architecture with critical fixes before Learner Agent integration

---

## ✅ COMPLETED (Phase 1)

### 1. Study Mode Selection ⭐⭐⭐⭐⭐
**Status:** ✅ IMPLEMENTED & TESTED

**What was added:**
- New `study_mode` field in StudentState: `"focus"` | `"mixed"`
- New planner stage: `collect_study_mode`
- User-facing question with clear explanation of both modes
- Extraction logic to parse user choice
- Test coverage: `test_study_mode.py`

**User flow:**
```
How would you like to study?

1. Focus Mode
   Finish one subject completely before moving to another.
   Best for: Deep mastery, fewer context switches.

2. Mixed Mode
   Study multiple subjects every day (rotating).
   Best for: Balanced preparation, variety.
```

**Files modified:**
- `app/state.py` - Added study_mode field
- `app/agents/planner.py` - Added collection stage, question, extraction

---

### 2. Learning Units Database Structure ⭐⭐⭐⭐⭐
**Status:** ✅ ARCHITECTURE ADDED

**What was added:**
```python
learning_units: list[dict] = []
# Structure: {
#   id, subject, chapter, unit_name, 
#   status, completion_pct, mastery,
#   revision_due, practice_due, difficulty,
#   attempts, time_spent, resources
# }
```

**Function added:**
- `_break_into_learning_units(topic, subject)` - Breaks chapters into granular units using LLM
- Returns: `[{unit_name, estimated_minutes, unit_type: 'concept'|'example'|'practice'|'quiz'}]`
- Has fallback if LLM fails

**Files modified:**
- `app/state.py` - Added learning_units field
- `app/agents/planner.py` - Added breakdown function

---

### 3. Enhanced Progress Tracking ⭐⭐⭐⭐☆
**Status:** ✅ ARCHITECTURE READY (fields exist, logic in progress agent works)

**Tracking now includes:**
- Completion percentage
- Mastery rating (1-5)
- Revision due dates
- Practice due dates
- Difficulty level
- Attempts count
- Time spent per topic

---

### 4. Spaced Repetition System ⭐⭐⭐⭐⭐
**Status:** ✅ IMPLEMENTED & TESTED

**What works:**
- Rating 5 → day+1 revision only
- Rating 4 → day+1, day+7
- Rating 3 → day+1, day+3, day+7
- Rating 1-2 → day+1, day+3, day+7 + immediate 30min revision
- Difficulty detail collection for low ratings
- Auto-adjustment of future practice tasks based on rating

**Files:**
- `app/agents/progress.py` - Full spaced repetition logic
- `test_revision.py` - Comprehensive test coverage

---

### 5. Archive System (Knowledge Vault) ⭐⭐⭐⭐⭐
**Status:** ✅ IMPLEMENTED & TESTED

**Features:**
- Archive removes study/practice tasks
- Keeps all revision tasks (revision-only mode)
- Stores mastery, ratings, difficulty notes
- Command: `archive <topic> from <subject>`
- View command: `vault`
- Never deletes learning history

---

### 6. XP & Gamification System ⭐⭐⭐⭐☆
**Status:** ✅ FULLY FUNCTIONAL

**Features:**
- Base XP: 50
- Difficult subject bonus: +15
- Understanding bonus (rating 4+): +10
- Streak bonus: +10 per day
- Badges: 3d, 7d, 14d, 30d streaks + topic milestones
- Varied encouragement messages
- Break suggestions every 3 sessions

---

## 🔄 IN PROGRESS (Phase 1)

### 7. User Topic Selection ⭐⭐⭐⭐⭐
**Status:** 🔄 PARTIAL (needs orchestrator integration)

**What's needed:**
User should be able to say:
```
"Teach me FCFS"
"I only want Round Robin"
"Study CPU Scheduling"
```

Planner should:
1. Detect topic-specific request
2. Find subject → chapter → topic hierarchy
3. Break down into learning units
4. Schedule immediately

**Implementation plan:**
- Add intent detection in orchestrator for topic-specific requests
- Create `_extract_specific_topic()` function
- Integrate with learning units breakdown
- Update roadmap to show selected path only

---

### 8. Timetable Generator (Routine-Aware) ⭐⭐⭐⭐☆
**Status:** 🔄 PARTIAL (scheduler exists, needs enhancement)

**Current:** Scheduler has basic routine blocking
**What's needed:**
- Respect all routine fields (breakfast, lunch, dinner, college, travel, etc.)
- Place study sessions ONLY in free slots
- Show conflicts clearly
- Auto-reschedule if routine changes

**Files to modify:**
- `app/agents/scheduler.py` - Enhance `_blocked_intervals()` function

---

### 9. Task Sequencing Improvement ⭐⭐⭐⭐⭐
**Status:** 🔄 NEEDS IMPLEMENTATION

**Current pattern:**
```
Study → Revision → Study → Revision
```

**Desired pattern:**
```
Learning → Quick Recall → Practice → Quiz → Mastery Check
```

**Implementation plan:**
- Update `_generate_tasks()` to create proper sequence
- Add task dependencies
- Integrate with learning units
- Add mastery check tasks

---

### 10. Deadline Distribution ⭐⭐⭐⭐☆
**Status:** 🔄 BASIC EXISTS (needs smarter distribution)

**Current:** Estimates days but doesn't distribute clearly
**What's needed:**
```
10-day deadline:
  Day 1-3: OS (weakest subject)
  Day 4-6: DBMS
  Day 7-9: DS
  Day 10: Final Revision
```

**Implementation plan:**
- Add day-by-day breakdown in strategy phase
- Show clear daily goals
- Respect study_mode (focus vs mixed)

---

## ❌ NOT YET STARTED (Phase 1)

### 11. Flexible Commands ⭐⭐⭐⭐☆
**Status:** ❌ NOT IMPLEMENTED

**Commands to support:**
```
Study FCFS
Continue OS
Revise DBMS
Practice Trees
Quiz me
Show roadmap          ← already works
Today's schedule      ← partially works
Reschedule
Skip today
Pause
Resume
```

**Implementation plan:**
- Add command detection in orchestrator
- Create handlers for each command
- Update progress agent to route commands

---

### 12. Subject Recommendation ⭐⭐⭐☆☆
**Status:** ❌ NOT IMPLEMENTED

**What's needed:**
After extended study session:
```
You've studied OS for 3 hours.

Recommended:
1. Continue OS
2. Revise OS
3. Practice OS
4. Switch to DBMS
5. Take a break

Your choice?
```

**Implementation plan:**
- Track time per subject in current session
- Add recommendation engine to progress agent
- Show options, let user decide

---

### 13. Difficulty Adaptation ⭐⭐⭐⭐⭐
**Status:** 🔄 PARTIAL (some logic exists, needs enhancement)

**Current:** Auto-revision for rating 1-2, practice mode for rating 5
**What's needed:**
- More granular adaptation
- Visual explanation insertion for rating 1-2
- Mock test generation for rating 5
- Tutor session scheduling for confused state

---

## 📊 TEST COVERAGE

| Component | Test File | Status |
|-----------|-----------|--------|
| Planner | `test_planner.py` | ✅ Passing |
| Progress Agent | `test_progress.py` | ✅ Passing |
| Revision System | `test_revision.py` | ✅ Passing |
| Study Mode | `test_study_mode.py` | ✅ Passing |
| Learner Agent | `test_learner_agent.py` | ⏸ Needs integration updates |
| Scheduler | Manual testing | 🔄 Needs automated tests |

---

## 🎯 PRIORITY FOR NEXT SESSION

**High Priority (Must Complete Before Learner Integration):**

1. ⭐⭐⭐⭐⭐ **User Topic Selection** - Let users jump to specific topics
2. ⭐⭐⭐⭐⭐ **Task Sequencing** - Proper learning flow (not just study → revision)
3. ⭐⭐⭐⭐☆ **Timetable Enhancement** - Fully respect routine
4. ⭐⭐⭐⭐☆ **Deadline Distribution** - Clear day-by-day plan

**Medium Priority (Can Wait):**
5. ⭐⭐⭐⭐☆ **Flexible Commands** - More natural interaction
6. ⭐⭐⭐☆☆ **Subject Recommendation** - Smart suggestions

**Low Priority (Phase 2):**
7. Enhanced difficulty adaptation
8. Mock test generation
9. Advanced analytics

---

## 🚀 PHASE 2 READINESS

**When to move to Phase 2 (Learner Agent Integration):**
- ✅ Study mode working
- ✅ Learning units architecture ready
- ✅ Progress tracking enhanced
- ✅ Spaced repetition working
- ✅ Archive system working
- 🔄 User topic selection (HIGH PRIORITY)
- 🔄 Task sequencing improved (HIGH PRIORITY)
- 🔄 Timetable respects routine
- 🔄 Deadline distribution clear

**Estimated readiness:** 70% complete
**Next session focus:** Complete high-priority items (topic selection, task sequencing)

---

## 📝 NOTES

### What NOT to change (as per user request):
- ✅ Routine collection - works well
- ✅ Subject confidence collection - works well
- ✅ Syllabus parsing - works well
- ✅ Completed topic tracking - works well
- ✅ Review before confirmation - works well
- ✅ XP and streak system - works well
- ✅ Roadmap view - works well
- ✅ Summary view - works well
- ✅ Rescheduling after partial completion - works well

### Integration Plan for Learner Agent:
```
Planner
  ↓
Generates Learning Units
  ↓
User selects unit / Progress agent picks next
  ↓
Learner Agent teaches the unit
  ├→ Visual diagrams (SVG)
  ├→ Explanations (adapted to learning_style)
  ├→ Video suggestions
  ├→ Examples
  ├→ Practice MCQs
  └→ Summary
  ↓
Progress Agent captures mastery
  ↓
Planner updates roadmap & schedules revision
```

---

## 🎮 DEMO FLOW (When Complete)

```
USER: I'm preparing for semester exam in 10 days
→ Planner collects info
→ Asks: Focus or Mixed mode?
USER: Focus
→ Planner: "Finish OS first, then DBMS, then DS"
→ Breaks OS into learning units
→ Shows day-by-day plan

USER: Start
→ Progress: "Learn CPU Scheduling - Introduction (15 min)"
USER: Done
→ Progress: Rate understanding
USER: 3
→ Progress: ✅ Scheduled day+1/+3/+7 revisions
→ Shows next unit: "CPU Scheduling - Scheduling Criteria"

USER: Explain FCFS with diagram
→ Orchestrator detects specific topic request
→ Learner Agent generates:
    • SVG diagram of FCFS
    • Video suggestions
    • Step-by-step explanation
    • Practice MCQs
→ Returns to progress loop

USER: Skip to Round Robin
→ Planner finds: OS → CPU Scheduling → Round Robin
→ Breaks into units
→ Progress starts with first unit
```

This is the target experience.
