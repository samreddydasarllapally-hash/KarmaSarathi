"""
Engagement Monitor
------------------
Tracks student engagement, confusion, frustration and confidence using
rule-based signals.  The LLM is invoked ONLY when free-text sentiment
needs classification — never for routine metric updates.

Emits a EngagementSnapshot that the Teaching Engine uses to adapt its
next prompt to Claude/Gemini.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import re


# ─── snapshot returned to the teaching engine ───────────────────────────────

@dataclass
class EngagementSnapshot:
    engagement_pct:   float = 80.0   # 0-100  how engaged
    confusion_pct:    float = 0.0    # 0-100  accumulated confusion
    frustration_pct:  float = 0.0    # 0-100  accumulated frustration
    confidence_pct:   float = 60.0   # 0-100  self-assessed confidence
    attention_pct:    float = 85.0   # 0-100  proxy from response time
    sentiment:        str   = "neutral"   # positive / neutral / negative
    recommended_style: str  = "continue"  # see _decide_style()
    intervention_needed: bool = False

    def to_dict(self) -> dict:
        return {
            "engagement":   round(self.engagement_pct),
            "confusion":    round(self.confusion_pct),
            "frustration":  round(self.frustration_pct),
            "confidence":   round(self.confidence_pct),
            "attention":    round(self.attention_pct),
            "sentiment":    self.sentiment,
            "style":        self.recommended_style,
            "intervention": self.intervention_needed,
        }


# ─── main monitor ────────────────────────────────────────────────────────────

class EngagementMonitor:
    """
    Lightweight engagement tracker.

    Usage:
        monitor = EngagementMonitor(llm)       # llm only used for sentiment
        monitor.record_interaction(user_text, quiz_score, response_time_sec)
        snapshot = monitor.snapshot()
        prompt  = monitor.enrich_prompt(base_prompt, snapshot, topic)
    """

    # ── rule-based signals ───────────────────────────────────────────────────

    _CONFUSION_PHRASES = {
        "don't understand": 10, "dont understand": 10,
        "still confused":   12, "not clear":        8,
        "explain again":    8,  "one more time":    6,
        "doesn't make sense": 10, "lost":            7,
        "what do you mean":  6, "not getting it":   9,
        "i have no idea":   12, "totally lost":     14,
    }

    _FRUSTRATION_PHRASES = {
        "i've asked":        12, "ive asked":        12,
        "asked this":        12, "asked again":      12,
        "same question":     10, "again and again":  14,
        "still don't":       10, "told you":          8,
        "this is useless":   15, "hate this":        12,
        "makes no sense":    10, "so hard":           6,
        "i give up":         18, "forget it":        14,
    }

    _CONFIDENCE_POSITIVE = {
        "i understand": +8,  "got it":      +8,
        "makes sense":  +6,  "i see":       +5,
        "clear now":    +7,  "i think i":   +3,
        "exactly":      +5,  "yes":         +2,
    }

    _CONFIDENCE_NEGATIVE = {
        "not sure":     -5,  "maybe":       -3,
        "i guess":      -4,  "probably":    -3,
        "i don't know": -8,  "not confident": -7,
    }

    def __init__(self, llm=None):
        self.llm = llm          # optional; only used for sentiment when needed
        self._confusion    = 0.0
        self._frustration  = 0.0
        self._confidence   = 60.0
        self._interactions = 0
        self._quick_answers = 0   # proxy for low attention
        self._last_quiz_score: Optional[float] = None
        self._history: list[dict] = []

    # ── public API ───────────────────────────────────────────────────────────

    def record_interaction(
        self,
        user_text: str,
        quiz_score: Optional[float] = None,   # 0-100
        response_time_sec: Optional[float] = None,
        wrong_answers: int = 0,
    ):
        """Call after every student message."""
        text = user_text.lower()
        self._interactions += 1

        # Confusion signals
        for phrase, weight in self._CONFUSION_PHRASES.items():
            if phrase in text:
                self._confusion = min(100, self._confusion + weight)

        # Frustration signals
        for phrase, weight in self._FRUSTRATION_PHRASES.items():
            if phrase in text:
                self._frustration = min(100, self._frustration + weight)

        # Confidence signals
        for phrase, delta in self._CONFIDENCE_POSITIVE.items():
            if phrase in text:
                self._confidence = min(100, self._confidence + delta)
        for phrase, delta in self._CONFIDENCE_NEGATIVE.items():
            if phrase in text:
                self._confidence = max(0, self._confidence + delta)

        # Wrong answers tank confidence
        self._confidence = max(0, self._confidence - wrong_answers * 5)

        # Quiz score updates last_quiz_score and confidence
        if quiz_score is not None:
            self._last_quiz_score = quiz_score
            if quiz_score >= 80:
                self._confidence = min(100, self._confidence + 8)
                self._confusion  = max(0,   self._confusion  - 10)
            elif quiz_score < 50:
                self._confidence = max(0, self._confidence - 8)
                self._confusion  = min(100, self._confusion + 6)

        # Short responses may indicate low attention
        if response_time_sec is not None and response_time_sec < 5:
            self._quick_answers += 1

        self._history.append({
            "text": user_text[:120],
            "confusion": self._confusion,
            "frustration": self._frustration,
            "confidence": self._confidence,
            "ts": datetime.now().isoformat(),
        })

    def snapshot(self) -> EngagementSnapshot:
        """Return current engagement snapshot."""
        attention = max(20, 100 - self._quick_answers * 10)
        engagement = max(0, 100 - self._confusion * 0.4 - self._frustration * 0.4)
        sentiment = self._rule_sentiment()

        snap = EngagementSnapshot(
            engagement_pct   = round(engagement, 1),
            confusion_pct    = round(self._confusion, 1),
            frustration_pct  = round(self._frustration, 1),
            confidence_pct   = round(self._confidence, 1),
            attention_pct    = round(attention, 1),
            sentiment        = sentiment,
            recommended_style = self._decide_style(engagement, self._confusion, self._frustration),
            intervention_needed = self._frustration >= 40 or self._confusion >= 60,
        )
        return snap

    def classify_sentiment_llm(self, user_text: str) -> str:
        """
        LLM sentiment classification — called ONLY for ambiguous free-text.
        Returns: 'positive' | 'neutral' | 'negative'
        """
        if not self.llm:
            return self._rule_sentiment()
        prompt = (
            f"Classify the sentiment of this student message in ONE word "
            f"(positive/neutral/negative):\n\"{user_text}\"\n\nReply only with the word."
        )
        try:
            result = self.llm.invoke(prompt).content.strip().lower()
            if result in ("positive", "neutral", "negative"):
                return result
        except Exception:
            pass
        return self._rule_sentiment()

    def enrich_prompt(self, base_prompt: str, snapshot: EngagementSnapshot,
                      topic: str, used_analogies: list[str] | None = None) -> str:
        """
        Inject student state into a teaching prompt so Claude/Gemini
        adapts its explanation style automatically.
        """
        ctx_lines = [
            f"[Student Profile for this response]",
            f"Topic: {topic}",
            f"Confusion: {snapshot.confusion_pct:.0f}%",
            f"Frustration: {snapshot.frustration_pct:.0f}%",
            f"Confidence: {snapshot.confidence_pct:.0f}%",
            f"Engagement: {snapshot.engagement_pct:.0f}%",
            f"Sentiment: {snapshot.sentiment}",
            f"Teaching style: {snapshot.recommended_style}",
        ]
        if used_analogies:
            ctx_lines.append(f"Previously used analogies: {', '.join(used_analogies)} — do NOT repeat them.")
        if snapshot.intervention_needed:
            ctx_lines.append(
                "IMPORTANT: Student is frustrated or heavily confused. "
                "Begin with genuine empathy. Forget formulas for now — "
                "build intuition first with a fresh real-world analogy."
            )
        if snapshot.recommended_style == "visual":
            ctx_lines.append("Generate an SVG diagram alongside the explanation.")
        elif snapshot.recommended_style == "challenge":
            ctx_lines.append("Student is confident — include an interview-level or edge-case question.")
        elif snapshot.recommended_style == "simplify":
            ctx_lines.append("Simplify language. One concept at a time. Max 3 sentences per idea.")

        context_block = "\n".join(ctx_lines)
        return f"{context_block}\n\n{base_prompt}"

    # ── private helpers ──────────────────────────────────────────────────────

    def _rule_sentiment(self) -> str:
        if self._frustration >= 25 or self._confusion >= 40:
            return "negative"
        if self._confidence >= 70 and self._confusion < 20:
            return "positive"
        return "neutral"

    def _decide_style(self, engagement: float, confusion: float, frustration: float) -> str:
        if frustration >= 40 or confusion >= 60:
            return "empathy_reset"    # start over with fresh analogy + empathy
        if confusion >= 30:
            return "simplify"         # smaller chunks, plain language
        if confusion >= 15:
            return "visual"           # add SVG diagram
        if engagement >= 80 and confusion < 10:
            return "challenge"        # confidence high → go deeper
        return "continue"             # steady state
