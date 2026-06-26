"""
Understanding Engine

The heart of the Learner Agent.
Not just explaining - ensuring understanding.

Features:
- Layer 0: Prior knowledge assessment
- Layer 1-3: Progressive teaching (intuition → structured → advanced)
- Confusion detection
- Active understanding checks
- Adaptive re-explanation
"""

from typing import Literal, Optional
from app.llm import ask_gemini
import json
import re


class UnderstandingEngine:
    """Manages the teaching process with understanding verification."""
    
    def __init__(self, llm_or_state=None):
        # Accept either llm (new style) or state dict (legacy)
        if isinstance(llm_or_state, dict):
            self.state = llm_or_state
            self.llm = None
        else:
            self.llm = llm_or_state
            self.state = {}
        self.confusion_score = 0
        self.current_layer = "layer_0"
        self.understanding_checks = []
    
    def assess_prior_knowledge(self, topic: str, subject: str) -> dict:
        """
        Layer 0: Assess what student already knows.
        Don't assume zero knowledge.
        """
        prompt = f"""You are assessing a student's prior knowledge before teaching.

Topic: {topic}
Subject: {subject}

Generate 3 simple questions to check what they already know:
1. Basic familiarity check
2. Related concept check
3. Application awareness

Return ONLY JSON:
{{
  "questions": [
    "Have you studied {topic} before?",
    "What does [related concept] mean to you?",
    "Can you think of a real-world example?"
  ]
}}
"""
        
        try:
            raw = ask_gemini(prompt)
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(clean)
            return {
                "questions": data.get("questions", []),
                "layer": "prior_knowledge",
            }
        except:
            return {
                "questions": [
                    f"Have you studied {topic} before?",
                    "What do you already know about this topic?",
                    "Any questions or confusion before we start?"
                ],
                "layer": "prior_knowledge",
            }
    
    def analyze_prior_knowledge_response(self, responses: list[str]) -> dict:
        """Analyze prior knowledge to determine starting level."""
        # Simple heuristic analysis
        combined = " ".join(responses).lower()
        
        knowledge_level = "beginner"
        if any(word in combined for word in ["yes", "familiar", "studied", "know"]):
            knowledge_level = "intermediate"
        if any(word in combined for word in ["expert", "mastered", "taught", "explained"]):
            knowledge_level = "advanced"
        
        return {
            "level": knowledge_level,
            "skip_basics": knowledge_level in ["intermediate", "advanced"],
            "start_layer": "layer_1" if knowledge_level == "beginner" else "layer_2",
        }
    
    def teach_layer_1_intuition(self, topic: str, context_or_subject=None, prior_knowledge: dict = None) -> dict:
        subject = context_or_subject if isinstance(context_or_subject, str) else (context_or_subject or {}).get("subject", "general")
        prior_knowledge = prior_knowledge or {}
        """
        Layer 1: Intuition - No jargon, only analogies and real-life.
        """
        level = prior_knowledge.get("level", "beginner")
        
        prompt = f"""You are teaching {topic} in {subject} to a {level} student.

Layer 1: INTUITION (No technical jargon)

Rules:
- Use ONLY real-life analogies
- No technical terms yet
- Make it feel obvious
- 2-3 sentences max

Example for "FCFS Algorithm":
"Imagine a bank with one teller. Whoever arrives first gets served first. No skipping the line. That's First Come First Served."

Now explain {topic} in {subject} the same way.

Return ONLY JSON:
{{
  "intuition": "your simple explanation",
  "analogy": "real-world example",
  "understanding_check": "simple question to verify understanding"
}}
"""
        
        try:
            raw = ask_gemini(prompt)
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            start = clean.find("{")
            end = clean.rfind("}") + 1
            if start != -1 and end > start:
                clean = clean[start:end]
            data = json.loads(clean)
            
            return {
                "layer": "intuition",
                "content": data.get("intuition", ""),
                "analogy": data.get("analogy", ""),
                "check": data.get("understanding_check", "Does this make sense so far?"),
            }
        except Exception as e:
            print(f"[Understanding Engine] Layer 1 fallback: {e}")
            return {
                "layer": "intuition",
                "content": f"{topic} is like... (think of a simple real-world analogy)",
                "analogy": "Real-world example needed",
                "check": "Does this basic idea make sense?",
            }
    
    def teach_layer_2_structured(self, topic: str, subject: str = "general", prior_knowledge: dict = None) -> dict:
        prior_knowledge = prior_knowledge or {}
        """
        Layer 2: Structured - Introduce terminology, components, flow.
        """
        prompt = f"""You are teaching {topic} in {subject}.

Layer 2: STRUCTURED EXPLANATION

Now introduce:
- Proper definitions
- Key components
- How it works (step-by-step)
- Important terminology

Keep it clear and organized.

Return ONLY JSON:
{{
  "definition": "formal definition",
  "components": ["component1", "component2"],
  "steps": ["step1", "step2", "step3"],
  "key_terms": {{"term1": "meaning", "term2": "meaning"}},
  "understanding_check": "question to verify structural understanding"
}}
"""
        
        try:
            raw = ask_gemini(prompt)
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            start = clean.find("{")
            end = clean.rfind("}") + 1
            if start != -1 and end > start:
                clean = clean[start:end]
            data = json.loads(clean)
            
            return {
                "layer": "structured",
                "definition": data.get("definition", ""),
                "components": data.get("components", []),
                "steps": data.get("steps", []),
                "key_terms": data.get("key_terms", {}),
                "check": data.get("understanding_check", "Can you explain the main steps?"),
            }
        except Exception as e:
            print(f"[Understanding Engine] Layer 2 fallback: {e}")
            return {
                "layer": "structured",
                "definition": f"Formal definition of {topic}",
                "components": [],
                "steps": [],
                "key_terms": {},
                "check": "Do you understand the main concept?",
            }
    
    def teach_layer_3_advanced(self, topic: str, subject: str = "general") -> dict:
        """
        Layer 3: Advanced - Edge cases, numericals, interview questions.
        """
        prompt = f"""You are teaching {topic} in {subject} at an advanced level.

Layer 3: ADVANCED CONCEPTS

Cover:
- Edge cases
- Advantages & Disadvantages
- Comparison with alternatives
- Numerical/problem-solving approach
- Interview-level insights

Return ONLY JSON:
{{
  "edge_cases": ["case1", "case2"],
  "advantages": ["adv1", "adv2"],
  "disadvantages": ["dis1", "dis2"],
  "comparison": "brief comparison with alternatives",
  "problem_approach": "how to solve problems on this",
  "understanding_check": "advanced-level question"
}}
"""
        
        try:
            raw = ask_gemini(prompt)
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            start = clean.find("{")
            end = clean.rfind("}") + 1
            if start != -1 and end > start:
                clean = clean[start:end]
            data = json.loads(clean)
            
            return {
                "layer": "advanced",
                "edge_cases": data.get("edge_cases", []),
                "advantages": data.get("advantages", []),
                "disadvantages": data.get("disadvantages", []),
                "comparison": data.get("comparison", ""),
                "problem_approach": data.get("problem_approach", ""),
                "check": data.get("understanding_check", "Can you solve a problem on this?"),
            }
        except Exception as e:
            print(f"[Understanding Engine] Layer 3 fallback: {e}")
            return {
                "layer": "advanced",
                "edge_cases": [],
                "advantages": [],
                "disadvantages": [],
                "comparison": "",
                "problem_approach": "",
                "check": "Ready for practice problems?",
            }
    
    def detect_confusion(self, message: str) -> int:
        """
        Detect confusion from student's response.
        Returns confusion score (0-10).
        """
        message_lower = message.lower()
        
        confusion_signals = {
            "explain again": 2,
            "don't get": 3,
            "don't understand": 3,
            "still confused": 3,
            "not clear": 2,
            "why": 1,
            "how": 1,
            "what": 1,
            "confused": 3,
            "lost": 2,
            "hard": 2,
            "difficult": 2,
            "complicated": 2,
            "can you simplify": 2,
            "one more time": 2,
            "another example": 1,
        }
        
        score = 0
        for signal, points in confusion_signals.items():
            if signal in message_lower:
                score += points
        
        self.confusion_score += score
        return self.confusion_score
    
    def check_understanding(self, student_response: str, expected_concepts) -> dict:
        """
        Active understanding check - analyze open-ended response.
        expected_concepts can be a list[str] or a single str (topic name).
        """
        if isinstance(expected_concepts, str):
            expected_concepts = [expected_concepts]
        response_lower = student_response.lower()
        
        # Check concept coverage
        concepts_mentioned = sum(1 for concept in expected_concepts if concept.lower() in response_lower)
        coverage = concepts_mentioned / len(expected_concepts) if expected_concepts else 0
        
        # Check for misconceptions (simple keyword-based)
        misconception_patterns = [
            (r"(opposite|reverse|backwards)", "Potential reversed understanding"),
            (r"(same as|identical to|exactly like)", "Potential over-simplification"),
        ]
        
        misconceptions = []
        for pattern, description in misconception_patterns:
            if re.search(pattern, response_lower):
                misconceptions.append(description)
        
        # Confidence analysis (simple heuristic)
        confidence_high = any(word in response_lower for word in ["definitely", "clearly", "obviously", "sure"])
        confidence_low = any(word in response_lower for word in ["maybe", "think", "guess", "perhaps", "probably"])
        
        confidence = "high" if confidence_high else "low" if confidence_low else "medium"
        
        # Overall understanding score
        understanding_score = coverage * 5  # 0-5 scale
        
        if misconceptions:
            understanding_score = max(0, understanding_score - 1)
        
        return {
            "understanding_score": round(understanding_score, 1),
            "concept_coverage": round(coverage * 100),
            "confidence": confidence,
            "misconceptions": misconceptions,
            "needs_clarification": understanding_score < 3 or misconceptions or confidence == "low",
        }
    
    def adapt_explanation(self, confusion_score: int, failed_checks: int) -> str:
        """
        Decide how to adapt teaching based on confusion.
        """
        if confusion_score >= 7 or failed_checks >= 3:
            return "switch_method"  # Try completely different approach
        elif confusion_score >= 4 or failed_checks >= 2:
            return "simplify"  # Break into smaller pieces
        elif confusion_score >= 2 or failed_checks >= 1:
            return "add_example"  # Give another example
        else:
            return "continue"  # Understanding is good
    
    def generate_alternative_explanation(self, topic: str, subject: str, failed_approach: str) -> dict:
        """Generate a different type of explanation when student is confused."""
        prompt = f"""The student is confused about {topic} in {subject}.

Previous approach ({failed_approach}) didn't work.

Generate a COMPLETELY DIFFERENT explanation:
- If theory failed, use visual/diagram approach
- If abstract, use concrete examples
- If examples failed, try interactive question-based approach

Return ONLY JSON:
{{
  "approach": "new approach type",
  "explanation": "completely different way to explain",
  "interactive_element": "question or activity for student"
}}
"""
        
        try:
            raw = ask_gemini(prompt)
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            start = clean.find("{")
            end = clean.rfind("}") + 1
            if start != -1 and end > start:
                clean = clean[start:end]
            data = json.loads(clean)
            
            return {
                "approach": data.get("approach", "alternative"),
                "explanation": data.get("explanation", ""),
                "interactive": data.get("interactive_element", ""),
            }
        except:
            return {
                "approach": "alternative",
                "explanation": f"Let's try thinking about {topic} differently...",
                "interactive": "What part is most confusing?",
            }


def understanding_engine_node(state: dict) -> dict:
    """Main entry point for understanding engine."""
    from app.state import StudentState
    
    s = StudentState(**state)
    engine = UnderstandingEngine(state)
    
    # Get current learning unit
    unit_id = s.learner_output.get("current_unit_id")
    if not unit_id:
        s.agent_response = "No active learning unit. Start from Planner or search for a topic."
        return s.model_dump()
    
    # Teaching flow based on current stage
    stage = s.learner_output.get("teaching_stage", "prior_knowledge")
    
    if stage == "prior_knowledge":
        # Layer 0: Assess what they know
        result = engine.assess_prior_knowledge(
            s.learner_output.get("topic", ""),
            s.learner_output.get("subject", "")
        )
        
        s.agent_response = (
            f"Before we start learning {s.learner_output.get('topic')}...\n\n"
            f"Quick check:\n"
        )
        for i, q in enumerate(result["questions"], 1):
            s.agent_response += f"{i}. {q}\n"
        
        s.learner_output["teaching_stage"] = "assess_response"
        s.learner_output["pending_questions"] = result["questions"]
    
    return s.model_dump()
