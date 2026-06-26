# Learner Agent: 4 High-Impact Additions — Implementation Guide

**Focus:** Build the "Teacher → Mentor" transformation  
**Effort:** ~4 weeks  
**Result:** 8.9/10 → 9.8/10

---

## Quick Summary: What to Build

| Feature | Why It Matters | Effort | Impact |
|---------|---|---|---|
| **Real RAG** | Student learns from actual resources, not just LLM memory | 4 days | ⭐⭐⭐⭐⭐ |
| **Adaptive Re-explanations** | Never repeat same explanation; use multiple angles | 3 days | ⭐⭐⭐⭐⭐ |
| **Planner Handoff** | Learner → Planner feedback loop; schedule updates | 2 days | ⭐⭐⭐⭐⭐ |
| **Interactive Multimodal** | SVG + audio + quiz + resources all working together | 4 days | ⭐⭐⭐⭐☆ |

**Total: ~2 weeks to add these 4 features**

---

## Feature 1: Real RAG Integration

### The Problem
```
Current:
  Student: "Explain FCFS"
           ↓
  Learner: Uses Claude's training data
           ↓
  Result: Generic explanation without student's actual resources
```

### The Solution
```
New:
  Student: "Explain FCFS"
           ↓
  Learner: Vector search student's resources
           ├─ "Operating Systems.pdf"
           ├─ "Notes on CPU Scheduling"
           └─ "GeeksforGeeks article"
           ↓
  Retrieve: Top 5 relevant passages
           ↓
  Claude: "Based on your resources..." + explanation + citations
           ↓
  Result: Personalized explanation with sources
```

### Implementation Steps

#### Step 1: Set up Vector DB (2 hours)
```python
from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

class ResourceRAG:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.vector_db = Chroma(
            collection_name="student_resources",
            embedding_function=self.embeddings
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def index_pdf(self, file_path: str, source: str):
        """Index a PDF into the vector DB."""
        # Extract text from PDF
        # Split into chunks
        # Create embeddings
        # Store in Chroma
        pass
    
    def index_text(self, text: str, source: str):
        """Index raw text (notes, articles)."""
        chunks = self.text_splitter.split_text(text)
        self.vector_db.add_texts(
            texts=chunks,
            metadatas=[{"source": source}] * len(chunks)
        )
```

#### Step 2: Retrieve Relevant Context (1 hour)
```python
def retrieve_context(self, query: str, top_k: int = 5):
    """
    Search for relevant passages based on query.
    Returns top_k chunks with source citations.
    """
    results = self.vector_db.similarity_search_with_scores(
        query=query,
        k=top_k
    )
    
    context = []
    for chunk, score in results:
        context.append({
            "text": chunk.page_content,
            "source": chunk.metadata.get("source", "Unknown"),
            "relevance": score
        })
    
    return context
```

#### Step 3: Generate Explanation with Citations (1.5 hours)
```python
def generate_explanation_from_resources(self, topic: str, subject: str):
    """
    Main function: retrieve context + generate explanation.
    """
    # Step 1: Retrieve context
    context = self.retrieve_context(
        query=f"Explain {topic} in {subject}",
        top_k=5
    )
    
    # Step 2: Prepare context string
    context_str = "\n\n".join([
        f"[Source: {c['source']}]\n{c['text']}"
        for c in context
    ])
    
    # Step 3: Ask Claude to explain with citations
    prompt = f"""
You are teaching {topic} in {subject}.

Based on these resources:
{context_str}

Generate a clear, comprehensive explanation that:
1. Uses information from the resources
2. Includes citations in format [Source: filename, page X]
3. Connects concepts from multiple sources if relevant
4. Is written for a student, not technical

Explanation:
"""
    
    explanation = self.llm.generate(prompt)
    
    # Step 4: Attach citations to passport
    return {
        "explanation": explanation,
        "citations": [c["source"] for c in context],
        "retrieved_chunks": len(context)
    }
```

#### Step 4: Integration with Learner Agent (1.5 hours)
```python
# In LearnerAgent class

def __init__(self, llm, user_id, state):
    # ... existing code ...
    self.rag = ResourceRAG()
    self.resource_library = ResourceLibrary(user_id)  # NEW

def teach_concept(self, topic: str, layer: int):
    """Enhanced teaching with RAG."""
    
    # Load student's resources
    resources = self.resource_library.get_all_resources()
    for resource in resources:
        self.rag.index_resource(resource)
    
    # Generate explanation from RAG
    rag_result = self.rag.generate_explanation_from_resources(
        topic=topic,
        subject=context.get("subject")
    )
    
    return {
        "explanation": rag_result["explanation"],
        "citations": rag_result["citations"],
        "sources": rag_result["retrieved_chunks"],
        "layer": layer
    }
```

#### Testing RAG (1 hour)
```python
def test_rag():
    rag = ResourceRAG()
    
    # Add sample resources
    rag.index_text("""
    FCFS (First Come First Served):
    - Simplest CPU scheduling algorithm
    - Processes execute in the order they arrive
    - Non-preemptive
    - Average waiting time is often high
    - Suffers from convoy effect
    """, "sample_notes.txt")
    
    # Query and verify
    context = rag.retrieve_context("What is convoy effect in FCFS?")
    assert len(context) > 0
    assert "convoy effect" in context[0]["text"].lower()
    print("✓ RAG retrieval working")
```

---

## Feature 2: Adaptive Re-explanations

### The Problem
```
Student: "I still don't understand"
         ↓
Learner: Returns similar explanation (same structure, different words)
         ↓
Student: Still confused because approach didn't change
```

### The Solution
```
Student: "I still don't understand"
         ↓
Learner: Recognizes teaching_approach = "abstract_definition"
         ↓
Selects completely different approach: "real_world_analogy"
         ↓
Generates NEW story + NEW analogy + NEW SVG
         ↓
Student: "Oh! That makes sense now!"
```

### Implementation Steps

#### Step 1: Track Teaching Approaches (1 hour)
```python
class TeachingApproachTracker:
    """Track what approaches have been tried."""
    
    AVAILABLE_APPROACHES = [
        "abstract_definition",      # Theory-based
        "real_world_analogy",       # Story/metaphor
        "visual_stepwise",          # Diagram + flow
        "interactive_problem",      # Hands-on example
        "historical_context",       # How it was invented
        "mathematical_proof",       # Formal reasoning
        "code_example",             # Programming
        "biological_parallel",      # Nature parallel
        "game_based",               # Gamification
        "comparative_analysis"      # Vs other concepts
    ]
    
    def __init__(self):
        self.attempted = []
        self.teaching_history = []
    
    def record_approach(self, approach: str, explanation: str):
        """Record that we tried this approach."""
        self.attempted.append(approach)
        self.teaching_history.append({
            "approach": approach,
            "explanation": explanation,
            "timestamp": datetime.now()
        })
    
    def get_available_approaches(self) -> list:
        """Return only approaches NOT yet tried."""
        return [a for a in self.AVAILABLE_APPROACHES if a not in self.attempted]
    
    def select_next_approach(self) -> str:
        """Choose most different from what was tried."""
        available = self.get_available_approaches()
        if not available:
            # If all tried, cycle to most different
            return self._get_most_diverse_approach(self.attempted)
        
        # Return approach most different from recent attempts
        return self._select_most_diverse(available, self.attempted[-3:])
```

#### Step 2: Generate Different Explanations (2 hours)
```python
def generate_alternative_explanation(self, topic: str, subject: str, 
                                     failed_approaches: list) -> dict:
    """
    Generate completely different explanation.
    """
    
    # Select next approach
    next_approach = self.approach_tracker.select_next_approach()
    
    prompt = self._build_prompt_for_approach(
        topic=topic,
        subject=subject,
        approach=next_approach,
        previous_approaches=failed_approaches
    )
    
    # Generate new content
    explanation = self.llm.generate(prompt)
    
    # Record this attempt
    self.approach_tracker.record_approach(next_approach, explanation)
    
    return {
        "explanation": explanation,
        "approach": next_approach,
        "is_different": True
    }

def _build_prompt_for_approach(self, topic, subject, approach, previous):
    """Build prompt tailored to the approach."""
    
    approaches_prompts = {
        "abstract_definition": f"""
        Explain {topic} in {subject} using formal definitions.
        Focus on: What it is, why it matters, mathematical basis.
        """,
        
        "real_world_analogy": f"""
        Explain {topic} in {subject} using a real-world story/analogy.
        Previous approaches ({', '.join(previous)}) didn't work.
        Use a completely different comparison.
        Make it relatable and memorable.
        """,
        
        "visual_stepwise": f"""
        Explain {topic} in {subject} as a step-by-step process.
        Use: "First → Then → Finally"
        Make it sequential and clear.
        """,
        
        "interactive_problem": f"""
        Explain {topic} in {subject} through a hands-on problem.
        Start with: "Let me show you an example"
        Walk through: Case 1, Case 2, Edge Case
        Let student discover the pattern.
        """,
        
        "historical_context": f"""
        Explain {topic} in {subject} through history.
        Why was it invented?
        What problem did it solve?
        How has it evolved?
        """,
        
        "mathematical_proof": f"""
        Explain {topic} in {subject} with formal reasoning.
        Show derivations, proofs, mathematical relationships.
        """,
        
        "code_example": f"""
        Explain {topic} in {subject} with pseudocode/code.
        Show: Structure, Algorithm, Key operations
        """,
        
        "comparative_analysis": f"""
        Explain {topic} in {subject} by comparing to alternatives.
        Highlight: Pros/cons vs other approaches
        When to use this over alternatives
        """
    }
    
    return approaches_prompts[approach]
```

#### Step 3: Integrate with Learner (1 hour)
```python
# In LearnerAgent

def _handle_confusion(self, confusion_score: int, topic: str, context: dict):
    """When student is confused, use adaptive re-explanation."""
    
    if confusion_score > 5:
        # Get available approaches
        available = self.approach_tracker.get_available_approaches()
        
        if not available:
            return {
                "type": "exhausted",
                "message": "We've tried different approaches. Let's take a break.",
                "suggestion": "Practice problems first, then revisit theory"
            }
        
        # Generate adaptive explanation
        new_explanation = self.generate_alternative_explanation(
            topic=topic,
            subject=context.get("subject"),
            failed_approaches=self.approach_tracker.attempted
        )
        
        return {
            "type": "new_approach",
            "approach": new_explanation["approach"],
            "explanation": new_explanation["explanation"],
            "message": "Let me try a completely different angle..."
        }
```

#### Testing Adaptive Explanations (1 hour)
```python
def test_adaptive_explanations():
    tracker = TeachingApproachTracker()
    
    # Simulate trying approaches
    tracker.record_approach("abstract_definition", "def_explanation")
    tracker.record_approach("real_world_analogy", "story_explanation")
    
    # Should suggest something different
    next_approach = tracker.select_next_approach()
    assert next_approach not in ["abstract_definition", "real_world_analogy"]
    print(f"✓ Next approach selected: {next_approach}")
    
    # Test all approaches available
    available = tracker.get_available_approaches()
    assert len(available) == len(tracker.AVAILABLE_APPROACHES) - 2
    print(f"✓ {len(available)} approaches still available")
```

---

## Feature 3: Planner ↔ Learner Bidirectional Handoff

### The Problem
```
Learner and Planner don't communicate.
- Learner doesn't know: What does Planner expect?
- Planner doesn't know: Is student ready for practice?
```

### The Solution
```
Learner: "Student understood concept, ready for practice"
         ↓
Planner: "Received! Updating schedule..."
         ├─ Mark unit status as "Practicing"
         ├─ Move to practice phase
         ├─ Update timetable
         └─ Notify student
```

### Implementation Steps

#### Step 1: Define Handoff Protocol (1 hour)
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class LearnerHandoff:
    """Message from Learner → Planner."""
    
    unit_id: str
    student_id: str
    status: str  # "learning_complete" | "needs_revision" | "ready_practice"
    
    # Mastery dimensions
    concept_understanding: float  # 0-5
    application_readiness: float  # 0-5
    problem_solving_ready: bool
    
    # Session metrics
    time_spent_minutes: int
    confusion_score: float
    engagement_level: float  # 0-1
    
    # Recommendations
    next_action: str  # "practice" | "revise" | "layer_3" | "break"
    estimated_time_for_next: int  # minutes
    
    # Passport updates
    teaching_approaches_used: list[str]
    resources_referenced: list[str]
    student_doubts: list[str]
    
    timestamp: Optional[str] = None
```

#### Step 2: Learner Side - Send Handoff (1 hour)
```python
# In LearnerAgent

def complete_learning_session(self, context: dict) -> dict:
    """
    Student finished learning session.
    Send completion handoff to Planner.
    """
    
    # Collect mastery data
    mastery = self._calculate_mastery_dimensions()
    
    # Create handoff message
    handoff = LearnerHandoff(
        unit_id=self.current_unit,
        student_id=self.user_id,
        status="learning_complete",
        concept_understanding=mastery["concept"],
        application_readiness=mastery["application"],
        problem_solving_ready=mastery["problem_solving"] >= 3,
        time_spent_minutes=self.session_timer.elapsed(),
        confusion_score=self.current_passport.cumulative_confusion_score,
        engagement_level=self._calculate_engagement(),
        next_action="practice" if mastery["overall"] >= 3.5 else "revise",
        estimated_time_for_next=self._estimate_next_session_time(),
        teaching_approaches_used=self.approach_tracker.attempted,
        resources_referenced=[],  # from RAG citations
        student_doubts=self.current_passport.doubts,
        timestamp=datetime.now().isoformat()
    )
    
    # Send to Planner via orchestrator
    return self._notify_planner(handoff)

def _notify_planner(self, handoff: LearnerHandoff):
    """Send handoff to Planner."""
    # This is called via Orchestrator
    return {
        "event": "learner_handoff",
        "data": handoff.__dict__,
        "action": "update_unit_status"
    }
```

#### Step 3: Planner Side - Receive & Act (1 hour)
```python
# In Planner

def handle_learner_handoff(self, handoff: LearnerHandoff):
    """Planner receives handoff from Learner."""
    
    # Update unit in learning_passports
    unit = self._get_learning_unit(handoff.unit_id)
    
    if handoff.status == "learning_complete":
        unit.status = "practicing" if handoff.next_action == "practice" else "revision_due"
        unit.mastery = handoff.concept_understanding
        unit.last_studied = datetime.now().isoformat()
        unit.teaching_approaches = handoff.teaching_approaches_used
    
    # Update schedule based on next_action
    if handoff.next_action == "practice":
        self._promote_to_practice_phase(handoff.unit_id)
        self._recalculate_schedule()
    elif handoff.next_action == "revise":
        self._schedule_immediate_revision(handoff.unit_id)
    
    # Update student info
    self._notify_student({
        "type": "learning_milestone",
        "message": f"Great learning session! Next: {handoff.next_action}",
        "mastery": handoff.concept_understanding,
        "time_spent": handoff.time_spent_minutes
    })
    
    return {"status": "acknowledged", "action": handoff.next_action}
```

#### Testing Handoff (1 hour)
```python
def test_planner_learner_handoff():
    learner = LearnerAgent(llm, "student_1", state)
    planner = PlannerAgent(llm, state)
    
    # Learner completes session
    handoff = learner.complete_learning_session({
        "unit_id": "OS-FCFS",
        "mastery": 4.0,
        "time_spent": 45
    })
    
    # Planner receives it
    planner_response = planner.handle_learner_handoff(handoff)
    
    # Verify unit status updated
    unit = state["learning_passports"]["OS-FCFS"]
    assert unit["status"] == "practicing"
    assert unit["last_studied"] is not None
    print("✓ Bidirectional handoff working")
```

---

## Feature 4: Interactive Multimodal Teaching

### The Problem
```
Current: Static explanation + static SVG
         ↓
Missing: Student interacts with diagram, plays audio, solves quiz
```

### The Solution
```
Teaching Screen:

┌──────────────────────────────┐
│ Interactive SVG              │
│ [Click Process] [Zoom] [Play]│  ← Student can interact
├──────────────────────────────┤
│ Explanation Audio 🔊         │  ← Listen to narration
├──────────────────────────────┤
│ Quick Quiz                   │  ← Test understanding
│ Q: What happens next?        │
│ □ A  □ B  □ C               │
├──────────────────────────────┤
│ Related Resources            │  ← RAG results
│ • Operating Systems.pdf (p145)
│ • GeeksforGeeks (link)       │
└──────────────────────────────┘
```

### Implementation Steps

#### Step 1: Interactive SVG Generation (2 hours)
```python
def generate_interactive_svg(self, topic: str, layer: int) -> str:
    """
    Generate SVG with interactivity based on layer.
    Layer 1: Simple animation
    Layer 2: Clickable components
    Layer 3: Full simulation
    """
    
    prompt = f"""Generate an interactive SVG for {topic}.

Layer {layer} teaching:
{self._get_layer_specific_instructions(layer)}

Requirements:
1. Use <g> for grouping
2. Add onclick events for clickable areas
3. Add <animate> for animations
4. Include labels and highlights
5. Make it educational and clear

SVG CODE:"""
    
    svg = self.llm.generate(prompt)
    return svg

def _get_layer_specific_instructions(self, layer: int) -> str:
    if layer == 1:
        return """
        - Auto-play animation showing flow
        - Simple labeled boxes
        - Arrow showing progression
        """
    elif layer == 2:
        return """
        - Clickable components that show details
        - Hover effects on each element
        - Play/pause buttons
        """
    elif layer == 3:
        return """
        - Fully interactive simulation
        - Can adjust parameters (queue size, time slice, etc)
        - Run button to execute algorithm
        - Step-by-step visualization
        """
```

#### Step 2: Audio Narration (1.5 hours)
```python
def generate_audio_narration(self, explanation: str) -> dict:
    """Generate audio from explanation."""
    
    # Use text-to-speech service (e.g., Google Cloud, Azure)
    audio_url = tts_service.synthesize(
        text=explanation,
        voice="en-US-Neural2-C",  # Professional voice
        speed=1.0
    )
    
    return {
        "audio_url": audio_url,
        "duration": estimate_duration(explanation),
        "transcription": explanation
    }
```

#### Step 3: Interactive Quiz (1 hour)
```python
def generate_interactive_quiz(self, topic: str, layer: int) -> dict:
    """Generate quick quiz right after explanation."""
    
    prompt = f"""Generate 1-2 quick comprehension questions for {topic}.

Layer {layer} difficulty:
{self._get_difficulty_prompt(layer)}

Return JSON:
{{
  "questions": [
    {{
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "correct": 0,
      "explanation": "Why this is correct"
    }}
  ],
  "difficulty": "{layer}"
}}
"""
    
    quiz = json.loads(self.llm.generate(prompt))
    return quiz

def _get_difficulty_prompt(self, layer: int) -> str:
    difficulties = {
        1: "Simple recall: Does the student remember the basic concept?",
        2: "Comprehension: Can they explain in their own words?",
        3: "Application: Can they apply to edge cases?"
    }
    return difficulties.get(layer, "")
```

#### Step 4: Resource Links Integration (1 hour)
```python
def prepare_teaching_view(self, topic: str, layer: int) -> dict:
    """
    Prepare complete multimodal teaching view.
    Combines: SVG + Audio + Quiz + Resources
    """
    
    # Generate SVG
    svg = self.generate_interactive_svg(topic, layer)
    
    # Generate explanation with RAG
    rag_result = self.rag.generate_explanation_from_resources(topic, "general")
    
    # Generate audio
    audio = self.generate_audio_narration(rag_result["explanation"])
    
    # Generate quiz
    quiz = self.generate_interactive_quiz(topic, layer)
    
    # Return complete view
    return {
        "type": "multimodal_teaching",
        "svg": svg,
        "explanation": rag_result["explanation"],
        "audio": audio,
        "quiz": quiz,
        "resources": rag_result["citations"],
        "layer": layer
    }
```

#### Step 5: Frontend Integration (Placeholder)
```html
<!-- Teaching view component -->
<div class="teaching-view">
  <!-- Interactive SVG -->
  <div class="svg-container">
    <svg>{{ svg }}</svg>
    <div class="controls">
      <button onclick="play()">▶ Play</button>
      <button onclick="pause()">⏸ Pause</button>
      <button onclick="reset()">↻ Reset</button>
    </div>
  </div>

  <!-- Explanation + Audio -->
  <div class="explanation">
    <p>{{ explanation }}</p>
    <audio controls>
      <source src="{{ audio.url }}" type="audio/mpeg">
    </audio>
  </div>

  <!-- Quick Quiz -->
  <div class="quiz">
    <h4>{{ quiz.questions[0].question }}</h4>
    <div class="options">
      <label><input type="radio" name="q1"> {{ opt }}</label>
    </div>
    <button onclick="checkAnswer()">Submit</button>
  </div>

  <!-- Related Resources -->
  <div class="resources">
    <h4>Learn More</h4>
    <ul>
      <li><a href="#">{{ resource }}</a></li>
    </ul>
  </div>
</div>
```

#### Testing Multimodal (1 hour)
```python
def test_multimodal_teaching():
    learner = LearnerAgent(llm, "student_1", state)
    
    # Generate complete teaching view
    view = learner.prepare_teaching_view(
        topic="FCFS",
        layer=2
    )
    
    # Verify all components present
    assert "svg" in view
    assert "<svg>" in view["svg"]
    assert "explanation" in view
    assert "audio" in view
    assert "quiz" in view
    assert len(view["quiz"]["questions"]) > 0
    print("✓ Multimodal teaching view ready")
```

---

## Integration Checklist

After building all 4 features:

- [ ] RAG system indexes all student resources
- [ ] Adaptive explanations try different approaches on confusion
- [ ] Learner sends mastery data to Planner on completion
- [ ] Planner updates schedule based on learner handoff
- [ ] Teaching view shows SVG + audio + quiz + resources
- [ ] End-to-end flow tested: Learning → Practice → Revision
- [ ] Student can learn full 5-day session without issues
- [ ] Passport tracks all learning interactions
- [ ] Resource library persists across sessions

---

## Timeline Suggestion

**Week 1:**
- Day 1–2: RAG setup + testing
- Day 3–4: Adaptive explanations
- Day 5–6: Planner handoff

**Week 2:**
- Day 7–8: Interactive multimodal
- Day 9–10: Full integration testing
- Day 11–14: Polish + documentation

**Result:** Learner Agent 9.8/10, ready for Research Agent

---

## Why These 4 Features Matter Most

| Feature | Makes Learner Feel Like | Key Metric | Time to Build |
|---------|---|---|---|
| **Real RAG** | Mentor (uses actual resources) | Citation count per session | 4 days |
| **Adaptive** | Intelligent (never repeats) | Approach diversity | 3 days |
| **Handoff** | Part of system (not isolated) | Integration completeness | 2 days |
| **Multimodal** | Professional (SVG + audio + quiz) | Learning effectiveness | 4 days |

Together: **Transform 8.9 → 9.8**
