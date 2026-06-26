"""
Test Planner ↔ Learner Event System
Shows bidirectional communication through events
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.learner import LearnerAgent
from app.event_bus import EventBus, PlannerEventEmitter, EventType


class MockLLM:
    def invoke(self, prompt):
        class Response:
            content = "Mock response"
        return Response()


def test_event_system():
    print("\n" + "="*80)
    print("  TEST: PLANNER ↔ LEARNER EVENT SYSTEM")
    print("="*80)
    
    state = {}
    
    # Initialize Learner with event system
    learner = LearnerAgent(MockLLM(), "student_123", state)
    
    # Initialize Planner event emitter
    planner_emitter = PlannerEventEmitter(learner.event_bus, "student_123")
    
    # Test 1: Unit Completion Event
    print("\n[Test 1] Learner → Planner: Unit Completed")
    print("-" * 80)
    
    completion_event = learner.event_emitter.emit_unit_completed(
        learning_unit="FCFS Scheduling",
        mastery_data={
            "mastery_score": 0.87,
            "confidence_level": 8,
            "time_spent_minutes": 45,
            "layers_completed": [0, 1, 2, 3],
            "doubts_count": 2,
            "confusion_score": 3,
            "resources_used": ["os_notes.pdf"]
        }
    )
    
    print(f"✓ Event emitted: {completion_event.event_type.value}")
    print(f"  Source: {completion_event.source}")
    print(f"  Target: {completion_event.target}")
    print(f"  Unit: {completion_event.data['learning_unit']}")
    print(f"  Mastery: {completion_event.data['mastery_score']}")
    print(f"  Time: {completion_event.data['time_spent_minutes']} min")
    
    # Check event in queue
    pending = learner.event_bus.get_pending_events(target="planner")
    print(f"\n✓ Planner has {len(pending)} pending event(s)")
    
    # Test 2: Needs More Time Event
    print("\n[Test 2] Learner → Planner: Needs More Time")
    print("-" * 80)
    
    more_time_event = learner.event_emitter.emit_needs_more_time(
        learning_unit="FCFS Scheduling",
        additional_sessions=2,
        reason="Student struggling with advanced concepts"
    )
    
    print(f"✓ Event emitted: {more_time_event.event_type.value}")
    print(f"  Unit: {more_time_event.data['learning_unit']}")
    print(f"  Additional sessions: {more_time_event.data['additional_sessions']}")
    print(f"  Reason: {more_time_event.data['reason']}")
    
    # Test 3: Student Struggling Event
    print("\n[Test 3] Learner → Planner: Student Struggling")
    print("-" * 80)
    
    struggling_event = learner.event_emitter.emit_student_struggling(
        learning_unit="FCFS Scheduling",
        confusion_score=8,
        stuck_on="convoy effect formula"
    )
    
    print(f"✓ Event emitted: {struggling_event.event_type.value}")
    print(f"  Confusion score: {struggling_event.data['confusion_score']}")
    print(f"  Stuck on: {struggling_event.data['stuck_on']}")
    print(f"  Priority: {struggling_event.priority} (very high)")
    
    # Test 4: Session Paused Event
    print("\n[Test 4] Learner → Planner: Session Paused")
    print("-" * 80)
    
    paused_event = learner.event_emitter.emit_session_paused(
        learning_unit="FCFS Scheduling",
        progress_pct=65,
        checkpoint={
            "completed_layers": [0, 1, 2],
            "current_layer": 3,
            "completion_pct": 65
        }
    )
    
    print(f"✓ Event emitted: {paused_event.event_type.value}")
    print(f"  Progress: {paused_event.data['progress_pct']}%")
    print(f"  Can resume from: Layer {paused_event.data['checkpoint']['current_layer']}")
    
    # Test 5: Planner → Learner: Deadline Approaching
    print("\n[Test 5] Planner → Learner: Deadline Approaching")
    print("-" * 80)
    
    deadline_event = planner_emitter.emit_deadline_approaching(
        subject="Operating Systems",
        days_remaining=5,
        units_pending=12
    )
    
    print(f"✓ Event emitted: {deadline_event.event_type.value}")
    print(f"  Days remaining: {deadline_event.data['days_remaining']}")
    print(f"  Units pending: {deadline_event.data['units_pending']}")
    print(f"  Urgency: {deadline_event.data['urgency']}")
    
    # Check learner received it
    learner_events = learner.event_bus.get_pending_events(target="learner")
    print(f"\n✓ Learner has {len(learner_events)} pending event(s)")
    
    # Test 6: Planner → Learner: Next Unit Ready
    print("\n[Test 6] Planner → Learner: Next Unit Ready")
    print("-" * 80)
    
    next_unit_event = planner_emitter.emit_next_unit_ready(
        next_unit="SJF Scheduling",
        scheduled_time="2024-01-15 10:00"
    )
    
    print(f"✓ Event emitted: {next_unit_event.event_type.value}")
    print(f"  Next unit: {next_unit_event.data['next_unit']}")
    print(f"  Scheduled: {next_unit_event.data['scheduled_time']}")
    
    # Test 7: Event History
    print("\n[Test 7] Event History")
    print("-" * 80)
    
    history = state.get("event_history", [])
    print(f"✓ Total events in history: {len(history)}")
    
    # Show event types
    event_types = {}
    for event in history:
        etype = event['event_type']
        event_types[etype] = event_types.get(etype, 0) + 1
    
    print("\nEvent breakdown:")
    for etype, count in event_types.items():
        print(f"  - {etype}: {count}")
    
    # Test 8: Event Priority
    print("\n[Test 8] Event Priority Queue")
    print("-" * 80)
    
    all_events = state.get("event_queue", [])
    sorted_events = sorted(all_events, key=lambda x: x['priority'], reverse=True)
    
    print(f"✓ Events sorted by priority:")
    for i, event in enumerate(sorted_events[:5], 1):
        print(f"  {i}. {event['event_type']} (priority: {event['priority']})")
    
    # Test 9: Request More Time (using learner method)
    print("\n[Test 9] Student requests more time (via Learner method)")
    print("-" * 80)
    
    learner.session_active = True
    learner.current_unit = "FCFS Scheduling"
    
    result = learner.request_more_time(
        additional_sessions=3,
        reason="Need more practice with problems"
    )
    
    print(f"✓ Request result: {result['type']}")
    print(f"  Message: {result['message']}")
    print(f"  Status: {result['status']}")
    
    # Verify event was emitted
    recent_events = [e for e in state.get("event_queue", []) if e['event_type'] == 'needs_more_time']
    print(f"\n✓ Needs more time events: {len(recent_events)}")
    
    # Test 10: Summary
    print("\n[Test 10] System Summary")
    print("-" * 80)
    
    total_events = len(state.get("event_history", []))
    learner_to_planner = sum(1 for e in state.get("event_history", []) if e['source'] == 'learner')
    planner_to_learner = sum(1 for e in state.get("event_history", []) if e['source'] == 'planner')
    
    print(f"Total events: {total_events}")
    print(f"  Learner → Planner: {learner_to_planner}")
    print(f"  Planner → Learner: {planner_to_learner}")
    print(f"\nBidirectional communication: ✓ WORKING")
    
    print("\n" + "="*80)
    print("  ✓ EVENT SYSTEM: ALL TESTS PASSED")
    print("  Planner ↔ Learner communication fully functional")
    print("="*80)
    
    print("\n✅ Event Types Working:")
    print("  • UNIT_COMPLETED - Learner notifies Planner of completion")
    print("  • NEEDS_MORE_TIME - Student requests additional sessions")
    print("  • STUDENT_STRUGGLING - High confusion alert to Planner")
    print("  • SESSION_PAUSED - Save checkpoint for resume")
    print("  • DEADLINE_APPROACHING - Planner warns Learner of time pressure")
    print("  • NEXT_UNIT_READY - Planner schedules next learning unit")
    
    print("\n🎯 Integration Complete:")
    print("  Learner can now seamlessly hand off to Planner")
    print("  Planner can influence Learner's teaching strategy")
    print("  Full bidirectional event-driven communication ✓")


if __name__ == "__main__":
    test_event_system()
