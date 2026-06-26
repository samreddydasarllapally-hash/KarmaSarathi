"""
Learning Passport System

The unified database for all learning data - single source of truth.
Every agent (Planner, Learner, Progress, Revision) reads/writes here.

Each learning unit has a complete "passport" containing:
- Learning journey (attempts, time, revisions)
- Resources used
- Doubts and weak areas
- Assessment data
- Generated materials
- Personalized metadata
"""

from datetime import datetime, date
from typing import Optional, Literal


class LearningPassport:
    """Complete profile for a single learning unit."""
    
    def __init__(self, unit_id: int, subject: str, chapter: str, topic: str):
        self.unit_id = unit_id
        self.subject = subject
        self.chapter = chapter
        self.topic = topic
        
        # For Learner Agent compatibility
        self.user_id = None
        self.learning_unit = None
        self.mastery_level = 0.0
        self.confidence_level = 5
        self.total_time_spent_minutes = 0
        self.learning_attempts = 0
        self.cumulative_confusion_score = 0
        self.confusion_signals = []
        
        # Status
        self.status: Literal["pending", "learning", "completed", "practicing", "revision_due", "mastered", "archived"] = "pending"
        self.mastery: float = 0.0  # 0-5 scale
        self.confidence: int = 5  # 0-10 scale
        
        # Learning journey
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.last_accessed: Optional[str] = None
        self.time_spent_minutes: int = 0
        self.attempts: int = 0
        self.revisions: int = 0
        
        # Session state (for resume capability)
        self.session_checkpoint: dict = {
            "last_session_date": None,
            "completed_layers": [],
            "current_layer": None,
            "completion_pct": 0,
            "paused_at": None,
        }
        
        # Revision schedule
        self.last_revised: Optional[str] = None
        self.next_revision: Optional[str] = None
        self.revision_history: list[dict] = []
        
        # Resources — detailed per-session tracking
        self.resources_used: dict = {
            "pdfs": [],             # [{id, filename, chunks_used, used_at}]
            "videos": [],           # [{id, title, watched_seconds, used_at}]
            "notes": [],
            "textbooks": [],
            "bookmarks_used": [],   # bookmark IDs referenced during session
            "svgs_generated": 0,
            "svgs_viewed": 0,
            "svgs_interacted": 0,   # hovered/clicked on SVG nodes
            "generated_notes": False,
            "videos_watched": 0,
            "research_papers": [],
        }
        
        # Learning data
        self.questions_asked: int = 0
        self.doubts: list[str] = []
        self.doubt_history: list[dict] = []
        self.weak_areas: list[str] = []
        self.strong_areas: list[str] = []
        self.frustration_signals: int = 0  # count of emotional frustration events
        
        # Assessment
        self.quiz_score: Optional[int] = None
        self.quiz_attempts: int = 0
        self.practice_score: Optional[int] = None
        self.practice_attempts: int = 0
        self.understanding_checks: int = 0
        self.confusion_events: int = 0
        self.misconceptions: list[str] = []
        
        # Revision history — each entry: {date, score, time_spent, method}
        self.revision_history: list[dict] = []
        
        # Generated materials
        self.materials: dict = {
            "summary": False,
            "flashcards": 0,
            "mind_map": False,
            "formula_sheet": False,
            "revision_notes": False,
            "practice_problems": 0,
        }
        
        # Metadata
        self.difficulty_perceived: str = "medium"
        self.enjoyment_level: int = 3  # 1-5
        self.recommended_next: list[str] = []
        
        # Learning style adaptation
        self.effective_styles: dict = {}
        self.preferred_teaching_sequence: list[str] = []
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "unit_id": self.unit_id,
            "subject": self.subject,
            "chapter": self.chapter,
            "topic": self.topic,
            "status": self.status,
            "mastery": self.mastery,
            "confidence": self.confidence,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "last_accessed": self.last_accessed,
            "time_spent_minutes": self.time_spent_minutes,
            "attempts": self.attempts,
            "revisions": self.revisions,
            "session_checkpoint": self.session_checkpoint,
            "last_revised": self.last_revised,
            "next_revision": self.next_revision,
            "revision_history": self.revision_history,
            "resources_used": self.resources_used,
            "questions_asked": self.questions_asked,
            "doubts": self.doubts,
            "doubt_history": self.doubt_history,
            "weak_areas": self.weak_areas,
            "strong_areas": self.strong_areas,
            "frustration_signals": self.frustration_signals,
            "quiz_score": self.quiz_score,
            "quiz_attempts": self.quiz_attempts,
            "practice_score": self.practice_score,
            "practice_attempts": self.practice_attempts,
            "understanding_checks": self.understanding_checks,
            "confusion_events": self.confusion_events,
            "misconceptions": self.misconceptions,
            "materials": self.materials,
            "difficulty_perceived": self.difficulty_perceived,
            "enjoyment_level": self.enjoyment_level,
            "recommended_next": self.recommended_next,
            "effective_styles": self.effective_styles,
            "preferred_teaching_sequence": self.preferred_teaching_sequence,
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Restore from dictionary."""
        passport = cls(
            unit_id=data["unit_id"],
            subject=data["subject"],
            chapter=data["chapter"],
            topic=data["topic"],
        )
        for key, value in data.items():
            if hasattr(passport, key):
                setattr(passport, key, value)
        return passport


class PassportManager:
    """Manages all learning passports - CRUD operations."""
    
    def __init__(self, state: dict):
        self.state = state
        self._ensure_passport_storage()
    
    def _ensure_passport_storage(self):
        """Ensure passport storage exists in state."""
        if "learning_passports" not in self.state:
            self.state["learning_passports"] = {}
    
    def get_passport(self, user_id: str, learning_unit: str) -> Optional[LearningPassport]:
        """Get passport for a learning unit."""
        key = f"{user_id}:{learning_unit}"
        passport_data = self.state.get("learning_passports", {}).get(key)
        if passport_data:
            return LearningPassport.from_dict(passport_data)
        return None
    
    def create_passport(self, user_id: str, learning_unit: str, subject: str, chapter: str = "", topic: str = "") -> LearningPassport:
        """Create new passport."""
        unit_id = hash(f"{user_id}:{learning_unit}") % 1000000
        passport = LearningPassport(unit_id, subject, chapter or learning_unit, topic or learning_unit)
        passport.user_id = user_id
        passport.learning_unit = learning_unit
        self.save_passport(passport)
        return passport
    
    def save_passport(self, passport: LearningPassport):
        """Save passport to state."""
        if "learning_passports" not in self.state:
            self.state["learning_passports"] = {}
        user_id = getattr(passport, 'user_id', 'default')
        learning_unit = getattr(passport, 'learning_unit', passport.topic)
        key = f"{user_id}:{learning_unit}"
        self.state["learning_passports"][key] = passport.to_dict()
    
    def update_passport(self, unit_id: int, updates: dict):
        """Update specific fields in passport."""
        passport = self.get_passport(unit_id)
        if not passport:
            return None
        
        for key, value in updates.items():
            if hasattr(passport, key):
                setattr(passport, key, value)
        
        self.save_passport(passport)
        return passport
    
    def get_all_passports(self) -> list[LearningPassport]:
        """Get all passports."""
        passports = []
        for passport_data in self.state.get("learning_passports", {}).values():
            passports.append(LearningPassport.from_dict(passport_data))
        return passports
    
    def get_passports_by_subject(self, subject: str) -> list[LearningPassport]:
        """Get all passports for a subject."""
        return [p for p in self.get_all_passports() if p.subject == subject]
    
    def get_passports_by_status(self, status: str) -> list[LearningPassport]:
        """Get passports by status."""
        return [p for p in self.get_all_passports() if p.status == status]
    
    def record_session_start(self, user_id: str, learning_unit: str):
        """Record start of learning session."""
        passport = self.get_passport(user_id, learning_unit)
        if not passport:
            return
        
        passport.started_at = passport.started_at or datetime.now().isoformat()
        passport.last_accessed = datetime.now().isoformat()
        passport.attempts += 1
        passport.status = "learning"
        passport.session_checkpoint["last_session_date"] = date.today().isoformat()
        
        self.save_passport(passport)
    
    def record_session_checkpoint(self, user_id: str, learning_unit: str, completed_layers: list, current_layer: int, completion_pct: int):
        """Record progress checkpoint during session."""
        passport = self.get_passport(user_id, learning_unit)
        if not passport:
            return
        
        passport.session_checkpoint["completed_layers"] = completed_layers
        passport.session_checkpoint["current_layer"] = current_layer
        passport.session_checkpoint["completion_pct"] = completion_pct
        passport.session_checkpoint["paused_at"] = datetime.now().isoformat()
        
        self.save_passport(passport)
    
    def record_doubt(self, user_id: str, learning_unit: str, question: str, confusion_level: int, context: dict = None, resolved: bool = False):
        """Record a doubt/question."""
        passport = self.get_passport(user_id, learning_unit)
        if not passport:
            return
        
        passport.questions_asked += 1
        
        doubt_entry = {
            "question": question,
            "asked_at": datetime.now().isoformat(),
            "resolved": resolved,
            "confusion_level": confusion_level,
        }
        
        passport.doubt_history.append(doubt_entry)
        
        if not resolved or confusion_level >= 3:
            passport.doubts.append(question)
            passport.confusion_events += 1
        
        self.save_passport(passport)
    
    def record_completion(self, user_id: str, learning_unit: str, completion_data: dict):
        """Record completion of learning unit."""
        passport = self.get_passport(user_id, learning_unit)
        if not passport:
            return
        
        passport.status = "completed"
        passport.completed_at = datetime.now().isoformat()
        passport.mastery = completion_data.get('mastery_score', 0.0)
        passport.confidence = completion_data.get('confidence_level', 5)
        passport.time_spent_minutes += completion_data.get('time_spent_minutes', 0)
        passport.session_checkpoint["completion_pct"] = 100
        
        self.save_passport(passport)
        
        return passport
    
    def can_resume_session(self, user_id: str, learning_unit: str) -> tuple[bool, Optional[dict]]:
        """Check if there's a paused session to resume."""
        passport = self.get_passport(user_id, learning_unit)
        if not passport:
            return False, None
        
        checkpoint = passport.session_checkpoint
        can_resume = (
            checkpoint.get("paused_at") and
            checkpoint.get("completion_pct", 0) > 0 and
            checkpoint.get("completion_pct", 0) < 100
        )
        return can_resume, checkpoint if can_resume else None
    
    def get_resume_info(self, user_id: str, learning_unit: str) -> Optional[dict]:
        """Get information about paused session for resume."""
        can_resume, checkpoint = self.can_resume_session(user_id, learning_unit)
        if not can_resume:
            return None
        
        passport = self.get_passport(user_id, learning_unit)
        
        return {
            "topic": passport.topic,
            "last_session": checkpoint["last_session_date"],
            "completed_layers": checkpoint["completed_layers"],
            "current_layer": checkpoint["current_layer"],
            "completion_pct": checkpoint["completion_pct"],
            "time_spent": passport.time_spent_minutes,
        }
    
    def record_resource_used(self, user_id: str, learning_unit: str, resource_type: str, resource_info: dict):
        """Record a resource used during a session (PDF, video, SVG, bookmark, etc.)."""
        passport = self.get_passport(user_id, learning_unit)
        if not passport:
            return
        ru = passport.resources_used
        if resource_type == "pdf":
            existing = [r for r in ru["pdfs"] if r.get("id") == resource_info.get("id")]
            if not existing:
                ru["pdfs"].append({**resource_info, "used_at": datetime.now().isoformat()})
        elif resource_type == "video":
            ru["videos"].append({**resource_info, "used_at": datetime.now().isoformat()})
            ru["videos_watched"] = ru.get("videos_watched", 0) + 1
        elif resource_type == "bookmark":
            bookmark_id = resource_info.get("id")
            if bookmark_id and bookmark_id not in ru.get("bookmarks_used", []):
                ru.setdefault("bookmarks_used", []).append(bookmark_id)
        elif resource_type == "svg_generated":
            ru["svgs_generated"] = ru.get("svgs_generated", 0) + 1
        elif resource_type == "svg_viewed":
            ru["svgs_viewed"] = ru.get("svgs_viewed", 0) + 1
        elif resource_type == "svg_interacted":
            ru["svgs_interacted"] = ru.get("svgs_interacted", 0) + 1
        self.save_passport(passport)
    
    def record_quiz_result(self, user_id: str, learning_unit: str, score: int, total: int):
        """Record quiz attempt and score."""
        passport = self.get_passport(user_id, learning_unit)
        if not passport:
            return
        passport.quiz_score = score
        passport.quiz_attempts += 1
        self.save_passport(passport)
    
    def record_practice_result(self, user_id: str, learning_unit: str, score: int):
        """Record practice attempt and score."""
        passport = self.get_passport(user_id, learning_unit)
        if not passport:
            return
        passport.practice_score = score
        passport.practice_attempts += 1
        self.save_passport(passport)
    
    def record_frustration(self, user_id: str, learning_unit: str):
        """Increment frustration counter for a unit."""
        passport = self.get_passport(user_id, learning_unit)
        if not passport:
            return
        passport.frustration_signals += 1
        self.save_passport(passport)
    
    def add_revision_entry(self, user_id: str, learning_unit: str, score: float, time_spent: int, method: str = "review"):
        """Add a revision history entry."""
        passport = self.get_passport(user_id, learning_unit)
        if not passport:
            return
        passport.revision_history.append({
            "date": datetime.now().isoformat(),
            "score": score,
            "time_spent_minutes": time_spent,
            "method": method,
        })
        passport.revisions += 1
        self.save_passport(passport)
    
    def get_rich_passport_summary(self, user_id: str, learning_unit: str) -> Optional[dict]:
        """Return a human-readable summary of the full learning passport."""
        passport = self.get_passport(user_id, learning_unit)
        if not passport:
            return None
        ru = passport.resources_used
        return {
            "unit": learning_unit,
            "status": passport.status,
            "mastery": passport.mastery,
            "confidence": passport.confidence,
            "time_spent_minutes": passport.time_spent_minutes,
            "attempts": passport.attempts,
            "revisions": passport.revisions,
            "revision_history": passport.revision_history,
            "doubts_total": len(passport.doubt_history),
            "doubts_unresolved": len(passport.doubts),
            "quiz_score": passport.quiz_score,
            "quiz_attempts": passport.quiz_attempts,
            "practice_score": passport.practice_score,
            "practice_attempts": passport.practice_attempts,
            "pdfs_used": len(ru.get("pdfs", [])),
            "bookmarks_used": len(ru.get("bookmarks_used", [])),
            "svgs_generated": ru.get("svgs_generated", 0),
            "svgs_viewed": ru.get("svgs_viewed", 0),
            "videos_watched": ru.get("videos_watched", 0),
            "frustration_signals": passport.frustration_signals,
            "materials": passport.materials,
            "weak_areas": passport.weak_areas,
            "strong_areas": passport.strong_areas,
        }


def get_passport_manager(state: dict) -> PassportManager:
    """Factory function to get passport manager."""
    return PassportManager(state)
