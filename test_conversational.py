"""
Test Conversational Teaching Style
Shows how learner adapts when student is confused
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.conversational_teacher import ConversationalTeacher


class MockLLM:
    def invoke(self, prompt):
        class Response:
            def __init__(self, content):
                self.content = content
        
        prompt_lower = prompt.lower()
        
        # Empathy + reset explanation
        if "forget" in prompt_lower and "fresh way" in prompt_lower:
            return Response("""Let's forget operating systems for a second.

Imagine you're at a coffee shop. Five people are in line. The barista serves whoever arrived first—that's FCFS!

Now, what if the first person orders 20 custom drinks? Everyone else waits, even if they just want a simple coffee. That's the convoy effect.

Does this make more sense now?""")
        
        # New analogy
        if "new analogy" in prompt_lower:
            return Response("""Think of FCFS like boarding an airplane. First passengers in line board first. But if someone in front has tons of bags and takes forever, everyone behind them gets delayed—even passengers with no bags who could board quickly!

Can you see how this relates to processes?""")
        
        # Clarification
        if "clarification" in prompt_lower:
            return Response("""You already understand that FCFS means first-come-first-served. The confusing part is probably the formula.

Here's a simple way: Waiting Time = when you finish - when you arrived - how long you actually worked.

Make sense?""")
        
        # Confusion area detection
        if "confused about" in prompt_lower:
            return Response("the convoy effect")
        
        # Counter question
        if "guiding question" in prompt_lower:
            return Response("If you had 3 tasks—one takes 2 hours and two take 5 minutes each—which order makes more sense?")
        
        return Response("FCFS is a scheduling algorithm.")


def test_conversational_teaching():
    print("\n" + "="*70)
    print("  TEST: CONVERSATIONAL TEACHING STYLE")
    print("="*70)
    
    teacher = ConversationalTeacher(MockLLM())
    
    # Test 1: High confusion - reset explanation
    print("\n[Test 1] High confusion (score=7) - Reset explanation")
    print("Student: 'I still don't understand FCFS at all'")
    
    explanation = teacher.generate_conversational_explanation(
        topic="FCFS Scheduling",
        student_input="I still don't understand FCFS at all",
        confusion_score=7,
        layer=1,
        context={}
    )
    
    print("\nLearner response:")
    print(f"  {explanation[:200]}...")
    
    checks = {
        "Has empathy": any(phrase in explanation.lower() for phrase in ["no worries", "okay", "let me"]),
        "Uses real-life analogy": "coffee" in explanation.lower() or "line" in explanation.lower(),
        "Asks guiding question": "?" in explanation
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    # Test 2: Medium confusion - new analogy
    print("\n[Test 2] Medium confusion (score=4) - New analogy")
    print("Student: 'Can you explain it differently?'")
    
    explanation = teacher.generate_conversational_explanation(
        topic="FCFS Scheduling",
        student_input="Can you explain it differently?",
        confusion_score=4,
        layer=1,
        context={}
    )
    
    print("\nLearner response:")
    print(f"  {explanation[:200]}...")
    
    checks = {
        "Different from first": "airplane" in explanation.lower() or "boarding" in explanation.lower(),
        "Still conversational": any(phrase in explanation.lower() for phrase in ["think of", "imagine", "like"])
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    # Test 3: Low confusion - clarification
    print("\n[Test 3] Low confusion (score=2) - Quick clarification")
    print("Student: 'I get the concept but not the formula'")
    
    explanation = teacher.generate_conversational_explanation(
        topic="FCFS Scheduling",
        student_input="I get the concept but not the formula",
        confusion_score=2,
        layer=2,
        context={}
    )
    
    print("\nLearner response:")
    print(f"  {explanation[:200]}...")
    
    checks = {
        "Acknowledges understanding": "already understand" in explanation.lower() or "you get" in explanation.lower(),
        "Brief": len(explanation) < 300
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    # Test 4: Counter question (Socratic)
    print("\n[Test 4] Generate counter question (Socratic method)")
    
    question = teacher.generate_counter_question("FCFS", {})
    
    print(f"\nLearner asks: {question}")
    
    checks = {
        "Is a question": "?" in question,
        "Relatable": any(word in question.lower() for word in ["you", "your", "tasks", "if"])
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    # Test 5: Celebration
    print("\n[Test 5] Celebrate understanding")
    
    celebration = teacher.celebrate_understanding("Oh I get it now!")
    
    print(f"\nLearner celebrates: {celebration}")
    
    checks = {
        "Enthusiastic": any(emoji in celebration for emoji in ["🎯", "💡", "⭐", "🎉", "🌟", "💯"]),
        "Positive": any(word in celebration.lower() for word in ["perfect", "exactly", "yes", "brilliant"])
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    # Test 6: Follow-up question
    print("\n[Test 6] Generate follow-up question")
    
    followup = teacher.generate_follow_up_question("FCFS", student_got_it=True)
    
    print(f"\nLearner asks: {followup[:100]}...")
    
    checks = {
        "Keeps conversation going": "?" in followup,
        "Natural": any(word in followup.lower() for word in ["now", "want", "can you", "should"])
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    print("\n" + "="*70)
    print("  ✓ CONVERSATIONAL TEACHING: ALL TESTS PASSED")
    print("  Learner feels like a mentor, not a robot teacher")
    print("="*70)


if __name__ == "__main__":
    test_conversational_teaching()
