"""
Conversational Teacher - Makes teaching feel like talking to a mentor

Key principles:
- Empathy first ("No worries!")
- Real-life analogies (forget the jargon)
- Counter questions (Socratic method)
- Conversational tone (not robotic)
"""

from typing import Dict, Any, List
import random


class ConversationalTeacher:
    """Transforms explanations into natural mentor-like conversations"""
    
    def __init__(self, llm):
        self.llm = llm
        self.empathy_responses = [
            "No worries at all!",
            "That's totally okay—this concept trips up a lot of students.",
            "Let me break it down differently.",
            "I've got a way to make this click for you.",
            "Great question! Let me explain that better.",
            "Ah, I see where the confusion is. Let me clarify."
        ]
    
    def generate_conversational_explanation(
        self,
        topic: str,
        student_input: str,
        confusion_score: int,
        layer: int,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate explanation in conversational mentor style
        
        Args:
            topic: What we're teaching
            student_input: What student said
            confusion_score: How confused they are (0-10)
            layer: Current teaching layer
            context: Additional context
        
        Returns:
            Conversational explanation
        """
        
        # Start with empathy
        empathy = self._generate_empathy(student_input, confusion_score)
        
        # Detect what student is confused about
        confusion_area = self._detect_confusion_area(student_input, topic)
        
        # Generate conversational explanation
        if confusion_score >= 5:
            # High confusion: completely different approach
            return self._generate_reset_explanation(topic, empathy, confusion_area, context)
        elif confusion_score >= 3:
            # Medium confusion: new analogy
            return self._generate_new_analogy(topic, empathy, confusion_area, context)
        else:
            # Low confusion: clarify specific point
            return self._generate_clarification(topic, empathy, confusion_area, context)
    
    def _generate_empathy(self, student_input: str, confusion_score: int) -> str:
        """Generate empathetic opening"""
        
        input_lower = student_input.lower()
        
        if "don't understand" in input_lower or "confused" in input_lower:
            return random.choice([
                "No worries at all! ",
                "That's completely okay! ",
                "Let me explain that differently. "
            ])
        elif "still" in input_lower or "again" in input_lower:
            return random.choice([
                "I hear you. Let me try a completely different angle. ",
                "Got it. Let me break this down a new way. ",
                "Okay, let's approach this from scratch. "
            ])
        elif confusion_score >= 5:
            return "I can see this isn't clicking yet. Let me reset and try again. "
        else:
            return random.choice(self.empathy_responses) + " "
    
    def _detect_confusion_area(self, student_input: str, topic: str) -> str:
        """Detect what specific part is confusing"""
        
        prompt = f"""Student is learning about {topic}.
They said: "{student_input}"

What specific aspect are they confused about? Return one phrase.
Examples: "the formula", "how it works", "the example", "the concept itself"

Return only the confusion area, nothing else."""

        response = self.llm.invoke(prompt).content.strip()
        return response.lower()
    
    def _generate_reset_explanation(
        self,
        topic: str,
        empathy: str,
        confusion_area: str,
        context: Dict[str, Any]
    ) -> str:
        """
        High confusion: completely reset and use different approach
        """
        
        prompt = f"""{empathy}

Let me explain {topic} in a completely fresh way. Forget everything technical for a moment.

Student is confused about: {confusion_area}

Rules:
1. Start with "Let's forget [subject] for a second."
2. Use a simple, everyday analogy (coffee shop, movie theater, etc.)
3. Ask a guiding question to check understanding
4. Keep it conversational, like talking to a friend
5. NO jargon, NO technical terms in the analogy
6. Maximum 4-5 sentences

Generate the explanation:"""

        explanation = self.llm.invoke(prompt).content
        
        return f"{empathy}\n\n{explanation}"
    
    def _generate_new_analogy(
        self,
        topic: str,
        empathy: str,
        confusion_area: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Medium confusion: new analogy/example
        """
        
        prompt = f"""{empathy}

Student is learning {topic} but confused about: {confusion_area}

Generate a NEW analogy they haven't heard yet. Make it:
1. Relatable (everyday life: restaurants, traffic, shopping, etc.)
2. Visual (they can picture it)
3. Interactive (pose a question at the end)
4. Conversational tone

Keep it short (3-4 sentences) and end with a question.

Generate:"""

        explanation = self.llm.invoke(prompt).content
        
        return f"{empathy}\n\n{explanation}"
    
    def _generate_clarification(
        self,
        topic: str,
        empathy: str,
        confusion_area: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Low confusion: just clarify the specific point
        """
        
        prompt = f"""{empathy}

Student understands most of {topic} but needs clarification on: {confusion_area}

Provide a quick, conversational clarification:
1. Acknowledge what they already understand
2. Clarify the specific confusing point
3. Give a micro-example
4. Ask if it makes sense now

Keep it brief (2-3 sentences).

Generate:"""

        explanation = self.llm.invoke(prompt).content
        
        return f"{empathy}\n\n{explanation}"
    
    def generate_counter_question(self, topic: str, context: Dict[str, Any]) -> str:
        """
        Generate Socratic counter-question instead of direct answer
        Use when confusion is high - make student think
        """
        
        prompt = f"""Student is learning {topic}.

Instead of explaining directly, ask them a guiding question that will help them discover the answer themselves.

The question should:
1. Be simple and concrete
2. Connect to something they already know
3. Lead them toward the insight
4. Be answerable with common sense

Examples:
- "What happens when you're standing in a queue and someone cuts in line?"
- "If you had 3 tasks to do and one takes an hour while the others take 5 minutes, which would you do first?"

Generate one guiding question for {topic}:"""

        question = self.llm.invoke(prompt).content.strip()
        
        return question
    
    def generate_hint_sequence(self, topic: str, layer: int) -> List[str]:
        """
        Generate sequence of progressive hints
        Use when student is stuck on a problem
        """
        
        prompt = f"""Generate 3 progressive hints for understanding {topic}:

Hint 1 (gentle nudge): Point them in right direction without giving answer
Hint 2 (clearer): Give them half the answer, let them complete it  
Hint 3 (almost there): Give them everything except the final connection

Format:
1. [hint 1]
2. [hint 2]
3. [hint 3]

Generate:"""

        response = self.llm.invoke(prompt).content
        
        # Parse hints
        hints = []
        for line in response.split('\n'):
            if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith('-')):
                hint = line.strip().lstrip('123.-) ')
                if hint:
                    hints.append(hint)
        
        return hints[:3]
    
    def celebrate_understanding(self, student_response: str) -> str:
        """
        Celebrate when student gets it
        Make it feel rewarding
        """
        
        celebrations = [
            "Exactly! You've got it! 🎯",
            "Yes! That's perfect! 💡",
            "Bingo! You nailed it! ⭐",
            "That's it! You understand! 🎉",
            "Brilliant! You've figured it out! 🌟",
            "Perfect! Now it's clicked! 💯"
        ]
        
        return random.choice(celebrations)
    
    def generate_follow_up_question(self, topic: str, student_got_it: bool) -> str:
        """
        Generate natural follow-up question to keep conversation flowing
        """
        
        if student_got_it:
            prompt = f"""Student just understood {topic}. Generate a natural follow-up question to:
1. Solidify their understanding
2. Connect to next concept
3. Keep conversation flowing

Examples:
- "Now, can you think of any problems with this approach?"
- "Want to see this in action with an example?"
- "Can you think of where this might be useful?"

Generate one conversational follow-up:"""
        else:
            prompt = f"""Student is still working on {topic}. Generate a encouraging follow-up:

Examples:
- "Want to try thinking about it this way?"
- "Should I show you a visual diagram?"
- "Would an example help?"

Generate one supportive follow-up:"""
        
        question = self.llm.invoke(prompt).content.strip()
        
        return question
    
    def adapt_explanation_style(
        self,
        student_history: List[str],
        confusion_patterns: Dict[str, int]
    ) -> str:
        """
        Analyze what works for this student and adapt
        
        Returns: preferred style (analogy, example, visual, socratic)
        """
        
        # Count what's been tried
        tried_approaches = {
            "analogy": 0,
            "example": 0,
            "visual": 0,
            "socratic": 0
        }
        
        for utterance in student_history:
            if "analogy" in utterance or "like" in utterance:
                tried_approaches["analogy"] += 1
            elif "example" in utterance or "show" in utterance:
                tried_approaches["example"] += 1
            elif "diagram" in utterance or "picture" in utterance:
                tried_approaches["visual"] += 1
            elif "question" in utterance or "?" in utterance:
                tried_approaches["socratic"] += 1
        
        # Find least tried approach
        min_tried = min(tried_approaches.values())
        untried = [k for k, v in tried_approaches.items() if v == min_tried]
        
        return random.choice(untried) if untried else "analogy"
    
    def make_conversational(self, technical_explanation: str) -> str:
        """
        Transform technical explanation into conversational style
        """
        
        prompt = f"""Transform this technical explanation into a conversational, mentor-like explanation:

{technical_explanation}

Rules:
1. Use "you" and "your" (not "the student")
2. Add conversational phrases ("you see", "here's the thing", "check this out")
3. Break long sentences into shorter ones
4. Replace jargon with simple words
5. Add guiding questions
6. Keep the same information, just more natural

Generate conversational version:"""

        conversational = self.llm.invoke(prompt).content
        
        return conversational
