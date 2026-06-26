"""
Daily Planning Cycle Agent

Responsibilities:
1. Morning reassessment — generate fresh optimized plan for today
2. End-of-day review — analyze progress, update metrics
3. Tomorrow preparation — pre-calculate next day's plan
4. Deadline tracking — monitor progress vs deadline

Called by orchestrator at:
- Start of day (first message after midnight)
- End of day (explicit "goodnight" or after 10 PM)
- On-demand (user asks "plan today" or "review day")
"""

import re
from datetime import datetime, timedelta, date
from app.state import StudentState


def _parse_deadline_days(deadline_str: str | None) -> int:
    """Parse deadline string to days remaining."""
    if not deadline_str:
        return 7
    s = str(deadline_str).lower().strip()
    if "tomorrow" in s:
        return 1
    nums = re.findall(r"\d+", s)
    return int(nums[0]) if nums else 7


def _calculate_progress_metrics(s: StudentState) -> dict:
    """Calculate progress metrics for dashboard."""
    total_units = len(s.learning_units)
    completed = len([u for u in s.learning_units if u.get("status") in ("completed", "mastered")])
    pending = total_units - completed
    
    # Calculate average mastery
    completed_units = [u for u in s.learning_units if u.get("status") in ("completed", "mastered")]
    avg_mastery = sum(u.get("mastery", 0) for u in completed_units) / len(completed_units) if completed_units else 0
    
    # Time statistics
    total_time = sum(u.get("actual_time_spent", 0) for u in s.learning_units)
    hours = total_time // 60
    mins = total_time % 60
    
    # Calculate velocity (units per day)
    if s.current_day > 1:
        velocity = completed / (s.current_day - 1)
    else:
        velocity = 0
    
    # Deadline pressure
    days_remaining = _parse_deadline_days(s.deadline)
    if days_remaining > 0 and pending > 0:
        required_velocity = pending / days_remaining
        on_track = velocity >= required_velocity if velocity > 0 else None
    else:
        required_velocity = 0
        on_track = True
    
    return {
        "total_units": total_units,
        "completed": completed,
        "pending": pending,
        "completion_pct": round(completed / total_units * 100) if total_units else 0,
        "avg_mastery": round(avg_mastery, 1),
        "total_time_hours": hours,
        "total_time_mins": mins,
        "velocity": round(velocity, 2),
        "required_velocity": round(required_velocity, 2),
        "on_track": on_track,
        "days_remaining": days_remaining,
    }


def morning_reassessment(state: dict) -> dict:
    """
    Called at start of each day.
    
    Steps:
    1. Check revisions due today
    2. Check practice due today
    3. Calculate target units for today
    4. Prioritize: Revisions > Practice > New Learning
    5. Generate optimized task list for today
    6. Trigger scheduler to build time-blocked schedule
    """
    s = StudentState(**state)
    
    today = date.today()
    s.current_day += 1
    s.today_date = today.isoformat()
    s.completed_today = 0
    s.recovered_time_minutes = 0
    s.daily_plan_status = "planning"
    
    print(f"[Daily Planner] Morning reassessment — Day {s.current_day}")
    
    # 1. Check revisions due today
    s.today_revisions_due = []
    for unit in s.learning_units:
        next_rev = unit.get("next_revision")
        if next_rev:
            try:
                rev_date = datetime.fromisoformat(next_rev).date()
                if rev_date <= today:
                    s.today_revisions_due.append(unit["id"])
            except:
                pass
    
    # 2. Check practice due today
    s.today_practice_due = []
    for unit in s.learning_units:
        practice_due = unit.get("practice_due")
        if practice_due:
            try:
                practice_date = datetime.fromisoformat(practice_due).date()
                if practice_date <= today:
                    s.today_practice_due.append(unit["id"])
            except:
                pass
    
    # 3. Calculate target units for today
    pending_units = len([u for u in s.learning_units if u.get("status") == "pending"])
    days_remaining = _parse_deadline_days(s.deadline)
    
    if days_remaining > 0 and pending_units > 0:
        s.today_target_units = max(1, round(pending_units / days_remaining))
    else:
        s.today_target_units = min(3, pending_units)
    
    # 4. Prioritize tasks
    priority_tasks = []
    
    # Add revision-due tasks (highest priority)
    for unit_id in s.today_revisions_due:
        unit = next((u for u in s.learning_units if u["id"] == unit_id), None)
        if unit:
            # Find or create revision task
            task = next((t for t in s.tasks 
                        if t.get("learning_unit_id") == unit_id 
                        and t.get("type") == "revision"
                        and t.get("status") == "pending"), None)
            
            if not task:
                # Create revision task
                next_id = max((t.get("id", 0) for t in s.tasks), default=0) + 1
                task = {
                    "id": next_id,
                    "title": f"Revise: {unit['unit_name']}",
                    "subject": unit["subject"],
                    "chapter": unit["chapter"],
                    "topic": unit["unit_name"],
                    "learning_unit_id": unit["id"],
                    "type": "revision",
                    "duration_minutes": 20,
                    "priority": "critical",
                    "difficulty": "easy",
                    "energy": "low",
                    "depends_on": [],
                    "recommended_resource_type": "revision",
                    "status": "pending",
                    "reason": "Revision due today (spaced repetition)",
                }
                s.tasks.append(task)
            
            priority_tasks.append((1, task))  # priority 1 = highest
    
    # Add practice-due tasks
    for unit_id in s.today_practice_due:
        unit = next((u for u in s.learning_units if u["id"] == unit_id), None)
        if unit:
            task = next((t for t in s.tasks 
                        if t.get("learning_unit_id") == unit_id 
                        and t.get("type") == "practice"
                        and t.get("status") == "pending"), None)
            
            if not task:
                next_id = max((t.get("id", 0) for t in s.tasks), default=0) + 1
                task = {
                    "id": next_id,
                    "title": f"Practice: {unit['unit_name']}",
                    "subject": unit["subject"],
                    "chapter": unit["chapter"],
                    "topic": unit["unit_name"],
                    "learning_unit_id": unit["id"],
                    "type": "practice",
                    "duration_minutes": 25,
                    "priority": "high",
                    "difficulty": "medium",
                    "energy": "medium",
                    "depends_on": [],
                    "recommended_resource_type": "practice",
                    "status": "pending",
                    "reason": "Practice due today",
                }
                s.tasks.append(task)
            
            priority_tasks.append((2, task))
    
    # Add new learning tasks (by subject priority)
    priority_subjects = s.structured_strategy.get("priority_order", []) if s.structured_strategy else []
    pending_tasks = [t for t in s.tasks 
                    if t.get("status") == "pending" 
                    and t.get("type") in ("learning", "concept")
                    and t not in [pt[1] for pt in priority_tasks]]
    
    for task in pending_tasks[:s.today_target_units]:
        subj_priority = priority_subjects.index(task.get("subject", "")) if task.get("subject") in priority_subjects else 99
        priority_tasks.append((3 + subj_priority, task))
    
    # Sort by priority and update task order
    priority_tasks.sort(key=lambda x: x[0])
    
    s.daily_plan_status = "in_progress"
    
    # Build response
    metrics = _calculate_progress_metrics(s)
    
    lines = [
        f"🌅 Good morning! Day {s.current_day} Planning",
        "",
        f"📊 Progress Dashboard:",
        f"  Completed: {metrics['completed']}/{metrics['total_units']} units ({metrics['completion_pct']}%)",
        f"  Average mastery: {metrics['avg_mastery']}/5",
        f"  Time invested: {metrics['total_time_hours']}h {metrics['total_time_mins']}m",
        "",
        f"📅 Deadline: {s.deadline} ({metrics['days_remaining']} days)",
    ]
    
    if metrics["on_track"] is True:
        lines.append(f"  ✅ On track! (Pace: {metrics['velocity']} units/day, Need: {metrics['required_velocity']})")
    elif metrics["on_track"] is False:
        lines.append(f"  ⚠️ Behind schedule (Pace: {metrics['velocity']} units/day, Need: {metrics['required_velocity']})")
    else:
        lines.append(f"  📈 Building momentum...")
    
    lines.append("")
    lines.append(f"🎯 Today's Goal: {s.today_target_units} learning units")
    
    if s.today_revisions_due:
        lines.append(f"  🔄 {len(s.today_revisions_due)} revisions due (spaced repetition)")
    if s.today_practice_due:
        lines.append(f"  ✏️ {len(s.today_practice_due)} practice sessions due")
    
    lines.append("")
    lines.append("📋 Today's Priority Tasks:")
    for i, (_, task) in enumerate(priority_tasks[:5], 1):
        icon = "🔄" if task.get("type") == "revision" else "✏️" if task.get("type") == "practice" else "📖"
        lines.append(f"  {i}. {icon} {task['title']} ({task.get('duration_minutes')}m)")
    
    if len(priority_tasks) > 5:
        lines.append(f"  ... +{len(priority_tasks) - 5} more tasks")
    
    lines.append("")
    lines.append("Type 'schedule' for time-blocked timetable, or 'next' to start first task.")
    
    s.agent_response = "\n".join(lines)
    s.reschedule_needed = True  # Trigger scheduler
    
    return s.model_dump()


def end_of_day_review(state: dict) -> dict:
    """
    Called at end of day.
    
    Steps:
    1. Analyze today's progress
    2. Update metrics
    3. Identify gaps and risks
    4. Prepare tomorrow's plan
    5. Update streak/badges
    """
    s = StudentState(**state)
    
    print(f"[Daily Planner] End-of-day review — Day {s.current_day}")
    
    # Get metrics
    metrics = _calculate_progress_metrics(s)
    
    # Today's completed units
    today_completed = [u for u in s.learning_units 
                      if u.get("completed_at") 
                      and u["completed_at"].startswith(date.today().isoformat())]
    
    # Achievement level
    target = s.today_target_units
    actual = len(today_completed)
    
    if actual >= target:
        achievement = "🌟 Excellent! Target achieved."
    elif actual >= target * 0.75:
        achievement = "👍 Good progress! Close to target."
    elif actual >= target * 0.5:
        achievement = "📈 Steady progress. Let's pick up pace tomorrow."
    elif actual > 0:
        achievement = "💪 You showed up. Consistency matters."
    else:
        achievement = "😔 No progress today. Let's regroup tomorrow."
    
    # Calculate tomorrow's target
    days_remaining = metrics["days_remaining"] - 1
    pending_units = metrics["pending"]
    
    if days_remaining > 0 and pending_units > 0:
        tomorrow_target = max(1, round(pending_units / days_remaining))
    else:
        tomorrow_target = min(3, pending_units)
    
    # Identify risks
    risks = []
    if metrics["on_track"] is False:
        risks.append("⚠️ Behind schedule — need to increase daily pace")
    
    overdue_revisions = len([u for u in s.learning_units 
                            if u.get("next_revision") 
                            and datetime.fromisoformat(u["next_revision"]).date() < date.today()])
    if overdue_revisions > 0:
        risks.append(f"⚠️ {overdue_revisions} overdue revisions — forgetting risk")
    
    low_mastery = len([u for u in s.learning_units 
                      if u.get("status") == "completed" and u.get("mastery", 0) < 3])
    if low_mastery > 0:
        risks.append(f"⚠️ {low_mastery} topics with low mastery — need revision")
    
    # Build response
    lines = [
        f"🌙 Day {s.current_day} Review",
        "",
        achievement,
        "",
        f"📊 Today's Stats:",
        f"  Target: {target} units",
        f"  Completed: {actual} units",
        f"  Study time: {s.total_study_minutes // 60}h {s.total_study_minutes % 60}m",
        f"  XP earned: {s.xp}",
        f"  Streak: {s.streak} days",
        "",
        f"📈 Overall Progress:",
        f"  {metrics['completed']}/{metrics['total_units']} units ({metrics['completion_pct']}%)",
        f"  Days remaining: {days_remaining}",
    ]
    
    if metrics["on_track"] is True:
        lines.append(f"  ✅ On track for deadline")
    elif metrics["on_track"] is False:
        lines.append(f"  ⚠️ Need to catch up")
    
    if risks:
        lines.append("")
        lines.append("⚠️ Action Needed:")
        for risk in risks:
            lines.append(f"  {risk}")
    
    lines.append("")
    lines.append(f"🎯 Tomorrow's Target: {tomorrow_target} learning units")
    
    # Preview tomorrow's top tasks
    pending_tasks = [t for t in s.tasks if t.get("status") == "pending"][:3]
    if pending_tasks:
        lines.append("")
        lines.append("📋 Tomorrow's Top Tasks:")
        for task in pending_tasks:
            lines.append(f"  • {task['title']} ({task.get('duration_minutes')}m)")
    
    lines.append("")
    lines.append("Rest well. Tomorrow's plan will be ready when you wake up. 😴")
    
    s.agent_response = "\n".join(lines)
    s.daily_plan_status = "completed"
    
    # Update state for tomorrow
    s.today_target_units = tomorrow_target
    
    return s.model_dump()


def deadline_dashboard(state: dict) -> dict:
    """Show comprehensive deadline tracking dashboard."""
    s = StudentState(**state)
    
    metrics = _calculate_progress_metrics(s)
    
    # Calculate burndown
    days_elapsed = s.current_day - 1
    days_remaining = metrics["days_remaining"]
    total_days = days_elapsed + days_remaining
    
    # Expected vs actual progress
    expected_completion = (days_elapsed / total_days * 100) if total_days > 0 else 0
    actual_completion = metrics["completion_pct"]
    
    # Burndown chart (text-based)
    chart_width = 20
    completed_bar = "█" * int(actual_completion / 100 * chart_width)
    expected_marker = " " * int(expected_completion / 100 * chart_width) + "▼"
    remaining_bar = "░" * (chart_width - len(completed_bar))
    
    # Subject-wise breakdown
    subject_stats = []
    for subj in s.subjects:
        subj_units = [u for u in s.learning_units if u.get("subject") == subj["name"]]
        if not subj_units:
            continue
        
        completed = len([u for u in subj_units if u.get("status") in ("completed", "mastered")])
        total = len(subj_units)
        pct = round(completed / total * 100) if total else 0
        
        subject_stats.append({
            "name": subj["name"],
            "completed": completed,
            "total": total,
            "pct": pct,
            "confidence": subj.get("confidence", 5),
        })
    
    subject_stats.sort(key=lambda x: x["pct"])  # Show weakest first
    
    lines = [
        "📊 Deadline Tracking Dashboard",
        f"   Goal: {s.goal}",
        f"   Deadline: {s.deadline}",
        "",
        f"⏱️ Timeline:",
        f"  Day {s.current_day} / ~{total_days}",
        f"  Days remaining: {days_remaining}",
        "",
        f"📈 Progress:",
        f"  [{completed_bar}{remaining_bar}] {actual_completion}%",
        f"  {expected_marker} ← Expected: {int(expected_completion)}%",
        "",
        f"📊 Metrics:",
        f"  Completed: {metrics['completed']}/{metrics['total_units']} units",
        f"  Average mastery: {metrics['avg_mastery']}/5",
        f"  Velocity: {metrics['velocity']} units/day",
        f"  Required: {metrics['required_velocity']} units/day",
    ]
    
    if metrics["on_track"] is True:
        lines.append(f"  Status: ✅ On track")
    elif metrics["on_track"] is False:
        gap = metrics["required_velocity"] - metrics["velocity"]
        lines.append(f"  Status: ⚠️ Behind (need +{gap:.1f} units/day)")
    
    lines.append("")
    lines.append("📚 Subject Breakdown:")
    for stat in subject_stats:
        bar = "█" * int(stat["pct"] / 10) + "░" * (10 - int(stat["pct"] / 10))
        conf = "★" * stat["confidence"] + "☆" * (10 - stat["confidence"])
        lines.append(f"  {stat['name']:10s} [{bar}] {stat['pct']:3d}%  |  {conf}")
    
    lines.append("")
    lines.append("💡 Recommendations:")
    
    if metrics["on_track"] is False:
        lines.append("  • Increase daily study sessions")
        lines.append("  • Focus on high-priority subjects")
    
    weak_subjects = [s for s in subject_stats if s["pct"] < 50]
    if weak_subjects:
        lines.append(f"  • Prioritize: {', '.join(s['name'] for s in weak_subjects[:2])}")
    
    if metrics["avg_mastery"] < 3:
        lines.append("  • Schedule more revision sessions")
    
    s.agent_response = "\n".join(lines)
    
    return s.model_dump()


def daily_planner_node(state: dict) -> dict:
    """
    Main entry point for daily planning cycle.
    
    Routes to:
    - morning_reassessment() if start of day
    - end_of_day_review() if end of day
    - deadline_dashboard() if requested
    """
    s = StudentState(**state)
    msg = s.user_message.strip().lower()
    
    # Check if it's a new day
    today = date.today().isoformat()
    is_new_day = s.today_date != today
    
    # Route based on intent
    if "dashboard" in msg or "deadline" in msg:
        return deadline_dashboard(state)
    
    elif "end of day" in msg or "goodnight" in msg or "good night" in msg:
        return end_of_day_review(state)
    
    elif is_new_day or "plan today" in msg or "morning" in msg or msg == "start":
        return morning_reassessment(state)
    
    else:
        # Default: show current day status
        s.agent_response = (
            f"Day {s.current_day} in progress.\n\n"
            f"Type 'dashboard' for deadline tracking, or 'next' to continue studying."
        )
        return s.model_dump()
