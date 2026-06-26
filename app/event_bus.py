"""
Event Bus - Planner ↔ Learner Communication

Handles bidirectional events:
- Learner → Planner: Unit completed, needs more time, mastery data
- Planner → Learner: Schedule updated, deadline pressure, next unit ready
"""

from datetime import datetime
from typing import Dict, Any, List, Callable, Optional
from enum import Enum


class EventType(Enum):
    """Event types for agent communication"""
    
    # Learner → Planner
    UNIT_COMPLETED = "unit_completed"
    UNIT_PARTIALLY_COMPLETED = "unit_partially_completed"
    NEEDS_MORE_TIME = "needs_more_time"
    STUDENT_STRUGGLING = "student_struggling"
    SESSION_PAUSED = "session_paused"
    MASTERY_UPDATE = "mastery_update"
    
    # Planner → Learner
    SCHEDULE_UPDATED = "schedule_updated"
    DEADLINE_APPROACHING = "deadline_approaching"
    NEXT_UNIT_READY = "next_unit_ready"
    REVISION_DUE = "revision_due"
    BREAK_SUGGESTED = "break_suggested"


class Event:
    """Event object"""
    
    def __init__(
        self,
        event_type: EventType,
        source: str,
        target: str,
        data: Dict[str, Any],
        priority: int = 5
    ):
        self.event_type = event_type
        self.source = source
        self.target = target
        self.data = data
        self.priority = priority
        self.timestamp = datetime.now().isoformat()
        self.processed = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "source": self.source,
            "target": self.target,
            "data": self.data,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "processed": self.processed
        }


class EventBus:
    """Central event bus for agent communication"""
    
    def __init__(self, state: dict):
        self.state = state
        self.listeners: Dict[EventType, List[Callable]] = {}
        self._ensure_event_storage()
    
    def _ensure_event_storage(self):
        """Initialize event storage in state"""
        if "event_queue" not in self.state:
            self.state["event_queue"] = []
        if "event_history" not in self.state:
            self.state["event_history"] = []
    
    def emit(self, event: Event):
        """Emit an event to the bus"""
        
        # Add to queue
        self.state["event_queue"].append(event.to_dict())
        
        # Notify listeners
        if event.event_type in self.listeners:
            for listener in self.listeners[event.event_type]:
                try:
                    listener(event)
                except Exception as e:
                    print(f"Error in listener for {event.event_type}: {e}")
        
        # Mark as processed
        event.processed = True
        
        # Move to history
        self.state["event_history"].append(event.to_dict())
        
        return event
    
    def subscribe(self, event_type: EventType, listener: Callable):
        """Subscribe to an event type"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(listener)
    
    def get_pending_events(self, target: str = None) -> List[Dict[str, Any]]:
        """Get pending events, optionally filtered by target"""
        pending = [e for e in self.state["event_queue"] if not e.get("processed", False)]
        
        if target:
            pending = [e for e in pending if e.get("target") == target]
        
        return pending
    
    def mark_processed(self, event_dict: Dict[str, Any]):
        """Mark an event as processed"""
        for event in self.state["event_queue"]:
            if event["timestamp"] == event_dict["timestamp"]:
                event["processed"] = True
                break


class LearnerEventEmitter:
    """Handles event emission from Learner Agent"""
    
    def __init__(self, event_bus: EventBus, user_id: str):
        self.event_bus = event_bus
        self.user_id = user_id
    
    def emit_unit_completed(
        self,
        learning_unit: str,
        mastery_data: Dict[str, Any]
    ) -> Event:
        """
        Emit event when student completes a learning unit
        
        Args:
            learning_unit: Name of completed unit
            mastery_data: Detailed mastery breakdown
        """
        
        event = Event(
            event_type=EventType.UNIT_COMPLETED,
            source="learner",
            target="planner",
            data={
                "user_id": self.user_id,
                "learning_unit": learning_unit,
                "mastery_score": mastery_data.get("mastery_score", 0.0),
                "confidence_level": mastery_data.get("confidence_level", 0),
                "time_spent_minutes": mastery_data.get("time_spent_minutes", 0),
                "layers_completed": mastery_data.get("layers_completed", []),
                "doubts_count": mastery_data.get("doubts_count", 0),
                "confusion_score": mastery_data.get("confusion_score", 0),
                "resources_used": mastery_data.get("resources_used", []),
                "detailed_mastery": mastery_data.get("detailed_mastery", {})
            },
            priority=8  # High priority
        )
        
        return self.event_bus.emit(event)
    
    def emit_needs_more_time(
        self,
        learning_unit: str,
        additional_sessions: int,
        reason: str
    ) -> Event:
        """
        Emit event when student needs more time on a unit
        """
        
        event = Event(
            event_type=EventType.NEEDS_MORE_TIME,
            source="learner",
            target="planner",
            data={
                "user_id": self.user_id,
                "learning_unit": learning_unit,
                "additional_sessions": additional_sessions,
                "reason": reason,
                "current_mastery": 0.0  # Can be filled from passport
            },
            priority=7
        )
        
        return self.event_bus.emit(event)
    
    def emit_student_struggling(
        self,
        learning_unit: str,
        confusion_score: int,
        stuck_on: str
    ) -> Event:
        """
        Emit event when student is struggling significantly
        """
        
        event = Event(
            event_type=EventType.STUDENT_STRUGGLING,
            source="learner",
            target="planner",
            data={
                "user_id": self.user_id,
                "learning_unit": learning_unit,
                "confusion_score": confusion_score,
                "stuck_on": stuck_on,
                "suggestion": "schedule_lighter_session" if confusion_score >= 7 else "continue"
            },
            priority=9  # Very high priority
        )
        
        return self.event_bus.emit(event)
    
    def emit_session_paused(
        self,
        learning_unit: str,
        progress_pct: int,
        checkpoint: Dict[str, Any]
    ) -> Event:
        """
        Emit event when student pauses a session
        """
        
        event = Event(
            event_type=EventType.SESSION_PAUSED,
            source="learner",
            target="planner",
            data={
                "user_id": self.user_id,
                "learning_unit": learning_unit,
                "progress_pct": progress_pct,
                "checkpoint": checkpoint
            },
            priority=5
        )
        
        return self.event_bus.emit(event)
    
    def emit_mastery_update(
        self,
        learning_unit: str,
        mastery_breakdown: Dict[str, float]
    ) -> Event:
        """
        Emit detailed mastery breakdown update
        """
        
        event = Event(
            event_type=EventType.MASTERY_UPDATE,
            source="learner",
            target="planner",
            data={
                "user_id": self.user_id,
                "learning_unit": learning_unit,
                "mastery_breakdown": mastery_breakdown
            },
            priority=6
        )
        
        return self.event_bus.emit(event)


class PlannerEventEmitter:
    """Handles event emission from Planner Agent"""
    
    def __init__(self, event_bus: EventBus, user_id: str):
        self.event_bus = event_bus
        self.user_id = user_id
    
    def emit_schedule_updated(
        self,
        updates: List[Dict[str, Any]]
    ) -> Event:
        """
        Emit event when schedule is updated
        """
        
        event = Event(
            event_type=EventType.SCHEDULE_UPDATED,
            source="planner",
            target="learner",
            data={
                "user_id": self.user_id,
                "updates": updates,
                "reason": "completion" if updates else "adjustment"
            },
            priority=6
        )
        
        return self.event_bus.emit(event)
    
    def emit_deadline_approaching(
        self,
        subject: str,
        days_remaining: int,
        units_pending: int
    ) -> Event:
        """
        Emit event when deadline is approaching
        """
        
        event = Event(
            event_type=EventType.DEADLINE_APPROACHING,
            source="planner",
            target="learner",
            data={
                "user_id": self.user_id,
                "subject": subject,
                "days_remaining": days_remaining,
                "units_pending": units_pending,
                "urgency": "high" if days_remaining <= 7 else "medium"
            },
            priority=8
        )
        
        return self.event_bus.emit(event)
    
    def emit_next_unit_ready(
        self,
        next_unit: str,
        scheduled_time: str
    ) -> Event:
        """
        Emit event when next unit is scheduled and ready
        """
        
        event = Event(
            event_type=EventType.NEXT_UNIT_READY,
            source="planner",
            target="learner",
            data={
                "user_id": self.user_id,
                "next_unit": next_unit,
                "scheduled_time": scheduled_time
            },
            priority=5
        )
        
        return self.event_bus.emit(event)
    
    def emit_revision_due(
        self,
        learning_unit: str,
        last_revised: str,
        mastery_before: float
    ) -> Event:
        """
        Emit event when revision is due for a unit
        """
        
        event = Event(
            event_type=EventType.REVISION_DUE,
            source="planner",
            target="learner",
            data={
                "user_id": self.user_id,
                "learning_unit": learning_unit,
                "last_revised": last_revised,
                "mastery_before": mastery_before,
                "revision_type": "spaced_repetition"
            },
            priority=7
        )
        
        return self.event_bus.emit(event)


class PlannerEventHandler:
    """Handles events received by Planner"""
    
    def __init__(self, planner_agent, state: dict):
        self.planner = planner_agent
        self.state = state
    
    def handle_unit_completed(self, event: Event):
        """Handle unit completion from Learner"""
        
        data = event.data
        learning_unit = data["learning_unit"]
        mastery_score = data["mastery_score"]
        
        print(f"[Planner] Unit completed: {learning_unit} (mastery: {mastery_score:.2f})")
        
        # Mark unit as completed in planner state
        # Update progress
        # Calculate next unit
        # Schedule next session
        
        # For now, just acknowledge
        return {
            "acknowledged": True,
            "next_action": "schedule_next_unit",
            "message": f"Great! {learning_unit} marked complete."
        }
    
    def handle_needs_more_time(self, event: Event):
        """Handle request for more time"""
        
        data = event.data
        learning_unit = data["learning_unit"]
        additional_sessions = data["additional_sessions"]
        
        print(f"[Planner] More time requested for {learning_unit}: +{additional_sessions} sessions")
        
        # Adjust schedule
        # Add additional sessions
        # Recalculate deadline velocity
        
        return {
            "acknowledged": True,
            "sessions_added": additional_sessions,
            "message": f"Added {additional_sessions} more sessions for {learning_unit}"
        }
    
    def handle_student_struggling(self, event: Event):
        """Handle struggling student alert"""
        
        data = event.data
        learning_unit = data["learning_unit"]
        confusion_score = data["confusion_score"]
        
        print(f"[Planner] Student struggling with {learning_unit} (confusion: {confusion_score})")
        
        # Adjust schedule to lighter load
        # Suggest break
        # Flag for intervention
        
        return {
            "acknowledged": True,
            "action": "reduce_load" if confusion_score >= 7 else "monitor",
            "message": "Adjusting schedule to reduce cognitive load"
        }


class LearnerEventHandler:
    """Handles events received by Learner"""
    
    def __init__(self, learner_agent):
        self.learner = learner_agent
    
    def handle_deadline_approaching(self, event: Event):
        """Handle deadline pressure notification"""
        
        data = event.data
        days_remaining = data["days_remaining"]
        units_pending = data["units_pending"]
        
        # Adjust teaching style (more focused, less exploration)
        # Suggest prioritization
        
        return {
            "acknowledged": True,
            "teaching_adjustment": "focused_mode",
            "message": f"{days_remaining} days left, {units_pending} units pending"
        }
    
    def handle_revision_due(self, event: Event):
        """Handle revision notification"""
        
        data = event.data
        learning_unit = data["learning_unit"]
        
        # Prepare revision session
        # Load previous materials
        
        return {
            "acknowledged": True,
            "session_type": "revision",
            "message": f"Revision ready for {learning_unit}"
        }


def setup_event_system(state: dict, planner_agent=None, learner_agent=None):
    """
    Setup complete event system with subscriptions
    
    Returns:
        (event_bus, planner_emitter, learner_emitter)
    """
    
    event_bus = EventBus(state)
    
    # Create emitters
    planner_emitter = PlannerEventEmitter(event_bus, user_id="system")
    learner_emitter = LearnerEventEmitter(event_bus, user_id="system")
    
    # Create handlers
    if planner_agent:
        planner_handler = PlannerEventHandler(planner_agent, state)
        
        # Subscribe planner to learner events
        event_bus.subscribe(EventType.UNIT_COMPLETED, planner_handler.handle_unit_completed)
        event_bus.subscribe(EventType.NEEDS_MORE_TIME, planner_handler.handle_needs_more_time)
        event_bus.subscribe(EventType.STUDENT_STRUGGLING, planner_handler.handle_student_struggling)
    
    if learner_agent:
        learner_handler = LearnerEventHandler(learner_agent)
        
        # Subscribe learner to planner events
        event_bus.subscribe(EventType.DEADLINE_APPROACHING, learner_handler.handle_deadline_approaching)
        event_bus.subscribe(EventType.REVISION_DUE, learner_handler.handle_revision_due)
    
    return event_bus, planner_emitter, learner_emitter
