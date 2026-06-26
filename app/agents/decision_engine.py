"""
Event-Driven Decision Engine

Wakes up on every state change to make intelligent decisions:
- Task completion → unlock dependent units
- Confidence change → promote/demote tasks
- Deadline pressure → adjust pace
- Revision overdue → re-prioritize
- Low mastery detected → inject revision
- Streak broken → motivational intervention

Called by orchestrator after every progress update.
"""

from datetime import datetime, timedelta, date
from app.state import StudentState


def _auto_unlock_dependent_units(s: StudentState, completed_unit_id: int) -> tuple[StudentState, list[str]]:
    """
    When a learning unit is completed, unlock units that depend on it.
    Returns updated state and list of unlocked unit names.
    """
    unlocked = []
    
    # Find units that depend on the completed unit
    for unit in s.learning_units:
        if unit.get("status") == "pending":
            # Check if this unit has the completed unit as a prerequisite
            # (This assumes learning units have a dependency structure)
            # For now, we'll unlock within the same chapter sequentially
            
            completed_unit = next((u for u in s.learning_units if u["id"] == completed_unit_id), None)
            if not completed_unit:
                continue
            
            # If same chapter and next in sequence
            if (unit.get("chapter") == completed_unit.get("chapter")
                and unit.get("subject") == completed_unit.get("subject")
                and unit["id"] > completed_unit_id
                and unit["id"] == completed_unit_id + 1):
                
                # Check if this unit has a pending task
                has_pending_task = any(
                    t.get("learning_unit_id") == unit["id"] 
                    and t.get("status") == "pending"
                    for t in s.tasks
                )
                
                if not has_pending_task:
                    # Create unlocked task
                    next_id = max((t.get("id", 0) for t in s.tasks), default=0) + 1
                    
                    task_type = "learning" if unit.get("unit_type") == "concept" else unit.get("unit_type", "learning")
                    
                    s.tasks.append({
                        "id": next_id,
                        "title": f"Learn: {unit['unit_name']}",
                        "subject": unit["subject"],
                        "chapter": unit["chapter"],
                        "topic": unit["unit_name"],
                        "learning_unit_id": unit["id"],
                        "type": task_type,
                        "duration_minutes": unit.get("estimated_minutes", 15),
                        "priority": "high",
                        "difficulty": unit.get("difficulty", "medium"),
                        "energy": "high",
                        "depends_on": [completed_unit_id],
                        "recommended_resource_type": "explanation",
                        "status": "pending",
                        "reason": f"Unlocked after completing {completed_unit.get('unit_name')}",
                    })
                    
                    unlocked.append(unit["unit_name"])
    
    return s, unlocked


def _adjust_pace_for_deadline(s: StudentState) -> tuple[StudentState, str | None]:
    """
    Monitor deadline pressure and adjust daily pace.
    Returns adjustment message if action taken.
    """
    from app.agents.daily_planner import _calculate_progress_metrics
    
    metrics = _calculate_progress_metrics(s)
    
    # If behind schedule, increase daily target
    if metrics["on_track"] is False:
        gap = metrics["required_velocity"] - metrics["velocity"]
        
        if gap > 1:  # Significantly behind
            # Increase target by 50%
            s.today_target_units = int(s.today_target_units * 1.5)
            
            msg = (
                f"⚠️ Deadline Pressure Alert:\n"
                f"   Current pace: {metrics['velocity']:.1f} units/day\n"
                f"   Required: {metrics['required_velocity']:.1f} units/day\n"
                f"   Gap: {gap:.1f} units/day\n\n"
                f"📈 Adjustment: Increased today's target to {s.today_target_units} units.\n"
                f"   Consider extending study hours or shortening breaks."
            )
            return s, msg
    
    return s, None


def _detect_and_fix_forgetting(s: StudentState) -> tuple[StudentState, str | None]:
    """
    Detect units with overdue revisions or declining mastery.
    Auto-schedule urgent revision sessions.
    """
    today = date.today()
    urgent_revisions = []
    
    # Find overdue revisions
    for unit in s.learning_units:
        if unit.get("status") in ("completed", "mastered"):
            next_rev = unit.get("next_revision")
            if next_rev:
                try:
                    rev_date = datetime.fromisoformat(next_rev).date()
                    days_overdue = (today - rev_date).days
                    
                    if days_overdue > 0:
                        urgent_revisions.append({
                            "unit": unit,
                            "days_overdue": days_overdue,
                            "priority": days_overdue,  # More overdue = higher priority
                        })
                except:
                    pass
            
            # Also check mastery decline (if tracked in revision_history)
            rev_history = unit.get("revision_history", [])
            if len(rev_history) >= 2:
                recent_ratings = [h.get("rating", 0) for h in rev_history[-2:]]
                if recent_ratings and recent_ratings[-1] < recent_ratings[-2]:
                    # Mastery declining
                    urgent_revisions.append({
                        "unit": unit,
                        "days_overdue": 0,
                        "priority": 5 - recent_ratings[-1],  # Lower rating = higher priority
                    })
    
    if not urgent_revisions:
        return s, None
    
    # Sort by priority and create urgent revision tasks
    urgent_revisions.sort(key=lambda x: x["priority"], reverse=True)
    
    added = 0
    for item in urgent_revisions[:3]:  # Top 3 most urgent
        unit = item["unit"]
        
        # Check if revision task already exists
        has_task = any(
            t.get("learning_unit_id") == unit["id"]
            and t.get("type") == "revision"
            and t.get("status") == "pending"
            for t in s.tasks
        )
        
        if not has_task:
            next_id = max((t.get("id", 0) for t in s.tasks), default=0) + 1
            
            s.tasks.insert(0, {  # Insert at front (highest priority)
                "id": next_id,
                "title": f"URGENT Revision: {unit['unit_name']}",
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
                "reason": f"Overdue by {item['days_overdue']} days - forgetting risk",
            })
            added += 1
    
    if added > 0:
        s.reschedule_needed = True
        msg = (
            f"🔴 Forgetting Risk Detected!\n"
            f"   {added} urgent revision{'s' if added > 1 else ''} added to your schedule.\n"
            f"   These topics are at risk of being forgotten.\n\n"
            f"📌 Review them ASAP to maintain mastery."
        )
        return s, msg
    
    return s, None


def _promote_demote_tasks_by_confidence(s: StudentState, subject: str, old_conf: int, new_conf: int) -> tuple[StudentState, str | None]:
    """
    When subject confidence changes significantly, adjust task types.
    
    Confidence <= 4: Focus on Study (theory)
    Confidence 5-6: Mix Study + Practice
    Confidence >= 7: Promote to Practice (application)
    """
    if new_conf == old_conf:
        return s, None
    
    msg_parts = []
    
    # Promote: confidence reached 7+ (from <7)
    if new_conf >= 7 and old_conf < 7:
        promoted = 0
        for task in s.tasks:
            if (task.get("status") == "pending"
                and task.get("subject") == subject
                and task.get("type") == "learning"):
                
                task["type"] = "practice"
                task["title"] = task["title"].replace("Study", "Practice").replace("Learn", "Practice")
                task["recommended_resource_type"] = "practice"
                task["reason"] = f"Confidence reached {new_conf}/10 → promoted to application mode"
                promoted += 1
        
        if promoted > 0:
            msg_parts.append(
                f"🎯 Confidence Boost: {subject}\n"
                f"   {old_conf}/10 → {new_conf}/10\n"
                f"   {promoted} tasks promoted to Practice mode."
            )
    
    # Demote: confidence dropped below 5
    elif new_conf < 5 and old_conf >= 5:
        demoted = 0
        for task in s.tasks:
            if (task.get("status") == "pending"
                and task.get("subject") == subject
                and task.get("type") == "practice"):
                
                task["type"] = "learning"
                task["title"] = task["title"].replace("Practice", "Study")
                task["recommended_resource_type"] = "explanation"
                task["reason"] = f"Confidence dropped to {new_conf}/10 → back to concept review"
                demoted += 1
        
        if demoted > 0:
            msg_parts.append(
                f"⚠️ Confidence Drop: {subject}\n"
                f"   {old_conf}/10 → {new_conf}/10\n"
                f"   {demoted} tasks reverted to Study mode (concept focus)."
            )
    
    if msg_parts:
        s.reschedule_needed = True
        return s, "\n\n".join(msg_parts)
    
    return s, None


def _motivational_intervention(s: StudentState, event: str) -> str | None:
    """
    Provide motivational messages for specific events.
    
    Events:
    - streak_broken
    - milestone_reached
    - halfway_complete
    - deadline_near
    """
    if event == "streak_broken":
        return (
            "💔 Streak Broken\n\n"
            "Don't worry—progress isn't lost. Streaks are about consistency, not perfection.\n"
            "What matters is that you came back. Let's restart stronger.\n\n"
            "Type 'next' to continue."
        )
    
    elif event == "milestone_reached":
        completed = len([u for u in s.learning_units if u.get("status") in ("completed", "mastered")])
        total = len(s.learning_units)
        pct = round(completed / total * 100) if total else 0
        
        if pct >= 25 and pct < 30:
            return "🎉 25% Complete! You've built momentum. Keep going."
        elif pct >= 50 and pct < 55:
            return "🎉 Halfway There! The hardest part is behind you."
        elif pct >= 75 and pct < 80:
            return "🎉 75% Complete! The finish line is in sight."
        elif pct >= 100:
            return "🏆 ALL DONE! You've completed your study plan. Incredible work!"
    
    elif event == "deadline_near":
        from app.agents.daily_planner import _parse_deadline_days
        days = _parse_deadline_days(s.deadline)
        
        if days == 1:
            return "⏰ Deadline Tomorrow! Final push. Review key topics and stay calm."
        elif days <= 3:
            return f"⏰ {days} Days Left! Focus on high-priority topics and practice."
    
    elif event == "halfway_complete":
        return (
            "🎯 Milestone Unlocked: Halfway Complete!\n\n"
            "You've crossed the 50% mark. The momentum you've built is real.\n"
            "The second half will feel easier because you've proven you can do this.\n\n"
            "Keep going. You're on track."
        )
    
    return None


def decision_engine(state: dict, event: str, context: dict = None) -> dict:
    """
    Main decision engine entry point.
    
    Called by orchestrator after every state change with event type:
    - "task_completed" → unlock next, adjust confidence
    - "day_started" → check revisions, adjust pace
    - "rating_low" → inject revision
    - "deadline_check" → pressure adjustment
    - "streak_event" → motivational intervention
    
    Args:
        state: Current StudentState
        event: Event type string
        context: Additional event data (e.g., {"task_id": 123, "rating": 2})
    
    Returns:
        Updated state dict with decision messages
    """
    s = StudentState(**state)
    context = context or {}
    
    messages = []
    
    # Event: Task Completed
    if event == "task_completed":
        task_id = context.get("task_id")
        unit_id = context.get("learning_unit_id")
        
        if unit_id:
            # Auto-unlock dependent units
            s, unlocked = _auto_unlock_dependent_units(s, unit_id)
            if unlocked:
                messages.append(
                    f"🔓 Unlocked: {', '.join(unlocked[:3])}"
                    + (f" (+{len(unlocked)-3} more)" if len(unlocked) > 3 else "")
                )
                s.reschedule_needed = True
        
        # Check milestone
        milestone_msg = _motivational_intervention(s, "milestone_reached")
        if milestone_msg:
            messages.append(milestone_msg)
    
    # Event: Confidence Changed
    elif event == "confidence_changed":
        subject = context.get("subject")
        old_conf = context.get("old_confidence", 5)
        new_conf = context.get("new_confidence", 5)
        
        s, msg = _promote_demote_tasks_by_confidence(s, subject, old_conf, new_conf)
        if msg:
            messages.append(msg)
    
    # Event: Day Started
    elif event == "day_started":
        # Check deadline pressure
        s, msg = _adjust_pace_for_deadline(s)
        if msg:
            messages.append(msg)
        
        # Check forgetting risk
        s, msg = _detect_and_fix_forgetting(s)
        if msg:
            messages.append(msg)
        
        # Check deadline proximity
        deadline_msg = _motivational_intervention(s, "deadline_near")
        if deadline_msg:
            messages.append(deadline_msg)
    
    # Event: Low Rating
    elif event == "low_rating":
        # Auto-revision already handled in progress.py
        # Additional check for persistent low ratings
        task_id = context.get("task_id")
        rating = context.get("rating", 3)
        
        if rating <= 1:
            messages.append(
                "📚 Consider:\n"
                "  • Breaking this topic into smaller parts\n"
                "  • Watching a video explanation\n"
                "  • Using the Tutor agent for step-by-step guidance"
            )
    
    # Event: Streak Broken
    elif event == "streak_broken":
        msg = _motivational_intervention(s, "streak_broken")
        if msg:
            messages.append(msg)
    
    # Event: Deadline Check (manual trigger)
    elif event == "deadline_check":
        s, msg = _adjust_pace_for_deadline(s)
        if msg:
            messages.append(msg)
    
    # Append decision messages to response
    if messages:
        decision_msg = "\n\n".join(messages)
        if s.agent_response:
            s.agent_response += "\n\n" + decision_msg
        else:
            s.agent_response = decision_msg
    
    return s.model_dump()
