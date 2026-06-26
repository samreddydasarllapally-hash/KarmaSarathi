"""
Learner Agent - The Understanding Engine
Complete teaching system that ensures student understanding, not just explanation
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from app.learning_passport import PassportManager, LearningPassport
from app.safety import ContextAnalyzer
from app.agents.understanding_engine import UnderstandingEngine
from app.agents.resource_generator import ResourceGenerator
from app.agents.resource_hub import KnowledgeHub
from app.agents.rag_engine import RAGEngine
from app.agents.conversational_teacher import ConversationalTeacher
from app.agents.engagement_monitor import EngagementMonitor, EngagementSnapshot
from app.event_bus import LearnerEventEmitter, EventBus, EventType


class _LivePlannerHandler:
    """
    Real-time planner state updater wired to Learner events.
    Updates learning_units in planner state when Learner emits
    completion / struggling events — no polling required.
    """

    def __init__(self, planner_state: dict):
        self.planner_state = planner_state

    def handle_unit_completed(self, event):
        data = event.data
        unit_name = data.get("learning_unit", "")
        mastery   = data.get("mastery_score", 0.0)

        for unit in self.planner_state.get("learning_units", []):
            if (unit.get("unit_name", "").lower() == unit_name.lower() or
                    unit.get("chapter", "").lower() == unit_name.lower()):
                unit["status"]        = "completed"
                unit["completion_pct"] = 100
                unit["mastery"]       = round(mastery * 5, 2)   # 0-1 → 0-5
                unit["completed_at"]  = datetime.now().isoformat()
                unit["last_accessed"] = datetime.now().isoformat()
                break

        # Unlock next pending unit sequentially
        pending = [u for u in self.planner_state.get("learning_units", [])
                   if u.get("status") == "pending"]
        if pending:
            self.planner_state.setdefault("next_unit_ready", pending[0].get("unit_name"))

    def handle_needs_more_time(self, event):
        data      = event.data
        unit_name = data.get("learning_unit", "")
        extra     = data.get("additional_sessions", 1)

        for unit in self.planner_state.get("learning_units", []):
            if unit.get("unit_name", "").lower() == unit_name.lower():
                unit["estimated_minutes"] = unit.get("estimated_minutes", 30) + extra * 30
                break

    def handle_student_struggling(self, event):
        data      = event.data
        unit_name = data.get("learning_unit", "")
        score     = data.get("confusion_score", 0)

        for unit in self.planner_state.get("learning_units", []):
            if unit.get("unit_name", "").lower() == unit_name.lower():
                unit["difficulty"] = "hard"
                unit.setdefault("struggle_events", []).append({
                    "confusion_score": score,
                    "timestamp": datetime.now().isoformat()
                })
                break


class LearnerAgent:
    """
    The Understanding Engine — ensures students truly understand concepts.
    Teaches one learning unit at a time with layered RAG-grounded explanations,
    engagement monitoring, and automatic planner handoff via event bus.
    """

    def __init__(self, llm, user_id: str, state: dict = None):
        self.llm     = llm
        self.user_id = user_id
        self.state   = state or {}

        # Core teaching components
        self.passport_manager    = PassportManager(self.state)
        self.safety              = ContextAnalyzer(llm)
        self.understanding_engine = UnderstandingEngine(llm)
        self.resource_generator  = ResourceGenerator(llm)
        self.resource_hub        = KnowledgeHub(user_id, self.state)
        self.rag_engine          = RAGEngine(llm, user_id, self.state)
        self.conversational      = ConversationalTeacher(llm)

        # Event system
        self.event_bus     = EventBus(self.state)
        self.event_emitter = LearnerEventEmitter(self.event_bus, user_id)

        # Engagement monitor — rule-based; LLM used only for free-text sentiment
        self.engagement_monitor = EngagementMonitor(llm)
        self._used_analogies: list = []   # prevent analogy repetition

        # Session state
        self.current_unit     = None
        self.current_passport = None
        self.session_active   = False
        self._planner_handler = None   # set via wire_planner()

    # ── Planner wiring ────────────────────────────────────────────────────────

    def wire_planner(self, planner_state: dict):
        """
        Connect this learner to the planner's live state dict.
        Unit-completion events automatically update planner.learning_units.
        """
        self._planner_handler = _LivePlannerHandler(planner_state)
        self.event_bus.subscribe(EventType.UNIT_COMPLETED,
                                 self._planner_handler.handle_unit_completed)
        self.event_bus.subscribe(EventType.NEEDS_MORE_TIME,
                                 self._planner_handler.handle_needs_more_time)
        self.event_bus.subscribe(EventType.STUDENT_STRUGGLING,
                                 self._planner_handler.handle_student_struggling)

    # ── Session lifecycle ─────────────────────────────────────────────────────

    def start_learning_session(self, learning_unit: str, subject: str) -> Dict[str, Any]:
        """Start or resume a learning session for one unit."""
        self.current_passport = self.passport_manager.get_passport(self.user_id, learning_unit)
        if not self.current_passport:
            self.current_passport = self.passport_manager.create_passport(
                user_id=self.user_id,
                learning_unit=learning_unit,
                subject=subject
            )

        self.current_unit   = learning_unit
        self.session_active = True

        can_resume, checkpoint = self.passport_manager.can_resume_session(
            self.user_id, learning_unit
        )
        if can_resume and checkpoint:
            return {
                "type":      "resume_session",
                "message":   f"Welcome back! You were at {checkpoint['completion_pct']}% completion.",
                "checkpoint": checkpoint,
                "options":   ["Resume from checkpoint", "Start fresh", "Skip to practice"]
            }

        return {
            "type":        "start_session",
            "message":     f"Let's learn: {learning_unit}",
            "next_action": "assess_prior_knowledge"
        }

    def end_session(self) -> Dict[str, Any]:
        if not self.session_active:
            return {"message": "No active session to end"}

        checkpoint   = self.current_passport.session_checkpoint
        progress_pct = checkpoint.get("completion_pct", 0)

        if progress_pct < 100:
            self.event_emitter.emit_session_paused(
                learning_unit=self.current_unit,
                progress_pct=progress_pct,
                checkpoint=checkpoint
            )

        self.session_active = False
        return {
            "type":     "session_ended",
            "message":  f"Session saved! You can resume '{self.current_unit}' anytime.",
            "unit":     self.current_unit,
            "progress": f"{self.current_passport.mastery_level * 100:.0f}%"
        }

    def request_more_time(self, additional_sessions: int, reason: str) -> Dict[str, Any]:
        if not self.session_active:
            return {"error": "No active session"}
        self.event_emitter.emit_needs_more_time(
            learning_unit=self.current_unit,
            additional_sessions=additional_sessions,
            reason=reason
        )
        return {
            "type":    "more_time_requested",
            "message": f"Requested {additional_sessions} more sessions for {self.current_unit}",
            "status":  "planner_notified"
        }

    def get_session_status(self) -> Dict[str, Any]:
        if not self.session_active or not self.current_passport:
            return {"active": False}
        return {
            "active":          True,
            "unit":            self.current_unit,
            "mastery_level":   self.current_passport.mastery_level,
            "confusion_score": self.current_passport.cumulative_confusion_score,
            "doubts_count":    len(self.current_passport.doubt_history),
            "time_spent":      self.current_passport.total_time_spent_minutes
        }

    # ── Main interaction handler ──────────────────────────────────────────────

    def process_learning_interaction(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route one student message through the full pipeline:
        safety → engagement monitoring → confusion detection → teaching layer.
        """
        if not self.session_active or not self.current_passport:
            return {"error": "No active learning session. Start a session first."}

        # Safety check
        safety_result = self.safety.analyze_safety(
            user_input,
            context={"learning_unit": self.current_unit, "intent": "learning"}
        )
        if not safety_result["is_safe"]:
            return {
                "type":       "safety_block",
                "message":    "I can't help with that. Let's stay focused on learning.",
                "suggestion": safety_result.get("suggestion", "Ask an educational question.")
            }

        # Engagement monitor — rule-based, zero extra LLM calls for routine messages
        self.engagement_monitor.record_interaction(
            user_input,
            quiz_score=context.get("quiz_score"),
            response_time_sec=context.get("response_time_sec"),
            wrong_answers=context.get("wrong_answers", 0)
        )
        snap = self.engagement_monitor.snapshot()
        context["engagement"] = snap.to_dict()

        # Confusion detection (keyword-based)
        confusion_score = self.understanding_engine.detect_confusion(user_input)
        if confusion_score > 0:
            self.current_passport.confusion_signals.append(user_input)
            self.current_passport.cumulative_confusion_score += confusion_score

        # Frustration tracking
        self._check_emotional_state(user_input)

        # Emit struggling event to planner when confusion is high
        if self.current_passport.cumulative_confusion_score >= 7:
            self.event_emitter.emit_student_struggling(
                learning_unit=self.current_unit,
                confusion_score=self.current_passport.cumulative_confusion_score,
                stuck_on=user_input[:100]
            )

        # Route to doubt handler or teaching layer
        if self._is_question(user_input):
            return self._handle_doubt(user_input, context)

        layer = context.get("current_layer", 0)
        if layer == 0:
            return self._handle_layer_0(user_input, context)
        elif layer == 1:
            return self._handle_layer_1(user_input, context)
        elif layer == 2:
            return self._handle_layer_2(user_input, context)
        elif layer == 3:
            return self._handle_layer_3(user_input, context)
        else:
            return self._handle_completion(user_input, context)

    # ── Teaching layers ───────────────────────────────────────────────────────

    def _handle_layer_0(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 0: Prior-knowledge assessment."""
        if context.get("action") == "start_assessment":
            assessment = self.understanding_engine.assess_prior_knowledge(
                self.current_unit, context.get("subject", "general")
            )
            self.passport_manager.record_session_checkpoint(
                self.user_id, self.current_unit,
                completed_layers=[], current_layer=0, completion_pct=10
            )
            return {
                "type":      "assessment",
                "questions": assessment["questions"],
                "message":   "Let me understand what you already know. Answer these briefly:",
                "progress":  "10% - Assessing knowledge"
            }

        prior_knowledge = self._analyze_assessment(user_input)
        self.current_passport.prior_knowledge_level = prior_knowledge["level"]
        start_layer = 1 if prior_knowledge["level"] == "beginner" else 2
        return {
            "type":    "assessment_complete",
            "message": f"Got it! Starting at {['beginner', 'intermediate', 'advanced'][start_layer-1]} level.",
            "next_layer": start_layer,
            "action":  "proceed_to_teaching"
        }

    def _handle_layer_1(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 1: Intuitive teaching — RAG-grounded, engagement-enriched."""
        snap = self.engagement_monitor.snapshot()

        if context.get("action") == "teach":
            rag_result = self.rag_engine.generate_grounded_explanation(
                topic=self.current_unit,
                query="explain intuitively with real-life analogies, no jargon",
                context={"layer": 1, "subject": context.get("subject", "general")}
            )

            if not rag_result.get("grounded"):
                base = (
                    f"Explain {self.current_unit} intuitively with a real-life analogy. "
                    f"No jargon. 2-3 sentences max."
                )
                enriched = self.engagement_monitor.enrich_prompt(
                    base, snap, self.current_unit, self._used_analogies
                )
                explanation = self.llm.invoke(enriched).content
                sources = []
            else:
                explanation = rag_result["explanation"]
                sources     = rag_result.get("sources", [])

            analogy = self.resource_generator.generate_analogy(
                self.current_unit, context.get("student_profile", {})
            )
            if analogy:
                self._used_analogies.append(analogy[:60])

            self.passport_manager.record_session_checkpoint(
                self.user_id, self.current_unit,
                completed_layers=[], current_layer=1, completion_pct=30
            )
            return {
                "type":               "teaching",
                "layer":              1,
                "explanation":        explanation,
                "analogy":            analogy,
                "sources":            sources,
                "grounded":           rag_result.get("grounded", False),
                "engagement":         snap.to_dict(),
                "message":            "Here's the intuitive understanding:",
                "progress":           "30% - Building intuition",
                "check_understanding": True
            }

        understanding = self.understanding_engine.check_understanding(
            user_input, self.current_unit
        )
        if understanding.get("passes", False):
            return {
                "type":    "layer_complete",
                "message": "Great! You've got the intuition. Ready for details?",
                "next_layer": 2,
                "options": ["Continue to structured learning", "Practice with problems", "Take a break"]
            }

        clarification = self._conversational_response(user_input, context, layer=1)
        return {
            "type":               "clarification",
            "message":            clarification,
            "explanation":        clarification,
            "engagement":         snap.to_dict(),
            "check_understanding": True
        }

    def _handle_layer_2(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 2: Structured teaching — RAG-grounded + SVG diagram."""
        snap = self.engagement_monitor.snapshot()

        if context.get("action") == "teach":
            rag_result = self.rag_engine.generate_grounded_explanation(
                topic=self.current_unit,
                query="structured explanation with definition, components, and step-by-step flow",
                context={"layer": 2, "subject": context.get("subject", "general")}
            )

            if not rag_result.get("grounded"):
                base = (
                    f"Explain {self.current_unit} in a structured way: "
                    f"definition, key components, step-by-step flow."
                )
                enriched = self.engagement_monitor.enrich_prompt(
                    base, snap, self.current_unit, self._used_analogies
                )
                explanation = self.llm.invoke(enriched).content
                sources = []
            else:
                explanation = rag_result["explanation"]
                sources     = rag_result.get("sources", [])

            svg = self.resource_generator.generate_interactive_svg(
                self.current_unit, self.current_unit, layer=2
            )
            self.passport_manager.record_resource_used(
                self.user_id, self.current_unit, "svg_generated", {"layer": 2}
            )
            self.passport_manager.record_session_checkpoint(
                self.user_id, self.current_unit,
                completed_layers=[0, 1], current_layer=2, completion_pct=60
            )
            return {
                "type":               "teaching",
                "layer":              2,
                "explanation":        explanation,
                "svg":                svg,
                "sources":            sources,
                "grounded":           rag_result.get("grounded", False),
                "engagement":         snap.to_dict(),
                "message":            "Now let's understand the structure:",
                "progress":           "60% - Structured learning",
                "check_understanding": True
            }

        understanding = self.understanding_engine.check_understanding(
            user_input, self.current_unit
        )
        if understanding.get("passes", False):
            flashcards = self.resource_generator.generate_flashcards(
                self.current_unit, context.get("concepts_taught", []), difficulty="medium"
            )
            return {
                "type":       "layer_complete",
                "message":    "Excellent! You understand the structure. Want to go deeper?",
                "flashcards": flashcards,
                "next_layer": 3,
                "options":    ["Continue to advanced", "Practice problems", "Review flashcards", "End session"]
            }

        clarification = self._conversational_response(user_input, context, layer=2)
        return {
            "type":               "clarification",
            "message":            clarification,
            "explanation":        clarification,
            "engagement":         snap.to_dict(),
            "check_understanding": True
        }

    def _handle_layer_3(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 3: Advanced teaching — edge cases, practice problems, SVG."""
        snap = self.engagement_monitor.snapshot()

        if context.get("action") == "teach":
            raw         = self.understanding_engine.teach_layer_3_advanced(
                self.current_unit, context.get("subject", "general")
            )
            explanation = raw if isinstance(raw, str) else raw.get("comparison", str(raw))

            # Enrich if confidence is high (challenge mode)
            if snap.recommended_style == "challenge":
                base     = explanation + "\n\nAdd an interview-level edge-case question."
                enriched = self.engagement_monitor.enrich_prompt(
                    base, snap, self.current_unit, self._used_analogies
                )
                explanation = self.llm.invoke(enriched).content

            problems = self.resource_generator.generate_practice_problems(
                self.current_unit, difficulty="medium", count=3
            )
            svg = self.resource_generator.generate_interactive_svg(
                self.current_unit, self.current_unit, layer=3
            )
            self.passport_manager.record_resource_used(
                self.user_id, self.current_unit, "svg_generated", {"layer": 3}
            )
            self.passport_manager.record_session_checkpoint(
                self.user_id, self.current_unit,
                completed_layers=[0, 1, 2], current_layer=3, completion_pct=90
            )
            return {
                "type":               "teaching",
                "layer":              3,
                "explanation":        explanation,
                "svg":                svg,
                "practice_problems":  problems,
                "engagement":         snap.to_dict(),
                "message":            "Now for the advanced understanding:",
                "progress":           "90% - Advanced mastery",
                "check_understanding": True
            }

        understanding = self.understanding_engine.check_understanding(
            user_input, self.current_unit
        )
        if understanding.get("passes", False):
            summary         = self.resource_generator.generate_summary(
                self.current_unit, layer=3,
                content_covered=context.get("concepts_taught", [])
            )
            completion_data = self._generate_completion_data(context)
            self.passport_manager.record_completion(
                self.user_id, self.current_unit, completion_data
            )

            # Notify planner via event bus (no polling)
            self.event_emitter.emit_unit_completed(
                learning_unit=self.current_unit,
                mastery_data={
                    "mastery_score":      completion_data["mastery_score"],
                    "confidence_level":   completion_data["confidence_level"],
                    "time_spent_minutes": completion_data["time_spent_minutes"],
                    "layers_completed":   completion_data["layers_completed"],
                    "doubts_count":       len(self.current_passport.doubt_history),
                    "confusion_score":    self.current_passport.cumulative_confusion_score,
                    "resources_used":     completion_data["resources_used"],
                    "engagement":         snap.to_dict()
                }
            )
            return {
                "type":         "unit_complete",
                "message":      "Congratulations! You've mastered this unit!",
                "summary":      summary,
                "mastery_score": completion_data["mastery_score"],
                "time_spent":   completion_data["time_spent_minutes"],
                "engagement":   snap.to_dict(),
                "options":      ["Return to planner", "Practice more", "Review summary"]
            }

        return {
            "type":               "needs_practice",
            "message":            "You're close! Let's practice with some problems:",
            "practice_problems":  self.resource_generator.generate_practice_problems(
                self.current_unit, difficulty="easy", count=2
            ),
            "check_understanding": True
        }

    def _handle_completion(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type":    "session_end",
            "message": "Session completed! Great work today.",
            "action":  "return_to_planner"
        }

    # ── Support methods ───────────────────────────────────────────────────────

    def _check_emotional_state(self, user_input: str):
        """Rule-based frustration detection — no LLM call."""
        phrases = [
            "asked this", "asked again", "still don't", "i've asked",
            "told you", "not getting it", "same question", "again and again"
        ]
        if any(p in user_input.lower() for p in phrases):
            self.passport_manager.record_frustration(self.user_id, self.current_unit)
            self.current_passport.frustration_signals += 1

    def _conversational_response(self, user_input: str, context: Dict[str, Any], layer: int) -> str:
        """
        Build a single LLM call enriched with the full engagement snapshot.
        Tone shifts automatically based on frustration / confusion levels.
        """
        passport    = self.current_passport
        frustration = getattr(passport, "frustration_signals", 0)
        snap        = self.engagement_monitor.snapshot()

        if snap.intervention_needed or frustration >= 2:
            base = (
                f"The student has asked about '{self.current_unit}' "
                f"{len(passport.doubt_history)} time(s) and shown frustration "
                f"{frustration} time(s). Their last message: \"{user_input}\"\n\n"
                f"Respond as a patient mentor. Acknowledge frustration FIRST. "
                f"Forget formulas — build intuition with a fresh real-world analogy. "
                f"Max 4 sentences. End with one easy re-engagement question."
            )
        else:
            base = (
                f"Student is learning '{self.current_unit}' (layer {layer}). "
                f"They said: \"{user_input}\"\n\n"
                f"Respond conversationally as a mentor. Clarify the specific confusion. "
                f"Give one concrete example. End with a guiding question."
            )

        enriched = self.engagement_monitor.enrich_prompt(
            base, snap, self.current_unit, self._used_analogies
        )
        return self.llm.invoke(enriched).content

    def _handle_doubt(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Record doubt in passport and return an adapted explanation."""
        confusion_level = min(self.current_passport.cumulative_confusion_score / 3, 3)
        self.passport_manager.record_doubt(
            self.user_id, self.current_unit,
            question=question,
            confusion_level=int(confusion_level),
            context=context
        )
        strategy    = self.understanding_engine.adapt_explanation(
            confusion_score=self.current_passport.cumulative_confusion_score,
            failed_checks=self.current_passport.attempts
        )
        doubt_answer = self.understanding_engine.generate_alternative_explanation(
            topic=self.current_unit,
            subject=context.get("subject", "general"),
            failed_approach=strategy
        )
        return {
            "type":      "doubt_response",
            "question":  question,
            "answer":    doubt_answer.get("explanation", ""),
            "message":   "Great question! Here's the answer:",
            "follow_up": "Does that make sense? Any other questions?"
        }

    def _is_question(self, text: str) -> bool:
        question_words = ["what", "why", "how", "when", "where", "explain", "clarify", "mean"]
        text_lower = text.lower()
        return "?" in text or any(w in text_lower for w in question_words)

    def _analyze_assessment(self, answers: str) -> Dict[str, Any]:
        import json
        prompt = (
            f"Analyze these assessment answers:\n{answers}\n\n"
            "Determine knowledge level: beginner / intermediate / advanced\n"
            'Return JSON: {"level": "...", "knows": ["concept1"], "gaps": ["concept2"]}'
        )
        response = self.llm.invoke(prompt).content
        try:
            start = response.find("{")
            end   = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except Exception:
            pass
        return {"level": "beginner", "knows": [], "gaps": []}

    def _generate_completion_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        confusion_score   = self.current_passport.cumulative_confusion_score
        confusion_penalty = min(confusion_score * 0.05, 0.3)
        mastery_score     = min(1.0, max(0.0, 0.7 - confusion_penalty + 0.1))
        resources         = self.current_passport.resources_used
        doubt_count       = len(self.current_passport.doubt_history)
        return {
            "mastery_score":       mastery_score,
            "confidence_level":    context.get("confidence_level", 2),
            "time_spent_minutes":  context.get("time_spent", 0),
            "layers_completed":    [0, 1, 2, 3],
            "mastery_dimensions": {
                "concept":         round(max(0.0, 1.0 - confusion_score * 0.08), 2),
                "application":     round(max(0.0, mastery_score - 0.1), 2),
                "problem_solving": round(max(0.0, mastery_score - 0.15), 2),
                "explanation":     round(mastery_score, 2),
                "overall":         round(mastery_score, 2)
            },
            "resources_used":    context.get("resources_used", []),
            "svgs_generated":    resources.get("svgs_generated", 0),
            "svgs_viewed":       resources.get("svgs_viewed", 0),
            "pdfs_used":         len(resources.get("pdfs", [])),
            "bookmarks_used":    len(resources.get("bookmarks_used", [])),
            "doubts_count":      doubt_count,
            "confusion_score":   confusion_score,
            "quiz_score":        context.get("quiz_score"),
            "practice_score":    context.get("practice_score"),
            "quiz_attempts":     context.get("quiz_attempts", 0),
            "practice_attempts": context.get("practice_attempts", 0),
            "assessment_results": context.get("assessment_results", {}),
        }


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph node  (entry point used by graph.py)
# ─────────────────────────────────────────────────────────────────────────────

def learner_node(state: dict) -> dict:
    """
    LangGraph entry point for the Learner Agent.

    Handles three cases:
      1. Returning from a research handoff (return_to_agent == "learner")
      2. Bridge call during active task (diagram/mcq/video requested mid-task)
      3. Direct teach/explain request (standalone or post-mastery)
    """
    from app.state import StudentState
    from app.llm import ask_gemini
    import json
    from datetime import datetime

    s = StudentState(**state)
    msg = (s.user_message or "").strip()
    lower = msg.lower()

    # Clear any consumed handoff
    if s.agent_handoff and s.agent_handoff.get("to") == "learner":
        s.agent_handoff = None

    # ── helpers ───────────────────────────────────────────────────────────────

    def _explanation(topic: str, subject: str, style: str) -> str:
        style_map = {
            "videos":   "visual and diagram-heavy",
            "books":    "detailed textbook-style",
            "practice": "example-driven with practice problems",
            "notes":    "concise bullet-point style",
        }
        fmt = style_map.get(style.lower() if style else "", "clear and simple")
        prompt = (
            f"Explain {topic} from {subject} in a {fmt} way.\n"
            "Structure: 1) Core concept (1-2 sentences) "
            "2) Key points (3-4 bullets) 3) Simple example 4) Common mistake.\n"
            "Keep it under 150 words. Be practical."
        )
        try:
            return ask_gemini(prompt).strip()
        except Exception:
            return f"**{topic}** — focus on definition, use cases, and examples."

    def _analogy(topic: str, subject: str) -> str:
        prompt = (
            f"Create a funny, memorable analogy to explain {topic} from {subject}.\n"
            "Make it relatable, funny, and 2-3 sentences. Return ONLY the analogy."
        )
        try:
            return ask_gemini(prompt).strip().strip('"').strip("'")
        except Exception:
            return f"Think of {topic} as a recipe — you need the right ingredients in the right order."

    def _svg(topic: str, subject: str) -> str:
        prompt = (
            f"Generate a clean SVG diagram explaining {topic} from {subject}.\n"
            "Return ONLY valid SVG. Dimensions 600x400. Use shapes, arrows, labels."
        )
        try:
            raw = ask_gemini(prompt).strip()
            if "<svg" in raw:
                s_idx = raw.find("<svg")
                e_idx = raw.find("</svg>") + 6
                return raw[s_idx:e_idx] if e_idx > s_idx else _fallback_svg(topic)
        except Exception:
            pass
        return _fallback_svg(topic)

    def _fallback_svg(topic: str) -> str:
        return (
            f"<svg xmlns='http://www.w3.org/2000/svg' width='600' height='300'>"
            "<rect width='100%' height='100%' fill='#f8f9fa'/>"
            f"<text x='300' y='150' text-anchor='middle' font-size='20' fill='#333'>{topic}</text>"
            "</svg>"
        )

    def _videos(topic: str, subject: str) -> list:
        return [
            f"{topic} explained simply — {subject}",
            f"{topic} tutorial for beginners",
            f"{topic} with examples and practice",
        ]

    def _mcqs(topic: str, subject: str) -> list:
        prompt = (
            f"Create 5 MCQs on {topic} ({subject}).\n"
            'Return ONLY JSON array: [{"q":"...","opts":["A","B","C","D"],"ans":"A","why":"..."}]'
        )
        try:
            raw = ask_gemini(prompt).strip()
            clean = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            s_idx = clean.find("[")
            e_idx = clean.rfind("]") + 1
            if s_idx != -1 and e_idx > s_idx:
                return json.loads(clean[s_idx:e_idx])
        except Exception:
            pass
        return [{"q": f"What is {topic}?", "opts": ["A", "B", "C", "D"], "ans": "A", "why": "Definition"}]

    def _revision_notes(topic: str, subject: str, expl: str) -> dict:
        prompt = (
            f"Create concise revision notes for {topic} ({subject}).\n"
            f"Based on: {expl[:400]}\n"
            'Return ONLY JSON: {"key_points":["..."],"common_mistakes":["..."],'
            '"remember":"...","quick_revision_time":"5 minutes"}'
        )
        try:
            raw = ask_gemini(prompt).strip()
            clean = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            s_idx = clean.find("{")
            e_idx = clean.rfind("}") + 1
            if s_idx != -1 and e_idx > s_idx:
                return json.loads(clean[s_idx:e_idx])
        except Exception:
            pass
        return {
            "key_points": [f"{topic} — core concepts", "Practice examples", "Review formulas"],
            "common_mistakes": ["Skipping prerequisites", "Not practising enough"],
            "remember": f"Understand {topic} through examples first, then theory.",
            "quick_revision_time": "5 minutes",
        }

    # ── extract topic + subject ───────────────────────────────────────────────

    topic = msg
    subject = ""

    for prefix in ("explain ", "learn ", "teach me ", "diagram ", "visualize ",
                   "show me ", "mcq ", "quiz me on ", "video "):
        if lower.startswith(prefix):
            topic = msg[len(prefix):].strip()
            break

    # Infer subject from active task first, then subjects list
    if s.active_task_id:
        for t in s.tasks:
            if t.get("id") == s.active_task_id:
                subject = t.get("subject", "")
                if not topic or topic == msg:
                    topic = t.get("topic") or topic
                break

    if not subject and s.subjects:
        subject = s.subjects[0]["name"]

    if not topic:
        s.agent_response = "📚 What topic would you like to learn? (e.g. 'teach me CPU Scheduling')"
        s.history.append({"role": "assistant", "content": s.agent_response})
        return s.model_dump()

    # ── generate multi-modal content ──────────────────────────────────────────

    expl    = _explanation(topic, subject, s.learning_style or "mixed")
    funny   = _analogy(topic, subject)
    diagram = _svg(topic, subject)
    vids    = _videos(topic, subject)
    mcq_list = _mcqs(topic, subject)
    notes   = _revision_notes(topic, subject, expl)

    # Save revision notes to db
    already = any(
        n.get("topic") == topic and n.get("subject") == subject
        for n in s.revision_notes_db
    )
    if not already:
        s.revision_notes_db.append({
            "topic": topic, "subject": subject,
            "created_at": datetime.now().isoformat(),
            **notes,
        })

    s.learner_output = {
        "topic": topic, "subject": subject,
        "explanation": expl, "funny_analogy": funny,
        "svg": diagram, "videos": vids,
        "mcqs": mcq_list, "revision_notes": notes,
        "generated_at": datetime.now().isoformat(),
    }

    s.agent_response = (
        f"🎓 **{topic}** ({subject})\n\n"
        f"{expl}\n\n"
        f"😂 **Remember this:**\n{funny}\n\n"
        f"📊 Visual diagram: [attached]\n\n"
        f"🎥 Video suggestions:\n"
        + "\n".join(f"  • {v}" for v in vids) +
        f"\n\n✅ {len(mcq_list)} practice MCQs attached\n"
        f"📝 Revision notes saved\n\n"
        f"Type 'next' to return to your schedule, or ask another topic."
    )

    # ── handle return handoff (research → learner → research) ────────────────
    if s.return_to_agent == "research":
        s.agent_response += (
            f"\n\n🔁 When you're ready, type 'continue research' to return to your project."
        )

    s.history.append({"role": "user", "content": s.user_message})
    s.history.append({"role": "assistant", "content": s.agent_response})
    print(f"[Learner] '{topic}' ({subject}) → {len(s.agent_response)} chars")
    return s.model_dump()
