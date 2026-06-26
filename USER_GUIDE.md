# KarmaSarathi User Guide

## Quick Start

### 1. Initial Setup (Planner)
```
You: I'm preparing for semester exam in 10 days
Bot: What subjects do you need to study?
You: DS 8 4/5, OS 3 1/5, DBMS 6 2/4
     (format: Name Confidence CompletedUnits/TotalUnits)
```

The bot will collect:
- Wake/sleep times
- Routine (meals, college, gym)
- Study preferences (focus duration, breaks)
- Topics per subject
- Completed topics

### 2. Confirm Strategy
After analysis, bot shows recommended strategy:
```
Goal: Semester Exam | Deadline: 10 days
Subjects:
  - DS: confidence 8, 4/5 units
  - OS: confidence 3, 1/5 units (WEAK)
  - DBMS: confidence 6, 2/4 units

Strategy:
- OS gets morning slots (your energy peak)
- DS on alternate days (already strong)
- Daily revision for weak topics
- Practice sessions after theory

Reply 'yes' to confirm or tell me what to change.
```

### 3. View Schedule
```
You: schedule

📅 Today's Schedule

  9:00 – 9:45   📖 Study OS Scheduling  [OS]
  9:45 – 10:00  ☕ Break
  10:00 – 10:45 📖 Study DBMS Normalization  [DBMS]
  10:45 – 11:00 ☕ Break
  ...
  1:00 – 2:00   🔒 Lunch
  ...

⏱ Estimated finish: 6:30 PM
📊 Today's goal: [░░░░] 0/4 sessions
```

---

## Daily Study Loop

### Start a Session
```
You: next

📚 Study OS Scheduling
   OS  ·  45 min  ·  Priority: high
   Reason: confidence 3/10

Did you complete this topic?
  1) Yes
  2) Partially
  3) No, not yet
```

### Completion Flow

#### Option 1: Completed
```
You: 1

Rate your understanding of OS Scheduling:
  1 — I didn't understand it
  2 — Very difficult
  3 — Mostly understood
  4 — Comfortable
  5 — I can teach someone else

You: 4

✅ OS Scheduling marked complete!
Understanding: Comfortable

XP earned:
  +50 Completed topic
  +15 Difficult subject bonus
  +10 Streak bonus (3d)
  +10 Good understanding bonus
  ─────────
  +85 XP total

🔥 Streak: 3 days  |  Total XP: 385
🏅 New badge: 🔥 3-Day Streak

Excellent! Keep the momentum going.

📆 Spaced revision scheduled: day+1, day+3, day+7

📋 Today's Schedule:
  ✔ 9:00–9:45  Study OS Scheduling
  ○ 10:00–10:45  Study DBMS Normalization
  ○ 11:00–11:45  Study DS Arrays
  ...

🔓 Next: Study DBMS Normalization
Type 'next' to continue, 'roadmap' or 'summary' to review.
```

#### Option 2: Partially Completed
```
You: 2

How much of OS Scheduling did you cover?
  1) Around 25%
  2) Around 50%
  3) Around 75%

You: 2

👍 Good progress on OS Scheduling (50% done).

XP earned:
  +20 Partial completion
  ─────────
  +20 XP total

Remaining 23 min added to next session.
Type 'next' to continue.
```

#### Option 3: Not Completed
```
You: 3

No problem. What stopped you from studying OS Scheduling?
  1) Was busy
  2) Too difficult
  3) Felt tired
  4) Forgot
  5) Didn't understand the topic

You: 2 (too difficult)

OS Scheduling split into two shorter sessions.
We'll tackle it step by step. 💡
```

---

## Spaced Repetition System

### How It Works
When you complete a topic, the system **automatically schedules revisions**:

```
Day 0: Study DBMS Normalization (rating: 3/5)
  ↓
Day 1: Quick recap: Normalization (15 min) — auto-scheduled
  ↓
Day 3: Medium revision: Normalization (20 min) — auto-scheduled
  ↓
Day 7: Final checkpoint: Normalization (25 min) — auto-scheduled
```

**Smart Intervals Based on Understanding:**
- Rating 1-2 → revision on day+1, +3, +7
- Rating 3-4 → revision on day+1, +7
- Rating 5 → revision on day+7 only

### Low Understanding Bonus
If you rate understanding as 1-2:
```
📌 30-min revision added to upcoming sessions.

What specifically was difficult?
  1) Theory / concepts
  2) Numericals / problems
  3) Too many concepts at once
  4) Didn't have enough time

You: 1 (theory)

Got it — noted as: theory.
The Tutor Agent will focus on that when you revise.
```

---

## Archive System (Revision-Only Mode)

### What is Archiving?
**Archiving DOES NOT delete a topic.** It:
- ✅ Moves topic to Knowledge Vault
- ✅ Removes active study/practice tasks
- ✅ **KEEPS all revision tasks**
- ✅ Preserves mastery rating and notes

### Archive a Topic
```
You: archive Normalization from DBMS

🗃️ Normalization archived.
  Mastery: 3.5/5  ·  Revisions still scheduled.
  The topic lives in your Knowledge Vault — future revision tasks remain active.
```

### View Knowledge Vault
```
You: vault

🗃️ Knowledge Vault:

  DBMS       Normalization       ★★★☆☆  (revision only)
  OS         Scheduling          ★★★★☆  (revision only)
  DS         Arrays              ★★★★★  (revision only)
```

**Benefits:**
- Declutters active task list
- Keeps knowledge accessible for future revision
- Tracks mastery over time
- Never lose what you've learned

---

## Learner Agent (Multi-Modal Learning)

### What is Learner Agent?
An **on-demand AI tutor** that generates:
- 📄 Adaptive explanations (based on your learning style)
- 📊 SVG diagrams (visual representations)
- 🎥 Video suggestions (YouTube search queries)
- ✅ Practice MCQs (with explanations)

### How to Use

#### During a Study Task
```
You: next
Bot: 📚 Study DBMS Normalization
You: show me a diagram

🎓 DBMS Normalization (DBMS)

Normalization is the process of organizing database tables to reduce redundancy...

Core concept: Split tables to eliminate duplicate data
Key points:
  • 1NF: Atomic values only
  • 2NF: Remove partial dependencies
  • 3NF: Remove transitive dependencies
Example: Student table → split into Student + Course tables

📊 Visual diagram: [attached]

🎥 Video suggestions:
  • DBMS Normalization explained simply - DBMS
  • Normalization tutorial for beginners
  • Normalization with examples

✅ Practice MCQs: 5 questions attached

Type 'next' to return to your schedule.
```

#### Free Exploration
```
You: teach me Operating System scheduling algorithms

🎓 Operating System scheduling algorithms (OS)

[Explanation adapted to your learning style]
[SVG diagram generated]
[Video suggestions]
[5 MCQs with answers]

Type 'next' to return to your schedule.
```

### Learner Keywords
Trigger learner agent with:
- "explain [topic]"
- "teach me [topic]"
- "show me a diagram of [topic]"
- "visualize [topic]"
- "give me MCQs on [topic]"
- "quiz me on [topic]"

---

## Progress Tracking

### Roadmap
```
You: roadmap

📍 Learning Roadmap:

  Data Structures  [████░] 4/5
    ✔ Arrays
    ✔ Linked Lists
    ▶ Stacks (current)
    ○ Queues
    ○ Trees

  Operating System  [██░░░] 2/5
    ✔ Introduction
    ○ Scheduling
    ○ Memory Management
    ○ Deadlocks
    ○ File Systems

  DBMS  [███░░] 3/5
    ✔ ER Diagrams
    ✔ Normalization
    ○ SQL Queries
    ○ Transactions
    ○ Indexing
```

### Summary
```
You: summary

📊 Progress Summary
  Completed : 9/15 tasks (60%)
  Pending   : 6 tasks
  Study time: 4h 35m
  XP        : 385
  Streak    : 3 days

Subject Performance:
  DS         [████░] 80%
  OS         [██░░░] 40%
  DBMS       [███░░] 60%

  Badges: 🔥 3-Day Streak  🏅 First Topic
```

### End of Day
```
You: goodnight

🌙 Day Complete!

Topics finished today:
  ✔ OS Scheduling
  ✔ DBMS Normalization
  ✔ DS Stacks

Study time : 2h 15m
XP earned  : 175
Streak     : 3 days
Badges     : 🔥 3-Day Streak  🏅 First Topic
Remaining  : 6 tasks (~3h 45m, est. 2 more days)

Tomorrow starts with: Study DS Queues
Good night! 😴
```

---

## Adaptive Features

### 1. Confidence-Based Task Evolution
As your confidence grows, tasks automatically adapt:

```
Confidence ≤4: Study tasks (learning mode)
  → Study OS Scheduling

Confidence 5-6: Mixed study + practice
  → Study + Practice sessions

Confidence ≥7: Auto-promotion to practice mode
  → System converts remaining "Study" → "Practice"
  → Practice OS Scheduling — Numericals & MCQs
```

### 2. Smart Task Adaptation
After rating understanding:

**High Understanding (4-5):**
```
You're confident in OS Scheduling.
I'll prioritize practice over theory next.

[Next practice task becomes:]
Practice OS Scheduling — Numericals & MCQs
```

**Low Understanding (1-2):**
```
I'll slow things down. Tomorrow we'll review this with the Tutor before moving ahead.

[Auto-adds:]
Revise OS Scheduling with Tutor (30 min)
```

### 3. Break Suggestions
```
🟡 You've done 3 sessions in a row. Take a 20-min break before continuing.
  Stretch, drink water, walk a bit.
Type 'next' when ready.
```

### 4. Missed Days Recovery
If you miss 3+ days:
```
⚠️ You've missed a few days. Sessions shortened to help you ease back in.

[All pending tasks → duration ÷ 2]
Study OS Scheduling: 45 min → 22 min
```

---

## Command Reference

| Command | Description |
|---------|-------------|
| `next` | Start next task in schedule |
| `schedule` | View today's timetable |
| `plan` | Multi-day study plan |
| `roadmap` | Subject-wise progress tree |
| `summary` | Overall progress stats |
| `vault` | View archived topics |
| `archive <topic>` | Archive topic (revision-only) |
| `goodnight` | End of day summary |
| `teach me <topic>` | Launch learner agent |
| `diagram <topic>` | Get visual diagram |
| `quiz <topic>` | Get practice MCQs |

---

## Tips for Success

### 1. Trust the Spaced Repetition
Don't skip revision tasks — they prevent forgetting.

### 2. Archive Strategically
Archive topics you've mastered (rating 4-5) to focus on weak areas.

### 3. Use Learner Agent Liberally
Stuck? Type "explain [topic]" or "show diagram" anytime.

### 4. Rate Honestly
Your understanding ratings drive adaptive scheduling. Be truthful.

### 5. Maintain Streak
Study daily to build momentum and earn bonuses.

### 6. Review Vault Weekly
Check mastery ratings to identify topics needing more revision.

---

## Troubleshooting

### "I don't see any tasks"
```
You: next
Bot: 🎉 All tasks complete!
```
→ Either all done or planner not initialized. Type your goal to restart.

### "Schedule is too packed"
Adjust in planner setup:
- Shorter focus blocks (e.g., 30 min instead of 45)
- Longer breaks
- Update routine (add more fixed activities)

### "I want to change a subject's priority"
Tell the bot:
```
You: I want to focus more on OS and less on DS
Bot: [Regenerates strategy with new priority]
```

---

**Made with ❤️ for students who want to study smarter, not just harder.**
