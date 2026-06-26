# KarmaSarathi - Final Frozen Architecture (9.8/10)

**Status**: FROZEN - No changes to Planner while building Learner Agent

---

## Core Philosophy

**Three Visible Agents. Everything Else is Internal Modules.**

```
                Orchestrator
                     │
     ┌───────────────┼───────────────┐
     │               │               │
 Planner Agent   Learner Agent   Research Agent
     │               │               │
     └───────────────┼───────────────┘
             Shared Student State
```

---

## 1. Planner Agent

**Responsibility**: Decide WHAT should be learned and WHEN

**Never teaches. Never explains concepts.**

### Internal Modules

```
Planner Agent
│
├── Goal Analyzer          # Analyzes student goals, deadlines, syllabus
├── Routine Analyzer       # Understands daily schedule, blocked times
├── Scheduler              # Creates time-blocked timetables
├── Learning Unit Generator # Breaks chapters into granular learning units
├── Progress Tracker       # Tracks completion, mastery, attempts
├── Revision Engine        # Spaced repetition (day+1, +3, +7)
├── Resource Index         # Topic tree structure (NOT teaching content)
└── Deadline Optimizer     # Adjusts pace based on deadline pressure
```

### Resource Index

**Only stores structure, not content:**

```
Subject → Chapter → Topics → Learning Units

Example:
Operating Systems
  └── CPU Scheduling
      └── FCFS
          ├── Introduction
          ├── Need
          ├── Algorithm
          ├── Worked Example
          ├── Problems
          └── MCQs
```

**Stores**:
- Topic Tree
- Estimated Time per unit
- Difficulty level
- Dependencies (prerequisites)
- Current status (pending/learning/completed/revision_due/mastered)

**Does NOT store**:
- Explanations
- Teaching content
- Resources (PDFs, videos, notes)

### Resource Index Sources

```
1. User uploads (syllabus, textbooks)
   ↓
2. OCR + Parser
   ↓
3. LLM generates topic tree
   ↓
4. Store in Resource Index

OR

1. User provides subject name
   ↓
2. LLM generates standard syllabus
   ↓
3. Store in Resource Index
```

### Planner Output

```json
{
  "today_schedule": [
    {
      "time": "09:00-09:45",
      "subject": "Operating Systems",
      "learning_unit": "FCFS - Worked Example",
      "type": "new_learning",
      "estimated_duration": 45
    },
    {
      "time": "10:00-10:30",
      "subject": "DBMS",
      "learning_unit": "Normalization - 2NF",
      "type": "revision",
      "estimated_duration": 30
    }
  ]
}
```

**Student clicks** → Opens Learner Agent directly at that learning unit

---

## 2. Learner Agent

**Responsibility**: Explain ONE learning unit until student understands it

**Works at learning unit level only. Not chapters. Not subjects.**

### Internal Modules

```
Learner Agent
│
├── Resource Manager       # Upload, search, library, bookmarks
├── RAG Engine            # Vector DB, retrieval, context grounding
├── Understanding Engine   # Layered teaching (L0→L1→L2→L3)
├── SVG Generator         # Visual diagrams on confusion
├── Quiz Engine           # MCQs, practice problems, instant feedback
├── Audio Engine          # Text-to-speech, voice notes
├── Video Helper          # Timestamps, transcripts, search
├── Conversation Manager   # Chat history, context, session memory
├── Confusion Detector    # Passive signals → intervention
└── Explanation Generator  # Analogies, examples, alternative styles
```

### Resource Hub (Inside Learner)

**Student's personal knowledge base:**

```
Resource Hub
│
├── Upload
│   ├── PDF upload
│   ├── OCR processing
│   ├── Image extraction
│   ├── Voice notes
│   └── Video timestamps
│
├── Search
│   ├── Google Scholar
│   ├── ArXiv papers
│   ├── YouTube videos
│   ├── Documentation
│   └── Textbook search
│
├── Library
│   ├── My PDFs
│   ├── My notes
│   ├── Bookmarks
│   ├── Generated summaries
│   └── Flashcards
│
├── Parser
│   ├── PDF chunking
│   ├── Heading detection
│   ├── Table extraction
│   └── Code block parsing
│
└── RAG Storage
    ├── Vector DB (embeddings)
    ├── Chunk metadata
    ├── Retrieved context
    └── Rerank results
```

### RAG Pipeline

**Learner has RAG. Planner doesn't.**

```
Student Question
    ↓
Embedding
    ↓
Vector Search (top-k chunks)
    ↓
Rerank by relevance
    ↓
Retrieved Context
    ↓
LLM (with context)
    ↓
Grounded Answer
```

### Layered Teaching System

**Layer 0**: Prior Knowledge Assessment (3 questions)
**Layer 1**: Intuition (analogies, no jargon, real-life examples)
**Layer 2**: Structured (terminology, components, steps)
**Layer 3**: Advanced (edge cases, numericals, problem-solving)

**Understanding verification** at each layer before proceeding.

### Session Flow

```
Planner schedules: "FCFS - Worked Example"
    ↓
Learner opens that specific unit
    ↓
Layer 0: "Have you studied FCFS before?" (assess)
    ↓
Layer 1: "Think of a queue at a ticket counter..." (intuition)
    ↓
Check understanding: "Explain in your words"
    ↓
Layer 2: "FCFS = First Come First Serve. Formula: TAT = CT - AT" (structured)
    ↓
Check understanding: Quiz question
    ↓
Layer 3: "Now solve: 4 processes with varying arrival times" (advanced)
    ↓
Check understanding: Problem-solving
    ↓
Student: "I understand"
    ↓
Learner: Generate summary, flashcards
    ↓
Emit event: "FCFS - Worked Example" completed (mastery: 0.85)
    ↓
Planner receives event: Mark complete, schedule next unit
```

### Confusion Detection

**Passive signals**:
- "I don't understand"
- "Explain again"
- "Still confused"
- "What does that mean?"
- Repeated wrong answers

**Intervention**:
- Score ≥ 3: Generate SVG diagram
- Score ≥ 5: Switch teaching style (video/analogy/example)
- Score ≥ 7: Suggest break or flag for human help

### Student Control

**Student always has options**:
```
After completing a layer:
- Continue to next layer
- Practice with problems
- Review flashcards
- Take a break
- End session and return to planner
```

**Learner never forces decisions.**

If student says "enough", Learner saves checkpoint and returns control to Planner.

---

## 3. Research Agent

**Status**: NOT BUILT YET - FROZEN FOR LATER

**Responsibility**: Explore beyond syllabus (applications, projects, research)

### Future Internal Modules

```
Research Agent
│
├── Research Hub
│   ├── Paper Search (ArXiv, Google Scholar)
│   ├── Citation Tracker
│   ├── Industry Applications
│   └── Innovation Ideas
│
├── Project Generator
│   ├── Mini-project ideas
│   ├── Code scaffolding
│   ├── Build mode
│   └── Capstone suggestions
│
└── RAG Engine (research-focused)
    ├── Paper embeddings
    ├── Code repositories
    └── Technical blogs
```

**Will be built after Learner is complete and validated.**

---

## 4. Planner ↔ Learner Flow

### Happy Path

```
Planner shows today's timetable
    ↓
Student clicks: "09:00 - FCFS Worked Example"
    ↓
Learner opens at that exact unit
    ↓
Learner teaches (Layer 0 → Layer 1 → Layer 2 → Layer 3)
    ↓
Student: "I understand"
    ↓
Learner emits event: {unit: "FCFS", status: "completed", mastery: 0.85}
    ↓
Planner receives event
    ↓
Planner marks complete, updates progress
    ↓
Planner shows next unit in timetable
```

### Confusion Path

```
Student: "Still confused"
    ↓
Planner waits (doesn't interrupt)
    ↓
Learner continues teaching (alternative explanations, SVG, examples)
    ↓
Student eventually: "Got it" or "Need more time"
    ↓
If "Need more time":
    Learner emits: {unit: "FCFS", request: "schedule +2 sessions"}
    ↓
    Planner receives request
    ↓
    Planner adds 2 more FCFS sessions to timetable
```

### Early Exit Path

```
Student: "Enough. Back to planner."
    ↓
Learner saves checkpoint: {completed_layers: [0, 1], current_layer: 2, completion: 60%}
    ↓
Learner emits: {unit: "FCFS", status: "paused", progress: 60%}
    ↓
Planner receives event
    ↓
Planner shows timetable
    ↓
Later, student clicks "FCFS" again
    ↓
Learner detects checkpoint
    ↓
Learner: "Welcome back! You were at 60%. Resume from Layer 2?"
```

---

## 5. Shared Student State

**Single source of truth. All agents read/write here.**

```json
{
  "user_id": "student_123",
  
  "current_context": {
    "active_agent": "learner",
    "current_subject": "Operating Systems",
    "current_topic": "CPU Scheduling",
    "current_learning_unit": "FCFS - Worked Example",
    "current_session_id": "session_456",
    "study_mode": "deep_learning"
  },
  
  "learning_passports": {
    "OS_FCFS_Example": {
      "status": "learning",
      "mastery_level": 0.6,
      "attempts": 2,
      "time_spent_minutes": 45,
      "session_checkpoint": {
        "completed_layers": [0, 1],
        "current_layer": 2,
        "completion_pct": 60
      },
      "confusion_score": 3,
      "doubts": ["Why is waiting time calculated before arrival?"],
      "resources_used": ["lecture_notes.pdf", "youtube_video_timestamp_5:30"]
    }
  },
  
  "progress": {
    "OS": {
      "total_units": 120,
      "completed": 35,
      "mastered": 20,
      "revision_due": 8,
      "overall_mastery": 0.72
    }
  },
  
  "resources": {
    "pdfs": ["os_textbook.pdf", "cpu_scheduling_notes.pdf"],
    "videos": ["yt_fcfs_tutorial"],
    "bookmarks": ["os_chapter_5_page_89", "gantt_chart_example"],
    "vector_db_indexed": true
  },
  
  "preferences": {
    "learning_style": ["visual", "examples", "analogies"],
    "preferred_sequence": ["intuition_first", "then_theory"],
    "pace": "medium",
    "break_frequency": 45
  },
  
  "history": {
    "sessions": [],
    "quiz_scores": {},
    "revision_history": []
  }
}
```

**All modules read from and write to this state.**

---

## 6. Orchestrator

**Very simple. No business logic.**

```python
def orchestrate(user_message, state):
    intent = detect_intent(user_message)
    
    if intent == "planning":
        return planner_agent.handle(user_message, state)
    
    elif intent == "learning":
        return learner_agent.handle(user_message, state)
    
    elif intent == "research":
        return research_agent.handle(user_message, state)
    
    else:
        return "I didn't understand. Are you trying to plan your schedule or learn something?"
```

**Intent Detection**:
- "schedule", "timetable", "deadline", "plan" → Planner
- "explain", "teach", "learn", "understand" → Learner
- "research", "project", "application" → Research

**That's it. Orchestrator just routes.**

---

## 7. Emotional Layer

**NOT another agent. Shared module.**

All agents emit events:
```json
{
  "event": "repeated_confusion",
  "unit": "FCFS",
  "confusion_score": 7,
  "attempts": 3
}
```

**Emotional Module observes and suggests**:
```
"I notice you're struggling with FCFS. Would you like to:
- Try a different learning style (video instead of text)?
- Take a 10-minute break?
- Skip to an easier topic and come back later?"
```

**It doesn't control conversation. Just suggests actions.**

---

## 8. Progress Engine

**One shared engine. All agents update it.**

```
Planner emits → "Unit scheduled"
    ↓
Progress DB: status = "scheduled"

Learner emits → "Unit completed, mastery = 0.85"
    ↓
Progress DB: status = "completed", mastery = 0.85, attempts = 1

Revision Engine checks → "Unit due for revision"
    ↓
Progress DB: status = "revision_due"

Student revises → "Revision complete, mastery = 0.92"
    ↓
Progress DB: status = "mastered", mastery = 0.92, last_revised = today
```

**Progress levels**:
1. pending
2. scheduled
3. learning
4. completed (mastery < 0.8)
5. revision_due
6. mastered (mastery ≥ 0.8, revised ≥ 2 times)
7. archived (knowledge vault)

---

## 9. Resource Flow

### Upload Flow

```
Student uploads PDF
    ↓
OCR extraction
    ↓
Parser (detect headings, tables, code blocks)
    ↓
Chunking (semantic chunks, ~500 tokens each)
    ↓
Embedding (generate vectors)
    ↓
Vector DB storage
    ↓
Resource Hub (student's library)
    ↓
Available to Learner RAG
```

### Search Flow

```
Student: "Find FCFS examples"
    ↓
Google/YouTube/ArXiv search
    ↓
Download/scrape content
    ↓
Parse and chunk
    ↓
Embed and store
    ↓
Return to student: "Found 3 resources"
    ↓
Student selects one
    ↓
RAG uses it for teaching
```

### Reuse Flow

```
Student studies "FCFS" again
    ↓
Learner: "You previously used lecture_notes.pdf. Reuse it?"
    ↓
Student: "Yes"
    ↓
RAG retrieves from existing embeddings (no re-upload)
```

**Student owns all resources**:
- Download anytime
- Delete if not useful
- Bookmark important sections
- Share with classmates (future feature)

---

## 10. Why This Architecture is 9.8/10

### Strengths

✅ **Clear separation of concerns**: Planner plans, Learner teaches, Research explores
✅ **No tight coupling**: Agents communicate via events, not direct calls
✅ **Student control**: Never forces, always offers choices
✅ **Scalable**: Modules can be replaced/upgraded independently
✅ **Grounded teaching**: RAG ensures answers are based on student's resources
✅ **Resume capability**: Checkpoints allow pause/resume anywhere
✅ **Context-aware**: Educational safety filter understands legitimate academic content
✅ **Adaptive**: Confusion detection → automatic intervention
✅ **Production-ready**: Not just a demo, but a system students can use daily

### Why Not 10/10 Yet?

🔶 **Learner Agent not implemented**: Need to validate layered teaching works in practice
🔶 **RAG performance unknown**: Need to test retrieval quality, chunk size, reranking
🔶 **SVG generation quality**: Need to ensure diagrams are actually helpful
🔶 **Real student testing**: Need feedback from actual students using the system

**Once Learner is built and validated, this becomes 10/10.**

---

## 11. Implementation Roadmap

### Phase 1: DONE ✅
- Planner Agent (complete, frozen)
- Learning Passport system
- Progress tracking
- Revision engine
- Scheduler

### Phase 2: IN PROGRESS 🔨
- Learner Agent core
- Understanding Engine (layered teaching)
- Confusion detection
- Resource Generator (SVG, flashcards, summaries)
- Context-aware safety

### Phase 3: NEXT 🚀
- Resource Hub (upload, search, library)
- RAG Engine (vector DB, retrieval, grounding)
- Quiz Engine (MCQs, problems, instant feedback)
- Planner ↔ Learner integration (event system)

### Phase 4: FUTURE 🌟
- Research Agent
- Emotional Module
- Audio/Video helpers
- Advanced analytics

---

## 12. Critical Design Decisions

### Decision 1: Why Only 3 Agents?

**Reasoning**: More agents = more complexity. Students need simple mental model:
- "Need a plan?" → Planner
- "Need to learn?" → Learner
- "Need to explore?" → Research

Everything else is internal complexity hidden from user.

### Decision 2: Why RAG in Learner, Not Planner?

**Reasoning**: 
- Planner only needs structure (topic trees), not content
- Learner needs actual explanations, examples, definitions
- RAG is expensive (embeddings, vector search) - only use where needed
- Keeps Planner fast and lightweight

### Decision 3: Why Shared State Instead of Agent-to-Agent Communication?

**Reasoning**:
- Prevents tight coupling (agents don't know about each other)
- Single source of truth (no synchronization issues)
- Easy to add new agents (just read/write shared state)
- Simpler to debug (one place to check state)

### Decision 4: Why Layered Teaching?

**Reasoning**:
- Students need gradual progression (intuition → details → mastery)
- Forces understanding verification at each step
- Prevents "explain everything at once" problem
- Allows checkpoints for resume capability

### Decision 5: Why Confusion Detection?

**Reasoning**:
- Students often don't explicitly say "I'm confused"
- Passive signals more reliable ("explain again", wrong answers)
- Automatic intervention prevents frustration
- Escalation strategy (SVG → style switch → human help)

---

## 13. File Structure

```
KarmaSarathi/
│
├── app/
│   │
│   ├── agents/
│   │   ├── planner.py               # FROZEN ❄️
│   │   ├── scheduler.py             # FROZEN ❄️
│   │   ├── progress.py              # FROZEN ❄️
│   │   ├── daily_planner.py         # FROZEN ❄️
│   │   ├── decision_engine.py       # FROZEN ❄️
│   │   ├── knowledge_tracker.py     # FROZEN ❄️
│   │   │
│   │   ├── learner.py               # IN PROGRESS 🔨
│   │   ├── understanding_engine.py  # IN PROGRESS 🔨
│   │   ├── resource_generator.py    # IN PROGRESS 🔨
│   │   ├── resource_hub.py          # NEXT 🚀
│   │   ├── rag_engine.py            # NEXT 🚀
│   │   └── quiz_engine.py           # NEXT 🚀
│   │
│   ├── learning_passport.py         # Shared state ✅
│   ├── safety.py                    # Context-aware safety ✅
│   ├── orchestrator.py              # Simple router ✅
│   └── graph.py                     # LangGraph setup ✅
│
├── tests/
│   ├── test_complete_system.py      # Planner tests ✅
│   └── test_learner_agent.py        # Learner tests ✅
│
├── ARCHITECTURE_FINAL.md            # This file 📄
└── README.md
```

---

## 14. Next Steps

1. **Freeze Planner** ❄️ - No more changes while building Learner
2. **Build Resource Hub** 🚀 - Upload, parse, embed, store
3. **Build RAG Engine** 🚀 - Vector search, retrieval, grounding
4. **Build Quiz Engine** 🚀 - MCQs, problems, feedback
5. **Test Learner End-to-End** 🧪 - Full session flow with real student
6. **Integrate Planner ↔ Learner** 🔗 - Event system, handoffs
7. **User Testing** 👥 - Get feedback, iterate
8. **Research Agent** 🌟 - Build after validation

---

## 15. Success Metrics

**Learner Agent is successful when**:

✅ Student can learn ANY unit from uploaded resources
✅ Confusion is detected and handled automatically
✅ Understanding verification works (not just explanation)
✅ Resume capability works (pause/resume anywhere)
✅ RAG provides grounded answers (not hallucinated)
✅ Student feels in control (not forced)
✅ Planner ↔ Learner handoff is seamless

**System is production-ready when**:

✅ Students use it daily without bugs
✅ 80%+ of students report better understanding vs traditional study
✅ Average session time is reasonable (30-45 min, not hours)
✅ Students return to use it voluntarily (not forced by us)
✅ System handles 100+ concurrent students without slowdown

---

## Final Notes

**This architecture is frozen.**

No changes to Planner while building Learner.

No new agents until Learner is validated.

**Focus: Build one thing at a time. Build it well.**

---

**Architecture Version**: 3.0 (Final)
**Date**: 2024
**Status**: FROZEN FOR LEARNER IMPLEMENTATION
**Rating**: 9.8/10 → Target 10/10 after Learner validation
