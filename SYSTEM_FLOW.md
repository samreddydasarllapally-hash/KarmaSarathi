# KarmaSarathi System Flow Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         USER INPUT                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                             │
│  (Intent Classification & Routing)                          │
│                                                             │
│  • Planner mid-stage? → planner                            │
│  • Active task + learner keyword? → learner (BRIDGE)       │
│  • Progress loop active? → progress                        │
│  • Reschedule needed? → scheduler                          │
│  • Default → classify intent                               │
└──────┬────────┬────────┬────────┬────────┬─────────────────┘
       │        │        │        │        │
       ▼        ▼        ▼        ▼        ▼
   ┌───────┐┌────────┐┌────────┐┌───────┐┌─────────┐
   │Planner││Schedule││Progress││Learner││Research │
   └───────┘└────────┘└────────┘└───────┘└─────────┘
```

---

## Detailed Flow: Planner → Scheduler → Progress

```
STEP 1: PLANNER (Strategy Creation)
┌──────────────────────────────────────────────────────────┐
│  User: "I'm preparing for semester exam in 10 days"     │
│         ↓                                                │
│  Collect: goal, deadline, routine, subjects, topics      │
│         ↓                                                │
│  Analyze: deadline intensity, confidence, weak areas     │
│         ↓                                                │
│  Generate: priority_order, practice_subjects, roadmap    │
│         ↓                                                │
│  Output: tasks[] (learning, practice, revision)          │
└──────────────────────────────────────────────────────────┘
                       │
                       ▼
STEP 2: SCHEDULER (Time Blocking)
┌──────────────────────────────────────────────────────────┐
│  Input: tasks[], routine, wake/sleep times               │
│         ↓                                                │
│  Calculate: blocked intervals (meals, college, gym)      │
│         ↓                                                │
│  Find: free slots (gaps between blocked intervals)       │
│         ↓                                                │
│  Distribute: tasks across free slots                     │
│         ↓                                                │
│  Output: today_schedule[], day_plan[]                    │
└──────────────────────────────────────────────────────────┘
                       │
                       ▼
STEP 3: PROGRESS (Daily Execution Loop)
┌──────────────────────────────────────────────────────────┐
│  Stage: idle → ask_completion → ask_rating → idle        │
│         ↓                                                │
│  For each task:                                          │
│    • Show task details                                   │
│    • Ask completion (Yes/Partial/No)                     │
│    • If Yes → rate understanding 1-5                     │
│    • Award XP + update streak                            │
│    • Schedule spaced revisions (day+1, +3, +7)          │
│    • Archive if mastered                                 │
│         ↓                                                │
│  Output: XP, streak, badges, next_task                   │
└──────────────────────────────────────────────────────────┘
```

---

## Spaced Repetition Flow

```
USER COMPLETES TASK
┌─────────────────────────────────────────────────────┐
│  Task: Study DBMS Normalization                     │
│  User rating: 3/5 (mostly understood)               │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
SPACED REPETITION ENGINE
┌─────────────────────────────────────────────────────┐
│  IF rating <= 4:                                    │
│    → Schedule revision day+1 (15 min)               │
│  IF rating <= 3:                                    │
│    → Schedule revision day+3 (20 min)               │
│  IF rating <= 4:                                    │
│    → Schedule revision day+7 (25 min)               │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
NEW REVISION TASKS CREATED
┌─────────────────────────────────────────────────────┐
│  [Task 46] Quick recap: Normalization (day+1)       │
│  [Task 47] Medium revision: Normalization (day+3)   │
│  [Task 48] Final checkpoint: Normalization (day+7)  │
│                                                     │
│  stored in: tasks[] with status="pending"           │
│              spaced_day_offset: 1, 3, 7             │
│              available_on: future dates             │
└─────────────────────────────────────────────────────┘
                   │
                   ▼
SCHEDULER PICKS UP ON NEXT RUN
┌─────────────────────────────────────────────────────┐
│  When date = available_on:                          │
│    → Task appears in today_schedule                 │
│    → User prompted to revise                        │
└─────────────────────────────────────────────────────┘
```

---

## Archive System Flow

```
USER ARCHIVES TOPIC
┌─────────────────────────────────────────────────────┐
│  User: "archive Normalization from DBMS"            │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
ARCHIVE PROCESSOR
┌─────────────────────────────────────────────────────┐
│  1. Calculate mastery (avg of all ratings)          │
│  2. Gather difficulty_notes from past tasks         │
│  3. Create knowledge_vault entry:                   │
│     {                                               │
│       topic: "Normalization",                       │
│       subject: "DBMS",                              │
│       mastery: 3.5,                                 │
│       status: "archived",                           │
│       revision_only: true                           │
│     }                                               │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
TASK CLEANUP
┌─────────────────────────────────────────────────────┐
│  Remove from tasks[]:                               │
│    ✘ Learning tasks (Study Normalization)           │
│    ✘ Practice tasks (Practice Normalization)        │
│    ✔ Revision tasks (KEPT — day+3, day+7)          │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
USER VIEW
┌─────────────────────────────────────────────────────┐
│  Active tasks:                                      │
│    [Study OS Scheduling]                            │
│    [Study DS Arrays]                                │
│                                                     │
│  Knowledge vault:                                   │
│    DBMS  Normalization  ★★★☆☆  (revision only)     │
│                                                     │
│  Upcoming revisions:                                │
│    [day+3] Medium revision: Normalization           │
│    [day+7] Final checkpoint: Normalization          │
└─────────────────────────────────────────────────────┘
```

---

## Learner Agent Flow

```
USER REQUEST
┌─────────────────────────────────────────────────────┐
│  During task: "show me a diagram"                   │
│  OR                                                 │
│  Anytime: "teach me DBMS Normalization"            │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
ORCHESTRATOR BRIDGE
┌─────────────────────────────────────────────────────┐
│  Detects keywords: diagram, video, mcq, quiz        │
│  Routes to: learner agent                           │
│  Preserves: active_task_id (context)                │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
LEARNER AGENT (Multi-Modal Generator)
┌─────────────────────────────────────────────────────┐
│  Input: topic, subject, learning_style              │
│         ↓                                           │
│  Generate (parallel):                               │
│    ┌──────────────┐ ┌──────────────┐              │
│    │ Explanation  │ │  SVG Diagram │              │
│    │ (LLM call 1) │ │  (LLM call 2)│              │
│    └──────────────┘ └──────────────┘              │
│    ┌──────────────┐ ┌──────────────┐              │
│    │ Video Queries│ │  5 MCQs      │              │
│    │ (rule-based) │ │  (LLM call 3)│              │
│    └──────────────┘ └──────────────┘              │
│         ↓                                           │
│  Store in: learner_output{}                         │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
USER RECEIVES
┌─────────────────────────────────────────────────────┐
│  🎓 DBMS Normalization (DBMS)                       │
│                                                     │
│  [Explanation adapted to learning style]            │
│                                                     │
│  📊 Visual diagram: [SVG attached]                  │
│                                                     │
│  🎥 Video suggestions:                              │
│    • Query 1                                        │
│    • Query 2                                        │
│    • Query 3                                        │
│                                                     │
│  ✅ Practice MCQs: 5 questions attached             │
│                                                     │
│  Type 'next' to return to schedule.                 │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
RETURN TO PROGRESS LOOP
┌─────────────────────────────────────────────────────┐
│  User: "next"                                       │
│  Orchestrator: active_task_id exists → progress     │
│  Progress: continues from where it left off         │
└─────────────────────────────────────────────────────┘
```

---

## Adaptive Task Evolution

```
INITIAL STATE (Confidence: 5/10)
┌─────────────────────────────────────────────────────┐
│  Tasks:                                             │
│    [Study DS Arrays]                                │
│    [Study DS Linked Lists]                          │
│    [Study DS Trees]                                 │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
USER COMPLETES TASKS WITH HIGH RATINGS
┌─────────────────────────────────────────────────────┐
│  Arrays: rating 4/5                                 │
│  Linked Lists: rating 5/5                           │
│  Trees: rating 4/5                                  │
│         ↓                                           │
│  Confidence: 5 → 6 → 7 → 8/10                       │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
SYSTEM DETECTS CONFIDENCE ≥7
┌─────────────────────────────────────────────────────┐
│  Trigger: Auto-promote to Practice mode             │
│         ↓                                           │
│  For all pending tasks where subject="DS":          │
│    IF type == "learning":                           │
│      type = "practice"                              │
│      title = title.replace("Study ", "Practice ")   │
│      reason = "Confidence reached 8/10 → practice"  │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
NEW STATE (Confidence: 8/10)
┌─────────────────────────────────────────────────────┐
│  Tasks:                                             │
│    [Practice DS Graphs — Numericals & MCQs]         │
│    [Practice DS Sorting — Problem solving]          │
│                                                     │
│  Message: "You're confident in DS now. Remaining    │
│            tasks promoted to practice mode."        │
└─────────────────────────────────────────────────────┘
```

---

## Complete User Journey

```
DAY 0: ONBOARDING
User → "I'm preparing for semester exam in 10 days"
  ↓
Planner collects profile
  ↓
Generates strategy + tasks
  ↓
User confirms: "yes"
  ↓
Scheduler builds timetable
  ↓
Shows: Day 1 preview


DAY 1: STUDY SESSION
User → "next"
  ↓
Progress: "Study OS Scheduling? (1/2/3)"
User → "1" (completed)
  ↓
Progress: "Rate understanding 1-5"
User → "3"
  ↓
Progress:
  • Awards XP (50 + bonuses)
  • Updates streak (+1)
  • Schedules revisions (day+1, +3, +7)
  • Shows next task


DAY 1: LEARNER BRIDGE
User → "show me a diagram"
  ↓
Orchestrator → routes to learner (preserves task context)
  ↓
Learner generates:
  • SVG diagram
  • Explanation
  • Videos
  • MCQs
  ↓
User → "next"
  ↓
Returns to progress loop
  ↓
Continues with next task


DAY 2: SPACED REVISION
Scheduler checks: day+1 tasks available?
  ↓
Yes: "Quick recap: OS Scheduling" (15 min)
  ↓
User completes revision
  ↓
Mastery reinforced


DAY 4: ARCHIVE TOPIC
User → "archive Normalization from DBMS"
  ↓
Progress:
  • Moves to knowledge_vault
  • Removes study/practice tasks
  • KEEPS revision tasks
  ↓
Shows: "Archived. Revisions still scheduled."


DAY 10: EXAM DAY
User → "summary"
  ↓
Progress:
  Completed: 28/30 tasks (93%)
  Study time: 18h 45m
  XP: 1,420
  Streak: 10 days
  
  Subject Performance:
    DS   [█████] 100%
    OS   [████░] 90%
    DBMS [████░] 85%
  
  🎉 Ready for exam!
```

---

## Data Flow Between Agents

```
┌─────────────────────────────────────────────────────────┐
│                     STATE (Shared)                      │
│                                                         │
│  • user_message                                         │
│  • intent                                               │
│  • tasks[]                                              │
│  • today_schedule[]                                     │
│  • knowledge_vault[]                                    │
│  • learner_output{}                                     │
│  • active_task_id                                       │
│  • xp, streak, badges                                   │
└──────┬──────┬──────┬──────┬──────┬───────────────────────┘
       │      │      │      │      │
       ▼      ▼      ▼      ▼      ▼
   Planner Sched Progress Learner Tutor
   
   Planner writes:
     • tasks[]
     • subjects[]
     • structured_strategy{}
   
   Scheduler writes:
     • today_schedule[]
     • day_plan[]
   
   Progress writes:
     • tasks[].status
     • xp, streak, badges
     • knowledge_vault[] (on archive)
     • revision_queue[] (on completion)
   
   Learner writes:
     • learner_output{}
   
   All read from: state (shared memory)
```

---

## Key Decision Points

```
ORCHESTRATOR ROUTING LOGIC
┌────────────────────────────────────────────┐
│  Is planner mid-stage?                     │
│    YES → planner                           │
│    NO  ↓                                   │
├────────────────────────────────────────────┤
│  Is tutor active?                          │
│    YES → tutor                             │
│    NO  ↓                                   │
├────────────────────────────────────────────┤
│  Is task active + learner keyword?         │
│    YES → learner (BRIDGE)                  │
│    NO  ↓                                   │
├────────────────────────────────────────────┤
│  Is schedule request OR reschedule needed? │
│    YES → scheduler                         │
│    NO  ↓                                   │
├────────────────────────────────────────────┤
│  Is progress loop active?                  │
│    YES → progress                          │
│    NO  ↓                                   │
├────────────────────────────────────────────┤
│  Classify intent from message              │
│    → planner / tutor / research / learner  │
└────────────────────────────────────────────┘
```

---

## Performance Characteristics

### Time Complexity
- Planner: O(n) where n = number of topics
- Scheduler: O(m) where m = number of free slots
- Progress: O(1) per task
- Learner: O(1) per request (3 LLM calls)

### Space Complexity
- State: ~10KB for typical user
- knowledge_vault: ~50 bytes per archived topic
- learner_output: ~2KB per generation

### LLM Call Budget (per session)
- Planner: 2 calls (strategy + roadmap)
- Scheduler: 0 calls (pure logic)
- Progress: 0 calls (rule-based)
- Learner: 3 calls (explanation, SVG, MCQs)

**Total: ~5 LLM calls per complete onboarding + study session**

---

## Summary

This system implements a **complete learning loop**:

1. **Plan** → Planner creates strategy
2. **Schedule** → Scheduler blocks time
3. **Execute** → Progress tracks completion
4. **Reinforce** → Spaced repetition schedules revisions
5. **Preserve** → Archive moves to knowledge vault
6. **Explore** → Learner provides on-demand teaching

**The key innovation:** Topics never disappear — they either:
- Stay active (pending tasks)
- Get archived (revision-only mode)
- Get revised (spaced repetition)

**Result:** A system that truly helps users **learn and retain**, not just complete tasks.
