"""
Resource Generator for Learner Agent
Generates dynamic educational resources: SVGs, flashcards, practice problems, summaries.

Refinements added:
  R1 — SVG validation + auto-repair (LLM fallback with stricter prompt)
  R3 — Diagram history cache (reuse SVGs instead of regenerating every time)
"""

import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional


# ── SVG validator / repairer ─────────────────────────────────────────────────

def _validate_svg(raw: str) -> tuple[bool, str]:
    """
    Returns (is_valid, cleaned_svg).
    Strips markdown fences, ensures the string starts with <svg or <?xml.
    Does NOT import a full XML parser — keeps the dependency list zero.
    """
    text = raw.strip()

    # Strip markdown code fences
    text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip()

    # Must start with <svg or <?xml
    if not (text.lower().startswith("<svg") or text.lower().startswith("<?xml")):
        return False, text

    # Must contain a closing </svg>
    if "</svg>" not in text.lower():
        return False, text

    # Basic attribute sanity: width/height present
    has_width  = "width=" in text
    has_height = "height=" in text
    if not (has_width and has_height):
        # Inject minimal defaults before the first >
        text = text.replace("<svg", '<svg width="600" height="400"', 1)

    return True, text


def _repair_svg(llm, concept: str, bad_svg: str) -> str:
    """
    Ask the LLM to fix a broken SVG.
    Uses a much stricter prompt that has historically fewer hallucinations.
    """
    prompt = (
        f"The following SVG code is malformed or incomplete. "
        f"Fix it so it is valid SVG that renders correctly in a browser. "
        f"Topic: {concept}. "
        f"Return ONLY the corrected SVG code, nothing else — "
        f"no markdown, no explanation, no extra text.\n\n"
        f"Broken SVG:\n{bad_svg[:2000]}"
    )
    fixed = llm.invoke(prompt).content.strip()
    _, cleaned = _validate_svg(fixed)
    return cleaned


# ── main class ────────────────────────────────────────────────────────────────

class ResourceGenerator:
    """Generates educational resources dynamically based on learning context."""

    def __init__(self, llm):
        self.llm = llm
        # R3: in-memory diagram cache  {cache_key: svg_string}
        self._svg_cache: Dict[str, str] = {}

    # ── SVG generation ────────────────────────────────────────────────────────

    def generate_svg_diagram(self, concept: str, learning_unit: str,
                             context: Dict[str, Any]) -> str:
        """Generate (or retrieve from cache) an SVG diagram."""
        layer_label = context.get("current_layer", "basic")
        cache_key   = f"{concept}|{learning_unit}|{layer_label}"

        # R3: return cached diagram if available
        if cache_key in self._svg_cache:
            return self._svg_cache[cache_key]

        prompt = (
            f"Generate a clear, labeled educational SVG diagram for: {concept}\n"
            f"Learning Unit: {learning_unit}\n"
            f"Detail level: {layer_label}\n\n"
            f"Requirements:\n"
            f"- Valid SVG with width=\"600\" height=\"400\"\n"
            f"- Simple filled shapes (rect, circle, ellipse)\n"
            f"- Text labels on each shape\n"
            f"- Arrows (lines with marker-end) showing flow\n"
            f"- Colours: use fill=\"#4A90D9\" for boxes, fill=\"#F5A623\" for key items\n"
            f"- A <title> element describing the diagram\n\n"
            f"Return ONLY the complete SVG code — no markdown, no explanation."
        )

        raw = self.llm.invoke(prompt).content
        valid, svg = _validate_svg(raw)

        if not valid:
            # R1: attempt repair with a stricter prompt
            svg = _repair_svg(self.llm, concept, raw)

        # R3: store in cache
        self._svg_cache[cache_key] = svg
        return svg

    def generate_interactive_svg(self, concept: str, learning_unit: str,
                                  layer: int = 1) -> str:
        """Layer-aware SVG — delegates to generate_svg_diagram."""
        depth = {
            1: "intuitive overview",
            2: "structured component diagram",
            3: "advanced flow with edge cases"
        }
        ctx = {"current_layer": depth.get(layer, "basic")}
        return self.generate_svg_diagram(concept, learning_unit, ctx)

    def get_cached_diagrams(self) -> Dict[str, Any]:
        """Return all cached diagrams with metadata — used by diagram history view."""
        return {
            key: {"svg_chars": len(svg), "cache_key": key}
            for key, svg in self._svg_cache.items()
        }

    # ── Flashcards ────────────────────────────────────────────────────────────

    def generate_flashcards(self, learning_unit: str, concepts: List[str],
                             difficulty: str = "medium") -> List[Dict[str, str]]:
        """Generate flashcards for concept review."""
        prompt = (
            f"Create 5 flashcards for: {learning_unit}\n"
            f"Key concepts: {', '.join(concepts) if concepts else learning_unit}\n"
            f"Difficulty: {difficulty}\n\n"
            f"Format each as:\nQ: [question]\nA: [answer]\n\n"
            f"Make questions test understanding, not memorization."
        )
        response   = self.llm.invoke(prompt).content
        flashcards = []
        for pair in response.strip().split("\n\n"):
            lines = pair.strip().split("\n")
            if len(lines) >= 2:
                q = lines[0].replace("Q:", "").strip()
                a = lines[1].replace("A:", "").strip()
                if q and a:
                    flashcards.append({"question": q, "answer": a})
        return flashcards

    # ── Practice problems ─────────────────────────────────────────────────────

    def generate_practice_problems(self, learning_unit: str, difficulty: str,
                                    count: int = 3) -> List[Dict[str, Any]]:
        """Generate practice problems with solutions."""
        prompt = (
            f"Create {count} practice problems for: {learning_unit}\n"
            f"Difficulty: {difficulty}\n\n"
            f"For each problem provide:\n"
            f"PROBLEM: [clear problem statement]\n"
            f"SOLUTION: [step-by-step solution]\n"
            f"KEY_CONCEPTS: [concepts tested]\n\n"
            f"Separate each problem with ---"
        )
        response = self.llm.invoke(prompt).content
        problems = []
        for section in response.strip().split("---"):
            if "PROBLEM:" not in section:
                continue
            problem_text = solution_text = ""
            concepts: List[str] = []
            current = None
            for line in section.strip().split("\n"):
                if line.startswith("PROBLEM:"):
                    current      = "problem"
                    problem_text = line.replace("PROBLEM:", "").strip()
                elif line.startswith("SOLUTION:"):
                    current       = "solution"
                    solution_text = line.replace("SOLUTION:", "").strip()
                elif line.startswith("KEY_CONCEPTS:"):
                    concepts = [c.strip() for c in
                                line.replace("KEY_CONCEPTS:", "").split(",")]
                elif current == "problem" and line.strip():
                    problem_text  += "\n" + line
                elif current == "solution" and line.strip():
                    solution_text += "\n" + line
            if problem_text:
                problems.append({
                    "problem":         problem_text.strip(),
                    "solution":        solution_text.strip(),
                    "concepts_tested": concepts,
                    "difficulty":      difficulty
                })
        return problems

    # ── Summary ───────────────────────────────────────────────────────────────

    def generate_summary(self, learning_unit: str, layer: int,
                          content_covered: List[str]) -> str:
        """Generate concise summary of what was learned."""
        layer_name = {0: "prerequisite", 1: "intuitive",
                      2: "structured", 3: "advanced"}.get(layer, "basic")
        prompt = (
            f"Create a concise summary of: {learning_unit}\n"
            f"Level: {layer_name}\n"
            f"Topics covered: {', '.join(content_covered) if content_covered else learning_unit}\n\n"
            f"Format:\n"
            f"KEY POINTS:\n- [3-5 essential points]\n\n"
            f"YOU NOW UNDERSTAND:\n- [what student can now do/explain]\n\n"
            f"Keep it brief, clear, and encouraging."
        )
        return self.llm.invoke(prompt).content.strip()

    # ── Analogy ───────────────────────────────────────────────────────────────

    def generate_analogy(self, concept: str,
                          student_profile: Dict[str, Any]) -> str:
        """Generate a personalized analogy."""
        interests = student_profile.get("interests", [])
        age_group = student_profile.get("age_group", "general")
        prompt = (
            f"Create a simple, relatable analogy to explain: {concept}\n"
            f"Student interests: {', '.join(interests) if interests else 'general'}\n"
            f"Age group: {age_group}\n\n"
            f"Make it:\n- 2-3 sentences\n- Everyday examples\n"
            f"- Easy to visualize\n- Accurate\n\n"
            f"Return only the analogy, no extra text."
        )
        return self.llm.invoke(prompt).content.strip()

    # ── Concept map ───────────────────────────────────────────────────────────

    def generate_concept_map(self, learning_unit: str,
                              related_concepts: List[str]) -> Dict[str, Any]:
        """Generate concept relationship map."""
        prompt = (
            f"Create a concept map for: {learning_unit}\n"
            f"Related concepts: {', '.join(related_concepts)}\n\n"
            f"Return ONLY valid JSON:\n"
            f'{{"central_concept": "...", "relationships": '
            f'[{{"from": "c1", "to": "c2", "type": "requires/leads_to/part_of"}}]}}'
        )
        response = self.llm.invoke(prompt).content
        try:
            s = response.find("{")
            e = response.rfind("}") + 1
            if s >= 0 and e > s:
                return json.loads(response[s:e])
        except Exception:
            pass
        return {"central_concept": learning_unit, "relationships": []}

    # ── Decision helpers ──────────────────────────────────────────────────────

    def should_generate_svg(self, confusion_score: int, attempts: int) -> bool:
        return confusion_score >= 3 or attempts >= 2

    def should_generate_flashcards(self, mastery_level: float) -> bool:
        return mastery_level >= 0.6

    def should_generate_practice(self, layer: int,
                                  understanding_score: float) -> bool:
        return layer >= 2 and understanding_score >= 0.5
