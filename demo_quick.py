"""
Quick Demo: Planner + Learner Agent
Simplified test that shows the key features quickly
"""

from app.graph import karma_graph
from app.state import StudentState
import json

def demo_header(title: str):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def quick_planner_setup():
    """Quick planner setup with minimal interaction"""
    demo_header("🎯 DEMO 1: PLANNER (Quick Setup)")
    
    state = StudentState().model_dump()
    
    # Simulate quick onboarding
    interactions = [
        ("Goal", "I'm preparing for semester exam in 10 days"),
        ("Wake time", "6 AM"),
        ("Sleep time", "11 PM"),
        ("Breakfast", "8 AM"),
        ("Lunch", "1 PM"),
        ("Dinner", "8 PM"),
        ("College hours", "9am-4pm"),
        ("Gym", "no"),
        ("Travel", "30 min"),
        ("Prayer", "no"),
        ("Fixed activities", "no"),
        ("Water reminder", "every 60 min"),
        ("Subjects", "Data Structures 8 4/5, Operating System 3 1/5, DBMS 6 2/4"),
        ("Syllabus method", "4"),  # Generate roadmap
        ("Completed topics", "no"),
        ("Focus duration", "45 min"),
        ("Break duration", "10"),
        ("Productivity peak", "Morning"),
        ("Energy peak", "morning"),
        ("Learning style", "mixed"),
        ("Confirm", "yes")
    ]
    
    print("🤖 Running automated planner setup...")
    print("   (In real use, user answers each question interactively)\n")
    
    for label, message in interactions:
        print(f"  [{label}] {message}")
        state["user_message"] = message
        state = karma_graph.invoke(state)
    
    print("\n✓ Planner setup complete!")
    print(f"  • Goal: {state.get('goal')}")
    print(f"  • Deadline: {state.get('deadline')}")
    print(f"  • Subjects: {len(state.get('subjects', []))}")
    print(f"  • Tasks generated: {len(state.get('tasks', []))}")
    
    # Show sample tasks
    print("\n📋 Sample Tasks:")
    for task in state.get('tasks', [])[:3]:
        print(f"  • {task.get('title')} ({task.get('duration_minutes')}min)")
    
    return state

def demo_learner_basic(state: dict):
    """Demo basic learner functionality"""
    demo_header("🎓 DEMO 2: LEARNER AGENT (Basic)")
    
    print("User asks: 'teach me DBMS Normalization'\n")
    
    state["user_message"] = "teach me DBMS Normalization"
    result = karma_graph.invoke(state)
    
    print("🤖 BOT RESPONSE:")
    print("-" * 70)
    print(result.get('agent_response', 'No response'))
    print("-" * 70)
    
    # Show learner output
    learner_output = result.get('learner_output', {})
    
    print("\n✓ Generated Content:")
    print(f"  • Explanation: {len(learner_output.get('explanation', ''))} characters")
    print(f"  • SVG Diagram: {'✓' if learner_output.get('svg') else '✗'}")
    print(f"  • Video suggestions: {len(learner_output.get('videos', []))}")
    print(f"  • MCQs: {len(learner_output.get('mcqs', []))}")
    
    # Show first MCQ
    if learner_output.get('mcqs'):
        print("\n📝 Sample MCQ:")
        mcq = learner_output['mcqs'][0]
        print(f"  Q: {mcq.get('q', 'N/A')}")
        for opt in mcq.get('opts', []):
            print(f"     {opt}")
        print(f"  ✓ Answer: {mcq.get('ans', 'N/A')}")
    
    # Save SVG if generated
    if learner_output.get('svg'):
        try:
            with open('demo_normalization.svg', 'w', encoding='utf-8') as f:
                f.write(learner_output['svg'])
            print("\n💾 SVG diagram saved to: demo_normalization.svg")
        except:
            pass
    
    return result

def demo_learner_different_topic(state: dict):
    """Demo learner with different topic"""
    demo_header("🎓 DEMO 3: LEARNER AGENT (Different Topic)")
    
    print("User asks: 'explain CPU Scheduling Algorithms'\n")
    
    state["user_message"] = "explain CPU Scheduling Algorithms"
    result = karma_graph.invoke(state)
    
    print("🤖 BOT RESPONSE:")
    print("-" * 70)
    print(result.get('agent_response', 'No response'))
    print("-" * 70)
    
    learner_output = result.get('learner_output', {})
    
    print("\n✓ Generated Content:")
    print(f"  • Topic: {learner_output.get('topic', 'N/A')}")
    print(f"  • Subject: {learner_output.get('subject', 'N/A')}")
    print(f"  • Explanation: {len(learner_output.get('explanation', ''))} chars")
    print(f"  • Videos: {len(learner_output.get('videos', []))}")
    
    # Show video suggestions
    if learner_output.get('videos'):
        print("\n🎥 Video Search Queries:")
        for i, video in enumerate(learner_output['videos'], 1):
            print(f"  {i}. {video}")
    
    return result

def demo_spaced_repetition(state: dict):
    """Demo spaced repetition feature"""
    demo_header("🔄 DEMO 4: SPACED REPETITION")
    
    print("Simulating task completion with rating...\n")
    
    # Start a task
    state["user_message"] = "next"
    state = karma_graph.invoke(state)
    
    print(f"Started task: {state.get('tasks', [{}])[0].get('title', 'Unknown')}")
    
    # Complete it
    state["user_message"] = "1"  # Yes, completed
    state = karma_graph.invoke(state)
    
    # Rate understanding
    state["user_message"] = "3"  # Mostly understood
    state = karma_graph.invoke(state)
    
    # Check for spaced revisions
    revision_tasks = [t for t in state.get('tasks', []) 
                      if t.get('type') == 'revision' and t.get('spaced_day_offset')]
    
    print(f"\n✓ Spaced Revisions Auto-Scheduled: {len(revision_tasks)}")
    for rev in revision_tasks[:3]:
        print(f"  • Day+{rev.get('spaced_day_offset')}: {rev.get('title')}")
        print(f"    Duration: {rev.get('duration_minutes')}min")
        print(f"    Available: {rev.get('available_on', 'N/A')[:10]}")
    
    print(f"\n📊 Stats:")
    print(f"  • XP earned: {state.get('xp')}")
    print(f"  • Streak: {state.get('streak')} days")
    
    return state

def demo_archive_system(state: dict):
    """Demo archive system"""
    demo_header("🗃️ DEMO 5: ARCHIVE SYSTEM")
    
    # Find a completed task to archive
    completed = [t for t in state.get('tasks', []) if t.get('status') == 'completed']
    
    if completed:
        topic = completed[0].get('topic') or completed[0].get('title')
        subject = completed[0].get('subject', 'General')
        
        print(f"Archiving topic: '{topic}' from {subject}\n")
        
        state["user_message"] = f"archive {topic} from {subject}"
        state = karma_graph.invoke(state)
        
        print("🤖 BOT RESPONSE:")
        print(result.get('agent_response', 'No response'))
        
        # Show vault
        vault = state.get('knowledge_vault', [])
        print(f"\n✓ Knowledge Vault: {len(vault)} topics")
        for entry in vault:
            stars = "★" * round(entry.get('mastery', 0)) + "☆" * (5 - round(entry.get('mastery', 0)))
            print(f"  • {entry.get('subject')}: {entry.get('topic')} {stars}")
    else:
        print("⚠️  No completed tasks to archive yet (needs task completion first)")
    
    return state

def run_quick_demo():
    """Run quick demo showing all features"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║              KARMASARATHI - QUICK DEMO                           ║
║                                                                  ║
║  Demonstrating: Planner + Learner + Spaced Repetition + Archive ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    try:
        # Demo 1: Quick planner setup
        state = quick_planner_setup()
        input("\n⏸  Press Enter to continue...")
        
        # Demo 2: Basic learner
        state = demo_learner_basic(state)
        input("\n⏸  Press Enter to continue...")
        
        # Demo 3: Learner with different topic
        state = demo_learner_different_topic(state)
        input("\n⏸  Press Enter to continue...")
        
        # Demo 4: Spaced repetition
        state = demo_spaced_repetition(state)
        input("\n⏸  Press Enter to continue...")
        
        # Demo 5: Archive system
        state = demo_archive_system(state)
        
        demo_header("✅ DEMO COMPLETE")
        print("All key features demonstrated successfully!")
        print("\nKey Takeaways:")
        print("  ✓ Planner creates personalized study strategy")
        print("  ✓ Learner generates multi-modal content (text + SVG + videos + MCQs)")
        print("  ✓ Spaced repetition auto-schedules revisions (day+1, +3, +7)")
        print("  ✓ Archive system preserves knowledge in vault")
        print("\nRun test_full_flow.py for comprehensive testing")
        print("Run test_learner_agent.py for detailed learner testing")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_quick_demo()
