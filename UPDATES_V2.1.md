# KarmaSarathi v2.1 — Knowledge Hub Update

## What Changed (Based on User Feedback)

This update transforms KarmaSarathi from a task manager into a true **AI Study Companion** with better action naming, enhanced learner capabilities, and smarter knowledge retention.

---

## 1. Better Action Naming ✅

### Problem
The old "Delete" action implied losing knowledge — wrong behavior for a learning system.

### Solution
Replaced with three clear options that preserve learning history:

| Old | New | Behavior |
|-----|-----|----------|
| Delete | **Skip for now** | Reschedule task, keep in active plan |
| - | **Archive** | Remove from active plan, preserve all history + revision tasks |
| - | **Mark as not required** | Explicitly mark as outside syllabus |

### Implementation
Location: `app/agents/progress.py`

```python
Did you complete this topic?
  1) Yes
  2) Partially  
  3) Skip/Later  # New stage

↓ If user selects 3:

What would you like to do with **Topic**?
  1) Skip for now (reschedule for later)
  2) Archive (remove from active plan, keep history)
  3) Mark as not required (outside syllabus)
```

**Key Insight:** The learner agent NEVER loses information — everything is preserved in knowledge vault, revision notes, or task history.

---

## 2. Enhanced Learner Agent 🎓

### New Capabilities

#### A) Funny Analogies (Retention Boost)
**Function:** `_generate_funny_analogy()`

Generates memorable, relatable analogies using LLM:

```python
Topic: Deadlock
Analogy: "Imagine four friends at a restaurant. Everyone grabs one 
         spoon and waits for another spoon. Nobody lets go. 
         Everyone waits forever."

Topic: Virtual Memory
Analogy: "Your desk is RAM. Your bookshelf is the hard disk. When 
         the desk is full, you move books back to the shelf."

Topic: CPU Scheduling
Analogy: "Think of a barber shop with one barber and ten customers 
         waiting. The barber picks who's next based on different 
         rules."
```

**Why it works:** Concrete examples stick better than abstract concepts.

#### B) Personalized Revision Notes
**Function:** `_generate_revision_notes()`

Auto-generates quick review material after each learning session:

```json
{
  "key_points": [
    "CPU Scheduling assigns CPU time to processes",
    "FCFS is simplest but causes convoy effect",
    "SJF minimizes average waiting time"
  ],
  "common_mistakes": [
    "Confusing waiting time with turnaround time",
    "Forgetting context switch overhead"
  ],
  "remember": "Shortest Job First minimizes average waiting time",
  "quick_revision_time": "5 minutes"
}
```

**Storage:** `state.revision_notes_db[]`

**Usage:** When planner schedules revision (day+3, day+7), learner opens these notes instead of reteaching entire chapter.

#### C) Enhanced Output Format
```
🎓 CPU Scheduling (Operating System)

[Explanation adapted to learning style]

😂 Remember This:
Think of a barber shop with one barber and ten customers...

📊 Visual diagram: [SVG attached]

🎥 Video suggestions:
  • CPU Scheduling explained simply
  • Scheduling algorithms tutorial
  • FCFS vs SJF with examples

✅ Practice MCQs: 5 questions attached

📝 Revision notes generated for quick review later

Type 'next' to return to schedule.
```

---

## 3. Knowledge Hub Architecture

### Before (v2.0)
```
Learner Agent
    ↓
Generate explanation
    ↓
Show to user
    ↓
[Lost after session]
```

### After (v2.1)
```
Learner Agent
    ↓
Generate multi-modal content:
  • Explanation
  • Funny analogy
  • SVG diagram
  • Videos
  • MCQs
  • Revision notes
    ↓
Store in:
  • learner_output (current session)
  • revision_notes_db (long-term)
  • knowledge_vault (archived topics)
    ↓
Retrieve later for:
  • Spaced revision (day+3, +7)
  • Progress tracking
  • Adaptive learning
```

**Key Insight:** The learner becomes a knowledge hub that accumulates and retrieves information over time.

---

## 4. Future Enhancements (Roadmap)

### Phase 1: Multi-Source Learning ✅ (Implemented)
- [x] Text explanations
- [x] SVG diagrams
- [x] Video suggestions
- [x] MCQs
- [x] Funny analogies
- [x] Revision notes

### Phase 2: Document Upload (Next)
```
User uploads PDF
    ↓
Extract chapters using RAG
    ↓
Find relevant section
    ↓
Generate explanation from PDF + general knowledge
```

**Implementation:**
- Use `PyPDF2` or `pdfplumber` to extract text
- Chunk by headings
- Embed using sentence-transformers
- Store in vector DB (ChromaDB/FAISS)

### Phase 3: Web Search Integration
```
User: "Teach me Deadlocks"
    ↓
Search trusted sources:
  • University lecture notes
  • Official documentation
  • Quality tutorials
    ↓
Combine into single lesson
    ↓
Present: "I searched several resources and created this lesson"
```

**Advantage:** Grounded answers instead of hallucinations.

### Phase 4: Interactive Learning
```
Explain concept
    ↓
Ask question
    ↓
User answers
    ↓
Provide feedback
    ↓
Continue
```

Instead of passive reading.

### Phase 5: Audio Mode (TTS)
```
Generate explanation
    ↓
Convert to audio (TTS)
    ↓
User listens while commuting
```

**Tools:** gTTS, AWS Polly, or Azure Speech

### Phase 6: Animated Diagrams
```
CPU Scheduling timeline:
Time →
P1 ███████
P2       ████
P3           ███

[Animate execution with moving blocks]
```

**Tools:** SVG `<animate>` tags, or generate video with `manim`

---

## 5. RAG Strategy (Retrieval-Augmented Generation)

### Why RAG?
- Grounds answers in actual materials
- Prevents hallucinations
- Enables learning from user's own textbooks/notes
- Creates long-term memory

### Where to Use RAG

#### A) Learner Agent (Heavy RAG)
```
User: "Teach CPU Scheduling"
    ↓
Retrieve:
  • Uploaded PDFs
  • Previous notes
  • Web search results
  • Generated summaries
    ↓
LLM generates answer grounded in sources
```

#### B) Revision Agent (Medium RAG)
```
User: "Revise CPU Scheduling"
    ↓
Retrieve:
  • Yesterday's notes
  • Tutor explanation
  • Weak points
  • Revision notes
    ↓
Focus on what user struggled with
```

#### C) Progress Agent (Light RAG)
```
Calculate progress
    ↓
Retrieve:
  • Completed tasks
  • Ratings
  • Study history
  • Difficulty logs
    ↓
Show trends
```

#### D) Planner Agent (Light RAG)
```
Create study plan
    ↓
Retrieve:
  • Previous plans
  • Completion history
  • Confidence scores
  • Exam date
    ↓
Prioritize weak subjects
```

### RAG Implementation Phases

**Phase 1: Local Knowledge Base** ✅ (Current)
```
revision_notes_db
knowledge_vault
learner_output
task history
```

**Phase 2: Document RAG** (Next)
```
Upload PDF → Chunk → Embed → Store in vector DB
Query → Retrieve chunks → Generate answer
```

**Phase 3: Web RAG**
```
Search web → Filter quality sources → Extract content → Generate lesson
```

**Phase 4: Long-term Memory**
```
After 2 months:
User: "Teach CPU Scheduling again"
    ↓
Retrieve:
  • Old ratings
  • Past mistakes
  • Weak concepts
  • Previous notes
    ↓
"Last time you struggled with Round Robin. Let's focus there."
```

---

## 6. Complete System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERACTION                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                          │
│  (Intent Classification & Routing)                      │
└──┬────────┬────────┬────────┬────────┬─────────────────┘
   │        │        │        │        │
   ▼        ▼        ▼        ▼        ▼
Planner  Schedule Progress Learner  Tutor
   │        │        │        │        │
   │        │        │        │        │
   └────────┴────────┴────────┴────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              KNOWLEDGE LAYER (RAG)                      │
├─────────────────────────────────────────────────────────┤
│  Local Storage:                                         │
│    • revision_notes_db  (personalized notes)            │
│    • knowledge_vault    (archived topics)               │
│    • learner_output     (generated content)             │
│    • task history       (completed tasks)               │
│                                                         │
│  Future (Phase 2+):                                     │
│    • Vector DB          (uploaded PDFs, textbooks)      │
│    • Web search cache   (trusted resources)             │
│    • Long-term memory   (2+ months history)             │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  LLM RESPONSE                           │
│  (Gemini + RAG context)                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 7. User Experience Flow

### Scenario 1: Learning New Topic
```
User: "teach me CPU Scheduling"
    ↓
Learner Agent:
  ✓ Generates explanation (adapted to learning style)
  ✓ Creates funny analogy (retention boost)
  ✓ Generates SVG diagram (visual learning)
  ✓ Suggests 3 videos (multi-modal)
  ✓ Creates 5 MCQs (practice)
  ✓ Generates revision notes (future use)
    ↓
Stores everything in:
  • learner_output (current)
  • revision_notes_db (long-term)
```

### Scenario 2: Revision After 3 Days
```
Day 3: Spaced revision task appears
    ↓
User: "next"
    ↓
System retrieves:
  • Revision notes (key points only)
  • Previous rating (3/5)
  • Difficulty notes ("theory was hard")
    ↓
Learner shows:
  "Last time you struggled with theory.
   Here's a quick recap with simpler analogies."
    ↓
Uses 5-min revision notes instead of full lesson
```

### Scenario 3: Archive Topic
```
User completes topic with rating 5/5
    ↓
User: "archive CPU Scheduling from OS"
    ↓
System:
  ✓ Moves to knowledge_vault
  ✓ Removes study/practice tasks
  ✓ KEEPS revision tasks (day+7)
  ✓ KEEPS revision notes
  ✓ KEEPS learner output
    ↓
Response:
  "🗃️ CPU Scheduling archived.
   Mastery: 5/5 ⭐⭐⭐⭐⭐
   Revisions still scheduled.
   Revision notes saved for future reference."
```

---

## 8. Testing the New Features

### Test 1: Skip/Archive/Not Required
```bash
python main.py

# Start task
User: next

# Try skip
User: 3  # Skip/Later
Bot: What would you like to do?
     1) Skip for now
     2) Archive
     3) Mark as not required

User: 2  # Archive
Bot: 🗃️ Topic archived. Mastery: X/5. Revisions still scheduled.
```

### Test 2: Funny Analogies
```bash
python test_learner_agent.py

User: teach me Deadlocks
Bot: [Shows explanation]
     😂 Remember This:
     Imagine four friends at a restaurant...
```

### Test 3: Revision Notes
```bash
User: teach me CPU Scheduling
Bot: [Generates content]
     📝 Revision notes generated

# Check state
print(state['revision_notes_db'])
# Output: [{topic, key_points, common_mistakes, remember, ...}]
```

---

## 9. File Changes Summary

| File | Changes | Purpose |
|------|---------|---------|
| `progress.py` | Added `ask_skip_action` stage | Better action naming |
| `learner.py` | Added `_generate_funny_analogy()` | Retention boost |
| `learner.py` | Added `_generate_revision_notes()` | Quick review material |
| `state.py` | Added `revision_notes_db` | Store personalized notes |
| `learner.py` | Enhanced output format | Include analogy + notes |

---

## 10. Benefits Summary

### For Students
✅ **Never lose knowledge** — everything preserved  
✅ **Better retention** — funny analogies stick  
✅ **Faster revision** — 5-min notes instead of full chapter  
✅ **Clear actions** — skip/archive/not required  
✅ **Multi-modal learning** — text + visual + video + quiz

### For System
✅ **Knowledge accumulation** — builds over time  
✅ **Personalized learning** — remembers what worked  
✅ **Efficient revision** — uses stored notes  
✅ **Better UX** — clear, non-destructive actions  
✅ **RAG-ready** — foundation for document upload

---

## Next Steps

1. **Test current features** — run test scripts
2. **Implement document upload** — Phase 2 RAG
3. **Add web search** — Phase 3 RAG
4. **Build interactive learning** — Q&A flow
5. **Add audio mode** — TTS integration
6. **Create animated diagrams** — SVG animations

---

**Version:** 2.1  
**Release Date:** 2025-01-15  
**Key Theme:** From Task Manager to Knowledge Hub
