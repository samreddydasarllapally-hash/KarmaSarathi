"""
Context-Aware Safety Pipeline

Understands educational context before applying content moderation.
Prevents false positives on legitimate academic terms.

Pipeline:
1. Intent Detection (Why is user asking?)
2. Subject Detection (What domain?)
3. Context Classification (Educational vs inappropriate?)
4. Safety Check (Final validation)
"""

from typing import Literal, Optional
import re


# Educational domains where sensitive terminology is legitimate
EDUCATIONAL_DOMAINS = {
    "biology": ["reproduction", "anatomy", "physiology", "genetics", "zoology"],
    "medicine": ["anatomy", "surgery", "pathology", "gynecology", "urology"],
    "psychology": ["behavior", "mental health", "sexuality", "trauma"],
    "nursing": ["patient care", "anatomy", "pharmacology"],
    "pharmacy": ["drugs", "medications", "pharmacology"],
    "veterinary": ["animal anatomy", "mating", "reproduction"],
    "cybersecurity": ["hacking", "injection", "exploitation", "vulnerabilities"],
    "criminal_law": ["assault", "violence", "weapons", "crime"],
    "forensics": ["autopsy", "death", "crime scene", "weapons"],
    "sociology": ["gender", "sexuality", "discrimination", "violence"],
    "chemistry": ["explosives", "chemicals", "reactions"],
    "botany": ["reproduction", "pollination", "fertilization"],
}

# Educational intent keywords
LEARNING_INTENTS = [
    "teach", "explain", "learn", "study", "understand", "help me understand",
    "what is", "how does", "why", "define", "describe", "elaborate",
    "give notes", "quiz me", "test me", "practice", "solve", "show example",
    "diagram", "visualize", "summarize", "revision", "clarify"
]

# Subject indicators
SUBJECT_INDICATORS = {
    "biology": ["cell", "organ", "tissue", "species", "anatomy", "physiology", "reproduction", "genetics"],
    "medicine": ["patient", "diagnosis", "treatment", "surgery", "disease", "medical", "clinical"],
    "chemistry": ["molecule", "atom", "reaction", "compound", "element", "formula"],
    "physics": ["force", "energy", "motion", "quantum", "wave", "particle"],
    "computer_science": ["algorithm", "code", "program", "database", "network"],
    "cybersecurity": ["security", "encryption", "vulnerability", "attack", "exploit", "sql injection"],
    "law": ["legal", "statute", "criminal", "civil", "court", "justice"],
}

# Sensitive terms that are VALID in educational contexts
EDUCATIONAL_SENSITIVE_TERMS = {
    # Biology/Medicine
    "reproductive_system", "genital", "penis", "vagina", "breast", "sperm", "ovum",
    "fertilization", "menstruation", "puberty", "sex determination", "mating",
    "sexual reproduction", "gametes", "testosterone", "estrogen",
    
    # Cybersecurity
    "sql injection", "xss", "exploit", "vulnerability", "hack", "attack",
    "penetration testing", "backdoor", "malware", "virus",
    
    # Criminal Law/Forensics
    "murder", "assault", "weapon", "autopsy", "death", "crime scene",
    
    # Chemistry
    "explosive", "combustion", "oxidation", "acid", "toxic",
}


class ContextAnalyzer:
    """Analyzes context to determine if content is educational."""
    
    def __init__(self, llm=None):
        """Initialize with optional LLM for advanced analysis."""
        self.llm = llm
    
    def detect_intent(self, message: str) -> Literal["learning", "entertainment", "harmful", "unclear"]:
        """Detect user's intent."""
        message_lower = message.lower()
        
        # Check for learning intent
        if any(keyword in message_lower for keyword in LEARNING_INTENTS):
            return "learning"
        
        # Check for harmful intent (red flags)
        harmful_patterns = [
            r"how to (build|make|create) (bomb|weapon|explosive)",
            r"how to (hack|break into|steal|scam)",
            r"how to (hurt|harm|kill|injure)",
            r"(illegal|unethical) (activity|method|way)",
        ]
        
        for pattern in harmful_patterns:
            if re.search(pattern, message_lower):
                return "harmful"
        
        # Check for entertainment/inappropriate
        entertainment_keywords = ["joke", "funny", "meme", "prank", "entertainment"]
        if any(keyword in message_lower for keyword in entertainment_keywords):
            return "entertainment"
        
        return "unclear"
    
    def detect_subject(self, message: str) -> Optional[str]:
        """Detect subject/domain from message."""
        message_lower = message.lower()
        
        scores = {}
        for subject, indicators in SUBJECT_INDICATORS.items():
            score = sum(1 for indicator in indicators if indicator in message_lower)
            if score > 0:
                scores[subject] = score
        
        if not scores:
            return None
        
        # Return subject with highest score
        return max(scores, key=scores.get)
    
    def classify_context(self, message: str, intent: str, subject: Optional[str]) -> dict:
        """Classify the overall context."""
        message_lower = message.lower()
        
        # If learning intent + educational subject, it's educational
        is_educational = (
            intent == "learning" and 
            subject in EDUCATIONAL_DOMAINS
        )
        
        # Check for sensitive but valid educational terms
        contains_sensitive_educational = any(
            term in message_lower for term in EDUCATIONAL_SENSITIVE_TERMS
        )
        
        return {
            "is_educational": is_educational,
            "subject": subject,
            "intent": intent,
            "contains_sensitive_terms": contains_sensitive_educational,
            "risk_level": "low" if is_educational else "medium" if intent == "unclear" else "high",
        }
    
    def is_safe_for_education(self, context: dict) -> tuple[bool, Optional[str]]:
        """Final safety check with context awareness."""
        
        # Educational context with sensitive terms = SAFE
        if context["is_educational"] and context["contains_sensitive_terms"]:
            return True, f"Educational context detected: {context['subject']}"
        
        # Learning intent = SAFE (even without clear subject)
        if context["intent"] == "learning":
            return True, "Learning intent detected"
        
        # Harmful intent = UNSAFE
        if context["intent"] == "harmful":
            return False, "Harmful intent detected - cannot assist with this request"
        
        # Entertainment with sensitive terms = UNSAFE
        if context["intent"] == "entertainment":
            return False, "This is an educational assistant. I can't help with entertainment requests."
        
        # Unclear = Ask for clarification
        if context["intent"] == "unclear":
            return True, "Context unclear - will proceed cautiously"
        
        return True, None


    def analyze_safety(self, message: str, context: dict = None) -> dict:
        """
        Main safety analysis function.
        
        Args:
            message: User input
            context: Optional context dict with learning_unit, intent, etc.
        
        Returns:
            {"is_safe": bool, "reason": str, "context": dict, "intent": str, "subject": str}
        """
        # Step 1: Detect intent
        intent = context.get('intent', self.detect_intent(message)) if context else self.detect_intent(message)
        
        # Step 2: Detect subject
        subject = self.detect_subject(message)
        
        # Step 3: Classify context
        ctx = self.classify_context(message, intent, subject)
        
        # Step 4: Safety check
        is_safe, reason = self.is_safe_for_education(ctx)
        
        return {
            "is_safe": is_safe,
            "reason": reason,
            "context": ctx,
            "allow_sensitive_terms": ctx["is_educational"],
            "intent": intent,
            "subject": subject,
        }


def analyze_safety(message: str) -> dict:
    """
    Main safety analysis function.
    
    Returns:
        {
            "safe": bool,
            "reason": str,
            "context": dict,
            "allow_sensitive_terms": bool
        }
    """
    analyzer = ContextAnalyzer()
    
    # Step 1: Detect intent
    intent = analyzer.detect_intent(message)
    
    # Step 2: Detect subject
    subject = analyzer.detect_subject(message)
    
    # Step 3: Classify context
    context = analyzer.classify_context(message, intent, subject)
    
    # Step 4: Safety check
    is_safe, reason = analyzer.is_safe_for_education(context)
    
    return {
        "safe": is_safe,
        "reason": reason,
        "context": context,
        "allow_sensitive_terms": context["is_educational"],
        "intent": intent,
        "subject": subject,
    }


def safe_content_filter(message: str, resource_type: str = "text") -> tuple[bool, str]:
    """
    Filter content with context awareness.
    
    Args:
        message: User input or content to check
        resource_type: Type of resource (text, pdf, video, etc.)
    
    Returns:
        (is_safe, message)
    """
    analysis = analyze_safety(message)
    
    if not analysis["safe"]:
        return False, analysis["reason"]
    
    # If educational context, allow all educational terms
    if analysis["allow_sensitive_terms"]:
        return True, f"✓ Educational content ({analysis['subject']}) - processing normally"
    
    return True, "✓ Content approved for learning"


# Example usage and tests
def test_safety_pipeline():
    """Test cases for safety pipeline."""
    
    test_cases = [
        # Should PASS (Educational)
        ("Explain human reproductive system", True),
        ("Teach me about sexual reproduction in plants", True),
        ("What is SQL injection in cybersecurity?", True),
        ("Define male genital anatomy", True),
        ("How does fertilization occur in biology?", True),
        ("Explain sperm formation", True),
        
        # Should PASS (Learning intent)
        ("How does encryption work?", True),
        ("Explain mating behavior in animals", True),
        
        # Should FAIL (Harmful)
        ("How to build a bomb", False),
        ("How to hack someone's account", False),
        
        # Should FAIL (Entertainment)
        ("Tell me a dirty joke", False),
        ("Give me adult content", False),
    ]
    
    print("🧪 Testing Context-Aware Safety Pipeline\n")
    
    for message, expected_safe in test_cases:
        result = analyze_safety(message)
        status = "✅ PASS" if result["safe"] == expected_safe else "❌ FAIL"
        
        print(f"{status}: '{message}'")
        print(f"   Intent: {result['intent']}, Subject: {result['subject']}")
        print(f"   Educational: {result['context']['is_educational']}")
        print(f"   Safe: {result['safe']} - {result['reason']}\n")


if __name__ == "__main__":
    test_safety_pipeline()
