"""
Test: Learning Unit Breakdown
Run: python -X utf8 test_learning_units.py
"""

from app.state import StudentState
from app.agents.planner import planner_node

SEP = "-" * 60

MINIMAL_STEPS = [
    ("Goal", "Semester Exam"),
    ("Deadline", "10 days"),
    ("Wake", "6 AM"),
    ("Sleep", "11 PM"),
    ("Breakfast", "7:30 AM"),
    ("Lunch", "1 PM"),
    ("Dinner", "8 PM"),
    ("College", "9am-4pm"),
    ("Gym", "no"),
    ("Travel", "30 min"),
    ("Prayer", "no"),
    ("Fixed", "no"),
    ("Water", "every 2 hours"),
    ("Goal specific", "1. OS\n2. OS\n3. 1"),
    ("Subjects", "OS 3 1/5"),
    ("Study mode", "1"),  # Focus mode
    ("Syllabus", "1"),  # Paste
    ("Topics", "OS: CPU Scheduling"),
    ("Completed", "all pending"),
    ("Focus", "45 min"),
    ("Break", "10"),
    ("Peak", "Morning"),
    ("Energy", "Morning"),
    ("Learning style", "Videos"),
    ("Adjust", "looks good"),
    ("Confirm", "yes"),
]


def run():
    print("\n" + "=" * 70)
    print("TEST: Learning Unit Breakdown")
    print("=" * 70)
    
    state = StudentState().model_dump()
    
    # Run through all steps
    for i, (label, message) in enumerate(MINIMAL_STEPS):
        state["user_message"] = message
        if state.get("planner_stage") and state["planner_stage"] != "done":
            state["intent"] = "planner"
        state = planner_node(state)
        
        if i < len(MINIMAL_STEPS) - 1:  # Don't show every step, just progress
            print(f".", end="", flush=True)
    
    print("\n\n" + SEP)
    print("LEARNING UNITS GENERATED")
    print(SEP)
    
    units = state.get("learning_units", [])
    
    if not units:
        print("❌ No learning units generated!")
        return
    
    print(f"\n✓ Total learning units: {len(units)}\n")
    
    # Group by subject and chapter
    by_subject = {}
    for unit in units:
        subj = unit.get("subject", "Unknown")
        chapter = unit.get("chapter", "Unknown")
        key = f"{subj} → {chapter}"
        if key not in by_subject:
            by_subject[key] = []
        by_subject[key].append(unit)
    
    for key, unit_list in by_subject.items():
        print(f"\n{key}")
        print("=" * 50)
        for i, unit in enumerate(unit_list, 1):
            unit_name = unit.get("unit_name", "N/A")
            unit_type = unit.get("unit_type", "N/A")
            est_min = unit.get("estimated_minutes", 0)
            status = unit.get("status", "pending")
            
            icon = "✔" if status == "completed" else "○"
            type_icon = {
                "concept": "📖",
                "example": "💡",
                "practice": "✏️",
                "quiz": "❓"
            }.get(unit_type, "📌")
            
            print(f"  {icon} {i:2d}. {type_icon} {unit_name:40s} ({est_min} min)")
    
    print("\n" + SEP)
    print("TASKS GENERATED FROM UNITS")
    print(SEP)
    
    tasks = state.get("tasks", [])
    study_tasks = [t for t in tasks if t.get("type") != "break"]
    
    print(f"\n✓ Total tasks: {len(tasks)} ({len(study_tasks)} study tasks + {len(tasks) - len(study_tasks)} breaks)\n")
    
    # Check if tasks have learning_unit_id
    tasks_with_units = [t for t in study_tasks if t.get("learning_unit_id")]
    print(f"✓ Tasks linked to learning units: {len(tasks_with_units)}/{len(study_tasks)}\n")
    
    # Show first 10 tasks
    print("First 10 tasks:")
    for i, task in enumerate(tasks[:10], 1):
        title = task.get("title", "N/A")
        ttype = task.get("type", "N/A")
        duration = task.get("duration_minutes", 0)
        unit_id = task.get("learning_unit_id", "")
        
        if ttype == "break":
            print(f"  {i:2d}. ☕ {title} ({duration} min)")
        else:
            print(f"  {i:2d}. {title} ({duration} min) [unit_id={unit_id}]")
    
    if len(tasks) > 10:
        print(f"  ... +{len(tasks) - 10} more tasks")
    
    # Verify structure
    print("\n" + SEP)
    print("STRUCTURE VERIFICATION")
    print(SEP)
    
    checks = []
    
    # Check 1: All units have required fields
    required_fields = ["id", "subject", "chapter", "unit_name", "unit_type", "status", 
                       "estimated_minutes", "resources"]
    for unit in units:
        missing = [f for f in required_fields if f not in unit]
        if missing:
            checks.append(f"❌ Unit {unit.get('id')} missing fields: {missing}")
    
    if not checks:
        checks.append("✓ All units have required fields")
    
    # Check 2: Unit types are valid
    valid_types = {"concept", "example", "practice", "quiz"}
    invalid = [u["id"] for u in units if u.get("unit_type") not in valid_types]
    if invalid:
        checks.append(f"❌ Invalid unit types in: {invalid}")
    else:
        checks.append("✓ All unit types valid")
    
    # Check 3: Tasks reference valid learning units
    unit_ids = {u["id"] for u in units}
    orphan_tasks = [t["id"] for t in study_tasks 
                    if t.get("learning_unit_id") and t["learning_unit_id"] not in unit_ids]
    if orphan_tasks:
        checks.append(f"❌ Tasks with invalid unit_id: {orphan_tasks}")
    else:
        checks.append("✓ All tasks reference valid learning units")
    
    # Check 4: Resources structure
    for unit in units:
        resources = unit.get("resources", {})
        if not isinstance(resources, dict):
            checks.append(f"❌ Unit {unit['id']} has invalid resources structure")
        elif not all(k in resources for k in ["videos", "diagrams", "notes", "practice", "quiz"]):
            checks.append(f"❌ Unit {unit['id']} missing resource fields")
    
    if len(checks) <= 3:  # Only the positive checks
        checks.append("✓ All resources structures valid")
    
    for check in checks:
        print(f"  {check}")
    
    print("\n" + "=" * 70)
    print("✅ Learning Unit Breakdown Test Complete")
    print("=" * 70)
    
    # Summary stats
    print(f"\nSummary:")
    print(f"  Subjects: {len(state.get('subjects', []))}")
    print(f"  Chapters: {len(set(u['chapter'] for u in units))}")
    print(f"  Learning Units: {len(units)}")
    print(f"  Tasks: {len(tasks)}")
    print(f"  Average units per chapter: {len(units) / max(len(set(u['chapter'] for u in units)), 1):.1f}")
    
    unit_types = {}
    for unit in units:
        ut = unit.get("unit_type", "unknown")
        unit_types[ut] = unit_types.get(ut, 0) + 1
    
    print(f"\n  Unit type distribution:")
    for ut, count in sorted(unit_types.items()):
        print(f"    {ut:10s}: {count}")


if __name__ == "__main__":
    run()
