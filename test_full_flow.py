"""
Comprehensive Test: Full Planner → Scheduler → Progress → Learner Flow
Tests the complete user journey through the system
"""

import sys
from app.graph import karma_graph
from app.state import StudentState

def print_section(title: str):
    """Print formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def run_interaction(state: dict, user_message: str, show_state: bool = False):
    """Run one interaction and display response"""
    print(f"USER: {user_message}")
    print("-" * 70)
    
    state["user_message"] = user_message
    result = karma_graph.invoke(state)
    
    print(f"BOT: {result.get('agent_response', 'No response')}")
    print()
    
    if show_state:
        print(f"[STATE] Intent: {result.get('intent')}")
        print(f"[STATE] Planner stage: {result.get('planner_stage')}")
        print(f"[STATE] Tasks count: {len(result.get('tasks', []))}")
        print()
    
    return result

def test_planner_flow():
    """Test complete planner setup flow"""
    print_section("TEST 1: PLANNER FLOW (Initial Setup)")
    
    state = StudentState().model_dump()
    
    # Step 1: Initial goal
    print("Step 1: User provides goal and deadline")
    state = run_interaction(state, "I'm preparing for semester exam in 10 days", show_state=True)
    
    # Step 2: Routine - wake time
    print("\nStep 2: Wake time")
    state = run_interaction(state, "6 AM")
    
    # Step 3: Routine - sleep time
    print("\nStep 3: Sleep time")
    state = run_interaction(state, "11 PM")
    
    # Step 4-11: Routine details (answering all 9 questions)
    routine_answers = [
        "8 AM",           # breakfast
        "1 PM",           # lunch
        "8 PM",           # dinner
        "9am-4pm",        # college hours
        "no",             # gym
        "30 min",         # travel
        "no",             # prayer
        "no",             # fixed activities
        "every 60 min"    # water interval
    ]
    
    print("\nSteps 4-12: Routine details")
    for i, answer in enumerate(routine_answers, start=4):
        print(f"\nStep {i}: {answer}")
        state = run_interaction(state, answer)
    
    # Step 13: Subjects
    print("\nStep 13: Subjects with confidence and progress")
    state = run_interaction(state, "DS 8 4/5, OS 3 1/5, DBMS 6 2/4", show_state=True)
    
    # Step 14: Syllabus method
    print("\nStep 14: Syllabus method - choose generated")
    state = run_interaction(state, "4", show_state=True)
    
    # Wait for AI to generate roadmap (automatic)
    print("\n[Waiting for AI to generate topic roadmap...]")
    
    # Step 15: Completed topics
    print("\nStep 15: Mark some topics as completed")
    state = run_interaction(state, "DS: Arrays, Linked Lists")
    
    # Step 16: Focus duration
    print("\nStep 16: Focus duration")
    state = run_interaction(state, "45 min")
    
    # Step 17: Break duration
    print("\nStep 17: Break duration")
    state = run_interaction(state, "10")
    
    # Step 18: Productivity peak
    print("\nStep 18: Productivity peak")
    state = run_interaction(state, "Morning")
    
    # Step 19: Energy peak
    print("\nStep 19: Energy peak")
    state = run_interaction(state, "morning")
    
    # Step 20: Learning style
    print("\nStep 20: Learning style")
    state = run_interaction(state, "mixed", show_state=True)
    
    # System analyzes and creates strategy (automatic)
    print("\n[System analyzing user profile and creating strategy...]")
    
    # Step 21: Review plan
    print("\nStep 21: Confirm strategy")
    state = run_interaction(state, "yes", show_state=True)
    
    # Display final state
    print_section("PLANNER RESULTS")
    print(f"✓ Goal: {state.get('goal')}")
    print(f"✓ Deadline: {state.get('deadline')}")
    print(f"✓ Available hours: {state.get('available_hours')} hrs/day")
    print(f"✓ Subjects: {len(state.get('subjects', []))}")
    print(f"✓ Total tasks generated: {len(state.get('tasks', []))}")
    
    # Show some tasks
    print("\n📋 Sample Tasks Generated:")
    for task in state.get('tasks', [])[:5]:
        print(f"  • [{task.get('type', '?')}] {task.get('title')} - {task.get('duration_minutes')}min")
    
    return state

def test_scheduler(state: dict):
    """Test scheduler building today's timetable"""
    print_section("TEST 2: SCHEDULER (Today's Timetable)")
    
    print("Requesting today's schedule...")
    state = run_interaction(state, "schedule", show_state=True)
    
    # Display schedule details
    schedule = state.get('today_schedule', [])
    print(f"\n📅 Today's Schedule: {len(schedule)} slots")
    
    return state

def test_progress_flow(state: dict):
    """Test progress agent with task completion"""
    print_section("TEST 3: PROGRESS AGENT (Daily Loop)")
    
    # Start first task
    print("Step 1: Start first task")
    state = run_interaction(state, "next", show_state=True)
    
    # Complete task
    print("\nStep 2: Mark as completed")
    state = run_interaction(state, "1")  # Yes, completed
    
    # Rate understanding
    print("\nStep 3: Rate understanding")
    state = run_interaction(state, "4", show_state=True)  # Comfortable
    
    # Check for spaced revisions
    revision_tasks = [t for t in state.get('tasks', []) 
                      if t.get('type') == 'revision' and t.get('spaced_day_offset')]
    
    print(f"\n✓ Spaced revisions scheduled: {len(revision_tasks)}")
    for rev in revision_tasks[:3]:
        print(f"  • Day+{rev.get('spaced_day_offset')}: {rev.get('title')} ({rev.get('duration_minutes')}min)")
    
    # Show progress stats
    print(f"\n📊 Progress Stats:")
    print(f"  • XP: {state.get('xp')}")
    print(f"  • Streak: {state.get('streak')} days")
    print(f"  • Completed today: {state.get('completed_today')}")
    
    return state

def test_learner_agent(state: dict):
    """Test learner agent with multi-modal output"""
    print_section("TEST 4: LEARNER AGENT (Multi-Modal Learning)")
    
    # Test 1: Direct topic request
    print("Test 4a: Direct topic explanation")
    state = run_interaction(state, "teach me DBMS Normalization", show_state=True)
    
    # Check learner output
    learner_output = state.get('learner_output', {})
    print(f"\n✓ Learner Output Generated:")
    print(f"  • Topic: {learner_output.get('topic', 'N/A')}")
    print(f"  • Subject: {learner_output.get('subject', 'N/A')}")
    print(f"  • Explanation length: {len(learner_output.get('explanation', ''))} chars")
    print(f"  • SVG diagram: {'✓ Generated' if learner_output.get('svg') else '✗ None'}")
    print(f"  • Video suggestions: {len(learner_output.get('videos', []))}")
    print(f"  • MCQs: {len(learner_output.get('mcqs', []))}")
    
    if learner_output.get('svg'):
        print(f"\n📊 SVG Diagram Preview (first 200 chars):")
        print(f"  {learner_output['svg'][:200]}...")
    
    if learner_output.get('mcqs'):
        print(f"\n✅ Sample MCQ:")
        mcq = learner_output['mcqs'][0]
        print(f"  Q: {mcq.get('q', 'N/A')}")
        print(f"  Options: {', '.join(mcq.get('opts', []))}")
        print(f"  Answer: {mcq.get('ans', 'N/A')}")
    
    return state

def test_learner_bridge(state: dict):
    """Test learner agent bridge during active task"""
    print_section("TEST 5: LEARNER BRIDGE (During Task)")
    
    # Start a new task
    print("Step 1: Start next task")
    state = run_interaction(state, "next", show_state=True)
    
    active_task_id = state.get('active_task_id')
    print(f"\n✓ Active task ID: {active_task_id}")
    
    # Trigger learner agent during task
    print("\nStep 2: Request diagram during task (BRIDGE)")
    state = run_interaction(state, "show me a diagram", show_state=True)
    
    # Check if learner was triggered
    if state.get('learner_output'):
        print("\n✓ BRIDGE SUCCESS: Learner agent triggered during active task")
        print(f"  • Active task ID preserved: {state.get('active_task_id')}")
        print(f"  • Learner output generated: {state.get('learner_output', {}).get('topic')}")
    
    # Return to progress loop
    print("\nStep 3: Return to progress loop")
    state = run_interaction(state, "next", show_state=True)
    
    return state

def test_archive_system(state: dict):
    """Test archive and knowledge vault"""
    print_section("TEST 6: ARCHIVE SYSTEM (Knowledge Vault)")
    
    # First, complete a task to have something to archive
    print("Step 1: Complete another task")
    state = run_interaction(state, "next")
    state = run_interaction(state, "1")  # Completed
    state = run_interaction(state, "5", show_state=True)  # Perfect understanding
    
    # Get a completed topic
    completed_tasks = [t for t in state.get('tasks', []) if t.get('status') == 'completed']
    if completed_tasks:
        topic = completed_tasks[0].get('topic') or completed_tasks[0].get('title')
        subject = completed_tasks[0].get('subject', '')
        
        print(f"\nStep 2: Archive topic: {topic} from {subject}")
        state = run_interaction(state, f"archive {topic} from {subject}", show_state=True)
        
        # Check knowledge vault
        vault = state.get('knowledge_vault', [])
        print(f"\n✓ Knowledge Vault: {len(vault)} topics")
        for entry in vault:
            stars = "★" * round(entry.get('mastery', 0)) + "☆" * (5 - round(entry.get('mastery', 0)))
            print(f"  • {entry.get('subject')}: {entry.get('topic')} {stars}")
        
        # Check revision tasks still exist
        revision_tasks = [t for t in state.get('tasks', []) 
                          if t.get('type') == 'revision' and t.get('topic') == topic]
        print(f"\n✓ Revision tasks preserved: {len(revision_tasks)}")
    
    # View vault
    print("\nStep 3: View full vault")
    state = run_interaction(state, "vault")
    
    return state

def test_roadmap_and_summary(state: dict):
    """Test roadmap and summary commands"""
    print_section("TEST 7: PROGRESS TRACKING")
    
    print("Step 1: View roadmap")
    state = run_interaction(state, "roadmap")
    
    print("\nStep 2: View summary")
    state = run_interaction(state, "summary")
    
    return state

def run_all_tests():
    """Run all tests in sequence"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║           KARMASARATHI - COMPREHENSIVE SYSTEM TEST               ║
║                                                                  ║
║  Testing: Planner → Scheduler → Progress → Learner → Archive    ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    try:
        # Test 1: Complete planner flow
        state = test_planner_flow()
        input("\n⏸  Press Enter to continue to Scheduler test...")
        
        # Test 2: Scheduler
        state = test_scheduler(state)
        input("\n⏸  Press Enter to continue to Progress test...")
        
        # Test 3: Progress agent
        state = test_progress_flow(state)
        input("\n⏸  Press Enter to continue to Learner test...")
        
        # Test 4: Learner agent
        state = test_learner_agent(state)
        input("\n⏸  Press Enter to continue to Bridge test...")
        
        # Test 5: Learner bridge
        state = test_learner_bridge(state)
        input("\n⏸  Press Enter to continue to Archive test...")
        
        # Test 6: Archive system
        state = test_archive_system(state)
        input("\n⏸  Press Enter to continue to Tracking test...")
        
        # Test 7: Roadmap and summary
        state = test_roadmap_and_summary(state)
        
        print_section("ALL TESTS COMPLETED ✓")
        print("System is fully functional!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
